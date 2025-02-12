from typing import TYPE_CHECKING

from ImageArea import ImageArea
from Labels import Labels
from MigrationInfo import remove_migration_task
from Tail import Tail
from Value import IntegerValue
from VicarSyntax import VicarSyntax

if TYPE_CHECKING:
    from typing import List, Optional, Tuple
    from LabelItem import LabelItem


def _get_int_value(label_items, keyword, default=0):
    # type: (List[LabelItem], str, int) -> int
    label_items = [label_item
                   for label_item in label_items
                   if label_item.keyword == keyword]
    len_label_items = len(label_items)
    assert len_label_items <= 1
    if len_label_items:
        value = label_items[0].value
        assert isinstance(value, IntegerValue)
        return int(value.value_byte_string)
    else:
        return default


def parse_vicar_file(byte_str):
    # type: (str) -> Tuple[str, VicarFile]
    """
    Parse the given bytes into a VicarFile.  Return a 2-tuple of any
    remaining bytes (must be empty, by construction) and the VicarFile
    object.
    """
    from ImageArea import parse_image_area
    from Labels import parse_labels

    # Parse the labels.
    byte_str, labels = parse_labels(byte_str)

    # Extract info from the labels needed for further parsing.
    binary_header_size = labels.get_binary_header_size()
    image_height = labels.get_image_height()
    prefix_width = labels.get_binary_prefix_width()
    image_width = labels.get_image_width()

    # Parse the image area.
    byte_str, image_area = parse_image_area(binary_header_size,
                                            image_height,
                                            prefix_width,
                                            image_width,
                                            byte_str)

    # If there are EOL labels, parse them.
    has_eol_labels = labels.get_int_value('EOL')
    if has_eol_labels:
        byte_str, eol_labels = parse_labels(byte_str)
    else:
        eol_labels = None

    # Parse the tail as either PDS3 or PDS4 depending on whether the
    # image area has binary prefixes.
    has_binary_prefixes = image_area.has_binary_prefixes()
    if has_binary_prefixes:
        from Tail import parse_pds3_tail
        byte_str, tail = parse_pds3_tail(byte_str)
    else:
        # Figure out how long the binary header in the tail is.
        if False:
            migration_info, _history = remove_migration_task(
                labels.history_labels)
            old_label_items = migration_info.label_items
            old_nlb = _get_int_value(old_label_items, 'NLB')
            old_recsize = _get_int_value(old_label_items, 'RECSIZE')
            binary_header_length = old_nlb * old_recsize

        # Parse the tail.
        from Tail import parse_pds4_tail
        byte_str, tail = parse_pds4_tail(image_height,
                                         prefix_width,
                                         byte_str)

    assert not byte_str, 'should consume all input'

    # Return the result.
    return byte_str, VicarFile(labels, image_area, eol_labels, tail)


class VicarFile(VicarSyntax):
    """
    Represents a full VICAR file, whether unmigrated or migrated.
    """

    def __init__(self,
                 labels,
                 image_area,
                 eol_labels,
                 tail):
        # type: (Labels, ImageArea, Optional[Labels], Tail) -> None
        assert labels is not None
        assert isinstance(labels, Labels)
        assert image_area is not None
        assert isinstance(image_area, ImageArea)
        assert eol_labels is None or isinstance(labels, Labels)
        assert tail is not None
        assert isinstance(tail, Tail)

        # keyword EOL
        assert (labels.get_int_value('EOL') == 0) == (eol_labels is None), \
            'nonzero EOL keyword value exactly when eol_labels present'

        # keyword RECSIZE
        recsize = labels.get_int_value('RECSIZE')
        assert recsize > 0, 'RECSIZE is zero or missing'
        assert (recsize == image_area.implicit_recsize_value()), \
            ('RECSIZE value not correct for image; should be %d' %
             image_area.implicit_recsize_value())

        assert labels.to_byte_length() % recsize == 0, \
            'Size of labels must be a multiple of RECSIZE'
        
        assert image_area.to_byte_length() % recsize == 0, \
            'Size of image_area must be a multiple of RECSIZE'
        
        if eol_labels:
            assert eol_labels.to_byte_length() % recsize == 0, \
                'Size of eol_labels must be a multiple of RECSIZE'
        

        # keyword NBB
        assert (labels.get_int_value('NBB') ==
                image_area.implicit_nbb_value()), \
            ('NBB value not correct for image; is %d but should be %d' %
             (labels.get_int_value('NBB'), image_area.implicit_nbb_value()))

        # keyword NLB
        assert (labels.get_int_value('NLB') ==
                image_area.implicit_nlb_value()), \
            ('NLB value not correct for image; is %d but should be %d' %
             (labels.get_int_value('NLB'), image_area.implicit_nlb_value()))

        # keyword LBLSIZE
        assert labels.get_lblsize() % recsize == 0, \
            'LBLSIZE must be a multiple of RECSIZE'
        if eol_labels is not None:
            assert eol_labels.get_lblsize() % recsize == 0, \
                'EOL LBLSIZE must be a multiple of RECSIZE'

        # check structures

        # migration must remove binary prefixes
        assert not (image_area.has_binary_prefixes() and
                    labels.has_migration_task()), \
            'a migrated VICAR file cannot have binary prefixes'

        # binary prefixes either in ImageArea or Tail but not both
        assert not (image_area.has_binary_prefixes() and
                    tail.has_binary_prefixes()), \
            'binary prefixes cannot appear in both ImageArea and Tail'

        # I shouldn't need to check consistency of saved NBB, NLB, and
        # RECSIZE because they're right by construction.

        self.labels = labels
        self.image_area = image_area
        self.eol_labels = eol_labels
        self.tail = tail

    def __eq__(self, other):
        return [self.labels,
                self.image_area,
                self.eol_labels,
                self.tail] == [other.labels,
                               other.image_area,
                               other.eol_labels,
                               other.tail]

    def __repr__(self):
        return 'VicarFile(%r, %r, %r, %r)' % (self.labels,
                                              self.image_area,
                                              self.eol_labels,
                                              self.tail)

    def to_byte_length(self):
        if self.eol_labels is None:
            eol_labels_byte_length = 0
        else:
            eol_labels_byte_length = self.eol_labels.to_byte_length()
        return sum([self.labels.to_byte_length(),
                    self.image_area.to_byte_length(),
                    eol_labels_byte_length,
                    self.tail.to_byte_length()])

    def to_byte_string(self):
        if self.eol_labels is None:
            eol_labels_byte_string = ''
        else:
            eol_labels_byte_string = self.eol_labels.to_byte_string()
        return ''.join([self.labels.to_byte_string(),
                        self.image_area.to_byte_string(),
                        eol_labels_byte_string,
                        self.tail.to_byte_string()])

    def get_recsize(self):
        # type: () -> int
        """Return the RECSIZE."""
        return self.labels.get_int_value('RECSIZE')

    def has_binary_prefixes(self):
        # type: () -> bool
        """
        Return True if there are binary prefixes.
        """
        return self.image_area.has_binary_prefixes()

    def has_migration_task(self):
        # type: () -> bool
        """
        Return True if the last task in the HistoryLabels is a
        migration task.  It has to be the last task because we don't
        guarantee we can backmigrate the file if it's been further
        processed.
        """
        return self.labels.has_migration_task()
