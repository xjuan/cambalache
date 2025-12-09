#
# Cambalache Library Info wrapper
#
# Copyright (C) 2022-2024  Juan Pablo Ugarte
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

from gi.repository import GObject
from .cmb_base_objects import CmbBaseLibraryInfo
from .cmb_type_info import CmbTypeInfo
from cambalache import _, CmbObject


class CmbLibraryInfo(CmbBaseLibraryInfo):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Type Information
        self.type_info = {}

        self.object_types = self.__init_object_types()
        self.min_version = self.__init_min_version()

        # Init type_info for this library
        for row in self.project.db.execute(
            "SELECT * FROM type WHERE parent_id IS NOT NULL AND library_id=? ORDER BY type_id;",
            (self.library_id, )
        ):
            type_id = row[0]
            info = CmbTypeInfo.from_row(self.project, *row)
            self.type_info[type_id] = info

        # Set parent back reference
        for type_id, info in self.type_info.items():
            info.parent = self.type_info.get(info.parent_id, None) or self.project.type_info.get(info.parent_id)

    def __str__(self):
        return f"CmbLibraryInfo<{self.library_id}-{self.version}>"

    def __init_object_types(self):
        prefix = self.prefix
        prefix_len = len(prefix)
        retval = []

        for row in self.project.db.execute("SELECT type_id FROM type WHERE library_id=?", (self.library_id,)):
            (type_id,) = row
            if type_id.startswith(prefix):
                # Remove Prefix from type name
                retval.append(type_id[prefix_len:])

        return retval

    def __init_min_version(self):
        row = self.project.db.execute(
            "SELECT MIN_VERSION(version) FROM library_version WHERE library_id=?;", (self.library_id,)
        ).fetchone()

        return row[0] if row is not None else None

    @GObject.Property(type=bool, default=False)
    def enabled(self):
        return self.db_get("SELECT enabled FROM library WHERE (library_id) IS (?);", (self.library_id,))

    @enabled.setter
    def _set_enabled(self, value):
        if self.enabled == value:
            return

        self.db_set("UPDATE library SET enabled=? WHERE (library_id) IS (?);", (self.library_id,), value)

        # Load or Unload type infos from project
        if value:
            self.project.type_info.update(self.type_info)
            for type_id, info in self.type_info.items():
                self.project.emit("type-info-added", info)
        else:
            for type_id in self.type_info.keys():
                info = self.project.type_info.pop(type_id)
                self.project.emit("type-info-removed", info)

        self.project._library_info_changed(self, "enabled")

