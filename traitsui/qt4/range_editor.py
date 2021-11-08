# ------------------------------------------------------------------------------
# Copyright (c) 2008, Riverbank Computing Limited
# All rights reserved.
#
# This software is provided without warranty under the terms of the BSD license.
# However, when used with the GPL version of PyQt the additional terms
# described in the PyQt GPL exception also apply

#
# Author: Riverbank Computing Limited
# ------------------------------------------------------------------------------

""" Defines the various range editors and the range editor factory, for the
PyQt user interface toolkit.
"""


import ast
from math import log10

from pyface.qt import QtCore, QtGui
from traits.api import TraitError, Str, Float, Any, Bool

# FIXME: ToolkitEditorFactory is a proxy class defined here just for backward
# compatibility. The class has been moved to the
# traitsui.editors.range_editor file.
from traitsui.editors.range_editor import ToolkitEditorFactory

from .editor_factory import TextEditor

from .editor import Editor

from .constants import OKColor, ErrorColor

from .helper import IconButton


# -------------------------------------------------------------------------
#  'BaseRangeEditor' class:
# -------------------------------------------------------------------------


class BaseRangeEditor(Editor):
    """ The base class for Range editors. Using an evaluate trait, if specified,
        when assigning numbers the object trait.
    """

    # -------------------------------------------------------------------------
    #  Trait definitions:
    # -------------------------------------------------------------------------

    #: Low value for the range
    low = Any()

    #: High value for the range
    high = Any()

    #: Function to evaluate floats/ints
    evaluate = Any()

    #: Formatting string used to format value and labels
    format = Str()

    #: Flag indicating that the UI is in the process of being updated
    ui_changing = Bool(False)

    def init(self, parent):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        self._init_with_factory_defaults()
        self.control = self._make_control()
        self._do_layout(self.control)

    def _init_with_factory_defaults(self):
        factory = self.factory
        # Initialize using the factory range defaults:
        if not factory.low_name:
            self.low = factory.low
        if not factory.high_name:
            self.high = factory.high
        self.evaluate = factory.evaluate

        # Hook up the traits to listen to the object.
        self.sync_value(factory.evaluate_name, "evaluate", "from")
        self.sync_value(factory.high_name, "high", "from")
        self.sync_value(factory.low_name, "low", "from")

    def _make_control(self):
        raise NotImplementedError

    def _make_text_entry(self, fvalue_text):
        text = QtGui.QLineEdit(fvalue_text)
        if self.factory.enter_set:
            text.returnPressed.connect(self.update_object_on_enter)
        text.editingFinished.connect(self.update_object_on_enter)
        if self.factory.auto_set:
            text.textChanged.connect(self.update_object_on_enter)
        # The default size is a bit too big and probably doesn't need to grow.
        sh = text.sizeHint()
        sh.setWidth(sh.width() / 2)
        text.setMaximumSize(sh)
        self.set_tooltip(text)

        return text

    def _do_layout(self, control):
        raise NotImplementedError

    def _set_format(self):
        self.format = self.factory.format

    def _set_value(self, value):
        if self.evaluate is not None:
            value = self.evaluate(value)
        super()._set_value(value)

    def _validate(self, value):
        if self.low is not None and value < self.low:
            message = "The value ({}) must be larger than {}!"
            raise ValueError(message.format(value, self.low))
        if self.high is not None and value > self.high:
            message = "The value ({}) must be smaller than {}!"
            raise ValueError(message.format(value, self.high))
        if not self.factory.is_float and isinstance(value, float):
            message = "The value must be an integer, but a value of {} was specified."
            raise ValueError(message.format(value))

    def _clip(self, fvalue, low, high):
        """ Returns fvalue clipped between low and high"""
