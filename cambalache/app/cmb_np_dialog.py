#
# CmbNewProjectDialog
#
# Copyright (C) 2026  Matthieu Lorier
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
#   Matthieu Lorier <loriermatthieu@gmail.com>
#
# SPDX-License-Identifier: LGPL-2.1-only
#

import os

from gi.repository import Gtk, Adw, GObject, GLib
from cambalache import getLogger, _

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/app/cmb_np_dialog.ui")
class CmbNewProjectDialog(Adw.Dialog):
    __gtype_name__ = "CmbNewProjectDialog"
    __gsignals__ = {
        "create-new-project": (GObject.SignalFlags.ACTION, None, (str, str, str))
    }

    name_entry = Gtk.Template.Child()
    ui_filename_entry = Gtk.Template.Child()
    location_row = Gtk.Template.Child()
    toolkit_chooser = Gtk.Template.Child()
    create_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        home = GLib.get_home_dir()
        projects = os.path.join(home, "Projects")
        self.__location = projects if os.path.isdir(projects) else home

    @GObject.Property(type=str)
    def location(self):
        return self.__location

    @location.setter
    def location(self, location):
        self.__location = location
        self.location_row.props.subtitle = self.__location

    @Gtk.Template.Callback("on_name_entry_changed")
    def __on_name_entry_changed(self, entry):
        name = entry.get_text()
        sensitive = len(name) > 0
        filename = ""

        if sensitive:
            name, ext = os.path.splitext(name)
            filename = os.path.join(self.location, name + ".cmb")

            if os.path.exists(filename):
                error_msg = _("File name already exists, choose a different name.")
                self.name_entry.props.tooltip_text = error_msg
                self.create_button.props.tooltip_text = error_msg

                self.name_entry.add_css_class("warning")

                self.create_button.set_sensitive(False)
            else:
                self.name_entry.remove_css_class("warning")
                self.name_entry.props.tooltip_text = None
                self.create_button.props.tooltip_text = None
                self.create_button.set_sensitive(True)

            self.ui_filename_entry.set_text(name + ".ui")
        else:
            self.name_entry.add_css_class("warning")
            self.ui_filename_entry.set_text("")

        self.location_row.set_sensitive(sensitive)
        self.ui_filename_entry.set_sensitive(sensitive)

    @Gtk.Template.Callback("on_location_button_clicked")
    def __on_location_button_clicked(self, button):
        def dialog_callback(dialog, res):
            try:
                self.location = dialog.select_folder_finish(res).get_path()
            except Exception as e:
                logger.warning(f"Error {e}")

        dialog = Gtk.FileDialog(title=_("Select project location"), modal=True)
        dialog.select_folder(self.props.root, None, dialog_callback)

    @Gtk.Template.Callback("on_create_button_clicked")
    def __on_create_button_clicked(self, button):
        name = self.name_entry.props.text
        uiname = self.ui_filename_entry.props.text
        filename = ""
        uipath = ""
        target_tk = self.toolkit_chooser.props.active_name

        if len(name):
            name, ext = os.path.splitext(name)
            filename = os.path.join(self.location, name + ".cmb")

            if len(uiname) == 0:
                uiname = self.name_entry.props.text + ".ui"

            if os.path.exists(filename):
                self.name_entry.props.title = _("File name already exists, choose a different name.")
                self.set_focus(self.name_entry)
                return

            uipath = os.path.join(self.location, uiname)

        self.emit("create-new-project", target_tk, filename, uipath)
