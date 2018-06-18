from django.test import TestCase
from unittest.mock import patch

from dips.models import Collection, DIP, DigitalFile


class ModelsToDocsTests(TestCase):
    fixtures = ['models_to_docs']

    def test_collection(self):
        # Test data transformation
        collection = Collection.objects.get(identifier='123')
        doc_dict = {
            '_id': '123',
            'identifier': '123',
            'title': 'Example collection',
            'date': 'Example date',
            'description': 'Example description',
        }
        self.assertEqual(doc_dict, collection.get_es_data())

        # Verify DocType creation, avoid already tested transformation
        with patch.object(Collection, 'get_es_data', return_value=doc_dict):
            doc = collection.to_es_doc()
            self.assertEqual(collection.identifier, doc.meta.id)
            self.assertEqual(
                repr(doc),
                "CollectionDoc(index='accesspoc_collections', id='123')"
            )

    def test_dip(self):
        # Test data transformation
        dip = DIP.objects.get(identifier='ABC')
        doc_dict = {
            '_id': 'ABC',
            'identifier': 'ABC',
            'title': 'Example DIP',
            'date': 'Example date',
            'description': 'Example description',
            'ispartof': {
                'identifier': '123',
                'title': 'Example collection',
            }
        }
        self.assertEqual(doc_dict, dip.get_es_data())

        # Verify DocType creation, avoid already tested transformation
        with patch.object(DIP, 'get_es_data', return_value=doc_dict):
            doc = dip.to_es_doc()
            self.assertEqual(dip.identifier, doc.meta.id)
            self.assertEqual(
                repr(doc),
                "DIPDoc(index='accesspoc_dips', id='ABC')"
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
                'identifier': 'ABC',
                'title': 'Example DIP',
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
