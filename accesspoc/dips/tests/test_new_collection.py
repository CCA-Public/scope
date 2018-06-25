from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test import TestCase
from unittest.mock import patch

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
            'format': 'test',
            'abstract': 'Lorem ipsum dolor sit amet',
            'creator': 'test',
            'link': 'http://fake.url'
        }
        self.client.post(url, data)
        collection = Collection.objects.get(pk=1)
        self.assertTrue(collection)

    def test_new_topic_invalid_post_data_empty_fields(self):
        """
        Invalid post data should not redirect
        The expected behavior is to show the form again with validation errors
        """
        url = reverse('new_collection')
        response = self.client.post(url, {})
        form = response.context.get('dc_form')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(form.fields['identifier'].error_messages)

    def test_contains_form(self):
        url = reverse('new_collection')
        response = self.client.get(url)
        self.assertTrue(response.context.get('form'))
