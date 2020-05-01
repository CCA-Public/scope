from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from scope.models import DIP
from scope.models import Collection
from scope.models import DublinCore


class DcByDcFormTests(TestCase):
    @patch("elasticsearch_dsl.Document.save")
    def setUp(self, mock_es_save):
        User = get_user_model()
        User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.client.login(username="admin", password="admin")
        dc = DublinCore.objects.create(identifier="1")
        self.collection = Collection.objects.create(dc=dc)
        dc = DublinCore.objects.create(identifier="A")
        self.dip = DIP.objects.create(
            dc=dc, collection=self.collection, objectszip="/path/to/fake.zip"
        )

    def test_dip_deletion_error(self):
        url = reverse("delete_dip", kwargs={"pk": self.dip.pk})
        response = self.client.post(url, {})
        form = response.context.get("form")
        self.assertTrue(form.fields["identifier"].error_messages)
        response = self.client.post(url, {"identifier": "wrong_identifier"})
        form = response.context.get("form")
        self.assertTrue(form.fields["identifier"].error_messages)

    @patch("elasticsearch.client.Elasticsearch.delete")
    @patch("scope.models.celery_app.send_task")
    def test_dip_deletion_success(self, mock_send_task, mock_es_delete):
        url = reverse("delete_dip", kwargs={"pk": self.dip.pk})
        self.assertTrue(DIP.objects.filter(dc__identifier="A").exists())
        self.client.post(url, {"identifier": "A"})
        self.assertFalse(DIP.objects.filter(dc__identifier="A").exists())

    def test_collection_deletion_error(self):
        url = reverse("delete_collection", kwargs={"pk": self.collection.pk})
        response = self.client.post(url, {})
        form = response.context.get("form")
        self.assertTrue(form.fields["identifier"].error_messages)
        response = self.client.post(url, {"identifier": "wrong_identifier"})
        form = response.context.get("form")
        self.assertTrue(form.fields["identifier"].error_messages)

    @patch("elasticsearch.client.Elasticsearch.delete")
    @patch("scope.models.celery_app.send_task")
    def test_collection_deletion_success(self, mock_send_task, mock_es_delete):
        url = reverse("delete_collection", kwargs={"pk": self.collection.pk})
        self.assertTrue(Collection.objects.filter(dc__identifier="1").exists())
        self.client.post(url, {"identifier": "1"})
        self.assertFalse(Collection.objects.filter(dc__identifier="1").exists())
