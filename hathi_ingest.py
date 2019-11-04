#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 15:53:38 2019

@author: tug76662
"""

import yaml
import glob
import os
import shutil
from zipfile import ZipFile
from datetime import datetime
import hashlib
import exiftool
from PIL import Image
import pytesseract

#
# LOCATION OF EXTERNAL UTILITY BINARIES
#
pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"
exiftool_bin = "/usr/local/bin/exiftool"

# 
# DIRECTORY STRUCTURE TO SCAN
# e.g.  /Volumes/Novel\ Database/Sci-Fi\ Round\ 2/Batch\ 5/SSFCBZ201808000043/TIFFs\ to\ OCR/SSFCBZ201808000043Y0001-farmerstran.tif
#
top_level_dirs = ["/Volumes/Novel Database/Sci Fi Round 1", "/Volumes/Novel Database/Sci-Fi Round 2"]
subdir_1 = "/Batch *"
subdir_2 = "/SSF*"
tif_dirs = ["/TIFFs to OCR/*.tif", "/Cover TIFFs/*.tif"]
# 
# DIRECTORY FOR GENERATED ARTIFACTS
#
working_dir = "/Users/tug76662/Documents/Python/ocr_text/"

#
# TOP LEVEL METADATA FOR ALL SCANS
#
scanner_user = "Temple University Libraries Metadata and Digitization Services"
scanner_make = "Fujitsu"
scanner_model = "fi-7460"

#f4-5c-89-b5-e3-ad:~ tug76662$ ls  /Volumes/Novel\ Database/
#20th Century Corpus	Sci Fi Round 1		Sci-Fi Round 2		Web Archives		desktop.ini
#f4-5c-89-b5-e3-ad:~ tug76662$ ls  /Volumes/Novel\ Database/Sci
#Sci Fi Round 1/ Sci-Fi Round 2/ 
#f4-5c-89-b5-e3-ad:~ tug76662$ ls  /Volumes/Novel\ Database/Sci\ Fi\ Round\ 1/
#Batch 1				Batch 2				Batch 3				Batch 4				Sci Fi Corpus Clean Txt Files
#f4-5c-89-b5-e3-ad:~ tug76662$ ls  /Volumes/Novel\ Database/Sci\ Fi\ Round\ 1/Batch\ 1/
#SSFCBZ201710000327	SSFCBZ201710000338	SSFCBZ201710000347	SSFCBZ201710000354	SSFCBZ201710000372	SSFCBZ201710000380	SSFCBZ201710000400	SSFCBZ201710000411
#SSFCBZ201710000330	SSFCBZ201710000341	...
#f4-5c-89-b5-e3-ad:~ tug76662$ ls  /Volumes/Novel\ Database/Sci\ Fi\ Round\ 1/Batch\ 1/SSFCBZ201710000327/
#Cover TIFFs	OCR Files	TIFFs to OCR
#f4-5c-89-b5-e3-ad:~ tug76662$ ls  /Volumes/Novel\ Database/Sci\ Fi\ Round\ 1/Batch\ 1/SSFCBZ201710000327/TIFFs\ to\ OCR/
#SSFCBZ201710000327Y0001-ballarddrowned.tif	SSFCBZ201710000327Y0033-ballarddrowned.tif	SSFCBZ201710000327Y0065-ballarddrowned.tif	SSFCBZ201710000327Y0097-ballarddrowned.tif	SSFCBZ201710000327Y0129-ballarddrowned.tif
#SSFCBZ201710000327Y0002-ballarddrowned.tif	SSFCBZ201710000327Y0034-ballarddrowned.tif	SSFCBZ201710000327Y0066-ballarddrowned.tif	SSFCBZ201710000327Y0098-ballarddrowned.tif	SSFCBZ201710000327Y0130-ballarddrowned.tif
#SSFCBZ201710000327Y0003-ballarddrowned.tif	...


for tld in top_level_dirs:
    for subdir1 in glob.glob(tld+subdir_1):
        for subdir2 in glob.glob(subdir1+subdir_2):
#           #
#           # START OF NEW BOOK HERE
#           #
            hathi_data = {}
            hathi_metadata_pulled = False
            scan_metadata = {}
            noid = os.path.split(subdir2)[-1]
            current_book_dir = working_dir+noid+"/"
            os.mkdir(current_book_dir)
            # PROCESS PAGES
            for subdir_3 in tif_dirs:
                for filepath in glob.glob(subdir2+subdir_3):
                    if hathi_metadata_pulled == False:
                        with exiftool.ExifTool(exiftool_bin) as et:
                            scan_metadata = et.get_metadata(filepath)
                            print(scan_metadata)
                        # PULL SCAN DATE FROM TIF TAGS AND FORMAT AS ISO8601 PER HATHI SPECS
                        date_time_str = scan_metadata['File:FileModifyDate']
                        date_time_obj = datetime.strptime(date_time_str, '%Y:%m:%d %H:%M:%S%z')
                        hathi_data['capture_date'] = datetime.isoformat(date_time_obj)
                        # OTHER TOP LEVEL METADATA
                        hathi_data['scanner_user'] = scanner_user
                        hathi_data['scanner_make'] = scanner_make
                        hathi_data['scanner_model'] = scanner_model
                        hathi_metadata_pulled = True # we won't update the metadata until the next novel
                        
                    ocr_text = pytesseract.image_to_string(Image.open(filepath))
    #                print(ocr_text)             
                    filename, file_extension = os.path.splitext(os.path.basename(filepath))
                    filenum = filename.split("Y")[-1].split('-')[0]
    
                    ocr_txtfilename = "{}0000{}.txt".format(current_book_dir,filenum)
                    # "OCR MUST be provided as one page of plain text UTF-8 per image", so force UTF-8 
                    with open(ocr_txtfilename, "w", encoding='utf-8') as outfile:
                        outfile.write(ocr_text)
                    ocr_tiffilename = "{}0000{}.tif".format(current_book_dir,filenum)
                    # "copy2() ... attempts to preserve file metadata"
                    shutil.copy2(filepath, ocr_tiffilename)
                    
            # DUMP METADATA
            with open(current_book_dir+'meta.yml', 'w') as outfile:
                yaml.dump(hathi_data, outfile)
            # GENERATE CHECKSUM 
            with open(current_book_dir+"checksum.md5", "w") as md5file:
                for fn in glob.glob(current_book_dir+"*"):
                    hash = hashlib.md5()
                    hash.update(open(fn, "rb").read())
                    md5sum = hash.hexdigest()
                    # "checksum.md5 MUST NOT contain a checksum for checksum.md5"
                    if os.path.split(fn)[-1].split('.')[-1] != "md5":
                        f = os.path.split(fn)[-1]                    
                        md5file.write("{} {}\n".format(md5sum, f))
            # CREATE ZIP
            with ZipFile(working_dir+noid+'.zip', 'w') as zipfile:
                for fn in glob.glob(current_book_dir+"*"):
                    zipfile.write(fn,os.path.basename(fn))
            break
        break
    break

#os.chdir("/mydir")

#
#

