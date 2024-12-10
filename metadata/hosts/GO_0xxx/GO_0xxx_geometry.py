#!/usr/bin/env python
################################################################################
# GO_0xxx_geometry.py: Generates all geometry indices for Galileo SSI
#
# Usage:
#   python GO_0xxx_geometry.py input_tree output_tree [volume]
#
#   e.g., python GO_0xxx_geometry.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA/GO_0xxx/
#         python GO_0xxx_geometry.py $RMS_METADATA/GO_0xxx/ $RMS_METADATA/GO_0xxx/ GO_0017
#
# Procedure:
#  1) Create the supplemental index files in the input tree using 
#     GO_0xxx_index.py.
#  2) Run this script to generate the geometry tables in the output tree.
#
################################################################################
import metadata as meta
import metadata.geometry_support as geom

parser = meta.get_geometry_args(host='GOISS', 
                                selection="S", exclude=['GO_0999'])
args = parser.parse_args()

geom.process_index(args.input_tree, args.output_tree, volume=args.volume,
                   selection=args.selection, exclude=args.exclude, 
                   glob='GO_????_index.lbl')
################################################################################