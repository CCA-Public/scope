from celery import shared_task, states, Task
from django.db.utils import DatabaseError
from elasticsearch.exceptions import TransportError
from .parsemets import METS
from .models import DIP

import logging
import os
import re
import tempfile
import zipfile

# Use a normal logger to avoid redirecting both `stdout` and `stderr` to the
# logger and back when using Celery's `get_task_logger`, and to avoid changing
# the default `CELERY_REDIRECT_STDOUTS_LEVEL` when using `print`.
logger = logging.getLogger('dips.tasks')


class MetsTask(Task):

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Update DIP `import_status` when the task ends. Make sure it's one
        of Celery's READY_STATES and set it to 'FAILURE' for all possible
        non 'SUCCESS' states.
        """
        if status not in states.READY_STATES:
            return
        dip = DIP.objects.get(pk=args[0])
        logger.info('Updating DIP import status [Identifier: %s]' % dip.dc.identifier)
        if status == states.SUCCESS:
            dip.import_status = DIP.IMPORT_SUCCESS
        else:
            dip.import_status = DIP.IMPORT_FAILURE
        dip.save()
        # Update also related DigitalFiles in ES to reflect
        # the import status of the parent DIP.
        # TODO: Do it in signal or custom save method
        # using partial updates and ideally bulk requests.
        for digital_file in dip.digital_files.all():
            digital_file.save()


@shared_task(
    base=MetsTask, autoretry_for=(TransportError, DatabaseError,),
    max_retries=10, default_retry_delay=30,
)
def extract_and_parse_mets(dip_id, zip_path):
    """
    Extracts a METS file from a given DIP zip file and uses the METS class
    to parse its content, create the related DigitalFiles and update the DIP
    DC metadata. Creates and deletes a temporary directory to hold the METS
    file during its parsing. This function is meant to be called with
    `.delay()` to be executed asynchronously by the Celery worker.
    """
    logger.info('Extracting METS file from ZIP [Path: %s]' % zip_path)
    with tempfile.TemporaryDirectory() as dir_:
        with zipfile.ZipFile(zip_path) as zip_:
            # Extract METS file
            metsfile = None
            mets_re = re.compile(r'.*METS.[0-9a-f\-]{36}.*$')
            for info in zip_.infolist():
                if mets_re.match(info.filename):
                    metsfile = zip_.extract(info, dir_)
            if not metsfile:
                raise Exception('METS file not found in ZIP file.')
            # Parse METS file
            path = os.path.abspath(metsfile)
            logger.info('METS file extracted [Path: %s]' % path)
            mets = METS(path, dip_id)
            mets.parse_mets()
