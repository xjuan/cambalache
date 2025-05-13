#
# CmbFileButton
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


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/control/cmb_file_button.ui")
class CmbFileButton(Gtk.Button):
    __gtype_name__ = "CmbFileButton"

    dirname = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    dialog_title = GObject.Property(type=str, default=_("Select filename"), flags=GObject.ParamFlags.READWRITE)
    use_open = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__filename = None

    @Gtk.Template.Callback("on_button_clicked")
    def __on_button_clicked(self, button):
        dialog = Gtk.FileDialog(
            modal=True,
            title=self.dialog_title
        )

        if self.dirname is not None:
            if self.__filename is not None:
                fullpath = os.path.join(self.dirname, self.__filename)
                dialog.set_initial_file(Gio.File.new_for_path(fullpath))
            else:
                dialog.set_initial_folder(Gio.File.new_for_path(self.dirname))
            #     dialog.set_initial_name("unnamed.ui")

        def dialog_callback(dialog, res):
            try:
                file = dialog.open_finish(res) if self.use_open else dialog.save_finish(res)
                self.cmb_value = os.path.relpath(file.get_path(), start=self.dirname)
            except Exception:
                pass

        if self.use_open:
            dialog.open(self.get_root(), None, dialog_callback)
        else:
            dialog.save(self.get_root(), None, dialog_callback)

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.__filename

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if value == self.__filename:
            return

        self.__filename = value if value is not None else ""
        self.label.set_label(self.__filename)
