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

from gi.repository import GObject, Adw, CambalachePrivate
from merengue.mrg_gtk import MrgGtkWidget, MrgSelection
from merengue import MrgPlaceholder


class MrgAdwDialog(MrgGtkWidget):
    object = GObject.Property(type=Adw.Dialog, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.__headerbar_height = 0
        super().__init__(**kwargs)

        self.selection = MrgSelection(app=self.app, container=self.object)

    def object_changed(self, old, new):
        if old:
            old.close()

        # Handle widget selection
        if self.selection:
            self.selection.container = self.object

        self.on_selected_changed()

        if self.object is None:
            return

        # Make sure we call adw_dialog_present()
        self.object.present(None)

        self.object.set_title(GObject.type_name(self.object.__gtype__))
        CambalachePrivate.widget_set_application_id(self.object.props.parent, f"Casilda:{self.ui_id}.{self.object_id}")
        self.__update_placeholder()

    def __update_placeholder(self):
        if self.object is None:
            return

        if len(self.get_children()) == 0:
            self.add(MrgPlaceholder(visible=True, controller=self))

    def get_children(self):
        child = self.object.get_child() if self.object else None
        return [child] if child else []

    def add(self, child):
        if self.object:
            self.object.set_child(child)
