#
# CmbNewProjectPage
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

import os

from gi.repository import GLib, GObject, Gio, Gdk, Gtk, Pango, Adw, GtkSource, CambalachePrivate


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/app/cmb_np_page.ui")
class CmbNewProjectPage(Adw.PreferencesPage):
    __gtype_name__ = "CmbNewProjectPage"
    __gsignals__ = {
        "name-changed": (GObject.SignalFlags.ACTION, None, ())
    }

    name_entry = Gtk.Template.Child()
    ui_filename_entry = Gtk.Template.Child()
    location_row = Gtk.Template.Child()
    toolkit_chooser = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__np_location = None
        
    @property
    def np_location(self):
        return self.__np_location
        
    @np_location.setter
    def np_location(self, location):
        self.__np_location = location
        
    def setup_default_project_location(self):
        home = GLib.get_home_dir()
        projects = os.path.join(home, "Projects")
        self.__np_location = projects if os.path.isdir(projects) else home
        self.location_row.props.subtitle = os.path.basename(self.__np_location)

    @Gtk.Template.Callback("on_name_entry_changed")
    def __on_name_entry_changed(self, entry):
        sensitive = bool(entry.get_text())
        if not sensitive:
            self.name_entry.add_css_class("warning")
            self.ui_filename_entry.set_text("")
        else:
            self.name_entry.remove_css_class("warning")
            self.ui_filename_entry.set_text(entry.get_text() + ".ui")
        self.location_row.set_sensitive(sensitive)
        self.ui_filename_entry.set_sensitive(sensitive)
        self.emit("name-changed")
        
    def clear_properties(self):
        self.name_entry.props.text = ""
        self.name_entry.remove_css_class("warning")
        self.ui_filename_entry.props.text = ""
        self.ui_filename_entry.set_sensitive(False)
        self.location_row.set_sensitive(False)
        self.toolkit_chooser.set_active_name("gtk-4.0")
        self.setup_default_project_location()
