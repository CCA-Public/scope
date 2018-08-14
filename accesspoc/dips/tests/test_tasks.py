from django.test import TestCase
from unittest.mock import patch, Mock

from dips.models import DIP
from dips.tasks import extract_and_parse_mets, MetsTask


class TasksTests(TestCase):
    fixtures = ['index_data']

    @patch('dips.tasks.zipfile.ZipFile.infolist', return_value=[])
    @patch('dips.tasks.zipfile.ZipFile.__init__', return_value=None)
    def test_extract_and_parse_mets_not_found(self, patch_1, patch_2):
        with self.assertRaises(Exception):
            extract_and_parse_mets(1, '/DIP.zip')

    @patch('dips.tasks.METS.parse_mets')
    @patch('dips.tasks.METS.__init__', return_value=None)
    @patch('dips.tasks.zipfile.ZipFile.extract', return_value='/mets.xml')
    @patch('dips.tasks.zipfile.ZipFile.infolist', return_value=[
        Mock(filename='METS.ab028cb0-9942-4f26-a966-7197d7a2e15a.xml'),
    ])
    @patch('dips.tasks.zipfile.ZipFile.__init__', return_value=None)
    def test_extract_and_parse_mets_found(self, patch_1, patch_2, patch_3, mock_1, mock_2):
        extract_and_parse_mets(1, '/DIP.zip')
        mock_1.assert_called_with('/mets.xml', 1)
        mock_2.assert_called()

    @patch('dips.models.DigitalFile.save')
    @patch('elasticsearch_dsl.DocType.save')
    def test_mets_task_after_return(self, patch, mock):
        task = MetsTask()
        task.after_return(
            status='SUCCESS',
            retval=None,
            task_id=None,
            args=(1, '/mets.xml'),
            kwargs=None,
            einfo=None,
        )
        task.after_return(
            status='REVOKED',
            retval=None,
            task_id=None,
            args=(2, '/mets.xml'),
            kwargs=None,
            einfo=None,
        )
        # Rare case where the status is not a READY state,
        # it should not update the related resources.
        task.after_return(
            status='RETRY',
            retval=None,
            task_id=None,
            args=(1, '/mets.xml'),
            kwargs=None,
            einfo=None,
        )
        # DIP import_status should be updated
        dip_1 = DIP.objects.get(pk=1)
        dip_2 = DIP.objects.get(pk=2)
        self.assertEqual(dip_1.import_status, DIP.IMPORT_SUCCESS)
        self.assertEqual(dip_2.import_status, DIP.IMPORT_FAILURE)
        # All DigitalFile descendants should be saved
        self.assertEqual(mock.call_count, 12)
