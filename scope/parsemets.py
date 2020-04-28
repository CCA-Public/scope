import os
from datetime import datetime
from datetime import timezone

from django.core.exceptions import ValidationError
from lxml import etree
from lxml import objectify

from .helpers import convert_size
from .helpers import update_instance_from_dict
from .models import DIP
from .models import Collection
from .models import DigitalFile
from .models import PREMISEvent


class METSError(Exception):
    """Exception raised when there is a problem in the METS parsing process"""


class METS:
    """Class for METS file parsing methods."""

    # Fields and xpaths for DigitalFile
    FILE_ELEMENTS = [
        ("filepath", "./techMD/mdWrap/xmlData/object/originalName"),
        (
            "uuid",
            "./techMD/mdWrap/xmlData/object/objectIdentifier/objectIdentifierValue",
        ),
        (
            "hashtype",
            "./techMD/mdWrap/xmlData/object/objectCharacteristics/fixity/messageDigestAlgorithm",
        ),
        (
            "hashvalue",
            "./techMD/mdWrap/xmlData/object/objectCharacteristics/fixity/messageDigest",
        ),
        ("size_bytes", "./techMD/mdWrap/xmlData/object/objectCharacteristics/size"),
        (
            "fileformat",
            "./techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatDesignation/formatName",
        ),
        (
            "formatversion",
            "./techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatDesignation/formatVersion",
        ),
        (
            "puid",
            "./techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatRegistry/formatRegistryKey",
        ),
        (
            "datemodified",
            './techMD/mdWrap/xmlData/object/objectCharacteristics/objectCharacteristicsExtension/fits/fileinfo/fslastmodified[@toolname="OIS File Information"]',
        ),
    ]
    # Fields and xpaths for PREMISEvent
    PREMIS_ELEMENTS = [
        ("uuid", "./xmlData/event/eventIdentifier/eventIdentifierValue"),
        ("eventtype", ".xmlData/event/eventType"),
        ("datetime", "./xmlData/event/eventDateTime"),
        ("detail", "./xmlData/event//eventDetail"),
        ("outcome", "./xmlData/event/eventOutcomeInformation/eventOutcome"),
        (
            "detailnote",
            "./xmlData/event/eventOutcomeInformation/eventOutcomeDetail/eventOutcomeDetailNote",
        ),
    ]

    def __init__(self, path, dip_id):
        self.path = os.path.abspath(path)
        self.dip_id = dip_id
        self.mets_root = self._get_mets_root()

    def _get_mets_root(self):
        """Open XML and return the root element with all namespaces stripped."""
        tree = etree.parse(self.path)
        root = tree.getroot()
        for elem in root.getiterator():
            if hasattr(elem.tag, "find"):
                i = elem.tag.find("}")
                if i >= 0:
                    elem.tag = elem.tag[i + 1 :]
        objectify.deannotate(root, cleanup_namespaces=True)
        return root

    def parse_mets(self):
        """Parse METS and save data to DIP, DigitalFile, and PremisEvent models."""
        # Get DIP object
        dip = DIP.objects.get(pk=self.dip_id)

        # Gather info for each file in filegroup "original"
        for file_ in self.mets_root.findall(".//fileGrp[@USE='original']/file"):
            amdsec_id = file_.get("ADMID")
            if not amdsec_id:
                continue

            file_data, premis_events = self._parse_file_metadata(amdsec_id)
            file_data = self._transform_file_metadata(file_data)

            # Check mandatory UUID field
            uuid = file_data.pop("uuid", None)
            if not uuid:
                raise METSError(
                    "An original file in this METS file is missing its UUID."
                )
            # Get existing DigitalFile by UUID
            try:
                digitalfile = DigitalFile.objects.get(uuid=uuid)
                # Don't update DigitalFile from other DIP
                if digitalfile.dip.pk != dip.pk:
                    raise METSError(
                        "An original file in this METS file has the same UUID "
                        "as an existing one from another DIP "
                        "(%s)." % uuid
                    )
            except DigitalFile.DoesNotExist:
                # Create DigitalFIle if it doesn't exist
                digitalfile = DigitalFile(uuid=uuid)
            # Add/update instance fields with file_data values
            digitalfile = update_instance_from_dict(digitalfile, file_data)
            digitalfile.dip = dip
            # Validate
            try:
                digitalfile.full_clean()
            except ValidationError as e:
                message = "A DigitalFile could not be created:"
                for field, errors in e.message_dict.items():
                    message += "\n- %s: %s" % (field, " ".join(errors))
                raise METSError(message)
            digitalfile.save()

            # Add premis events data to PREMISEvent model
            for event in premis_events:
                # Check mandatory UUID field
                uuid = event.pop("uuid", None)
                if not uuid:
                    raise METSError(
                        "A PREMISEvent in this METS file is missing its UUID."
                    )
                # Get existing PREMISEvent by UUID
                try:
                    premisevent = PREMISEvent.objects.get(uuid=uuid)
                    # Don't update PREMISEvent from other DigitalFile
                    if premisevent.digitalfile.uuid != digitalfile.uuid:
                        raise METSError(
                            "A PREMISEvent in this METS file has the same "
                            "UUID as an existing one from another DIP "
                            "(%s)." % uuid
                        )
                except PREMISEvent.DoesNotExist:
                    # Create PREMISEvent if it doesn't exist
                    premisevent = PREMISEvent(uuid=uuid)
                # Add/update instance fields with event values
                premisevent = update_instance_from_dict(premisevent, event)
                premisevent.digitalfile = digitalfile
                # Validate
                try:
                    premisevent.full_clean()
                except ValidationError as e:
                    message = "A PREMISEvent could not be created:"
                    for field, errors in e.message_dict.items():
                        message += "\n- %s: %s" % (field, " ".join(errors))
                    raise METSError(message)
                premisevent.save()

        # Gather Dublin Core metadata from most recent
        # dmdSec and update DIP DublinCore object.
        dc_data = self._parse_dc()
        if dc_data:
            # The `isPartOf` and `relation` values are only used to find a
            # related Collection, giving priority to the `isPartOf` value.
            is_part_of = dc_data.pop("isPartOf", None)
            relation = dc_data.pop("relation", None)
            if is_part_of:
                # Remove AIC prefix if present (added by AM)
                is_part_of = is_part_of.replace("AIC#", "")
            for collection_identifier in [is_part_of, relation]:
                if collection_identifier:
                    try:
                        # Until slugs are implemented the relation is made using
                        # the DC identifier from the collections, which is not
                        # an unique field.
                        dip.collection = Collection.objects.get(
                            dc__identifier=collection_identifier
                        )
                        dip.save(update_es=False)
                        # Stop loop after finding a match
                        break
                    except (
                        Collection.DoesNotExist,
                        Collection.MultipleObjectsReturned,
                    ):
                        pass

            # No validation is needed as all the fields are non
            # required string fields initiated with empty strings,
            # but do not update identifier with an empty value.
            if "identifier" in dc_data and not dc_data["identifier"]:
                dc_data.pop("identifier")
            dip.dc = update_instance_from_dict(dip.dc, dc_data)
            dip.dc.save()

        return dip

    def _parse_file_metadata(self, amdsec_id):
        """Parse file metadata into a dict and an events list."""
        # Create new dictionary for this item's info, including
        # the amdSec id, and new list of dicts for premis events.
        data = {"amdsec": amdsec_id}
        events = list()

        # Parse amdSec
        amdsec_xpath = ".//amdSec[@ID='{}']".format(amdsec_id)
        for amdsec in self.mets_root.findall(amdsec_xpath):
            # Iterate over elements and write key, value
            # for each to data dictionary.
            for key, xpath in self.FILE_ELEMENTS:
                try:
                    data[key] = amdsec.find(xpath).text
                except AttributeError:
                    data[key] = ""

            # Parse premis events related to file
            premis_event_xpath = ".//digiprovMD/mdWrap[@MDTYPE='PREMIS:EVENT']"
            for premis_event in amdsec.findall(premis_event_xpath):
                # Iterate over elements and write key, value
                # for each to event dictionary.
                event = dict()
                for key, xpath in self.PREMIS_ELEMENTS:
                    try:
                        event[key] = premis_event.find(xpath).text
                    except AttributeError:
                        event[key] = ""
                events.append(event)

        return (data, events)

    def _transform_file_metadata(self, data):
        """Transform file metadata to be saved in DigitalFile fields."""
        # Format filepath
        data["filepath"] = data["filepath"].replace("%transferDirectory%", "")

        # Create human-readable size
        data["size_bytes"] = int(data["size_bytes"])
        data["size_human"] = "0 bytes"
        if data["size_bytes"] != 0:
            data["size_human"] = convert_size(data["size_bytes"])

        # Transfrom timestamp. This timestamp comes from the FITS output,
        # `fits/fileinfo/fslastmodified[@toolname="OIS File Information"]`
        # element, and it seems to be an UTC timestamp.
        try:
            unixtime = int(data["datemodified"]) / 1000
            data["datemodified"] = datetime.fromtimestamp(unixtime, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            data["datemodified"] = None

        return data

    def _parse_dc(self):
        """Parse SIP-level Dublin Core metadata into dc_model dictionary.

        Based on `parse_dc` from Archivematica parse_mets_to_db.py script
        (src/MCPClient/lib/clientScripts/parse_mets_to_db.py).
        """
        # Find DMD sections and return if none is found
        xpath = 'dmdSec/mdWrap[@MDTYPE="DC"]/parent::*'
        dmds = self.mets_root.xpath(xpath)
        if len(dmds) == 0:
            return

        # Find SIP DMD ids, not file, and return if none is found
        xpath = 'structMap/div/div[@TYPE="Directory"][@LABEL="objects"]'
        divs = self.mets_root.find(xpath)
        dmdids = divs.get("DMDID")
        if dmdids is None:
            return

        # Sort by date and loop over reversed DMD sections, check SIP
        # DMD ids to get the last updated SIP's Dublin Core metadata.
        dmdids = dmdids.split()
        dmds = sorted(dmds, key=lambda e: e.get("CREATED", ""))
        for dmd in dmds[::-1]:
            if dmd.get("ID", "") in dmdids:
                dc_xml = dmd.find("mdWrap/xmlData/dublincore")
                if dc_xml is not None and len(dc_xml):
                    break

        # Parse all DC elements to a dictionary. Initiate all fields with
        # empty strings as no one can be null.
        dc_model = {
            "identifier": "",
            "title": "",
            "creator": "",
            "subject": "",
            "description": "",
            "publisher": "",
            "contributor": "",
            "date": "",
            "type": "",
            "format": "",
            "source": "",
            "language": "",
            "coverage": "",
            "rights": "",
            "isPartOf": "",
            "relation": "",
        }
        for elem in dc_xml:
            key = str(elem.tag)
            if key in dc_model and elem.text:
                dc_model[key] = str(elem.text)

        return dc_model
