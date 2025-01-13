################################################################################
# geometry_support.py - Tools for generating geometry tables.
################################################################################
import oops
import numpy as np
import traceback
import warnings
import fnmatch

import metadata as meta
import metadata.label_support as lab
import config

from pathlib import Path

################################################################################
# FORMAT_DICT tuples are:
#
#   (flag, number_of_values, column_width, standard_format, overflow_format,
#    null_value)
#
# where...
#
#   flag = "RAD" = convert values from radians to degrees;
#        = "360" = convert to degrees, with 360-deg periodicity;
#        = ""    = do not modify value.
#
# Adding a column:
#   1. Update format dictionary below as needed
#   2. Run GO_xxxx_geometry.py
#   3. Update label template:
#       a. Update RECORD_BYTES (= .tab last line number + 2)
#       b. Update ROW_BYTES (= RECORD_BYTES)
#       c. Update COLUMNS
#       d. Add column description(s) in label template(s)
#          - Update COLUMN_NUMBER
#          - Update START_BYTE (= table character # after comma + 1)
#       e. Run make_label.py
#          **** check other tables for any new columns resulting from step 1.
#   4. Update unit tests
#   
################################################################################
FORMAT_DICT = {
    "right_ascension"           : ("360", 2, 10, "%10.6f", "%10.5f", -999.),
    "center_right_ascension"    : ("360", 2, 10, "%10.6f", "%10.5f", -999.),
    "declination"               : ("DEG", 2, 10, "%10.6f", "%10.5f", -999.),
    "center_declination"        : ("DEG", 2, 10, "%10.6f", "%10.5f", -999.),

    "distance"                  : ("",    2, 12, "%12.3f", "%12.5e", -999.),
    "center_distance"           : ("",    2, 12, "%12.3f", "%12.5e", -999.),

    "event_time"                : ("",    2, 16, "%16.3f", "%16.9e",    0.),

    "ring_radius"               : ("",    2, 12, "%12.3f", "%12.5e", -999.),
    "ansa_radius"               : ("",    2, 12, "%12.3f", "%12.5e", -999.),

    "altitude"                  : ("",    2, 12, "%12.3f", "%12.5e", -9.99e9),
    "ansa_altitude"             : ("",    2, 12, "%12.3f", "%12.5e", -9.99e9),

    "resolution"                : ("",    2, 10, "%10.5f", "%10.4e", -999.),
    "finest_resolution"         : ("",    2, 10, "%10.5f", "%10.4e", -999.),
    "coarsest_resolution"       : ("",    2, 10, "%10.5f", "%10.4e", -999.),
    "ring_radial_resolution"    : ("",    2, 10, "%10.5f", "%10.4e", -999.),
    "ansa_radial_resolution"    : ("",    2, 10, "%10.5f", "%10.4e", -999.),
    "ansa_vertical_resolution"  : ("",    2, 10, "%10.5f", "%10.4e", -999.),
    "center_resolution"         : ("",    2, 10, "%10.5f", "%10.4e", -999.),

    "ring_angular_resolution"   : ("DEG", 2, 10, "%8.5f",  "%8.4f",  -999.),

    "longitude"                 : ("360", 2,  8, "%8.3f",  None,     -999.),
    "ring_longitude"            : ("360", 2,  8, "%8.3f",  None,     -999.),
    "ring_azimuth"              : ("360", 2,  8, "%8.3f",  None,     -999.),
    "ansa_longitude"            : ("360", 2,  8, "%8.3f",  None,     -999.),
    "sub_solar_longitude"       : ("360", 2,  8, "%8.3f",  None,     -999.),
    "sub_observer_longitude"    : ("360", 2,  8, "%8.3f",  None,     -999.),
    "ring_sub_solar_longitude"  : ("360", 2,  8, "%8.3f",  None,     -999.),
    "ring_sub_observer_longitude"
                                : ("360", 2,  8, "%8.3f",  None,     -999.),

    "latitude"                  : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "sub_solar_latitude"        : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "sub_observer_latitude"     : ("DEG", 2,  8, "%8.3f",  None,     -999.),

    "phase_angle"               : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "center_phase_angle"        : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "incidence_angle"           : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "ring_incidence_angle"      : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "center_incidence_angle"    : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "ring_center_incidence_angle":("DEG", 2,  8, "%8.3f",  None,     -999.),
    "emission_angle"            : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "ring_emission_angle"       : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "center_emission_angle"     : ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "ring_center_emission_angle": ("DEG", 2,  8, "%8.3f",  None,     -999.),
    "ring_elevation"            : ("DEG", 2,  8, "%8.3f",  None,     -999.),

    "where_inside_shadow"       : ("",    2,  1, "%1d",    None,        0 ),
    "where_in_front"            : ("",    2,  1, "%1d",    None,        0 ),
    "where_in_back"             : ("",    2,  1, "%1d",    None,        0 ),
    "where_antisunward"         : ("",    2,  1, "%1d",    None,        0 )}

