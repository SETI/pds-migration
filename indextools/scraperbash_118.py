#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 17 09:52:15 2023

@author: emiliesimpson
"""

import csv
import os

import argparse
from lxml import objectify


# This exception is raised when a LID belongs to a collection that is not
# a subdirectory within the bundle being scraped. 
class BadLID(Exception):
    
    'The LID does not contain an accepted collection term'
    pass


directory_path = ('/Users/emiliesimpson/holdingsdisk/pds4-holdings'
                  '/bundles/uranus_occs_earthbased/')
collection_term_dict = {}
bundle_file_paths = []
bundle_member_index = {}
collection_terms = []
fullpaths = []

ns = {'pds':'http://pds.nasa.gov/pds4/pds/v1',
      'cassini': 'http://pds.nasa.gov/pds4/mission/cassini/v1'}

bundle_name = directory_path.split('/')[-2]

# Not all bundle.xml files within a bundle contain the same bundle member
# entries, so we need to walk through all instances of bundle.xml.

for path, subdirs, files in os.walk(directory_path + '/'): 
    for file in files: 
        if file == 'bundle.xml': 
            bundle_file_paths.append(os.path.join(path, file))
                
    for bundle_file_path in bundle_file_paths: 
        bundle_file_root = (objectify.parse(bundle_file_path, 
                                      objectify.makeparser(remove_blank_text=True))
                                     .getroot())
          
        bundle_member_entries = bundle_file_root.findall('pds:Bundle_Member_Entry', 
                                                 namespaces=ns)
        
        # Some files may belong to a subset of collections while existing in a 
        # larger subdirectory. To ensure they get sorted into the proper entry
        # within the dictionary, we search for all available collection terms
        # within all files named bundle.xml. This ensures that files not
        # present in all subdirectories get sorted regardless of location.
        
        for bundle_member_entry in bundle_member_entries: 
            lid_whole = (bundle_member_entry.lid_reference
                                            .text
                                            .split(':'))
            collection_term = lid_whole[-1]
            if collection_term not in collection_terms: 
                collection_terms.append(collection_term)
                collection_term_dict[str(collection_term)] = ({
                     'Reference Type' : str(bundle_member_entry.reference_type), 
                     'Member Status' : str(bundle_member_entry.member_status)})
                
first_level_subdirectories = next(os.walk(directory_path))[1]

subdirectory = first_level_subdirectories[4]
fullpath = directory_path + subdirectory

term = 'browse'
subs = next(os.walk(fullpath + '/' + term))[2]
print(subs)
# =============================================================================
# for subdirectory in first_level_subdirectories: 
#     fullpath = directory_path + subdirectory
# =============================================================================
    
# =============================================================================
#     for root, dirs, files in os.walk(fullpath): 
#         for file in files: 
#             if file.endswith(('.xml', '.lblx')): 
#                 fullpaths.append(os.path.join(root, file))
#         break
# # Code is currently limited to the first 50 files for debugging and
# # development. When this code is fully developed, the cap will be removed,
# # which will scrape the entire bundle.
# 
# for fullpath in fullpaths:
#     lid_root = (objectify.parse(fullpath,
#                                objectify.makeparser(remove_blank_text=True))
#                                         .getroot())
#     lid = str(lid_root.Identification_Area.logical_identifier)
#     for term in collection_terms:
#         if lid.endswith(term):
#             bundle_member_index[lid] = (
#                 {'LID' : lid,
#                  'Reference Type' : collection_term_dict[term]['Reference Type'],
#                  'Member Status' : collection_term_dict[term]['Member Status'],
#                  'Path' : fullpath})
#         
#         elif not[term in lid for term in collection_terms]: 
#             raise BadLID
# =============================================================================
# =============================================================================
# with open('/Users/emiliesimpson/' \
#           'Desktop/' + bundle_name + '_indexed.csv',
#           mode='w') as index_csv: 
#     bundle_member_index_writer = csv.DictWriter(index_csv, 
#                             fieldnames=['LID',
#                                         'Reference Type',
#                                         'Member Status',
#                                         'Path'])
#     bundle_member_index_writer.writeheader()
#     for index in bundle_member_index:
#         bundle_member_index_writer.writerow(bundle_member_index[index])
# =============================================================================
        

# =============================================================================
# parser = argparse.ArgumentParser()
# parser.add_argument('directorypath', type=str, nargs=1,
#                 help = 'The path to the directory containing the bundles '
#                        'you wish to scrape.')
# 
# args = parser.parse_args()
# 
# create_bundle_member_index(args.directorypath[0])
# =============================================================================