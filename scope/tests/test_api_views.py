import uuid
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from scope.models import DIP, User


class DIPStoredWebhookTest(APITestCase):
    def setUp(self):
        self.dip_uuid = uuid.uuid4()
        self.url = reverse("dip_stored_webhook", kwargs={"dip_uuid": self.dip_uuid})
        admin = User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.admin_token = Token.objects.create(user=admin)

    @patch("scope.api_views.chain")
    @patch("elasticsearch_dsl.DocType.save")
    def test_dip_stored_webhook_success(self, mock_es_save, mock_chain):
        self.client.credentials(HTTP_AUTHORIZATION="Token %s" % self.admin_token.key)
        origin = "http://192.168.1.128:62081"
        headers = {"HTTP_ORIGIN": origin}
        response = self.client.post(self.url, **headers)
        dip = DIP.objects.get(
            ss_uuid=self.dip_uuid,
            ss_host_url=origin,
            ss_download_url="%s/api/v2/file/%s/download/" % (origin, self.dip_uuid),
            dc__identifier=self.dip_uuid,
            import_status=DIP.IMPORT_PENDING,
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn(str(self.dip_uuid), response.data["message"])
        self.assertTrue(dip)
        mock_chain.assert_called()

    def test_dip_stored_webhook_no_authorization(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dip_stored_webhook_not_enough_permissions(self):
        user = User.objects.create_user("editor", "editor@example.com", "editor")
        group = Group.objects.get(name="Editors")
        user.groups.add(group)
        token = Token.objects.create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION="Token %s" % token.key)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dip_stored_webhook_no_origin(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token %s" % self.admin_token.key)
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"], "Origin not set in the request headers."
        )

    def test_dip_stored_webhook_unknown_origin(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token %s" % self.admin_token.key)
        origin = "http://localhost"
        headers = {"HTTP_ORIGIN": origin}
        response = self.client.post(self.url, **headers)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data["detail"], "SS host not configured for Origin: %s" % origin
        )

    @patch("elasticsearch_dsl.DocType.save")
    def test_dip_stored_webhook_dip_already_exists(self, mock_es_save):
        DIP.objects.create(ss_uuid=self.dip_uuid)
        self.client.credentials(HTTP_AUTHORIZATION="Token %s" % self.admin_token.key)
        origin = "http://192.168.1.128:62081"
        headers = {"HTTP_ORIGIN": origin}
        response = self.client.post(self.url, **headers)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertEqual(
            response.data["detail"],
            "A DIP already exists with the same UUID: %s" % self.dip_uuid,
        )
