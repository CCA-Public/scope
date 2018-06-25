from django.test import TestCase
from unittest.mock import patch

from dips.models import Collection, DIP, DigitalFile


class ModelsToDocsTests(TestCase):
    fixtures = ['models_to_docs']

    def test_collection(self):
        # Test data transformation
        collection = Collection.objects.get(pk=1)
        doc_dict = {
            '_id': 1,
            'dc': {
                'identifier': '123',
                'title': 'Example collection',
                'date': 'Example date',
                'description': 'Example description',
            },
        }
        self.assertEqual(doc_dict, collection.get_es_data())

        # Verify DocType creation, avoid already tested transformation
        with patch.object(Collection, 'get_es_data', return_value=doc_dict):
            doc = collection.to_es_doc()
            self.assertEqual(collection.pk, doc.meta.id)
            self.assertEqual(
                repr(doc),
                "CollectionDoc(index='accesspoc_collections', id=1)"
            )

    def test_dip(self):
        # Test data transformation
        dip = DIP.objects.get(pk=1)
        doc_dict = {
            '_id': 1,
            'dc': {
                'identifier': 'ABC',
                'title': 'Example DIP',
                'date': 'Example date',
                'description': 'Example description',
            },
            'collection': {
                'id': 1,
                'identifier': '123',
            }
        }
        self.assertEqual(doc_dict, dip.get_es_data())

        # Verify DocType creation, avoid already tested transformation
        with patch.object(DIP, 'get_es_data', return_value=doc_dict):
            doc = dip.to_es_doc()
            self.assertEqual(dip.pk, doc.meta.id)
            self.assertEqual(
                repr(doc),
                "DIPDoc(index='accesspoc_dips', id=1)"
            )

    def test_digital_file(self):
        # Test data transformation
        digital_file = DigitalFile.objects.get(
            uuid='07263cdf-d11f-4d24-9e16-ef46f002d037'
        )
        doc_dict = {
            '_id': '07263cdf-d11f-4d24-9e16-ef46f002d037',
            'uuid': '07263cdf-d11f-4d24-9e16-ef46f002d037',
            'filepath': 'objects/example.ai',
            'fileformat': 'Adobe Illustrator',
            'size_bytes': 1080282,
            'datemodified': '2018-02-08T20:00:57',
            'dip': {
                'id': 1,
                'identifier': 'ABC',
            }
        }
        self.assertEqual(doc_dict, digital_file.get_es_data())

        # Verify DocType creation, avoid already tested transformation
        with patch.object(DigitalFile, 'get_es_data', return_value=doc_dict):
            doc = digital_file.to_es_doc()
            self.assertEqual(digital_file.uuid, doc.meta.id)
            self.assertEqual(
                repr(doc),
                "DigitalFileDoc(index='accesspoc_digital_files', "
                "id='07263cdf-d11f-4d24-9e16-ef46f002d037')"
            )
