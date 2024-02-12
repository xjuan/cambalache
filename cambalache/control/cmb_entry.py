#
# CmbEntry
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

from gi.repository import GObject, Gtk
from .cmb_translatable_popover import CmbTranslatablePopover


class CmbEntry(Gtk.Entry):
    __gtype_name__ = "CmbEntry"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::text", self.__on_text_notify)

    def make_translatable(self, target):
        self._target = target
        self.props.secondary_icon_name = "document-edit-symbolic"
        self.connect("icon-press", self.__on_icon_pressed)

    def __on_icon_pressed(self, widget, icon_pos):
        popover = CmbTranslatablePopover()
        popover.set_parent(self)
        popover.bind_properties(self._target)
        popover.popup()

    def __on_text_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.text if self.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.text = value if value is not None else ""