#         try:
#             1 // (low <= value <= high)
#             text = self.format % fvalue
#         except:
#             text = ''
#             fvalue = low
#         return fvalue, text
        try:
            if not (low <= fvalue <= high):
                fvalue = min(max(low, fvalue), high)
        except:
            fvalue = low
        return fvalue

    def _set_color(self, color):
        if self.control is not None:
            pal = QtGui.QPalette(self.control.text.palette())
            pal.setColor(QtGui.QPalette.Base, color)
            self.control.text.setPalette(pal)

    def update_object_on_enter(self):
        """ Handles the user pressing the Enter key in the text field.
        """
        # it is possible we get the event after the control has gone away
        if self.control is None:
            return

        try:
            value = ast.literal_eval(self.control.text.text())
            self._validate(value)
            self.value = value
        except Exception as excp:
            # self._set_color(ErrorColor)
            self.error(excp)
            return

        if not self.ui_changing:
            self._set_slider(value)

        self._set_color(OKColor)
        if self._error is not None:
            self._error = None
            self.ui.errors -= 1

    def error(self, excp):
        """ Handles an error that occurs while setting the object's trait value.
        """
        if self._error is None:
            self._error = True
            self.ui.errors += 1
            super().error(excp)
        self.set_error_state(True)

    def update_editor(self, value=None):
        """ Updates the editor when the object trait changes externally to the
            editor.
        """
        if value is None:
            value = self.value
        fvalue = self._clip(value, self.low, self.high)
        text = self.format % fvalue

        self.ui_changing = True
        self.control.text.setText(text)
        self.ui_changing = False
        self._set_slider(fvalue)

    def _set_slider(self, value):
        """ Updates the slider range controls.
        """
        # Do nothing for non-sliders.

    def _get_current_range(self):
        low, high = self.low, self.high
        return low, high

    def get_error_control(self):
        """ Returns the editor's control for indicating error status.
        """
        return self.control.text

    def _low_changed(self, low):
        if self.value < low:
            self.value = float(low) if self.factory.is_float else int(low)

        if self.control is not None:
            self.update_editor()

    def _high_changed(self, high):
        if self.value > high:
            self.value = float(high) if self.factory.is_float else int(high)

        if self.control is not None:
            self.update_editor()


class SimpleSliderEditor(BaseRangeEditor):
    """ Simple style of range editor that displays a slider and a text field.

    The user can set a value either by moving the slider or by typing a value
    in the text field.
    """

    # -------------------------------------------------------------------------
    #  Trait definitions:  See BaseRangeEditor
    # -------------------------------------------------------------------------

    def _make_control(self):

        low, high = self._get_current_range()

        self._set_format()

        fvalue = self._clip(self.value, low, high)
        fvalue_text = self.format % fvalue

        width = self._get_default_width()

        control = QtGui.QWidget()
        control.label_lo = self._make_label_low(low, width)
        control.slider = self._make_slider(fvalue)
        control.label_hi = self._make_label_high(high, width)
        control.text = self._make_text_entry(fvalue_text)
        return control

    @staticmethod
    def _do_layout(control):
        layout = QtGui.QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(control.label_lo)
        layout.addWidget(control.slider)
        layout.addWidget(control.label_hi)
        layout.addWidget(control.text)

    def _get_default_width(self):
        return self.factory.label_width

    def _get_label_high(self, high):
        if self.factory.high_name != "":
            return self.format % high
        return self.factory.high_label

    def _get_label_low(self, low):
        if self.factory.low_name != "":
            return self.format % low
        return self.factory.low_label

    def _make_label_low(self, low, width):
        label_lo = QtGui.QLabel()
        label_lo.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        if width > 0:
            label_lo.setMinimumWidth(width)

        low_label = self._get_label_low(low)
        label_lo.setText(low_label)
        self.set_tooltip(label_lo)

        return label_lo

    def _make_slider(self, fvalue):
        ivalue = self._convert_to_slider(fvalue)
        slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        slider.setTracking(self.factory.auto_set)
        slider.setMinimum(0)
        slider.setMaximum(10000)
        slider.setPageStep(1000)
        slider.setSingleStep(100)
        slider.setValue(ivalue)
        slider.valueChanged.connect(self.update_object_on_scroll)
        self.set_tooltip(slider)

        return slider

    def _make_label_high(self, high, width):
        label_hi = QtGui.QLabel()
        if width > 0:
            label_hi.setMinimumWidth(width)
        high_label = self._get_label_high(high)
        label_hi.setText(high_label)
        self.set_tooltip(label_hi)

        return label_hi

    def update_object_on_scroll(self, pos):
        """ Handles the user changing the current slider value.
        """
        value = self._convert_from_slider(pos)
        try:
            self.ui_changing = True
            self.control.text.setText(self.format % value)
            self.value = value
        except TraitError:
            pass
        finally:
            self.ui_changing = False

    def _set_slider(self, value):
        """ Updates the slider range controls.
        """
        low, high = self._get_current_range()
        self.control.label_lo.setText(self.format % low)
        self.control.label_hi.setText(self.format % high)
        blocked = self.control.slider.blockSignals(True)
        try:
            ivalue = self._convert_to_slider(value)
            self.control.slider.setValue(ivalue)
        finally:
            self.control.slider.blockSignals(blocked)

    def _convert_to_slider(self, value):
        """ Returns the slider setting corresponding to the user-supplied value.
        """
        low, high = self._get_current_range()
        if high > low:
            return int(float(value - low) / (high - low) * 10000.0)
        return low

    def _convert_from_slider(self, ivalue):
        """ Returns the float or integer value corresponding to the slider
        setting.
        """
        low, high = self._get_current_range()
        value = low + ((float(ivalue) / 10000.0) * (high - low))
        if not self.factory.is_float:
            value = int(round(value))
        return value


