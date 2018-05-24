from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.urls import resolve
from django.test import TestCase
from .views import home, collection, dip, new_collection
from .models import Collection, DIP
from .forms import CollectionForm

import os

class HomeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')

    def test_home_view_status_code(self):
        url = reverse('home')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_home_url_resolves_home_view(self):
        view = resolve('/')
        self.assertEquals(view.func, home)

class CollectionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')
        Collection.objects.create(identifier='AP999', title='Title', date='1990',
            dcformat='test', description='test', creator='test',
            link='http://fake.url')

    def test_collection_view_success_status_code(self):
        url = reverse('collection', kwargs={'identifier': 'AP999'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_collection_view_not_found_status_code(self):
        url = reverse('collection', kwargs={'identifier': 'AP998'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)

    def test_collection_url_resolves_collection_view(self):
        view = resolve('/collection/AP999/')
        self.assertEquals(view.func, collection)

class DIPTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')
        Collection.objects.create(identifier='AP999', title='Title', date='1990',
            dcformat='test', description='test', creator='test',
            link='http://fake.url')
        collection = Collection.objects.only('identifier').get(identifier='AP999')
        DIP.objects.create(identifier='AP999.S1.001', title='Title', date='1990',
            dcformat='test', description='test', creator='test',
            ispartof=collection,
            objectszip=os.path.join(settings.MEDIA_ROOT, 'fake.zip'))

    def test_dip_view_success_status_code(self):
        url = reverse('dip', kwargs={'identifier': 'AP999.S1.001'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)

    def test_dip_view_not_found_status_code(self):
        url = reverse('dip', kwargs={'identifier': 'AP998.S1.001'})
        response = self.client.get(url)
        self.assertEquals(response.status_code, 404)

    def test_dip_url_resolves_dip_view(self):
        view = resolve('/folder/AP999.S1.001/')
        self.assertEquals(view.func, dip)

class NewCollectionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')

    def test_csrf(self):
        url = reverse('new_collection')
        response = self.client.get(url)
        self.assertContains(response, 'csrfmiddlewaretoken')

    def test_new_topic_valid_post_data(self):
        # make collection
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
        response = self.client.post(url, data)
        collection = Collection.objects.get(identifier='AP999')
        self.assertTrue(collection)

    def test_new_topic_invalid_post_data(self):
        '''
        Invalid post data should not redirect
        The expected behavior is to show the form again with validation errors
        '''
        url = reverse('new_collection')
        response = self.client.post(url)
        form = response.context.get('form')
        self.assertIsInstance(form, CollectionForm)

    def test_new_topic_invalid_post_data_empty_fields(self):
        '''
        Invalid post data should not redirect
        The expected behavior is to show the form again with validation errors
        '''
        url = reverse('new_collection')
        response = self.client.post(url, {})
        form = response.context.get('form')
        self.assertEquals(response.status_code, 200)
        self.assertTrue(form.errors)

    def test_contains_form(self):
        url = reverse('new_collection')
        response = self.client.get(url)
        form = response.context.get('form')
        self.assertIsInstance(form, CollectionForm)
