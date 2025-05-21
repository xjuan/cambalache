#
# Cambalache Type Info wrapper
#
# Copyright (C) 2021-2022  Juan Pablo Ugarte
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

from .cmb_objects_base import (
    CmbBaseTypeInfo,
    CmbBaseTypeDataInfo,
    CmbBaseTypeDataArgInfo,
    CmbBaseTypeInternalChildInfo,
    CmbTypeChildInfo,
    CmbSignalInfo,
)
from .cmb_property_info import CmbPropertyInfo

from .constants import EXTERNAL_TYPE, GMENU_TYPE, GMENU_SECTION_TYPE, GMENU_SUBMENU_TYPE, GMENU_ITEM_TYPE

from cambalache import getLogger

logger = getLogger(__name__)


class CmbTypeDataArgInfo(CmbBaseTypeDataArgInfo):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __str__(self):
        return f"CmbTypeDataArgInfo<{self.owner_id}>::{self.key}"


class CmbTypeDataInfo(CmbBaseTypeDataInfo):
    def __init__(self, **kwargs):
        self.args = {}
        self.children = {}
        super().__init__(**kwargs)

    def __str__(self):
        return f"CmbTypeDataArgInfo<{self.owner_id}>::{self.key}"


class CmbTypeInternalChildInfo(CmbBaseTypeInternalChildInfo):
    def __init__(self, **kwargs):
        self.children = {}
        super().__init__(**kwargs)

    def __str__(self):
        return f"CmbTypeInternalChildInfo<{self.type_id}>::{self.internal_child_id}"


