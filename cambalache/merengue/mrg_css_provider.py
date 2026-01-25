#
# Merengue CSS provider
#
# Copyright (C) 2022  Juan Pablo Ugarte
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

from gi.repository import GObject, Gdk, Gtk

from merengue import getLogger

logger = getLogger(__name__)


class MrgCssProvider(Gtk.CssProvider):
    __gtype_name__ = "MrgCssProvider"

    app = GObject.Property(type=Gtk.Application, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)

    css_id = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    filename = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    priority = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    is_global = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)

    ui_id = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    provider_for = GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    css = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)

    def __init__(self, **kwargs):
        self.error_count = 0

        super().__init__(**kwargs)

        self.connect("parsing-error", self.__on_parsing_error)
        self.connect("notify", self.__on_notify)
        self.__update()

    def __css_parsing_status(self, message, start, end):
        self.app.write_command(
            "css_parsing_status",
            args={
                "css_id": self.css_id,
                "error_count": self.error_count,
                "error": message,
                "start": start,
                "end": end
            }
        )

    def __on_parsing_error(self, provider, section, error):
        self.error_count += 1

        if Gtk.MAJOR_VERSION == 4:
            start = section.get_start_location().chars
            end = section.get_end_location().chars
        else:
            def get_start_end(text, section):
                start_line, end_line = section.get_start_line(),  section.get_end_line()
                start_index, start_offset, end_offset = 0, 0, 0

                for i in range(0, end_line + 1):
                    if i == start_line:
                        start_offset = start_index
                    if i == end_line:
                        end_offset = start_index

                    index = text.index("\n", start_index)
                    start_index = index + 1

                return start_offset, end_offset

            s, e = get_start_end(self.css, section)
            start = s + section.get_start_position()
            end = e + section.get_end_position()

        self.__css_parsing_status(error.message, start, end)

    def __on_notify(self, obj, pspec):
        self.__update()

    def __update(self):
        self.remove()

        if self.is_global or (self.provider_for and self.ui_id in self.provider_for):
            self.load()

    def load(self):
        self.error_count = 0

        if Gtk.MAJOR_VERSION == 4:
            try:
                self.load_from_string(self.css)
            except Exception:
                return
            Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), self, self.priority)
        else:
            try:
                self.load_from_data(self.css, -1)
            except Exception:
                return
            Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), self, self.priority)

        if self.error_count == 0:
            self.__css_parsing_status(None, -1, -1)

    def remove(self):
        if Gtk.MAJOR_VERSION == 4:
            Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), self)
        elif Gtk.MAJOR_VERSION == 3:
            Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(), self)
