#
# CmbTypeChooserPopover - Cambalache Type Chooser Popover
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

from gi.repository import GObject, Gtk

from .cmb_project import CmbProject
from .cmb_type_info import CmbTypeInfo
from .cmb_type_chooser_widget import CmbTypeChooserWidget


class CmbTypeChooserPopover(Gtk.Popover):
    __gtype_name__ = "CmbTypeChooserPopover"

    __gsignals__ = {
        "type-selected": (GObject.SignalFlags.RUN_LAST, None, (CmbTypeInfo,)),
    }

    project = GObject.Property(type=CmbProject, flags=GObject.ParamFlags.READWRITE)
    category = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    uncategorized_only = GObject.Property(type=bool, flags=GObject.ParamFlags.READWRITE, default=False)
    show_categories = GObject.Property(type=bool, flags=GObject.ParamFlags.READWRITE, default=False)
    parent_type_id = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    derived_type_id = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._chooser = CmbTypeChooserWidget()
        self._chooser.connect("type-selected", self.__on_type_selected)

        self.set_child(self._chooser)
        self.set_default_widget(self._chooser)

        for prop in [
            "project",
            "category",
            "uncategorized_only",
            "show_categories",
            "parent_type_id",
            "derived_type_id",
        ]:
            GObject.Object.bind_property(self, prop, self._chooser, prop, GObject.BindingFlags.SYNC_CREATE)

    def __on_type_selected(self, chooser, info):
        self.emit("type-selected", info)
        self.popdown()
