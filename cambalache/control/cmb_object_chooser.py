#
# CmbObjectChooser
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

from cambalache import _
from gi.repository import GObject, Gdk, Gtk

from ..cmb_object import CmbObject
from ..cmb_type_chooser_popover import CmbTypeChooserPopover


class CmbObjectChooser(Gtk.Entry):
    __gtype_name__ = "CmbObjectChooser"

    parent = GObject.Property(type=CmbObject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    is_inline = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    inline_object_id = GObject.Property(type=str, default=None, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    inline_property_id = GObject.Property(type=str, default=None, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    type_id = GObject.Property(type=str, default="GObject", flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)

    def __init__(self, **kwargs):
        self.__object_id = None
        self.__updating = None
        super().__init__(**kwargs)

        self.connect("notify::parent", self.__on_parent_notify)
        self.connect("notify::text", self.__on_text_notify)

        if self.is_inline:
            self.connect("icon-press", self.__on_icon_pressed)
            if self.parent:
                self.parent.connect("property-changed", self.__on_parent_property_changed)
            self.__update_icons()
        else:
            self.props.placeholder_text = f"<{self.type_id}>"

        drop_target = Gtk.DropTarget.new(
            type=GObject.TYPE_NONE, actions=Gdk.DragAction.COPY
        )
        drop_target.set_gtypes([CmbObject])
        drop_target.connect("accept", self.__on_drop_accept)
        drop_target.connect("drop", self.__on_drop_drop)
        self.add_controller(drop_target)

    def __on_parent_notify(self, obj, pspec):
        if self.parent:
            self.parent.connect("property-changed", self.__on_parent_property_changed)

    def __on_text_notify(self, obj, pspec):
        if self.inline_object_id:
            return

        if self.__updating:
            self.__updating = False
            return

        obj = self.parent.project.get_object_by_name(self.parent.ui_id, self.props.text)
        value = obj.object_id if obj else None

        if self.__object_id != value:
            self.__object_id = value
            self.notify("cmb-value")

    def __on_parent_property_changed(self, parent, prop, field):
        if not self.is_inline or prop.property_id != self.inline_property_id:
            return

        self.inline_object_id = prop.inline_object_id
        self.__update_icons()

    def __on_drop_accept(self, target, drop):
        drag = drop.get_drag()
        origin_item = drag._item

        if origin_item == self.parent:
            return False

        return origin_item.info.is_a(self.type_id)

    def __on_drop_drop(self, target, origin_item, x, y):
        if self.is_inline:
            prop = self.parent.properties_dict.get(self.inline_property_id, None)

            if prop is None:
                return

            self.parent.project.history_push(_("Move {name} to {property}").format(
                name=origin_item.display_name,
                property=f"{self.parent.type_id}::{self.inline_property_id}"))

            # TODO: implement this in plain SQL
            parent_id = self.parent.object_id
            object_id = origin_item.object_id

            origin_item.parent_id = parent_id
            origin_item.inline_property_id = self.inline_property_id

            prop.value = object_id

            prop.inline_object_id = object_id
            self.inline_object_id = object_id
            self.__update_icons()

            self.parent.project.history_pop()
        else:
            # TODO: ensure dragged object has an id
            # Select dragged object id
            self.cmb_value = origin_item.object_id

    @GObject.Property(type=str)
    def cmb_value(self):
        return str(self.__object_id) if self.__object_id else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        parent = self.parent
        value = value if value else None

        if self.__object_id == value:
            return

        self.__object_id = value

        self.__updating = True
        if self.__object_id:
            obj = parent.project.get_object_by_id(parent.ui_id, self.__object_id)
            self.props.text = obj.name if obj else ""
        else:
            self.props.text = ""

    def __update_icons(self):
        if not self.is_inline:
            return

        if self.inline_object_id:
            obj = self.parent.project.get_object_by_id(self.parent.ui_id, self.inline_object_id)
            type = obj.type_id
            self.props.secondary_icon_name = "edit-clear-symbolic"
            self.props.secondary_icon_tooltip_text = _("Clear property")
            self.props.placeholder_text = f"<inline {type}>"
            self.props.editable = False
            self.props.can_focus = False
        else:
            self.props.secondary_icon_name = "list-add-symbolic"
            self.props.secondary_icon_tooltip_text = _("Add inline object")
            self.props.placeholder_text = f"<{self.type_id}>"
            self.props.editable = True
            self.props.can_focus = True

    def __get_name_for_object(self, obj):
        name = obj.name
        return obj.type_id.lower() if name is None else name

    def __on_type_selected(self, popover, info):
        parent = self.parent
        parent.project.add_object(parent.ui_id, info.type_id, parent_id=parent.object_id, inline_property=self.inline_property_id)
        self.__update_icons()

    def __on_icon_pressed(self, widget, icon_pos):
        if not self.is_inline:
            return

        parent = self.parent
        project = parent.project

        if self.inline_object_id:
            obj = project.get_object_by_id(self.parent.ui_id, self.inline_object_id)
            project.remove_object(obj)
            self.inline_object_id = None
            self.__update_icons()
        else:
            chooser = CmbTypeChooserPopover(parent_type_id=parent.type_id, derived_type_id=self.type_id)
            chooser.set_parent(self)
            chooser.project = project
            chooser.connect("type-selected", self.__on_type_selected)
            chooser.popup()