# -------------------------------------------------------------------------
class LogRangeSliderEditor(SimpleSliderEditor):
    # -------------------------------------------------------------------------
    """ A slider editor for log-spaced values
    """

    def _convert_to_slider(self, value):
        """ Returns the slider setting corresponding to the user-supplied value.
        """
        low, high = self._get_current_range()
        value = max(value, low)
        return int((log10(value) - log10(low)) / (log10(high) - log10(low)) * 10000.0)

    def _convert_from_slider(self, ivalue):
        """ Returns the float or integer value corresponding to the slider
        setting.
        """
        low, high = self._get_current_range()
        value = float(ivalue) / 10000.0 * (log10(high) - log10(low))
        # Do this to handle floating point errors, where fvalue may exceed
        # self.high.
        fvalue = min(low * 10 ** (value), high)
        if not self.factory.is_float:
            fvalue = int(round(fvalue))
        return fvalue


class LargeRangeSliderEditor(SimpleSliderEditor):
    """ A slider editor for large ranges.

    The editor displays a slider and a text field. A subset of the total
    range is displayed in the slider; arrow buttons at each end of the
    slider let the user move the displayed range higher or lower.
    """

    # -------------------------------------------------------------------------
    #  Trait definitions: See BaseRangeEditor
    # -------------------------------------------------------------------------

    #: Low end of displayed slider range
    cur_low = Float()

    #: High end of displayed slider range
    cur_high = Float()

    def init(self, parent):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        self._init_with_factory_defaults()
        self.init_current_range(self.value)
        self.control = self._make_control(parent)
        # Set-up the layout:
        self._do_layout(self.control)

    def _make_control(self, parent):
        control = super()._make_control()
        low, high = self._get_current_range()

        control.button_lo = self._make_button_low(low)
        control.button_hi = self._make_button_high(high)
        return control

    @staticmethod
    def _do_layout(control):
        layout = QtGui.QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(control.label_lo)
        layout.addWidget(control.button_lo)
        layout.addWidget(control.slider)
        layout.addWidget(control.button_hi)
        layout.addWidget(control.label_hi)
        layout.addWidget(control.text)

    def _make_button_low(self, low):
        button_lo = IconButton(QtGui.QStyle.SP_ArrowLeft, self.reduce_range)
        button_lo.setEnabled(low != self.low)
        return button_lo

    def _make_button_high(self, high):
        button_hi = IconButton(QtGui.QStyle.SP_ArrowRight, self.increase_range)
        button_hi.setEnabled(high != self.high)
        return button_hi

    def _set_slider(self, value):
        """ Updates the slider range controls.
        """
        low, high = self._get_current_range()
        if not low <= value <= high:
            low, high = self.init_current_range(value)
        ivalue = self._convert_to_slider(value)
        blocked = self.control.slider.blockSignals(True)
        try:
            self.control.slider.setValue(ivalue)
        finally:
            self.control.slider.blockSignals(blocked)

        self._set_format()
        self.control.label_lo.setText(self.format % low)
        self.control.label_hi.setText(self.format % high)
        self.control.button_lo.setEnabled(low != self.low)
        self.control.button_hi.setEnabled(high != self.high)

    def init_current_range(self, value):
        """ Initializes the current slider range controls, cur_low and cur_high.
        """
        low, high = self.low, self.high
