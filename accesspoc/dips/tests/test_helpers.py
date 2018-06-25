from django.test import TestCase

from dips.helpers import add_if_not_empty


class HelpersTests(TestCase):

    def test_add_if_not_empty(self):
        data = {}
        add_if_not_empty(data, 'a', 'value')
        add_if_not_empty(data, 'b', '')
        add_if_not_empty(data, 'c', [])
        add_if_not_empty(data, 'd', {})
        add_if_not_empty(data, 'e', ())
        add_if_not_empty(data, 'f', 0)
        self.assertEqual(data, {'a': 'value'})
