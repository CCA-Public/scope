from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from unittest.mock import patch


class HomeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        User.objects.create_user("temp", "temp@example.com", "temp")
        self.client.login(username="temp", password="temp")

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", return_value=0)
    def test_home_template(self, mock_es_count, mock_es_exec):
        url = reverse("home")
        response = self.client.get(url)
        self.assertTemplateUsed(response, "home.html")

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", return_value=0)
    def test_collections_template(self, mock_es_count, mock_es_exec):
        url = reverse("collections")
        response = self.client.get(url)
        self.assertTemplateUsed(response, "collections.html")
