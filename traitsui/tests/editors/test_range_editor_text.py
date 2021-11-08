# ------------------------------------------------------------------------------
#
#  Copyright (c) 2012, Enthought, Inc.
#  All rights reserved.
#
#  This software is provided without warranty under the terms of the BSD
#  license included in LICENSE.txt and may be redistributed only
#  under the conditions described in the aforementioned license.  The license
#  is also available online at http://www.enthought.com/licenses/BSD.txt
#
#  Author: Pietro Berkes
#  Date:   Jan 2012
#
# ------------------------------------------------------------------------------

"""
Test case for bug (wx, Mac OS X)

A RangeEditor in mode 'text' for an Int or Float allows values out of range.
"""
# from traits.etsconfig.api import ETSConfig
# ETSConfig.toolkit = 'wx'
import pytest
from traits.has_traits import HasTraits
from traits.trait_types import Float, Int, Range
from traitsui.item import Item
from traitsui.view import View

from traitsui import editor
from traitsui.editors.range_editor import RangeEditor
from traitsui.tests._tools import (store_exceptions_on_all_threads,
                                   skip_if_null,
                                   set_text,
                                   press_ok_button)

editor.UNITTESTING = True  # if True raise error on all errors. Makes it easier to test
MODES = ("text", "slider", "xslider", "logslider", "spinner", "enum")
MODES = ("spinner", "enum")
OPTIONS = dict(show_error_dialog=False, auto_set=True, enter_set=False)


def gen_type_number_with_editor(type_, editor_, label, repr_):
    class TypeNumberWithRangeEditor(HasTraits):
        """Dialog containing a RangeEditor for a type_ like Int, Float or Range.
        """

        number = type_()

        traits_view = View(
            Item(label=label),
            Item("number", editor=editor_),
            buttons=["OK"])

        def __repr__(self):
            return repr_  # return test ID

    return TypeNumberWithRangeEditor()


def _make_valid_test_combinations(integers=tuple(range(3, 9)),
                                  floats=(3.5, 4.5, 7.5),
                                  modes=MODES):
    """Returns list of (number_with_editor, test_input, expected_output) tuples."""

    valid_test_combo = []
    for i, (type_, low, high) in enumerate([(Int, 3, 8), (Float, 3., 8.)]):
        label = ("Value can only be {} from {} to {} ".format(type_.info_text, low, high)
                 + "Check illegal values: 1, 10,..")
        if type_ is Int:
            valid_numbers = integers
            current_modes = modes
        else:
            valid_numbers = integers + floats
            current_modes = list(set(modes).difference(['enum']))

        for mode in current_modes:
            repr_ = "{} from {} to {} and mode={}".format(type_.info_text, low, high, mode)
            editor_ = RangeEditor(low=low, high=high, mode=mode, **OPTIONS)
            number_with_editor = gen_type_number_with_editor(type_, editor_, label, repr_)

            for valid_number in valid_numbers:
                valid_test_combo.append((number_with_editor, str(valid_number), valid_number))

    return valid_test_combo


def _make_invalid_test_combinations(integers=(-1, 2, 9, 10, '1+2', '2+2', '6-2'),
                                    floats=(-3.5, 14.5, 17.5, '1+2.2', '2+2.4', '6-5.2')):
    return [(num, tinput, ValueError)
            for num, tinput, _ in _make_valid_test_combinations(integers, floats, MODES[:-1])]
                                                    # Does not work for "enum"
                                                    # Works: 'text',"slider", "xslider","logslider",

class NumberWithRangeEditor(HasTraits):
    """Dialog containing a RangeEditor in 'text' mode for an Int.
    """

    number = Int()

    traits_view = View(
        Item(label="Value can only be an integer from 3 to 8. Check illegal values: 1, 4.5,.."),
        Item("number", editor=RangeEditor(low=3, high=8, mode="spinner", **OPTIONS)),
        buttons=["OK"],
    )


class FloatWithRangeEditor(HasTraits):
    """Dialog containing a RangeEditor in 'spinner' mode for a Float.
    """

    number = Float(5.0)

    traits_view = View(
        Item(label="Any real value allowed even if slider only goes from 0.0 to 12!"),
        Item("number", editor=RangeEditor(low=None, high=12.0, mode='xslider', **OPTIONS)),
        buttons=["OK"]
    )


class RangeWithTextEditor(HasTraits):
    """Dialog containing a RangeEditor in 'text' mode for a Range.
    """

    number = Range(high=-0.01, value=-10.)

    traits_view = View(
        Item(label="Any real value below -0.01 is allowed. Check illegal values: 1, 4.5,.."),
        Item("number"),
        buttons=["OK"],
    )


class IntRangeWithTextEditor(HasTraits):
    """Dialog containing a RangeEditor in 'text' mode for a Range.
    """

    number = Range(high=12, value=-10)

    traits_view = View(
        Item(label="Any real value below 12. is allowed. Check illegal values: 13, 4.5,.."),
        Item("number", editor=RangeEditor(low=None, high=12, mode='slider', **OPTIONS)),
        buttons=["OK"],
    )


