#
# CmbTranslatablePopover - Cambalache Translatable Popover
#
# Copyright (C) 2021  Philipp Unger
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
#   Philipp Unger <philipp.unger.1988@gmail.com>
#

from gi.repository import Gtk

from .cmb_translatable_widget import CmbTranslatableWidget
from cambalache import _


class CmbTranslatablePopover(Gtk.Popover):
    __gtype_name__ = "CmbTranslatablePopover"

    def __init__(self, **kwargs):
        self._object = None
        super().__init__(**kwargs)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(Gtk.Label(label=_("<b>Translation</b>"), use_markup=True), False, True, 4)
        box.pack_start(Gtk.Separator(), False, False, 0)

        self._translation = CmbTranslatableWidget()
        box.pack_start(self._translation, False, False, 0)

        box.show_all()
        self.add(box)

    def bind_properties(self, target):
        self._translation.bind_properties(target)
