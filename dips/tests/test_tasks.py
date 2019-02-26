from django.test import TestCase
from unittest.mock import patch, Mock

from dips.models import DIP, DigitalFile
from dips.tasks import (extract_and_parse_mets, MetsTask, update_es_descendants,
                        delete_es_descendants)


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

    @patch('dips.models.celery_app.send_task')
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
        self.assertEqual(mock.call_count, 2)

    def test_update_es_descendants_wrong_class(self):
        with self.assertRaises(Exception):
            update_es_descendants('DigitalFile', 1)

    @patch('dips.tasks.bulk', return_value=(1, []))
    @patch('dips.models.Collection.get_es_data_for_files')
    @patch('dips.models.DigitalFile.objects.filter')
    def test_update_es_descendants_collection(self, mock, mock_2, mock_3):
        update_es_descendants('Collection', 1)
        # The DigitalFiles should be filtered
        mock.assert_called_with(dip__collection__pk=1)
        # The Collection data should be obtained (actual
        # data is tested in `test_models_to_docs`)
        mock_2.assert_called()
        # It's hard to assert the bulk call parameters as the second
        # one is a generator so we'll only check that it has been called.
        mock_3.assert_called()

    @patch('dips.tasks.bulk', return_value=(1, []))
    @patch('dips.models.DIP.get_es_data_for_files')
    @patch('dips.models.DigitalFile.objects.filter')
    def test_update_es_descendants_dip(self, mock, mock_2, mock_3):
        update_es_descendants('DIP', 1)
        # The DigitalFiles should be filtered
        mock.assert_called_with(dip__pk=1)
        # The DIP data should be obtained (actual
        # data is tested in `test_models_to_docs`)
        mock_2.assert_called()
        # It's hard to assert the bulk call parameters as the second
        # one is a generator so we'll only check that it has been called.
        mock_3.assert_called()

    @patch('dips.tasks.logger.info')
    @patch('dips.tasks.bulk', return_value=(1, ['error_1', 'error_2']))
    def test_update_es_descendants_errors_logged(self, patch, mock):
        update_es_descendants('DIP', 1)
        self.assertEqual(mock.call_count, 5)

    def test_delete_es_descendants_wrong_class(self):
        with self.assertRaises(Exception):
            delete_es_descendants('DigitalFile', 1)

    @patch('elasticsearch.Elasticsearch.delete_by_query')
    def test_delete_es_descendants_collection(self, mock):
        indexes = '%s,%s' % (
            DIP.es_doc._index._name, DigitalFile.es_doc._index._name)
        body = {'query': {'match': {'collection.id': 1}}}
        delete_es_descendants('Collection', 1)
        mock.assert_called_with(index=indexes, body=body)

    @patch('elasticsearch.Elasticsearch.delete_by_query')
    def test_delete_es_descendants_dip(self, mock):
        indexes = DigitalFile.es_doc._index._name
        body = {'query': {'match': {'dip.id': 1}}}
        delete_es_descendants('DIP', 1)
        mock.assert_called_with(index=indexes, body=body)

    @patch('dips.tasks.logger.info')
    @patch('elasticsearch.Elasticsearch.delete_by_query',
           return_value={'total': 1, 'deleted': 1, 'failures': ['error']})
    def test_delete_es_descendants_errors_logged(self, patch, mock):
        delete_es_descendants('DIP', 1)
        self.assertEqual(mock.call_count, 4)
