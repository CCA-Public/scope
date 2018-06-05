from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.urls import resolve
from django.test import TestCase
from dips.views import home


class HomeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user('temp', 'temp@example.com', 'temp')
        self.client.login(username='temp', password='temp')

    def test_home_view_status_code(self):
        url = reverse('home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_home_url_resolves_home_view(self):
        view = resolve('/')
        self.assertEqual(view.func, home)
