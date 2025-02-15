#
# CmbPollOptionCheck
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

from cambalache import getLogger
from gi.repository import GLib, GObject, Gtk

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_poll_option_check.ui")
class CmbPollOptionCheck(Gtk.CheckButton):
    __gtype_name__ = "CmbPollOptionCheck"

    label = Gtk.Template.Child()
    bar = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.__fraction = None
        self.__tick_id = None
        super().__init__(**kwargs)

    @GObject.Property(type=str)
    def option(self):
        return self.label.props.label

    @option.setter
    def _set_option(self, option):
        self.label.props.label = option

    @GObject.Property(type=float)
    def fraction(self):
        return self.__fraction

    @fraction.setter
    def _set_fraction(self, fraction):
        self.__fraction = fraction

        if fraction < 0:
            self.bar.props.visible = False
        else:
            self.bar.props.visible = True
            if self.__tick_id is None:
                self.__tick_id = self.add_tick_callback(self.__update_fraction)

    def __update_fraction(self, widget, frame_clock):
        if self.bar.props.fraction < self.__fraction:
            self.bar.props.fraction = min(self.__fraction, self.bar.props.fraction + 0.08)
        elif self.bar.props.fraction > self.__fraction:
            self.bar.props.fraction = max(self.__fraction, self.bar.props.fraction - 0.08)
        else:
            self.__tick_id = None
            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE
