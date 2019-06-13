from django.test import TestCase
from unittest.mock import patch

from scope.models import Content, User


class ViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin", "admin@example.com", "admin")
        self.client.login(username="admin", password="admin")
        self.faq = Content.objects.get(key="03_faq")

    @patch("elasticsearch_dsl.Search.execute")
    @patch("elasticsearch_dsl.Search.count", return_value=0)
    @patch("scope.views.messages.error")
    def test_search_wrong_dates(self, mock_msg_error, mock_es_count, mock_es_exec):
        response = self.client.get(
            "/search/", {"start_date": "2018/01/01", "end_date": "Nov. 6, 2018"}
        )
        expected_filters = {
            "formats": [],
            "collections": [],
            "start_date": "2018/01/01",
            "end_date": "Nov. 6, 2018",
        }
        # Wrong formats should be maintained in filters
        self.assertEqual(response.context["filters"], expected_filters)
        # But the errors should be added to the messages
        self.assertEqual(mock_msg_error.call_count, 2)

    def test_content_get_en(self):
        response = self.client.get("/content/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(len(response.context["formset"]), 3)
        self.assertContains(response, "## Digital Archives Access Interface")

    def test_content_get_fr(self):
        response = self.client.get("/content/", HTTP_ACCEPT_LANGUAGE="fr")
        self.assertEqual(len(response.context["formset"]), 3)
        self.assertContains(
            response, "## Interface d&#39;accès aux archives numériques"
        )

    def test_content_post_en(self):
        data = {
            "form-TOTAL_FORMS": ["3"],
            "form-INITIAL_FORMS": ["3"],
            "form-MIN_NUM_FORMS": ["0"],
            "form-MAX_NUM_FORMS": ["1000"],
            "form-0-content": ["New English content"],
            "form-0-key": ["01_home"],
            "form-1-content": [""],
            "form-1-key": ["02_login"],
            "form-2-content": [""],
            "form-2-key": ["03_faq"],
        }
        self.client.post("/content/", data, HTTP_ACCEPT_LANGUAGE="en")
        content = Content.objects.get(key="01_home")
        self.assertEqual(content.content_en, "New English content")

    def test_content_post_fr(self):
        data = {
            "form-TOTAL_FORMS": ["3"],
            "form-INITIAL_FORMS": ["3"],
            "form-MIN_NUM_FORMS": ["0"],
            "form-MAX_NUM_FORMS": ["1000"],
            "form-0-content": ["New French content"],
            "form-0-key": ["01_home"],
            "form-1-content": [""],
            "form-1-key": ["02_login"],
            "form-2-content": [""],
            "form-2-key": ["03_faq"],
        }
        self.client.post("/content/", data, HTTP_ACCEPT_LANGUAGE="fr")
        content = Content.objects.get(key="01_home")
        self.assertEqual(content.content_fr, "New French content")

    def test_faq_deleted(self):
        self.faq.delete()
        response = self.client.get("/faq/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 200)

    def test_faq_markdown(self):
        self.faq.content_en = "## Header"
        self.faq.save()
        response = self.client.get("/faq/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "<h2>Header</h2>")

    def test_faq_html(self):
        self.faq.content_en = "<h2>Header</h2>"
        self.faq.save()
        response = self.client.get("/faq/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "<h2>Header</h2>")

    def test_faq_langs(self):
        self.faq.content_en = "English content"
        self.faq.save()
        # English
        response = self.client.get("/faq/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertContains(response, "English content")
        # Fallback
        response = self.client.get("/faq/", HTTP_ACCEPT_LANGUAGE="fr")
        self.assertContains(response, "English content")
        # French
        self.faq.content_fr = "French content"
        self.faq.save()
        response = self.client.get("/faq/", HTTP_ACCEPT_LANGUAGE="fr")
        self.assertContains(response, "French content")
