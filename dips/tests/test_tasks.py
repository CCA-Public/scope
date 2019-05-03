import os

from django.conf import settings
from django.test import TestCase, override_settings
import requests
from unittest.mock import patch, Mock
import vcr

from dips.models import DIP, DigitalFile
from dips.tasks import download_mets, extract_mets, parse_mets, save_import_error


class TasksTests(TestCase):
    @patch("elasticsearch_dsl.DocType.save")
    def setUp(self, mock_es_save):
        self.ss_uuid = "a2cddc10-6132-4690-8dd9-25ee7a01943f"
        self.mets_path = os.path.join(settings.MEDIA_ROOT, "METS.%s.xml" % self.ss_uuid)
        self.dip = DIP.objects.create(
            ss_uuid=self.ss_uuid, ss_host_url="http://192.168.1.128:62081"
        )
        DigitalFile.objects.create(uuid="fake-uuid", dip=self.dip, size_bytes=1)

    def test_download_mets_no_host(self):
        self.dip.ss_host_url = "http://unknown.host"
        self.dip.save(update_es=False)
        with self.assertRaises(RuntimeError):
            download_mets(self.dip.pk)

    @override_settings(
        SS_HOSTS={"http://192.168.1.128:62081": {"user": "foo", "secret": "bar"}}
    )
    @vcr.use_cassette(
        "dips/tests/fixtures/vcr_cassettes/download_mets_unauthorized.yaml"
    )
    def test_download_mets_unauthorized(self):
        with self.assertRaises(requests.exceptions.HTTPError):
            download_mets(self.dip.pk)

    @override_settings(
        SS_HOSTS={"http://192.168.1.128:62081": {"user": "test", "secret": "test"}}
    )
    @vcr.use_cassette("dips/tests/fixtures/vcr_cassettes/download_mets_not_found.yaml")
    def test_download_mets_not_found(self):
        with self.assertRaises(requests.exceptions.HTTPError):
            download_mets(self.dip.pk)

    @override_settings(
        SS_HOSTS={"http://192.168.1.128:62081": {"user": "test", "secret": "test"}}
    )
    @vcr.use_cassette("dips/tests/fixtures/vcr_cassettes/download_mets_success.yaml")
    @patch("elasticsearch_dsl.DocType.save")
    def test_download_mets_success(self, mock_es_save):
        self.assertEqual(self.mets_path, download_mets(self.dip.pk))
        self.assertTrue(os.path.isfile(self.mets_path))
        os.remove(self.mets_path)

    @patch("dips.tasks.os.remove")
    @patch("dips.tasks.zipfile.ZipFile.infolist", return_value=[])
    @patch("dips.tasks.zipfile.ZipFile.__init__", return_value=None)
    def test_extract_mets_not_found(self, mock_zip_init, mock_zip_info, mock_os_remove):
        with self.assertRaises(FileNotFoundError):
            extract_mets("/DIP.zip")
        mock_os_remove.assert_called_with("/DIP.zip")

    @patch("dips.tasks.os.remove")
    @patch("dips.tasks.zipfile.ZipFile.extract", return_value="/mets.xml")
    @patch(
        "dips.tasks.zipfile.ZipFile.infolist",
        return_value=[Mock(filename="METS.ab028cb0-9942-4f26-a966-7197d7a2e15a.xml")],
    )
    @patch("dips.tasks.zipfile.ZipFile.__init__", return_value=None)
    def test_extract_mets_found(
        self, mock_zip_init, mock_zip_info, mock_zip_extract, mock_os_remove
    ):
        mets_path = extract_mets("/DIP.zip", delete_zip=True)
        self.assertEqual("/mets.xml", mets_path)
        mock_os_remove.assert_called_with("/DIP.zip")

    @patch("dips.models.celery_app.send_task")
    @patch("dips.tasks.os.remove")
    @patch("elasticsearch_dsl.DocType.save")
    @patch("dips.tasks.METS")
    def test_parse_mets(self, mock_mets, mock_es_save, mock_os_remove, mock_send_task):
        mock_mets().return_value = None
        mock_mets().parse_mets.return_value = self.dip
        parse_mets("/mets.xml", self.dip.pk)
        self.assertEqual(self.dip.import_status, DIP.IMPORT_SUCCESS)
        mock_send_task.assert_called()
        mock_os_remove.assert_called_with("/mets.xml")

    @patch("dips.models.celery_app.send_task")
    @patch("elasticsearch_dsl.DocType.save")
    def test_save_import_error(self, mock_es_save, mock_send_task):
        save_import_error({}, "Error message", "Error trace", self.dip.pk)
        self.dip.refresh_from_db()
        self.assertEqual(self.dip.import_status, DIP.IMPORT_FAILURE)
        self.assertEqual(self.dip.import_error, "Error message")
        mock_send_task.assert_called()
