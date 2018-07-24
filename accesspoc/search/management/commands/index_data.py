from django.conf import settings
from django.core.management.base import BaseCommand
from elasticsearch.helpers import streaming_bulk
from elasticsearch_dsl import analyzer, Index
from elasticsearch_dsl.connections import connections
from tqdm import tqdm

from dips.models import Collection, DIP, DigitalFile

# Tuples with display name and models to index in ES.
MODELS = [
    ('collections', Collection),
    ('folders', DIP),
    ('digital files', DigitalFile),
]


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        es = connections.get_connection()
        for name, model in MODELS:
            print('Processing %s:' % name)
            document = model.es_doc
            index_name = document._doc_type.index
            index = Index(index_name)
            index.settings(**settings.ES_INDEXES_SETTINGS)
            # Use English analizer by default, other analyzers may be
            # defined in the documents declaration for specific fields.
            index.analyzer(analyzer('default', 'english'))
            index.doc_type(document)
            print(' - Deleting index.')
            index.delete(ignore=404)
            print(' - Creating index.')
            index.create()
            total = model.objects.count()
            if total == 0:
                print(' - No %s to index.' % name)
                continue
            progress_bar = tqdm(
                total=total,
                bar_format=' - Indexing: {n_fmt}/{total_fmt} [{elapsed} < {remaining}]',
                ncols=1,  # required to show the custom bar_format
            )
            for _ in streaming_bulk(
                es,
                (obj.get_es_data() for obj in model.objects.all().iterator()),
                index=index_name,
                doc_type=document._doc_type.name,
            ):
                progress_bar.update(1)
            progress_bar.close()
