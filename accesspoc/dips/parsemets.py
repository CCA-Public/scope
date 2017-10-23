import collections
import datetime
import fnmatch
import math
import os
import sys
from lxml import etree, objectify

from .models import DIP, DigitalFile, PREMISEvent

def convert_size(size):
    # convert size to human-readable form
    size_name = ("bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size,1024)))
    p = math.pow(1024,i)
    s = round(size/p)
    s = str(s)
    s = s.replace('.0', '')
    return '{} {}'.format(s,size_name[i])

class METS(object):
    """
    Class for METS file parsing methods
    """

    def __init__(self, path, dip_id):
        self.path = os.path.abspath(path)
        self.dip_id = dip_id

    def __str__(self):
        return self.path

    def parse_mets(self):
        """
        Parse METS file and save data to DIP, DigitalFile, and PremisEvent models
        """
        # open xml file and strip namespaces
        tree = etree.parse(self.path)
        root = tree.getroot()

        for elem in root.getiterator():
            if not hasattr(elem.tag, 'find'): continue  # (1)
            i = elem.tag.find('}')
            if i >= 0:
                elem.tag = elem.tag[i+1:]
        objectify.deannotate(root, cleanup_namespaces=True)

        # create dict for names and xpaths of desired info from individual files
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
            'fits_modified': './techMD/mdWrap/xmlData/object/objectCharacteristics/objectCharacteristicsExtension/fits/toolOutput/tool[@name="Exiftool"]/exiftool/FileModifyDate'
            }

        # build xml document root
        mets_root = root

        # gather info for each file in filegroup "original"
        for target in mets_root.findall(".//fileGrp[@USE='original']/file"):

            # create new dictionary for this item's info
            file_data = dict()

            # create new list of dicts for premis events in file_data
            file_data['premis_events'] = list()

            # gather amdsec id from filesec
            amdsec_id = target.attrib['ADMID']
            file_data['amdsec_id'] = amdsec_id
                
            # parse amdSec 
            amdsec_xpath = ".//amdSec[@ID='{}']".format(amdsec_id)
            for target1 in mets_root.findall(amdsec_xpath):
                
                # iterate over elements and write key, value for each to file_data dictionary
                for key, value in xml_file_elements.items():
                    try:
                        file_data['{}'.format(key)] = target1.find(value).text
                    except AttributeError:
                        file_data['{}'.format(key)] = ''

                # parse premis events related to file
                premis_event_xpath = ".//digiprovMD/mdWrap[@MDTYPE='PREMIS:EVENT']"
                for target2 in target1.findall(premis_event_xpath):

                    # create dict to store data
                    premis_event = dict()

                    # create dict for names and xpaths of desired elements
                    premis_key_values = {
                        'event_uuid': './xmlData/event/eventIdentifier/eventIdentifierValue', 
                        'event_type': '.xmlData/event/eventType', 
                        'event_datetime': './xmlData/event/eventDateTime', 
                        'event_detail': './xmlData/event/eventDetail', 
                        'event_outcome': './xmlData/event/eventOutcomeInformation/eventOutcome', 
                        'event_detail_note': './xmlData/event/eventOutcomeInformation/eventOutcomeDetail/eventOutcomeDetailNote'
                    }

                    # iterate over elements and write key, value for each to premis_event dictionary
                    for key, value in premis_key_values.items():
                        try:
                            premis_event['{}'.format(key)] = target2.find(value).text
                        except AttributeError:
                            premis_event['{}'.format(key)] = ''

                    # write premis_event dict to file_data
                    file_data['premis_events'].append(premis_event)

            # format filepath
            file_data['filepath'] = file_data['filepath'].replace('%transferDirectory%', '')

            # create human-readable size
            file_data['bytes'] = int(file_data['bytes'])
            file_data['size'] = '0 bytes' # default to none
            if file_data['bytes'] != 0:
                file_data['size'] = convert_size(file_data['bytes'])

            # create human-readable version of last modified Unix time stamp (if file was characterized by FITS)
            if file_data['fits_modified_unixtime']:
                unixtime = int(file_data['fits_modified_unixtime'])/1000 # convert milliseconds to seconds
                file_data['modified_ois'] = datetime.datetime.fromtimestamp(unixtime).isoformat() # convert from unix to iso8601
            else:
                file_data['modified_ois'] = ''

            # add file_data to DigitalFile model
            digitalfile = DigitalFile(uuid=file_data['uuid'], filepath=file_data['filepath'], 
                fileformat=file_data['format'], formatversion=file_data['version'], 
                size_bytes=file_data['bytes'], size_human=file_data['size'], 
                datemodified=file_data['modified_ois'], puid=file_data['puid'], 
                amdsec=file_data['amdsec_id'], hashtype=file_data['hashtype'], 
                hashvalue=file_data['hashvalue'], dip=DIP.objects.get(identifier=self.dip_id))
            digitalfile.save()

            # add premis events data to PREMISEvent model
            for event in file_data['premis_events']:
                premisevent = PREMISEvent(uuid=event['event_uuid'], eventtype=event['event_type'], 
                    datetime=event['event_datetime'], detail=event['event_detail'], 
                    outcome=event['event_outcome'], detailnote=event['event_detail_note'], 
                    digitalfile=DigitalFile.objects.get(uuid=file_data['uuid']))
                premisevent.save()

        # gather and save descriptive metadata from dmdsec
        for target in mets_root.findall('.//dmdSec/mdWrap[@MDTYPE="DC"]'): #TODO: use only most recently updated, if exists

            # create dict to store data
            dip_dmd = dict()

            # create dict for names and xpaths of desired elements
            dmdsec_dc_elements = {
                        'identifier': './xmlData/dublincore/identifier', 
                        'ispartof': './xmlData/dublincore/isPartof', 
                        'title': './xmlData/dublincore/title', 
                        'creator': './xmlData/dublincore/creator', 
                        'subject': './xmlData/dublincore/subject', 
                        'description': './xmlData/dublincore/description',
                        'publisher': './xmlData/dublincore/publisher', 
                        'contributor': './xmlData/dublincore/contributor', 
                        'date': './xmlData/dublincore/date', 
                        'dctype': './xmlData/dublincore/type', 
                        'dcformat': './xmlData/dublincore/format', 
                        'source': './xmlData/dublincore/source', 
                        'language': './xmlData/dublincore/language', 
                        'coverage': './xmlData/dublincore/coverage', 
                        'rights': './xmlData/dublincore/rights'
                    }

            # iterate over elements and write key, value for each to dip_dmd dictionary
            for key, value in dmdsec_dc_elements.items():
                try:
                    dip_dmd['{}'.format(key)] = target.find(value).text
                except AttributeError:
                    dip_dmd['{}'.format(key)] = ''

            # update DIP model object - not ispartof (hardset)
            dip = DIP.objects.get(identifier=self.dip_id)
            dip.title = dip_dmd['title']
            dip.creator = dip_dmd['creator']
            dip.subject = dip_dmd['subject']
            dip.description = dip_dmd['description']
            dip.publisher = dip_dmd['publisher']
            dip.contributor = dip_dmd['contributor']
            dip.date = dip_dmd['date']
            dip.dctype = dip_dmd['dctype']
            dip.dcformat = dip_dmd['dcformat']
            dip.source = dip_dmd['source']
            dip.language = dip_dmd['language']
            dip.coverage = dip_dmd['coverage']
            dip.rights = dip_dmd['rights']
            dip.save()

