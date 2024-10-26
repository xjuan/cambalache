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
from .control import cmb_create_editor, CmbEnumComboBox
from .cmb_property_label import CmbPropertyLabel
from . import utils, _


class CmbAccessibleEditor(Gtk.Box):
    __gtype_name__ = "CmbAccessibleEditor"

    def __init__(self, **kwargs):
        self.__object = None
        self.__bindings = []
        self.__accessibility_metadata = None
        self.__role_filter_model = None

        super().__init__(**kwargs)

        self.props.orientation = Gtk.Orientation.VERTICAL

        self.__role_box = Gtk.Box(spacing=6)
        self.__role_box.append(Gtk.Label(label="accessible-role"))
        self.__role_combobox = CmbEnumComboBox()
        self.__role_box.append(self.__role_combobox)

        self.append(self.__role_box)

        self.__box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.append(self.__box)

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
        for child in utils.widget_get_children(self.__box):
            self.__box.remove(child)

        if self.__object is None:
            return

        obj = self.__object

        if obj.project.target_tk == "gtk-4.0":
            prop = self.__object.properties_dict["accessible-role"]
            role_data = self.__object.project.db.accessibility_metadata.get(prop.value, None)

            if role_data:
                role_properties = role_data["properties"]
                role_states = role_data["states"]
            else:
                role_properties = None
                role_states = None

            a11y_data = [
                ("CmbAccessibleProperty", _("Properties"), len("cmb-a11y-properties"), role_properties),
                ("CmbAccessibleState", _("States"), len("cmb-a11y-states"), role_states),
                ("CmbAccessibleRelation", _("Relations"), None, None),
            ]

            if not self.__object.info.is_a("GtkWidget"):
                self.__role_box.hide()
                return

            self.__role_box.show()
        else:
            type_actions = self.__object.project.db.accessibility_metadata.get(obj.type_id, [])

            a11y_data = [
                ("CmbAccessibleAction", _("Actions"), len("cmb-a11y-actions"), type_actions),
                ("CmbAccessibleProperty", _("Properties"), None, None),
                ("CmbAccessibleRelation", _("Relations"), None, None),
            ]
            self.__role_box.hide()

        properties = obj.properties_dict

        for owner_id, title, prefix_len, allowed_ids in a11y_data:
            info = obj.project.type_info.get(owner_id, None)

            if info is None:
                continue

            # Editor count
            i = 0

            # Grid for all editors
            grid = Gtk.Grid(hexpand=True, row_spacing=4, column_spacing=4)

            # Accessible iface properties
            for property_id in info.properties:
                # Ignore properties or status not for this role
                if prefix_len and allowed_ids is not None and property_id[prefix_len:] not in allowed_ids:
                    continue

                prop = properties.get(property_id, None)

                if prop is None or prop.info is None:
                    continue

                editor = cmb_create_editor(prop.project, prop.info.type_id, prop=prop)

                if editor is None:
                    return None, None

                self.bind_property(
                    prop,
                    "value",
                    editor,
                    "cmb-value",
                    GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
                )

                label = CmbPropertyLabel(prop=prop, bindable=False)
                grid.attach(label, 0, i, 1, 1)
                grid.attach(editor, 1, i, 1, 1)
                i += 1

            if i == 0:
                continue

            # Create expander/revealer to pack editor grid
            expander = Gtk.Expander(label=f"<b>{title}</b>", use_markup=True, expanded=True)
            revealer = Gtk.Revealer(reveal_child=True)
            expander.connect("notify::expanded", self.__on_expander_expanded, revealer)
            revealer.set_child(grid)
            self.__box.append(expander)
            self.__box.append(revealer)

        self.show()

    def __on_object_property_changed_notify(self, obj, prop):
        if prop.property_id == "accessible-role":
            self.__update_view()

    def __visible_func(self, model, iter, data):
        if self.__accessibility_metadata is None:
            return False

        name, nick, value = model[iter]

        role_data = self.__accessibility_metadata.get(nick, None)
        if role_data:
            # Ignore abstract roles
            if nick != "none" and role_data.get("is_abstract", False):
                return False

        return True

    @GObject.Property(type=CmbObject)
    def object(self):
        return self.__object

    @object.setter
    def _set_object(self, obj):
        if obj == self.__object:
            return

        if self.__object:
            self.__object.disconnect_by_func(self.__on_object_property_changed_notify)
            self.__role_combobox.props.model = None
            self.__accessibility_metadata = None

        for binding in self.__bindings:
            binding.unbind()

        self.__bindings = []
        self.__object = obj

        if self.__object and self.__object.info.is_a("GtkWidget"):
            self.__object.connect("property-changed", self.__on_object_property_changed_notify)

            self.__accessibility_metadata = self.__object.project.db.accessibility_metadata
            a11y_info = self.__object.project.type_info.get("GtkAccessibleRole", None)

            if a11y_info:
                a11y_info = self.__object.project.type_info.get("GtkAccessibleRole", None)

                self.__role_filter_model = Gtk.TreeModelFilter(child_model=a11y_info.enum)
                self.__role_filter_model.set_visible_func(self.__visible_func)
                self.__role_combobox.info = a11y_info
                self.__role_combobox.props.model = self.__role_filter_model

                prop = self.__object.properties_dict.get("accessible-role", None)
                self.bind_property(
                        prop,
                        "value",
                        self.__role_combobox,
                        "cmb-value",
                        GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
                    )

        self.__update_view()


Gtk.WidgetClass.set_css_name(CmbAccessibleEditor, "CmbAccessibleEditor")
