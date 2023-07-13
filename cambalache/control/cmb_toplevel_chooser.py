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
from cambalache import _, CmbObject, CmbUI


class CmbToplevelChooser(Gtk.ComboBox):
    __gtype_name__ = "CmbToplevelChooser"

    object = GObject.Property(type=CmbUI, flags=GObject.ParamFlags.READWRITE)
    derivable_only = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.filter = None

        super().__init__(**kwargs)
        self.connect("notify::object", self.__on_object_notify)
        self.connect("changed", self.__on_changed)

        renderer = Gtk.CellRendererText()
        self.pack_start(renderer, True)
        self.set_cell_data_func(renderer, self.__name_cell_data_func, None)

    def __name_cell_data_func(self, column, cell, model, iter_, data):
        obj = model.get_value(iter_, 0)

        if type(obj) != CmbObject:
            return

        name = f"{obj.name} " if obj.name else ""
        extra = _("(template)") if not obj.parent_id and obj.ui.template_id == obj.object_id else obj.type_id
        cell.set_property("markup", f"{name}<i>{extra}</i>")

    def __filter_func(self, model, iter, data):
        obj = model[iter][0]

        if self.object.ui_id != obj.ui_id:
            return False

        if type(obj) == CmbObject:
            if self.derivable_only:
                return obj.info.derivable and obj.parent_id == 0
            else:
                return obj.parent_id == 0

        return False

    def __on_object_notify(self, obj, pspec):
        self.props.model = None
        self.filter = None

        if self.object is None:
            return

        project = self.object.project
        iter = project.get_iter_from_object(self.object)
        path = project.get_path(iter)

        # Create filter and set visible function before using it
        self.filter = project.filter_new(path)
        self.filter.set_visible_func(self.__filter_func)

        # Use filter as model
        self.props.model = self.filter

    def __on_changed(self, combo):
        self.notify("cmb-value")

    @GObject.Property(type=int)
    def cmb_value(self):
        if self.filter is None:
            return 0

        iter = self.get_active_iter()
        if iter is None:
            return 0

        row = self.filter[iter]
        return row[0].object_id if row else 0

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if self.object is None:
            return

        iter = self.object.project.get_iter_from_object_id(self.object.ui_id, value)
        if iter:
            valid, filter_iter = self.filter.convert_child_iter_to_iter(iter)
            self.set_active_iter(filter_iter if valid else None)
