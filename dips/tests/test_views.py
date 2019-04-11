import uuid
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from dips.models import User


class ViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.client.login(username="admin", password="admin")

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", return_value=0)
    @patch("dips.views.messages.error")
    def test_search_wrong_dates(self, mock_msg_error, mock_es_count, mock_es_exec):
        response = self.client.get(
            "/search/", {"start_date": "2018/01/01", "end_date": "Nov. 6, 2018"}
        )
        expected_filters = {
            "formats": [],
            "collections": [],
            "start_date": "2018/01/01",
            "end_date": "Nov. 6, 2018",
        }
        # Wrong formats should be maintained in filters
        self.assertEqual(response.context["filters"], expected_filters)
        # But the errors should be added to the messages
        self.assertEqual(mock_msg_error.call_count, 2)


class DIPStoredWebhookTest(APITestCase):
    def test_dip_stored_webhook_success(self):
        user = User.objects.create_superuser("admin", "admin@example.com", "admin")
        token = Token.objects.create(user=user)
        dip_uuid = uuid.uuid4()

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        url = reverse("dip_stored_webhook", kwargs={"dip_uuid": dip_uuid})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(str(dip_uuid), response.data["message"])
