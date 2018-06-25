from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.urls import resolve
from django.test import TestCase
from unittest.mock import patch

from dips.views import collection
from dips.models import Collection, DublinCore


class CollectionTests(TestCase):
    @patch('elasticsearch_dsl.DocType.save')
    def setUp(self, patch):
        User = get_user_model()
        User.objects.create_user('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')
        dc = DublinCore.objects.create(
            identifier='AP999', title='Title', date='1990',
            format='test', description='test', creator='test',
        )
        self.collection = Collection.objects.create(
            link='http://fake.url',
            dc=dc,
        )

    @patch('elasticsearch_dsl.Search.execute')
    def test_collection_view_success_status_code(self, patch):
        url = reverse('collection', kwargs={'pk': self.collection.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_collection_view_not_found_status_code(self):
        url = reverse('collection', kwargs={'pk': 0})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_collection_url_resolves_collection_view(self):
        view = resolve('/collection/%s/' % self.collection.pk)
        self.assertEqual(view.func, collection)
