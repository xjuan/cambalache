#
# CmbEntry
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


class CmbEntry(Gtk.Entry):
    __gtype_name__ = "CmbEntry"

    __gsignals__ = {
        "edit-translatable": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::text", self.__on_text_notify)
        self.connect("icon-press", self.__on_icon_pressed)

    def __on_icon_pressed(self, widget, icon_pos):
        self.emit("edit-translatable")

    def __on_text_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=bool, default=False)
    def translatable(self):
        return self.props.secondary_icon_name == "document-edit-symbolic"

    @translatable.setter
    def _set_translatable(self, value):
        self.props.secondary_icon_name = "document-edit-symbolic" if value else None

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.text if self.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        # We do not want to emit a change if there is none
        if value == self.props.text:
            return

        self.props.text = value if value is not None else ""
