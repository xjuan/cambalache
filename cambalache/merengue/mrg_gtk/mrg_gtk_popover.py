# GtkPopover Controller
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

from gi.repository import GObject, Gtk, CambalachePrivate

from .mrg_selection import MrgSelection
from .mrg_gtk_widget import MrgGtkWidget


class MrgGtkPopover(MrgGtkWidget):
    object = GObject.Property(type=Gtk.Popover, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.window = None
        self.__button = None

        super().__init__(**kwargs)

        # Create wrapper window
        self.__button = Gtk.MenuButton(
            visible=True, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, receives_default=False
        )

        self.window = Gtk.Window(title="Popover Preview Window", deletable=False)
        self.window.set_default_size(320, 240)

        if Gtk.MAJOR_VERSION == 4:
            self.__button.set_icon_name("open-menu-symbolic")
            self.window.set_child(self.__button)
            self.property_ignore_list.add("autohide")
        else:
            self.__button.add(Gtk.Image(visible=True, icon_name="open-menu-symbolic"))
            self.window.add(self.__button)
            self.property_ignore_list.add("modal")

    def object_changed(self, old, new):
        self.selection = None

        if self.object is None:
            self.__button.set_popover(None)
            self.window.hide()
            return

        self.selection = MrgSelection(app=self.app, container=self.object)
        CambalachePrivate.widget_set_application_id(self.window, f"Cmb:{self.ui_id}.{self.object_id}")

        # TODO: keep track when these prop changes and update window
        if Gtk.MAJOR_VERSION == 4:
            unused = self.object.props.parent is None
        else:
            unused = self.object.props.relative_to is None

        if unused:
            self.__button.set_popover(self.object)

            if Gtk.MAJOR_VERSION == 3:
                self.window.show_all()
                self.object.set_modal(False)
            else:
                self.object.set_autohide(False)

            self.window.present()
        else:
            self.window.hide()

    def on_selected_changed(self):
        super().on_selected_changed()

        if self.__button:
            self.__button.popup()

    def show_child(self, child):
        if self.__button:
            self.__button.popup()
