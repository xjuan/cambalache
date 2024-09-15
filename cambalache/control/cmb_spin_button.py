#
# CmbSpinButton
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

import math

from gi.repository import GObject, GLib, Gtk


class CmbSpinButton(Gtk.SpinButton):
    __gtype_name__ = "CmbSpinButton"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::value", self.__on_value_notify)
        self.props.halign = Gtk.Align.START
        self.props.numeric = True
        self.props.width_chars = 8
        self.__ignore_notify = False
        self.__cmb_value = None

    def __on_value_notify(self, obj, pspec):
        if self.__ignore_notify:
            return

        self.cmb_value = self.props.value

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.__cmb_value

    @cmb_value.setter
    def _set_cmb_value(self, value):
        value = float(value)

        if value == math.inf:
            value = GLib.MAXDOUBLE
        elif value == -math.inf:
            value = -GLib.MAXDOUBLE
        else:
            value = value

        if self.props.digits == 0:
            cmb_value = str(int(value))
        else:
            # NOTE: round() to avoid setting numbers like 0.7000000000000001
            cmb_value = str(round(value, 15))

        if value == cmb_value:
            return

        self.__ignore_notify = True
        self.__cmb_value = cmb_value
        self.props.value = value
        self.__ignore_notify = False
