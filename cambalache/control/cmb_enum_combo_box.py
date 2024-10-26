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
# SPDX-License-Identifier: LGPL-2.1-only
#

from gi.repository import GObject, Gtk
from ..cmb_type_info import CmbTypeInfo


class CmbEnumComboBox(Gtk.ComboBox):
    __gtype_name__ = "CmbEnumComboBox"

    info = GObject.Property(type=CmbTypeInfo, flags=GObject.ParamFlags.READWRITE)
    text_column = GObject.Property(type=int, default=1, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("changed", self.__on_changed)

        renderer_text = Gtk.CellRendererText()
        self.pack_start(renderer_text, True)
        self.add_attribute(renderer_text, "text", self.text_column)

        self.props.id_column = self.text_column

        if self.info:
            self.props.model = self.info.enum

    def __on_changed(self, obj):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.active_id

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if self.info is None:
            return

        self.props.active_id = None
        active_id = self.info.enum_get_value_as_string(value)

        if active_id == self.props.active_id:
            return

        self.props.active_id = active_id
