# GtkBox Controller
#
# Copyright (C) 2021  Juan Pablo Ugarte
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

from gi.repository import GObject, Gtk

from .mrg_gtk_widget import MrgGtkWidget
from merengue import MrgPlaceholder, getLogger

logger = getLogger(__name__)


class MrgGtkBox(MrgGtkWidget):
    object = GObject.Property(type=Gtk.Box, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.size = None
        super().__init__(**kwargs)

    def add(self, child):
        if self.object is None:
            return

        if Gtk.MAJOR_VERSION == 3:
            self.object.add(child)
        else:
            self.object.append(child)

    def __ensure_placeholders(self):
        if self.object is None:
            return

        children = self.get_children()
        n_children = len(children)

        if self.size is None:
            self.size = n_children if n_children else 3

        for i in range(n_children, self.size):
            self.add(MrgPlaceholder(visible=True, controller=self))

    def object_changed(self, old, new):
        super().object_changed(old, new)

        self.__ensure_placeholders()

    def get_child_position(self, child):
        return self.get_children().index(child)

    def get_child_layout(self, child, layout):
        if Gtk.MAJOR_VERSION == 3:
            layout["position"] = self.get_child_position(child)

        return super().get_child_layout(child, layout)

    def remove_child(self, child):
        if self.object is None:
            return

        if Gtk.MAJOR_VERSION == 4:
            self.object.remove(child)
        else:
            super().remove_child(child)

    def add_placeholder(self, mod):
        self.add(MrgPlaceholder(visible=True, controller=self))
        self.size += 1

    def remove_placeholder(self, mod):
        children = self.get_children()
        if len(children) <= 1:
            return

        for child in reversed(children):
            if isinstance(child, MrgPlaceholder):
                self.remove_child(child)
                self.size -= 1
                break
            else:
                if Gtk.MAJOR_VERSION == 4:
                    break
                else:
                    (pack_type,) = self.child_get(child, ["pack-type"])
                    if pack_type == Gtk.PackType.START:
                        break
