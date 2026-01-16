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

from .cmb_base_objects import CmbBaseProperty, CmbBaseObject
from .cmb_property_info import CmbPropertyInfo
from . import utils
from cambalache import _, getLogger

logger = getLogger(__name__)


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
        return f"CmbProperty<{self.object.type_id} {self.info.owner_id}::{self.property_id}>"

    def __on_notify(self, obj, pspec):
        self.object._property_changed(self, pspec.name)

    def __db_get(self, column):
        row = self.project.db.execute(
            f"SELECT {column} FROM object_property WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;",
            (self.ui_id, self.object_id, self.owner_id, self.property_id),
        ).fetchone()
        return row[0] if row is not None else None

    def has_value(self):
        return self.db_get(
            "SELECT count(ui_id) FROM object_property WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;",
            (self.ui_id, self.object_id, self.owner_id, self.property_id),
        ) > 0

    def __db_set(self, **kwargs):
        # Do not use REPLACE INTO, to make sure both INSERT and UPDATE triggers are used

        columns = tuple(kwargs.keys())
        values = tuple(kwargs.values())
        placeholders = ",".join((["?"] * len(values)))

        # Ensure row exists
        if self.has_value():
            # Execute update statement and return row values
            statement = ",".join([f"{col}=?" for col in columns])
            row = self.project.db.execute(
                f"""
                UPDATE object_property SET {statement} WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?
                RETURNING
                    value, translatable, comment, translation_context, translation_comments,
                    inline_object_id,
                    bind_source_id, bind_owner_id, bind_property_id, bind_flags,
                    binding_expression_id, binding_expression_object_id;
                """,
                values + (self.ui_id, self.object_id, self.owner_id, self.property_id)
            ).fetchone()

            value, *others = row

            # If value is the same as the default and the rest are none/false we can remove the row
            # Do not reset properties that where loaded from xml with the default value
            if not self.serialize_default_value and value == self.info.default_value and all(not val for val in others):
                self.__reset()
        else:
            self.project.db.execute(
                f"""
                INSERT INTO object_property (ui_id, object_id, owner_id, property_id, {",".join(columns)})
                VALUES (?, ?, ?, ?, {placeholders});
                """,
                (self.ui_id, self.object_id, self.owner_id, self.property_id) + values,
            )

        self.__update_internal_child()

        if self._init is False:
            self.object._property_changed(self, columns[0])

    @GObject.Property(type=str)
    def value(self):
        return self.__db_get("value") or self.info.default_value

    @value.setter
    def _set_value(self, value):
        self.__db_set(value=value)

    @GObject.Property(type=bool, default=False)
    def translatable(self):
        return self.__db_get("translatable")

    @translatable.setter
    def _set_translatable(self, value):
        self.__db_set(translatable=value)

    @GObject.Property(type=str)
    def translation_context(self):
        return self.__db_get("translation_context")

    @translation_context.setter
    def _set_translation_context(self, value):
        self.__db_set(translation_context=value)

    @GObject.Property(type=str)
    def translation_comments(self):
        return self.__db_get("translation_comments")

    @translation_comments.setter
    def _set_translation_comments(self, value):
        self.__db_set(translation_comments=value)

    def __reset(self):
        self.project.db.execute(
            "DELETE FROM object_property WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;",
            (self.ui_id, self.object_id, self.owner_id, self.property_id),
        )

    def reset(self):
        if self.info.internal_child:
            self.project.history_push(_("Unset {obj} {prop} {prop_type}").format(**self.__get_msgs()))

        self.__reset()
        self.__update_internal_child()
        self.notify("value")

        if self.info.internal_child:
            self.project.history_pop()

    def __update_internal_child(self):
        internal_info = self.info.internal_child
        if internal_info and internal_info.internal_parent_id:
            logger.warning("Adding an internal child within an internal child automatically is not implemented")
            return
        elif internal_info is None:
            return

        value = self.value
        child_id = self.db_get(
            "SELECT object_id FROM object WHERE ui_id=? AND parent_id=? AND internal=?",
            (self.ui_id, self.object_id, internal_info.internal_child_id)
        )

        if value and not child_id:
            self.project.add_object(
                self.ui_id,
                internal_info.internal_type,
                parent_id=self.object_id,
                internal=internal_info.internal_child_id
            )
        elif child_id:
            internal_child = self.project.get_object_by_id(self.ui_id, child_id)
            if internal_child:
                self.project.remove_object(internal_child, allow_internal_removal=True)

    def __get_msgs(self, value=None):
        return {
            "obj": self.object.display_name_type,
            "prop": self.property_id,
            "prop_type": _("property"),
            "value": str(value)
        }

    @GObject.Property(type=CmbBaseProperty)
    def bind_property(self):
        bind_source_id = self.bind_source_id
        bind_property_id = self.bind_property_id

        if bind_source_id and bind_property_id:
            source = self.project.get_object_by_id(self.ui_id, bind_source_id) if bind_property_id else None
            return source.properties_dict.get(bind_property_id, None) if source else None

        return None

    @bind_property.setter
    def _set_bind_property(self, bind_property):
        bind_source_id, bind_owner_id, bind_property_id, bind_flags = (None, None, None, None)

        if bind_property:
            obj = bind_property.object

            bind_source_id = obj.object_id
            bind_owner_id = bind_property.owner_id
            bind_property_id = bind_property.property_id
            bind_flags = bind_property.bind_flags

            if obj.ui_id == self.ui_id and obj.object_id == self.bind_source_id and \
               self.bind_property_id == bind_property.property_id:
                return

            self.project.history_push(
                _("Bind {object}::{property} to {bind_object}::{bind_property}").format(
                    object=self.object.display_name_type,
                    property=self.property_id,
                    bind_object=obj.display_name_type,
                    bind_property=bind_property.property_id
                )
            )
        else:
            if not self.bind_source_id and not self.bind_property_id:
                return

            self.project.history_push(
                _("Clear {object}::{property} binding").format(
                    object=self.object.display_name_type,
                    property=self.property_id
                )
            )

        self.__db_set(
            bind_source_id=bind_source_id,
            bind_owner_id=bind_owner_id,
            bind_property_id=bind_property_id,
            bind_flags=bind_flags
        )

        self.project.history_pop()
        self.project._object_property_binding_changed(self.object, self)

    @GObject.Property(type=CmbBaseObject)
    def binding_expression(self):
        return self.project.get_object_by_id(self.ui_id, self.binding_expression_id)

    @binding_expression.setter
    def _set_binding_expression(self, binding_expression):
        if binding_expression:

            if binding_expression.ui_id == self.ui_id and binding_expression.object_id == self.binding_expression_id:
                return

            self.project.history_push(
                _("Bind {object}::{property} to {expression_object}").format(
                    object=self.object.display_name_type,
                    property=self.property_id,
                    expression_object=binding_expression.display_name_type
                )
            )
        else:
            if not self.binding_expression_id:
                return

            self.project.history_push(
                _("Clear {object}::{property} binding expression").format(
                    object=self.object.display_name_type,
                    property=self.property_id
                )
            )

        self.__db_set(binding_expression_id=binding_expression.object_id)

        self.project.history_pop()
        self.project._object_property_binding_changed(self.object, self)

    @GObject.Property(type=CmbBaseObject)
    def binding_expression_object(self):
        return self.project.get_object_by_id(self.ui_id, self.binding_expression_id)

    @binding_expression.setter
    def _set_binding_expression_object(self, expression_object):
        if expression_object:
            if expression_object.ui_id == self.ui_id and expression_object.object_id == self.expression_object_id:
                return

            self.project.history_push(
                _("Bind {object}::{property} to {expression_object}").format(
                    object=self.object.display_name_type,
                    property=self.property_id,
                    expression_object=expression_object.display_name_type
                )
            )
        else:
            if not self.binding_expression_id:
                return

            self.project.history_push(
                _("Clear {object}::{property} binding expression object").format(
                    object=self.object.display_name_type,
                    property=self.property_id
                )
            )

        self.__db_set(binding_expression_id=expression_object.object_id)
        self.project.history_pop()
        self.project._object_property_binding_changed(self.object, self)

    @GObject.Property(type=bool, default=False)
    def serialize_default_value(self):
        return self.__db_get("serialize_default_value")

    @serialize_default_value.setter
    def _set_serialize_default_value(self, value):
        self.__db_set(serialize_default_value=value, value=self.value)

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

    def __clear_expression_inline_object(self):
        binding_expression_id = self.binding_expression_id

        if binding_expression_id:
            expression_source = self.project.get_object_by_id(self.ui_id, binding_expression_id)
            self.project.remove_object(expression_source)

    def clear_binding(self):
        if self.bind_property is None and self.bind_flags is None and self.binding_expression_id is None and \
           self.binding_expression_object_id is None:
            return

        self.project.history_push(
            _("Clear {object}::{property} binding").format(
                object=self.object.display_name_type,
                property=self.property_id
            )
        )

        self.__clear_expression_inline_object()

        bind_source_id = self.bind_source_id != 0
        bind_owner_id = self.bind_owner_id is not None
        bind_property_id = self.bind_property_id is not None
        bind_flags = self.bind_flags is not None
        binding_expression_id = self.binding_expression_id != 0
        binding_expression_object_id = self.binding_expression_object_id != 0

        self.__db_set(
            bind_source_id=None,
            bind_owner_id=None,
            bind_property_id=None,
            bind_flags=None,
            binding_expression_id=None,
            binding_expression_object_id=None
        )

        if bind_source_id:
            self.notify("bind-source-id")
        if bind_owner_id:
            self.notify("bind-owner-id")
        if bind_property_id:
            self.notify("bind-property-id")
        if bind_flags:
            self.notify("bind-flags")
        if binding_expression_id:
            self.notify("binding-expression-id")
        if binding_expression_object_id:
            self.notify("binding-expression-object-id")

        self.project.history_pop()

    def set_binding_expression_type(self, expression_type):
        info = self.project.type_info.get(expression_type)

        if info is None:
            return

        self.project.history_push(
            _("Bind {object}::{property} to {expression_type}").format(
                object=self.object.display_name_type,
                property=self.property_id,
                expression_type=expression_type
            )
        )

        self.__clear_expression_inline_object()

        self.project.add_object(
            self.ui_id,
            info.type_id,
            parent_id=self.object.object_id,
            inline_property=self.property_id,
            inline_binding_expression=True
        )

        self.notify("binding-expression-id")
        self.project.history_pop()
