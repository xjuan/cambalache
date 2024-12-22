#
# CmbFlagsEntry
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

from gi.repository import GObject, Gtk
from ..cmb_type_info import CmbTypeInfo


class CmbFlagsEntry(Gtk.Entry):
    __gtype_name__ = "CmbFlagsEntry"

    info = GObject.Property(type=CmbTypeInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    id_column = GObject.Property(type=int, default=1, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    text_column = GObject.Property(type=int, default=1, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    value_column = GObject.Property(type=int, default=2, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    separator = GObject.Property(type=str, default="|", flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        self.flags = {}
        self._checks = {}

        super().__init__(**kwargs)

        self.props.editable = False
        self.props.secondary_icon_name = "document-edit-symbolic"

        self.connect("icon-release", self.__on_icon_release)

        self.__init_popover()

    def __init_popover(self):
        self._popover = Gtk.Popover()
        self._popover.set_parent(self)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(Gtk.Label(label=f"<b>{self.info.type_id}</b>", use_markup=True))
        box.append(Gtk.Separator())
        sw = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, propagate_natural_height=True, max_content_height=360)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sw.set_child(vbox)
        box.append(sw)

        for row in self.info.flags:
            flag = row[self.text_column]
            flag_id = row[self.id_column]

            check = Gtk.CheckButton(label=flag)
            check.connect("toggled", self.__on_check_toggled, flag_id)
            vbox.append(check)
            self._checks[flag_id] = check

        self._popover.set_child(box)

    def __on_check_toggled(self, check, flag_id):
        self.flags[flag_id] = check.props.active
        self.props.text = self.__to_string()
        self.notify("cmb-value")

    def __on_icon_release(self, obj, pos):
        self._popover.popup()

    def __to_string(self):
        retval = None
        for row in self.info.flags:
            flag_id = row[self.id_column]
            if self.flags.get(flag_id, False):
                retval = flag_id if retval is None else f"{retval} {self.separator} {flag_id}"

        return retval if retval is not None else ""

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.text if self.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if value == self.props.text:
            return

        self.props.text = value if value is not None else ""

        self.flags = {}
        for check in self._checks:
            self._checks[check].props.active = False

        if value:
            tokens = [t.strip() for t in value.split(self.separator)]

            for row in self.info.flags:
                flag_id = row[self.id_column]
                flag_name = row[0]
                flag_nick = row[1]

                check = self._checks.get(flag_id, None)
                if check:
                    val = flag_name in tokens or flag_nick in tokens
                    check.props.active = val
                    self.flags[flag_id] = val
