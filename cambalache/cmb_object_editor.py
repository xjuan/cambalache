#
# CmbObjectEditor - Cambalache Object Editor
#
# Copyright (C) 2021-2024  Juan Pablo Ugarte
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
from .cmb_object_data_editor import CmbObjectDataEditor
from .control import CmbEntry, CmbChildTypeComboBox, cmb_create_editor
from .cmb_property_label import CmbPropertyLabel
from cambalache import _
from .constants import EXTERNAL_TYPE
from . import utils


class CmbObjectEditor(Gtk.Box):
    __gtype_name__ = "CmbObjectEditor"

    layout = GObject.Property(type=bool, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY, default=False)

    def __init__(self, **kwargs):
        self.__object = None
        self.__id_label = None
        self.__template_switch = None
        self.__bindings = []

        super().__init__(**kwargs)

        self.props.orientation = Gtk.Orientation.VERTICAL

    def bind_property(self, *args):
        binding = GObject.Object.bind_property(*args)
        self.__bindings.append(binding)
        return binding

    def __create_id_editor(self):
        grid = Gtk.Grid(hexpand=True, row_spacing=4, column_spacing=4)

        # Label
        self.__id_label = Gtk.Label(label=_("Object Id"), halign=Gtk.Align.START)

        # Id/Class entry
        entry = CmbEntry()
        self.bind_property(
            self.__object,
            "name",
            entry,
            "cmb-value",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )

        grid.attach(self.__id_label, 0, 0, 1, 1)
        grid.attach(entry, 1, 0, 1, 1)

        # Template check
        if self.__object and self.__object.parent_id == 0:
            is_template = self.__object.object_id == self.__object.ui.template_id
            tooltip_text = _("Switch between object and template")
            derivable = self.__object.info.derivable

            if not derivable:
                tooltip_text = _("{type} is not derivable.").format(type=self.__object.info.type_id)

            label = Gtk.Label(label=_("Template"), halign=Gtk.Align.START, tooltip_text=tooltip_text, sensitive=derivable)
            self.__template_switch = Gtk.Switch(
                active=is_template, halign=Gtk.Align.START, tooltip_text=tooltip_text, sensitive=derivable
            )

            self.__template_switch.connect("notify::active", self.__on_template_switch_notify)
            self.__update_template_label()

            grid.attach(label, 0, 1, 1, 1)
            grid.attach(self.__template_switch, 1, 1, 1, 1)

        return grid

    def __on_shortcut_button_clicked(self, button, type_id):
        obj = self.__object
        obj.project.add_object(obj.ui_id, type_id, parent_id=obj.object_id)

    def __create_child_shortcuts(self, info):
        box = Gtk.FlowBox(visible=True, hexpand=True, selection_mode=Gtk.SelectionMode.NONE)

        label = Gtk.Label(label=_("Add"), xalign=0, visible=True)
        box.append(label)

        for type_id in info.child_type_shortcuts:
            button = Gtk.Button(label=type_id, visible=True)
            button.connect("clicked", self.__on_shortcut_button_clicked, type_id)
            box.append(button)

        return box

    def __update_template_label(self):
        istmpl = self.__object.ui.template_id == self.__object.object_id
        self.__id_label.props.label = _("Type Name") if istmpl else _("Object Id")

    def __on_template_switch_notify(self, switch, pspec):
        self.__object.ui.template_id = self.__object.object_id if switch.props.active else 0
        self.__update_template_label()

    def __on_expander_expanded(self, expander, pspec, revealer):
        expanded = expander.props.expanded

        if expanded:
            revealer.props.transition_type = Gtk.RevealerTransitionType.SLIDE_DOWN
        else:
            revealer.props.transition_type = Gtk.RevealerTransitionType.SLIDE_UP

        revealer.props.reveal_child = expanded

    def __create_child_type_editor(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        box.append(Gtk.Label(label=_("Child Type"), width_chars=8))

        combo = CmbChildTypeComboBox(object=self.__object)

        self.bind_property(
            self.__object,
            "type",
            combo,
            "cmb-value",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )
        box.append(combo)
        return box

    def __update_view(self):
        for child in utils.widget_get_children(self):
            self.remove(child)

        if self.__object is None:
            return

        obj = self.__object
        parent = obj.parent
        is_builtin = obj.info.is_builtin

        if self.layout:
            if parent is None or is_builtin:
                return

            # Child Type input
            if parent.info.has_child_types():
                self.append(self.__create_child_type_editor())
        else:
            # ID
            self.append(self.__create_id_editor())

        if obj.type_id == EXTERNAL_TYPE:
            label = Gtk.Label(
                label=_(
                    "This object will not be exported, it is only used to make a reference to it. \
It has to be exposed by your application with GtkBuilder expose_object method."
                ),
                halign=Gtk.Align.START,
                margin_top=8,
                xalign=0,
                wrap=True,
            )
            self.append(label)
            self.show()
            return

        info = parent.info if self.layout and parent else obj.info
        for owner_id in [info.type_id] + info.hierarchy:
            if self.layout:
                owner_id = f"{owner_id}LayoutChild"

            info = obj.project.type_info.get(owner_id, None)

            if info is None:
                continue

            # Editor count
            i = 0

            # Grid for all properties and custom data editors
            grid = Gtk.Grid(hexpand=True, row_spacing=4, column_spacing=4)

            # Add shortcuts
            if not self.layout and len(info.child_type_shortcuts):
                shortcuts = self.__create_child_shortcuts(info)
                shortcuts.props.margin_start = 14
                grid.attach(shortcuts, 0, i, 2, 1)
                i += 1

            # Properties
            properties = obj.layout_dict if self.layout else obj.properties_dict
            for property_id in info.properties:
                prop = properties.get(property_id, None)

                if prop is None or prop.info is None:
                    continue

                # Only show properties in the class they where originally defined
                if prop.info.original_owner_id is not None and owner_id != prop.info.original_owner_id:
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

                if self.layout:
                    label = CmbPropertyLabel(layout_prop=prop)
                else:
                    label = CmbPropertyLabel(prop=prop, bindable=not is_builtin)

                # Keep a dict of labels

                grid.attach(label, 0, i, 1, 1)
                grid.attach(editor, 1, i, 1, 1)
                i += 1

            for data_key in info.data:
                data = None

                # Find data
                for d in obj.data:
                    if d.info.key == data_key:
                        data = d
                        break

                editor = CmbObjectDataEditor(
                    visible=True,
                    hexpand=True,
                    object=obj,
                    data=data,
                    info=None if data else info.data[data_key],
                )

                grid.attach(editor, 0, i, 2, 1)
                i += 1

            # Continue if class had no editors to add
            if i == 0:
                continue

            # Create expander/revealer to pack editor grid
            expander = Gtk.Expander(label=f"<b>{owner_id}</b>", use_markup=True, expanded=True)
            revealer = Gtk.Revealer(reveal_child=True)
            expander.connect("notify::expanded", self.__on_expander_expanded, revealer)
            revealer.set_child(grid)
            self.append(expander)
            self.append(revealer)

        self.show()

    def __on_object_ui_notify(self, obj, pspec):
        if pspec.name == "template-id" and self.__template_switch:
            self.__template_switch.set_active(obj.props.template_id != 0)

    def __on_object_notify(self, obj, pspec):
        if pspec.name == "parent-id":
            self.__update_view()

    @GObject.Property(type=CmbObject)
    def object(self):
        return self.__object

    @object.setter
    def _set_object(self, obj):
        if obj == self.__object:
            return

        if self.__object:
            self.__object.disconnect_by_func(self.__on_object_notify)
            self.__object.ui.disconnect_by_func(self.__on_object_ui_notify)

        for binding in self.__bindings:
            binding.unbind()

        self.__bindings = []

        self.__object = obj

        if obj:
            obj.connect("notify", self.__on_object_notify)
            obj.ui.connect("notify", self.__on_object_ui_notify)

        self.__update_view()


Gtk.WidgetClass.set_css_name(CmbObjectEditor, "CmbObjectEditor")
