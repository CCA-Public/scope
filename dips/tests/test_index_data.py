from django.core.management import call_command
from django.test import TestCase
from unittest.mock import patch

from dips.models import Collection, DIP, DigitalFile


class IndexDataTests(TestCase):
    fixtures = ['index_data']

    # Patch tqdm and print to disable output
    @patch('search.management.commands.index_data.print')
    @patch('search.management.commands.index_data.tqdm')
    # Patch bulk to avoid ES requests
    @patch('elasticsearch.Elasticsearch.bulk')
    # Mock models get_es_data to check call_counts
    @patch.object(Collection, 'get_es_data', return_value={})
    @patch.object(DIP, 'get_es_data', return_value={})
    @patch.object(DigitalFile, 'get_es_data', return_value={})
    # Mock index create and delete to avoid ES requests and check call_counts
    @patch('elasticsearch_dsl.Index.create')
    @patch('elasticsearch_dsl.Index.delete')
    def test_index_recreation(self, mock_delete, mock_create,
                              mock_dig, mock_dip, mock_col,
                              patch_a, patch_b, patch_c):
        call_command('index_data')
        self.assertEqual(mock_delete.call_count, 3)
        self.assertEqual(mock_create.call_count, 3)
        self.assertEqual(mock_dig.call_count, 12)
        self.assertEqual(mock_dip.call_count, 2)
        self.assertEqual(mock_col.call_count, 2)
