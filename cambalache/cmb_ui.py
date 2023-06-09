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

from gi.repository import GObject

from .cmb_objects_base import CmbBaseUI
from cambalache import getLogger, _

logger = getLogger(__name__)


class CmbUI(CmbBaseUI):
    __gsignals__ = {
        "library-changed": (GObject.SignalFlags.RUN_FIRST, None, (str, )),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.connect("notify", self.__on_notify)

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
            (self.ui_id, self.ui_id)
        ).fetchall():
            library_id, version = row

            versions = []
            for row in self.project.db.execute(
                "SELECT version FROM library_version WHERE library_id=? ORDER BY version COLLATE version DESC;",
                (library_id, )
            ).fetchall():
                versions.append(row[0])

            retval[library_id] = { "target": version, "versions": versions }

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

    def get_display_name(self):
        return self.filename if self.filename else _("Unnamed {ui_id}").format(ui_id=self.ui_id)
