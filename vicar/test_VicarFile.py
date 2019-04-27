import random
import unittest

from VicarFile import *
from VicarFile import _VicarSyntax

if TYPE_CHECKING:
    from typing import Iterable


class VicarSyntaxTests(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def args_for_test(self):
        # type: () -> Iterable[_VicarSyntax]
        """
        Some interesting (or not) values for testing.
        """
        pass

    def assertEqual(self, first, second, msg=None):
        assert False, 'should be overridden'

    def test_equal(self):
        # type: () -> None
        """
        Verify that equality is reflexive on the given values.
        """
        for arg in self.args_for_test():
            self.assertEqual(arg, arg)

    def test_to_byte_length(self):
        # type: () -> None
        """
        Verify that to_byte_length() yields the same as (the possibly less
        efficient) length of the result of to_byte_string().
        """
        for arg in self.args_for_test():
            self.assertEqual(len(arg.to_byte_string()), arg.to_byte_length())

    def test_to_padded_byte_string(self):
        # type: () -> None
        """
        Verify that to_padded_byte_string(recsize) yields a string of
        a length that's a multiple of recsize.
        """
        for arg in self.args_for_test():
            byte_str = arg.to_byte_string()
            byte_len = arg.to_byte_length()

            if byte_len:
                # check that it won't pad at all if not necessary
                padded_byte_str = arg.to_padded_byte_string(byte_len)
                self.assertEqual(byte_str, padded_byte_str)

            # check that it pads properly in other cases:
            recsize = random.randint(256, 2048)
            padded_byte_str = arg.to_padded_byte_string(recsize)
            # that the length is a multiple
            self.assertEqual(0, len(padded_byte_str) % recsize)
            # and that the initial part of the string is untouched
            self.assertEqual(byte_str, padded_byte_str[:byte_len])

    def test_repr(self):
        """
        Verify that evaluating repr(arg) is equal to arg.
        """
        for arg in self.args_for_test():
            self.assertEqual(arg, eval(str(arg)), str(arg))


class TestValue(unittest.TestCase, VicarSyntaxTests):
    def test__eq__(self):
        self.assertTrue(IntegerValue('3') == IntegerValue('3'))
        self.assertFalse(IntegerValue('3') == RealValue('3.'))
        self.assertTrue(RealValue('3.') == RealValue('3.'))
        self.assertTrue(
            StringValue("'foo'") == StringValue.from_raw_string('foo'))

    def args_for_test(self):
        return [IntegerValue('3'), StringValue.from_raw_string('foobar'),
                RealValue('3.14159265')]

    def test__str__(self):
        self.assertEqual("IntegerValue('3')", str(IntegerValue('3')))
        self.assertEqual("RealValue('3.')", str(RealValue('3.')))
        self.assertEqual(
            """StringValue("'I don''t like that.'")""",
            str(StringValue.from_raw_string("I don't like that.")))


class TestLabelItem(unittest.TestCase, VicarSyntaxTests):
    def test__init__(self):
        str_value = StringValue.from_raw_string('foo')
        # verify that bad inputs raise exception
        with self.assertRaises(Exception):
            LabelItem(None, None, '=', str_value, None)
        with self.assertRaises(Exception):
            LabelItem(None, 'KEYWORD', None, str_value, None)
        with self.assertRaises(Exception):
            LabelItem(None, 'KEYWORD', '=', None, None)
        with self.assertRaises(Exception):
            LabelItem(None, 'KEYWORD', '=', 'foo', None)

        # verify that this does not raise
        LabelItem(None, 'KEYWORD', ' =  ', str_value, ' ')

    def args_for_test(self):
        exotic_label_item = LabelItem('   ', 'SHERPA_HOME', ' \t   =\n\n',
                                      StringValue.from_raw_string('Nepal'),
                                      '  ')
        return [LabelItem('    ', 'TRES', '=', IntegerValue('3'), '      '),
                exotic_label_item,
                exotic_label_item.to_saved_label_item('PREFIX_')
                ]

    def test_to_saved_string_value(self):
        # works for basic LabelItems
        label_item = LabelItem.create('FIVE_IS_EVEN', IntegerValue('0'))
        self.assertEqual(StringValue("'FIVE_IS_EVEN=0 '"),
                         label_item.to_saved_string_value())

        # works for LabelItems with crazy whitespace
        label_item = LabelItem('   ', 'SHERPA_HOME', ' \t   =\n\n',
                               StringValue.from_raw_string('Nepal'), '  ')
        self.assertEqual(StringValue(
            "'   SHERPA_HOME \t   =\n\n''Nepal''  '"),
            label_item.to_saved_string_value())

    def test_to_saved_label_item(self):
        label_item = LabelItem.create('FIVE_IS_EVEN', IntegerValue('0'))
        expected = LabelItem.create('MAIN_FIVE_IS_EVEN',
                                    StringValue("'FIVE_IS_EVEN=0 '"))
        self.assertEqual(expected, label_item.to_saved_label_item('MAIN_'))


_ENG = ['FOUR', 'FIVE', 'SIX', 'SEVEN']  # type: List[str]

_SPAN = ['cuatro', 'cinco', 'seis', 'siete']  # type: List[str]

_PORT = ['quatro', 'cinco', 'seis', 'sete']  # type: List[str]


def _mk_label_items_from_lists(keys, value_strs):
    # type: (List[str], List[str]) -> List[LabelItem]
    """
    Make LabelItems from a list of keys and a list of strings to be turned
    into StringValues.
    """
    return [LabelItem.create(k, StringValue.from_raw_string(v))
            for k, v in zip(keys, value_strs)]


def _mk_system_labels_from_lists(keys, value_strs):
    # type: (List[str], List[str]) -> SystemLabels
    """
    Make a SystemLabels whose LabelItems come from a list of keys and a list
    of strings to be turned into StringValues.
    """
    return SystemLabels(_mk_label_items_from_lists(keys, value_strs))


def _mk_sqr_label_items():
    """
    Make a bunch of LabelItems showing squares of
    integers.
    """
    return [LabelItem.create('SQR_%d' % i, IntegerValue(str(i * i)))
            for i in range(1, 100)]


def _mk_sqr_system_labels():
    """
    Make a SystemLabels containing a bunch of LabelItems showing squares of
    integers.
    """
    return SystemLabels(_mk_sqr_label_items())


class TestSystemLabels(unittest.TestCase, VicarSyntaxTests):
    def test__init__(self):
        # verify that bad inputs raise exception
        with self.assertRaises(Exception):
            SystemLabels(None)
        with self.assertRaises(Exception):
            SystemLabels([None])
        with self.assertRaises(Exception):
            SystemLabels([1, 2, 3])

        # verify that this does not raise
        SystemLabels([LabelItem.create('ONE',
                                       StringValue.from_raw_string('uno')),
                      LabelItem.create('TWO',
                                       IntegerValue('2')),
                      ])

    def args_for_test(self):
        return [SystemLabels([]),
                SystemLabels([LabelItem.create('ONE',
                                               StringValue.from_raw_string(
                                                   'uno')),
                              LabelItem.create('TWO',
                                               IntegerValue(
                                                   '2')),
                              ]),
                _mk_sqr_system_labels(),
                _mk_system_labels_from_lists(_ENG, _SPAN)]

    def test_select_labels(self):
        sqr_system_labels = _mk_sqr_system_labels()

        keywords = ['SQR_20', 'SQR_3']
        selected = sqr_system_labels.select_labels(keywords)

        expected_1 = LabelItem.create('SQR_3', IntegerValue('9'))
        expected_2 = LabelItem.create('SQR_20', IntegerValue('400'))
        expected = [expected_1, expected_2]

        self.assertEqual(expected, selected)

        # verify that bad inputs raise exception
        with self.assertRaises(Exception):
            sqr_system_labels.select_labels(None)

    def test_replace_label_items(self):
        eng_to_span = _mk_system_labels_from_lists(_ENG, _SPAN)
        eng_to_port = _mk_system_labels_from_lists(_ENG, _PORT)

        # by changing a few words, we can turn Spanish into Portuguese
        port_replacements = [
            LabelItem.create('SEVEN', StringValue.from_raw_string('sete')),
            LabelItem.create('FOUR', StringValue.from_raw_string('quatro'))
        ]

        # check that it changed
        self.assertNotEqual(eng_to_span,
                            eng_to_span.replace_label_items(port_replacements))

        # check that it changed to the right thing
        self.assertEqual(eng_to_port,
                         eng_to_span.replace_label_items(port_replacements))

        # verify that bad inputs raise exception
        with self.assertRaises(Exception):
            eng_to_span.replace_label_items(None)

    def test_lookup_label_items(self):
        eng_to_span = _mk_system_labels_from_lists(_ENG, _SPAN)
        threes = eng_to_span.lookup_label_items('THREE')
        self.assertEqual([], threes)

        fours = eng_to_span.lookup_label_items('FOUR')
        self.assertEqual(1, len(fours))
        self.assertEqual(
            [LabelItem.create('FOUR', StringValue.from_raw_string('cuatro'))],
            fours)

        # verify that bad inputs raise exception
        with self.assertRaises(Exception):
            eng_to_span.lookup_label_items(None)

    def test_get_int_value(self):
        system_labels = SystemLabels([])
        self.assertEqual(0, system_labels.get_int_value('FOO'))
        self.assertEqual(666, system_labels.get_int_value('FOO', 666))

        system_labels = SystemLabels([
            LabelItem.create('ONE', IntegerValue('1')),
            LabelItem.create('AMBIGUOUS', IntegerValue('123')),
            LabelItem.create('AMBIGUOUS', IntegerValue('456')),
            LabelItem.create('STRING', StringValue.from_raw_string('foobar'))
        ])

        self.assertEqual(0, system_labels.get_int_value('FOO'))
        self.assertEqual(666, system_labels.get_int_value('FOO', 666))
        self.assertEqual(1, system_labels.get_int_value('ONE'))
        self.assertEqual(1, system_labels.get_int_value('ONE', 666))

        with self.assertRaises(Exception):
            # multiple labels match
            system_labels.get_int_value('AMBIGUOUS')

        with self.assertRaises(Exception):
            # a mistyped value: it's string
            system_labels.get_int_value('STRING')
        with self.assertRaises(Exception):
            # a default answer doesn't fix a mistyped value
            system_labels.get_int_value('STRING', 666)


def _mk_map_property():
    # type: () -> Property
    """
    Make a sample property.  Example taken from the VICAR File Format,
    https://www-mipl.jpl.nasa.gov/external/VICAR_file_fmt.pdf
    """
    return Property(
        [LabelItem.create('PROPERTY', StringValue.from_raw_string('MAP')),
         LabelItem.create('PROJECTION',
                          StringValue.from_raw_string('mercator')),
         LabelItem.create('LAT', RealValue('34.2')),
         LabelItem.create('LON', RealValue('177.221'))])


class TestProperty(unittest.TestCase, VicarSyntaxTests):
    def test__init__(self):
        # verify that bad inputs raise an exception
        with self.assertRaises(Exception):
            Property(None)
        with self.assertRaises(Exception):
            Property([None])
        with self.assertRaises(Exception):
            Property([1, 2, 3])

        # verify that this does not raise
        _mk_map_property()

    def args_for_test(self):
        return [Property([]),
                _mk_map_property()]


class TestPropertyLabels(unittest.TestCase, VicarSyntaxTests):
    def test__init__(self):
        # verify that bad inputs raise an exception
        with self.assertRaises(Exception):
            PropertyLabels(None)
        with self.assertRaises(Exception):
            PropertyLabels([None])
        with self.assertRaises(Exception):
            PropertyLabels([1, 2, 3])

    def args_for_test(self):
        return [PropertyLabels([]),
                PropertyLabels([_mk_map_property()])]


def _mk_label_task():
    return Task.create('LABEL', 'RGD059', 'Thu Sep 24 17:32:54 1992')


class TestTask(unittest.TestCase, VicarSyntaxTests):
    def test__init__(self):
        # verify that bad inputs raise an exception
        with self.assertRaises(Exception):
            Task(None)
        with self.assertRaises(Exception):
            Task([None, None, None])
        with self.assertRaises(Exception):
            Task([1, 2, 3])
        with self.assertRaises(Exception):
            # missing TASK
            Task([
                LabelItem.create('USER', StringValue.from_raw_string('bar')),
                LabelItem.create('DAT_TIM',
                                 StringValue.from_raw_string('baz')),
                LabelItem.create('SOMETHING_ELSE',
                                 StringValue.from_raw_string('baz'))
            ])
        with self.assertRaises(Exception):
            # missing USER
            Task([
                LabelItem.create('TASK', StringValue.from_raw_string('foo')),
                LabelItem.create('DAT_TIM',
                                 StringValue.from_raw_string('baz')),
                LabelItem.create('SOMETHING_ELSE',
                                 StringValue.from_raw_string('baz'))
            ])
        with self.assertRaises(Exception):
            # missing DAT_TIM
            Task([
                LabelItem.create('TASK', StringValue.from_raw_string('foo')),
                LabelItem.create('USER', StringValue.from_raw_string('bar')),
                LabelItem.create('SOMETHING_ELSE',
                                 StringValue.from_raw_string('baz'))
            ])

        with self.assertRaises(Exception):
            # out of order
            Task([
                LabelItem.create('TASK', StringValue.from_raw_string('foo')),
                LabelItem.create('DAT_TIM',
                                 StringValue.from_raw_string('baz')),
                LabelItem.create('USER', StringValue.from_raw_string('bar')),
            ])

        # verify that this does not raise
        _mk_label_task()

    def test_create(self):
        # make a task; verify its values
        task = Task.create('CLEAN_UP', 'JacquesCustodian', 'dat_tim goes here')
        self.assertEqual(
            map(escape_byte_string,
                ['CLEAN_UP', 'JacquesCustodian', 'dat_tim goes here']),
            [label_item.value.value_byte_string
             for label_item in task.history_label_items])

        # make a task with an additional LabelItem; verify its values
        task = Task.create(
            'CLEAN_UP', 'JacquesCustodian', 'dat_tim goes here',
            LabelItem.create('REMINDER',
                             StringValue.from_raw_string('Recycle!')))

        self.assertEqual(
            [LabelItem.create('REMINDER',
                              StringValue.from_raw_string('Recycle!'))],
            task.history_label_items[3:])

    def test_create_migration_task(self):
        dat_tim = 'dat_tim goes here'

        # Create a simple task and check that the task contains the right
        # LabelItems
        task = Task.create_migration_task(dat_tim)
        expected_strs = [MIGRATION_TASK_NAME, MIGRATION_USER_NAME, dat_tim]
        self.assertEqual(map(escape_byte_string, expected_strs),
                         [label_item.value.value_byte_string
                          for label_item in
                          task.history_label_items[:3]])
        self.assertEqual([], task.history_label_items[3:])

        # Create a complicated task and check that the task contains the right
        # LabelItems
        extra_label_items = _mk_sqr_label_items()
        task = Task.create_migration_task(dat_tim, *extra_label_items)

        self.assertEqual(extra_label_items,
                         task.history_label_items[3:])

    def test_is_migration_task(self):
        # Not a migration task, but a conversion task, whatever that is.
        self.assertFalse(Task.create('PDS4 conversion',
                                     MIGRATION_USER_NAME,
                                     'dat_tim goes here').is_migration_task())

        # Looks like a migration task of ours, but the wrong user
        self.assertFalse(Task.create(MIGRATION_TASK_NAME,
                                     'some other guy',
                                     'dat_tim goes here').is_migration_task())

        # A true migration task
        self.assertTrue(Task.create_migration_task(
            'dat_tim goes here').is_migration_task())

    def args_for_test(self):
        return [_mk_label_task(),
                Task.create('CHORE', 'ChoreDoer', 'dat_tim'),
                Task.create('CALC_SQRS', 'SquarePants', 'dat_tim',
                            *_mk_sqr_label_items()),
                Task.create_migration_task('dat_tim'),
                Task.create_migration_task('dat_tim', *_mk_sqr_label_items())
                ]
