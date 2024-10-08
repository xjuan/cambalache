#
# CmbFragmentEditor - Cambalache CSS Editor
#
# Copyright (C) 2022-2024  Juan Pablo Ugarte
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
from .cmb_object import CmbObject


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_fragment_editor.ui")
class CmbFragmentEditor(Gtk.Box):
    __gtype_name__ = "CmbFragmentEditor"

    view = Gtk.Template.Child()
    child_view = Gtk.Template.Child()
    switcher = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self._object = None
        self.__bindings = []

        super().__init__(**kwargs)

    @GObject.Property(type=GObject.Object)
    def object(self):
        return self._object

    @object.setter
    def _set_object(self, obj):
        if obj == self._object:
            return

        for binding in self.__bindings:
            binding.unbind()

        self.__bindings = []

        self._object = obj

        if obj is None:
            return

        binding = GObject.Object.bind_property(
            obj,
            "custom-fragment",
            self.view,
            "text",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )
        self.__bindings.append(binding)

        # Only objects have child fragments
        if type(obj) is CmbObject and obj.parent:
            binding = GObject.Object.bind_property(
                obj,
                "custom-child-fragment",
                self.child_view,
                "text",
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            )
            self.__bindings.append(binding)

            self.switcher.set_visible(True)


Gtk.WidgetClass.set_css_name(CmbFragmentEditor, "CmbFragmentEditor")
