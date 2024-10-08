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
from .cmb_objects_base import CmbBaseLibraryInfo


class CmbLibraryInfo(CmbBaseLibraryInfo):
    third_party = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.object_types = self.__init_object_types()
        self.min_version = self.__init_min_version()

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
