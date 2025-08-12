#
# CmbSourceView
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

from gi.repository import GObject, Gtk, GtkSource


class CmbSourceView(GtkSource.View):
    __gtype_name__ = "CmbSourceView"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.manager = GtkSource.LanguageManager.get_default()

        self.buffer = GtkSource.Buffer()
        self.props.buffer = self.buffer
        self.buffer.connect("changed", self.__on_buffer_changed)

        self.connect("notify::root", self.__on_parent_notify)
        self.__source_style_binding = None

    def __on_parent_notify(self, obj, pspec):
        if self.__source_style_binding:
            self.__source_style_binding.unbind()
            self.__source_style_binding = None

        root = self.props.root
        if root is None:
            return

        if isinstance(root, Gtk.ApplicationWindow) and hasattr(root, "source_style"):
            self.__source_style_binding = GObject.Object.bind_property(
                root,
                "source-style",
                self.buffer,
                "style-scheme",
                GObject.BindingFlags.SYNC_CREATE,
            )

    @GObject.Property(type=str)
    def lang(self):
        language = self.buffer.get_language()
        return language.get_id() if language else ""

    @lang.setter
    def _set_lang(self, value):
        lang = self.manager.get_language(value)
        self.buffer.set_language(lang)

    @GObject.Property(type=str)
    def text(self):
        return self.buffer.props.text if len(self.buffer.props.text) else None

    @text.setter
    def _set_text(self, value):
        self.buffer.set_text(value if value else "")

    def __on_buffer_changed(self, buffer):
        self.notify("text")