@skip_if_null
@pytest.mark.parametrize("num,test_input,expected", _make_valid_test_combinations())
def test_number_with_range_editor_for_valid_input(num, test_input, expected):
    """
    Test that the integer number is updated to the expected value.

    When editing the text part of a text control box, pressing
    the OK button should update the value of the HasTraits class
    (tests a bug where it failed with an AttributeError)

    Note the test gives unpredictable results for values outside the 3 to 8 range!
    """

    with store_exceptions_on_all_threads():

        ui = num.edit_traits()

        set_text(ui, test_input)  # equivalent to setting the text in the text control
        press_ok_button(ui)  # pressing OK button and close the dialog

    print("Actual value:", num.number)
    assert 3 <= num.number <= 8
    assert num.number == expected


@skip_if_null
@pytest.mark.parametrize("num,test_input,expected_error", _make_invalid_test_combinations())
def test_number_with_range_editor_for_invalid_input(num, test_input, expected_error):
    """
    Test that the RangeEditor number complains about invalid input.

    Note that this test requires that editor.UNITTESTING == True
    so that it raises an error on all invalid input.

    """

    with pytest.raises(expected_error):
        with store_exceptions_on_all_threads():
            ui = num.edit_traits()
            set_text(ui, test_input)  # equivalent to setting the text in the text control


@skip_if_null
@pytest.mark.parametrize("test_input,expected", [("4", 4), ("6", 6), ("8", 8)])
def test_number_with_range_editor(test_input, expected):
    """
    Test that the integer number is updated to the expected value.

    When editing the text part of a text control box, pressing
    the OK button should update the value of the HasTraits class
    (tests a bug where it failed with an AttributeError)

    Note the test fails for input values outside the 3 to 8 range!
    """

    with store_exceptions_on_all_threads():
        num = NumberWithRangeEditor()
        ui = num.edit_traits()

        set_text(ui, test_input)  # equivalent to setting the text in the text control
        press_ok_button(ui)  # pressing OK button and close the dialog

    print("Actual value:", num.number)
    assert 3 <= num.number <= 8
    assert num.number == expected


@skip_if_null
@pytest.mark.parametrize("test_input,expected_error", [("10", ValueError),
                                                        ("1", ValueError),
                                                        ("4.5", ValueError)])
def test_invalid_numbers_with_range_editor(test_input, expected_error):
    """
    Test that the RangeEditor number complains about invalid input.

    Note that this test requires that editor.UNITTESTING == True
    so that it raises an error on all invalid input.

    Note the test gives unpredictable results for values outside the 3 to 8 range!
    """

    with pytest.raises(expected_error):
        with store_exceptions_on_all_threads():
            num = NumberWithRangeEditor()
            ui = num.edit_traits()
            set_text(ui, test_input)  # equivalent to setting the text in the text control
            press_ok_button(ui)


@skip_if_null
@pytest.mark.parametrize("test_input,expected", [("-4", -4), ("-10.5", -10.5)])
def test_range_with_range_editor(test_input, expected):
    """
    Test that the float is updated to the expected value.

    When editing the text part of a text control box, pressing
    the OK button should update the value of the HasTraits class
    (tests a bug where the num.number fails with an AttributeError)

    Note the test gives unpredictable results for values larger than -0.01!
    """

    with store_exceptions_on_all_threads():
        num = RangeWithTextEditor()
        # num.number = float(test_input)
        ui = num.edit_traits()

        # the following is equivalent to setting the text in the text control,
        # then pressing OK button and close the dialog.
        set_text(ui, test_input)
        press_ok_button(ui)

    # the number traits should be below -0.01
    print("Actual value:", num.number)
    assert num.number < -0.010001
    assert num.number == expected


@skip_if_null
@pytest.mark.parametrize("test_input,expected", [("1", 1), ("4.5", 4.5), ("10", 10)])
def test_float_with_range_editor(test_input, expected):
    """
    Test the slider and that the float is updated to the expected value.

    When editing the text box part of a range editor, the value
    should not be adjusted by the slider part of the range editor
    even if the value is outside the range from 0 to 12 of the RangeEditor!
    """

    with store_exceptions_on_all_threads():
        num = FloatWithRangeEditor()
        # num.number = float(test_input)
        ui = num.edit_traits()

        # the following is equivalent to setting the text in the text control,
        # then pressing OK button and close the dialog.
        set_text(ui, test_input)
        press_ok_button(ui)

    # the number trait should be extactly equal to the expected
    print(num.number)
    assert num.number == expected


def manual_testing():
    editor.UNITTESTING = False
    # Executing the file opens the dialog for manual testing
    num = NumberWithRangeEditor()
    # num = FloatWithRangeEditor()
    # num = IntRangeWithTextEditor()
    num.configure_traits()
    print(num.number)


if __name__ == "__main__":
    manual_testing()
