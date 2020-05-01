from unittest.mock import patch

from django.test import TestCase

from scope.models import DIP
from scope.models import Collection
from scope.models import DublinCore


class DcDeletionTests(TestCase):
    @patch("elasticsearch_dsl.Document.save")
    def setUp(self, mock_es_save):
        dc = DublinCore.objects.create(identifier="1")
        self.collection = Collection.objects.create(dc=dc)
        dc = DublinCore.objects.create(identifier="A")
        self.dip = DIP.objects.create(
            dc=dc, collection=self.collection, objectszip="/path/to/fake.zip"
        )

    @patch("elasticsearch.client.Elasticsearch.delete")
    @patch("scope.models.celery_app.send_task")
    def test_dip_deletion(self, mock_send_task, mock_es_delete):
        dc_count = DublinCore.objects.filter(identifier="A").count()
        self.assertEqual(dc_count, 1)
        self.dip.delete()
        dc_count = DublinCore.objects.filter(identifier="A").count()
        self.assertEqual(dc_count, 0)

    @patch("elasticsearch.client.Elasticsearch.delete")
    @patch("scope.models.celery_app.send_task")
    def test_collection_deletion(self, mock_send_task, mock_es_delete):
        dc_count = DublinCore.objects.all().count()
        self.assertEqual(dc_count, 2)
        self.collection.delete()
        # It should also delete the DIP DublinCore
        dc_count = DublinCore.objects.all().count()
        self.assertEqual(dc_count, 0)
