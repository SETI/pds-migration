##########################################################################################
# metadata_label.py
##########################################################################################
"""\
This program creates a PDS3 label for an index in the RMS node's PDS3 holdings/metadata
tree.

To use:
    > python metadata_label.py path/to/template.lbl path/to/metadata.tab ...

The first argument must be the path to the template file. Subsequent paths must point to
metadata index files. The program will create a label for each metadata table provided.

Note that the template must be customized to the format of each metadata file.
"""

import os
import shutil
import sys

from pdstemplate import PdsTemplate


if __name__ == '__main__':

    template = PdsTemplate(sys.argv[1], xml=False)
    for filepath in sys.argv[2:]:
        parts = os.path.splitext(filepath)
        label = parts[0] + '.lbl'
        print(label)

        backup = parts[0] + '-backup.lbl'
        if os.path.exists(label) and not os.path.exists(backup):
            shutil.move(label, backup)

        try:
            template.write({}, label)
        except Exception:
            if os.path.exists(backup):
                shutil.copy(backup, label)
            raise

##########################################################################################
