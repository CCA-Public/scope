from unittest.mock import patch

from django.test import TestCase

from scope.models import DIP
from scope.models import DigitalFile
from search.tasks import delete_es_descendants
from search.tasks import update_es_descendants


class TasksTests(TestCase):
    fixtures = ["index_data"]

    def test_update_es_descendants_wrong_class(self):
        with self.assertRaises(ValueError):
            update_es_descendants("DigitalFile", 1)

    @patch("search.tasks.bulk", return_value=(1, []))
    @patch("scope.models.Collection.get_es_data_for_files")
    @patch("scope.models.DigitalFile.objects.filter")
    def test_update_es_descendants_collection(
        self, mock_orm_filter, mock_get_es_data, mock_task_bulk
    ):
        update_es_descendants("Collection", 1)
        # The DigitalFiles should be filtered
        mock_orm_filter.assert_called_with(dip__collection__pk=1)
        # The Collection data should be obtained (actual
        # data is tested in `test_models_to_docs`)
        mock_get_es_data.assert_called()
        # It's hard to assert the bulk call parameters as the second
        # one is a generator so we'll only check that it has been called.
        mock_task_bulk.assert_called()

    @patch("search.tasks.bulk", return_value=(1, []))
    @patch("scope.models.DIP.get_es_data_for_files")
    @patch("scope.models.DigitalFile.objects.filter")
    def test_update_es_descendants_dip(
        self, mock_orm_filter, mock_get_es_data, mock_task_bulk
    ):
        update_es_descendants("DIP", 1)
        # The DigitalFiles should be filtered
        mock_orm_filter.assert_called_with(dip__pk=1)
        # The DIP data should be obtained (actual
        # data is tested in `test_models_to_docs`)
        mock_get_es_data.assert_called()
        # It's hard to assert the bulk call parameters as the second
        # one is a generator so we'll only check that it has been called.
        mock_task_bulk.assert_called()

    @patch("search.tasks.logger.info")
    @patch("search.tasks.bulk", return_value=(1, ["error_1", "error_2"]))
    def test_update_es_descendants_errors_logged(self, mock_task_bulk, mock_log_info):
        update_es_descendants("DIP", 1)
        self.assertEqual(mock_log_info.call_count, 5)

    def test_delete_es_descendants_wrong_class(self):
        with self.assertRaises(ValueError):
            delete_es_descendants("DigitalFile", 1)

    @patch("elasticsearch.Elasticsearch.delete_by_query")
    def test_delete_es_descendants_collection(self, mock_es_delete):
        indexes = "%s,%s" % (DIP.es_doc._index._name, DigitalFile.es_doc._index._name)
        body = {"query": {"match": {"collection.id": 1}}}
        delete_es_descendants("Collection", 1)
        mock_es_delete.assert_called_with(index=indexes, body=body)

    @patch("elasticsearch.Elasticsearch.delete_by_query")
    def test_delete_es_descendants_dip(self, mock_es_delete):
        indexes = DigitalFile.es_doc._index._name
        body = {"query": {"match": {"dip.id": 1}}}
        delete_es_descendants("DIP", 1)
        mock_es_delete.assert_called_with(index=indexes, body=body)

    @patch("search.tasks.logger.info")
    @patch(
        "elasticsearch.Elasticsearch.delete_by_query",
        return_value={"total": 1, "deleted": 1, "failures": ["error"]},
    )
    def test_delete_es_descendants_errors_logged(self, mock_es_delete, mock_log_info):
        delete_es_descendants("DIP", 1)
        self.assertEqual(mock_log_info.call_count, 4)
