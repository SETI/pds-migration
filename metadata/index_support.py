################################################################################
# index_support.py
################################################################################
import os, time
import glob as glb
import hosts.pds3 as pds3
import pdsparser
import fortranformat as ff
import fnmatch
import warnings

import metadata as meta
import index_config as config
import pdstable

from pathlib import Path
from pdstemplate import PdsTemplate

################################################################################
# Built-in key functions
################################################################################

#===============================================================================
def key__volume_id(label_path, label_dict):
    """Key function for VOLUME_ID.

    Inputs:
        label_path        path to the PDS label.
        label_dict        dictionary containing the PDS label fields.

    The return value will appear in the index file under VOLUME_ID.
    """
    return config.get_volume_id(label_path)

#===============================================================================
def key__file_specification_name(label_path, label_dict):
    """Key function for FILE_SPECIFICATION_NAME.

    Inputs:
        label_path        path to the PDS label.
        label_dict        dictionary containing the PDS label fields.

    The return value will appear in the index file under FILE_SPECIFICATION_NAME.
    """
    return _get_subdir(label_path)
    

################################################################################
# internal functions
################################################################################

#===============================================================================
def _format_value(value, format):
    """Format a single value using a Fortran format code.

    Inputs:
        value         value to format.
        format        FORTRAN_style format code.
        
    Outputs:          formatted value.
    """
    
    # format value
    line = ff.FortranRecordWriter('(' + format + ')')
    result = line.write([value])

    # add double quotes to string formats
    if format[0] == 'A':
        result = '"' + result + '"'
    
    return result

#===============================================================================
def _format_parms(format):
    """Determine len and type corresopnding to a given FORTRAN format code..

    Inputs:
        format        FORTRAN_style format code.
        
    Output:           (width, data_type)
        width         number of bytes required for a formatted value, including
                      any quotes.
        data_type     data type corresponding to the format code.
    """
    
    data_types = {'A':'CHARACTER', 
                  'E':'ASCII_REAL', 
                  'F':'ASCII_REAL', 
                  'I':'ASCII_INTEGER'}
    try:
        f = _format_value('0', format)
    except TypeError:
        f = _format_value(0, format)

    width = len(f)
    data_type = data_types[format[0]]
    
    return (width, data_type)

#===============================================================================
def _format_column(value, name=None, 
                          count=None, 
                          nbytes=None, 
                          width=None, 
                          format=None, 
                          nullval=None, 
                          data_type=None, 
                          description=None):
    """Format a column.

    Inputs:
        value       value to format.       
        <keys>      fields of the column dictionary.
        
    Outputs:        formatted value.
    """

    # Split multiple elements into individual columns
    if count > 1:
        if not isinstance(value, (list,tuple)):
            assert value == nullval
            value = count * [nullval]
        else:
            assert len(value) == count

        fmt_list = []
        for item in value:
            result = _format_column(item, name=name, 
                                       count=1, 
                                       nbytes=nbytes, 
                                       width=width, 
                                       format=format, 
                                       nullval=nullval, 
                                       data_type=None, 
                                       description=description)
            fmt_list.append(result)
        return ','.join(fmt_list)

    # Clean up strings
    if isinstance(value, str):
        value = value.strip()
        value = value.replace('\n', ' ')
        while ('  ' in value):
            value = value.replace('  ', ' ')

    # Format the value
    if isinstance(value, str):
        value = value.replace('"', '')

    try:
        result = _format_value(value, format)
    except TypeError:
        print("**** WARNING: Invalid format: ", name, value, format)
        result = width * "*"

    if len(result) > width:
        print("**** WARNING: No second format: ", name, value, format, result)

    # Validate the formatted value
    try:
        test = eval(result)
    except Exception:
        print("**** WARNING: Eval failure: ", name, value, result)
        test = nullval
    else:
        if isinstance(test, str):
            test = test.rstrip()

# Values change when reformatted to a larger width, which is desired behavior
#    if test != value and test != nullval and test != str(value):
#        print("**** WARNING: Value has changed: ", name, value, format, result)

    return result

#===============================================================================
def _index_one_value(column_desc, label_path, label):
    """Determine value for one row of one column.

    Inputs:
        column_desc     column dictionary.
        label_path      path to the PDS label.
        
    Outputs:            determined value.
    """

    # Check for built-in key function
    key = column_desc['name']
    fn_name = 'key__' + key.lower()
    try:
        fn = globals()[fn_name]
        value = fn(label_path, label)

    # Check for key function in index_config module
    except KeyError:
        try:
            fn = getattr(config, fn_name)
            value = fn(label_path, label)

        # If no key function, just take the value from the label
        except AttributeError:
            value = label[key] if key in label else column_desc['nullval']

    return value

