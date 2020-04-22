from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from django.urls import resolve
from unittest.mock import patch

from scope.views import dip
from scope.models import Collection, DIP, DublinCore


class DIPTests(TestCase):
    @patch("elasticsearch_dsl.DocType.save")
    def setUp(self, mock_es_save):
        User = get_user_model()
        User.objects.create_user("temp", "temp@example.com", "temp")
        self.client.login(username="temp", password="temp")
        dc = DublinCore.objects.create(
            identifier="AP999",
            title="Title",
            date="1990",
            format="test",
            description="test",
            creator="test",
        )
        collection = Collection.objects.create(link="http://fake.url", dc=dc)
        dc = DublinCore.objects.create(
            identifier="AP999.S1.001",
            title="Title",
            date="1990",
            format="test",
            description="test",
            creator="test",
        )
        self.dip = DIP.objects.create(
            dc=dc, collection=collection, objectszip="/path/to/fake.zip"
        )

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", autospec=True, return_value=0)
    def test_dip_view_success_status_code(self, mock_es_count, mock_es_exec):
        url = reverse("dip", kwargs={"pk": self.dip.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dip_view_not_found_status_code(self):
        url = reverse("dip", kwargs={"pk": 0})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_dip_url_resolves_dip_view(self):
        view = resolve("/folder/%s/" % self.dip.pk)
        self.assertEqual(view.func, dip)
