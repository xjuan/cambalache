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

import ast
import json
import os
import sqlite3

from gi.repository import Gio, GObject
from lxml import etree
from lxml.builder import E

from .cmb_gir_data import CmbGirData

CmbCatalogUtils = None

# Global XML name space
nsmap = {}


# Helper function to get a namespaced attribute
def ns(namespace, name):
    return f"{{{nsmap[namespace]}}}{name}"


class CmbCatalogDB:
    def __init__(self, gtk_version, dependencies=None, external_catalogs=[]):
        self.lib = None
        self.dependencies = dependencies or []
        self.gtk_version = gtk_version

        if gtk_version == 4:
            if "gtk+-3.0" in dependencies:
                print("Catalog can not target both Gtk versions, ignoring gtk+-3.0 dependency")
                self.dependencies.remove("gtk+-3.0")

            self.target_tk = "Gtk-4.0"
        elif gtk_version == 3:
            if "gtk-4.0" in dependencies:
                print("Catalog can not target both Gtk versions, ignoring gtk-4.0 dependency")
                self.dependencies.remove("gtk-4.0")

            self.target_tk = "Gtk+-3.0"

        # Create DB
        self.conn = sqlite3.connect(":memory:")

        # Load base schema
        gbytes = Gio.resources_lookup_data("/ar/xjuan/Cambalache/db/cmb_base.sql", Gio.ResourceLookupFlags.NONE)
        cmb_base = gbytes.get_data().decode("UTF-8")
        self.conn.executescript(cmb_base)
        self.conn.execute("CREATE TEMP TABLE external_property AS SELECT * FROM property LIMIT 0;")
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
            "type_internal_child",
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

        # Append Accessibility metadata for gtk 4 catalog
        if libid == "gtk" and self.lib.version == "4.0":
            element = etree.Element("accessibility-metadata")
            element.text = json.dumps(self.__a11y_get_aria_metadata(os.path.dirname(filename)), indent=2, sort_keys=True)
            catalog.append(element)
        elif libid == "gtk+" and self.lib.version == "3.0":
            element = etree.Element("accessibility-metadata")
            element.text = json.dumps(self.lib.accessibility_metadata, indent=2, sort_keys=True)
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

    def __a11y_get_aria_metadata(self, basedir):
        def get_gtk_enum_as_set(name):
            gtk_enum = self.lib.enumerations.get(name, None)
            if gtk_enum is None:
                return
            retval = {}
            for member in gtk_enum["members"].values():
                nick = member["nick"]
                retval[nick.replace("-", "")] = nick

            return retval

        gtk_roles = get_gtk_enum_as_set("GtkAccessibleRole")
        gtk_properties = get_gtk_enum_as_set("GtkAccessibleProperty")
        gtk_states = get_gtk_enum_as_set("GtkAccessibleState")

        # Download wai aria spec documentation
        wai_aria_path = os.path.join(basedir, "wai-aria.html")
        if not os.path.exists(wai_aria_path):
            import urllib.request
            response = urllib.request.urlopen("https://www.w3.org/TR/wai-aria")
            with open(wai_aria_path, "wb") as f:
                f.write(response.read())
                f.close()

        # Parse standard documentation to extract which properties can be used by role
        tree = etree.parse(wai_aria_path, etree.HTMLParser())
        root = tree.getroot()

        #
        # W3 wai aria documentation format
        #
        # <section id="role_definitions">
        #   <section id="role name">
        #     <table class="role-features">
        #       <td class="role-inherited">
        #         <ul>
        #           <li><a class="[property-reference|state-reference]" href="#aria-[property|state]">
        #
        role_definitions = root.xpath('//section[@id="role_definitions"]')
        if len(role_definitions) != 1:
            return None

        # Documentation node that contains all aria property information
        role_definitions = role_definitions[0]

        # Set of all aria properties and states
        properties = []
        states = []

        # Roles -> aria properties map
        roles = {}

        for role in role_definitions.iterchildren(tag="section"):
            role_id = role.get("id")

            # Ignore non Gtk roles
            if role_id not in gtk_roles:
                continue

            table = role.find("table")
            if table is None or table.get("class") != "role-features":
                continue

            role_properties = set()
            role_states = set()
            role_parents = set()

            # Get if role is abstract
            is_abstract = False
            role_abstract = table.xpath('tbody/tr/td[@class="role-abstract"]')
            if role_abstract:
                role_abstract = role_abstract[0]
                is_abstract = role_abstract.text and role_abstract.text.lower() == "true"

            # Get role parents
            for a in table.xpath('tbody/tr/td[@class="role-parent"]/ul/li/a[@class="role-reference"]'):
                href = a.get("href").removeprefix("#")
                # Add parent if its a Gtk role
                if href in gtk_roles:
                    role_parents.add(href)

            # Get allowed role properties and states
            for a in table.xpath('tbody/tr/td[@class="role-inherited"]/ul/li/a'):
                klass = a.get("class")
                href = a.get("href").removeprefix("#aria-")

                if klass == "property-reference" and href in gtk_properties:
                    role_properties.add(gtk_properties[href])
                elif klass == "state-reference" and href in gtk_states:
                    role_states.add(gtk_states[href])

            # Add properties set of role to list if unique and get index
            if role_properties:
                if role_properties not in properties:
                    properties.append(role_properties)
                property_index = properties.index(role_properties)
            else:
                property_index = -1

            # Add states set of role to list if unique and get index
            if role_states:
                if role_states not in states:
                    states.append(role_states)
                state_index = states.index(role_states)
            else:
                state_index = -1

            # Store just the index to the properties and states sets
            roles[gtk_roles[role_id]] = [is_abstract, sorted(list(role_parents)), property_index, state_index]

        aria_roles_gtk_roles = set(roles.keys()) - set(gtk_roles.values())
        if len(aria_roles_gtk_roles):
            print("Discrepancy between aria and gtk roles", aria_roles_gtk_roles)

        return {
            "properties": [sorted(list(p)) for p in properties],
            "states": [sorted(list(s)) for s in states],
            "roles": roles
        }

    def load_catalog_types(self, filename):
        def get_table_data_from_node(node):
            return ast.literal_eval(f"[{node.text}]") if node.text else []

        tree = etree.parse(filename)
        root = tree.getroot()

        name = root.get("name", None)
        namespace = root.get("namespace", None)
        prefix = root.get("prefix", None)

        self.lib_namespace[name] = (namespace, prefix)

        for node in root.getchildren():
            if node.tag == "property":
                # load properties in a different table
                data = get_table_data_from_node(node)
                if len(data) == 0:
                    continue

                cols = ", ".join(["?" for col in data[0]])
                self.conn.executemany(f"INSERT INTO external_property VALUES ({cols})", data)

            elif node.tag == "type":
                data = get_table_data_from_node(node)
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
        self.lib = CmbGirData(girfile, external_types=self.external_types, **kwargs, gtk_version=self.gtk_version)
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

    def _import_internal_children(self, c, node, type_id, internal_parent_id=None):
        global CmbCatalogUtils

        if node.tag != "child":
            return

        name = node.get("name", None)
        internal_type = node.get("type", None)
        creation_property_id = node.get("creation-property-id", None)

        if CmbCatalogUtils is None:
            import gi
            gi.require_version("CmbCatalogUtils", "4.0" if self.gtk_version == 4 else "3.0")
            from gi.repository import CmbCatalogUtils

        if internal_type is None:
            instance = self.lib._get_instance_from_type(type_id)

            if instance:
                internal = CmbCatalogUtils.buildable_get_internal_child(instance, name)
                internal_type = GObject.type_name(internal.__gtype__) if internal else None

        if internal_type is None:
            print("WARNING can not infer internal child type for", type_id, name)
            return

        c.execute(
            """
            INSERT INTO type_internal_child
                (type_id, internal_child_id, internal_parent_id, internal_type, creation_property_id)
            VALUES (?, ?, ?, ?, ?);
            """,
            (type_id, name, internal_parent_id, internal_type, creation_property_id),
        )

        for child in node.iterchildren("child"):
            self._import_internal_children(c, child, type_id, name)

    def get_bool(self, node, prop, default="false"):
        val = node.get(prop, default)
        return 1 if val.lower() in ["true", "yes", "1", "t", "y"] else 0

    def populate_types(self, c, types):
        def check_target(node):
            target = node.get("target", None)

            return target is not None and target != self.target_tk

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
                    type_id = prop.get("type", None)

                    if self.gtk_version == 4:
                        disable_inline_object = self.get_bool(prop, "disable-inline-object")
                    else:
                        disable_inline_object = None

                    required = self.get_bool(prop, "required")
                    workspace_default = prop.get("workspace-default", None)
                    disabled = self.get_bool(prop, "disabled")
                    original_owner_id = prop.get("original-owner-id", None)

                    if original_owner_id:
                        # Override property, copy from original and update the owner
                        for table in ["property", "external_property"]:
                            row = c.execute(
                                f"SELECT * FROM {table} WHERE owner_id=? AND property_id=?;",
                                (original_owner_id, property_id)
                            ).fetchone()

                            if row is not None:
                                break

                        if row is not None:
                            values = list(row)
                            cols = ", ".join(["?" for col in values])

                            # Override owner id
                            values[0] = owner_id
                            values[16] = original_owner_id
                            c.execute(f"INSERT INTO property VALUES ({cols});", values)

                    c.execute(
                        """
                        UPDATE property
                        SET translatable=?, save_always=?, disable_inline_object=?, required=?, workspace_default=?, disabled=?
                        WHERE owner_id=? AND property_id=?;
                        """,
                        (
                            translatable,
                            save_always,
                            disable_inline_object,
                            required,
                            workspace_default,
                            disabled,
                            owner_id,
                            property_id,
                        ),
                    )

                    # Override construct-only (NOTE: make sure we do not override default from Gir)
                    if prop.get("construct-only", None) is not None:
                        c.execute(
                            "UPDATE property SET construct_only=? WHERE owner_id=? AND property_id=?;",
                            (
                                self.get_bool(prop, "construct-only"),
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

            # Read internal children types
            for types in klass.iterchildren("internal-children"):
                if check_target(types):
                    continue
                for type in types:
                    self._import_internal_children(c, type, owner_id)

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
            """
            SELECT owner_id, property_id
            FROM property
            WHERE type_id='gchararray' AND original_owner_id IS NULL AND property_id LIKE '%icon-name%';
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
            WHERE type_id='gchararray' AND original_owner_id IS NULL AND translatable IS NULL AND
                (property_id LIKE '%title%' OR
                 property_id LIKE '%label%');
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

