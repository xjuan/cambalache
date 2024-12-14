#
# CmbPath
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

from gi.repository import GObject, Gio

from .cmb_base import CmbBase


class CmbPath(CmbBase, Gio.ListModel):
    __gtype_name__ = "CmbPath"

    path_parent = GObject.Property(type=CmbBase, flags=GObject.ParamFlags.READWRITE)
    path = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # GListModel
        self.__items = []
        self.__path_items = {}

    def __bool__(self):
        return True

    def __str__(self):
        return f"CmbPath<{self.path}>"

    @GObject.Property(type=str)
    def display_name(self):
        return self.path

    def get_item(self, directory):
        return self.__path_items.get(directory, None)

    def add_item(self, item, path=None):
        if path:
            self.__path_items[path] = item

        display_name = item.display_name
        is_path = isinstance(item, CmbPath)

        i = 0
        for list_item in self.__items:
            if is_path:
                if not isinstance(list_item, CmbPath):
                    break

                if display_name < list_item.display_name:
                    break
            elif not isinstance(list_item, CmbPath) and display_name < list_item.display_name:
                break

            i += 1

        item.path_parent = self
        self.__items.insert(i, item)
        self.items_changed(i, 0, 1)

    def remove_item(self, item):
        i = self.__items.index(item)
        self.__items.pop(i)
        self.items_changed(i, 1, 0)

    # GListModel iface
    @GObject.Property(type=int)
    def n_items(self):
        return len(self.__items)

    def do_get_item(self, position):
        return self.__items[position] if position < len(self.__items) else None

    def do_get_item_type(self):
        return CmbBase

    def do_get_n_items(self):
        return self.n_items

