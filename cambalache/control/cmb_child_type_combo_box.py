#
# CmbChildTypeComboBox
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

from cambalache import utils
from gi.repository import GObject, Gtk


class CmbChildTypeComboBox(Gtk.ComboBox):
    __gtype_name__ = "CmbChildTypeComboBox"

    object = GObject.Property(type=GObject.Object, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.connect("changed", self.__on_changed)

        # Model, store it in a Python variable to make sure we hold a reference
        # First column is the ID and the second is if you can select the child or not
        self.__model = Gtk.ListStore(str, bool)
        self.props.model = self.__model
        self.props.id_column = 0

        # Simple cell renderer
        renderer_text = Gtk.CellRendererText()
        self.pack_start(renderer_text, True)
        self.add_attribute(renderer_text, "text", 0)
        self.add_attribute(renderer_text, "sensitive", 1)

        self.__populate_model()

    def __populate_model(self):
        self.__model.clear()

        parent = self.object.parent
        if parent is None:
            return

        self.__model.append([None, True])

        pinfo = parent.info
        while pinfo:
            if pinfo.child_types:
                for t in pinfo.child_types:
                    self.__model.append([t, True])
            pinfo = pinfo.parent

    def __on_changed(self, obj):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.active_id

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.active_id = value
