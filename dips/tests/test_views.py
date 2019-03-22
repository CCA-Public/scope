from django.test import TestCase
from unittest.mock import patch

from dips.models import User


class ViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'admin')
        self.client.login(username='admin', password='admin')

    @patch('elasticsearch_dsl.Search.execute')
    @patch('elasticsearch_dsl.Search.count', return_value=0)
    @patch('dips.views.messages.error')
    def test_search_wrong_dates(self, mock, patch, patch_2):
        response = self.client.get(
            '/search/', {'start_date': '2018/01/01', 'end_date': 'Nov. 6, 2018'})
        expected_filters = {
            'formats': [],
            'collections': [],
            'start_date': '2018/01/01',
            'end_date': 'Nov. 6, 2018',
        }
        # Wrong formats should be maintained in filters
        self.assertEqual(response.context['filters'], expected_filters)
        # But the errors should be added to the messages
        self.assertEqual(mock.call_count, 2)
