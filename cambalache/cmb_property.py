#
# Cambalache Property wrapper
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

from gi.repository import GObject

from .cmb_objects_base import CmbBaseProperty
from .cmb_property_info import CmbPropertyInfo
from . import utils
from cambalache import _


class CmbProperty(CmbBaseProperty):
    object = GObject.Property(type=GObject.GObject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    info = GObject.Property(type=CmbPropertyInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        self._init = True
        super().__init__(**kwargs)
        self._init = False
        self.version_warning = None

        owner_info = self.project.type_info.get(self.info.owner_id, None)
        self.library_id = owner_info.library_id
        self._update_version_warning()

        self.connect("notify", self.__on_notify)

    def __str__(self):
        return f"CmbProperty<{self.object.type_id} {self.info.owner_id}:{self.property_id}>"

    def __on_notify(self, obj, pspec):
        self.project._object_property_changed(self.object, self)

    @GObject.Property(type=str)
    def value(self):
        c = self.project.db.execute(
            "SELECT value FROM object_property WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;",
            (self.ui_id, self.object_id, self.owner_id, self.property_id),
        )
        row = c.fetchone()
        return row[0] if row is not None else self.info.default_value

    @value.setter
    def _set_value(self, value):
        self.__update_values(value, self.translatable, self.translation_context, self.translation_comments, self.bind_property)

    @GObject.Property(type=bool, default=False)
    def translatable(self):
        return super().translatable

    @translatable.setter
    def _set_translatable(self, value):
        self.__update_values(self.value, value, self.translation_context, self.translation_comments, self.bind_property)

    @GObject.Property(type=str)
    def translation_context(self):
        return self.db_get(
            "SELECT translation_context FROM object_property WHERE (ui_id, object_id, owner_id, property_id) IS (?, ?, ?, ?);",
            (
                self.ui_id,
                self.object_id,
                self.owner_id,
                self.property_id,
            ),
        )

    @translation_context.setter
    def _set_translation_context(self, value):
        self.__update_values(self.value, self.translatable, value, self.translation_comments, self.bind_property)

    @GObject.Property(type=str)
    def translation_comments(self):
        return self.db_get(
            "SELECT translation_comments FROM object_property WHERE (ui_id, object_id, owner_id, property_id) IS (?, ?, ?, ?);",
            (
                self.ui_id,
                self.object_id,
                self.owner_id,
                self.property_id,
            ),
        )

    @translation_comments.setter
    def _set_translation_comments(self, value):
        self.__update_values(self.value, self.translatable, self.translation_context, value, self.bind_property)

    def reset(self):
        self.project.db.execute(
            "DELETE FROM object_property WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;",
            (self.ui_id, self.object_id, self.owner_id, self.property_id),
        )

    def __update_values(self, value, translatable, translation_context, translation_comments, bind_property):
        c = self.project.db.cursor()

        bind_source_id, bind_owner_id, bind_property_id = (None, None, None)
        if bind_property:
            bind_source_id = bind_property.object.object_id
            bind_owner_id = bind_property.owner_id
            bind_property_id = bind_property.property_id

        if (
            (value is None or value == self.info.default_value or (self.info.is_object and value == 0)) and
            bind_property is None and
            not translatable and
            translation_context is None and
            translation_comments is None
        ):
            self.reset()
        else:
            if (
                value == self.value and
                translatable == self.translatable and
                translation_context == self.translation_context and
                translation_comments == self.translation_comments and
                bind_source_id == self.bind_source_id and
                bind_owner_id == self.bind_owner_id and
                bind_property_id == self.bind_property_id
            ):
                return

            # Do not use REPLACE INTO, to make sure both INSERT and UPDATE triggers are used
            count = self.db_get(
                "SELECT count(ui_id) FROM object_property WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;",
                (self.ui_id, self.object_id, self.owner_id, self.property_id),
            )

            if count:
                c.execute(
                    """
                    UPDATE object_property
                    SET
                      value=?,
                      translatable=?, translation_context=?, translation_comments=?,
                      bind_source_id=?, bind_owner_id=?, bind_property_id=?
                    WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;
                    """,
                    (
                        value,
                        translatable,
                        translation_context,
                        translation_comments,
                        bind_source_id,
                        bind_owner_id,
                        bind_property_id,
                        self.ui_id,
                        self.object_id,
                        self.owner_id,
                        self.property_id,
                    ),
                )
            else:
                c.execute(
                    """
                    INSERT INTO object_property
                        (
                          ui_id, object_id, owner_id, property_id,
                          value,
                          translatable, translation_context, translation_comments,
                          bind_source_id, bind_owner_id, bind_property_id
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        self.ui_id,
                        self.object_id,
                        self.owner_id,
                        self.property_id,
                        value,
                        translatable,
                        translation_context,
                        translation_comments,
                        bind_source_id,
                        bind_owner_id,
                        bind_property_id,
                    ),
                )

        if self._init is False:
            self.object._property_changed(self)

        c.close()

    @GObject.Property(type=CmbBaseProperty)
    def bind_property(self):
        c = self.project.db.cursor()
        row = c.execute(
            """
            SELECT bind_source_id, bind_property_id
            FROM object_property
            WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;
            """,
            (self.ui_id, self.object_id, self.owner_id, self.property_id),
        ).fetchone()

        if row:
            bind_source_id, bind_property_id = row
            source = self.project.get_object_by_id(self.ui_id, bind_source_id) if bind_property_id else None
            return source.properties_dict.get(bind_property_id, None) if source else None

        return None

    @bind_property.setter
    def _set_bind_property(self, bind_property):
        self.__update_values(self.value, self.translatable, self.translation_context, self.translation_comments, bind_property)
        self.project._object_property_binding_changed(self.object, self)

    def _update_version_warning(self):
        target = self.object.ui.get_target(self.library_id)
        warning = utils.get_version_warning(
            target, self.info.version, self.info.deprecated_version, self.property_id
        ) or ""

        if self.project.target_tk == "gtk-4.0" and self.info.type_id == "GFile":
            target = self.object.ui.get_target("gtk")
            if target is not None:
                version = utils.parse_version(target)
                if version is None or utils.version_cmp(version, (4, 16, 0)) < 0:
                    if len(warning):
                        warning += "\n"
                    warning += _("Warning: GFile uri needs to be absolute for Gtk < 4.16")

        self.version_warning = warning if len(warning) else None
