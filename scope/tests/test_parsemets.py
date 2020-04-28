from unittest.mock import patch

from django.forms.models import model_to_dict
from django.test import TestCase

from scope.models import DIP
from scope.models import Collection
from scope.models import DigitalFile
from scope.models import DublinCore
from scope.models import PREMISEvent
from scope.parsemets import METS
from scope.parsemets import METSError


class ParsemetsTests(TestCase):
    @patch("elasticsearch_dsl.DocType.save")
    def setUp(self, mock_es_save):
        self.dc = DublinCore.objects.create(identifier="A")
        self.dip = DIP.objects.create(dc=self.dc)

    @patch("elasticsearch_dsl.DocType.save")
    def test_only_original_files(self, mock_es_save):
        mets = METS("scope/tests/fixtures/mets/full.xml", self.dip.pk)
        mets.parse_mets()
        self.assertEqual(DigitalFile.objects.all().count(), 2)
        self.assertEqual(PREMISEvent.objects.all().count(), 13)

    @patch("elasticsearch_dsl.DocType.save")
    def test_no_metadata(self, mock_es_save):
        mets = METS("scope/tests/fixtures/mets/basic.xml", self.dip.pk)
        dip = mets.parse_mets()
        self.assertEqual(dip.dc.identifier, self.dc.identifier)
        self.assertIsNone(dip.collection)
        self.assertEqual(DigitalFile.objects.all().count(), 1)
        self.assertEqual(PREMISEvent.objects.all().count(), 1)

    @patch("elasticsearch_dsl.DocType.save")
    def test_metadata(self, mock_es_save):
        mets = METS("scope/tests/fixtures/mets/metadata.xml", self.dip.pk)
        dip = mets.parse_mets()
        expected_dc = {
            "id": 1,
            "identifier": "Identifier",
            "title": "Title",
            "creator": "Creator",
            "subject": "Subject",
            "description": "Description",
            "publisher": "Publisher",
            "contributor": "Contributor",
            "date": "2019-02-02/2020-02-02",
            "type": "Archival Information Package",
            "format": "Format",
            "source": "Source",
            "language": "en",
            "coverage": "Coverage",
            "rights": "Rights",
        }
        self.assertEqual(model_to_dict(dip.dc), expected_dc)

    @patch("elasticsearch_dsl.DocType.save")
    def test_metadata_updated(self, mock_es_save):
        mets = METS("scope/tests/fixtures/mets/updated.xml", self.dip.pk)
        dip = mets.parse_mets()
        expected_dc = {
            "id": 1,
            "identifier": "Identifier updated",
            "title": "Title updated",
            "creator": "Creator updated",
            "subject": "Subject updated",
            "description": "Description updated",
            "publisher": "Publisher updated",
            "contributor": "Contributor updated",
            "date": "2019-12-02/2020-12-02",
            "type": "Archival Information Package",
            "format": "Format updated",
            "source": "Source updated",
            "language": "es",
            "coverage": "Coverage updated",
            "rights": "Rights updated",
        }
        self.assertEqual(model_to_dict(dip.dc), expected_dc)

    @patch("elasticsearch_dsl.DocType.save")
    def test_empty_identifier(self, mock_es_save):
        mets = METS("scope/tests/fixtures/mets/empty_identifier.xml", self.dip.pk)
        dip = mets.parse_mets()
        self.assertEqual(dip.dc.identifier, self.dc.identifier)

    @patch("elasticsearch_dsl.DocType.save")
    def test_no_amd_section(self, mock_es_save):
        mets = METS("scope/tests/fixtures/mets/no_amdsec.xml", self.dip.pk)
        mets.parse_mets()
        self.assertEqual(DigitalFile.objects.all().count(), 1)

    @patch("elasticsearch_dsl.DocType.save")
    def test_collection_link_ispartof(self, mock_es_save):
        collection = Collection.objects.create(
            dc=DublinCore.objects.create(identifier="123")
        )
        mets = METS("scope/tests/fixtures/mets/metadata.xml", self.dip.pk)
        dip = mets.parse_mets()
        self.assertEqual(dip.collection, collection)

    @patch("elasticsearch_dsl.DocType.save")
    def test_collection_link_relation(self, mock_es_save):
        collection = Collection.objects.create(
            dc=DublinCore.objects.create(identifier="Relation")
        )
        mets = METS("scope/tests/fixtures/mets/metadata.xml", self.dip.pk)
        dip = mets.parse_mets()
        self.assertEqual(dip.collection, collection)

    @patch("elasticsearch_dsl.DocType.save")
    def test_collection_link_multiple_collections(self, mock_es_save):
        Collection.objects.create(dc=DublinCore.objects.create(identifier="123"))
        Collection.objects.create(dc=DublinCore.objects.create(identifier="123"))
        mets = METS("scope/tests/fixtures/mets/metadata.xml", self.dip.pk)
        dip = mets.parse_mets()
        self.assertIsNone(dip.collection)

    @patch("elasticsearch_dsl.DocType.save")
    def test_malformed_mets(self, mock_es_save):
        mets_paths = [
            "scope/tests/fixtures/mets/no_file_uuid.xml",
            "scope/tests/fixtures/mets/no_file_format.xml",
            "scope/tests/fixtures/mets/no_event_uuid.xml",
            "scope/tests/fixtures/mets/long_event_date.xml",
            "scope/tests/fixtures/mets/duplicated_event.xml",
        ]
        for path in mets_paths:
            mets = METS(path, self.dip.pk)
            self.assertRaises(METSError, mets.parse_mets)

    @patch("elasticsearch_dsl.DocType.save")
    def test_duplicated_import_different_dips(self, mock_es_save):
        mets = METS("scope/tests/fixtures/mets/basic.xml", self.dip.pk)
        mets.parse_mets()
        other_dip = DIP.objects.create(dc=DublinCore.objects.create(identifier="456"))
        mets = METS("scope/tests/fixtures/mets/basic.xml", other_dip.pk)
        self.assertRaises(METSError, mets.parse_mets)

    @patch("elasticsearch_dsl.DocType.save")
    def test_event_detail(self, mock_es_save):
        """Checks even detail import in PREMIS v2 and v3."""
        mets = METS("scope/tests/fixtures/mets/event_detail.xml", self.dip.pk)
        mets.parse_mets()
        for event in PREMISEvent.objects.all():
            self.assertEqual(event.detail, "fake event detail")
