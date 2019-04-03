from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from django_celery_results.models import TaskResult
from unittest.mock import patch

from dips.models import DIP


class ImportFailureDisplayTests(TestCase):
    fixtures = ["index_data"]

    def setUp(self):
        User = get_user_model()
        User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.client.login(username="admin", password="admin")
        TaskResult.objects.create(
            task_id="task_id", status="FAILURE", traceback="fake_trace"
        )
        dip = DIP.objects.get(pk=1)
        dip.import_status = DIP.IMPORT_FAILURE
        dip.import_task_id = "task_id"
        dip.save(update_es=False)
        dip = DIP.objects.get(pk=2)
        dip.import_status = DIP.IMPORT_FAILURE
        dip.import_task_id = "non_existing_task_id"
        dip.save(update_es=False)

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", return_value=0)
    def test_dip_view_error_message_with_trace(self, mock_es_count, mock_es_exec):
        url = reverse("dip", kwargs={"pk": 1})
        response = self.client.get(url)
        self.assertContains(response, '<div class="alert alert-danger')
        self.assertContains(response, "<p><pre>fake_trace</pre></p>")

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", return_value=0)
    def test_dip_view_error_message_without_trace(self, mock_es_count, mock_es_exec):
        url = reverse("dip", kwargs={"pk": 2})
        response = self.client.get(url)
        self.assertContains(response, '<div class="alert alert-danger')
        self.assertContains(response, "A related task result could not be found.")

    def test_digital_file_view_error_message_with_trace(self):
        url = reverse(
            "digital_file", kwargs={"pk": "07263cdf-d11f-4d24-9e16-ef46f002d037"}
        )
        response = self.client.get(url)
        self.assertContains(response, '<div class="alert alert-danger')
        self.assertContains(response, "<p><pre>fake_trace</pre></p>")

    def test_digital_file_view_error_message_without_trace(self):
        url = reverse(
            "digital_file", kwargs={"pk": "070b9cd9-a502-49c9-8b79-22abec1efd7e"}
        )
        response = self.client.get(url)
        self.assertContains(response, '<div class="alert alert-danger')
        self.assertContains(response, "A related task result could not be found.")
