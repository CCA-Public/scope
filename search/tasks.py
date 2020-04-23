import logging

from celery import shared_task
from django.db.utils import DatabaseError
from elasticsearch.exceptions import TransportError
from elasticsearch.helpers import bulk
from elasticsearch_dsl.connections import connections

from scope.models import DIP
from scope.models import Collection
from scope.models import DigitalFile

# Use a normal logger to avoid redirecting both `stdout` and `stderr` to the
# logger and back when using Celery's `get_task_logger`, and to avoid changing
# the default `CELERY_REDIRECT_STDOUTS_LEVEL` when using `print`.
logger = logging.getLogger("search.tasks")


@shared_task(
    autoretry_for=(TransportError, DatabaseError),
    max_retries=10,
    default_retry_delay=30,
    ignore_result=True,
)
def update_es_descendants(class_name, pk):
    """Update the related DigitalFiles documents in ES.

    With the partial data from the ancestor Collection or DIP.
    """
    if class_name not in ["Collection", "DIP"]:
        raise ValueError("Can not update descendants of %s." % class_name)
    logger.info("Updating DigitalFiles of %s [id: %s] " % (class_name, pk))
    if class_name == "Collection":
        collection = Collection.objects.get(pk=pk)
        # Partial update with `doc` doesn't remove the fields missing in data,
        # they have to be removed via script to clear the existing value,
        # `script` and `doc` can't be combined in update actions, therefore
        # it's required to generate a Painless script to perform the update.
        script = {
            "source": "ctx._source.collection = params.collection;",
            "lang": "painless",
            "params": {"collection": collection.get_es_data_for_files()},
        }
        file_uuids = DigitalFile.objects.filter(dip__collection__pk=pk).values_list(
            "uuid", flat=True
        )
    else:
        dip = DIP.objects.get(pk=pk)
        data_params = {"dip": dip.get_es_data_for_files()}
        if dip.collection:
            data_params["collection"] = dip.collection.get_es_data_for_files()
        script = {
            "source": """
                ctx._source.dip = params.dip;
                if (params.containsKey('collection')) {
                  ctx._source.collection = params.collection;
                } else {
                  ctx._source.remove('collection');
                }
            """,
            "lang": "painless",
            "params": data_params,
        }
        file_uuids = DigitalFile.objects.filter(dip__pk=pk).values_list(
            "uuid", flat=True
        )
    # Get connection to ES
    es = connections.get_connection()
    # Bulk update with partial data
    success_count, errors = bulk(
        es,
        (
            {
                "_op_type": "update",
                "_index": DigitalFile.es_doc._index._name,
                "_type": DigitalFile.es_doc._doc_type.name,
                "_id": uuid,
                "script": script,
            }
            for uuid in file_uuids
        ),
    )
    logger.info("%d/%d DigitalFiles updated." % (success_count, len(file_uuids)))
    if len(errors) > 0:
        logger.info("The following errors were encountered:")
        for error in errors:
            logger.info("- %s" % error)


@shared_task(
    autoretry_for=(TransportError,),
    max_retries=10,
    default_retry_delay=30,
    ignore_result=True,
)
def delete_es_descendants(class_name, pk):
    """Deletes the related documents in ES based on the ancestor id."""
    if class_name not in ["Collection", "DIP"]:
        raise ValueError("Can not delete descendants of %s." % class_name)
    logger.info("Deleting descendants of %s [id: %s] " % (class_name, pk))
    if class_name == "Collection":
        # DIPs and DigitalFiles use the same field to store the Collection id
        # so we can perform a single delete_by_query request over both indexes.
        indexes = "%s,%s" % (DIP.es_doc._index._name, DigitalFile.es_doc._index._name)
        body = {"query": {"match": {"collection.id": pk}}}
    else:
        indexes = DigitalFile.es_doc._index._name
        body = {"query": {"match": {"dip.id": pk}}}
    es = connections.get_connection()
    response = es.delete_by_query(index=indexes, body=body)
    logger.info("%d/%d descendants deleted." % (response["deleted"], response["total"]))
    if response["failures"] and len(response["failures"]) > 0:
        logger.info("The following errors were encountered:")
        for error in response["failures"]:
            logger.info("- %s" % error)
