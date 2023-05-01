#
# Cambalache Object Data wrapper
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

from gi.repository import GObject

from .cmb_objects_base import CmbBaseObjectData
from .cmb_type_info import CmbTypeDataInfo
from cambalache import getLogger

logger = getLogger(__name__)


class CmbObjectData(CmbBaseObjectData):
    __gsignals__ = {
        "data-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbBaseObjectData,)),
        "data-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbBaseObjectData,)),
        "arg-changed": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    parent = GObject.Property(type=CmbBaseObjectData, flags=GObject.ParamFlags.READWRITE)

    object = GObject.Property(type=GObject.Object, flags=GObject.ParamFlags.READWRITE)
    info = GObject.Property(type=CmbTypeDataInfo, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.args = []
        self.children = []

        super().__init__(**kwargs)

        if self.project is None:
            return

        if self.info is None:
            type_info = self.project.type_info.get(self.owner_id, None)
            if type_info:
                self.info = type_info.find_data_info(self.data_id)

        if self.object is None:
            self.object = self.project.get_object_by_id(self.ui_id, self.object_id)

        if self.parent_id is not None and self.parent is None:
            self.parent = self.object.data_dict.get(f"{self.owner_id}.{self.parent_id}", None)

        self.__populate_children()

    def __str__(self):
        return f"CmbObjectData<{self.owner_id}:{self.info.key}> obj={self.ui_id}:{self.object_id} data={self.data_id}:{self.id}"

    def get_id_string(self):
        return f"{self.owner_id}.{self.id}"

    def get_arg(self, key):
        c = self.project.db.execute(
            "SELECT value FROM object_data_arg WHERE ui_id=? AND object_id=? AND owner_id=? AND data_id=? AND id=? AND key=?;",
            (self.ui_id, self.object_id, self.owner_id, self.data_id, self.id, key),
        )
        row = c.fetchone()
        return row[0] if row is not None else None

    def __arg_changed(self, key):
        self.emit("arg-changed", key)
        self.project._object_data_arg_changed(self, key)

    def set_arg(self, key, value):
        # Prenvent potential infinite recursion
        val = self.get_arg(key)
        if val == value:
            return

        c = self.project.db.cursor()

        try:
            if value is None:
                c.execute(
                    """
                    DELETE FROM object_data_arg
                    WHERE ui_id=? AND object_id=? AND owner_id=? AND data_id=? AND id=? AND key=?;
                    """,
                    (self.ui_id, self.object_id, self.owner_id, self.data_id, self.id, key),
                )
            else:
                # Do not use REPLACE INTO, to make sure both INSERT and UPDATE triggers are used
                count = self.db_get(
                    """
                    SELECT count(value) FROM object_data_arg
                    WHERE ui_id=? AND object_id=? AND owner_id=? AND data_id=? AND id=? AND key=?;
                    """,
                    (self.ui_id, self.object_id, self.owner_id, self.data_id, self.id, key),
                )

                if count:
                    c.execute(
                        """
                        UPDATE object_data_arg SET value=?
                        WHERE ui_id=? AND object_id=? AND owner_id=? AND data_id=? AND id=? AND key=?;
                        """,
                        (str(value), self.ui_id, self.object_id, self.owner_id, self.data_id, self.id, key),
                    )
                else:
                    c.execute(
                        """
                        INSERT INTO object_data_arg (ui_id, object_id, owner_id, data_id, id, key, value)
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                        """,
                        (self.ui_id, self.object_id, self.owner_id, self.data_id, self.id, key, str(value)),
                    )

            self.__arg_changed(key)
        except Exception as e:
            logger.warning(f"{self} Error setting arg {key}={value}: {e}")

        c.close()

    def __add_child(self, child):
        if child in self.children:
            return

        self.children.append(child)
        self.object.data_dict[child.get_id_string()] = child
        self.emit("data-added", child)
        self.project._object_data_data_added(self, child)

    def _remove_child(self, child):
        self.children.remove(child)
        del self.object.data_dict[child.get_id_string()]
        self.emit("data-removed", child)
        self.project._object_data_data_removed(self, child)

    def _add_child(self, owner_id, data_id, id, info=None):
        new_data = CmbObjectData(
            project=self.project,
            object=self.object,
            ui_id=self.ui_id,
            object_id=self.object_id,
            owner_id=owner_id,
            data_id=data_id,
            id=id,
            parent=self,
            info=info,
        )
        self.__add_child(new_data)
        return new_data

    def __populate_children(self):
        c = self.project.db.cursor()

        # Populate children
        for row in c.execute(
            "SELECT * FROM object_data WHERE ui_id=? AND object_id=? AND owner_id=? AND parent_id=?;",
            (self.ui_id, self.object_id, self.owner_id, self.id),
        ):
            obj = CmbObjectData.from_row(self.project, *row)
            self.__add_child(obj)

    def add_data(self, data_key, value=None, comment=None):
        try:
            value = str(value) if value is not None else None
            taginfo = self.info.children.get(data_key)
            owner_id = taginfo.owner_id
            data_id = taginfo.data_id
            id = self.project.db.object_add_data(self.ui_id, self.object_id, owner_id, data_id, value, self.id, comment)
        except Exception as e:
            logger.warning(f"{self} Error adding child data {data_key}: {e}")
            return None
        else:
            return self._add_child(owner_id, data_id, id, taginfo)

    def remove_data(self, data):
        try:
            assert data in self.children
            self.project.db.execute(
                "DELETE FROM object_data WHERE ui_id=? AND object_id=? AND owner_id=? AND data_id=? AND id=?;",
                (self.ui_id, self.object_id, data.owner_id, data.data_id, data.id),
            )
            self.project.db.commit()
        except Exception as e:
            logger.warning(f"{self} Error removing data {data}: {e}")
            return False
        else:
            self._remove_child(data)
            return True
