#
# Cambalache Layout Property wrapper
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

from .cmb_objects_base import CmbBaseLayoutProperty, CmbPropertyInfo
from . import utils


class CmbLayoutProperty(CmbBaseLayoutProperty):
    object = GObject.Property(type=GObject.GObject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    info = GObject.Property(type=CmbPropertyInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        self.__on_init = True
        super().__init__(**kwargs)
        self.__on_init = False
        self.version_warning = None

        owner_info = self.project.type_info.get(self.info.owner_id, None)
        self.library_id = owner_info.library_id
        self._update_version_warning()

        self.connect("notify", self.__on_notify)

    def __str__(self):
        return f"CmbLayoutProperty<{self.object.type_id} {self.info.owner_id}:{self.property_id}>"

    def __on_notify(self, obj, pspec):
        obj = self.object
        self.project._object_layout_property_changed(obj.parent, obj, self)

    @GObject.Property(type=str)
    def value(self):
        c = self.project.db.execute(
            """
            SELECT value
            FROM object_layout_property
            WHERE ui_id=? AND object_id=? AND child_id=? AND owner_id=? AND property_id=?;
            """,
            (self.ui_id, self.object_id, self.child_id, self.owner_id, self.property_id),
        )
        row = c.fetchone()
        return row[0] if row is not None else self.info.default_value

    @value.setter
    def _set_value(self, value):
        # Update object position if this is a position property
        if self.info.is_position and not self.__on_init:
            self.object.parent.reorder_child(self.object, int(value) if value else 0)
            return

        c = self.project.db.cursor()

        if value is None or value == self.info.default_value:
            c.execute(
                """
                DELETE FROM object_layout_property
                WHERE ui_id=? AND object_id=? AND child_id=? AND owner_id=? AND property_id=?;
                """,
                (self.ui_id, self.object_id, self.child_id, self.owner_id, self.property_id),
            )
            value = None
        else:
            # Do not use REPLACE INTO, to make sure both INSERT and UPDATE triggers are used
            count = self.db_get(
                """
                SELECT count(value)
                FROM object_layout_property
                WHERE ui_id=? AND object_id=? AND child_id=? AND owner_id=? AND property_id=?;
                """,
                (self.ui_id, self.object_id, self.child_id, self.owner_id, self.property_id),
            )

            if count:
                c.execute(
                    """
                    UPDATE object_layout_property
                    SET value=?
                    WHERE ui_id=? AND object_id=? AND child_id=? AND owner_id=? AND property_id=?;
                    """,
                    (value, self.ui_id, self.object_id, self.child_id, self.owner_id, self.property_id),
                )
            else:
                c.execute(
                    """
                    INSERT INTO object_layout_property (ui_id, object_id, child_id, owner_id, property_id, value)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (self.ui_id, self.object_id, self.child_id, self.owner_id, self.property_id, value),
                )

        if not self.__on_init:
            self.object._layout_property_changed(self)

        c.close()

    def _update_version_warning(self):
        target = self.object.ui.get_target(self.library_id)
        return utils.get_version_warning(target, self.info.version, self.info.deprecated_version, self.property_id)
