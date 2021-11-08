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

Editing the text part of a spin control box and pressing the OK button
without de-focusing raises an AttributeError::

    Traceback (most recent call last):
    File "ETS/traitsui/traitsui/wx/range_editor.py", line 783, in update_object
        self.value = self.control.GetValue()
    AttributeError: 'NoneType' object has no attribute 'GetValue'
"""

from traits.has_traits import HasTraits
from traits.trait_types import Int, Float
from traitsui.item import Item
from traitsui.view import View
from traitsui.editors.range_editor import RangeEditor

from traitsui.tests._tools import (store_exceptions_on_all_threads,
                                   set_spinctrl_text,
                                   skip_if_null,
                                   press_ok_button)


class NumberWithSpinnerEditor(HasTraits):
    """Dialog containing a RangeEditor in 'spinner' mode for an Int.
    """

    number = Int()

    traits_view = View(
        Item(label="Enter 4, then press OK without defocusing"),
        Item("number", editor=RangeEditor(low=3, high=8, mode="spinner",
                                          show_error_dialog=False, auto_set=True, enter_set=True)),
        buttons=["OK"],
    )


class FloatWithSpinnerEditor(HasTraits):
    """Dialog containing a RangeEditor in 'spinner' mode for a Float.
    """

    number = Float(3.5)

    traits_view = View(
        Item(label="Enter 4, then press OK without defocusing"),
        Item("number", editor=RangeEditor(low=3., high=8., mode="spinner",
                                          show_error_dialog=False, auto_set=True, enter_set=True)),
        buttons=["OK"],
    )

@skip_if_null
def test_spin_control_editing():
    """ Test the spin controll and that the integer is updated to the expected value.

    Behavior: when editing the text part of a spin control box, pressing
    the OK button updates the value of the HasTraits class
    the following is equivalent to clicking in the text control of the
    range editor, enter a number, and clicking ok without defocusing

    Bug: when editing the text part of a spin control box, pressing
    the OK button does not update the value of the HasTraits class
    on Mac OS X under wx, but for wx >= 3.0 this has been resolved

    Bug: when editing the text part of a spin control box, pressing
    the OK button raises an AttributeError on Mac OS X
    """

    with store_exceptions_on_all_threads():
        num = NumberWithSpinnerEditor()
        ui = num.edit_traits()
        # text element inside the spin control
        set_spinctrl_text(ui, '4')
        # press the OK button and close the dialog
        press_ok_button(ui)

    # if all went well, the number traits has been updated and its value is 4
    assert num.number == 4


@skip_if_null
def test_float_spin_control_editing():
    """ Test the spin controll and that the integer is updated to the expected value.

    Behavior: when editing the text part of a spin control box, pressing
    the OK button updates the value of the HasTraits class
    the following is equivalent to clicking in the text control of the
    range editor, enter a number, and clicking ok without defocusing

    Bug: when editing the text part of a spin control box, pressing
    the OK button does not update the value of the HasTraits class
    on Mac OS X under wx, but for wx >= 3.0 this has been resolved

    Bug: when editing the text part of a spin control box, pressing
    the OK button raises an AttributeError on Mac OS X
    """

    with store_exceptions_on_all_threads():
        num = FloatWithSpinnerEditor()
        ui = num.edit_traits()
        # text element inside the spin control
        set_spinctrl_text(ui, '4.')
        # press the OK button and close the dialog
        press_ok_button(ui)

    # if all went well, the number traits has been updated and its value is 4
    assert num.number == 4


def manual_testing():
    # Executing the file opens the dialog for manual testing
    # num = NumberWithSpinnerEditor()
    num = FloatWithSpinnerEditor()
    num.configure_traits()
    print(num.number)


if __name__ == "__main__":
    manual_testing()
