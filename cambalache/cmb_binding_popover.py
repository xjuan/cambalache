#
# CmbBindingPopover
#
# Copyright (C) 2025  Juan Pablo Ugarte
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

from gi.repository import GLib, GObject, Gtk
from .cmb_property import CmbProperty


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_binding_popover.ui")
class CmbBindingPopover(Gtk.Popover):
    __gtype_name__ = "CmbBindingPopover"

    prop = GObject.Property(type=CmbProperty, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    object_chooser = Gtk.Template.Child()
    property_chooser = Gtk.Template.Child()
    flags_entry = Gtk.Template.Child()

    # Expression
    expression_dropdown = Gtk.Template.Child()
    expression_object_chooser = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if self.prop is None:
            return

        # Get bind property to initialize inputs
        bind_source, bind_property = self.__find_bind_source_property(self.prop.bind_source_id, self.prop.bind_property_id)

        # Object editor (it does not set the object directly to CmbProperty, just choose the object in the prop chooser)
        self.object_chooser.parent = self.prop.object
        self.object_chooser.cmb_value = bind_source.object_id if bind_source else 0

        # Update Property editor
        self.property_chooser.object = bind_source
        self.property_chooser.target_info = self.prop.info

        # Update active_id after letting the object populate the properties
        if bind_property:
            self.property_chooser.props.active_id = bind_property.property_id

        # Flags editor
        binding_flags_info = self.prop.project.type_info.get("GBindingFlags", None)
        self.flags_entry.info = binding_flags_info

        GObject.Object.bind_property(
            self.prop,
            "bind_flags",
            self.flags_entry,
            "cmb-value",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )

        self.__updating = True

        # Expression stuff
        if self.prop.binding_expression_id:
            expression_source = self.prop.project.get_object_by_id(self.prop.ui_id, self.prop.binding_expression_id)
            item_index = self.expression_dropdown.props.model.find(expression_source.type_id)
            self.expression_dropdown.set_selected(item_index if item_index < GLib.MAXUINT else 0)
        else:
            self.expression_dropdown.set_selected(0)

        self.expression_object_chooser.parent = self.prop.object
        self.expression_object_chooser.cmb_value = self.prop.binding_expression_object_id

        self.__updating = False

    @Gtk.Template.Callback("on_clear_clicked")
    def __on_clear_clicked(self, button):
        if self.prop:
            self.prop.clear_binding()

        self.popdown()

    @Gtk.Template.Callback("on_close_clicked")
    def __on_close_clicked(self, button):
        self.popdown()

    @Gtk.Template.Callback("on_object_editor_notify")
    def __on_object_editor_notify(self, object_editor, pspec):
        object_id = object_editor.cmb_value
        if object_id:
            obj = self.prop.project.get_object_by_id(self.prop.ui_id, int(object_id)) if self.prop else None
            self.property_chooser.object = obj
        else:
            self.property_chooser.object = None

    @Gtk.Template.Callback("on_property_editor_changed")
    def __on_property_editor_changed(self, combo):
        if self.prop is None:
            return

        if combo.object:
            bind_source, bind_property = self.__find_bind_source_property(combo.object.object_id, combo.props.active_id)
            self.prop.bind_property = bind_property
        else:
            self.prop.bind_property = None

    def __find_bind_source_property(self, bind_source_id, bind_property_id):
        bind_source = self.prop.project.get_object_by_id(self.prop.ui_id, bind_source_id) if bind_source_id else None
        bind_property = bind_source.properties_dict.get(bind_property_id, None) if bind_source else None

        return bind_source, bind_property

    @Gtk.Template.Callback("on_popover_show")
    def __on_popover_show(self, combo):
        if self.prop.binding_expression_id:
            self.expression_dropdown.grab_focus()
        else:
            self.object_chooser.grab_focus()

    # GtkExpression support
    @Gtk.Template.Callback("on_expression_dropdown_notify")
    def __on_expression_dropdown_notify(self, dropdown, pspec):
        if self.prop is None or self.__updating:
            return

        self.prop.set_binding_expression_type(dropdown.props.selected_item.get_string())
