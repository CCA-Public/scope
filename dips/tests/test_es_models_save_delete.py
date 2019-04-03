from django.test import TestCase
from unittest.mock import patch

from dips.models import Collection, DIP, DigitalFile, DublinCore
from search.documents import CollectionDoc, DIPDoc, DigitalFileDoc


class EsModelsSaveDeleteTests(TestCase):
    @patch("elasticsearch_dsl.DocType.save")
    def setUp(self, mock_es_save):
        dc = DublinCore.objects.create(identifier="1")
        self.collection = Collection.objects.create(dc=dc)
        dc = DublinCore.objects.create(identifier="A")
        self.dip = DIP.objects.create(
            dc=dc, collection=self.collection, objectszip="/path/to/fake.zip"
        )
        self.digital_file = DigitalFile.objects.create(
            uuid="fake-uuid", dip=self.dip, size_bytes=1
        )

    @patch("dips.models.celery_app.send_task")
    @patch.object(CollectionDoc, "save")
    def test_collection_save(self, mock_es_save, mock_send_task):
        self.collection.save(update_es=False)
        mock_es_save.assert_not_called()
        mock_send_task.assert_not_called()
        self.collection.save()
        mock_es_save.assert_called()
        mock_send_task.assert_called_with(
            "dips.tasks.update_es_descendants", args=("Collection", 1)
        )

    @patch("dips.models.celery_app.send_task")
    @patch.object(DIPDoc, "save")
    def test_dip_save(self, mock_es_save, mock_send_task):
        self.dip.save(update_es=False)
        mock_es_save.assert_not_called()
        mock_send_task.assert_not_called()
        self.dip.save()
        mock_es_save.assert_called()
        mock_send_task.assert_called_with(
            "dips.tasks.update_es_descendants", args=("DIP", 1)
        )

    @patch("dips.models.celery_app.send_task")
    @patch.object(DigitalFileDoc, "save")
    def test_digital_file_save(self, mock_es_save, mock_send_task):
        self.digital_file.save(update_es=False)
        mock_es_save.assert_not_called()
        mock_send_task.assert_not_called()
        self.digital_file.save()
        mock_es_save.assert_called()
        mock_send_task.assert_not_called()

    @patch("dips.models.celery_app.send_task")
    @patch("dips.models.delete_document")
    def test_digital_file_delete(self, mock_es_delete, mock_send_task):
        uuid = self.digital_file.uuid
        self.digital_file.delete()
        mock_es_delete.assert_called_with(
            index=DigitalFile.es_doc._index._name,
            doc_type=DigitalFile.es_doc._doc_type.name,
            id=uuid,
        )
        mock_send_task.assert_not_called()

    @patch("dips.models.celery_app.send_task")
    @patch("dips.models.delete_document")
    def test_dip_delete(self, mock_es_delete, mock_send_task):
        pk = self.dip.pk
        self.dip.delete()
        mock_es_delete.assert_called_with(
            index=DIP.es_doc._index._name, doc_type=DIP.es_doc._doc_type.name, id=pk
        )
        mock_send_task.assert_called_with(
            "dips.tasks.delete_es_descendants", args=("DIP", 1)
        )

    @patch("dips.models.celery_app.send_task")
    @patch("dips.models.delete_document")
    def test_collection_delete(self, mock_es_delete, mock_send_task):
        pk = self.collection.pk
        self.collection.delete()
        mock_es_delete.assert_called_with(
            index=Collection.es_doc._index._name,
            doc_type=Collection.es_doc._doc_type.name,
            id=pk,
        )
        mock_send_task.assert_called_with(
            "dips.tasks.delete_es_descendants", args=("Collection", 1)
        )