#===============================================================================
def _index_one_file(root, name, index, column_descs):
    """Write a single index file entry .

    Inputs:
        root          top of the directory tree containing the volume. 
        name          name of PDS label.
        index         open descriptor for the index file.
        column_descs  dictionary of columns descriptions
    """

    # Read the PDS3 label
    path = root/name
    label = pds3.get_label(path.as_posix())

    # Write columns
    first = True
    for name in column_descs:
        column_desc = column_descs[name]

        # Get the value
        value = _index_one_value(column_desc, path, label)

        # Write the value into the index
        if not first:
            index.write(",")
        fvalue = _format_column(value, **column_desc)
        index.write(fvalue)

        first = False

    index.write('\r\n')

#===============================================================================
def _get_volume_id(dir):
    """Determine the volume ID.

    Inputs:
        path          top dir for volume. 
        
    Outputs:          volume ID.
    """
    return config.get_volume_id(dir)

#===============================================================================
def _get_subdir(path):
    """Determine the Subdirectory of an input file.

    Inputs:
        path          input path or directory. 
        
    Outputs:          final directory in tree.
    """
    return meta.splitpath(path, _get_volume_id(path))[1]

#===============================================================================
def _get_index_name(dir, type):
    """Determine the name of the index file.
    
    Inputs:
        dir           top dir for volume. 
        type          index type. 
        
    Outputs:          index name.
    """   

    # Name starts with volume id
    dir = dir.absolute()
    name = _get_volume_id(dir)

    # Add type if given
    if type:
        name += '_' + type

    name += '_index'

    return name

#===============================================================================
def _get_template_name(type):
    """Determine the name of the label template.
    
    Inputs:
        dir           top dir for volume. 
        name          base name of the index file and label.  If None, it 
                      is derived from the volume id.
        type          index type. 
        
    Outputs:          index name.
    """   

    # Name starts with collection id
    dir = Path.cwd()
    name = dir.name

    # Add type if given
    if type:
        name += '_' + type

    name += '_index'

    return name

#===============================================================================
def _get_override_name(type):
    """Determine the name of the override label.
    
    Inputs:
        dir           top dir for volume. 
        name          base name of the index file and label.  If None, it 
                      is derived from the volume id.
        type          index type. 
        
    Outputs:          index name.
    """   

    # Name starts with collection id
    dir = Path.cwd()
    name = dir.name + '_override'

    return name

#===============================================================================
def _parse_block(lines, head=0, 
                 start_token='OBJECT=COLUMN', end_token='END_OBJECT=COLUMN'):
    """Extract a block of lines between two tokens.
    
    Inputs:
        lines         list of strings. 
        head          line at which to start search. 
        start_token   string giving token that starts a block. 
        end_token     string giving token that ends a block. 
        
    Outputs:
        block         list of strings inthe first detected block.
        head          line number of the start of the block.
        tail          line number of the end of the block.
    """   

    tail = -1
    block = []
    for i in range(head,len(lines)):
        line = lines[i]
        if line.replace(' ', '').startswith(start_token):
            head = i
            tail = head
            for line in lines[i:]:
                tail += 1
                block.append(line)
                if line.replace(' ', '').startswith(end_token):
                    break
            if block:
                break

    return (block, head, tail)

#===============================================================================
def _parse_column(lines):
    """Parse a column description into a dictionary.
    
    Inputs:
        lines         list of strings giving the column description. 
        
    Outputs:          column dictionary.
    """
    
    column_desc = {}
    for line in lines:
        line = line.replace(' ', '')
        kv = line.split('=')
        column_desc[kv[0]] = kv[1].strip()
    return column_desc

#===============================================================================
def _parse_columns(lines):
    """Parse all column descriptions into a list of dictionaries.
    
    Inputs:
        lines         list of strings containing the PDS label. 
        
    Outputs:          list of column dictionaries.
    """

    column_dicts = []
    head = 0
    while(True):
    
        # Get the current block
        block, head, tail = _parse_block(lines, head)
        if block == []:
            break
            
        # Append the column dictionary 
        column_dicts.append(_parse_column(block))

        # Advance the read head
        head += len(block)

    return column_dicts

