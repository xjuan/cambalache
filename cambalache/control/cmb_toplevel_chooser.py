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

from gi.repository import GObject, Gtk, Gio
from cambalache import CmbObject, CmbUI


class CmbNoneObject(CmbObject):
    __gtype_name__ = "CmbNoneObject"

    @GObject.Property(type=str)
    def display_name_type(self):
        return "(None)"

    @GObject.Property(type=str)
    def display_name(self):
        return "<b>(None)</b>"


class CmbToplevelChooser(Gtk.DropDown):
    __gtype_name__ = "CmbToplevelChooser"

    object = GObject.Property(type=CmbUI, flags=GObject.ParamFlags.READWRITE)
    derivable_only = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.none_list = Gio.ListStore(item_type=CmbNoneObject)
        self.none_list.append(CmbNoneObject())

        self.__update_model()

        self.__expression = Gtk.PropertyExpression.new(CmbObject, None, "display-name-type")
        self.props.expression = self.__expression

        self.connect("notify::object", self.__on_object_notify)
        self.connect("notify::selected-item", self.__on_selected_item_notify)

    def __update_model(self):
        if self.object is None:
            self.props.model = None
            return

        lists = Gio.ListStore(item_type=Gio.ListModel)
        lists.append(self.none_list)

        if self.derivable_only:
            lists.append(Gtk.FilterListModel(
                model=self.object,
                filter=Gtk.CustomFilter.new(lambda i, d: i.info.derivable, None)
            ))
        else:
            lists.append(self.object)

        flatten = Gtk.FlattenListModel(model=lists)
        self.props.model = flatten
        self.set_selected(0)

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
        if self.object is None or value is None or value == 0:
            self.set_selected(0)
            return

        model = self.props.model
        item = self.object.project.get_object_by_id(self.object.ui_id, value)

        if item is not None:
            for position in range(1, model.props.n_items + 1):
                i = model.get_item(position)
                if i == item:
                    self.set_selected(position)
                    break
        else:
            self.set_selected(0)
