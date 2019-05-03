import os
import re
import shutil
import zipfile

from celery import shared_task
from django.conf import settings
from django.db.utils import DatabaseError
from elasticsearch.exceptions import TransportError
import requests

from .parsemets import METS
from .models import DIP

METS_RE = re.compile(r".*METS.[0-9a-f\-]{36}.*$")


@shared_task(autoretry_for=(TransportError,), max_retries=10, default_retry_delay=30)
def download_mets(dip_id):
    """Downloads the DIP's METS file from the SS.

    TODO: Check both DIP types integration and add fallback method if needed.
    """
    # Check the SS host is still configured in the settings
    dip = DIP.objects.get(pk=dip_id)
    if dip.ss_host_url not in settings.SS_HOSTS.keys():
        raise RuntimeError("Configuration not found for SS host: %s" % dip.ss_host_url)
    # We should have the full DIP download URL, but we'll try to download
    # only the METS file before. Build package info URL:
    info_url = "%s/api/v2/file/%s?format=json" % (dip.ss_host_url, dip.ss_uuid)
    headers = {
        "Authorization": "ApiKey %s:%s"
        % (
            settings.SS_HOSTS[dip.ss_host_url]["user"],
            settings.SS_HOSTS[dip.ss_host_url]["secret"],
        )
    }
    response = requests.get(info_url, headers=headers, timeout=5)
    # TODO: Do not raise if a fallback method is implemented
    response.raise_for_status()
    data = response.json()
    # At this point the `related_packages` may be empty in the
    # DIP information because the AIP has not been stored yet.
    # Nevertheless, we need the AIP UUID to download the METS
    # file only. This UUID can be obtained from the DIP current
    # path, but that may not always be true in the future.
    current_path = data["current_path"]
    dip_dir = os.path.basename(current_path)
    aip_uuid = dip_dir[-36:]
    # Save DIP directory name to form the filename for downloads
    dip.ss_dir_name = dip_dir
    dip.save(update_es=False)
    # Stream METS file to media folder
    mets_url = (
        "%s/api/v2/file/%s/extract_file/?relative_path_to_file=%s/METS.%s.xml"
        % (dip.ss_host_url, dip.ss_uuid, dip_dir, aip_uuid)
    )
    mets_path = os.path.abspath(
        os.path.join(settings.MEDIA_ROOT, "METS.%s.xml" % dip.ss_uuid)
    )
    with requests.get(mets_url, headers=headers, stream=True) as response:
        # TODO: Do not raise if a fallback method is implemented
        response.raise_for_status()
        with open(mets_path, "wb") as mets_file:
            shutil.copyfileobj(response.raw, mets_file)
    return mets_path


@shared_task()
def extract_mets(zip_path, delete_zip=False):
    """Extracts a METS file from a given zip file to the media folder.

    Deletes the ZIP file if the METS file is not found or based on the
    `delete_zip` parameter. Raises `Exception` if the METS file is not
    found or returns the absolute path to the extracted file.
    """
    metsfile = None
    with zipfile.ZipFile(zip_path) as zip_:
        for info in zip_.infolist():
            if METS_RE.match(info.filename):
                info.filename = os.path.basename(info.filename)
                metsfile = zip_.extract(info, settings.MEDIA_ROOT)

    if not metsfile or delete_zip:
        os.remove(zip_path)

    if not metsfile:
        raise FileNotFoundError("METS file not found in ZIP file.")

    path = os.path.abspath(metsfile)
    return path


@shared_task(
    autoretry_for=(TransportError, DatabaseError),
    max_retries=10,
    default_retry_delay=30,
)
def parse_mets(mets_path, dip_id):
    """Parses a METS file updating a DIP and creating the children DigitalFiles.

    Deletes the METS file and marks the import as finished as it's the last task
    in both imports processes.
    """
    try:
        mets = METS(mets_path, dip_id)
        dip = mets.parse_mets()
        dip.import_status = DIP.IMPORT_SUCCESS
        dip.save()
    finally:
        # Remove METS file on error too
        os.remove(mets_path)


@shared_task()
def save_import_error(request, exc, traceback, dip_id):
    """Update DIP when any of the import tasks fail."""
    dip = DIP.objects.get(pk=dip_id)
    dip.import_status = DIP.IMPORT_FAILURE
    dip.import_error = str(exc)
    dip.save()
