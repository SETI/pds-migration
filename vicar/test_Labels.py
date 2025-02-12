import unittest

from HistoryLabels import HistoryLabels
from LabelItem import LabelItem
from Labels import Labels, parse_labels, round_to_multiple_of
from PropertyLabels import PropertyLabels
from SystemLabels import SystemLabels
from Value import IntegerValue
from VicarSyntaxTests import VicarSyntaxTests
from test_SystemLabels import gen_system_labels


class TestLabels(unittest.TestCase, VicarSyntaxTests):
    def test__init__(self):
        system_labels = SystemLabels.create_with_lblsize(1, [
            LabelItem.create('RECSIZE', IntegerValue('16'))
        ])
        property_labels = PropertyLabels([])
        history_labels = HistoryLabels([])
        # verify that bad inputs raise an exception
        with self.assertRaises(Exception):
            Labels(None, property_labels, history_labels, None)
        with self.assertRaises(Exception):
            Labels(system_labels, None, history_labels, None)
        with self.assertRaises(Exception):
            Labels(system_labels, property_labels, None, None)

        # verify that this does not raise
        Labels.create_labels_with_adjusted_lblsize(system_labels,
                                                   property_labels,
                                                   history_labels,
                                                   None)

    def args_for_test(self):
        system_labels = SystemLabels.create_with_lblsize(1, [
            LabelItem.create('RECSIZE', IntegerValue('16'))
        ])
        property_labels = PropertyLabels([])
        history_labels = HistoryLabels([])

        return [Labels.create_labels_with_adjusted_lblsize(system_labels,
                                                           property_labels,
                                                           history_labels,
                                                           None)]

    def syntax_parser_for_arg(self, arg):
        return parse_labels

    def test_create_with_lblsize(self):
        # should not throw
        Labels.create_labels_with_adjusted_lblsize(
            gen_system_labels(RECSIZE=1, LBLSIZE=1),
            PropertyLabels([]),
            HistoryLabels([]),
            None)


def test_round_to_multiple_of():
    for m in xrange(1, 100):
        for n in xrange(1, 100):
            assert round_to_multiple_of(n, m) % m == 0
