from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from unittest.mock import patch

from dips.models import DIP


class ImportPendingRedirectTests(TestCase):
    fixtures = ['models_to_docs']

    @patch('elasticsearch_dsl.DocType.save')
    def setUp(self, patch):
        User = get_user_model()
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        self.client.login(username='admin', password='admin')
        self.dip = DIP.objects.get(pk=1)
        self.dip.import_status = DIP.IMPORT_PENDING
        self.dip.save()

    def test_dip_view_redirect(self):
        url = reverse('dip', kwargs={'pk': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            '/collection/%s/' % self.dip.collection.pk,
        )

    def test_digital_file_view_redirect(self):
        url = reverse(
            'digital_file',
            kwargs={'pk': '07263cdf-d11f-4d24-9e16-ef46f002d037'},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            '/collection/%s/' % self.dip.collection.pk,
        )