ALT_FORMAT_DICT = {
    ("longitude",      "-180")  : ("-180", 2, 8, "%8.3f",  None,     -999.),
    ("ring_longitude", "-180")  : ("-180", 2, 8, "%8.3f",  None,     -999.),
    ("sub_longitude",  "-180")  : ("-180", 2, 8, "%8.3f",  None,     -999.)}

SYSTEMS_TABLE = meta.convert_systems_table(config.SYSTEMS_TABLE, config.SCLK_BASES)

################################################################################
# Record class
################################################################################
class Record(object):
    """Class describing a single geometry record, i.e., a single row in a table.
    """

    #===========================================================================
    def __init__(self, observation, volume_id, meshgrids, level):
        """Constructor for a geometry record.

        Args:
            observation (oops.Observation): OOPS Observation object.
            volume_id (str): Volume ID.
            meshgrids (dict): All meshgrids associated with this host.
            level (str, optional): Processing level: 'summary' or 'detailed'.
        """
        self.observation = observation

        # Determine system, if any
        sclk = observation.dict["SPACECRAFT_CLOCK_START_COUNT"] + '' 
        self.system, self.secondaries = \
            meta.get_system(SYSTEMS_TABLE, sclk, config.SCLK_BASES)
        self.level = level

        # Level-specific column dictionaries
        self.dicts = {'sky' : meta.SKY_COLUMNS}
        if level == 'summary':
            self.dicts |= {
                'ring'   : meta.RING_SUMMARY_DICT,
                'body'   : meta.BODY_SUMMARY_DICT,
            }
        else:
            self.dicts |= {
                'ring'   : meta.RING_SUMMARY_DETAILEDT,
                'body'   : meta.BODY_SUMMARY_DETAILED,
            }

        # Set up planet-based geometry
        self.bodies = []
        self.blocker = None

        if self.system:
            self.rings_present = meta.BODIES[self.system].ring_frame is not None    
            self.ring_tile_dict = meta.RING_TILE_DICT[self.system]
            self.body_tile_dict = meta.BODY_TILE_DICT[self.system]

        # Determine target
        self.target = config.target_name(observation.dict)
        if self.target in meta.TRANSLATIONS.keys():
            self.target = meta.TRANSLATIONS[self.target]

        # Create the record prefix
        filespec = observation.dict["FILE_SPECIFICATION_NAME"]
        self.prefixes = ['"' + volume_id + '"',
                         '"%-32s"' % filespec.replace(".IMG", ".LBL")]
        
        # Create the backplane
        meshgrid = self._meshgrid(observation, meshgrids)
        self.backplane = oops.backplane.Backplane(observation, meshgrid)
        
        # Build body list
        body_names = meta.BODIES.keys()
        if self.target not in meta.BODIES and oops.Body.exists(self.target):
            body_names += [self.target]

        # Inventory the bodies in the FOV
        if body_names:
            body_names = self.observation.inventory(body_names, expand=config.EXPAND, cache=False)

        # Add any secondaries to body_names
        if self.secondaries:
            body_names += self.secondaries
        self.bodies = body_names

        if self.system:
            # Define a blocker body, if any
            if self.target in self.bodies:
                self.blocker = self.target

            # Add a targeted irregular moon to the dictionaries if present
            if self.target in self.bodies and self.target not in self.dicts['body'].keys():
                self.dicts['body'][self.target] = meta.replace(meta.BODY_SUMMARY_COLUMNS,
                                                         meta.BODYX, self.target)
                self.body_tile_dict[self.target] = meta.replace(meta.BODY_TILES, meta.BODYX, self.target)

    #===============================================================================
    def _meshgrid(self, observation, meshgrids):
        """Looks up the meshgrid for an observation.

        Args: 
            observation (oops.Observation): OOPS Observation object.
            meshgrids (dict): All meshgrids associated with this host.

        Returns: 
            oops.Meshgrid: Meshgrid for the given observation.
        """
        return config.meshgrid(meshgrids, observation)

    #===============================================================================
    def add(self, qualifier, *,
                  name=None,target=None, tiles=[], tiling_min=100,
                  ignore_shadows=False, start_index=1, allow_zero_rows=False, 
                  no_mask=False, no_body=False):
        """Generates the geometry for one row, given a list of column descriptions.

        The tiles argument supports detailed listings where a geometric region is
        broken down into separate subregions. If the tiles argument is empty (which
        is the default), then this routine writes a summary file.

        If the tiles argument is not empty, then the routine writes a detailed file,
        which generally contains one record for each non-empty subregion. The tiles
        argument must be a list of boolean backplane keys, each equal to True for
        the pixels within the subregion. An additional column is added before the
        geometry columns, containing the index value of the associated tile.

        The first backplane in the list is treated differently. It should evaluate
        to an area roughly equal to the union of all the other backplanes. It is
        used to ensure that tiling is suppressed when the region to be tiled is too
        small. If the number of meshgrid samples that are equal to True in this
        backplane is smaller than the limit specified by argument tiling_min, then
        no detailed record is written.

        In a summary listing, this routine writes one record per call, even if all
        values are null. In a detailed listing, only records associated with
        non-empty regions of the meshgrid are written.

        Args:
            qualifier: 'sky', 'ring', or 'body'.
            name (str, optional): Name identifying a specific column description.
            target (str, optional): Optionally, the target name to write into the record.
            tiles (list, optional):
                An optional list of boolean backplane keys, used to
                support the generation of detailed tabulations instead
                of summary tabulations. See details above.
            tiling_min (int, optional):
                The lower limit on the number of meshgrid points in a
                region before that region is subdivided into tiles.
            ignore_shadows (bool, optional):
                True to ignore any mask constraints applicable to
                shadowing or to the sunlit faces of surfaces.
            start_index (int, optional): Index to use for first subregion. Default 1.
            allow_zero_rows (bool, optional):
                True to allow the function to return no rows. If False,
                a row filled with null values will be returned if
                necessary.
            no_mask (bool, optional): True to suppress the use of a mask.
            no_body (bool, optional): True to suppress body prefixes.
        """
    
        # Get the column decsriptions
        column_descs = self.dicts[qualifier]
        if name:
            column_descs = column_descs[name]

        # Prepare the rows
        rows = Record._prep_row(self.prefixes, self.backplane, self.blocker, column_descs,
                                system=self.system, target=target,
                                tiles=tiles, tiling_min=tiling_min, ignore_shadows=ignore_shadows,
                                start_index=start_index, allow_zero_rows=allow_zero_rows, no_mask=no_mask, 
                                no_body=no_body)

        # Append the complete rows to the output
        lines = []
        for row in rows:
            line = row[0]
            for column in row[1:]:
                line += ','
                line += column
            lines.append(line)

        return lines
    
    #===============================================================================
    @staticmethod
    def _prep_row(prefixes, backplane, blocker, column_descs, *,
                  system=None, target=None, name_length=meta.NAME_LENGTH,
                  tiles=[], tiling_min=100, ignore_shadows=False,
                  start_index=1, allow_zero_rows=False, no_mask=False, 
                  no_body=False):
        """Generates the geometry and returns a list of lists of strings. The inner
        list contains string representations for each column in one row of the
        output file. These will be concatenated with commas between them and written
        to the file. The outer list contains one list for each output row. The
        number of output rows can be zero or more.

        The tiles argument supports detailed listings where a geometric region is
        broken down into separate subregions. If the tiles argument is empty (which
        is the default), then this routine writes a summary file.

        If the tiles argument is not empty, then the routine writes a detailed file,
        which generally contains one record for each non-empty subregion. The tiles
        argument must be a list of boolean backplane keys, each equal to True for
        the pixels within the subregion. An additional column is added before the
        geometry columns, containing the index value of the associated tile.

        The first backplane in the list is treated differently. It should evaluate
        to an area roughly equal to the union of all the other backplanes. It is
        used as an overlay to all subsequent tiles.

        In a summary listing, this routine writes one record per call, even if all
        values are null. In a detailed listing, only records associated with
        non-empty regions of the meshgrid are written.

        Args:
            prefixes (list):
                A list of the strings to appear at the beginning of the
                line, up to and including the file specification name. Each
                individual string should already be enclosed in quotes.
            backplane (oops.Backplane): Backplane for the observation.
            blocker (str):
                The name of one body that may be able to block or shadow
                other bodies.
            column_descs (list): A list of column descriptions.
            system (str): Name of systembody, uppercase, e.g., "SATURN".
            target (str, optional): Optionally, the target name to write into the record.
            name_length (int, optional):
                The character width of a column to contain body names.
                If zero (which is the default), then no name is
                written into the record.
            tiles (list, optional):
                An optional list of boolean backplane keys, used to
                support the generation of detailed tabulations instead
                of summary tabulations. See details above.
            tiling_min (int, optional):
                The lower limit on the number of meshgrid points in a
                region before that region is subdivided into tiles.
            ignore_shadows (bool, optional):
                True to ignore any mask constraints applicable to
                shadowing or to the sunlit faces of surfaces.
            start_index (int, optional): Index to use for first subregion. Default 1.
            allow_zero_rows (bool, optional):
                True to allow the function to return no rows. If False,
                a row filled with null values will be returned if
                necessary.
            no_mask (bool, optional): True to suppress the use of a mask.
            no_body (bool, optional): True to suppress body prefixes.

        Returns:
           list: String comprising the resulting rows.
        """

        # Handle option for multiple tile sets
        if type(tiles) == tuple:
            rows = []
            local_index = start_index
            for tile in tiles:
                new_rows = Record._prep_row(prefixes, backplane, blocker, column_descs,
                                            system, target, name_length,
                                            tile, tiling_min, ignore_shadows,
                                            local_index, allow_zero_rows=True)
                rows += new_rows
                local_index += len(tile) - 1

            if rows or allow_zero_rows:
                return rows

            return Record._prep_row(prefixes, backplane, blocker, column_descs,
                                    system, target, name_length,
                                    [], tiling_min, ignore_shadows,
                                    start_index, allow_zero_rows=False)

        # Handle a single set of tiles
        if tiles:
            global_area = backplane.evaluate(tiles[0]).vals
            subregion_masks = [np.logical_not(global_area)]

            if global_area.sum() < tiling_min:
                tiles = []
            else:
                for tile in tiles[1:]:
                    mask = backplane.evaluate(tile).vals & global_area
                    subregion_masks.append(np.logical_not(mask))
        else:
            subregion_masks = []

        # Initialize the list of rows
        rows = []

        # Create all the needed pixel masks
        excluded_mask_dict = {}
        if not no_mask:
            for column_desc in column_descs:
                event_key = column_desc[0]
                mask_desc = column_desc[1]
                mask_target = event_key[1]

                key = (mask_target,) + mask_desc
                if key in excluded_mask_dict: continue

                excluded_mask_dict[key] = \
                    Record._construct_excluded_mask(
                                backplane, mask_target, system, mask_desc,
                                blocker=blocker, ignore_shadows=ignore_shadows)
        # Initialize the list of rows

        # Interpret the subregion list
        if tiles:
            indices = range(1,len(tiles))
        else:
            indices = [0]

        # For each subregion...
        for indx in indices:

            # Skip a subregion if it will be empty
            if indx != 0 and np.all(subregion_masks[indx]): continue

            # Initialize the list of columns
            prefix_columns = list(prefixes) # make a copy

            # Append the target and system name as needed
            if not no_body:
                Record._append_body_prefix(prefix_columns, system, name_length)
                if target is not None:
                    Record._append_body_prefix(prefix_columns, target, name_length)

            # Insert the subregion index
            if subregion_masks:
                prefix_columns.append('%2d' % (indx + start_index - 1))

            # Append the backplane columns
            data_columns = []
            nothing_found = True

            # For each column...
            for column_desc in column_descs:
                event_key = column_desc[0]
                mask_desc = column_desc[1]

                # Fill in the backplane array
                if event_key[1] == meta.NULL:
                    values = oops.Scalar(0., True)
                else:
                    values = backplane.evaluate(event_key)

                # Make a shallow copy and apply the new masks
                if excluded_mask_dict != {}:
                    target = event_key[1]
                    excluded = excluded_mask_dict[(target,) + mask_desc]
                    values = values.mask_where(excluded)
                    if len(subregion_masks) > 1:
                        values = values.mask_where(subregion_masks[indx])
                    elif len(subregion_masks) == 1:
                        values = values.mask_where(subregion_masks[0])

                if not np.all(values.mask):
                    nothing_found = False

                # Write the column using the specified format
                if len(column_desc) > 2:
                    format = ALT_FORMAT_DICT[(event_key[0], column_desc[2])]
                else:
                    format = FORMAT_DICT[event_key[0]]

                data_columns.append(Record._formatted_column(values, format))

            # Save the row if it was completed
            if len(data_columns) < len(column_descs): continue # hopeless error
            if nothing_found and (indx > 0 or allow_zero_rows): continue
            rows.append(prefix_columns + data_columns)

        # Return something if we can
        if rows or allow_zero_rows:
            return rows

        return Record._prep_row(prefixes, backplane, blocker, column_descs,
                                system, target, name_length,
                                [], 0, ignore_shadows, start_index,
                                allow_zero_rows=False)

    #===============================================================================
    @staticmethod
    def _append_body_prefix(prefix_columns, body, length):
        """Append a body name to the column prefixes.

        Args:
            prefix_columns (list):
                A list of the strings to appear at the beginning of the
                row, up to and including the file specification name. Each
                individual string should already be enclosed in quotes.
            body (str): Body name to append.
            length (int, optional):
                The character width of a column to contain body names.

        Returns:
            None.
        """
        if body is None:
            entry = '"' + length * ' ' + '"'
        else:
            lbody = len(body)
            if lbody > length:
                entry  = '"' + body[:length] + '"'
            else:
                entry  = '"' + body + (length - lbody) * ' ' + '"'

        prefix_columns.append(entry)

    #===============================================================================
    @staticmethod
    def _construct_excluded_mask(backplane, target, system, mask_desc, *,
                                 blocker=None, ignore_shadows=True):
        """Return a mask using the specified target, maskers and shadowers to
        indicate excluded pixels.

        Args:
            backplane (oops.Backplne): The backplane defining the target surface.
            target (str): The name of the target surface.
            system (str): Name of system, e.g., "SATURN".
            mask_desc (masker, shadower, face), where:
                Masker      a string identifying what surfaces can obscure the
                target. It is a concatenation of:
                "P" to let the planet obscure the target;
                "R" to let the rings obscure the target;
                "M" to let the blocker body obscure the target.
                shadower    a string identifying what surfaces can shadow the
                target. It is a string containing:
                "P" to let the planet shadow the target;
                "R" to let the rings shadow the target;
                "M" to let the blocker body shadow the target.
                face        a string identifying which face(s) of the surface to
                include:
                "D" to include only the day side of the target;
                "N" to include only the night side of the target;
                ""  to include both faces of the target.
            blocker (str, optional):
                Optionally, the name of the body to use for any "M"
                codes that appear in the mask_desc.
            ignore_shadows (bool, optional):
                True to ignore any shadower or face constraints; default
                is False.
       
        Returns:
            numpy.array: Boolean bitmask containing the mask.
        """

        # Do not let a body block itself
        if target == blocker:
            blocker = None

        # Generate the new mask, with True means included
        if type(target) == str:
            system_name = target.split(':')[0]
            if not oops.Body.exists(system_name):
                return True

        (masker, shadower, face) = mask_desc

        excluded = np.zeros(backplane.shape, dtype='bool')

        # Handle maskers
        if "R" in masker and system == "SATURN":
            excluded |= backplane.where_in_back(target, "SATURN_MAIN_RINGS").vals

        if "P" in masker:
            excluded |= backplane.where_in_back(target, system).vals
            if system == "PLUTO":
                excluded |= backplane.where_in_back(target, "CHARON").vals

        if "M" in masker and blocker is not None:
            excluded |= backplane.where_in_back(target, blocker).vals

        if not ignore_shadows:

            # Handle shadowers
            if "R" in shadower and system == "SATURN":
                excluded |= backplane.where_inside_shadow(target, "SATURN_MAIN_RINGS").vals

            if "P" in shadower:
                excluded |= backplane.where_inside_shadow(target, system).vals
                if system == "PLUTO":
                    excluded |= backplane.where_inside_shadow(target, "CHARON").vals

            if "M" in shadower and blocker is not None:
                excluded |= backplane.where_inside_shadow(target, blocker).vals

            # Handle face selection
            if "D" in face:
                excluded |= backplane.where_antisunward(target).vals

            if "N" in face:
                excluded |= backplane.where_sunward(target).vals

    #!!!!
    # This function does does not handle gridless backplanes properly.  This
    # code fixes that, but the core problem should be fixed before this point.
        if np.any(excluded):
            return excluded
        if np.all(excluded):
            return True
        return False

    #===============================================================================
    @staticmethod
    def _formatted_column(values, format):
        """Returns one formatted column (or a pair of columns) as a string.

        Args:
            values (oops.Scalar): A Scalar of values with its applied mask.
            format (tuple):
                A tuple (flag, number_of_values, column_width,standard_format, 
                overflow_format, null_value),describing the format to use. 
                Here...
                    flag: "DEG" implies that the values should be converted
                        from radians to degrees; "360" implies that the
                        values should be converted to a range of degrees,
                        allowing for ranges that cross from 360 to 0.
                        number_of_values  1 yields the mean value
                        2 yields the minimum and maximum values.
                    column_width: Total width of the formatted string.
                    standard_format: Desired format code for the field.
                    overflow_format: Format code if field overflows the 
                        standard_format length.
                    null_value: Value to indicate NULL.

        Returns:
            str: Formatted column.
        """

        # Interpret the format
        (flag, number_of_values, column_width,
        standard_format, overflow_format, null_value) = format

        # Convert from radians to degrees if necessary
        if flag in ("DEG","360","-180"):
            values = values * oops.DPR

        # Create a list of the numeric values for this column
        if number_of_values == 1:
            meanval = values.mean().as_builtin()
            if type(meanval) == oops.Scalar and meanval.mask:
                results = [null_value]
            else:
                results = [meanval]

        elif np.all(values.mask):
            results = [null_value, null_value]

        elif flag == "360":
            results = meta._get_range_mod360(values)

        elif flag == "-180":
            results = meta._get_range_mod360(values, alt_format=flag)

        else:
            results = [values.min().as_builtin(), values.max().as_builtin()]

        # Write the formatted value(s)
        strings = []
        for number in results:
            error_message = ""

            if np.isnan(number):
                warnings.warn("NaN encountered")
                number = null_value

            if np.isinf(number):
                warnings.warn("infinity encountered")
                number = null_value

            string = standard_format % number

            if len(string) > column_width:
                string = overflow_format % number

                if len(string) > column_width:
                    number = min(max(-9.99e99, number), 9.99e99)
                    string99 = overflow_format % number

                    if len(string99) > column_width:
                        error_message = "column overflow: " + string
                    else:
                        warnings.warn("column overflow: " + string +
                                    " clipped to " + string99)
                        string = string99

                    string = string[:column_width]

            strings.append(string)

            if error_message != "":
                raise RuntimeError(error_message)

        return ",".join(strings)

