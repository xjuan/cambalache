#
# Cambalache CSS wrapper
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

import os

from gi.repository import GObject

from .cmb_path import CmbPath
from .cmb_objects_base import CmbBaseCSS
from .cmb_file_monitor import CmbFileMonitor

from cambalache import _


class CmbCSS(CmbBaseCSS, CmbFileMonitor):
    path_parent = GObject.Property(type=CmbPath, flags=GObject.ParamFlags.READWRITE)
    css = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self._path = None

        super().__init__(**kwargs)
        self.init_monitor(self.filename)

        self.connect("notify", self.__on_notify)
        self.load_css()

    def __on_notify(self, obj, pspec):
        if pspec.name not in ["css"]:
            self.project._css_changed(self, pspec.name)

        if pspec.name == "filename":
            self.load_css()
            self.update_file_monitor(self.filename)

    @classmethod
    def get_display_name(cls, css_id, filename):
        return os.path.basename(filename) if filename else _("Unnamed CSS {css_id}").format(css_id=css_id)

    @GObject.Property(type=str)
    def display_name(self):
        return CmbCSS.get_display_name(self.css_id, self.filename)

    @GObject.Property(type=int)
    def priority(self):
        retval = self.db_get("SELECT priority FROM css WHERE css_id=?;", (self.css_id,))
        return retval if retval is not None else 0

    @priority.setter
    def _set_priority(self, value):
        self.db_set("UPDATE css SET priority=? WHERE css_id=?;", (self.css_id,), value if value != 0 else None)

    @GObject.Property(type=object)
    def provider_for(self):
        c = self.project.db.cursor()

        retval = []
        for row in c.execute("SELECT ui_id FROM css_ui WHERE css_id=? ORDER BY ui_id;", (self.css_id,)):
            retval.append(row[0])

        c.close()
        return retval

    def load_css(self):
        if not self.project or not self.filename:
            return False

        dirname = os.path.dirname(self.project.filename)
        path = os.path.join(dirname, self.filename)

        if os.path.exists(path):
            self._path = path
            with open(path) as fd:
                self.css = fd.read()
                fd.close()

                return True
        else:
            self._path = None

        return False

    def save_css(self):
        if not self.project or not self.filename:
            return

        needs_load = False

        if self._path is None:
            dirname = os.path.dirname(self.project.filename)
            self._path = os.path.join(dirname, self.filename)
            needs_load = True

        with open(self._path, "w") as fd:
            fd.write(self.css)

        if needs_load:
            self.notify("filename")

    def add_ui(self, ui):
        c = self.project.db.cursor()

        # Do not use REPLACE INTO, to make sure both INSERT and UPDATE triggers are used
        count = self.db_get("SELECT count(css_id) FROM css_ui WHERE css_id=? AND ui_id=?;", (self.css_id, ui.ui_id))

        if count == 0:
            c.execute("INSERT INTO css_ui (css_id, ui_id) VALUES (?, ?);", (self.css_id, ui.ui_id))

        c.close()

        self.notify("provider_for")

    def remove_ui(self, ui):
        c = self.project.db.cursor()

        c.execute("DELETE FROM css_ui WHERE css_id=? AND ui_id=?;", (self.css_id, ui.ui_id))
        c.close()

        self.notify("provider_for")
