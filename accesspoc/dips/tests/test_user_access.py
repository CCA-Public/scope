from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import Group
from dips.models import User, Collection, DIP, DigitalFile

import os

GET_PAGES = {
    'faq': [
        ('unauth', 200),
        ('admin', 200),
        ('editor', 200),
        ('basic', 200),
    ],
    'home': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 200),
    ],
    'search': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 200),
    ],
    'users': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 302),
        ('basic', 302),
    ],
    'new_user': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 302),
        ('basic', 302),
    ],
    'edit_user': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 302),
        ('basic', 302),
    ],
    'collection': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 200),
    ],
    'new_collection': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 302),
    ],
    'edit_collection': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 302),
    ],
    'delete_collection': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 302),
        ('basic', 302),
    ],
    'dip': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 200),
    ],
    'new_dip': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 302),
    ],
    'edit_dip': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 302),
    ],
    'delete_dip': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 302),
        ('basic', 302),
    ],
    'digital_file': [
        ('unauth', 302),
        ('admin', 200),
        ('editor', 200),
        ('basic', 200),
    ],
}


class UserAccessTests(TestCase):
    def setUp(self):
        # Create test users
        User.objects.create_superuser('admin', 'admin@example.com', 'admin')
        User.objects.create_user('basic', 'basic@example.com', 'basic')
        editor_user = User.objects.create_user('editor', 'editor@example.com', 'editor')
        group = Group.objects.get(name='Edit Collections and Folders')
        editor_user.groups.add(group)

        # Create editable resources
        self.user = User.objects.create_user('test', 'test@example.com', 'test')
        self.collection = Collection.objects.create(identifier='1')
        self.dip = DIP.objects.create(
            identifier='A',
            ispartof=self.collection,
            objectszip=os.path.join(settings.MEDIA_ROOT, 'fake.zip'),
        )
        self.digital_file = DigitalFile.objects.create(
            uuid='e75c7789-7ebf-41b3-a233-39d4003e42ec',
            dip=self.dip,
            size_bytes=1
        )

    def test_get_pages(self):
        '''
        Makes get requests to pages with different user types logged in
        and verifies if the user can see the page or gets redirected.
        '''
        for page, responses in GET_PAGES.items():
            if page in ['edit_user']:
                url = reverse(page, kwargs={'pk': self.user.pk})
            elif page in ['collection', 'edit_collection', 'delete_collection']:
                url = reverse(page, kwargs={'identifier': self.collection.identifier})
            elif page in ['dip', 'edit_dip', 'delete_dip']:
                url = reverse(page, kwargs={'identifier': self.dip.identifier})
            elif page in ['digital_file']:
                url = reverse(page, kwargs={'uuid': self.digital_file.uuid})
            else:
                url = reverse(page)

            for user, code in responses:
                if user is not 'unauth':
                    self.client.login(username=user, password=user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, code)
                self.client.logout()

    def test_post_user(self):
        '''
        Makes post requests to create and edit user pages with different
        user types logged in and verifies the results.
        '''
        new_url = reverse('new_user')
        new_data = {
            'username': 'test2',
            'password1': 'test123test',
            'password2': 'test123test',
        }
        edit_url = reverse('edit_user', kwargs={'pk': self.user.pk})
        edit_data = {
            'username': 'test_changed',
        }

        # Unauthenticated, create
        before_count = len(User.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/?next=/new_user/')
        after_count = len(User.objects.all())
        self.assertEqual(before_count, after_count)
        # Unauthenticated, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        next_url = '/login/?next=/user/%s/edit' % self.user.pk
        self.assertEqual(response.url, next_url)
        self.assertFalse(User.objects.filter(username='test_changed').exists())

        # Basic, create
        self.client.login(username='basic', password='basic')
        before_count = len(User.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        after_count = len(User.objects.all())
        self.assertEqual(before_count, after_count)
        # Basic, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.assertFalse(User.objects.filter(username='test_changed').exists())
        self.client.logout()

        # Editor, create
        self.client.login(username='editor', password='editor')
        before_count = len(User.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        after_count = len(User.objects.all())
        self.assertEqual(before_count, after_count)
        # Editor, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        self.assertFalse(User.objects.filter(username='test_changed').exists())
        self.client.logout()

        # Admin, create
        self.client.login(username='admin', password='admin')
        before_count = len(User.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/users/')
        after_count = len(User.objects.all())
        self.assertEqual(before_count + 1, after_count)
        # Admin, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/users/')
        self.assertTrue(User.objects.filter(username='test_changed').exists())
        self.client.logout()

    def test_post_collection(self):
        '''
        Makes post requests to create and edit collection pages with different
        user types logged in and verifies the results.
        '''
        new_url = reverse('new_collection')
        new_data = {
            'identifier': '2',
        }
        new_data_2 = {
            'identifier': '3',
        }
        edit_url = reverse('edit_collection', kwargs={'identifier': self.collection.identifier})
        edit_data = {
            'identifier': '2',
            'title': 'test_collection_2',
        }
        edit_data_2 = {
            'identifier': '3',
            'title': 'test_collection_3',
        }

        # Unauthenticated, create
        before_count = len(Collection.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/?next=/new_collection/')
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)
        # Unauthenticated, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        next_url = '/login/?next=/collection/%s/edit/' % self.collection.identifier
        self.assertEqual(response.url, next_url)
        self.assertFalse(Collection.objects.filter(title='test_collection_2').exists())

        # Basic, create
        self.client.login(username='basic', password='basic')
        before_count = len(Collection.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)
        # Basic, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/collection/%s/' % self.collection.identifier)
        self.assertFalse(Collection.objects.filter(title='test_collection_2').exists())
        self.client.logout()

        # Editor, create
        self.client.login(username='editor', password='editor')
        before_count = len(Collection.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count + 1, after_count)
        # Editor, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/collection/%s/' % self.collection.identifier)
        self.assertTrue(Collection.objects.filter(title='test_collection_2').exists())
        self.client.logout()

        # Admin, create
        self.client.login(username='admin', password='admin')
        before_count = len(Collection.objects.all())
        response = self.client.post(new_url, new_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count + 1, after_count)
        # Admin, edit
        response = self.client.post(edit_url, edit_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/collection/%s/' % self.collection.identifier)
        self.assertTrue(Collection.objects.filter(title='test_collection_3').exists())
        self.client.logout()

    def test_post_dip(self):
        '''
        Makes post requests to create and edit DIP pages with different
        user types logged in and verifies the results.
        '''
        new_url = reverse('new_dip')
        new_data = {
            'identifier': 'B',
            'ispartof': self.collection.identifier,
        }
        edit_url = reverse('edit_dip', kwargs={'identifier': self.dip.identifier})
        edit_data = {
            'identifier': 'A',
            'title': 'test_dip_2',
            'ispartof': self.collection.identifier,
        }
        edit_data_2 = {
            'identifier': 'A',
            'title': 'test_dip_3',
            'ispartof': self.collection.identifier,
        }

        # Unauthenticated, create
        before_count = len(DIP.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/login/?next=/new_folder/')
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)
        # Unauthenticated, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        next_url = '/login/?next=/folder/%s/edit/' % self.dip.identifier
        self.assertEqual(response.url, next_url)
        self.assertFalse(DIP.objects.filter(title='test_dip_2').exists())

        # Basic, create
        self.client.login(username='basic', password='basic')
        before_count = len(DIP.objects.all())
        response = self.client.post(new_url, new_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)
        # Basic, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/folder/%s/' % self.dip.identifier)
        self.assertFalse(DIP.objects.filter(title='test_dip_2').exists())
        self.client.logout()

        # Editor, create
        self.client.login(username='editor', password='editor')
        # To avoid testing the file upload in here, the form validation
        # should fail, returnnig a 200 status code with errors in the form.
        response = self.client.post(new_url, new_data)
        form = response.context.get('form')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(form.errors)
        # Editor, edit
        response = self.client.post(edit_url, edit_data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/folder/%s/' % self.dip.identifier)
        self.assertTrue(DIP.objects.filter(title='test_dip_2').exists())
        self.client.logout()

        # Admin, create
        self.client.login(username='admin', password='admin')
        # To avoid testing the file upload in here, the form validation
        # should fail, returnnig a 200 status code with errors in the form.
        response = self.client.post(new_url, new_data)
        form = response.context.get('form')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(form.errors)
        # Admin, edit
        response = self.client.post(edit_url, edit_data_2)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/folder/%s/' % self.dip.identifier)
        self.assertTrue(DIP.objects.filter(title='test_dip_3').exists())
        self.client.logout()

    def test_delete_dip(self):
        '''
        Makes post request to delete a DIP with different
        user types logged in and verifies the results.
        '''
        url = reverse('delete_dip', kwargs={'identifier': self.dip.identifier})
        data = {
            'identifier': 'A',
        }

        # Unauthenticated
        before_count = len(DIP.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = '/login/?next=/folder/%s/delete/' % self.dip.identifier
        self.assertEqual(response.url, next_url)
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)

        # Basic
        self.client.login(username='basic', password='basic')
        before_count = len(DIP.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = '/folder/%s/' % self.dip.identifier
        self.assertEqual(response.url, next_url)
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)

        # Editor
        self.client.login(username='editor', password='editor')
        before_count = len(DIP.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = '/folder/%s/' % self.dip.identifier
        self.assertEqual(response.url, next_url)
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count)

        # Admin
        self.client.login(username='admin', password='admin')
        before_count = len(DIP.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        after_count = len(DIP.objects.all())
        self.assertEqual(before_count, after_count + 1)

    def test_delete_collection(self):
        '''
        Makes post request to delete a collection with different
        user types logged in and verifies the results.
        '''
        url = reverse('delete_collection', kwargs={'identifier': self.collection.identifier})
        data = {
            'identifier': '1',
        }

        # Unauthenticated
        before_count = len(Collection.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = '/login/?next=/collection/%s/delete/' % self.collection.identifier
        self.assertEqual(response.url, next_url)
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)

        # Basic
        self.client.login(username='basic', password='basic')
        before_count = len(Collection.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = '/collection/%s/' % self.collection.identifier
        self.assertEqual(response.url, next_url)
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)

        # Editor
        self.client.login(username='editor', password='editor')
        before_count = len(Collection.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        next_url = '/collection/%s/' % self.collection.identifier
        self.assertEqual(response.url, next_url)
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count)

        # Admin
        self.client.login(username='admin', password='admin')
        before_count = len(Collection.objects.all())
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        after_count = len(Collection.objects.all())
        self.assertEqual(before_count, after_count + 1)
