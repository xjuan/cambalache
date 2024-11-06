#
# CmbObjectListEditor
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
from ..cmb_object import CmbObject


class CmbObjectListEditor(Gtk.ScrolledWindow):
    __gtype_name__ = "CmbObjectListEditor"

    parent = GObject.Property(type=CmbObject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    type_id = GObject.Property(type=str, default=None, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__updating = False
        self.__object_ids = None

        self.props.height_request = 96
        self.buffer = Gtk.TextBuffer()
        self.view = Gtk.TextView(visible=True, buffer=self.buffer)
        self.set_child(self.view)

        self.buffer .connect("notify::text", self.__on_text_notify)

    def __on_text_notify(self, obj, pspec):
        if self.__updating:
            return

        text = self.buffer.props.text
        objects = []

        if text and len(text):
            names = [name.strip() for name in text.split("\n")]
            ui_id = self.parent.ui_id
            project = self.parent.project

            for name in names:
                obj = project.get_object_by_name(ui_id, name)
                if obj is not None:
                    objects.append(str(obj.object_id))

        objects = ",".join(objects)

        if self.__object_ids == objects:
            return

        self.__object_ids = objects
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.__object_ids

    @cmb_value.setter
    def _set_cmb_value(self, value):
        value = value if value else None

        if self.__object_ids == value:
            return

        self.__object_ids = value

        self.__updating = True
        if self.__object_ids:
            names = self.parent.project._get_object_list_names(self.parent.ui_id, self.__object_ids)
            self.buffer.props.text = "\n".join(names)
        else:
            self.buffer.props.text = ""
        self.__updating = False
