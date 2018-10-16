from django.test import TestCase
from unittest.mock import patch

from dips.models import Collection, DIP, DigitalFile, DublinCore
from search.documents import CollectionDoc, DIPDoc, DigitalFileDoc


class SignalHandlerTests(TestCase):
    @patch('elasticsearch_dsl.DocType.save')
    def setUp(self, patch):
        # Create resources
        dc = DublinCore.objects.create(identifier='1')
        self.collection = Collection.objects.create(dc=dc)
        dc = DublinCore.objects.create(identifier='A')
        self.dip = DIP.objects.create(
            dc=dc,
            collection=self.collection,
            objectszip='/path/to/fake.zip',
        )
        self.digital_file = DigitalFile.objects.create(
            uuid='fake-uuid',
            dip=self.dip,
            size_bytes=1
        )

    @patch.object(CollectionDoc, 'save')
    def test_collection_post_save(self, mock):
        dc = DublinCore.objects.create(identifier='2')
        Collection.objects.create(dc=dc)
        mock.assert_called()

    @patch.object(DIPDoc, 'save')
    def test_dip_post_save(self, mock):
        dc = DublinCore.objects.create(identifier='B')
        DIP.objects.create(
            dc=dc,
            collection=self.collection,
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
            index=DigitalFile.es_doc._index._name,
            doc_type=DigitalFile.es_doc._doc_type.name,
            id=uuid,
        )

    @patch('dips.models.delete_document')
    def test_dip_pre_delete(self, mock):
        pk = self.dip.pk
        self.dip.delete()
        mock.assert_called_with(
            index=DIP.es_doc._index._name,
            doc_type=DIP.es_doc._doc_type.name,
            id=pk,
        )

    @patch('dips.models.delete_document')
    def test_collection_pre_delete(self, mock):
        pk = self.collection.pk
        self.collection.delete()
        mock.assert_called_with(
            index=Collection.es_doc._index._name,
            doc_type=Collection.es_doc._doc_type.name,
            id=pk,
        )
