from django.test import TestCase
from unittest.mock import patch

from dips.models import Collection, DIP, DigitalFile
from search.documents import CollectionDoc, DIPDoc, DigitalFileDoc


class SignalHandlerTests(TestCase):
    @patch('elasticsearch_dsl.DocType.save')
    def setUp(self, patch):
        # Create resources
        self.collection = Collection.objects.create(identifier='1')
        self.dip = DIP.objects.create(
            identifier='A',
            ispartof=self.collection,
            objectszip='/path/to/fake.zip',
        )
        self.digital_file = DigitalFile.objects.create(
            uuid='fake-uuid',
            dip=self.dip,
            size_bytes=1
        )

    @patch.object(CollectionDoc, 'save')
    def test_collection_post_save(self, mock):
        Collection.objects.create(identifier='2')
        mock.assert_called()

    @patch.object(DIPDoc, 'save')
    def test_dip_post_save(self, mock):
        DIP.objects.create(
            identifier='B',
            ispartof=self.collection,
            objectszip='/path/to/fake.zip',
        )
        mock.assert_called()

    @patch.object(DigitalFileDoc, 'save')
    def test_digital_file_post_save(self, mock):
        DigitalFile.objects.create(
            uuid='fake-uuid-2',
            dip=self.dip,
            size_bytes=1
        )
        mock.assert_called()

    @patch('dips.models.delete_document')
    def test_digital_file_pre_delete(self, mock):
        uuid = self.digital_file.uuid
        self.digital_file.delete()
        mock.assert_called_with(
            index=DigitalFile.es_doc._doc_type.index,
            doc_type=DigitalFile.es_doc._doc_type.name,
            id=uuid,
        )

    @patch('dips.models.delete_document')
    def test_dip_pre_delete(self, mock):
        identifier = self.dip.identifier
        self.dip.delete()
        mock.assert_called_with(
            index=DIP.es_doc._doc_type.index,
            doc_type=DIP.es_doc._doc_type.name,
            id=identifier,
        )

    @patch('dips.models.delete_document')
    def test_collection_pre_delete(self, mock):
        identifier = self.collection.identifier
        self.collection.delete()
        mock.assert_called_with(
            index=Collection.es_doc._doc_type.index,
            doc_type=Collection.es_doc._doc_type.name,
            id=identifier,
        )
