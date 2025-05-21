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
    accept_label = GObject.Property(type=str, default=_("Select"), flags=GObject.ParamFlags.READWRITE)
    unnamed_filename = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    use_open = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__filename = None
        self.__filters = None

    @Gtk.Template.Callback("on_button_clicked")
    def __on_button_clicked(self, button):
        dialog = Gtk.FileDialog(
            modal=True,
            filters=self.__filters,
            title=self.dialog_title,
            accept_label=self.accept_label
        )

        if self.dirname is not None:
            if self.__filename:
                fullpath = os.path.join(self.dirname, self.__filename)

                file = Gio.File.new_for_path(fullpath)
                dialog.set_initial_file(file)

                # See which filter matches the file info and use it as default
                if file.query_exists(None):
                    info = file.query_info(Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE, Gio.FileQueryInfoFlags.NONE, None)
                    for filter in self.__filters:
                        if filter.match(info):
                            dialog.set_default_filter(filter)
                            break
            else:
                dialog.set_initial_folder(Gio.File.new_for_path(self.dirname))
                if self.unnamed_filename:
                    dialog.set_initial_name(self.unnamed_filename)

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

    @GObject.Property(type=str)
    def mime_types(self):
        if self.__filters:
            return ";".join([f.props.mime_types for f in self.__filters])
        return ""

    @mime_types.setter
    def _set_mime_types(self, value):
        if value:
            self.__filters = Gio.ListStore()
            for mime in value.split(';'):
                self.__filters.append(Gtk.FileFilter(mime_types=[mime]))
        else:
            self.__filters = None
