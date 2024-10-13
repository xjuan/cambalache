#
# CmbAccessibleEditor - Cambalache Accessible Editor
#
# Copyright (C) 2024  Juan Pablo Ugarte
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

from .cmb_object import CmbObject
from .control import cmb_create_editor
from .cmb_property_label import CmbPropertyLabel
from . import utils, _


class CmbAccessibleEditor(Gtk.Box):
    __gtype_name__ = "CmbAccessibleEditor"

    def __init__(self, **kwargs):
        self.__object = None
        self.__bindings = []

        super().__init__(**kwargs)

        self.props.orientation = Gtk.Orientation.VERTICAL

    def bind_property(self, *args):
        binding = GObject.Object.bind_property(*args)
        self.__bindings.append(binding)
        return binding

    def __on_expander_expanded(self, expander, pspec, revealer):
        expanded = expander.props.expanded

        if expanded:
            revealer.props.transition_type = Gtk.RevealerTransitionType.SLIDE_DOWN
        else:
            revealer.props.transition_type = Gtk.RevealerTransitionType.SLIDE_UP

        revealer.props.reveal_child = expanded

    def __update_view(self):
        for child in utils.widget_get_children(self):
            self.remove(child)

        if self.__object is None:
            return

        obj = self.__object

        properties = obj.properties_dict
        for owner_id, title in [
            ("CmbAccessibleProperty", _("Properties")),
            ("CmbAccessibleRelation", _("Relations")),
            ("CmbAccessibleState", _("States"))
        ]:
            info = obj.project.type_info.get(owner_id, None)

            if info is None:
                continue

            # Editor count
            i = 0

            # Grid for all editors
            grid = Gtk.Grid(hexpand=True, row_spacing=4, column_spacing=4)

            # Accessible iface properties
            for property_id in info.properties:
                prop = properties.get(property_id, None)

                if prop is None or prop.info is None:
                    continue

                editor = cmb_create_editor(prop.project, prop.info.type_id, prop=prop)

                if editor is None:
                    continue

                self.bind_property(
                    prop,
                    "value",
                    editor,
                    "cmb-value",
                    GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
                )

                label = CmbPropertyLabel(prop=prop, bindable=False)

                # TODO: add button to clear property

                grid.attach(label, 0, i, 1, 1)
                grid.attach(editor, 1, i, 1, 1)
                i += 1

            # Create expander/revealer to pack editor grid
            expander = Gtk.Expander(label=f"<b>{title}</b>", use_markup=True, expanded=True)
            revealer = Gtk.Revealer(reveal_child=True)
            expander.connect("notify::expanded", self.__on_expander_expanded, revealer)
            revealer.set_child(grid)
            self.append(expander)
            self.append(revealer)

        self.show()

    @GObject.Property(type=CmbObject)
    def object(self):
        return self.__object

    @object.setter
    def _set_object(self, obj):
        if obj == self.__object:
            return

        for binding in self.__bindings:
            binding.unbind()

        self.__bindings = []
        self.__object = obj

        self.__update_view()


Gtk.WidgetClass.set_css_name(CmbAccessibleEditor, "CmbAccessibleEditor")
