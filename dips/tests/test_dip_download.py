from contextlib import contextmanager
from django.conf import settings
from django.urls import reverse
from django.test import TestCase
from unittest.mock import patch

from dips.models import Collection, DIP, DublinCore, User

import os


@contextmanager
def _sized_tmp_file(path, size):
    """
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
        self.collection = Collection.objects.create(
            dc=DublinCore.objects.create(identifier="1")
        )
        self.dip = DIP.objects.create(
            dc=DublinCore.objects.create(identifier="A"),
            collection=self.collection,
            objectszip="fake.zip",
        )

    def test_dip_download_zip_not_found(self):
        url = reverse("download_dip", kwargs={"pk": self.dip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_dip_download_headers(self):
        # Make sure the MEDIA_ROOT directory exists
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        # Create temporay sized ZIP file for request
        path = os.path.join(settings.MEDIA_ROOT, "fake.zip")
        size = 1048575
        with _sized_tmp_file(path, size):
            url = reverse("download_dip", kwargs={"pk": self.dip.pk})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Length"], str(size))
            self.assertEqual(response["Content-Type"], "application/zip")
            self.assertEqual(
                response["Content-Disposition"], "attachment; filename=fake.zip"
            )
            self.assertEqual(response["X-Accel-Redirect"], "/media/fake.zip")
