# MrgSelection Selection handling
#
# Copyright (C) 2021  Juan Pablo Ugarte
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
#
# library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# Authors:
#   Juan Pablo Ugarte <juanpablougarte@gmail.com>
#
# SPDX-License-Identifier: LGPL-2.1-only
#

from gi.repository import GObject, Gtk

from merengue import utils, MrgPlaceholder


class FindInContainerData:
    def __init__(self, toplevel, x, y):
        self.toplevel = toplevel
        self.x = x
        self.y = y
        self.child = None
        self.level = None


class MrgSelection(GObject.GObject):
    app = GObject.Property(type=GObject.GObject, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.__selecting = False
        self._container = None
        self.gesture = None

        super().__init__(**kwargs)

    @GObject.property(type=Gtk.Widget)
    def container(self):
        return self._container

    @container.setter
    def _set_container(self, obj):
        self._container = obj

        if self._container:
            self.gesture = utils.gesture_click_new(self._container, propagation_phase=Gtk.PropagationPhase.CAPTURE)
            self.gesture.connect("pressed", self.__on_gesture_button_pressed)
            self.gesture.connect("released", self.__on_gesture_button_released)
        elif self.gesture:
            self.gesture.disconnect_by_func(self.__on_gesture_button_pressed)
            self.gesture.disconnect_by_func(self.__on_gesture_button_released)
            self.gesture = None

    def __on_gesture_button_pressed(self, gesture, n_press, x, y):
        child = self.get_child_at_position(self._container, x, y)

        if isinstance(child, MrgPlaceholder):
            controller = child.controller

            # Write placeholder selected/activated message
            if n_press == 2:
                child.activated()
            else:
                child.selected()
        else:
            controller = self.app.get_controller_from_object(child)

        if controller is None or controller.selected:
            return

        object_id = utils.object_get_id(controller.object)
        if object_id is None:
            return

        # Select widget on button release only if its preselected
        self.app.write_command("selection_changed", args={"selection": [object_id]})
        controller.selected = True

        if not isinstance(child, Gtk.Window) and not isinstance(child, Gtk.HeaderBar):
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.__selecting = True

    def __on_gesture_button_released(self, gesture, n_press, x, y):
        if self.__selecting:
            gesture.set_state(Gtk.EventSequenceState.CLAIMED)
            self.__selecting = False

    def is_widget_from_ui(self, obj):
        if isinstance(obj, MrgPlaceholder):
            return True

        object_id = utils.object_get_builder_id(obj)
        return object_id is not None and object_id.startswith("__cmb__")

    def _find_first_child_inside_container(self, widget, data):
        if data.child is not None or not widget.get_mapped():
            return

        x, y = data.toplevel.translate_coordinates(widget, data.x, data.y)

        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        if x >= 0 and x < w and y >= 0 and y < h:
            from_ui = self.is_widget_from_ui(widget)

            if issubclass(type(widget), Gtk.Container):
                if from_ui:
                    data.child = self.get_child_at_position(widget, x, y)
                else:
                    widget.forall(self._find_first_child_inside_container, data)

            if data.child is None and from_ui:
                data.child = widget

    def get_child_at_position(self, widget, x, y):
        if Gtk.MAJOR_VERSION == 4:
            pick = widget.pick(x, y, Gtk.PickFlags.INSENSITIVE | Gtk.PickFlags.NON_TARGETABLE)
            while pick and not self.is_widget_from_ui(pick):
                pick = pick.props.parent
            return pick

        if not widget.get_mapped():
            return None

        w = widget.get_allocated_width()
        h = widget.get_allocated_height()

        if x >= 0 and x <= w and y >= 0 and y <= h:
            if issubclass(type(widget), Gtk.Container):
                data = FindInContainerData(widget, x, y)

                widget.forall(self._find_first_child_inside_container, data)

                return data.child if data.child is not None else widget
            else:
                return widget

        return None