#===============================================================================
def _process_columns(column_dicts):
    """Convert column description info into more useful form.
    
    Inputs:
       column_dicts   list of column dictionaries. 
        
    Outputs:          dictionary of column descriptions.
    """

    # Convert each column
    column_descs = {}
    for column_dict in column_dicts:
        name = column_dict['NAME']
        column_desc = {'name':name}
        
        column_desc['format'] = column_dict['FORMAT'].strip('"')
        (width, data_type) =  _format_parms(column_desc['format'])

        column_desc['count'] = int(column_dict['ITEMS']) if 'ITEMS' in column_dict.keys() else 1

        column_desc['width'] = width

        column_desc['data_type'] = data_type

        column_desc['nullval'] = column_dict['NULL_CONSTANT'] if 'NULL_CONSTANT' in column_dict.keys() else None
        if not column_desc['nullval'].startswith('"'):
            column_desc['nullval'] = float(column_desc['nullval'])

        column_desc['description'] = column_dict['DESCRIPTION'] if 'DESCRIPTION' in column_dict.keys() else ''
        
        column_desc['nbytes'] = width-2 if data_type == 'CHARACTER' else width
#        column_desc['nbytes'] = width-1 if data_type == 'CHARACTER' else width

        column_descs[name] = column_desc

    return column_descs

#===============================================================================
def _preprocess_template(lines):
    """Initial parse of the column descriptions handling preprocessor 
    directives and using PdsTemplate to create the directive names for 
    building the final label.

    Input:
        lines       list of strings containing the label template.

    Output:         list of strings containing the pre-processed label template.
    """

    # Handle preprocessor directives
    lines = meta.preprocess_label(lines)

    # Parse each column description with PdsTemplate
    head = 0
    while(True):

        # Get the current block
        block, head, tail = _parse_block(lines, head)
        if block == []:
            break

        # Parse the block
        T = PdsTemplate('_', content=block)
        content = T.generate({})
        block = content.split('\n')[0:-1]
        block = [line + '\n' for line in block]

        # Re-insert into template
        lines = lines[0:head] + block + lines[tail:]

        # Advance the read head
        head += len(block)

    return lines

#===============================================================================
def _get_columns(template):
    """Create column descriptions from a label template.

    Input:
        template    list of strings containing the label template.

    Output:         column description dictionaries
    """

    column_dicts = _parse_columns(template)
    column_descs = _process_columns(column_dicts)
    return column_descs

#===============================================================================
def _make_label(template_lines, input_dir, output_dir, type=''):
    """Creates a label for a given index table.

    Input:
        template_lines  list of strings containing the label template.
        input_dir       directory containing the volume.
        output_dir      directory in which to write the index files.
        type            qualifying string identifying the type of index file
                        to create, e.g., 'supplemental'. 
    """

    # Get filenames
    index_name = _get_index_name(input_dir, type) 

    index_filename = Path(index_name + '.tab')
    label_filename = Path(index_name + '.lbl')

    index_path = output_dir/index_filename
    label_path = output_dir/label_filename



    override_name = _get_override_name(type)        # assumes top dir is pwd
    override_path = Path('./templates/')/(override_name + '.lbl')



    # Read the data file
    f = open(index_path)
    index_lines = f.readlines()
    f.close()

    # Validate the data file
    recs = len(index_lines)
    linelen = len(index_lines[0])
    for line in index_lines:
        assert len(line) == linelen         # all lines have the same length
        assert line[-1] == '\n'             # all lines have proper <crlf>

    # Get the volume_id
    volume_id = _get_volume_id(input_dir)
    
    # Get the columns
    column_descs = _get_columns(template_lines)

    # Populate the standard PdsTemplate field dictionary
    fields = {'TYPE'            : type.upper(),
              'INDEX_FILENAME'  : index_filename,
              'RECORD_BYTES'    : linelen+1,
              'FILE_RECORDS'    : recs,
              'ROWS'            : recs,
              'COLUMNS'         : len(column_descs),
              'ROW_BYTES'       : linelen+1 }  

    # Add column-specific fields
    pos = 1
    line = index_lines[0]
    for name in column_descs:
        column_desc = column_descs[name]
        
        count = column_desc['count']
        nbytes = column_desc['nbytes']
        width = column_desc['width']
        data_type = column_desc['data_type']

        item_bytes = nbytes

        fields[name + '_START_BYTE'] = pos+1 if data_type == 'CHARACTER' else pos
        fields[name + '_BYTES'] = item_bytes
        fields[name + '_DATA_TYPE'] = data_type

        total_width = width
        if count>1:
            total_width = nbytes*count + (count-1)
            bytes = total_width
            if data_type == 'CHARACTER':
                total_width += 2*count
                bytes = total_width - 2
            fields[name + '_BYTES'] = bytes
            fields[name + '_ITEM_BYTES'] = item_bytes
            fields[name + '_ITEM_OFFSET'] = nbytes + 1
            if data_type == 'CHARACTER':
                fields[name + '_ITEM_OFFSET'] += 2

        pos = pos + total_width + 1

    # Add host-specific fields
    fields['VOLUME_ID'] = volume_id

    # Process the template
    template = PdsTemplate('', content=template_lines)
    template.write(fields, label_path.as_posix())

