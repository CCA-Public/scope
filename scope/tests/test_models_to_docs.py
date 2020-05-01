from datetime import datetime
from datetime import timezone
from unittest.mock import patch

from django.test import TestCase

from scope.models import DIP
from scope.models import Collection
from scope.models import DigitalFile


class ModelsToDocsTests(TestCase):
    fixtures = ["models_to_docs"]

    def test_collection(self):
        # Test data transformation
        collection = Collection.objects.get(pk=1)
        doc_dict = {
            "_id": 1,
            "dc": {
                "identifier": "123",
                "title": "Example collection",
                "date": "Example date",
                "description": "Example description",
            },
        }
        self.assertEqual(doc_dict, collection.get_es_data())

        # Verify Document creation, avoid already tested transformation
        with patch.object(Collection, "get_es_data", return_value=doc_dict):
            doc = collection.to_es_doc()
            self.assertEqual(collection.pk, doc.meta.id)
            self.assertEqual(repr(doc), "CollectionDoc(id=1)")

    def test_dip(self):
        # Test data transformation
        dip = DIP.objects.get(pk=1)
        doc_dict = {
            "_id": 1,
            "import_status": DIP.IMPORT_SUCCESS,
            "dc": {
                "identifier": "ABC",
                "title": "Example DIP",
                "date": "Example date",
                "description": "Example description",
            },
            "collection": {"id": 1},
        }
        self.assertEqual(doc_dict, dip.get_es_data())

        # Verify Document creation, avoid already tested transformation
        with patch.object(DIP, "get_es_data", return_value=doc_dict):
            doc = dip.to_es_doc()
            self.assertEqual(dip.pk, doc.meta.id)
            self.assertEqual(repr(doc), "DIPDoc(id=1)")

    def test_digital_file(self):
        # Test data transformation
        digital_file = DigitalFile.objects.get(
            uuid="07263cdf-d11f-4d24-9e16-ef46f002d037"
        )
        doc_dict = {
            "_id": "07263cdf-d11f-4d24-9e16-ef46f002d037",
            "uuid": "07263cdf-d11f-4d24-9e16-ef46f002d037",
            "filepath": "objects/example.ai",
            "fileformat": "Adobe Illustrator",
            "size_bytes": 1080282,
            "datemodified": datetime(2018, 2, 8, 20, 0, 57, tzinfo=timezone.utc),
            "dip": {
                "id": 1,
                "identifier": "ABC",
                "title": "Example DIP",
                "import_status": "SUCCESS",
            },
            "collection": {"id": 1, "identifier": "123", "title": "Example collection"},
        }
        self.assertEqual(doc_dict, digital_file.get_es_data())

        # Verify Document creation, avoid already tested transformation
        with patch.object(DigitalFile, "get_es_data", return_value=doc_dict):
            doc = digital_file.to_es_doc()
            self.assertEqual(digital_file.uuid, doc.meta.id)
            self.assertEqual(
                repr(doc), "DigitalFileDoc(id='07263cdf-d11f-4d24-9e16-ef46f002d037')"
            )
