#
# CmbSwitch
#
# Copyright (C) 2021-2023  Juan Pablo Ugarte
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


class CmbSwitch(Gtk.Switch):
    __gtype_name__ = "CmbSwitch"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::active", self.__on_notify)
        self.props.halign = Gtk.Align.START

    def __on_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return "True" if self.props.active else "False"

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if value is not None:
            val = value.lower()

            if type(val) == str:
                if val.lower() in {"1", "t", "y", "true", "yes"}:
                    self.props.active = True
                else:
                    self.props.active = False
            else:
                self.props.active = bool(value)
        else:
            self.props.active = False