#===============================================================================
def _make_one_index(input_dir, output_dir, type='', glob=None, no_table=False):
    """Creates index file for a single volume.

    Input:
        input_dir       directory containing the volume, specifically the 
                        data labels
        output_dir      directory in which to find the "updated" index file
                        (e.g., <volume>_index.tab, and in which to write the 
                        new index files.
        type            qualifying string identifying the type of index file
                        to create, e.g., 'supplemental'. 
        glob            glob pattern for index files.
        no_table        if True, do not produce a table, just a label.
    """

    if not no_table:
        # Get index and template filenames
        primary_index_name = _get_index_name(input_dir, None)
        index_name = _get_index_name(input_dir, type) 
        template_name = _get_template_name(type)         # assumes top dir is pwd

        create_primary = index_name == primary_index_name

        # This assumes that the primary index file has been copied from the 
        if not create_primary:
            primary_index_path = output_dir/(primary_index_name + '.lbl')
            if not primary_index_path.exists():
                warnings.warn('Primary index file not found: %s.  Skipping' % primary_index_path)
                return

        index_path = output_dir/(index_name + '.tab')
        template_path = Path('./templates/')/(template_name + '.lbl')

        # Read template
        f = open(template_path)
        template_lines = f.readlines()
        f.close()

        # Parse any directives in the columns
        template_lines = _preprocess_template(template_lines)

        # Set up columns
        column_descs = _get_columns(template_lines)

        # Walk the directory tree...

        # Open the output file; create dir if necessary
        output_dir.mkdir(exist_ok=True)
        index = open(index_path, 'w')

        # If there is a primary file, read it and build the file list
        if not create_primary:
            table = pdstable.PdsTable(primary_index_path)
            primary_row_dicts = table.dicts_by_row()
            files = [Path(primary_row_dict['FILE_SPECIFICATION_NAME']) \
                        for primary_row_dict in primary_row_dicts]

            for i in range(len(files)): 
                files[i] = Path(os.path.splitext(os.path.join(input_dir.as_posix(), files[i].as_posix()))[0] + '.LBL')
#xx                files[i] = input_dir/files[i].removesuffix.with_suffix('.LBL'))   # Doesn't work in 3.8

        # Otherwise, build the file list from the directory tree
        else:
            files = [f for f in input_dir.rglob('*.LBL')]

        # Build the index
        for file in files:
            name = file.name
            root = file.parent

            # Match the glob pattern
            file = fnmatch.filter([name], glob)[0]
            if file == []:
                continue

            # Print volume ID and subpath
            subdir = _get_subdir(root)
            volume_id = _get_volume_id(input_dir)
            print('    ', volume_id, subdir/name)

            # Make the index for this file
            _index_one_file(root, file, index, column_descs)

        # Close index file and make label if the index exists
        try:
            index.close()
        except:
            pass

    # Create the label
    _make_label(template_lines, input_dir, output_dir, type=type)    
        

################################################################################
# external functions
################################################################################

#===============================================================================
def make_index(input_tree, output_tree, type='', glob=None, volume=None, no_table=False):
    """Creates index files for a collection of volumes.

    Input:
        input tree      root of the tree containing the volumes.
        output tree     root of the tree in which the output files are
                        written in the same directory structure as in the 
                        input tree.
        prefix          prefix for index file namesof the form:
                            <prefix>_<volid>  
        type            qualifying string identifying the type of index file
                        to create, e.g., 'supplemental'. 
        volume          if given, only this volume is processed.
        glob            glob pattern for index files.
        no_table        if True, do not produce a table, just a label.
    """

    input_tree = Path(input_tree) 
    output_tree = Path(output_tree) 

    # Build volume glob
    vol_glob = meta.get_volume_glob(input_tree.name)

    # Walk the input tree, making indexes for each found volume
#xx    for root, dirs, files in input_tree.walk():    #### Path.walk() doens't exist in python 3.8
    for root, dirs, files in os.walk(input_tree.as_posix()):
        root = Path(root)

        # Determine notional set and volume
        parts = root.parts
        set = parts[-2]
        vol = parts[-1]

        # Test whether this root is a volume
        if fnmatch.filter([vol], vol_glob):
            if not volume or vol == volume:
                indir = root
                if output_tree.parts[-1] != set: 
                    outdir = output_tree/set
                outdir = output_tree/vol
                _make_one_index(indir, outdir, 
                                type=type, 
                                glob=glob, 
                                no_table=no_table)

################################################################################

