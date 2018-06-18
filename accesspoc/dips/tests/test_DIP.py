from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.urls import resolve
from unittest.mock import patch

from dips.views import dip
from dips.models import Collection, DIP

import os


class DIPTests(TestCase):
    @patch('elasticsearch_dsl.DocType.save')
    def setUp(self, patch):
        User = get_user_model()
        User.objects.create_user('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')
        Collection.objects.create(
            identifier='AP999', title='Title', date='1990',
            dcformat='test', description='test', creator='test',
            link='http://fake.url',
        )
        collection = Collection.objects.only('identifier').get(identifier='AP999')
        DIP.objects.create(
            identifier='AP999.S1.001', title='Title', date='1990',
            dcformat='test', description='test', creator='test',
            ispartof=collection,
            objectszip=os.path.join(settings.MEDIA_ROOT, 'fake.zip'),
        )

    @patch('elasticsearch_dsl.Search.execute')
    def test_dip_view_success_status_code(self, patch):
        url = reverse('dip', kwargs={'identifier': 'AP999.S1.001'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_dip_view_not_found_status_code(self):
        url = reverse('dip', kwargs={'identifier': 'AP998.S1.001'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_dip_url_resolves_dip_view(self):
        view = resolve('/folder/AP999.S1.001/')
        self.assertEqual(view.func, dip)
