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

    def __init__(self, path, dip_objectid):
        self.path = os.path.abspath(path)
        self.dip_objectid = dip_objectid

    def __str__(self):
        return self.path

    def parse_mets(self):
        """
        Parse METS file and return model object
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

        # store names and xpaths of desired info from individual files in tuples and convert to ordered dict
        xml_file_elements = (('filepath', './techMD/mdWrap/xmlData/object/originalName'),
                        ('uuid', './techMD/mdWrap/xmlData/object/objectIdentifier/objectIdentifierValue'), 
                        ('hashtype', './techMD/mdWrap/xmlData/object/objectCharacteristics/fixity/messageDigestAlgorithm'), 
                        ('hashvalue', './techMD/mdWrap/xmlData/object/objectCharacteristics/fixity/messageDigest'), 
                        ('bytes', './techMD/mdWrap/xmlData/object/objectCharacteristics/size'), 
                        ('format', './techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatDesignation/formatName'), 
                        ('version', './techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatDesignation/formatVersion'), 
                        ('puid', './techMD/mdWrap/xmlData/object/objectCharacteristics/format/formatRegistry/formatRegistryKey'), 
                        ('fits_modified_unixtime', './techMD/mdWrap/xmlData/object/objectCharacteristics/objectCharacteristicsExtension/fits/fileinfo/fslastmodified[@toolname="OIS File Information"]'), 
                        ('fits_modified', './techMD/mdWrap/xmlData/object/objectCharacteristics/objectCharacteristicsExtension/fits/toolOutput/tool[@name="Exiftool"]/exiftool/FileModifyDate'))
        xml_file_elements = collections.OrderedDict(xml_file_elements)

        # build xml document root
        mets_root = root

        # gather info for each file in filegroup "original"
        for target in mets_root.findall(".//fileGrp[@USE='original']/file"):

            # create new dictionary for this item's info
            file_data = {}

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
            file_data['size'] = convert_size(file_data['bytes'])

            # create human-readable version of last modified Unix time stamp (if file was characterized by FITS)
            if file_data['fits_modified_unixtime']:
                unixtime = int(file_data['fits_modified_unixtime'])/1000 # convert milliseconds to seconds
                file_data['modified_ois'] = datetime.datetime.fromtimestamp(unixtime).isoformat() # cconvert from unix to iso8601

            # add file_data to DigitalFile model
            digitalfile = DigitalFile(uuid=file_data['uuid'], filepath=file_data['filepath'], 
                fileformat=file_data['format'], formatversion=file_data['version'], 
                size_bytes=file_data['bytes'], size_human=file_data['size'], 
                datemodified=file_data['modified_ois'], puid=file_data['puid'], 
                amdsec=file_data['amdsec_id'], hashtype=file_data['hashtype'], 
                hashvalue=file_data['hashvalue'], dip=DIP.objects.get(objectid=self.dip_objectid))
            digitalfile.save()

            # add premis events data to PREMISEvent model
            for event in file_data['premis_events']:
                premisevent = PREMISEvent(uuid=event['event_uuid'], eventtype=event['event_type'], 
                    datetime=event['event_datetime'], detail=event['event_detail'], 
                    outcome=event['event_outcome'], detailnote=event['event_detail_note'], 
                    digitalfile=DigitalFile.objects.get(uuid=file_data['uuid']))
                premisevent.save()

