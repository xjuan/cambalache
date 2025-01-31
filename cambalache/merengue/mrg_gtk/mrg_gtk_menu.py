# GtkMenu Controller
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

from gi.repository import GObject, Gdk, Gtk, CambalachePrivate

from .mrg_selection import MrgSelection
from .mrg_gtk_widget import MrgGtkWidget


class MrgGtkMenu(MrgGtkWidget):
    object = GObject.Property(type=Gtk.Menu, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.window = None
        self.__button = None

        super().__init__(**kwargs)

        self.property_ignore_list.add("attach-widget")

    def popup(self):
        if self.object is None:
            return

        self.object.popup_at_widget(self.object.get_attach_widget(), Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)

    def object_changed(self, old, new):
        self.selection = None

        if self.object is None:
            if self.window:
                self.window.destroy()
                self.window = None
            return

        self.selection = MrgSelection(app=self.app, container=self.object)
        if self.object.get_attach_widget() is not None:
            return

        if self.window is None:
            self.__button = Gtk.MenuButton(
                visible=True, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, receives_default=False
            )

            image = Gtk.Image(visible=True, icon_name="open-menu-symbolic")
            self.__button.add(image)

            self.window = Gtk.Window(title="Menu Preview Window", deletable=False, width_request=320, height_request=240)
            self.window.add(self.__button)

        self.__button.set_popup(self.object)
        self.window.show_all()
        CambalachePrivate.widget_set_application_id(self.window, f"Casilda:{self.ui_id}.{self.object_id}")

    def on_selected_changed(self):
        super().on_selected_changed()

        if self.selected:
            self.popup()
        else:
            self.object.popdown()

    def show_child(self, child):
        self.popup()
