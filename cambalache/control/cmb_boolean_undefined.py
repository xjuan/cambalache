#
# CmbBooleanUndefined
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

from gi.repository import GObject, Gtk
from cambalache import _


class CmbBooleanUndefined(Gtk.Box):
    __gtype_name__ = "CmbBooleanUndefined"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__undefined = Gtk.CheckButton(label=_("undefined"))
        self.__true = Gtk.CheckButton(label=_("true"), group=self.__undefined)
        self.__false = Gtk.CheckButton(label=_("false"), group=self.__undefined)

        for button in [self.__undefined, self.__true, self.__false]:
            self.append(button)
            button.connect("notify::active", self.__on_notify)

    def __on_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        if self.__undefined.props.active:
            return "undefined"
        elif self.__true.props.active:
            return "True"

        return "False"

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if value is not None:
            if type(value) is str:
                val = value.lower()

                if val == "undefined":
                    self.__undefined.props.active = True
                    return

                if val in {"1", "t", "y", "true", "yes"}:
                    active = True
                else:
                    active = False
            else:
                active = bool(value)

            if active:
                self.__true.props.active = True
            else:
                self.__false.props.active = True
        else:
            self.__undefined.active = True
