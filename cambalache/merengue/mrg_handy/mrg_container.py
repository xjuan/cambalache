# Container Controller
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

from merengue import MrgPlaceholder
from merengue.mrg_gtk import MrgGtkWidget


class MrgContainer(MrgGtkWidget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __get_placeholder(self):
        for child in self.get_children():
            if isinstance(child, MrgPlaceholder):
                return child
        return None

    def __ensure_placeholders(self):
        if self.object is None:
            return

        if len(self.get_children()) == 0:
            self.add(MrgPlaceholder(visible=True, controller=self))

    def object_changed(self, old, new):
        super().object_changed(old, new)
        self.__ensure_placeholders()

    def add(self, child):
        if self.object:
            self.object.add(child)

    def remove_child(self, child):
        if self.object:
            super().remove(child)

    def add_placeholder(self, mod):
        placeholder = self.__get_placeholder()

        if placeholder is None:
            placeholder = MrgPlaceholder(visible=True, controller=self)
            self.add(placeholder)

        self.show_child(placeholder)

    def remove_placeholder(self, mod):
        placeholder = self.__get_placeholder()
        if placeholder:
            self.remove_child(placeholder)
            self.size -= 1
