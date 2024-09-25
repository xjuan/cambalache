# AdwDialog Controller
#
# Copyright (C) 2024  Juan Pablo Ugarte
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

from gi.repository import GObject, Adw, Gtk, CambalachePrivate
from merengue.mrg_gtk import MrgGtkWidget, MrgSelection


class MrgAdwDialog(MrgGtkWidget):
    object = GObject.Property(type=Adw.Dialog, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def object_changed(self, old, new):
        if old:
            old.close()

        self.on_selected_changed()

        if self.object is None:
            if self.window:
                self.window.hide()
            return

        if self.window is None:
            self.window = self.__window_new()
            self.selection = MrgSelection(app=self.app, container=self.window)

        # Make sure we call adw_dialog_present() instead of adding the widget to a window
        self.object.present(self.window)
        self.window.present()

        self.window.set_title(GObject.type_name(self.object.__gtype__))
        CambalachePrivate.widget_set_application_id(self.window, f"Casilda:{self.ui_id}.{self.object_id}")

    def __window_new(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        headerbar = Gtk.HeaderBar(valign=Gtk.Align.START, vexpand=False)
        button = Gtk.Button(label="Open", valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER, vexpand=True)
        button.connect("clicked", self.__on_open_button_clicked)
        box.append(headerbar)
        box.append(button)
        return Adw.Window(deletable=False, content=box)

    def __on_open_button_clicked(self, button):
        if self.object:
            self.object.present(self.window)

    def get_children(self):
        child = self.object.get_child() if self.object else None
        return [child] if child else []

    def add(self, child):
        if self.object:
            self.object.set_child(child)
