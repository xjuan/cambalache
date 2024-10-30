#
# Cambalache UI wrapper
#
# Copyright (C) 2021  Juan Pablo Ugarte
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

from gi.repository import GObject, Gio

from .cmb_list_error import CmbListError
from .cmb_objects_base import CmbBaseUI, CmbBaseObject
from cambalache import getLogger, _

logger = getLogger(__name__)


class CmbUI(CmbBaseUI, Gio.ListModel):
    __gsignals__ = {
        "library-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.connect("notify", self.__on_notify)

    def __bool__(self):
        # Override Truth Value Testing to ensure that CmbUI objects evaluates to True even if it does not have children objects
        return True

    def __str__(self):
        return f"CmbUI<{self.display_name}>"

    @GObject.Property(type=int)
    def template_id(self):
        retval = self.db_get("SELECT template_id FROM ui WHERE (ui_id) IS (?);", (self.ui_id,))
        return retval if retval is not None else 0

    @template_id.setter
    def _set_template_id(self, value):
        self.db_set("UPDATE ui SET template_id=? WHERE (ui_id) IS (?);", (self.ui_id,), value if value != 0 else None)

    def __on_notify(self, obj, pspec):
        self.project._ui_changed(self, pspec.name)

    def list_libraries(self):
        retval = {}

        for row in self.project.db.execute(
            """
            SELECT DISTINCT t.library_id, NULL
            FROM object AS o, type AS t
            WHERE t.library_id IS NOT NULL AND o.ui_id=? AND o.type_id = t.type_id
            UNION
            SELECT library_id, version FROM ui_library WHERE ui_id=?
            """,
            (self.ui_id, self.ui_id),
        ).fetchall():
            library_id, version = row

            versions = []
            for row in self.project.db.execute(
                "SELECT version FROM library_version WHERE library_id=? ORDER BY version COLLATE version DESC;", (library_id,)
            ).fetchall():
                versions.append(row[0])

            retval[library_id] = {"target": version, "versions": versions}

        return retval

    def get_library(self, library_id):
        c = self.project.db.execute("SELECT version FROM ui_library WHERE ui_id=? AND library_id=?;", (self.ui_id, library_id))
        row = c.fetchone()
        return row[0] if row is not None else None

    def _library_changed(self, lib):
        self.emit("library-changed", lib)
        self.project._ui_library_changed(self, lib)

    def set_library(self, library_id, version, comment=None):
        c = self.project.db.cursor()

        try:
            if version is None:
                c.execute("DELETE FROM ui_library WHERE ui_id=? AND library_id=?;", (self.ui_id, library_id))
            else:
                # Do not use REPLACE INTO, to make sure both INSERT and UPDATE triggers are used
                count = self.db_get(
                    "SELECT count(version) FROM ui_library WHERE ui_id=? AND library_id=?;", (self.ui_id, library_id)
                )

                if count:
                    c.execute(
                        "UPDATE ui_library SET version=?, comment=? WHERE ui_id=? AND library_id=?;",
                        (str(version), comment, self.ui_id, library_id),
                    )
                else:
                    c.execute(
                        "INSERT INTO ui_library (ui_id, library_id, version, comment) VALUES (?, ?, ?, ?);",
                        (self.ui_id, library_id, str(version), comment),
                    )

            self._library_changed(library_id)
        except Exception as e:
            logger.warning(f"{self} Error setting library {library_id}={version}: {e}")

        c.close()

    @GObject.Property(type=str)
    def display_name(self):
        if self.filename:
            return self.filename

        template_id = self.template_id

        if template_id:
            template = self.project.get_object_by_id(self.ui_id, template_id)
            if template:
                return template.name

        return _("Unnamed {ui_id}").format(ui_id=self.ui_id)

    def __get_infered_target(self, library_id):
        ui_id = self.ui_id

        row = self.project.db.execute(
            """
            WITH lib_version(version) AS (
                SELECT t.version
                FROM object AS o, type AS t
                WHERE t.library_id=? AND o.ui_id=? AND o.type_id = t.type_id AND t.version IS NOT NULL
                UNION
                SELECT p.version
                FROM object_property AS o, property AS p, type AS t
                WHERE t.library_id=? AND o.ui_id=? AND o.owner_id = t.type_id AND o.owner_id = p.owner_id
                  AND p.version IS NOT NULL
                UNION
                SELECT s.version
                FROM object_signal AS o, signal AS s, type AS t
                WHERE t.library_id=? AND o.ui_id=? AND o.owner_id = t.type_id AND o.owner_id = s.owner_id
                  AND s.version IS NOT NULL
            )
            SELECT MAX_VERSION(version) FROM lib_version;
            """,
            (library_id, ui_id, library_id, ui_id, library_id, ui_id),
        ).fetchone()

        return row[0] if row is not None else None

    def get_target(self, library_id):
        target = self.get_library(library_id)
        if target is None:
            target = self.__get_infered_target(library_id)

        if target is None:
            info = self.project.library_info.get(library_id, None)
            if info:
                return info.min_version

        return target

    # GListModel iface
    def do_get_item(self, position):
        ui_id = self.ui_id

        # This query should use auto index from UNIQUE constraint
        retval = self.db_get(
            """
            SELECT object_id
            FROM (
                SELECT ROW_NUMBER() OVER (ORDER BY position ASC) rownum, object_id
                FROM object
                WHERE ui_id=? AND parent_id IS NULL
            )
            WHERE rownum=?;
            """,
            (ui_id, position+1)
        )
        if retval is not None:
            return self.project.get_object_by_id(ui_id, retval)

        # This should not happen
        return CmbListError()

    def do_get_item_type(self):
        return CmbBaseObject

    @GObject.Property(type=int)
    def n_items(self):
        retval = self.db_get("SELECT COUNT(object_id) FROM object WHERE ui_id=? AND parent_id IS NULL;", (self.ui_id,))
        return retval if retval is not None else 0

    def do_get_n_items(self):
        return self.n_items
