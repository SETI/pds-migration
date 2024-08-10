##########################################################################################
# jnojir_index.py
##########################################################################################
"""\
This program re-formats the content of a JNOJIR index file in a standard, consistent
format for the RMS node's PDS3 holdings/metadata tree.

To use:
    > python jnojir_index.py path/to/index.tab ...

The file path can be to either an original INDEX.TAB file or to a v1.0 index in the
metadata tree. The output file is written into the metadata tree with the correct
subdirectory and name. If a file of that name is already present and there is no backup,
the existing file is renamed with the ending "-backup.tab".

This program does not correct any information that is incorrect in the existing index!
It also does not write a label.
"""

import os
import re
import shutil
import sys

import julian

# This is a regular expression that matches any time field
ISODATE_REGEX = re.compile(r'("?20\d\d-\d+-?\d*T?\d*:?\d*:?\d*\.?\d*)')

# This is a regular expression selecting the volume ID out of the directory path
VOLUME_ID_REGEX = re.compile(r'(.*?)(JNOJIR_\d\d\d\d)')

# Indices of the columns
# The header & label identify the first column as VOLUME_ID but it's really PRODUCT_TYPE,
# while VOLUME_ID is missing from each row. These are the columns for output; the
# delivered INDEX.TAB files start with PRODUCT_ID.
VOLUME_ID                 = 0
PRODUCT_TYPE              = 1
STANDARD_DATA_PRODUCT_ID  = 2
DATA_SET_ID               = 3
PRODUCT_ID                = 4
START_TIME                = 5
STOP_TIME                 = 6
FILE_SPECIFICATION_NAME   = 7
PRODUCT_CREATION_TIME     = 8
PRODUCT_LABEL_MD5CHECKSUM = 9

# The number of characters in each string
LENGTHS = [11, 3, 9, 22, 34, 23, 23, 43, 19, 32]

def write_jnojir_index(filepath):

    # Read the input index
    with open(filepath) as f:
        recs = f.readlines()

    # Identify the volume ID from the directory path
    prefix, volume_id = VOLUME_ID_REGEX.match(filepath).groups()

    # Identify the output file and optional backup
    output_file = (prefix.replace('volumes', 'metadata') + volume_id + '/'
                   + volume_id + '_index.tab')
    backup_file = output_file[:-4] + '-backup.tab'

    # Check the delivered INDEX.TAB vs. a pre-existing metadata file
    index_is_original = filepath.upper().endswith('/INDEX.TAB')
    if index_is_original:
        recs = recs[1:]     # skip header

    # Create a parent directory if necessary
    parent = os.path.split(output_file)[0]
    os.makedirs(parent, exist_ok=True)

    # Make a backup if necessary
    if os.path.exists(output_file) and not os.path.exists(backup_file):
        shutil.move(output_file, backup_file)

    # Open the output file
    f = open(output_file, 'wb')     # use binary write to suppress <cr><lf> handling

    # Loop through the records...
    for rec in recs:

        # Because the time fields are un-quoted, we need to quote them before the next
        # step. re.split() alternates between the fields between non-dates and dates.
        parts = ISODATE_REGEX.split(rec)
        for k, part in enumerate(parts):
            if k%2 == 1:
                if part[0] != '"':      # if not already quoted
                    parts[k] = '"' + part + '"'
        rec = ''.join(parts)

        # Now we can interpret the record as Python values
        values = list(eval(rec))

        # If the file is an original INDEX.TAB, insert the volume ID in front
        if index_is_original:
            values = [volume_id] + values

        # Otherwise, insert the product type second if it's not there
        elif len(values) < len(LENGTHS):
            product_type = 'EDR' if '_1' in volume_id else 'RDR'
            values = [values[0], product_type] + values[1:]

        # Change yyyy-doy to yyyy-mm-dd in all dates
        for k in (START_TIME, STOP_TIME, PRODUCT_CREATION_TIME):
            date, _, time = values[k].partition('T')
            if len(date) == 8:
                year = int(date[:4])
                doy = int(date[5:])
                ymd = julian.ymd_from_day(julian.day_from_yd(year, doy))
                values[k] = '%d-%02d-%02dT' % ymd + time

        # Early versions of INDEX.TAB have creation times ending in extraneous ".000"
        if values[PRODUCT_CREATION_TIME].endswith('.000'):
            values[PRODUCT_CREATION_TIME] = values[PRODUCT_CREATION_TIME][:-4]

        # Adjust all string lengths and check
        for k,v in enumerate(values):
            v = v.rstrip().ljust(LENGTHS[k])
            values[k] = v
            if len(v) != LENGTHS[k]:
                print('Length overflow in', repr(v))
                print(values)
                f.close()

                # If a backup file exists, copy it back
                if os.path.exists(backup_file):
                    shutil.copy(backup_file, output_file)

                sys.exit(1)

        # Merge this back into a single record
        # Note that the join() only works because every column in the index is a string
        new_rec = '"' + '","'.join(values) + '"\r\n'

        # Write the new record
        f.write(new_rec.encode('latin8'))

    # Close the output file
    f.close()

##########################################################################################

if __name__ == '__main__':

    for filepath in sys.argv[1:]:
        print(filepath)
        write_jnojir_index(filepath)

##########################################################################################
