#
# CmbToplevelChooser
#
# Copyright (C) 2021-2023  Juan Pablo Ugarte
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

from gi.repository import GObject, Gtk
from cambalache import CmbObject, CmbUI, CmbBaseObject


class CmbToplevelChooser(Gtk.DropDown):
    __gtype_name__ = "CmbToplevelChooser"

    object = GObject.Property(type=CmbUI, flags=GObject.ParamFlags.READWRITE)
    derivable_only = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__update_model()

        self.__expression = Gtk.PropertyExpression.new(CmbBaseObject, None, "display-name")
        self.props.expression = self.__expression

        self.connect("notify::object", self.__on_object_notify)
        self.connect("notify::selected-item", self.__on_selected_item_notify)

    def __filter_func(self, model, iter, data):
        obj = model[iter][0]

        if self.object.ui_id != obj.ui_id:
            return False

        if type(obj) is CmbObject:
            if self.derivable_only:
                return obj.info.derivable and obj.parent_id == 0
            else:
                return obj.parent_id == 0

        return False

    def __update_model(self):
        if self.object is None:
            return

        self.props.model = self.object.children_model

    def __on_object_notify(self, obj, pspec):
        self.props.model = None
        self.__update_model()

    def __on_selected_item_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=int)
    def cmb_value(self):
        item = self.get_selected_item()
        if item is None:
            return 0

        return item.object_id

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if self.object is None:
            return

        item = self.object.project.get_object_by_id(self.object.ui_id, value)

        if item:
            found, position = self.props.model.find(item)
            if found:
                self.set_selected(position)
        else:
            self.set_selected(Gtk.INVALID_LIST_POSITION)
