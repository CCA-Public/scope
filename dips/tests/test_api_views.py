import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from dips.models import User


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
