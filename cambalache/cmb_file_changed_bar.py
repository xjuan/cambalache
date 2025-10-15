#
# CmbFileChangedBar - Cambalache File Changed Bar
#
# Copyright (C) 2025  Juan Pablo Ugarte
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

from .cmb_base import CmbBase


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_file_changed_bar.ui")
class CmbFileChangedBar(Gtk.Box):
    __gtype_name__ = "CmbFileChangedBar"

    revealer = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self._object = None
        self.__binding = None

        super().__init__(**kwargs)

    @GObject.Property(type=CmbBase)
    def object(self):
        return self._object

    @object.setter
    def _set_object(self, obj):
        if self.__binding:
            self.__binding.unbind()
            self.__binding = None

        self._object = obj

        if obj:
            self.__binding = obj.bind_property(
                "changed-on-disk",
                self.revealer,
                "reveal-child",
                GObject.BindingFlags.SYNC_CREATE,
            )

    @Gtk.Template.Callback("on_close_clicked")
    def __on_close_clicked(self, button):
        if self._object:
            self._object.changed_on_disk = False
        else:
            self.revealer.props.reveal_child = False

    @Gtk.Template.Callback("on_reload_clicked")
    def __on_reload_clicked(self, button):
        if self._object:
            self._object.reload()
