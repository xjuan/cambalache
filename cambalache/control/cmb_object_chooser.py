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

from cambalache import _
from gi.repository import GObject, Gtk

from ..cmb_object import CmbObject
from ..cmb_property import CmbProperty
from ..cmb_type_chooser_popover import CmbTypeChooserPopover


class CmbObjectChooser(Gtk.Entry):
    __gtype_name__ = "CmbObjectChooser"

    parent = GObject.Property(type=CmbObject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    prop = GObject.Property(type=CmbProperty, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        self._value = None
        super().__init__(**kwargs)
        self.connect("notify::text", self.__on_text_notify)

        if self.prop is None:
            self.props.placeholder_text = "<GObject>"
            return

        self.__is_inline_object = self.prop.project.target_tk == "gtk-4.0" and not self.prop.info.disable_inline_object

        if self.__is_inline_object:
            self.connect("icon-press", self.__on_icon_pressed)
            self.parent.connect("property-changed", lambda o, p: self.__update_icons())
            self.__update_icons()
        else:
            self.props.placeholder_text = f"<{self.prop.info.type_id}>"

    def __on_text_notify(self, obj, pspec):
        if self.prop and self.prop.inline_object_id:
            return

        obj = self.parent.project.get_object_by_name(self.parent.ui_id, self.props.text)
        self._value = obj.object_id if obj else None

        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self._value

    @cmb_value.setter
    def _set_cmb_value(self, value):
        parent = self.parent

        self._value = int(value) if value else None

        if self._value:
            obj = parent.project.get_object_by_id(parent.ui_id, self._value)
            self.props.text = obj.name if obj else ""
        else:
            self.props.text = ""

    def __update_icons(self):
        if not self.__is_inline_object:
            return

        if self.prop.inline_object_id:
            obj = self.parent.project.get_object_by_id(self.parent.ui_id, self.prop.inline_object_id)
            type = obj.type_id
            self.props.secondary_icon_name = "edit-clear-symbolic"
            self.props.secondary_icon_tooltip_text = _("Clear property")
            self.props.placeholder_text = f"<inline {type}>"
            self.props.editable = False
            self.props.can_focus = False
        else:
            self.props.secondary_icon_name = "list-add-symbolic"
            self.props.secondary_icon_tooltip_text = _("Add inline object")
            self.props.placeholder_text = f"<{self.prop.info.type_id}>"
            self.props.editable = True
            self.props.can_focus = True

    def __get_name_for_object(self, obj):
        name = obj.name
        return obj.type_id.lower() if name is None else name

    def __on_type_selected(self, popover, info):
        parent = self.parent
        parent.project.add_object(parent.ui_id, info.type_id, parent_id=parent.object_id, inline_property=self.prop.property_id)
        self.__update_icons()

    def __on_icon_pressed(self, widget, icon_pos):
        parent = self.parent
        project = parent.project
        prop = self.prop

        if self.prop.inline_object_id:
            obj = project.get_object_by_id(self.parent.ui_id, prop.inline_object_id)
            project.remove_object(obj)
            self.__update_icons()
        else:
            chooser = CmbTypeChooserPopover(parent_type_id=parent.type_id, derived_type_id=prop.info.type_id)
            chooser.set_parent(self)
            chooser.project = project
            chooser.connect("type-selected", self.__on_type_selected)
            chooser.popup()
