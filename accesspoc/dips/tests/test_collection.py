from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.urls import resolve
from django.test import TestCase
from dips.views import collection
from dips.models import Collection


class CollectionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')
        Collection.objects.create(
            identifier='AP999', title='Title', date='1990',
            dcformat='test', description='test', creator='test',
            link='http://fake.url',
        )

    def test_collection_view_success_status_code(self):
        url = reverse('collection', kwargs={'identifier': 'AP999'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_collection_view_not_found_status_code(self):
        url = reverse('collection', kwargs={'identifier': 'AP998'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_collection_url_resolves_collection_view(self):
        view = resolve('/collection/AP999/')
        self.assertEqual(view.func, collection)
