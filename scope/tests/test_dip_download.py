from contextlib import contextmanager
import os

from django.conf import settings
from django.urls import reverse
from django.test import TestCase, override_settings
from unittest.mock import patch
import vcr

from scope.models import DIP, DublinCore, User


@contextmanager
def _sized_tmp_file(path, size):
    """Manage sized temporary file.

    Context manager that creates a file (raising FileExistsError if it exists)
    in a given path and with a given size, yields it and deletes it at the end.
    """
    file_ = open(path, "xb")
    try:
        file_.seek(size - 1)
        file_.write(b"0")
        file_.close()
        yield file_
    finally:
        os.remove(path)


class DipDownloadTests(TestCase):
    @patch("elasticsearch_dsl.DocType.save")
    def setUp(self, mock_es_save):
        User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.client.login(username="admin", password="admin")
        self.local_dip = DIP.objects.create(
            dc=DublinCore.objects.create(identifier="A"), objectszip="fake.zip"
        )
        ss_uuid = "041576bb-befb-4206-a4fb-f62b547c71ef"
        ss_host_url = "http://192.168.1.128:62081"
        self.ss_dip = DIP.objects.create(
            ss_uuid=ss_uuid,
            ss_dir_name="20190501122906-ac51028e-9be6-4f99-af77-e1ca6f02d6c9",
            ss_host_url="http://192.168.1.128:62081",
            ss_download_url="%s/api/v2/file/%s/download/" % (ss_host_url, ss_uuid),
            dc=DublinCore.objects.create(identifier=ss_uuid),
        )

    def test_dip_download_not_found(self):
        url = reverse("download_dip", kwargs={"pk": 999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_local_dip_download_zip_not_found(self):
        url = reverse("download_dip", kwargs={"pk": self.local_dip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @patch("scope.views.zipfile.is_zipfile", return_value=True)
    def test_local_dip_download_zip_headers(self, mock_is_zipfile):
        # Make sure the MEDIA_ROOT directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        # Create temporay sized ZIP file for request
        path = os.path.join(settings.MEDIA_ROOT, "fake.zip")
        size = 1048575
        with _sized_tmp_file(path, size):
            url = reverse("download_dip", kwargs={"pk": self.local_dip.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Length"], str(size))
            self.assertEqual(response["Content-Type"], "application/zip")
            self.assertEqual(
                response["Content-Disposition"], 'attachment; filename="fake.zip"'
            )
            self.assertEqual(response["X-Accel-Redirect"], "/media/fake.zip")

    @patch("elasticsearch_dsl.DocType.save")
    @patch("scope.views.zipfile.is_zipfile", return_value=False)
    def test_local_dip_download_tar_headers(self, mock_is_zipfile, mock_es_save):
        self.local_dip.objectszip = "fake.tar"
        self.local_dip.save()
        # Make sure the MEDIA_ROOT directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        # Create temporay sized ZIP file for request
        path = os.path.join(settings.MEDIA_ROOT, "fake.tar")
        size = 1048575
        with _sized_tmp_file(path, size):
            url = reverse("download_dip", kwargs={"pk": self.local_dip.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Length"], str(size))
            self.assertEqual(response["Content-Type"], "application/x-tar")
            self.assertEqual(
                response["Content-Disposition"], 'attachment; filename="fake.tar"'
            )
            self.assertEqual(response["X-Accel-Redirect"], "/media/fake.tar")

    def test_ss_dip_download_no_host(self):
        self.ss_dip.ss_host_url = "http://unknown.host"
        self.ss_dip.save(update_es=False)
        with self.assertRaises(RuntimeError):
            url = reverse("download_dip", kwargs={"pk": self.ss_dip.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 500)

    @override_settings(
        SS_HOSTS={"http://192.168.1.128:62081": {"user": "foo", "secret": "bar"}}
    )
    @vcr.use_cassette(
        "scope/tests/fixtures/vcr_cassettes/ss_dip_download_unauthorized.yaml"
    )
    def test_ss_dip_download_unauthorized(self):
        url = reverse("download_dip", kwargs={"pk": self.ss_dip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @override_settings(
        SS_HOSTS={"http://192.168.1.128:62081": {"user": "test", "secret": "test"}}
    )
    @vcr.use_cassette(
        "scope/tests/fixtures/vcr_cassettes/ss_dip_download_not_found.yaml"
    )
    def test_ss_dip_download_not_found(self):
        self.ss_dip.ss_download_url = (
            "%s/api/v2/file/fake_uuid/download/" % self.ss_dip.ss_host_url
        )
        self.ss_dip.save(update_es=False)
        url = reverse("download_dip", kwargs={"pk": self.ss_dip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @override_settings(
        SS_HOSTS={"http://192.168.1.128:62081": {"user": "test", "secret": "test"}}
    )
    @vcr.use_cassette("scope/tests/fixtures/vcr_cassettes/ss_dip_download_success.yaml")
    def test_ss_dip_download_success(self):
        url = reverse("download_dip", kwargs={"pk": self.ss_dip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Length"])
        self.assertEqual(response["Content-Type"], "application/x-tar")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="%s.tar"' % self.ss_dip.ss_dir_name,
        )
