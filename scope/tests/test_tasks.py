import os
from unittest.mock import ANY
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import requests
import vcr
from django.conf import settings
from django.test import TestCase
from django.test import override_settings

from scope.models import DIP
from scope.models import DigitalFile
from scope.tasks import download_mets
from scope.tasks import extract_mets
from scope.tasks import parse_mets
from scope.tasks import save_import_error


class TasksTests(TestCase):
    @patch("elasticsearch_dsl.Document.save")
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
        "scope/tests/fixtures/vcr_cassettes/download_mets_unauthorized.yaml"
    )
    def test_download_mets_unauthorized(self):
        with self.assertRaises(requests.exceptions.HTTPError):
            download_mets(self.dip.pk)

    @override_settings(
        SS_HOSTS={"http://192.168.1.128:62081": {"user": "test", "secret": "test"}}
    )
    @vcr.use_cassette("scope/tests/fixtures/vcr_cassettes/download_mets_not_found.yaml")
    def test_download_mets_not_found(self):
        with self.assertRaises(requests.exceptions.HTTPError):
            download_mets(self.dip.pk)

    @override_settings(
        SS_HOSTS={"http://192.168.1.128:62081": {"user": "test", "secret": "test"}}
    )
    @vcr.use_cassette("scope/tests/fixtures/vcr_cassettes/download_mets_success.yaml")
    @patch("elasticsearch_dsl.Document.save")
    def test_download_mets_success(self, mock_es_save):
        self.assertEqual(self.mets_path, download_mets(self.dip.pk))
        self.assertTrue(os.path.isfile(self.mets_path))
        os.remove(self.mets_path)

    @patch("scope.tasks.zipfile.is_zipfile", return_value=False)
    @patch("scope.tasks.tarfile.is_tarfile", return_value=False)
    def test_extract_mets_wrong_dip_format(self, mock_is_tarfile, mock_is_zipfile):
        with self.assertRaises(ValueError) as exc:
            extract_mets("/DIP.7z")
            self.assertEqual(str(exc), "DIP is not a tar or a zip file: DIP.7z")

    @patch("scope.tasks.tarfile.open", return_value=MagicMock())
    @patch("scope.tasks.tarfile.is_tarfile", return_value=True)
    def test_extract_mets_not_found_in_tar(self, mock_is_tarfile, mock_tarfile_open):
        mock_tarfile_open.__enter__.return_value = None
        with self.assertRaises(FileNotFoundError) as exc:
            extract_mets("/DIP.tar")
            self.assertEqual(str(exc), "METS file not found in DIP file.")

    @patch("scope.tasks.zipfile.ZipFile.infolist", return_value=[])
    @patch("scope.tasks.zipfile.ZipFile.__init__", return_value=None)
    @patch("scope.tasks.zipfile.is_zipfile", return_value=True)
    def test_extract_mets_not_found_in_zip(
        self, mock_is_zipfile, mock_zip_init, mock_zip_info
    ):
        with self.assertRaises(FileNotFoundError) as exc:
            extract_mets("/DIP.zip")
            self.assertEqual(str(exc), "METS file not found in DIP file.")

    @patch("scope.tasks.tarfile.open", return_value=MagicMock())
    @patch("scope.tasks.tarfile.is_tarfile", return_value=True)
    def test_extract_mets_found_in_tar(self, mock_is_tarfile, mock_tarfile_open):
        mock_member = Mock()
        mock_member.name = "relative/path/METS.ab028cb0-9942-4f26-a966-7197d7a2e15a.xml"
        mock_tarfile = Mock()
        mock_tarfile.getmembers.return_value = [mock_member]
        mock_tarfile_open().__enter__.return_value = mock_tarfile
        mets_path = extract_mets("/DIP.tar")
        self.assertEqual(
            os.path.join(
                settings.MEDIA_ROOT, "METS.ab028cb0-9942-4f26-a966-7197d7a2e15a.xml"
            ),
            mets_path,
        )

    @patch("scope.tasks.os.path.basename")
    @patch("scope.tasks.zipfile.ZipFile.extract", return_value="/mets.xml")
    @patch(
        "scope.tasks.zipfile.ZipFile.infolist",
        return_value=[
            Mock(filename="relative/path/METS.ab028cb0-9942-4f26-a966-7197d7a2e15a.xml")
        ],
    )
    @patch("scope.tasks.zipfile.ZipFile.__init__", return_value=None)
    @patch("scope.tasks.zipfile.is_zipfile", return_value=True)
    @patch("scope.tasks.tarfile.is_tarfile", return_value=False)
    def test_extract_mets_found_in_zip(
        self,
        mock_is_tarfile,
        mock_is_zipfile,
        mock_zip_init,
        mock_zip_info,
        mock_zip_extract,
        mock_os_basename,
    ):
        mets_path = extract_mets("/DIP.zip")
        mock_os_basename.assert_called_with(
            "relative/path/METS.ab028cb0-9942-4f26-a966-7197d7a2e15a.xml"
        )
        mock_zip_extract.assert_called_with(ANY, settings.MEDIA_ROOT)
        self.assertEqual("/mets.xml", mets_path)

    @patch("scope.models.celery_app.send_task")
    @patch("scope.tasks.os.remove")
    @patch("elasticsearch_dsl.Document.save")
    @patch("scope.tasks.METS")
    def test_parse_mets(self, mock_mets, mock_es_save, mock_os_remove, mock_send_task):
        mock_mets().return_value = None
        mock_mets().parse_mets.return_value = self.dip
        parse_mets("/mets.xml", self.dip.pk)
        self.assertEqual(self.dip.import_status, DIP.IMPORT_SUCCESS)
        mock_send_task.assert_called()
        mock_os_remove.assert_called_with("/mets.xml")

    @patch("scope.models.celery_app.send_task")
    @patch("elasticsearch_dsl.Document.save")
    def test_save_import_error(self, mock_es_save, mock_send_task):
        save_import_error({}, "Error message", "Error trace", self.dip.pk)
        self.dip.refresh_from_db()
        self.assertEqual(self.dip.import_status, DIP.IMPORT_FAILURE)
        self.assertEqual(self.dip.import_error, "Error message")
        mock_send_task.assert_called()
