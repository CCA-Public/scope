from celery import shared_task, states, Task
from django.db.utils import DatabaseError
from elasticsearch.exceptions import TransportError
from elasticsearch.helpers import bulk
from elasticsearch_dsl.connections import connections
from .parsemets import METS
from .models import Collection, DIP, DigitalFile

import logging
import os
import re
import tempfile
import zipfile

# Use a normal logger to avoid redirecting both `stdout` and `stderr` to the
# logger and back when using Celery's `get_task_logger`, and to avoid changing
# the default `CELERY_REDIRECT_STDOUTS_LEVEL` when using `print`.
logger = logging.getLogger('dips.tasks')


class MetsTask(Task):

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Update DIP `import_status` when the task ends. Make sure it's one
        of Celery's READY_STATES and set it to 'FAILURE' for all possible
        non 'SUCCESS' states.
        """
        if status not in states.READY_STATES:
            return
        dip = DIP.objects.get(pk=args[0])
        logger.info('Updating DIP import status [Identifier: %s]' % dip.dc.identifier)
        if status == states.SUCCESS:
            dip.import_status = DIP.IMPORT_SUCCESS
        else:
            dip.import_status = DIP.IMPORT_FAILURE
        # This save is triggering another Celery task (update_es_descendants),
        # TODO: consider the use of task chains.
        dip.save()


@shared_task(
    base=MetsTask, autoretry_for=(TransportError, DatabaseError,),
    max_retries=10, default_retry_delay=30,
)
def extract_and_parse_mets(dip_id, zip_path):
    """
    Extracts a METS file from a given DIP zip file and uses the METS class
    to parse its content, create the related DigitalFiles and update the DIP
    DC metadata. Creates and deletes a temporary directory to hold the METS
    file during its parsing. This function is meant to be called with
    `.delay()` to be executed asynchronously by the Celery worker.
    """
    logger.info('Extracting METS file from ZIP [Path: %s]' % zip_path)
    with tempfile.TemporaryDirectory() as dir_:
        with zipfile.ZipFile(zip_path) as zip_:
            # Extract METS file
            metsfile = None
            mets_re = re.compile(r'.*METS.[0-9a-f\-]{36}.*$')
            for info in zip_.infolist():
                if mets_re.match(info.filename):
                    metsfile = zip_.extract(info, dir_)
            if not metsfile:
                raise Exception('METS file not found in ZIP file.')
            # Parse METS file
            path = os.path.abspath(metsfile)
            logger.info('METS file extracted [Path: %s]' % path)
            mets = METS(path, dip_id)
            mets.parse_mets()


@shared_task(
    autoretry_for=(TransportError, DatabaseError,),
    max_retries=10, default_retry_delay=30,
)
def update_es_descendants(class_name, pk):
    """
    Updates the related DigitalFiles documents in ES with the partial data from
    the ancestor Collection or DIP.
    """
    if class_name not in ['Collection', 'DIP']:
        raise Exception('Can not update descendants of %s.' % class_name)
    logger.info('Updating DigitalFiles of %s [id: %s] ' % (class_name, pk))
    if class_name == 'Collection':
        ancestor = Collection.objects.get(pk=pk)
        # Partial update with `doc` doesn't remove the fields missing in data,
        # they have to be removed via script to clear the existing value,
        # `script` and `doc` can't be combined in update actions, therefore
        # it's required to generate a Painless script to perform the update.
        script = {
            'source': """
                if (params.containsKey('identifier')) {
                  ctx._source.collection.identifier = params.identifier;
                } else {
                  ctx._source.collection.remove('identifier');
                }
                if (params.containsKey('title')) {
                  ctx._source.collection.title = params.title;
                } else {
                  ctx._source.collection.remove('title');
                }
            """,
            'lang': 'painless',
            'params': ancestor.get_es_data_for_files(),
        }
        files = DigitalFile.objects.filter(dip__collection__pk=pk).all()
    else:
        ancestor = DIP.objects.get(pk=pk)
        script = {
            'source': """
                if (params.containsKey('identifier')) {
                  ctx._source.dip.identifier = params.identifier;
                } else {
                  ctx._source.dip.remove('identifier');
                }
                if (params.containsKey('title')) {
                  ctx._source.dip.title = params.title;
                } else {
                  ctx._source.dip.remove('title');
                }
                if (params.containsKey('import_status')) {
                  ctx._source.dip.import_status = params.import_status;
                } else {
                  ctx._source.dip.remove('import_status');
                }
            """,
            'lang': 'painless',
            'params': ancestor.get_es_data_for_files(),
        }
        files = DigitalFile.objects.filter(dip__pk=pk).all()
    # Get connection to ES
    es = connections.get_connection()
    # Bulk update with partial data
    success_count, errors = bulk(es, ({
        '_op_type': 'update',
        '_index': DigitalFile.es_doc._index._name,
        '_type': DigitalFile.es_doc._doc_type.name,
        '_id': file.pk,
        'script': script,
    } for file in files.iterator()))
    logger.info('%d/%d DigitalFiles updated.' % (success_count, files.count()))
    if len(errors) > 0:
        logger.info('The following errors were encountered:')
        for error in errors:
            logger.info('- %s' % error)


@shared_task(
    autoretry_for=(TransportError,),
    max_retries=10, default_retry_delay=30,
)
def delete_es_descendants(class_name, pk):
    """Deletes the related documents in ES based on the ancestor id."""
    if class_name not in ['Collection', 'DIP']:
        raise Exception('Can not delete descendants of %s.' % class_name)
    logger.info('Deleting descendants of %s [id: %s] ' % (class_name, pk))
    if class_name == 'Collection':
        # DIPs and DigitalFiles use the same field to store the Collection id
        # so we can perform a single delete_by_query request over both indexes.
        indexes = '%s,%s' % (
            DIP.es_doc._index._name, DigitalFile.es_doc._index._name)
        body = {'query': {'match': {'collection.id': pk}}}
    else:
        indexes = DigitalFile.es_doc._index._name
        body = {'query': {'match': {'dip.id': pk}}}
    es = connections.get_connection()
    response = es.delete_by_query(index=indexes, body=body)
    logger.info('%d/%d descendants deleted.' % (
        response['deleted'], response['total']))
    if response['failures'] and len(response['failures']) > 0:
        logger.info('The following errors were encountered:')
        for error in response['failures']:
            logger.info('- %s' % error)
