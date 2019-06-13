from django.test import TestCase

from scope.models import DigitalFile
from search.helpers import (
    add_query_to_search,
    add_digital_file_aggs,
    add_digital_file_filters,
)


class FunctionsTests(TestCase):
    def setUp(self):
        self.search = DigitalFile.es_doc.search()
        self.query_fields = ["filepath", "fileformat"]

    def test_add_query_to_search_empty_query(self):
        modified_search = add_query_to_search(self.search, "", self.query_fields)
        self.assertTrue("query" not in modified_search.to_dict().keys())

    def test_add_query_to_search_whitespace_query(self):
        modified_search = add_query_to_search(self.search, "      ", self.query_fields)
        self.assertTrue("query" not in modified_search.to_dict().keys())

    def test_add_query_to_search_populated_query(self):
        query = "test_query"
        modified_search = add_query_to_search(self.search, query, self.query_fields)
        expected_search = {
            "query": {
                "simple_query_string": {
                    "query": query,
                    "default_operator": "and",
                    "fields": self.query_fields,
                }
            }
        }
        self.assertEqual(modified_search.to_dict(), expected_search)

    def test_add_digital_file_aggs_with_collections(self):
        modified_search = add_digital_file_aggs(self.search)
        expected_search = {
            "aggs": {
                "formats": {
                    "terms": {
                        "field": "fileformat.raw",
                        "size": 10000,
                        "order": {"_key": "asc"},
                    }
                },
                "collections": {
                    "terms": {
                        "field": "collection.title.raw",
                        "size": 10000,
                        "order": {"_key": "asc"},
                    }
                },
            }
        }
        self.assertEqual(modified_search.to_dict(), expected_search)

    def test_add_digital_file_aggs_without_collections(self):
        modified_search = add_digital_file_aggs(self.search, collections=False)
        expected_search = {
            "aggs": {
                "formats": {
                    "terms": {
                        "field": "fileformat.raw",
                        "size": 10000,
                        "order": {"_key": "asc"},
                    }
                }
            }
        }
        self.assertEqual(modified_search.to_dict(), expected_search)

    def test_add_digital_file_filters_none(self):
        modified_search = add_digital_file_filters(self.search, {})
        self.assertEqual(modified_search.to_dict(), {})

    def test_add_digital_file_filters_all(self):
        params = {
            "formats": ["format_a", "format_b"],
            "collections": ["collection_a", "collection_b"],
            "start_date": "2018-01-31",
            "end_date": "2018-12-31",
        }
        modified_search = add_digital_file_filters(self.search, params)
        expected_search = {
            "query": {
                "bool": {
                    "must": [
                        {"terms": {"fileformat.raw": params["formats"]}},
                        {"terms": {"collection.title.raw": params["collections"]}},
                        {
                            "range": {
                                "datemodified": {
                                    "gte": params["start_date"],
                                    "format": "yyyy-MM-dd",
                                }
                            }
                        },
                        {
                            "range": {
                                "datemodified": {
                                    "lte": params["end_date"],
                                    "format": "yyyy-MM-dd",
                                }
                            }
                        },
                    ]
                }
            }
        }
        self.assertEqual(modified_search.to_dict(), expected_search)

    def test_add_digital_file_filters_all_empty(self):
        params = {"formats": [], "collections": [], "start_date": "", "end_date": ""}
        modified_search = add_digital_file_filters(self.search, params)
        self.assertEqual(modified_search.to_dict(), {})
