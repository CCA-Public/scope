from django.test import TestCase
from unittest.mock import patch

from dips import helpers
from dips.models import DigitalFile


class HelpersTests(TestCase):
    def setUp(self):
        self.es_search = DigitalFile.es_doc.search()
        self.orm_query_set = DigitalFile.objects.all().order_by("pk")
        self.sort_options = {
            "path": "filepath.raw",
            "format": "fileformat.raw",
            "size": "size_bytes",
            "date": "datemodified",
        }
        self.sort_default = "path"
        self.wrong_limits = [
            "0",  # can't be zero
            "-1",  # can't be negative
            "101",  # can't be higher than 100
            "text",  # has to be an integer
        ]

    def test_add_if_not_empty(self):
        data = {}
        helpers.add_if_not_empty(data, "a", "value")
        helpers.add_if_not_empty(data, "b", "")
        helpers.add_if_not_empty(data, "c", [])
        helpers.add_if_not_empty(data, "d", {})
        helpers.add_if_not_empty(data, "e", ())
        helpers.add_if_not_empty(data, "f", 0)
        self.assertEqual(data, {"a": "value"})

    def test_convert_size(self):
        SIZES_SUCCESS = [
            (2947251846, "3 GB"),
            (343623, "336 KB"),
            (15460865296738292569, "13 EB"),
            (2342, "2 KB"),
            (678678234206125, "617 TB"),
            (47021265234, "44 GB"),
        ]
        SIZES_ERROR = [
            (0, ValueError),
            ("string_value", TypeError),
            ("47021265234", TypeError),
        ]
        for size, result in SIZES_SUCCESS:
            self.assertEqual(result, helpers.convert_size(size))
        for size, error in SIZES_ERROR:
            self.assertRaises(error, helpers.convert_size, size)

    def test_update_instance_from_dict(self):
        digitalfile = DigitalFile(uuid="fake_uuid")
        file_data = {
            "filepath": "fake_path",
            "fileformat": "fake_format",
            "formatversion": "fake_version",
            "size_bytes": "fake_size",
            "unknown_field": "not_added_not_error",
        }
        digitalfile = helpers.update_instance_from_dict(digitalfile, file_data)
        # Update fields without throwing AttributeError for the
        # unknown field or ValueError for the size_bytes field.
        self.assertEqual(digitalfile.filepath, "fake_path")
        self.assertEqual(digitalfile.fileformat, "fake_format")
        self.assertEqual(digitalfile.formatversion, "fake_version")
        self.assertEqual(digitalfile.size_bytes, "fake_size")

    def test_get_sort_params_default_values(self):
        sort_option, sort_dir = helpers.get_sort_params(
            {}, self.sort_options, self.sort_default
        )
        self.assertEqual(sort_option, "path")
        self.assertEqual(sort_dir, "asc")

    def test_get_sort_params_wrong_values(self):
        sort_option, sort_dir = helpers.get_sort_params(
            {"sort": "unknown", "sort_dir": "unknown"},
            self.sort_options,
            self.sort_default,
        )
        self.assertEqual(sort_option, "path")
        self.assertEqual(sort_dir, "asc")

    def test_get_sort_params_good_values(self):
        sort_option, sort_dir = helpers.get_sort_params(
            {"sort": "format", "sort_dir": "desc"}, self.sort_options, self.sort_default
        )
        self.assertEqual(sort_option, "format")
        self.assertEqual(sort_dir, "desc")

    @patch("elasticsearch_dsl.Search.count", return_value=100)
    def test_get_page_from_search_es_defaults(self, mock_es_count):
        # Elasticsearch search
        page = helpers.get_page_from_search(self.es_search, {})
        # Count matches the return_value of the patch
        self.assertEqual(page.paginator.count, 100)
        # Default limit is 10 so there should be 10 pages
        self.assertEqual(page.paginator.num_pages, 10)
        # The first page is obtained
        self.assertEqual(page.number, 1)
        # The objects_list is the ES query, only with pagination
        self.assertEqual(page.object_list.to_dict(), {"from": 0, "size": 10})

    @patch("django.db.models.query.QuerySet.count", return_value=100)
    def test_get_page_from_search_orm_defaults(self, mock_orm_count):
        # ORM QuerySet
        page = helpers.get_page_from_search(self.orm_query_set, {})
        self.assertEqual(page.paginator.count, 100)
        self.assertEqual(page.paginator.num_pages, 10)
        self.assertEqual(page.number, 1)
        # The objects_list is the QuerySet SQL query
        self.assertEqual(page.object_list.query.low_mark, 0)
        self.assertEqual(page.object_list.query.high_mark, 10)

    @patch("elasticsearch_dsl.Search.count", return_value=100)
    def test_get_page_from_search_es_with_params(self, mock_es_count):
        page = helpers.get_page_from_search(
            self.es_search, {"page": "2", "limit": "20"}
        )
        self.assertEqual(page.number, 2)
        self.assertEqual(page.object_list.to_dict(), {"from": 20, "size": 20})

    @patch("django.db.models.query.QuerySet.count", return_value=100)
    def test_get_page_from_search_orm_with_params(self, mock_orm_count):
        page = helpers.get_page_from_search(
            self.orm_query_set, {"page": "2", "limit": "20"}
        )
        self.assertEqual(page.number, 2)
        self.assertEqual(page.object_list.query.low_mark, 20)
        self.assertEqual(page.object_list.query.high_mark, 40)

    @patch("elasticsearch_dsl.Search.count", return_value=100)
    def test_get_page_from_search_es_wrong_page(self, mock_es_count):
        # Not an integer
        page = helpers.get_page_from_search(self.es_search, {"page": "text"})
        self.assertEqual(page.paginator.num_pages, 10)
        self.assertEqual(page.number, 1)
        self.assertEqual(page.object_list.to_dict(), {"from": 0, "size": 10})
        # Empty page
        page = helpers.get_page_from_search(self.es_search, {"page": "11"})
        self.assertEqual(page.paginator.num_pages, 10)
        self.assertEqual(page.number, 10)
        self.assertEqual(page.object_list.to_dict(), {"from": 90, "size": 10})

    @patch("django.db.models.query.QuerySet.count", return_value=100)
    def test_get_page_from_search_orm_wrong_page(self, mock_orm_count):
        # Not an integer
        page = helpers.get_page_from_search(self.orm_query_set, {"page": "text"})
        self.assertEqual(page.paginator.num_pages, 10)
        self.assertEqual(page.number, 1)
        self.assertEqual(page.object_list.query.low_mark, 0)
        self.assertEqual(page.object_list.query.high_mark, 10)
        # Empty page
        page = helpers.get_page_from_search(self.orm_query_set, {"page": "11"})
        self.assertEqual(page.paginator.num_pages, 10)
        self.assertEqual(page.number, 10)
        self.assertEqual(page.object_list.query.low_mark, 90)
        self.assertEqual(page.object_list.query.high_mark, 100)

    @patch("elasticsearch_dsl.Search.count", return_value=100)
    def test_get_page_from_search_es_wrong_limit(self, mock_es_count):
        for limit in self.wrong_limits:
            page = helpers.get_page_from_search(self.es_search, {"limit": limit})
            self.assertEqual(page.paginator.num_pages, 10)
            self.assertEqual(page.number, 1)
            self.assertEqual(page.object_list.to_dict(), {"from": 0, "size": 10})

    @patch("django.db.models.query.QuerySet.count", return_value=100)
    def test_get_page_from_search_orm_wrong_limit(self, mock_orm_count):
        for limit in self.wrong_limits:
            page = helpers.get_page_from_search(self.orm_query_set, {"limit": limit})
            self.assertEqual(page.paginator.num_pages, 10)
            self.assertEqual(page.number, 1)
            self.assertEqual(page.object_list.query.low_mark, 0)
            self.assertEqual(page.object_list.query.high_mark, 10)