################################################################################
# Table class
################################################################################
class Table(object):
    """Class describing a single geometry table for a single volume.
    """

    #===========================================================================
    def __init__(self, volume_id=None, level=None, qualifier=None, suffix=None):
        """Constructor for a geometry table object.

        Args:
            volume_id (str): Volume ID.
            level (str, optional): Processing level: 'summary' or 'detailed'.
            qualifier (str): "sky", "ring", "body", or "inventory".
            suffix (str): [[]]
        """
        self.volume_id = volume_id
        self.level = level
        self.qualifier = qualifier
        
        if not suffix:
            self.suffix = "_%s_%s.tab" % (self.qualifier, self.level)
        else:
            self.suffix = suffix

        self.rows = []

     #===============================================================================
    def write(self, prefix, filename=None):
        """Write a table and its label.

        Args:
            prefix (str): Filename prefix including the full path.
            filename (str or Path, optional):
                Name of file to write instead of creating one using the given prefix, 
                and the suffix attribute.

        Returns:
            None.
        """
        logger = meta.get_logger()
        
        if self.rows == []:
            return

        # Create filename
        filename = Path(prefix + self.suffix)

        # Write table
        logger.info("Writing:", filename)
        meta.write_txt_file(filename, self.rows)

        # Write label
        table_type = ''
        table_type = self.qualifier + '_' + self.level
        lab.create(filename, table_type=table_type)

