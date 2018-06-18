from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase
from unittest.mock import patch

from dips.forms import CollectionForm
from dips.models import Collection


class NewCollectionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_superuser('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')

    def test_csrf(self):
        url = reverse('new_collection')
        response = self.client.get(url)
        self.assertContains(response, 'csrfmiddlewaretoken')

    @patch('elasticsearch_dsl.DocType.save')
    def test_new_topic_valid_post_data(self, patch):
        # Make collection
        url = reverse('new_collection')
        data = {
            'identifier': 'AP999',
            'title': 'Title',
            'date': '1990',
            'dcformat': 'test',
            'abstract': 'Lorem ipsum dolor sit amet',
            'creator': 'test',
            'findingaid': 'http://fake.url'
        }
        self.client.post(url, data)
        collection = Collection.objects.get(identifier='AP999')
        self.assertTrue(collection)

    def test_new_topic_invalid_post_data(self):
        """
        Invalid post data should not redirect
        The expected behavior is to show the form again with validation errors
        """
        url = reverse('new_collection')
        response = self.client.post(url)
        form = response.context.get('form')
        self.assertIsInstance(form, CollectionForm)

    def test_new_topic_invalid_post_data_empty_fields(self):
        """
        Invalid post data should not redirect
        The expected behavior is to show the form again with validation errors
        """
        url = reverse('new_collection')
        response = self.client.post(url, {})
        form = response.context.get('form')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(form.errors)

    def test_contains_form(self):
        url = reverse('new_collection')
        response = self.client.get(url)
        form = response.context.get('form')
        self.assertIsInstance(form, CollectionForm)