#         if (high is None) and (low is not None):
#             high = -low
        mag = max(abs(value), 1)
        rounded_value = 10 ** int(log10(mag))
        fact_hi, fact_lo = (10, 1) if value >= 0 else (-1, -10)
        cur_low = rounded_value * fact_lo
        cur_high = rounded_value * fact_hi
        if mag <= 10:
            if value >= 0:
                cur_low *= -1
            else:
                cur_high *= -1

        self.cur_low, self.cur_high = max(cur_low, low), min(cur_high, high)
        return self.cur_low, self.cur_high

    def reduce_range(self):
        """ Reduces the extent of the displayed range.
        """
        value = self.value
        low = self.low

        old_cur_low = self.cur_low
        if abs(self.cur_low) < 10:
            value = value - 10
            self.cur_low = max(-10, low)
            if old_cur_low - self.cur_low > 9:
                self.cur_high = old_cur_low
        else:
            fact = 0.1 if self.cur_low > 0 else 10
            value = value * fact
            new_cur_low = self.cur_low * fact
            self.cur_low = max(low, new_cur_low)
            if self.cur_low == new_cur_low:
                self.cur_high = old_cur_low

        value = min(max(value, self.cur_low), self.cur_high)

        if self.factory.is_float is False:
            value = int(value)
        self.value = value
        self.update_editor()

    def increase_range(self):
        """ Increased the extent of the displayed range.
        """
        value = self.value
        high = self.high
        old_cur_high = self.cur_high
        if abs(self.cur_high) < 10:
            value = value + 10
            self.cur_high = min(10, high)
            if self.cur_high - old_cur_high > 9:
                self.cur_low = old_cur_high
        else:
            fact = 10 if self.cur_high > 0 else 0.1
            value = value * fact
            new_cur_high = self.cur_high * fact
            self.cur_high = min(high, new_cur_high)
            if self.cur_high == new_cur_high:
                self.cur_low = old_cur_high

        value = min(max(value, self.cur_low), self.cur_high)

        if self.factory.is_float is False:
            value = int(value)

        self.value = value
        self.update_editor()

    def _set_format(self):
        self.format = "%d"
        if self.factory.is_float:
            low, high = self._get_current_range()
            diff = high - low
            if diff > 99999:
                self.format = "%.2g"
            elif diff > 1:
                self.format = "%%.%df" % max(0, 4 - int(log10(diff)))
            else:
                self.format = "%.3f"

    def _get_current_range(self):
        return self.cur_low, self.cur_high


class SimpleSpinEditor(BaseRangeEditor):
    """ A simple style of range editor that displays a spin box control.

    - ``Shift`` + arrow = 2 * increment        (or ``Shift`` + mouse wheel);
    - ``Ctrl``  + arrow = 10 * increment       (or ``Ctrl`` + mouse wheel);
    - ``Alt``   + arrow = 100 * increment      (or ``Alt`` + mouse wheel);
    - Combinations of ``Shift``, ``Ctrl``, ``Alt`` increment the
      :class:`SimpleSpinEditor` value by the product of the factors;

    """

    # -------------------------------------------------------------------------
    #  Trait definitions:  See BaseRangeEditor
    # -------------------------------------------------------------------------

    #: Step value for the spinner
    step = Any(1)

    def init(self, parent):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        self._init_with_factory_defaults()
        self.control = self._make_control()
        self._do_layout(self.control)

    def _make_control(self):

        low, high = self._get_current_range()

        self._set_format()

        fvalue = self._clip(self.value, low, high)
        fvalue_text = self.format % fvalue

        control = QtGui.QWidget()
        control.text = self._make_text_entry(fvalue_text)
        control.button_lo = self._make_button_low(fvalue)
        control.button_hi = self._make_button_high(fvalue)
        return control

    def _make_text_entry(self, fvalue_text):
        text = super()._make_text_entry(fvalue_text)
        # text.Bind(wx.EVT_MOUSEWHEEL, self.on_mouse_wheel)
        return text

    @staticmethod
    def _do_layout(control):
        layout = QtGui.QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(control.text)
        vwidget = QtGui.QWidget()
        vlayout = QtGui.QVBoxLayout(vwidget)
        vlayout.addWidget(control.button_hi)
        vlayout.addWidget(control.button_lo)
        layout.addWidget(vwidget)

    def _make_button_low(self, value):
        button_lo = IconButton(QtGui.QStyle.SP_ArrowDown, self.spin_down)
        button_lo.setEnabled(value >= self.low)
        return button_lo

    def _make_button_high(self, value):
        button_hi = IconButton(QtGui.QStyle.SP_ArrowUp, self.spin_up)
        button_hi.setEnabled(value <= self.high)
        return button_hi

    def _spin(self, step):
        value = self.value
        low, high = self._get_current_range()

        value = min(max(value + step, low), high)

        if self.factory.is_float is False:
            value = int(value)
        self.value = value
        self.update_editor()

    def _get_modifier(self):
        QModifiers = QtGui.QApplication.keyboardModifiers()
        modifier = float(self.step)
        if (QModifiers & QtCore.Qt.ShiftModifier) == QtCore.Qt.ShiftModifier:
            modifier *= 2
        if (QModifiers & QtCore.Qt.ControlModifier) == QtCore.Qt.ControlModifier:
            modifier *= 10
        if (QModifiers & QtCore.Qt.AltModifier) == QtCore.Qt.AltModifier:
            modifier *= 100
        return modifier

    def spin_down(self):
        """ Reduces the extent of the displayed range.
        """
        step = -1 * self._get_modifier()
        self._spin(step)

    def spin_up(self):
        """ Increased the extent of the displayed range.
        """
        step = self._get_modifier()
        self._spin(step)

    def on_mouse_wheel(self, event):
        sign = -1 if event.WheelRotation < 0 else 1
        step = sign * self._get_modifier()
        self._spin(step)

    def _set_slider(self, value):
        """ Updates the slider range controls.
        """
        low, high = self._get_current_range()
        self.control.button_lo.setEnabled(low < value)
        self.control.button_hi.setEnabled(value < high)


