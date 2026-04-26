#
# CmbGraphicsOffload
#
# Copyright (C) 2026 Juan Pablo Ugarte
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

from gi.repository import GLib, GObject, Gtk
from cambalache import config


class CmbGraphicsOffload(Gtk.GraphicsOffload, Gtk.Scrollable):
    __gtype_name__ = "CmbGraphicsOffload"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__hadjustment = None
        self.__vadjustment = None

        self.connect("notify::child", self.__on_child_notify)

    @GObject.Property(type=Gtk.Adjustment)
    def hadjustment(self):
        return self.__hadjustment

    @hadjustment.setter
    def _set_hadjustment(self, adjustment):
        self.__hadjustment = adjustment
        if self.props.child:
            self.props.child.props.hadjustment = adjustment

    @GObject.Property(type=Gtk.Adjustment)
    def vadjustment(self):
        return self.__vadjustment

    @vadjustment.setter
    def _set_vadjustment(self, adjustment):
        self.__vadjustment = adjustment
        if self.props.child:
            self.props.child.props.vadjustment = adjustment

    @GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)
    def hscroll_policy(self):
        return self.props.child.props.hscroll_policy if self.props.child else Gtk.ScrollablePolicy.MINIMUM

    @GObject.Property(type=Gtk.ScrollablePolicy, default=Gtk.ScrollablePolicy.MINIMUM)
    def vscroll_policy(self):
        return self.props.child.props.vscroll_policy if self.props.child else Gtk.ScrollablePolicy.MINIMUM

    def __on_child_notify(self, obj, pspec):
        if self.props.child:
            self.props.child.props.hadjustment = self.__hadjustment
            self.props.child.props.vadjustment = self.__vadjustment
