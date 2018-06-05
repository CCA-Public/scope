import datetime
import math
import os
from lxml import etree, objectify

from .models import DIP, DigitalFile, PREMISEvent


def convert_size(size):
    # Convert size to human-readable form
    size_name = ("bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p)
    s = str(s)
    s = s.replace('.0', '')
    return '{} {}'.format(s, size_name[i])


class METS(object):
    """
    Class for METS file parsing methods
    """

    def __init__(self, path, dip_id):
        self.path = os.path.abspath(path)
        self.dip_id = dip_id

    def __str__(self):
        return self.path

    def parse_dc(self, root):
        """
        Parse SIP-level Dublin Core metadata into dc_model dictionary.
        Based on parse_dc function from Archivematica parse_mets_to_db.py script:

        https://github.com/artefactual/archivematica/blob/92d7abd238585e64e6064bc3f1ddfc663c4d3ace/
        src/MCPClient/lib/clientScripts/parse_mets_to_db.py
        """
        # Parse DC
        dmds = root.xpath('dmdSec/mdWrap[@MDTYPE="DC"]/parent::*')
        dc_model = dict()

        # Find which DC to parse
        if len(dmds) > 0:
            # Want most recently updated
            dmds = sorted(dmds, key=lambda e: e.get('CREATED'))
            # Only want SIP DC, not file DC
            div = root.find('structMap/div/div[@TYPE="Directory"][@LABEL="objects"]')
            dmdids = div.get('DMDID')
            # No SIP DC
            if dmdids is None:
                return
            dmdids = dmdids.split()
            for dmd in dmds[::-1]:  # Reversed
                if dmd.get('ID') in dmdids:
                    dc_xml = dmd.find('mdWrap/xmlData/dublincore')
                    break
            for elem in dc_xml:
                tag = elem.tag
                dc_model['%s' % (tag)] = elem.text
            print('Dublin Core:', dc_model)
            return dc_model

    def parse_mets(self):
        """
        Parse METS file and save data to DIP, DigitalFile, and PremisEvent models
        """
        # Open xml file and strip namespaces
        tree = etree.parse(self.path)
        root = tree.getroot()

        for elem in root.getiterator():
            if not hasattr(elem.tag, 'find'):
                continue  # (1)
            i = elem.tag.find('}')
            if i >= 0:
                elem.tag = elem.tag[i + 1:]
        objectify.deannotate(root, cleanup_namespaces=True)

        # Create dict for names and xpaths of desired info from individual files
        xml_file_elements = {
            'filepath': './techMD/mdWrap/xmlData/object/originalName',
            'uuid': './techMD/mdWrap/xmlData/object/objectIdentifier/objectIdentifierValue',
            'hashtype': './techMD/mdWrap/xmlData/object/objectCharacteristics/fixity/messageDigestAlgorithm',
            'hashvalue': './techMD/mdWrap/xmlData/object/objectCharacteristics/fixity/messageDigest',
            'bytes': './techMD/mdWrap/xmlData/object/objectCharacteristics/size',
            'format': './techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatDesignation/formatName',
            'version': './techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatDesignation/formatVersion',
            'puid': './techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatRegistry/formatRegistryKey',
            'fits_modified_unixtime': './techMD/mdWrap/xmlData/object/objectCharacteristics/objectCharacteristicsExtension/fits/fileinfo/fslastmodified[@toolname="OIS File Information"]',
            'fits_modified': './techMD/mdWrap/xmlData/object/objectCharacteristics/objectCharacteristicsExtension/fits/toolOutput/tool[@name="Exiftool"]/exiftool/FileModifyDate',
        }

        # Build xml document root
        mets_root = root

        # Gather info for each file in filegroup "original"
        for target in mets_root.findall(".//fileGrp[@USE='original']/file"):

            # Create new dictionary for this item's info
            file_data = dict()

            # Create new list of dicts for premis events in file_data
            file_data['premis_events'] = list()

            # Gather amdsec id from filesec
            amdsec_id = target.attrib['ADMID']
            file_data['amdsec_id'] = amdsec_id

            # Parse amdSec
            amdsec_xpath = ".//amdSec[@ID='{}']".format(amdsec_id)
            for target1 in mets_root.findall(amdsec_xpath):
                # Iterate over elements and write key, value for each to file_data dictionary
                for key, value in xml_file_elements.items():
                    try:
                        file_data['{}'.format(key)] = target1.find(value).text
                    except AttributeError:
                        file_data['{}'.format(key)] = ''

                # Parse premis events related to file
                premis_event_xpath = ".//digiprovMD/mdWrap[@MDTYPE='PREMIS:EVENT']"
                for target2 in target1.findall(premis_event_xpath):

                    # Create dict to store data
                    premis_event = dict()

                    # Create dict for names and xpaths of desired elements
                    premis_key_values = {
                        'event_uuid': './xmlData/event/eventIdentifier/eventIdentifierValue',
                        'event_type': '.xmlData/event/eventType',
                        'event_datetime': './xmlData/event/eventDateTime',
                        'event_detail': './xmlData/event/eventDetail',
                        'event_outcome': './xmlData/event/eventOutcomeInformation/eventOutcome',
                        'event_detail_note': './xmlData/event/eventOutcomeInformation/eventOutcomeDetail/eventOutcomeDetailNote',
                    }

                    # Iterate over elements and write key, value for each to premis_event dictionary
                    for key, value in premis_key_values.items():
                        try:
                            premis_event['{}'.format(key)] = target2.find(value).text
                        except AttributeError:
                            premis_event['{}'.format(key)] = ''

                    # Write premis_event dict to file_data
                    file_data['premis_events'].append(premis_event)

            # Format filepath
            file_data['filepath'] = file_data['filepath'].replace('%transferDirectory%', '')

            # Create human-readable size
            file_data['bytes'] = int(file_data['bytes'])
            file_data['size'] = '0 bytes'  # Default to none
            if file_data['bytes'] != 0:
                file_data['size'] = convert_size(file_data['bytes'])

            # Create human-readable version of last modified Unix time stamp (if file was characterized by FITS)
            if file_data['fits_modified_unixtime']:
                unixtime = int(file_data['fits_modified_unixtime']) / 1000  # convert milliseconds to seconds
                file_data['modified_ois'] = datetime.datetime.fromtimestamp(unixtime).isoformat()  # convert from unix to iso8601
            else:
                file_data['modified_ois'] = ''

            # Add file_data to DigitalFile model
            digitalfile = DigitalFile(
                uuid=file_data['uuid'], filepath=file_data['filepath'],
                fileformat=file_data['format'], formatversion=file_data['version'],
                size_bytes=file_data['bytes'], size_human=file_data['size'],
                datemodified=file_data['modified_ois'], puid=file_data['puid'],
                amdsec=file_data['amdsec_id'], hashtype=file_data['hashtype'],
                hashvalue=file_data['hashvalue'], dip=DIP.objects.get(identifier=self.dip_id),
            )
            digitalfile.save()

            # Add premis events data to PREMISEvent model
            for event in file_data['premis_events']:
                premisevent = PREMISEvent(
                    uuid=event['event_uuid'], eventtype=event['event_type'],
                    datetime=event['event_datetime'], detail=event['event_detail'],
                    outcome=event['event_outcome'], detailnote=event['event_detail_note'],
                    digitalfile=DigitalFile.objects.get(uuid=file_data['uuid']),
                )
                premisevent.save()

        # Gather dublin core metadata from most recent dmdSec
        dc_model = self.parse_dc(root)

        # Update DIP model object - not ispartof (hardset)
        if dc_model:
            dip = DIP.objects.get(identifier=self.dip_id)
            if 'title' in dc_model and dc_model['title'] is not None:
                dip.title = dc_model['title']
            if 'creator' in dc_model and dc_model['creator'] is not None:
                dip.creator = dc_model['creator']
            if 'subject' in dc_model and dc_model['subject'] is not None:
                dip.subject = dc_model['subject']
            if 'description' in dc_model and dc_model['description'] is not None:
                dip.description = dc_model['description']
            if 'publisher' in dc_model and dc_model['publisher'] is not None:
                dip.publisher = dc_model['publisher']
            if 'contributor' in dc_model and dc_model['contributor'] is not None:
                dip.contributor = dc_model['contributor']
            if 'date' in dc_model and dc_model['date'] is not None:
                dip.date = dc_model['date']
            if 'type' in dc_model and dc_model['type'] is not None:
                dip.dctype = dc_model['type']
            if 'format' in dc_model and dc_model['format'] is not None:
                dip.dcformat = dc_model['format']
            if 'source' in dc_model and dc_model['source'] is not None:
                dip.source = dc_model['source']
            if 'language' in dc_model and dc_model['language'] is not None:
                dip.language = dc_model['language']
            if 'coverage' in dc_model and dc_model['coverage'] is not None:
                dip.coverage = dc_model['coverage']
            if 'rights' in dc_model and dc_model['rights'] is not None:
                dip.rights = dc_model['rights']
            dip.save()