class CmbTypeInfo(CmbBaseTypeInfo):
    __gtype_name__ = "CmbTypeInfo"

    type_id = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    parent_id = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    parent = GObject.Property(type=GObject.Object, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.project is None:
            return

        self.hierarchy = self.__init_hierarchy()
        self.interfaces = self.__init_interfaces()
        self.properties = self.__init_properties_signals(CmbPropertyInfo, "property")
        self.signals = self.__init_properties_signals(CmbSignalInfo, "signal")
        self.data = self.__init_data()
        self.internal_children = self.__init_internal_children()
        self.child_constraint, self.child_type_shortcuts = self.__init_child_constraint()

        if self.parent_id == "enum":
            self.enum = self.__init_enum_flags("enum")
        elif self.parent_id == "flags":
            self.flags = self.__init_enum_flags("flags")

        self.child_types = self.__init_child_type()

        self.is_object = self.is_a("GObject")

        self.instantiable = self.is_object and not self.abstract

        self.is_menu_builtin = self.type_id in [GMENU_TYPE, GMENU_SECTION_TYPE, GMENU_SUBMENU_TYPE, GMENU_ITEM_TYPE]
        self.is_builtin = self.is_menu_builtin or self.type_id in [EXTERNAL_TYPE]

    def __str__(self):
        return f"CmbTypeInfo<{self.type_id}>"

    def __init_hierarchy(self):
        retval = []

        c = self.project.db.cursor()
        for row in c.execute(
            """
            WITH RECURSIVE ancestor(type_id, generation, parent_id) AS (
                SELECT type_id, 1, parent_id
                FROM type
                WHERE parent_id IS NOT NULL AND
                      parent_id != 'interface' AND
                      parent_id != 'enum' AND
                      parent_id != 'flags' AND
                      type_id=?
                UNION ALL
                SELECT ancestor.type_id, generation + 1, type.parent_id
                FROM type JOIN ancestor ON type.type_id = ancestor.parent_id
                WHERE type.parent_id IS NOT NULL AND type.parent_id != 'object' AND ancestor.type_id=?
            )
            SELECT parent_id, generation FROM ancestor
            UNION
            SELECT type_iface.iface_id, 0
            FROM ancestor JOIN type_iface
            WHERE ancestor.type_id = type_iface.type_id
            ORDER BY generation;
            """,
            (self.type_id, self.type_id),
        ):
            retval.append(row[0])

        c.close()

        return retval

    def __init_interfaces(self):
        retval = []

        c = self.project.db.cursor()
        for row in c.execute("SELECT iface_id FROM type_iface WHERE type_id=? ORDER BY iface_id;", (self.type_id,)):
            retval.append(row[0])

        c.close()
        return retval

    def __init_properties_signals(self, Klass, table):
        retval = {}

        c = self.project.db.cursor()
        for row in c.execute(f"SELECT * FROM {table} WHERE owner_id=? ORDER BY {table}_id;", (self.type_id,)):
            retval[row[1]] = Klass.from_row(self.project, *row)

        c.close()
        return retval

    def __type_get_data(self, owner_id, data_id, parent_id, key, type_id, translatable):
        args = {}
        children = {}
        parent_id = parent_id if parent_id is not None else 0
        retval = CmbTypeDataInfo.from_row(self.project, owner_id, data_id, parent_id, key, type_id, translatable)

        c = self.project.db.cursor()

        # Collect Arguments
        for row in c.execute("SELECT * FROM type_data_arg WHERE owner_id=? AND data_id=?;", (owner_id, data_id)):
            _key = row[2]
            args[_key] = CmbTypeDataArgInfo.from_row(self.project, *row)

        # Recurse children
        for row in c.execute("SELECT * FROM type_data WHERE owner_id=? AND parent_id=?;", (owner_id, data_id)):
            _key = row[3]
            children[_key] = self.__type_get_data(*row)

        c.close()

        retval.args = args
        retval.children = children

        return retval

    def __init_data(self):
        retval = {}

        c = self.project.db.cursor()
        for row in c.execute(
            "SELECT * FROM type_data WHERE parent_id IS NULL AND owner_id=? ORDER BY data_id;", (self.type_id,)
        ):
            key = row[3]
            retval[key] = self.__type_get_data(*row)

        c.close()
        return retval

    def __type_get_internal_child(self, type_id, internal_child_id, internal_parent_id, internal_type, creation_property_id):
        retval = CmbTypeInternalChildInfo.from_row(
            self.project,
            type_id,
            internal_child_id,
            internal_parent_id,
            internal_type,
            creation_property_id
        )
        children = {}

        c = self.project.db.cursor()

        # Recurse children
        for row in c.execute(
            "SELECT * FROM type_internal_child WHERE type_id=? AND internal_parent_id=?;",
            (type_id, internal_child_id)
        ):
            key = row[1]
            children[key] = self.__type_get_internal_child(*row)

        c.close()

        retval.children = children

        # Internal child back reference in property
        if creation_property_id:
            if creation_property_id in self.properties:
                self.properties[creation_property_id].internal_child = retval

        return retval

    def __init_internal_children(self):
        retval = {}

        c = self.project.db.cursor()
        for row in c.execute(
            "SELECT * FROM type_internal_child WHERE type_id=? AND internal_parent_id IS NULL ORDER BY internal_child_id;",
            (self.type_id,)
        ):
            key = row[1]
            retval[key] = self.__type_get_internal_child(*row)

        c.close()
        return retval

    def __init_child_constraint(self):
        retval = {}
        shortcuts = []

        c = self.project.db.cursor()
        for row in c.execute(
            "SELECT child_type_id, allowed, shortcut FROM type_child_constraint WHERE type_id=?;", (self.type_id,)
        ):
            child_type_id, allowed, shortcut = row
            retval[child_type_id] = allowed
            if shortcut:
                shortcuts.append(child_type_id)

        c.close()
        return retval, shortcuts

    def __init_child_type(self):
        retval = {}

        c = self.project.db.cursor()
        for row in c.execute("SELECT * FROM type_child_type WHERE type_id=?;", (self.type_id,)):
            type_id, child_type, max_children, linked_property_id = row
            retval[child_type] = CmbTypeChildInfo(
                project=self.project,
                type_id=type_id,
                child_type=child_type,
                max_children=max_children if max_children else 0,
                linked_property_id=linked_property_id,
            )

        c.close()
        return retval

    def __init_enum_flags(self, name):
        retval = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_INT)

        c = self.project.db.cursor()
        for row in c.execute(f"SELECT name, nick, value FROM type_{name} WHERE type_id=? ORDER BY nick;", (self.type_id,)):
            retval.append(row)

        c.close()
        return retval

    def is_a(self, type_id):
        return self.type_id == type_id or type_id in self.hierarchy

    def get_data_info(self, name):
        parent = self
        while parent:
            if name in parent.data:
                return parent.data[name]

            parent = parent.parent

        return None

    def find_data_info(self, data_id):
        def find_child_info(info, data_id):
            for name in info.children:
                child_info = info.children[name]
                if child_info.data_id == data_id:
                    return child_info

                retval = find_child_info(child_info, data_id)
                if retval:
                    return retval

        for name in self.data:
            info = self.data[name]
            if info.data_id == data_id:
                return info

            retval = find_child_info(info, data_id)
            if retval:
                return retval

        return None

    def has_child_types(self):
        parent = self
        while parent:
            if parent.child_types:
                return True
            parent = parent.parent

        return False

    def enum_get_value_as_string(self, value, use_nick=True):
        if self.parent_id != "enum":
            return None

        for row in self.enum:
            enum_name, enum_nick, enum_value = row

            # Always use nick as value
            if value == enum_name or value == enum_nick or value == str(enum_value):
                return enum_nick if use_nick else enum_value

        return None

    def flags_get_value_as_string(self, value):
        if self.parent_id != "flags":
            return None

        value_type = type(value)
        tokens = None

        if value_type == str:
            if value.isnumeric():
                value = int(value)
                value_type = int
            else:
                tokens = [t.strip() for t in value.split("|")]
        elif value_type != int:
            logger.warning(f"Unhandled value type {value_type} {value}")
            return None

        flags = []

        for row in self.flags:
            flag_name, flag_nick, flag_value = row

            if value_type == str:
                # Always use nick as value
                if flag_name in tokens or flag_nick in tokens:
                    flags.append(flag_nick)
            else:
                if flag_value & value:
                    flags.append(flag_nick)

        return "|".join(flags)
