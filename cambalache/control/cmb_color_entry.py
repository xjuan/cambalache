#
# CmbColorEntry
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

from gi.repository import Gdk, GObject, Gtk


class CmbColorEntry(Gtk.Box):
    __gtype_name__ = "CmbColorEntry"

    use_color = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.__ignore_notify = False

        super().__init__(**kwargs)

        self.entry = Gtk.Entry(visible=True, width_chars=14, editable=False)
        self.button = Gtk.ColorButton(visible=True, use_alpha=True)

        self.__default_color = self.button.props.color
        self.__default_rgba = self.button.props.rgba

        self.pack_start(self.entry, False, True, 0)
        self.pack_start(self.button, False, True, 4)

        self.button.connect("color-set", self.__on_color_set)
        self.entry.connect("icon-press", self.__on_entry_icon_pressed)

    def __on_entry_icon_pressed(self, widget, icon_pos, event):
        self.cmb_value = None

    def __on_color_set(self, obj):
        if self.use_color:
            self.cmb_value = self.button.props.color.to_string() if self.button.props.color else None
        else:
            self.cmb_value = self.button.props.rgba.to_string() if self.button.props.rgba else None

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.entry.props.text if self.entry.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if value:
            self.entry.props.text = value
            self.entry.props.secondary_icon_name = "edit-clear-symbolic"
        else:
            self.entry.props.text = ""
            self.entry.props.secondary_icon_name = None

        valid = False

        if self.use_color:
            color = None
            if value:
                valid, color = Gdk.Color.parse(value)

            self.button.set_color(color if valid else self.__default_color)
        else:
            rgba = Gdk.RGBA()

            if value:
                valid = rgba.parse(value)

            self.button.set_rgba(rgba if valid else self.__default_rgba)
