#
# CmbTextView
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
from .cmb_text_buffer import CmbTextBuffer


class CmbTextView(Gtk.ScrolledWindow):
    __gtype_name__ = "CmbTextView"

    cmb_value = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.height_request = 96
        self.buffer = CmbTextBuffer()
        self.view = Gtk.TextView(visible=True, buffer=self.buffer)

        GObject.Object.bind_property(
            self,
            "cmb-value",
            self.buffer,
            "cmb-value",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )

        self.set_child(self.view)
