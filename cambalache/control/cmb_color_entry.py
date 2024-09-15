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
# SPDX-License-Identifier: LGPL-2.1-only
#

from gi.repository import Gdk, GObject, Gtk, Pango

from .named_colors import named_colors


# Reverse color maps
_named_colors = {v: k for k, v in named_colors.items()}


class CmbColorEntry(Gtk.Box):
    __gtype_name__ = "CmbColorEntry"

    use_color = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.__ignore_notify = False

        super().__init__(**kwargs)

        self.entry = Gtk.Entry(width_chars=14)
        self.button = Gtk.ColorDialogButton(dialog=Gtk.ColorDialog())

        self.__default_color = Gdk.RGBA()
        self.__default_color.parse("black")
        self.__use_named_color = False
        self.__in_sync = False

        self.append(self.entry)
        self.append(self.button)

        self.button.connect("notify::rgba", self.__on_color_set)
        self.entry.connect("icon-press", self.__on_entry_icon_pressed)
        self.entry.connect("activate", self.__on_entry_activate)

    def __on_entry_icon_pressed(self, widget, icon_pos):
        print("__on_entry_icon_pressed")
        self.cmb_value = None

    def __on_entry_activate(self, entry):
        print("__on_entry_activate")
        self.cmb_value = self.cmb_value

    def __on_color_set(self, obj, pspec):
        if self.__in_sync:
            return
        print("__on_color_set")
        rgba = self.button.props.rgba
        color = None

        if rgba and self.__use_named_color:
            color = self.rgba_to_hex(rgba)

            if color in _named_colors:
                self.cmb_value = _named_colors[color]
                return

        if self.use_color:
            if color is None:
                color = self.rgba_to_hex(rgba)

            self.cmb_value = color
        else:
            self.cmb_value = rgba.to_string() if rgba else None

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.entry.props.text if self.entry.props.text != "" else None

    def rgba_to_hex(self, rgba):
        if rgba and self.__use_named_color:
            r = format(int(rgba.red * 255), "X")
            g = format(int(rgba.green * 255), "X")
            b = format(int(rgba.blue * 255), "X")

            return f"#{r}{g}{b}"

        return None

    def parse_gdk_color(self, color):
        c = Pango.Color()

        # Both gdk_rgba_parse() and gdk_color_parse() use pango_color_parse()
        valid = c.parse(color)

        if valid:
            rgba = Gdk.RGBA()

            rgba.red = c.red / 65535.0
            rgba.green = c.green / 65535.0
            rgba.blue = c.blue / 65535.0
            rgba.alpha = 1.0

            return (True, rgba)

        return (False, None)

    @cmb_value.setter
    def _set_cmb_value(self, value):
        valid = False
        rgba = None

        self.__in_sync = True

        self.__use_named_color = value in named_colors

        if value is not None:
            if self.use_color:
                valid, rgba = self.parse_gdk_color(value)
            else:
                rgba = Gdk.RGBA()
                valid = rgba.parse(value)

        self.button.set_rgba(rgba if valid and rgba is not None else self.__default_color)

        if valid and value:
            self.entry.props.text = value
            self.entry.props.secondary_icon_name = "edit-clear-symbolic"
        else:
            self.entry.props.text = ""
            self.entry.props.secondary_icon_name = None

        self.__in_sync = False
