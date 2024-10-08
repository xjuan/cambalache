#
# CmbCatalogDB - Data Model for cmb-catalog-gen
#
# Copyright (C) 2021-2022  Juan Pablo Ugarte
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Authors:
#   Juan Pablo Ugarte <juanpablougarte@gmail.com>
#

import os
import ast
import sqlite3


from lxml import etree
from lxml.builder import E
from .cmb_gir_data import CmbGirData
from gi.repository import Gio


# Global XML name space
nsmap = {}


# Helper function to get a namespaced attribute
def ns(namespace, name):
    return f"{{{nsmap[namespace]}}}{name}"


class CmbCatalogDB:
    def __init__(self, dependencies=None, external_catalogs=[]):
        self.lib = None
        self.dependencies = dependencies if dependencies else []

        # Create DB
        self.conn = sqlite3.connect(":memory:")

        # Load base schema
        gbytes = Gio.resources_lookup_data("/ar/xjuan/Cambalache/db/cmb_base.sql", Gio.ResourceLookupFlags.NONE)
        cmb_base = gbytes.get_data().decode("UTF-8")
        self.conn.executescript(cmb_base)
        self.conn.commit()

        self.lib_namespace = {}
        self.external_types = {}

        for catalog in external_catalogs:
            self.load_catalog_types(catalog)

    def dump(self, filename):
        # Copy/Paste from CmbDB
        def get_row(row):
            r = None

            for c in row:
                if r:
                    r += ","
                else:
                    r = ""

                if type(c) is str:
                    # FIXME: find a better way to escape string
                    val = c.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                    r += f'"{val}"'
                elif c:
                    r += str(c)
                else:
                    r += "None"

            return f"\t({r})"

        def _dump_table(c, query):
            c.execute(query)
            row = c.fetchone()

            if row is None:
                return None

            retval = ""
            while row is not None:
                retval += get_row(row)
                row = c.fetchone()

                if row:
                    retval += ",\n"

            return f"\n{retval}\n  "

        c = self.conn.cursor()

        libid = self.lib.lib
        catalog = E("cambalache-catalog", name=libid, namespace=self.lib.name, prefix=self.lib.prefix, version=self.lib.version)

        targets = []
        for row in c.execute("SELECT version FROM library_version WHERE library_id=?;", (libid,)):
            targets.append(row[0])

        if len(targets):
            catalog.set("targets", ",".join(targets))

        if self.dependencies and len(self.dependencies):
            catalog.set("depends", ",".join(self.dependencies))

        for table in [
            "type",
            "type_iface",
            "type_enum",
            "type_flags",
            "type_data",
            "type_data_arg",
            "type_child_type",
            "type_child_constraint",
            "property",
            "signal",
        ]:
            if table == "type":
                data = _dump_table(c, "SELECT * FROM type WHERE parent_id IS NOT NULL;")
            else:
                data = _dump_table(c, f"SELECT * FROM {table};")

            if data is None:
                continue

            element = etree.Element(table)
            element.text = data
            catalog.append(element)

        # Dump xml to file
        with open(filename, "wb") as fd:
            tree = etree.ElementTree(catalog)
            tree.write(
                fd,
                pretty_print=True,
                xml_declaration=True,
                encoding="UTF-8",
                standalone=False,
                doctype='<!DOCTYPE cambalache-catalog SYSTEM "cambalache-catalog.dtd">',
            )
            fd.close()

        c.close()

    def load_catalog_types(self, filename):
        tree = etree.parse(filename)
        root = tree.getroot()

        name = root.get("name", None)
        namespace = root.get("namespace", None)
        prefix = root.get("prefix", None)

        self.lib_namespace[name] = (namespace, prefix)

        for node in root.iterfind("type"):
            data = ast.literal_eval(f"[{node.text}]") if node.text else []

            if len(data) == 0:
                continue

            for row in data:
                type_id = row[0]
                library_id = row[2]

                namespace, prefix = self.lib_namespace.get(library_id, None)

                if namespace is not None and type_id.startswith(prefix):
                    nstype = type_id[len(prefix) :]
                    self.external_types[f"{namespace}.{nstype}"] = type_id

    def populate_from_gir(self, girfile, **kwargs):
        self.lib = CmbGirData(girfile, external_types=self.external_types, **kwargs)
        self.lib.populate_db(self.conn)
        self.conn.commit()

    def _import_tag(self, c, node, owner_id, parent_id):
        key = node.tag
        if node.text:
            text = node.text.strip()
            type_id = None if text == "" else text
        else:
            type_id = None

        c.execute(
            "SELECT coalesce((SELECT data_id FROM type_data WHERE owner_id=? ORDER BY data_id DESC LIMIT 1), 0) + 1;",
            (owner_id,),
        )
        data_id = c.fetchone()[0]

        translatable = None
        translatable_attr = node.get(ns("Cmb", "translatable"))

        if translatable_attr:
            translatable = type_id == "gchararray" and translatable_attr == "True"
            del node.attrib[ns("Cmb", "translatable")]

        c.execute(
            "INSERT INTO type_data (owner_id, data_id, parent_id, key, type_id, translatable) VALUES (?, ?, ?, ?, ?, ?);",
            (owner_id, data_id, parent_id, key, type_id, translatable),
        )

        for attr in node.keys():
            c.execute(
                "INSERT INTO type_data_arg (owner_id, data_id, key, type_id) VALUES (?, ?, ?, ?);",
                (owner_id, data_id, attr, node.get(attr)),
            )

        # Iterate children tags
        for child in node:
            self._import_tag(c, child, owner_id, data_id)

    def _import_type(self, c, node, type_id):
        child_type = node.text.strip()
        max_children = node.get("max-children", None)
        linked_property_id = node.get("linked-property-id", None)

        c.execute(
            "INSERT INTO type_child_type (type_id, child_type, max_children, linked_property_id) VALUES (?, ?, ?, ?);",
            (type_id, child_type, int(max_children) if max_children else None, linked_property_id),
        )

    def _import_type_constraint(self, c, node, type_id):
        child_type_id = node.text.strip()
        allowed = self.get_bool(node, "allowed", "True")
        shortcut = self.get_bool(node, "shortcut")

        c.execute(
            "INSERT INTO type_child_constraint (type_id, child_type_id, allowed, shortcut) VALUES (?, ?, ?, ?);",
            (type_id, child_type_id, allowed, shortcut),
        )

    def get_bool(self, node, prop, default="false"):
        val = node.get(prop, default)
        return 1 if val.lower() in ["true", "yes", "1", "t", "y"] else 0

    def populate_types(self, c, types):
        def check_target(node):
            target = node.get("target", None)

            return target is not None and target != self.lib.target_tk

        for klass in types:
            owner_id = klass.tag

            if check_target(klass):
                continue

            row = c.execute("SELECT type_id FROM type WHERE type_id=?;", (owner_id,)).fetchone()
            if row is None:
                continue

            abstract = klass.get("abstract", None)
            if abstract is not None:
                abstract = self.get_bool(klass, "abstract")
                c.execute("UPDATE type SET abstract=? WHERE type_id=?;", (abstract, owner_id))

            workspace_type = klass.get("workspace-type", None)
            c.execute("UPDATE type SET workspace_type=? WHERE type_id=?;", (workspace_type, owner_id))

            for properties in klass.iterchildren("properties"):
                if check_target(properties):
                    continue

                for prop in properties:
                    property_id = prop.get("id", None)
                    if property_id is None:
                        continue

                    translatable = self.get_bool(prop, "translatable")
                    save_always = self.get_bool(prop, "save-always")
                    is_position = self.get_bool(prop, "is-position")
                    type_id = prop.get("type", None)

                    if self.lib.target_tk == "Gtk-4.0":
                        disable_inline_object = self.get_bool(prop, "disable-inline-object")
                    else:
                        disable_inline_object = None

                    required = self.get_bool(prop, "required")
                    workspace_default = prop.get("workspace-default", None)

                    c.execute(
                        """
                        UPDATE property
                        SET translatable=?, save_always=?, disable_inline_object=?, is_position=?, required=?,
                            workspace_default=?
                        WHERE owner_id=? AND property_id=?;
                        """,
                        (
                            translatable,
                            save_always,
                            disable_inline_object,
                            is_position,
                            required,
                            workspace_default,
                            owner_id,
                            property_id,
                        ),
                    )

                    # Force a different type (For Icon names stock ids etc)
                    if type_id:
                        c.execute(
                            "UPDATE property SET type_id=? WHERE owner_id=? AND property_id=?;",
                            (type_id, owner_id, property_id),
                        )

            # Read type custom tags
            for data in klass.iterchildren("data"):
                if check_target(data):
                    continue

                for child in data:
                    self._import_tag(c, child, owner_id, None)

            # Read children types
            for types in klass.iterchildren("children-types"):
                if check_target(types):
                    continue
                for type in types:
                    self._import_type(c, type, owner_id)

            # Read children constraints
            for constraints in klass.iterchildren("children-constraints"):
                if check_target(constraints):
                    continue
                for constraint in constraints:
                    self._import_type_constraint(c, constraint, owner_id)

    def populate_categories(self, c, categories):
        for category in categories:
            name = category.get("name")

            for klass in category:
                c.execute("UPDATE type SET category=? WHERE type_id=?;", (name, klass.tag))

    def populate_extra_data_from_xml(self, filename):
        if not os.path.exists(filename):
            return

        tree = etree.parse(filename)
        root = tree.getroot()

        global nsmap
        nsmap = root.nsmap

        c = self.conn.cursor()

        for node in root:
            if node.tag == "types":
                self.populate_types(c, node)
            elif node.tag == "categories":
                self.populate_categories(c, node)

        c.close()
        self.conn.commit()

    def get_ignored_named_icons(self):
        retval = {}
        n = 0
        c = self.conn.cursor()

        for row in c.execute(
            "SELECT owner_id, property_id FROM property WHERE type_id='gchararray' AND property_id LIKE '%icon-name%';"
        ):
            owner_id, property_id = row

            ids = retval.get(owner_id, None)
            if ids is None:
                ids = []
                retval[owner_id] = ids

            ids.append(property_id)
            n += 1

        c.close()

        return retval if n else None

    def get_position_layout_properties(self):
        retval = {}
        n = 0
        c = self.conn.cursor()

        for row in c.execute(
            """
            SELECT p.owner_id, p.property_id
            FROM property AS p, type AS t
            WHERE p.owner_id=t.type_id AND
                t.layout='child' AND
                p.type_id='gint' AND
                p.is_position IN (NULL, 0) AND
                p.property_id LIKE '%position%';
            """
        ):
            owner_id, property_id = row

            ids = retval.get(owner_id, None)
            if ids is None:
                ids = []
                retval[owner_id] = ids

            ids.append(property_id)
            n += 1

        c.close()

        return retval if n else None

    def get_possibly_translatable_properties(self):
        retval = {}
        n = 0
        c = self.conn.cursor()

        for row in c.execute(
            """
            SELECT owner_id, property_id
            FROM property
            WHERE type_id='gchararray' AND property_id LIKE '%title%' AND translatable IS NULL;
            """
        ):
            owner_id, property_id = row

            ids = retval.get(owner_id, None)
            if ids is None:
                ids = []
                retval[owner_id] = ids

            ids.append(property_id)
            n += 1

        c.close()

        return retval if n else None

    def get_property_overrides(self):
        retval = {}
        for name in self.lib.sorted_types:
            if name not in self.lib.types:
                continue
            data = self.lib.types[name]
            overrides = data.get("overrides", None)

            if overrides:
                retval[name] = overrides

        return retval if len(retval) else None



