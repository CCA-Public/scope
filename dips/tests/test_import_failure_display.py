from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from unittest.mock import patch

from dips.models import DIP, DigitalFile


class ImportFailureDisplayTests(TestCase):
    @patch("elasticsearch_dsl.DocType.save")
    def setUp(self, mock_es_save):
        User = get_user_model()
        User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.client.login(username="admin", password="admin")
        self.dip = DIP.objects.create(
            import_status=DIP.IMPORT_FAILURE, import_error="fake_error"
        )
        self.file = DigitalFile.objects.create(
            uuid="fake-uuid", dip=self.dip, size_bytes=1
        )

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", return_value=0)
    def test_error_message_display(self, mock_es_count, mock_es_exec):
        for url in [
            reverse("dip", kwargs={"pk": self.dip.pk}),
            reverse("digital_file", kwargs={"pk": self.file.pk}),
        ]:
            response = self.client.get(url)
            self.assertContains(response, '<div class="alert alert-danger')
            self.assertContains(response, "<p><pre>fake_error</pre></p>")