class RangeTextEditor(TextEditor):
    """Editor for ranges that displays a text field.

    If the user enters a value that is outside the allowed range,
    the background of the field changes color to indicate an error.
    """

    # -------------------------------------------------------------------------
    #  Trait definitions:
    # -------------------------------------------------------------------------

    #: Low value for the range
    low = Any()

    #: High value for the range
    high = Any()

    #: Function to evaluate floats/ints
    evaluate = Any()

    def init(self, parent):
        """ Finishes initializing the editor by creating the underlying toolkit
            widget.
        """
        super().init(parent)
        if not self.factory.low_name:
            self.low = self.factory.low

        if not self.factory.high_name:
            self.high = self.factory.high

        self.sync_value(self.factory.low_name, "low", "from")
        self.sync_value(self.factory.high_name, "high", "from")

        self.evaluate = self.factory.evaluate
        self.sync_value(self.factory.evaluate_name, "evaluate", "from")

    def _validate(self, value):
        if self.low is not None and value < self.low:
            message = "The value ({}) must be larger than {}!"
            raise ValueError(message.format(value, self.low))
        if self.high is not None and value > self.high:
            message = "The value ({}) must be smaller than {}!"
            raise ValueError(message.format(value, self.high))
        if not self.factory.is_float and isinstance(value, float):
            message = "The value must be an integer, but a value of {} was specified."
            raise ValueError(message.format(value))

    def update_object(self):
        """ Handles the user entering input data in the edit control.
        """
        try:
            value = str(self.control.text())
            if self.evaluate is not None:
                value = self.evaluate(value)
            else:
                value = ast.literal_eval(value)

            self._validate(value)
            self.value = value
            col = OKColor
        except Exception as excp:
            # The conversion failed.
            self.error(excp)
            col = ErrorColor

        if self.control is not None:
            pal = QtGui.QPalette(self.control.palette())
            pal.setColor(QtGui.QPalette.Base, col)
            self.control.setPalette(pal)

    def _low_changed(self, low):
        if self.value < low:
            if self.factory.is_float:
                self.value = float(low)
            else:
                self.value = int(low)
        if self.control:
            self.control.setText(str(self.value))

    def _high_changed(self, high):
        if self.value > high:
            if self.factory.is_float:
                self.value = float(high)
            else:
                self.value = int(high)
        if self.control:
            self.control.setText(str(self.value))


# -------------------------------------------------------------------------
#  'SimpleEnumEditor' factory adaptor:
# -------------------------------------------------------------------------


def SimpleEnumEditor(parent, factory, ui, object, name, description):
    return CustomEnumEditor(
        parent, factory, ui, object, name, description, "simple"
    )


def CustomEnumEditor(
    parent, factory, ui, object, name, description, style="custom"
):
    """ Factory adapter that returns a enumeration editor of the specified
    style.
    """
    if factory._enum is None:
        import traitsui.editors.enum_editor as enum_editor

        factory._enum = enum_editor.ToolkitEditorFactory(
            values=list(range(factory.low, factory.high + 1)),
            cols=factory.cols,
        )

    if style == "simple":
        return factory._enum.simple_editor(
            ui, object, name, description, parent
        )

    return factory._enum.custom_editor(ui, object, name, description, parent)


# -------------------------------------------------------------------------
#  Defines the mapping between editor factory 'mode's and Editor classes:
# -------------------------------------------------------------------------

# Mapping between editor factory modes and simple editor classes
SimpleEditorMap = {
    "slider": SimpleSliderEditor,
    "xslider": LargeRangeSliderEditor,
    "spinner": SimpleSpinEditor,
    "enum": SimpleEnumEditor,
    "text": RangeTextEditor,
    "logslider": LogRangeSliderEditor,
}
# Mapping between editor factory modes and custom editor classes
CustomEditorMap = {
    "slider": SimpleSliderEditor,
    "xslider": LargeRangeSliderEditor,
    "spinner": SimpleSpinEditor,
    "enum": CustomEnumEditor,
    "text": RangeTextEditor,
    "logslider": LogRangeSliderEditor,
}
