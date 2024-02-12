#
# CmbEnumComboBox
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

from gi.repository import GObject, Gtk
from ..cmb_type_info import CmbTypeInfo
from cambalache import utils


class CmbEnumComboBox(Gtk.ComboBox):
    __gtype_name__ = "CmbEnumComboBox"

    info = GObject.Property(type=CmbTypeInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    text_column = GObject.Property(type=int, default=1, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("changed", self.__on_changed)

        renderer_text = Gtk.CellRendererText()
        self.pack_start(renderer_text, True)
        self.add_attribute(renderer_text, "text", self.text_column)

        self.props.id_column = self.text_column
        self.props.model = self.info.enum

    def __on_changed(self, obj):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.active_id

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.active_id = None

        for row in self.info.enum:
            enum_name = row[0]
            enum_nick = row[1]

            # Always use nick as value
            if value == enum_name or value == enum_nick:
                self.props.active_id = enum_nick
