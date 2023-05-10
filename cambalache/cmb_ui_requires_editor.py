#
# CmbUIRequiresEditor - Cambalache UI Requires Editor
#
# Copyright (C) 2023  Juan Pablo Ugarte
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

from gi.repository import GObject, Gtk

from .cmb_ui import CmbUI


class CmbUIRequiresEditor(Gtk.Grid):
    __gtype_name__ = "CmbUIRequiresEditor"

    def __init__(self, **kwargs):
        self._object = None

        super().__init__(**kwargs)

        self.props.column_spacing = 4
        self.props.row_spacing = 4

    @GObject.Property(type=CmbUI)
    def object(self):
        return self._object

    @object.setter
    def _set_object(self, obj):
        if obj == self._object:
            return

        self._object = obj
        self.set_sensitive(obj is not None)

        if obj:
            i = 0
            for library_id, data in obj.list_libraries().items():
                label = Gtk.Label(label=library_id, visible=True)
                combo = self.__combobox_new(library_id, **data)

                self.attach(label, 1, i, 1, 1)
                self.attach(combo, 2, i, 1, 1)
                i += 1

    def __on_combobox_changed(self, combo, library_id):
        if self._object:
            self._object.set_library(library_id, combo.get_active_id())

    def __combobox_new(self, library_id, versions=[], target=None):
        combo = Gtk.ComboBoxText(visible=True)
        for version in versions:
            combo.append(version, version)

        if target:
            combo.set_active_id(target)

        combo.connect("changed", self.__on_combobox_changed, library_id)

        return combo
        