################################################################################
# InventoryTable class
################################################################################
"""Class describing an inventory geometry table.
"""
class InventoryTable(Table):
    #===========================================================================
    def __init__(self, **kwargs):
        """Constructor for an InventoryTable object.

        Args:
            table: Parent Table instance.
        """
        super().__init__(qualifier='inventory', suffix="_inventory.csv", **kwargs)

    #===============================================================================
    def add(self, record):
        """Add an Inventory row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        line = ",".join(record.prefixes)
        for name in record.bodies:
            line += ',"' + name + '"'
        self.rows += [line]

################################################################################
# SkyTable class
################################################################################
"""Class describing a sky geometry table.
"""
class SkyTable(Table):
    #===========================================================================
    def __init__(self, **kwargs):
        """Constructor for a SkyTable object.

        Args:
            table: Parent Table instance.
        """
        super().__init__(qualifier='sky', **kwargs)

    #===============================================================================
    def add(self, record):
        """Add a Sky row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """
        self.rows += record.add(self.qualifier, no_body=True)

################################################################################
# RingTable class
################################################################################
"""Class describing a ring geometry table.
"""
class RingTable(Table):
    #===========================================================================
    def __init__(self, **kwargs):
        """Constructor for a RingTable object.

        Args:
            table: Parent Table instance.
        """
        super().__init__(qualifier='ring', **kwargs)

    #===============================================================================
    def add(self, record):
        """Add a Ring row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """

        # Add record
        if record.system:
            if record.rings_present:
                self.rows += record.add(self.qualifier, name=record.system)

#        # Add other rings
#        for name in record.bodies
#           if record.rings_present:
#               self.rows += record.add(self.qualifier, name=name, 
#                                       target=name+'-ring', no_mask=True

################################################################################
# BodyTable class
################################################################################
"""Class describing a body geometry table.
"""
class BodyTable(Table):
    #===========================================================================
    def __init__(self, **kwargs):
        """Constructor for a BodyTable object.

        Args:
            table: Parent Table instance.
        """
        super().__init__(qualifier='body', **kwargs)

    #===============================================================================
    def add(self, record):
        """Add a Body row.

        Args:
            record (Record): Record describing the row to add.

        Returns:
            None.
        """

        # Add system body
        if record.system:
            self.rows += record.add(self.qualifier, name=record.system, target=record.system)

        # Add other bodies
        for name in record.bodies:
            if name != record.system:
                self.rows += record.add(self.qualifier, name=name, target=name)


################################################################################
# Suite class
################################################################################
class Suite(object):
    """Class describing the suite of geometry tables for a single volume.
    """

    #===========================================================================
    def __init__(self, input_dir, output_dir,
                       selection='', glob=None, first=None, sampling=8):
        """Constructor for a geometry Suite object.

        Args:
            input_dir (Path): Directory containing the volume.
            output_dir (Path): Directory in which to write the geometry files.
            selection (str, optional):
                A string containing...
                "S" to generate summary files;
                "D" to generate detailed files.
            glob (str, optional): Glob pattern for index files.
            first (bool, optional): 
                If given, at most this many files are processed in each volume.
            sampling (int, optional): Pixel sampling density.
        """
        logger = meta.get_logger()

        # Save inputs
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.glob = glob
        self.first = first
    
        # Determine processing levels
        self.levels = []
        for sel in selection:
            if sel == 'S':
                self.levels += ['summary']
            if sel == 'D':
                self.levels += ['detailed']

        # Check for supplemental index
        index_filenames = list(self.input_dir.glob(self.glob))
        if len(index_filenames) == 0:
            return
        if len(index_filenames) > 1:
            raise RuntimeError('Mulitple index files found in %s.' % self.input_dir)

        index_filename = index_filenames[0]
        ext = index_filename.suffix
        self.volume_id = config.get_volume_id(self.input_dir)
        supplemental_index_name = meta.get_index_name(self.input_dir, self.volume_id, 'supplemental')
        supplemental_index_filename = self.input_dir.joinpath(supplemental_index_name+ext)

        logger.info('New geometry index for %s.' % self.volume_id)

        # Get observations
        try:
            self.observations = config.from_index(index_filename, supplemental_index_filename)
        except FileNotFoundError:
            pass

        # Set file prefix
        self.prefix = self.output_dir.joinpath(self.volume_id).as_posix()

        # Initialize inventory table
        self.inventory_filename = Path(self.prefix + "_inventory.csv")
        self.inventory = []
        logger.info("Inventory file: " + self.inventory_filename.as_posix())

        # Initialize data tables
        for level in self.levels:
            self.add_tables(level)

        # Initialize meshgrids
        self.meshgrids = config.meshgrids(sampling)

    #===============================================================================
    def add_tables(self, level):
        """Add a set of tables.

        Args:
           level (str): 'summary' or'detailed''.

        Returns:
            None.
        """
        self.tables = [
            InventoryTable(volume_id=self.volume_id, level=level),
            SkyTable(volume_id=self.volume_id, level=level),
            RingTable(volume_id=self.volume_id, level=level),
            BodyTable(volume_id=self.volume_id, level=level)
            ]

    #===============================================================================
    def make_records(self, index):
        """Add a record for each processing level.

        Args:
           index (int): Row index.

        Returns:
            list: One record for each processing level.
        """
        records = []
        for level in self.levels:
            records.append(
                Record(self.observations[index], self.volume_id, self.meshgrids, level))
        return records

    #===============================================================================
    def add(self, records):
        """Add a row to all tables.

        Args:
            records (list): 
                Records describing the rows to add, one for each processing level.

        Returns:
            None.
        """
        for table in self.tables:
            for record in records:
                if record.level == table.level:
                    table.add(record)

    #===============================================================================
    def write(self):
        """Write all tables and their labels.

        Args: 
            None
        Returns: 
            None
        """
        for table in self.tables:
            table.write(self.prefix)

    #===============================================================================
    def create(self):
        """Process the volume and write a suite of geometry files.

        Args: 
            None
        Returns: 
            None
        """
        logger = meta.get_logger()
        
        if not hasattr(self, 'observations'):
            return

        # Loop through the observations...
        nobs = len(self.observations)
        count = 0
        for i in range(nobs):
            # Abort if count exceeds a specified limit
            if self.first and count >= self.first:
                continue

            # Print a log of progress
            logger.info("%s  %4d/%4d" % (self.volume_id, i+1, nobs))

            # Continue processing even if cspice throws a runtime error
            try:
                # Construct the record for this observation
                records = self.make_records(i)
 
                # Update the tables
                self.add(records)
                count += 1
 
            # A RuntimeError is probably caused by missing spice data. There is
            # probably nothing we can do.
            except RuntimeError as e:
                logger.warn(str(e))

            # Other kinds of errors are genuine bugs. For now, we just log the
            # problem, and jump over the image; we can deal with it later.
            except (AssertionError, AttributeError, IndexError, KeyError,
                    LookupError, TypeError, ValueError):
                logger.error(traceback.format_exc())

        # Write tables and make labels
        self.write()

        # Clean up
        config.cleanup()


################################################################################
# external functions
################################################################################

#===============================================================================
def get_args(host=None, selection=None, exclude=None, sampling=8):
    """Argument parser for geometric metadata.

    Args:
        host (str): Host name, e.g. 'GOISS'.
        selection (str, optional):
            A string containing...
            "S" to generate summary files;
            "D" to generate detailed files.
        exclude (list, optional): List of volumes to exclude.
        sampling (int, optional): Pixel sampling density.

     Returns:
        argparser.ArgumentParser : 
            Parser containing the argument specifications.
    """

    # Get parser with common args
    parser = meta.get_common_args(host=host)

    # Add parser for index args
    gr = parser.add_argument_group('Geometry Arguments')
    gr.add_argument('--selection', type=str, metavar='selection',
                    default=selection, 
                    help='''A string containing:
                             "S" to generate summary files;
                             "D" to generate detailed files.''')
    gr.add_argument('--exclude', '-e', nargs='*', type=str, metavar='exclude',
                    default=exclude, 
                    help='''List of volumes to exclude.''')
    gr.add_argument('--new_only', '-n', nargs='*', type=str, metavar='new_only',
                    default=False, 
                    help='''Only volumes that contain no output files are processed.''')
    gr.add_argument('--first', '-f',type=int, metavar='first',
                    help='''If given, at most this many input files are processed
                            in each volume.''')
    gr.add_argument('--sampling', '-s', type=int, metavar='sampling',
                    default=sampling, 
                    help='''Pixel sampling density.''')

    # Return parser
    return parser

#===============================================================================
def process_tables(host=None, selection=None, exclude=None, sampling=8, glob=None):
    """Create geometry tables for a collection of volumes.

    Args:
        host (str): Host name e.g. 'GOISS'.
        selection (str, optional):
            A string containing...
            "S" to generate summary files;
            "D" to generate detailed files.
        exclude (list, optional): List of volumes to exclude.
        sampling (int, optional): Pixel sampling density.
        glob (str, optional): Glob pattern for index files.
  """

    # Parse arguments
    parser = get_args(host=host, selection=selection, exclude=exclude, sampling=sampling)
    args = parser.parse_args()

    input_tree = Path(args.input_tree) 
    output_tree = Path(args.output_tree) 
    volume = args.volume
    new_only = args.new_only

    if volume:
        new_only = False

    # Build volume glob
    vol_glob = meta.get_volume_glob(input_tree.name)

    # Walk the input tree, making indexes for each found volume
    for root, dirs, files in input_tree.walk():
        # __skip directory will not be scanned, so it's safe for test results
        if '__skip' in root.as_posix():
            continue

        # Sort directories for progress monitoring
        dirs.sort()
        root = Path(root)

        # Determine notional set and volume
        parts = root.parts
        set = parts[-2]
        vol = parts[-1]

        # Proceed only if this root is a volume
        if fnmatch.filter([vol], vol_glob):
            if not volume or vol == volume:
                # Set up input and output directories
                indir = root
                if output_tree.parts[-1] != set: 
                    outdir = output_tree.joinpath(set)
                outdir = output_tree.joinpath(vol)

                # Do not continue if this volume is excluded
                skip = False
                if exclude is not None:
                    for item in exclude:
                        if item in indir.parts:
                            skip = True
                if skip:
                    continue

                # Check whether this volume has already been processed
                if new_only & (list(outdir.glob('*_inventory.csv')) != []):
                    continue

                # Process this volumne
                tables = Suite(indir, outdir, 
                              selection=args.selection, glob=glob, first=args.first, 
                              sampling=args.sampling)
                tables.create()

################################################################################