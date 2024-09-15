#
# CmbFileEntry
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

import os

from cambalache import _
from gi.repository import GObject, Gio, Gtk


class CmbFileEntry(Gtk.Entry):
    __gtype_name__ = "CmbFileEntry"

    dirname = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.title = _("Select File")
        self.filter = None
        self.props.placeholder_text = "<GFile>"
        self.props.secondary_icon_name = "document-open-symbolic"

        self.connect("notify::text", self.__on_text_notify)
        self.connect("icon-press", self.__on_icon_pressed)

    def __on_icon_pressed(self, widget, icon_pos):
        dialog = Gtk.FileDialog(
            modal=True,
            title=self.title,
            default_filter=self.filter,
        )

        if self.dirname is not None:
            dialog.set_initial_folder(Gio.File.new_for_path(self.dirname))

        def dialog_callback(dialog, res):
            try:
                file = dialog.open_finish(res)
                self.props.text = os.path.relpath(file.get_path(), start=self.dirname)
            except Exception:
                pass

        dialog.open(self.get_root(), None, dialog_callback)

    def __on_text_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.text if self.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if value == self.props.text:
            return
        self.props.text = value if value is not None else ""
