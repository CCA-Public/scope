from django.test import TestCase

from dips import helpers
from dips.models import DigitalFile


class HelpersTests(TestCase):

    def test_add_if_not_empty(self):
        data = {}
        helpers.add_if_not_empty(data, 'a', 'value')
        helpers.add_if_not_empty(data, 'b', '')
        helpers.add_if_not_empty(data, 'c', [])
        helpers.add_if_not_empty(data, 'd', {})
        helpers.add_if_not_empty(data, 'e', ())
        helpers.add_if_not_empty(data, 'f', 0)
        self.assertEqual(data, {'a': 'value'})

    def test_convert_size(self):
        SIZES_SUCCESS = [
            (2947251846, '3 GB'),
            (343623, '336 KB'),
            (15460865296738292569, '13 EB'),
            (2342, '2 KB'),
            (678678234206125, '617 TB'),
            (47021265234, '44 GB'),
        ]
        SIZES_ERROR = [
            (0, ValueError),
            ('string_value', TypeError),
            ('47021265234', TypeError),
        ]
        for size, result in SIZES_SUCCESS:
            self.assertEqual(result, helpers.convert_size(size))
        for size, error in SIZES_ERROR:
            self.assertRaises(error, helpers.convert_size, size)

    def test_update_instance_from_dict(self):
        digitalfile = DigitalFile(uuid='fake_uuid')
        file_data = {
            'filepath': 'fake_path',
            'fileformat': 'fake_format',
            'formatversion': 'fake_version',
            'size_bytes': 'fake_size',
            'unknown_field': 'not_added_not_error',
        }
        digitalfile = helpers.update_instance_from_dict(digitalfile, file_data)
        # Update fields without throwing AttributeError for the
        # unknown field or ValueError for the size_bytes field.
        self.assertEqual(digitalfile.filepath, 'fake_path')
        self.assertEqual(digitalfile.fileformat, 'fake_format')
        self.assertEqual(digitalfile.formatversion, 'fake_version')
        self.assertEqual(digitalfile.size_bytes, 'fake_size')
