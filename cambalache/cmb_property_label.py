#
# CmbPropertyLabel
#
# Copyright (C) 2023-2024  Juan Pablo Ugarte
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
from .cmb_property import CmbProperty
from .cmb_layout_property import CmbLayoutProperty
from .cmb_objects_base import CmbPropertyInfo
from .control import CmbObjectChooser, CmbFlagsEntry


class CmbPropertyLabel(Gtk.Button):
    __gtype_name__ = "CmbPropertyLabel"

    prop = GObject.Property(type=CmbProperty, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    layout_prop = GObject.Property(
        type=CmbLayoutProperty, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY
    )
    bindable = GObject.Property(type=bool, default=True, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.prop and not self.layout_prop:
            raise Exception("CmbPropertyLabel requires prop or layout_prop to be set")
            return

        self.label = Gtk.Label(xalign=0, visible=True)
        box = Gtk.Box(visible=True)

        # Update label status
        if self.prop:
            self.bind_icon = Gtk.Image(icon_size=Gtk.IconSize.NORMAL, visible=True)
            box.append(self.bind_icon)

            self.label.props.label = self.prop.property_id

            self.__update_property_label()
            self.prop.connect("notify::value", lambda o, p: self.__update_property_label())

            if self.bindable:
                self.connect("clicked", self.__on_bind_button_clicked)

        if self.layout_prop:
            self.bind_icon = None
            self.label.props.label = self.layout_prop.property_id
            self.__update_layout_property_label()
            self.layout_prop.connect("notify::value", lambda o, p: self.__update_layout_property_label())

        box.append(self.label)
        self.set_child(box)

    def __update_label(self, prop):
        if prop.value != prop.info.default_value:
            self.add_css_class("modified")
        else:
            self.remove_css_class("modified")

        msg = prop.version_warning
        self.set_tooltip_text(msg)

        if msg:
            self.add_css_class("warning")
        else:
            self.remove_css_class("warning")

    def __update_layout_property_label(self):
        self.__update_label(self.layout_prop)

    def __update_property_label(self):
        self.__update_label(self.prop)

        if not self.bindable:
            return

        if self.prop.bind_property_id:
            self.bind_icon.props.icon_name = "binded-symbolic"
            self.remove_css_class("hidden")
        else:
            self.bind_icon.props.icon_name = "bind-symbolic"
            self.add_css_class("hidden")

    def __on_object_editor_notify(self, object_editor, pspec, property_editor):
        object_id = object_editor.cmb_value
        if object_id:
            property_editor.object = self.prop.project.get_object_by_id(self.prop.ui_id, int(object_id))

    def __on_property_editor_changed(self, combo):
        bind_source, bind_property = self.__find_bind_source_property(combo.object.object_id, combo.props.active_id)
        self.prop.bind_property = bind_property
        self.__update_property_label()

    def __find_bind_source_property(self, bind_source_id, bind_property_id):
        bind_source = self.prop.project.get_object_by_id(self.prop.ui_id, bind_source_id) if bind_source_id else None
        bind_property = bind_source.properties_dict.get(bind_property_id, None) if bind_source else None

        return bind_source, bind_property

    def __on_clear_clicked(self, button, popover):
        self.prop.bind_property = None
        self.prop.bind_flags = None
        self.__update_property_label()
        popover.popdown()

    def __on_bind_button_clicked(self, button):
        popover = Gtk.Popover(position=Gtk.PositionType.LEFT)
        popover.set_parent(self)

        grid = Gtk.Grid(hexpand=True, row_spacing=4, column_spacing=4, visible=True)

        grid.attach(Gtk.Label(label="<b>Property Binding</b>", use_markup=True, visible=True, xalign=0), 0, 0, 2, 1)

        # Get bind property to initialize inputs
        bind_source, bind_property = self.__find_bind_source_property(self.prop.bind_source_id, self.prop.bind_property_id)

        # Create Property editor
        property_editor = CmbPropertyChooser(object=bind_source, target_info=self.prop.info)
        property_editor.connect("changed", self.__on_property_editor_changed)

        # Update active_id after letting the object populate the properties
        if bind_property:
            property_editor.props.active_id = bind_property.property_id

        # Object editor (it does not set the object directly to CmbProperty, just choose the object in the prop chooser)
        object_editor = CmbObjectChooser(parent=self.prop.object, cmb_value=bind_source.object_id if bind_source else 0)
        object_editor.connect("notify::cmb-value", self.__on_object_editor_notify, property_editor)

        # Flags editor
        binding_flags_info = self.prop.project.type_info.get("GBindingFlags", None)
        flags_editor = CmbFlagsEntry(info=binding_flags_info)
        GObject.Object.bind_property(
            self.prop,
            "bind_flags",
            flags_editor,
            "cmb-value",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )

        i = 1
        for prop_label, editor in [("source", object_editor), ("property", property_editor), ("flags", flags_editor)]:
            editor.props.visible = True

            label = Gtk.Label(label=prop_label, xalign=0, visible=True)

            grid.attach(label, 0, i, 1, 1)
            grid.attach(editor, 1, i, 1, 1)
            i += 1

        clear = Gtk.Button(label="Clear", visible=True, halign=Gtk.Align.END)
        clear.connect("clicked", self.__on_clear_clicked, popover)

        grid.attach(clear, 0, i, 2, 1)
        object_editor.grab_focus()

        popover.set_child(grid)
        popover.popup()


Gtk.WidgetClass.set_css_name(CmbPropertyLabel, "CmbPropertyLabel")


class CmbPropertyChooser(Gtk.ComboBoxText):
    __gtype_name__ = "CmbPropertyChooser"

    object = GObject.Property(type=CmbObject, flags=GObject.ParamFlags.READWRITE)
    target_info = GObject.Property(type=CmbPropertyInfo, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__populate()
        self.connect("notify::object", self.__on_object_notify)

    def __on_object_notify(self, obj, pspec):
        self.__populate()

    def __populate(self):
        self.remove_all()

        if self.object is None:
            return

        target_info = self.target_info
        target_type = target_info.type_id
        target_type_info = self.object.project.type_info.get(target_type, None)
        target_is_object = target_info.is_object
        target_is_iface = target_type_info.parent_id == "interface" if target_type_info else False

        for prop in sorted(self.object.properties, key=lambda p: p.property_id):
            info = prop.info

            # Ignore construct only properties
            if info.construct_only:
                continue

            source_type_info = self.object.project.type_info.get(info.type_id, None)
            source_is_object = info.is_object
            source_is_iface = source_type_info.parent_id == "interface" if source_type_info else False

            if target_is_object or target_is_iface:
                # Ignore non object properties
                if not source_is_object and not source_is_iface:
                    continue

                # Ignore object properties of a different type
                if source_type_info and not source_type_info.is_a(target_info.type_id):
                    continue
            elif source_is_object or source_is_iface:
                continue

            # Enums and Flags has to be the same type
            if target_type_info and target_type_info.parent_id in ["flags", "enum"] and info.type_id != target_type:
                continue

            if source_type_info and source_type_info.parent_id in ["flags", "enum"] and info.type_id != target_type:
                continue

            compatible = info.type_id == target_type

            if not compatible:
                try:
                    gtype_id = GObject.type_from_name(info.type_id)
                    gtarget_id = GObject.type_from_name(target_type)
                    if gtype_id and gtarget_id:
                        compatible = GObject.Value.type_compatible(gtype_id, gtarget_id)
                        if not compatible:
                            compatible = GObject.Value.type_transformable(gtype_id, gtarget_id)
                except Exception as e:  # noqa F841
                    self.append(prop.property_id, prop.property_id + "*")
                    continue

            if compatible:
                self.append(prop.property_id, prop.property_id)
