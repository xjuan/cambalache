#
# CmbDB - Cambalache DataBase
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

import os
import sys
import sqlite3
import ast
import json

from lxml import etree
from lxml.builder import E
from graphlib import TopologicalSorter, CycleError
from gi.repository import GLib, Gio, GObject
from cambalache import config, getLogger, _
from . import cmb_db_migration, utils
from .constants import EXTERNAL_TYPE, GMENU_TYPE, GMENU_SECTION_TYPE, GMENU_SUBMENU_TYPE, GMENU_ITEM_TYPE
from .cmb_db_profile import CmbProfileConnection

logger = getLogger(__name__)


def _get_text_resource(name):
    gbytes = Gio.resources_lookup_data(f"/ar/xjuan/Cambalache/{name}", Gio.ResourceLookupFlags.NONE)
    return gbytes.get_data().decode("UTF-8")


BASE_SQL = _get_text_resource("db/cmb_base.sql")
PROJECT_SQL = _get_text_resource("db/cmb_project.sql")
HISTORY_SQL = _get_text_resource("db/cmb_history.sql")


class CmbDB(GObject.GObject):
    __gtype_name__ = "CmbDB"

    target_tk = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        self.version = self.__parse_version(config.FILE_FORMAT_VERSION)
        self.accessibility_metadata = {}

        self.type_info = None
        self.__accessible_info = None

        self.__db_filename = None

        self.__tables = [
            "ui",
            "ui_library",
            "css",
            "css_ui",
            "gresource",
            "object",
            "object_property",
            "object_layout_property",
            "object_signal",
            "object_data",
            "object_data_arg",
        ]

        self.__history_commands = {}
        self.__table_column_mapping = {}

        self.clipboard = []
        self.clipboard_ids = []

        self.conn = self.__sqlite_connect(":memory:")

        super().__init__(**kwargs)

        c = self.conn.cursor()
        self.foreign_keys = True

        # Create type system tables
        c.executescript(BASE_SQL)

        # Create project tables
        c.executescript(PROJECT_SQL)

        self.conn.commit()
        c.close()

        # Initialize history (Undo/Redo) tables
        self.__init_dynamic_tables()
        self.__init_data()

    def __del__(self):
        self.conn.commit()
        self.conn.close()

    @GObject.Property(type=bool, default=True)
    def foreign_keys(self):
        self.conn.commit()
        c = self.conn.execute("PRAGMA foreign_keys;")
        fk = c.fetchone()[0]
        c.close()
        return fk

    @foreign_keys.setter
    def _set_foreign_keys(self, value):
        fk = "ON" if value else "OFF"
        self.conn.commit()
        self.conn.execute(f"PRAGMA foreign_keys={fk};")

    @GObject.Property(type=bool, default=False)
    def ignore_check_constraints(self):
        self.conn.commit()
        c = self.conn.execute("PRAGMA ignore_check_constraints;")
        fk = c.fetchone()[0]
        c.close()
        return fk

    @ignore_check_constraints.setter
    def _set_ignore_check_constraints(self, value):
        val = "ON" if value else "OFF"
        self.conn.commit()
        self.conn.execute(f"PRAGMA ignore_check_constraints={val};")
        self.conn.execute("PRAGMA quick_check;")

    def __sqlite_connect(self, path):
        debug_var = os.environ.get("CAMBALACHE_DEBUG", None)
        if debug_var == "db-profile" :
            conn = sqlite3.connect(path, factory=CmbProfileConnection)
        else:
            conn = sqlite3.connect(path)

        conn.create_collation("version", sqlite_version_cmp)
        conn.create_aggregate("MAX_VERSION", 1, MaxVersion)
        conn.create_aggregate("MIN_VERSION", 1, MinVersion)
        conn.create_function("CMB_PRINT", 1, cmb_print)
        conn.create_function("cmb_object_list_remove", 2, cmb_object_list_remove)

        return conn

    def history_insert(self, table, new_values):
        self.execute(self.__history_commands[table]["INSERT"], new_values)

    def history_delete(self, table, table_pk):
        self.execute(self.__history_commands[table]["DELETE"], table_pk)

    def history_update(self, table, columns, table_pk, values):
        update_command = self.__history_commands[table]["UPDATE"]
        set_expression = f"({','.join(columns)}) = ({','.join(['?' for i in columns])})"

        exp_vals = []
        for col in columns:
            exp_vals.append(values[self.__table_column_mapping[table][col]])

        self.execute(update_command.format(set_expression=set_expression), exp_vals + table_pk)

    def __create_history_triggers(self, c, table):
        # Get table columns
        columns = None
        old_values = None
        new_values = None

        all_columns = []
        pk_columns = []
        non_pk_columns = []

        # Use this flag to know if we should log history or not
        history_is_enabled = "(SELECT value FROM global WHERE key='history_enabled') IS TRUE"
        history_seq = "(SELECT MAX(history_id) FROM history)"
        history_next_seq = f"(coalesce({history_seq}, 0) + 1)"
        clear_history = """
            DELETE FROM history
            WHERE (SELECT value FROM global WHERE key='history_index') >= 0 AND
                history_id > (SELECT value FROM global WHERE key='history_index');
            UPDATE global SET value=-1 WHERE key='history_index' AND value >= 0
            """
        self.__clear_history = clear_history

        # Collect Column info
        i = 0
        column_mapping = {}
        for row in c.execute(f"PRAGMA table_info({table});"):
            col = row[1]
            pk = row[5]

            column_mapping[col] = i
            all_columns.append(col)
            if pk:
                pk_columns.append(col)
            else:
                non_pk_columns.append(col)

            i += 1

        # Collect unique constraint indexes
        unique_constraints_indexes = []
        for row in c.execute(f"PRAGMA index_list({table});"):
            n, name, is_unique, index_type, is_partial = row
            if is_unique and index_type == "u":
                unique_constraints_indexes.append(name)

        # Collect unique constraints indexes with more than one non pk column
        unique_constraints = []
        for index_name in unique_constraints_indexes:
            index_columns = []

            for row in c.execute(f"PRAGMA index_info({index_name});"):
                index_rank, table_rank, name = row
                if name not in pk_columns:
                    index_columns.append(name)

            if len(index_columns) > 1:
                unique_constraints.append(index_columns)

        unique_constraints_flat = [i for constraints in unique_constraints for i in constraints]

        # Map column index to column name
        self.__table_column_mapping[table] = column_mapping

        columns = ", ".join(all_columns)
        columns_format = ", ".join(["?" for col in all_columns])
        pkcolumns = ", ".join(pk_columns)
        pkcolumns_format = ", ".join(["?" for col in pk_columns])
        new_pk_values = ", ".join([f"NEW.{c}" for c in pk_columns])
        old_pk_values = ", ".join([f"OLD.{c}" for c in pk_columns])
        old_values = ", ".join([f"OLD.{c}" for c in all_columns])
        new_values = ", ".join([f"NEW.{c}" for c in all_columns])

        self.__history_commands[table] = {
            "DELETE": f"DELETE FROM {table} WHERE ({pkcolumns}) IS ({pkcolumns_format});",
            "INSERT": f"INSERT INTO {table} ({columns}) VALUES ({columns_format});",
            "UPDATE": f"UPDATE {table} SET {{set_expression}} WHERE ({pkcolumns}) IS ({pkcolumns_format});",
        }

        # INSERT Trigger
        c.execute(
            f"""
            CREATE TRIGGER on_{table}_insert AFTER INSERT ON {table}
            WHEN
              {history_is_enabled}
            BEGIN
              {clear_history};
              INSERT INTO history (history_id, command, table_name, table_pk, new_values)
              VALUES ({history_next_seq}, 'INSERT', '{table}', json_array({new_pk_values}), json_array({new_values}));
            END;
            """
        )

        # DELETE trigger
        c.execute(
            f"""
            CREATE TRIGGER on_{table}_delete AFTER DELETE ON {table}
            WHEN
              {history_is_enabled}
            BEGIN
              {clear_history};
              INSERT INTO history (history_id, command, table_name, table_pk, old_values)
              VALUES ({history_next_seq}, 'DELETE', '{table}', json_array({old_pk_values}), json_array({old_values}));
            END;
            """
        )

        if len(pk_columns) == 0:
            return

        # UPDATE Trigger for each non PK column unique indexes
        for columns in unique_constraints:
            underscore_columns = "_".join(columns)
            colon_columns = ",".join(columns)
            new_columns = ",".join(f"NEW.{col}" for col in columns)
            old_columns = ",".join(f"OLD.{col}" for col in columns)
            string_columns = ",".join(f"'{col}'" for col in columns)

            c.execute(
                f"""
                CREATE TRIGGER on_{table}_update_{underscore_columns} AFTER UPDATE OF {colon_columns} ON {table}
                WHEN
                  ({new_columns}) IS NOT ({old_columns}) AND {history_is_enabled} AND
                  (
                    (SELECT table_pk FROM history WHERE history_id = {history_seq}) IS NOT json_array({old_pk_values})
                    OR
                    (
                      (SELECT command, table_name, columns FROM history WHERE history_id = {history_seq})
                      IS NOT ('UPDATE', '{table}', json_array({string_columns}))
                      AND
                      (SELECT command, table_name, columns FROM history WHERE history_id = {history_seq})
                      IS NOT ('INSERT', '{table}',  NULL)
                    )
                  )
                BEGIN
                  {clear_history};
                  INSERT INTO history (history_id, command, table_name, columns, table_pk, new_values, old_values)
                    VALUES ({history_next_seq}, 'UPDATE', '{table}', json_array({string_columns}), json_array({new_pk_values}), json_array({new_values}), json_array({old_values}));
                END;
                """
            )

        # UPDATE Trigger for each non PK column
        for column in non_pk_columns:
            if column in unique_constraints_flat:
                continue

            c.execute(
                f"""
                CREATE TRIGGER on_{table}_update_{column} AFTER UPDATE OF {column} ON {table}
                WHEN
                  NEW.{column} IS NOT OLD.{column} AND {history_is_enabled} AND
                  (
                    (SELECT table_pk FROM history WHERE history_id = {history_seq}) IS NOT json_array({old_pk_values})
                    OR
                    (
                      (SELECT command, table_name, columns FROM history WHERE history_id = {history_seq})
                      IS NOT ('UPDATE', '{table}', json_array('{column}'))
                      AND
                      (SELECT command, table_name, columns FROM history WHERE history_id = {history_seq})
                      IS NOT ('INSERT', '{table}',  NULL)
                    )
                  )
                BEGIN
                  {clear_history};
                  INSERT INTO history (history_id, command, table_name, columns, table_pk, new_values, old_values)
                    VALUES ({history_next_seq}, 'UPDATE', '{table}', json_array('{column}'), json_array({new_pk_values}), json_array({new_values}), json_array({old_values}));
                END;
                """
            )

            c.execute(
                f"""
                CREATE TRIGGER on_{table}_update_{column}_compress_update AFTER UPDATE OF {column} ON {table}
                WHEN
                  NEW.{column} IS NOT OLD.{column} AND {history_is_enabled} AND
                  (SELECT table_pk FROM history WHERE history_id = {history_seq}) IS json_array({old_pk_values})
                  AND
                  (SELECT command, table_name, columns FROM history WHERE history_id = {history_seq})
                  IS ('UPDATE', '{table}', json_array('{column}'))
                BEGIN
                  UPDATE history SET new_values=json_array({new_values}) WHERE history_id = {history_seq};
                END;
                """
            )

            c.execute(
                f"""
                CREATE TRIGGER on_{table}_update_{column}_compress_insert AFTER UPDATE OF {column} ON {table}
                WHEN
                  NEW.{column} IS NOT OLD.{column} AND {history_is_enabled} AND
                  (SELECT table_pk FROM history WHERE history_id = {history_seq}) IS json_array({old_pk_values})
                  AND
                  (SELECT command, table_name, columns FROM history WHERE history_id = {history_seq})
                  IS ('INSERT', '{table}', NULL)
                BEGIN
                  UPDATE history SET new_values=json_array({new_values}) WHERE history_id = {history_seq};
                END;
                """
            )

    def __init_dynamic_tables(self):
        c = self.conn.cursor()

        # Create history main tables
        c.executescript(HISTORY_SQL)

        # Create history tables for each tracked table
        for table in self.__tables:
            self.__create_history_triggers(c, table)

        self.conn.commit()
        c.close()

    def __init_builtin_types(self):
        # Add special type for external object references. See gtk_builder_expose_object()
        self.execute(
            "INSERT INTO type (type_id, parent_id, library_id) VALUES (?, 'object', ?);",
            (EXTERNAL_TYPE, "gtk" if self.target_tk == "gtk-4.0" else "gtk+")
        )

        # Add GMenu related types
        for gtype, category in [
            (GMENU_TYPE, "model"),
            (GMENU_SECTION_TYPE, "hidden"),
            (GMENU_SUBMENU_TYPE, "hidden"),
            (GMENU_ITEM_TYPE, "hidden"),
        ]:
            self.execute(
                "INSERT INTO type (type_id, parent_id, library_id, category) VALUES (?, 'GObject', 'gio', ?);",
                (gtype, category),
            )

        # menu is a GMenuModel
        self.execute("INSERT INTO type_iface (type_id, iface_id) VALUES (?, ?);", (GMENU_TYPE, "GMenuModel"))

        # Add properties
        for values in [
            (GMENU_SECTION_TYPE, "label", "gchararray", True),
            (GMENU_SUBMENU_TYPE, "label", "gchararray", True),
            (GMENU_ITEM_TYPE, "target", "gchararray", False),
            (GMENU_ITEM_TYPE, "label", "gchararray", True),
            (GMENU_ITEM_TYPE, "action", "gchararray", False),
            (GMENU_ITEM_TYPE, "action-namespace", "gchararray", False),
            (GMENU_ITEM_TYPE, "icon", "CmbIconName", False),
        ]:
            self.execute("INSERT INTO property (owner_id, property_id, type_id, translatable) VALUES (?, ?, ?, ?);", values)

        # Add constraints
        for gtype in [GMENU_TYPE, GMENU_SECTION_TYPE, GMENU_SUBMENU_TYPE]:
            for child_type in [GMENU_SECTION_TYPE, GMENU_SUBMENU_TYPE, GMENU_ITEM_TYPE]:
                self.execute("INSERT INTO type_child_constraint VALUES (?, ?, 1, 1);", (gtype, child_type))

        for gtype in [GMENU_SECTION_TYPE, GMENU_SUBMENU_TYPE, GMENU_ITEM_TYPE]:
            self.execute(
                """
                INSERT INTO type_data
                VALUES
                (?, 3, null, 'attributes', null, null),
                (?, 4, null, 'links', null, null),
                (?, 1, 3, 'attribute', 'gchararray', True),
                (?, 2, 4, 'link', null, null);
                """,
                (gtype, gtype, gtype, gtype),
            )

            self.execute(
                """
                INSERT INTO type_data_arg (owner_id, data_id, key, type_id)
                VALUES
                (?, 1, 'name', 'gchararray'),
                (?, 1, 'type', 'gchararray'),
                (?, 2, 'id', 'gchararray'),
                (?, 2, 'name', 'gchararray');
                """,
                (gtype, gtype, gtype, gtype),
            )

    def __init_data(self):
        supported_targets = {"gtk+-3.0", "gtk-4.0"}

        if self.target_tk not in supported_targets:
            raise Exception(f"Unknown target toolkit {self.target_tk}")

        exclude_catalogs = {"gdk-3.0", "gtk+-3.0"} if self.target_tk == "gtk-4.0" else {"gdk-4.0", "gsk-4.0", "gtk-4.0"}

        # Dictionary of catalog XML trees
        catalogs_tree = {}

        # Catalog dependencies
        catalog_graph = {}

        catalog_dirs = [os.path.join(dir, "cambalache", "catalogs") for dir in GLib.get_system_data_dirs()]

        # Prepend package data dir
        if config.catalogsdir not in catalog_dirs:
            catalog_dirs.insert(0, config.catalogsdir)

        # Append user catalog dir
        user_catalogs = os.path.join(GLib.get_home_dir(), ".cambalache", "catalogs")
        if user_catalogs not in catalog_dirs:
            catalog_dirs.append(user_catalogs)

        # Collect and parse all catalogs in all system data directories
        for catalogs_dir in catalog_dirs:
            if not os.path.exists(catalogs_dir) or not os.path.isdir(catalogs_dir):
                continue

            # Collect and parse all catalogs in directory
            for catalog in os.listdir(catalogs_dir):
                catalog_path = os.path.join(catalogs_dir, catalog)
                if os.path.isdir(catalog_path):
                    continue

                content_type = utils.content_type_guess(catalog_path)

                if content_type != "application/xml":
                    continue

                tree = etree.parse(catalog_path)

                if tree.docinfo.doctype != "<!DOCTYPE cambalache-catalog SYSTEM \"cambalache-catalog.dtd\">":
                    continue

                root = tree.getroot()
                name = root.get("name", None)
                version = root.get("version", None)
                dependecies = root.get("depends", None)
                name_version = f"{name}-{version}"

                if name_version in catalog_graph:
                    continue

                catalogs_tree[name_version] = (tree, catalog_path)

                # Ignore different gtk catalog from target_tk
                if name_version in exclude_catalogs:
                    continue

                depends = set()
                if dependecies is not None:
                    for dependency in dependecies.split(","):
                        # Ignore catalogs that depends on the wrong gtk version
                        if dependency in exclude_catalogs:
                            exclude_catalogs.add(name_version)
                            depends = None
                            break
                        depends.add(dependency)

                if depends is not None:
                    catalog_graph[name_version] = depends

        if self.target_tk not in catalog_graph:
            raise Exception(f"Could not find {self.target_tk} catalog")

        try:
            ts = TopologicalSorter(catalog_graph)
            sorted_catalogs = tuple(ts.static_order())
        except CycleError as e:
            raise Exception(f"Could not load catalogs because of dependency cycle {e}")

        # Load catalogs in topological order
        for name_version in sorted_catalogs:
            # Ignore edges not in the root list
            if name_version not in catalog_graph:
                continue

            deps = catalog_graph[name_version]

            # Check all dependencies for it are available
            for dep in deps:
                if dep not in catalog_graph:
                    deps = None
                    break

            # Ignore catalogs with not all deps
            if deps is None:
                continue

            # Load catalog
            tree, path = catalogs_tree.get(name_version, (None, None))
            if tree:
                self.load_catalog_from_tree(tree, path)

        # Add builtins, (menu depends on gio)
        self.__init_builtin_types()

    @staticmethod
    def get_target_from_file(filename):
        def get_target_from_line(line, tag):
            if not line.endswith("/>"):
                line = line + f"</{tag}>"

            root = etree.fromstring(line)
            return root.get("target_tk", None)

        retval = None
        try:
            f = open(filename, "r")
            for line in f:
                line = line.strip()

                # FIXME: find a robust way of doing this without parsing the
                # whole file
                if line.startswith("<cambalache-project"):
                    retval = get_target_from_line(line, "cambalache-project")
                    break
                elif line.startswith("<project"):
                    retval = get_target_from_line(line, "project")
                    break
            f.close()
        except Exception:
            pass

        return retval

    def get_data(self, key):
        c = self.execute("SELECT value FROM global WHERE key=?;", (key,))
        row = c.fetchone()
        c.close()
        return row[0] if row is not None else None

    def set_data(self, key, value):
        self.execute("UPDATE global SET value=? WHERE key=?;", (value, key))

    def get_toplevels(self, ui_id):
        retval = []
        for row in self.execute("SELECT object_id FROM object WHERE ui_id=? AND parent_id IS NULL;", (ui_id,)):
            retval.append(row[0])

        return retval

    def __parse_version(self, version):
        if version is None:
            return (0, 0, 0)

        return utils.parse_version(version)

    def __ensure_table_data_columns(self, version, table, data):
        if version is None:
            return data

        if version < (0, 7, 5):
            data = cmb_db_migration.ensure_columns_for_0_7_5(table, data)

        if version < (0, 9, 0):
            data = cmb_db_migration.ensure_columns_for_0_9_0(table, data)

        if version < (0, 11, 2):
            data = cmb_db_migration.ensure_columns_for_0_11_2(table, data)

        if version < (0, 11, 4):
            data = cmb_db_migration.ensure_columns_for_0_11_4(table, data)

        if version < (0, 13, 1):
            data = cmb_db_migration.ensure_columns_for_0_13_1(table, data)

        if version < (0, 17, 3):
            data = cmb_db_migration.ensure_columns_for_0_17_3(table, data)

        return data

    def __migrate_table_data(self, c, version, table, data):
        if version is None:
            return

        if version < (0, 7, 5):
            cmb_db_migration.migrate_table_data_to_0_7_5(c, table, data)

        if version < (0, 9, 0):
            cmb_db_migration.migrate_table_data_to_0_9_0(c, table, data)

        if version < (0, 17, 3):
            cmb_db_migration.migrate_table_data_to_0_17_3(c, table, data)

        if version < (0, 91, 3):
            cmb_db_migration.migrate_table_data_to_0_91_3(c, table, data)

    def __load_table_from_tuples(self, c, table, tuples, version=None):
        data = ast.literal_eval(f"[{tuples}]") if tuples else []
        if len(data) == 0:
            return

        # version is None for catalog tables
        if version is None or self.version == version:
            cols = ", ".join(["?" for col in data[0]])
            c.executemany(f"INSERT INTO {table} VALUES ({cols})", data)
            return

        # Ensure table data has the right amount of columns
        data = self.__ensure_table_data_columns(version, table, data)
        cols = ", ".join(["?" for col in data[0]])

        # Create temp table without any constraints
        c.execute(f"CREATE TEMP TABLE {table} AS SELECT * FROM {table} LIMIT 0;")

        # Load table data
        c.executemany(f"INSERT INTO temp.{table} VALUES ({cols})", data)

        # Migrate data to current format
        self.__migrate_table_data(c, version, table, data)

        # Copy data from temp table
        c.execute(f"INSERT INTO main.{table} SELECT * FROM temp.{table};")

        # Drop temp table
        c.execute(f"DROP TABLE temp.{table};")

    def load_old_format(self, root, version):
        c = self.conn.cursor()

        # Avoid circular dependencies errors
        self.foreign_keys = False
        self.ignore_check_constraints = True

        # Support old format
        all_tables = self.__tables + ["property", "signal"]
        for child in root.getchildren():
            if child.tag in all_tables:
                self.__load_table_from_tuples(c, child.tag, child.text, version)
            else:
                raise Exception(f"Unknown tag {child.tag} in project file.")

        self.foreign_keys = True
        self.ignore_check_constraints = False

        c.close()

    def __load_accessibility_metadata(self, node):
        data = json.loads(node.text)

        if self.target_tk == "gtk-4.0":
            metadata = {}

            properties = data.get("properties", None)
            states = data.get("states", None)
            roles = data.get("roles", None)

            for role_id, role_data in roles.items():
                is_abstract, parents, property_index, status_index = role_data

                metadata[role_id] = {
                    "is_abstract": is_abstract,
                    "properties": properties[property_index],
                    "states": states[status_index],

                }
        else:
            metadata = data

        self.accessibility_metadata = metadata

    def load_catalog_from_tree(self, tree, filename):
        root = tree.getroot()

        logger.debug(f"Loading catalog: {filename}")

        name = root.get("name", None)
        version = root.get("version", None)
        namespace = root.get("namespace", None)
        prefix = root.get("prefix", None)
        targets = root.get("targets", "")

        c = self.conn.cursor()

        # Insert library
        c.execute(
            "INSERT INTO library(library_id, version, namespace, prefix) VALUES (?, ?, ?, ?);",
            (name, version, namespace, prefix),
        )

        # Insert target versions
        for target in targets.split(","):
            c.execute("INSERT INTO library_version(library_id, version) VALUES (?, ?);", (name, target))

        # Get dependencies
        deps = {}
        for dep in root.get("depends", "").split(","):
            tokens = dep.split("-")
            if len(tokens) == 2:
                lib, ver = tokens
                deps[lib] = ver

        c = self.conn.cursor()

        # Load dependencies
        for dep in deps:
            c.execute("SELECT version FROM library WHERE library_id=?;", (dep,))
            row = c.fetchone()
            if row and row[0] == deps[dep]:
                continue
            else:
                logger.warning(f"Missing dependency {dep} for {filename}")
                deps.pop(dep)

        # Insert dependencies
        for dep in deps:
            try:
                c.execute("INSERT INTO library_dependency(library_id, dependency_id) VALUES (?, ?);", (name, dep))
            except Exception as e:
                logger.warning(e)
                # TODO: should we try to load the module?
                # pass

        # Avoid circular dependencies errors
        self.foreign_keys = False

        for child in root.getchildren():
            if child.tag == "accessibility-metadata":
                self.__load_accessibility_metadata(child)
            else:
                self.__load_table_from_tuples(c, child.tag, child.text)

        self.foreign_keys = True
        c.close()

        self.commit()

    def move_to_fs(self, filename):
        self.conn.commit()

        if self.__db_filename == filename:
            return

        # Open new location
        conn = self.__sqlite_connect(filename)

        self.__db_filename = filename

        # Dump to file
        with conn:
            self.conn.backup(conn)

        # Close current connection
        self.conn.close()

        # Update current connection
        self.conn = conn

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        return self.conn.commit()

    def execute(self, *args):
        return self.conn.execute(*args)

    def executescript(self, *args):
        return self.conn.executescript(*args)

    def add_ui(self, name, filename, requirements={}, domain=None, comment=None):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO ui (name, filename, translation_domain, comment) VALUES (?, ?, ?, ?);",
            (name, filename, domain, comment)
        )
        ui_id = c.lastrowid

        for key in requirements:
            req = requirements[key]
            c.execute(
                "INSERT INTO ui_library (ui_id, library_id, version, comment) VALUES (?, ?, ?, ?);",
                (ui_id, key, req["version"], req["comment"]),
            )
        c.close()

        return ui_id

    def add_css(self, filename=None, priority=None, is_global=None):
        c = self.conn.cursor()

        c.execute("INSERT INTO css (filename, priority, is_global) VALUES (?, ?, ?);", (filename, priority, is_global))
        ui_id = c.lastrowid
        c.close()

        return ui_id

    def add_gresource(
        self,
        resource_type,
        parent_id=None,
        gresources_filename=None,
        gresource_prefix=None,
        file_filename=None,
        file_compressed=None,
        file_preprocess=None,
        file_alias=None
    ):
        if resource_type not in ["gresources", "gresource", "file"]:
            return

        c = self.conn.cursor()

        if resource_type == "gresources":
            c.execute("SELECT count(gresource_id) FROM gresource WHERE parent_id IS NULL;")
        else:
            c.execute("SELECT count(gresource_id) FROM gresource WHERE parent_id=?;", (parent_id, ))
        position = c.fetchone()[0]

        c.execute(
            """
            INSERT INTO gresource (
                resource_type,
                parent_id,
                position,
                gresources_filename,
                gresource_prefix,
                file_filename,
                file_compressed,
                file_preprocess,
                file_alias
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                resource_type,
                parent_id,
                position,
                gresources_filename,
                gresource_prefix,
                file_filename,
                file_compressed,
                file_preprocess,
                file_alias
            )
        )
        gresource_id = c.lastrowid
        c.close()

        return gresource_id

    def __add_internal_child(self, ui_id, object_id, child):
        child_id = self.execute("SELECT coalesce(MAX(object_id), 0) + 1 FROM object WHERE ui_id=?;", (ui_id,)).fetchone()[0]
        position = self.execute(
            "SELECT coalesce(MAX(position), -1) + 1 FROM object WHERE ui_id=? AND parent_id=?;",
            (ui_id, object_id)
        ).fetchone()[0]

        self.execute(
            "INSERT INTO object (ui_id, object_id, type_id, parent_id, internal, position) VALUES (?, ?, ?, ?, ?, ?);",
            (ui_id, child_id, child.internal_type, object_id, child.internal_child_id, position),
        )

        for internal_child_id, internal_child in child.children.items():
            self.__add_internal_child(ui_id, child_id, internal_child)

    def add_object(
        self,
        ui_id,
        obj_type,
        name=None,
        parent_id=None,
        internal_child=None,
        child_type=None,
        comment=None,
        layout=None,
        position=None,
        inline_property=None,
    ):
        c = self.conn.cursor()

        # Get new object id
        object_id = c.execute("SELECT coalesce(MAX(object_id), 0) + 1 FROM object WHERE ui_id=?;", (ui_id,)).fetchone()[0]

        # Check if position is already in use and ensure it wont raise an unique constraint error
        if position is not None and position > 0:
            row = c.execute(
                "SELECT object_id FROM object WHERE ui_id=? AND parent_id=? AND position=?;",
                (ui_id, parent_id, position)
            ).fetchone()

            if row is not None:
                position = None

        # Get position if not provided
        if position is None or position < 0:
            if parent_id is None:
                c.execute("SELECT coalesce(MAX(position), -1) + 1 FROM object WHERE ui_id=? AND parent_id IS NULL;", (ui_id, ))
            else:
                c.execute(
                    "SELECT coalesce(MAX(position), -1) + 1 FROM object WHERE ui_id=? AND parent_id=?;",
                    (ui_id, parent_id)
                )
            position = c.fetchone()[0]

        # Insert new object
        c.execute(
            """
            INSERT INTO object (ui_id, object_id, type_id, name, parent_id, internal, type, comment, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (ui_id, object_id, obj_type, name, parent_id, internal_child, child_type, comment, position),
        )

        # Automatically add internal children
        info = self.type_info.get(obj_type, None)
        for internal_child_id, child in info.internal_children.items():
            self.__add_internal_child(ui_id, object_id, child)

        # Get parent type for later
        if layout or inline_property:
            c.execute("SELECT type_id FROM object WHERE ui_id=? AND object_id=?;", (ui_id, parent_id))
            row = c.fetchone()
            parent_type = row[0] if row else None
        else:
            parent_type = None

        if layout and parent_type:
            for property_id in layout:
                owner_id = self.__get_layout_property_owner(parent_type, property_id)
                c.execute(
                    """
                    INSERT INTO object_layout_property (ui_id, object_id, child_id, owner_id, property_id, value)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (ui_id, parent_id, object_id, owner_id, property_id, layout[property_id]),
                )

        if parent_id and parent_type and inline_property:
            info = self.type_info.get(parent_type, None)
            pinfo = self.__get_property_info(info, inline_property)

            c.execute(
                "SELECT count(object_id) FROM object_property WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;",
                (ui_id, parent_id, pinfo.owner_id, inline_property),
            )
            count = c.fetchone()[0]

            if count:
                c.execute(
                    """
                    UPDATE object_property SET inline_object_id=?
                    WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id;
                    """,
                    (object_id, ui_id, parent_id, pinfo.owner_id, inline_property),
                )
            else:
                c.execute(
                    """
                    INSERT INTO object_property (ui_id, object_id, owner_id, property_id, inline_object_id)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (ui_id, parent_id, pinfo.owner_id, inline_property, object_id),
                )

        c.close()

        return object_id

    def __collect_error(self, error, node, name):
        # Ensure error object
        if error not in self.errors:
            self.errors[error] = {}

        errors = self.errors[error]

        # Ensure list
        if name not in errors:
            errors[name] = []

        # Add unknown tag occurrence
        errors[name].append(node.sourceline)

    def __unknown_tag(self, node, owner, name):
        if node.tag is etree.Comment:
            return

        self.__collect_error("unknown-tag", node, f"{owner}:{name}" if owner is not None and name else name)

    def __node_get(self, node, *args, collect_errors=True):
        errors = [] if collect_errors else None
        retval = utils.xml_node_get(node, *args, errors=errors)

        if errors:
            for error, node, attr in errors:
                self.__collect_error(error, node, attr)

        return retval

    def __get_property_info(self, info, property_id):
        pinfo = None

        # Find owner type for property
        if property_id in info.properties:
            pinfo = info.properties[property_id]
        else:
            # Search in interfaces properties
            for iface in info.interfaces:
                iface_info = self.type_info[iface]

                if property_id in iface_info.properties:
                    pinfo = iface_info.properties[property_id]
                    break

            for parent in info.hierarchy:
                type_info = self.type_info[parent]

                # Search in parent properties
                if property_id in type_info.properties:
                    pinfo = type_info.properties[property_id]

                # Search in parent interfaces properties
                for iface in type_info.interfaces:
                    iface_info = self.type_info[iface]

                    if property_id in iface_info.properties:
                        pinfo = iface_info.properties[property_id]
                        break

                if pinfo is not None:
                    break

        return pinfo

    def __import_property(self, c, info, ui_id, object_id, prop, object_id_map=None):
        name, translatable, context, comments, bind_source_id, bind_property_id, bind_flags = self.__node_get(
            prop, "name", ["translatable:bool", "context", "comments", "bind-source", "bind-property", "bind-flags"]
        )

        property_id = name.replace("_", "-")
        pinfo = self.__get_property_info(info, property_id)

        if pinfo is None:
            self.__collect_error("unknown-property", prop, f"{info.type_id}:{property_id}")
            return

        # Property value
        value = prop.text

        # Initialize to null
        inline_object_id = None

        # GtkBuilder in Gtk4 supports defining an object in a property
        obj_node = prop.find("object")
        if self.target_tk == "gtk-4.0" and pinfo.is_object and obj_node is not None:
            if pinfo.disable_inline_object:
                self.__collect_error("not-inline-object", prop, f"{info.type_id}:{property_id}")
                return

            inline_object_id = self.__import_object(ui_id, obj_node, object_id)
            value = None

        self.__upsert_object_property(
            c,
            info,
            pinfo,
            ui_id,
            object_id,
            prop,
            property_id,
            value,
            object_id_map=object_id_map,
            translatable=translatable,
            context=context,
            comments=comments,
            bind_source_id=bind_source_id,
            bind_property_id=bind_property_id,
            bind_flags=bind_flags,
            inline_object_id=inline_object_id
        )

    def __upsert_object_property(
        self,
        c,
        info,
        pinfo,
        ui_id,
        object_id,
        prop,
        property_id,
        value,
        object_id_map=None,
        translatable=None,
        context=None,
        comments=None,
        bind_source_id=None,
        bind_property_id=None,
        bind_flags=None,
        inline_object_id=None
    ):
        comment = self.__node_get_comment(prop)

        # Need to remap object ids on paste
        if object_id_map and pinfo.is_object:
            value = object_id_map.get(value, value)

        tinfo = self.type_info.get(pinfo.type_id, None)
        if tinfo:
            # Use nick for enum and flags
            if tinfo.parent_id == "enum":
                value = tinfo.enum_get_value_as_string(value)
            elif tinfo.parent_id == "flags":
                value = tinfo.flags_get_value_as_string(value)

        try:
            c.execute(
                """
                INSERT OR REPLACE INTO object_property
                  (ui_id, object_id, owner_id, property_id, value, translatable, comment, translation_context,
                   translation_comments, inline_object_id, bind_source_id, bind_property_id, bind_flags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ui_id,
                    object_id,
                    pinfo.owner_id,
                    property_id,
                    value,
                    translatable,
                    comment,
                    context,
                    comments,
                    inline_object_id,
                    bind_source_id,
                    bind_property_id,
                    bind_flags,
                ),
            )
        except Exception as e:
            raise Exception(
                f"XML:{prop.sourceline} - Can not import object {object_id} {pinfo.owner_id}:{property_id} property: {e}"
            )

    def __import_a11y_property(self, c, info, ui_id, object_id, prop, object_id_map=None, a11y_prefix=None):
        # Property value
        value = prop.text
        translatable = None
        context = None
        comments = None

        if self.target_tk == "gtk+-3.0":
            if prop.tag == 'property':
                name, translatable, context, comments = self.__node_get(
                    prop, "name", ["translatable:bool", "context", "comments"]
                )
                name = name.removeprefix("AtkObject::").removeprefix("accessible-")
            elif prop.tag == 'action':
                name, translatable, context, comments = self.__node_get(
                    prop, "action_name", ["translatable:bool", "context", "comments"]
                )
            elif prop.tag == 'relation':
                name, value = self.__node_get(prop, "type", "target")
        else:
            name, translatable, context, comments = self.__node_get(prop, "name", ["translatable:bool", "context", "comments"])

        # Accessibility properties are prefixed with cmb-a11y-{tag} to avoid name clashes
        property_id = name.replace("_", "-")
        property_id = f"cmb-a11y-{prop.tag}-{property_id}"

        pinfo = self.__get_property_info(info, property_id)

        if not pinfo:
            self.__collect_error("unknown-property", prop, f"{info.type_id}:{property_id}")
            return

        if pinfo.type_id == "CmbAccessibleList":
            # Check if this a11y list has already a value
            row = c.execute(
                "SELECT value FROM object_property WHERE ui_id=? AND object_id=? AND owner_id=? AND property_id=?;",
                (
                    ui_id,
                    object_id,
                    pinfo.owner_id,
                    property_id,
                ),
            ).fetchone()

            # if so, then append the value instead of replacing
            # FIXME: use object_id_map
            if row is not None:
                value = f"{row[0]},{value}"

        self.__upsert_object_property(
            c,
            info,
            pinfo,
            ui_id,
            object_id,
            prop,
            property_id,
            value,
            object_id_map=object_id_map,
            translatable=translatable,
            context=context,
            comments=comments
        )

    def __import_signal(self, c, info, ui_id, object_id, signal, object_id_map=None):
        (
            name,
            handler,
            user_data,
            swap,
            after,
        ) = self.__node_get(signal, "name", ["handler", "object", "swapped:bool", "after:bool"])

        tokens = name.split("::")

        if len(tokens) > 1:
            signal_id = tokens[0]
            detail = tokens[1]
        else:
            signal_id = tokens[0]
            detail = None

        comment = self.__node_get_comment(signal)

        owner_id = None

        # Find owner type for signal
        if signal_id in info.signals:
            owner_id = info.type_id
        else:
            for parent in info.hierarchy:
                pinfo = self.type_info[parent]
                if signal_id in pinfo.signals:
                    owner_id = parent
                    break

        # Need to remap object ids on paste
        if object_id_map and user_data:
            user_data = object_id_map.get(user_data, user_data)

        # If object/user_data is set then swapped is by default on
        if user_data and signal.get("swapped", None) is None:
            # Force swapped to true when there is an object
            swap = True

        # Insert signal
        if not owner_id:
            self.__collect_error("unknown-signal", signal, f"{info.type_id}:{signal_id}")
            return

        try:
            c.execute(
                """
                INSERT INTO object_signal
                  (ui_id, object_id, owner_id, signal_id, handler, detail, user_data, swap, after, comment)
                VALUES (?, ?, ?, ?, ?, ?, (SELECT object_id FROM object WHERE ui_id=? AND name=?), ?, ?, ?);
                """,
                (ui_id, object_id, owner_id, signal_id, handler, detail, ui_id, user_data, swap, after, comment),
            )
        except Exception as e:
            raise Exception(f"XML:{signal.sourceline} - Can not import object {object_id} {owner_id}:{signal_id} signal: {e}")

    def __import_child(self, c, info, ui_id, parent_id, child, object_id_map=None):
        ctype, internal = self.__node_get(child, ["type", "internal-child"])
        object_id = None
        packing = None

        custom_fragments = []

        for node in child.iterchildren():
            if node.tag == "object":
                object_id = self.__import_object(ui_id, node, parent_id, internal, ctype, object_id_map=object_id_map)
            elif node.tag == "packing" and self.target_tk == "gtk+-3.0":
                # Gtk 3, packing props are sibling to <object>
                packing = node
            elif node.tag == "placeholder":
                # Ignore placeholder tags
                pass
            elif node.tag is etree.Comment:
                pass
            else:
                custom_fragments.append(node)

        if packing is not None and object_id:
            self.__import_layout_properties(c, info, ui_id, parent_id, object_id, packing)

        fragment = self.__custom_fragments_tostring(custom_fragments)
        if fragment and object_id is not None:
            c.execute("UPDATE object SET custom_child_fragment=? WHERE ui_id=? AND object_id=?", (fragment, ui_id, object_id))

    def __get_layout_property_owner(self, type_id, property_id):
        info = self.type_info.get(type_id, None)

        if info is None:
            return None

        # Walk type hierarchy until we find the Layout child property
        while info:
            owner = self.type_info.get(f"{info.type_id}LayoutChild", None)

            if owner and owner.properties.get(property_id, None) is not None:
                return owner.type_id

            info = info.parent

        return None

    def __import_layout_properties(self, c, info, ui_id, parent_id, object_id, layout):
        c.execute("SELECT type_id FROM object WHERE ui_id=? AND object_id=?;", (ui_id, parent_id))
        parent_type = c.fetchone()

        if parent_type is None:
            return

        for prop in layout.iterchildren():
            if prop.tag != "property":
                self.__unknown_tag(prop, parent_id, prop.tag)
                continue

            name, translatable, context, comments = self.__node_get(prop, "name", ["translatable:bool", "context", "comments"])
            property_id = name.replace("_", "-")
            comment = self.__node_get_comment(prop)
            owner_id = self.__get_layout_property_owner(parent_type[0], property_id)
            owner_info = self.type_info.get(owner_id, None)

            if owner_info:
                pinfo = owner_info.properties.get(property_id, None)

                # Update object position if this layout property is_position
                if pinfo and pinfo.is_position:
                    try:
                        c.execute("UPDATE object SET position=? WHERE ui_id=? AND object_id=?;", (prop.text, ui_id, object_id))
                    except Exception:
                        # Ignore duplicated positions
                        pass
                    continue

            try:
                c.execute(
                    """
                    INSERT INTO object_layout_property (ui_id, object_id, child_id, owner_id, property_id, value, translatable,
                      comment, translation_context, translation_comments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        ui_id,
                        parent_id,
                        object_id,
                        owner_id,
                        property_id,
                        prop.text,
                        translatable,
                        comment,
                        context,
                        comments,
                    ),
                )
            except Exception as e:
                raise Exception(
                    f"XML:{prop.sourceline} - Can not import object {object_id} {owner_id}:{property_id} layout property: {e}"
                )

    def object_add_data(
        self,
        ui_id,
        object_id,
        owner_id,
        data_id,
        value=None,
        parent_id=None,
        comment=None,
        translatable=None,
        context=None,
        comments=None,
    ):
        c = self.conn.cursor()

        c.execute(
            """
            SELECT coalesce((SELECT id FROM object_data
            WHERE ui_id=? AND object_id=? AND owner_id=?
            ORDER BY id DESC LIMIT 1), 0) + 1;
            """,
            (ui_id, object_id, owner_id),
        )
        id = c.fetchone()[0]

        c.execute(
            """
            INSERT INTO object_data (
                ui_id, object_id, owner_id, data_id, id, value, parent_id, comment,
                translatable, translation_context, translation_comments
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (ui_id, object_id, owner_id, data_id, id, value, parent_id, comment, translatable, context, comments),
        )
        c.close()

        return id

    def object_add_data_arg(self, ui_id, object_id, owner_id, data_id, id, key, val):
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO object_data_arg (ui_id, object_id, owner_id, data_id, id, key, value) VALUES (?, ?, ?, ?, ?, ?, ?);",
            (ui_id, object_id, owner_id, data_id, id, key, val),
        )
        c.close()

    def __import_object_data(self, ui_id, object_id, owner_id, taginfo, ntag, parent_id):
        c = self.conn.cursor()

        data_id = taginfo.data_id
        text = ntag.text.strip() if ntag.text else None
        value = text if text and len(text) > 0 else None
        comment = self.__node_get_comment(ntag)

        if taginfo.translatable:
            # Do not collect errors since they are all optionals
            translatable, context, comments = self.__node_get(
                ntag,
                ["translatable:bool", "context", "comments"],
                collect_errors=False
            )
        else:
            translatable, context, comments = (None, None, None)

        id = self.object_add_data(
            ui_id, object_id, owner_id, data_id, value, parent_id, comment, translatable, context, comments
        )

        for key in taginfo.args:
            val = ntag.get(key, None)
            self.object_add_data_arg(ui_id, object_id, owner_id, data_id, id, key, val)

        for child in ntag.iterchildren():
            if child.tag in taginfo.children:
                self.__import_object_data(ui_id, object_id, owner_id, taginfo.children[child.tag], child, id)
            else:
                self.__unknown_tag(child, owner_id, child.tag)

        c.close()

    def __import_menu(self, ui_id, node, parent_id, object_id_map=None):
        (name,) = self.__node_get(node, ["id"])
        comment = self.__node_get_comment(node)

        tag = node.tag

        if tag == "menu":
            klass = GMENU_TYPE
        elif tag == "submenu":
            klass = GMENU_SUBMENU_TYPE
        elif tag == "section":
            klass = GMENU_SECTION_TYPE
        elif tag == "item":
            klass = GMENU_ITEM_TYPE
        else:
            self.__collect_error("unknown-tag", node, tag)
            return

        info = self.type_info.get(klass, None)

        if not info:
            logger.warning(f"Error importing menu: {klass} not found")
            return

        # Need to remap object ids on paste
        if object_id_map:
            name = object_id_map.get(name, name)

        # Insert menu
        try:
            menu_id = self.add_object(ui_id, klass, name, parent_id, None, None, comment)
        except Exception:
            logger.warning(f"XML:{node.sourceline} - Error importing menu")
            return

        c = self.conn.cursor()

        attributes_info = info.get_data_info("attributes")
        attributes_id = None
        links_info = info.get_data_info("links")
        links_id = None

        for child in node.iterchildren():
            if child.tag in ["submenu", "section", "item"]:
                self.__import_menu(ui_id, child, menu_id, object_id_map=object_id_map)
            elif child.tag == "attribute":
                if klass == GMENU_TYPE:
                    logger.warning(f"XML:{node.sourceline} - Ignoring attribute")
                    continue

                property_id = child.get("name")
                pinfo = self.__get_property_info(info, property_id)
                if pinfo:
                    self.__import_property(c, info, ui_id, menu_id, child, object_id_map=object_id_map)
                else:
                    if attributes_id is None:
                        attributes_id = self.object_add_data(
                            ui_id, menu_id, info.type_id, attributes_info.data_id, None, None, None
                        )

                    # This is a custom attribute, store as object data
                    taginfo = attributes_info.children["attribute"]
                    self.__import_object_data(ui_id, menu_id, taginfo.owner_id, taginfo, child, attributes_id)
            elif child.tag == "link":
                if links_id is None:
                    links_id = self.object_add_data(ui_id, menu_id, info.type_id, links_info.data_id, None, None, None)

                taginfo = attributes_info.children["links"]
                self.__import_object_data(ui_id, menu_id, taginfo.owner_id, taginfo, child, links_id)
            else:
                self.__collect_error("unknown-tag", node, child.tag)

        c.close()

        return menu_id

    def __import_accessibility(self, c, ui_id, object_id, node, object_id_map=None):
        is_gtk3 = self.target_tk == "gtk+-3.0"

        if self.__accessible_info is None:
            # Accessibility iface type info
            self.__accessible_info = {
                "property": self.type_info.get("CmbAccessibleProperty"),
                "relation": self.type_info.get("CmbAccessibleRelation")
            }
            if is_gtk3:
                self.__accessible_info["action"] = self.type_info.get("CmbAccessibleAction")
            else:
                self.__accessible_info["state"] = self.type_info.get("CmbAccessibleState")

        if is_gtk3:
            a11y_tags = ["property", "relation", "action"]
        else:
            a11y_tags = ["property", "relation", "state"]

        for child in node.iterchildren():
            if child.tag in a11y_tags:
                info = self.__accessible_info.get(child.tag, None)
                self.__import_a11y_property(c, info, ui_id, object_id, child, object_id_map=object_id_map)
            else:
                self.__collect_error("unknown-tag", node, child.tag)

    def __import_object(
        self, ui_id, node, parent_id, internal_child=None, child_type=None, is_template=False, object_id_map=None
    ):
        custom_fragments = []

        if node.tag == "menu":
            return self.__import_menu(ui_id, node, parent_id, object_id_map=object_id_map)

        is_template = node.tag == "template"

        if is_template:
            klass, name = self.__node_get(node, "parent", "class")
        else:
            klass, name = self.__node_get(node, "class", ["id"])

        comment = self.__node_get_comment(node)
        info = self.type_info.get(klass, None)

        if not info:
            self.__collect_error("unknown-type", node, klass)
            return

        # Accessibility properties for gtk 3
        if self.target_tk == "gtk+-3.0" and internal_child == "accessible" and klass == "AtkObject":
            c = self.conn.cursor()
            self.__import_accessibility(c, ui_id, parent_id, node, object_id_map=object_id_map)
            c.close()
            return

        # Need to remap object ids on paste
        if object_id_map:
            name = object_id_map.get(name, name)

        # Insert object
        try:
            object_id = self.add_object(ui_id, klass, name, parent_id, internal_child, child_type, comment)
        except Exception as e:
            logger.warning(f"XML:{node.sourceline} - Error importing {klass} {e}")
            return

        c = self.conn.cursor()

        if is_template:
            c.execute("UPDATE ui SET template_id=? WHERE ui_id=?", (object_id, ui_id))

        def find_data_info(info, tag):
            if tag in info.data:
                return info

            for parent in info.hierarchy:
                pinfo = self.type_info[parent]

                if tag in pinfo.data:
                    return pinfo

        for child in node.iterchildren():
            if child.tag == "property":
                self.__import_property(c, info, ui_id, object_id, child, object_id_map=object_id_map)
            elif child.tag == "signal":
                self.__import_signal(c, info, ui_id, object_id, child, object_id_map=object_id_map)
            elif child.tag == "child":
                self.__import_child(c, info, ui_id, object_id, child, object_id_map=object_id_map)
            elif child.tag == "layout" and self.target_tk == "gtk-4.0":
                # Gtk 4, layout props are children of <object>
                self.__import_layout_properties(c, info, ui_id, parent_id, object_id, child)
            elif child.tag == "accessibility":
                if info.is_a("GtkWidget"):
                    self.__import_accessibility(c, ui_id, object_id, child, object_id_map=object_id_map)
                else:
                    self.__collect_error("unknown-tag", node, child.tag)
            elif child.tag is etree.Comment:
                pass
            else:
                # Custom buildable tags
                taginfo = info.get_data_info(child.tag)

                if taginfo is not None:
                    self.__import_object_data(ui_id, object_id, taginfo.owner_id, taginfo, child, None)
                else:
                    custom_fragments.append(child)

        fragment = self.__custom_fragments_tostring(custom_fragments)
        if fragment:
            c.execute("UPDATE object SET custom_fragment=? WHERE ui_id=? AND object_id=?", (fragment, ui_id, object_id))

        c.close()

        return object_id

    def __custom_fragments_tostring(self, custom_fragments):
        if len(custom_fragments) == 0:
            return None

        fragment = ""

        for node in custom_fragments:
            fragment += etree.tostring(node).decode("utf-8").strip()

        return fragment

    def __node_get_comment(self, node):
        prev = node.getprevious()
        if prev is not None and prev.tag is etree.Comment:
            return prev.text if not prev.text.strip().startswith("interface-") else None
        return None

    def __node_get_requirements(self, root):
        retval = {}

        # Collect requirements and comments
        for req in root.iterfind("requires"):
            lib, version = self.__node_get(req, "lib", "version")

            retval[lib] = {"version": version, "comment": self.__node_get_comment(req)}

        return retval

    @staticmethod
    def _get_target_from_node(root):
        if root.tag != "interface":
            return (None, None, None)

        # Look for explicit gtk version first
        for req in root.iterfind("requires"):
            lib = req.get("lib", None)
            version = req.get("version", "")

            if lib == "gtk" and version.startswith("4."):
                return (lib, "4.0", False)
            elif lib == "gtk+" and version.startswith("3."):
                return (lib, "3.0", False)

        # Infer target by looking for exclusive tags
        for element in root.iter():
            if (
                element.tag in ["layout", "binding", "lookup"]
                or element.tag == "object"
                and element.get("class", "").startswith("Adw")
            ):
                return ("gtk", "4.0", True)

            if element.tag in ["packing"] or element.tag == "object" and element.get("class", "").startswith("Hdy"):
                return ("gtk+", "3.0", True)

        return (None, None, None)

    def __fix_object_references(self, ui_id, fix_externals=True):
        # Find all object references to external objects
        if fix_externals:
            for row in self.conn.execute(
                """
                SELECT DISTINCT op.value
                FROM object_property AS op, property AS p
                WHERE op.value IS NOT NULL AND op.ui_id=? AND p.is_object AND
                      op.owner_id = p.owner_id AND op.property_id = p.property_id
                EXCEPT
                SELECT name FROM object WHERE name IS NOT NULL;
                """,
                (ui_id,),
            ):
                # And create an object for each one so that references to external objects work
                self.add_object(ui_id, EXTERNAL_TYPE, name=row[0])

        # Fix properties value that refer to an object
        self.conn.execute(
            """
            UPDATE object_property AS op SET value=o.object_id
            FROM property AS p, object AS o
            WHERE op.ui_id=? AND p.is_object AND op.owner_id = p.owner_id AND
                  op.property_id = p.property_id AND o.ui_id = op.ui_id AND
                  o.name = op.value;
            """,
            (ui_id,),
        )

        # Fix bind source and set bind owner to the object type
        self.conn.execute(
            """
            UPDATE object_property AS op
            SET bind_source_id=o.object_id, bind_owner_id=o.type_id
            FROM object AS o
            WHERE op.ui_id=? AND bind_source_id IS NOT NULL AND o.ui_id = op.ui_id AND o.name = op.bind_source_id;
            """,
            (ui_id,),
        )

        # Fix a11y CmbAccessibleList references
        for row in self.conn.execute(
            """
            SELECT op.object_id, op.property_id, op.value
            FROM object_property AS op, property AS p
            WHERE
                op.owner_id=p.owner_id AND op.property_id=p.property_id AND
                op.ui_id=? AND p.type_id = 'CmbAccessibleList' AND
                op.value IS NOT NULL;
            """,
            (ui_id, )
        ):
            object_id, property_id, value = row

            ids = []

            for name in value.split(","):
                r = self.conn.execute("SELECT object_id FROM object WHERE ui_id=? AND name=?", (ui_id, name.strip())).fetchone()
                if r:
                    ids.append(str(r[0]))

            self.conn.execute(
                "UPDATE object_property SET value=? WHERE ui_id=? AND object_id=? AND property_id=?",
                (",".join(ids), ui_id, object_id, property_id)
            )

        # Fix bind owner (Owner needs to point to the right parent class)
        self.conn.execute(
            """
            WITH RECURSIVE ancestor(type_id, generation, parent_id) AS (
              SELECT type_id, 1, parent_id FROM type
                WHERE parent_id IS NOT NULL AND
                      parent_id != 'interface' AND
                      parent_id != 'enum' AND
                      parent_id != 'flags'
              UNION ALL
              SELECT ancestor.type_id, generation + 1, type.parent_id
                FROM type JOIN ancestor ON type.type_id = ancestor.parent_id
                WHERE type.parent_id IS NOT NULL
            )
            UPDATE object_property AS op
            SET bind_owner_id=p.owner_id
            FROM property AS p, ancestor AS a
            WHERE op.ui_id=? AND
                op.bind_owner_id IS NOT NULL AND
                op.bind_property_id = p.property_id AND
                op.bind_owner_id = a.type_id AND
                p.owner_id = a.parent_id
            """,
            (ui_id,),
        )

        # Fix data references to objects
        self.conn.execute(
            """
            WITH RECURSIVE ancestor(type_id, generation, parent_id) AS (
              SELECT type_id, 1, parent_id FROM type
                WHERE parent_id IS NOT NULL AND
                      parent_id != 'enum' AND
                      parent_id != 'flags'
              UNION ALL
              SELECT ancestor.type_id, generation + 1, type.parent_id
                FROM type JOIN ancestor ON type.type_id = ancestor.parent_id
                WHERE type.parent_id IS NOT NULL
            )
            UPDATE object_data AS od SET value=o.object_id
            FROM object AS o, type_data AS td, type AS t, ancestor AS a
            WHERE
                od.ui_id=? AND od.ui_id=o.ui_id AND od.value=o.name AND
                od.owner_id=td.owner_id AND od.data_id=td.data_id AND
                td.type_id=t.type_id AND
                t.type_id=a.type_id AND a.generation=1 AND a.parent_id IN ('GObject', 'interface')
            """,
            (ui_id,),
        )

        # Fix data arg references to objects
        self.conn.execute(
            """
            WITH RECURSIVE ancestor(type_id, generation, parent_id) AS (
              SELECT type_id, 1, parent_id FROM type
                WHERE parent_id IS NOT NULL AND
                      parent_id != 'enum' AND
                      parent_id != 'flags'
              UNION ALL
              SELECT ancestor.type_id, generation + 1, type.parent_id
                FROM type JOIN ancestor ON type.type_id = ancestor.parent_id
                WHERE type.parent_id IS NOT NULL
            )
            UPDATE object_data_arg AS oda SET value=o.object_id
            FROM object AS o, type_data_arg AS tda, type AS t, ancestor AS a
            WHERE
                oda.ui_id=? AND oda.ui_id=o.ui_id AND oda.value=o.name AND
                oda.owner_id=tda.owner_id AND oda.data_id=tda.data_id AND oda.key=tda.key AND
                tda.type_id=t.type_id AND
                t.type_id=a.type_id AND a.generation=1 AND a.parent_id IN ('GObject', 'interface')
            """,
            (ui_id,),
        )

    def import_from_node(self, root, relpath):
        custom_fragments = []
        self.foreign_keys = False

        # Clear parsing errors
        self.errors = {}

        if root.tag != "interface":
            raise Exception(_("Unknown root tag {tag}").format(tag=root.tag))

        requirements = self.__node_get_requirements(root)

        target_tk = self.target_tk
        lib, ver, inferred = CmbDB._get_target_from_node(root)

        if lib is not None and ((target_tk == "gtk-4.0" and lib != "gtk") or (target_tk == "gtk+-3.0" and lib != "gtk+")):
            # Translators: This text will be used in the next two string as {convert}
            convert = _("\nUse gtk4-builder-tool first to convert file.") if target_tk == "gtk-4.0" else ""

            if inferred:
                # Translators: {convert} will be replaced with the gtk4-builder-tool string
                raise Exception(
                    _("Can not import what looks like a {lib}-{ver} file in a {target_tk} project.{convert}").format(
                        lib=lib, ver=ver, target_tk=target_tk, convert=convert
                    )
                )
            else:
                # Translators: {convert} will be replaced with the gtk4-builder-tool string
                raise Exception(
                    _("Can not import a {lib}-{ver} file in a {target_tk} project.{convert}").format(
                        lib=lib, ver=ver, target_tk=target_tk, convert=convert
                    )
                )

        c = self.conn.cursor()

        # Update interface comment
        comment = self.__node_get_comment(root)
        if comment and comment.strip().startswith("Created with Cambalache"):
            comment = None

        # Make sure there is no attributes in root tag other than domain
        domain, = self.__node_get(root, ["domain"])

        basename = os.path.basename(relpath) if relpath else None
        ui_id = self.add_ui(basename, relpath, requirements, domain, comment)

        # These values come from Glade
        license_map = {
            "other": "custom",
            "gplv2": "gpl_2_0",
            "gplv3": "gpl_3_0",
            "lgplv2": "lgpl_2_1",
            "lgplv3": "lgpl_3_0",
            "bsd2c": "bsd",
            "bsd3c": "bsd_3",
            "apache2": "apache_2_0",
            "mit": "mit_x11",
        }

        # XML key <-> table column
        interface_key_map = {
            "interface-license-id": "license_id",
            "interface-name": "name",
            "interface-description": "description",
            "interface-copyright": "copyright",
            "interface-authors": "authors",
        }

        # Import objects
        for child in root.iterchildren():
            if child.tag == "object":
                self.__import_object(ui_id, child, None)
            elif child.tag == "template":
                self.__import_object(ui_id, child, None)
            elif child.tag == "menu":
                self.__import_menu(ui_id, child, None)
            elif child.tag == "requires":
                pass
            elif child.tag is etree.Comment:
                comment = etree.tostring(child).decode("utf-8").strip()
                comment = comment.removeprefix("<!--").removesuffix("-->").strip()

                # Import interface data from Glade comments
                if comment.startswith("interface-"):
                    key, value = comment.split(" ", 1)
                    if key == "interface-license-type":
                        license = license_map.get(value, "unknown")
                        c.execute("UPDATE ui SET license_id=? WHERE ui_id=?", (license, ui_id))
                    else:
                        column = interface_key_map.get(key, None)
                        if column is not None:
                            c.execute(f"UPDATE ui SET {column}=? WHERE ui_id=?", (value, ui_id))
            else:
                custom_fragments.append(child)

            main_loop = GLib.MainContext.default()
            while main_loop.pending():
                main_loop.iteration(False)

        # Fix object references!
        self.__fix_object_references(ui_id)

        fragment = self.__custom_fragments_tostring(custom_fragments)
        if fragment:
            c.execute("UPDATE ui SET custom_fragment=? WHERE ui_id=?", (fragment, ui_id))

        # Check for parsing errors and append .cmb if something is not supported
        if relpath and len(self.errors):
            filename, etx = os.path.splitext(relpath)
            c.execute("UPDATE ui SET filename=? WHERE ui_id=?", (f"{filename}.cmb.ui", ui_id))

        self.conn.commit()
        c.close()

        self.foreign_keys = True

        return ui_id

    def import_gresource_from_node(self, root, relpath):
        # Clear parsing errors
        self.errors = {}

        if root.tag != "gresources":
            raise Exception(_("Unknown root tag {tag}").format(tag=root.tag))

        gresource_id = self.add_gresource("gresources", gresources_filename=relpath)

        for child in root.iterchildren():
            if child.tag != "gresource":
                self.__unknown_tag(child, root, child.tag)
                continue

            prefix, = self.__node_get(child, "prefix")

            resource_id = self.add_gresource("gresource", parent_id=gresource_id, gresource_prefix=prefix)

            for file in child.iterchildren():
                if file.tag != "file":
                    self.__unknown_tag(file, child, file.tag)
                    continue

                compressed, preprocess, alias = self.__node_get(
                    file,
                    ["compressed:bool", "preprocess", "alias"],
                    collect_errors=False
                )
                self.add_gresource(
                    "file",
                    parent_id=resource_id,
                    file_filename=file.text,
                    file_compressed=compressed,
                    file_preprocess=preprocess,
                    file_alias=alias
                )

        return gresource_id

    def __node_add_comment(self, node, comment):
        if comment:
            node.addprevious(etree.Comment(comment))

    def __export_menu(self, ui_id, object_id, merengue=False, ignore_id=False):
        c = self.conn.cursor()

        c.execute("SELECT type_id, name, custom_fragment FROM object WHERE ui_id=? AND object_id=?;", (ui_id, object_id))
        type_id, name, custom_fragment = c.fetchone()

        if type_id == GMENU_TYPE:
            obj = E.menu()
            utils.xml_node_set(obj, "id", f"__cmb__{ui_id}.{object_id}" if merengue else name)
        elif type_id == GMENU_SECTION_TYPE:
            obj = E.section()
            utils.xml_node_set(obj, "id", f"__cmb__{ui_id}.{object_id}" if merengue else name)
        elif type_id == GMENU_SUBMENU_TYPE:
            obj = E.submenu()
            utils.xml_node_set(obj, "id", f"__cmb__{ui_id}.{object_id}" if merengue else name)
        elif type_id == GMENU_ITEM_TYPE:
            obj = E.item()
        else:
            logger.warning(f"Ignoring object type {type_id} while exporting menu.")
            return None

        # Properties
        for row in c.execute(
            """
            SELECT value, property_id, comment, translatable, translation_context, translation_comments
            FROM object_property
            WHERE ui_id=? AND object_id=?
            ORDER BY property_id
            """,
            (ui_id, object_id),
        ):
            (
                value,
                property_id,
                comment,
                translatable,
                translation_context,
                translation_comments,
            ) = row
            node = E.attribute(name=property_id)
            if value is not None:
                node.text = value

            if translatable:
                utils.xml_node_set(node, "translatable", "yes")
                utils.xml_node_set(node, "context", translation_context)
                utils.xml_node_set(node, "comments", translation_comments)

            obj.append(node)

        # Dump extra attributes
        info = self.type_info.get(type_id, None)
        for tag in info.data:
            taginfo = info.data[tag]

            for row in c.execute(
                "SELECT id FROM object_data WHERE ui_id=? AND object_id=? AND owner_id=? AND data_id=?;",
                (ui_id, object_id, type_id, taginfo.data_id),
            ):
                (id,) = row

                for child in taginfo.children:
                    self.__export_object_data(ui_id, object_id, type_id, child, taginfo.children[child], obj, id)

        # Children
        for row in c.execute(
            """
            SELECT object_id, comment
            FROM object
            WHERE ui_id=? AND parent_id=?
            ORDER BY position;
            """,
            (ui_id, object_id),
        ):
            child_id, comment = row
            child_obj = self.__export_menu(ui_id, child_id, merengue=merengue, ignore_id=ignore_id)

            if child_obj is not None:
                self.__node_add_comment(child_obj, comment)
                obj.append(child_obj)

        # Dump custom fragments
        self.__export_custom_fragment(obj, custom_fragment)

        c.close()

        return obj

    def __get_object_name(self, ui_id, object_id, merengue=False):
        if object_id is None:
            return None

        if merengue:
            # Ignore properties that reference an unknown object
            return f"__cmb__{ui_id}.{object_id}"

        row = self.conn.execute("SELECT name FROM object WHERE ui_id=? AND object_id=?;", (ui_id, object_id)).fetchone()
        return row[0] if row is not None else None

    def __export_object_data(self, ui_id, object_id, owner_id, name, info, node, parent_id, merengue=False):
        c = self.conn.cursor()
        cc = self.conn.cursor()

        for row in c.execute(
            """
            SELECT od.id, od.value, od.comment, od.translatable, od.translation_context, od.translation_comments, td.type_id
            FROM object_data AS od, type_data AS td
            WHERE od.owner_id = td.owner_id AND od.data_id = td.data_id AND
                  od.ui_id=? AND od.object_id=? AND od.owner_id=? AND od.data_id=? AND od.parent_id=?;
            """,
            (ui_id, object_id, owner_id, info.data_id, parent_id),
        ):
            id, value, comment, translatable, translation_context, translation_comments, type_id = row

            arg_info = self.type_info.get(type_id, None)
            if arg_info and arg_info.is_object:
                value = self.__get_object_name(ui_id, value, merengue=merengue)

            ntag = etree.Element(name)
            if value:
                ntag.text = value
            node.append(ntag)
            self.__node_add_comment(ntag, comment)

            for row in cc.execute(
                """
                SELECT od.key, od.value, td.type_id
                FROM object_data_arg AS od, type_data_arg AS td
                WHERE od.owner_id = td.owner_id AND od.data_id = td.data_id AND
                      od.ui_id=? AND od.object_id=? AND od.owner_id=? AND od.data_id=? AND
                      od.id=? AND od.value IS NOT NULL;
                """,
                (ui_id, object_id, owner_id, info.data_id, id),
            ):
                key, value, type_id = row

                arg_info = self.type_info.get(type_id, None)
                if arg_info and arg_info.is_object:
                    value = self.__get_object_name(ui_id, value, merengue=merengue)

                if value:
                    ntag.set(key, value)

            if translatable:
                utils.xml_node_set(ntag, "translatable", "yes")
                utils.xml_node_set(ntag, "context", translation_context)
                utils.xml_node_set(ntag, "comments", translation_comments)

            for tag in info.children:
                self.__export_object_data(ui_id, object_id, owner_id, tag, info.children[tag], ntag, id)

        c.close()
        cc.close()

    def __export_type_data(self, ui_id, object_id, owner_id, info, node, merengue=False):
        if len(info.data.keys()) == 0:
            return

        for tag in info.data:
            taginfo = info.data[tag]

            for row in self.execute(
                "SELECT id, value, comment FROM object_data WHERE ui_id=? AND object_id=? AND owner_id=? AND data_id=?;",
                (ui_id, object_id, owner_id, taginfo.data_id),
            ):
                id, value, comment = row
                ntag = etree.Element(tag)
                if value:
                    ntag.text = value
                node.append(ntag)
                self.__node_add_comment(ntag, comment)

                for child in taginfo.children:
                    self.__export_object_data(ui_id, object_id, owner_id, child, taginfo.children[child], ntag, id, merengue=merengue)

    def __internal_object_is_empty(self, ui_id, object_id):
        # Check if internal object is empty or not, it has name, xml fragments, children, property or any other data
        row = self.execute(
            """
            WITH RECURSIVE d(ui_id, object_id)
            AS (
              VALUES(?, ?)
              UNION
              SELECT o.ui_id, o.object_id FROM object AS o, d WHERE o.ui_id=d.ui_id AND o.parent_id=d.object_id
            )
            SELECT
              (SELECT COUNT(ui_id) FROM object
               WHERE (ui_id, object_id) IN d AND
               (name IS NOT NULL OR type IS NOT NULL OR custom_fragment IS NOT NULL OR custom_child_fragment IS NOT NULL)
              ),
              (SELECT COUNT(ui_id) FROM object WHERE internal IS NULL AND (ui_id, parent_id) IN d),
              (SELECT COUNT(ui_id) FROM object_property WHERE (ui_id, object_id) IN d),
              (SELECT COUNT(ui_id) FROM object_layout_property WHERE (ui_id, child_id) IN d),
              (SELECT COUNT(ui_id) FROM object_signal WHERE (ui_id, object_id) IN d),
              (SELECT COUNT(ui_id) FROM object_data WHERE (ui_id, object_id) IN d);
            """,
            (ui_id, object_id)
        ).fetchone()
        n_objs, n_children, n_props, n_layout_props, n_signals, n_data = row

        return n_objs == 0 and n_children == 0 and n_props == 0 and n_layout_props == 0 and n_signals == 0 and n_data == 0

    def __export_object(self, ui_id, object_id, merengue=False, template_id=None, ignore_id=False):
        c = self.conn.cursor()

        c.execute("SELECT type_id, name, custom_fragment FROM object WHERE ui_id=? AND object_id=?;", (ui_id, object_id))
        type_id, name, custom_fragment = c.fetchone()

        # Special case <menu>
        if type_id == GMENU_TYPE:
            c.close()
            return self.__export_menu(ui_id, object_id, merengue=merengue, ignore_id=ignore_id)

        info = self.type_info.get(type_id, None)

        if info is None:
            logger.warning(f"Type info missing for type {type_id}")
            c.close()
            return None

        cc = self.conn.cursor()

        merengue_template = merengue and info.library_id is None and info.parent_id is not None
        # Check if this is a custom template object
        # We do not export object templates in merengue mode, this way we do not really need to instantiate a real type
        # in the workspace
        if merengue_template:
            # Get ui_id and object_id from template object
            c.execute(
                """
                SELECT u.ui_id, u.template_id, o.type_id
                FROM ui AS u, object AS o
                WHERE u.template_id IS NOT NULL AND u.ui_id=o.ui_id AND u.template_id=o.object_id AND o.name=?;
                """,
                (type_id,),
            )
            tmpl_ui_id, tmpl_object_id, tmpl_type_id = c.fetchone()

            # Export template object for merengue without ids
            obj = self.__export_object(tmpl_ui_id, tmpl_object_id, merengue=True, ignore_id=True)

            # Set object id
            if not ignore_id:
                utils.xml_node_set(obj, "id", f"__cmb__{ui_id}.{object_id}")
        elif not merengue and template_id == object_id:
            obj = E.template()
            utils.xml_node_set(obj, "class", name)
            utils.xml_node_set(obj, "parent", type_id)
        else:
            obj = E.object()

            if merengue:
                workspace_type = info.workspace_type
                utils.xml_node_set(obj, "class", workspace_type if workspace_type else type_id)

                if merengue_template:
                    # From now own all output should be without an ID
                    # because we do not want so select internal widget from the template
                    ignore_id = True
                elif not ignore_id:
                    utils.xml_node_set(obj, "id", f"__cmb__{ui_id}.{object_id}")
            else:
                utils.xml_node_set(obj, "class", type_id)
                if not ignore_id:
                    utils.xml_node_set(obj, "id", name)

        # Create class hierarchy list
        hierarchy = [type_id] + info.hierarchy if info else [type_id]

        # SQL placeholder for every class in the list
        placeholders = ",".join((["?"] * len(hierarchy)))

        # This ensures we do not output template properties for merengue
        template_check = "AND t.library_id IS NOT NULL" if merengue_template else ""

        # Properties + required + save_always default values
        for row in c.execute(
            f"""
            SELECT op.value, op.property_id, op.inline_object_id, op.comment, op.translatable, op.translation_context,
                   op.translation_comments, p.is_object, p.disable_inline_object,
                   op.bind_source_id, op.bind_owner_id, op.bind_property_id, op.bind_flags,
                   NULL, NULL, p.type_id
            FROM object_property AS op, property AS p, type AS t
            WHERE op.owner_id NOT IN
                  ('CmbAccessibleProperty', 'CmbAccessibleRelation', 'CmbAccessibleState', 'CmbAccessibleAction') AND
                  op.ui_id=? AND op.object_id=? AND p.owner_id = op.owner_id AND p.property_id = op.property_id AND
                  p.owner_id == t.type_id
                  {template_check}
            UNION
            SELECT p.default_value, p.property_id, NULL, NULL, NULL, NULL, NULL, p.is_object, p.disable_inline_object,
                   NULL, NULL, NULL, NULL, p.required, p.workspace_default, p.type_id
            FROM property AS p, type AS t
            WHERE p.owner_id == t.type_id AND (required=1 OR save_always=1) AND owner_id IN ({placeholders}) AND
                  property_id NOT IN (SELECT property_id FROM object_property WHERE ui_id=? AND object_id=?)
                   {template_check}
            ORDER BY op.property_id
            """,
            (ui_id, object_id) + tuple(hierarchy) + (ui_id, object_id),
        ):
            (
                val,
                property_id,
                inline_object_id,
                comment,
                translatable,
                translation_context,
                translation_comments,
                is_object,
                disable_inline_object,
                bind_source_id,
                bind_owner_id,
                bind_property_id,
                bind_flags,
                required,
                workspace_default,
                property_type_id,
            ) = row

            value = None
            value_node = None

            is_inline_object = not disable_inline_object and self.target_tk == "gtk-4.0"

            if required and workspace_default:
                if is_object and is_inline_object:
                    value_node = etree.fromstring(workspace_default)
                else:
                    value = workspace_default
            elif is_object:
                # Ignore object properties with 0/null ID or unknown object references
                if val is not None and val.isnumeric() and int(val) == 0:
                    continue

                if inline_object_id and is_inline_object:
                    value_node = self.__export_object(ui_id, inline_object_id, merengue=merengue, ignore_id=ignore_id)
                elif ignore_id:
                    # Ignore references to object in template mode since the object could not exists in this UI
                    continue
                else:
                    obj_name = self.__get_object_name(ui_id, val, merengue=merengue)

                    # Ignore properties that reference an unknown object
                    if obj_name is None:
                        continue
                    value = obj_name
            elif property_type_id == "GBytes":
                value = etree.CDATA(val)
            else:
                value = val

            node = E.property(name=property_id)
            if value is not None:
                node.text = value
            elif value_node is not None:
                node.append(value_node)

            if translatable:
                utils.xml_node_set(node, "translatable", "yes")
                utils.xml_node_set(node, "context", translation_context)
                utils.xml_node_set(node, "comments", translation_comments)

            if bind_source_id and bind_owner_id and bind_property_id:
                bind_source = self.__get_object_name(ui_id, bind_source_id, merengue=merengue)

                if bind_source:
                    utils.xml_node_set(node, "bind-source", bind_source)
                    utils.xml_node_set(node, "bind-property", bind_property_id)
                    utils.xml_node_set(node, "bind-flags", bind_flags)

            obj.append(node)
            self.__node_add_comment(node, comment)

        # Signals
        if not merengue:
            for row in c.execute(
                """
                SELECT signal_id, handler, detail, (SELECT name FROM object WHERE ui_id=? AND object_id=user_data), swap, after,
                       comment
                FROM object_signal
                WHERE ui_id=? AND object_id=?;
                """,
                (
                    ui_id,
                    ui_id,
                    object_id,
                ),
            ):
                signal_id, handler, detail, data, swap, after, comment = row

                name = f"{signal_id}::{detail}" if detail is not None else signal_id
                node = E.signal(name=name, handler=handler)

                if data:
                    utils.xml_node_set(node, "object", data)

                    # if object is set, swap defaults to True
                    if not swap:
                        utils.xml_node_set(node, "swapped", "no")
                elif swap:
                    utils.xml_node_set(node, "swapped", "yes")

                if after:
                    utils.xml_node_set(node, "after", "yes")
                obj.append(node)
                self.__node_add_comment(node, comment)

        # Accessibility
        accessibility = E.accessibility()

        # For Gtk 3
        atk_object = None

        # For Gtk 4
        accessible_role = None
        a11y_data = {}

        if self.target_tk == "gtk+-3.0":
            atk_object = E.object()
            atk_object.set("class", "AtkObject")
        else:
            r = c.execute(
                """
                SELECT value, owner_id FROM object_property
                WHERE ui_id=? AND object_id=? AND property_id='accessible-role';
                """,
                (ui_id, object_id),
            ).fetchone()

            if r is None:
                pinfo = self.__get_property_info(info, "accessible-role")
                accessible_role = pinfo.default_value if pinfo else 'none'
            else:
                accessible_role = r[0]

            if accessible_role in self.accessibility_metadata:
                role_data = self.accessibility_metadata.get(accessible_role)
                a11y_data = {
                    "CmbAccessibleProperty": (len("cmb-a11y-properties"), role_data["properties"]),
                    "CmbAccessibleState": (len("cmb-a11y-states"), role_data["states"]),
                }

        if accessible_role is None or accessible_role not in ["none", "presentation"]:
            for row in c.execute(
                """
                SELECT op.value, op.property_id, op.comment, op.translatable, op.translation_context,
                       op.translation_comments, p.is_object, p.type_id, op.owner_id
                FROM object_property AS op, property AS p
                WHERE op.owner_id IN
                      ('CmbAccessibleProperty', 'CmbAccessibleRelation', 'CmbAccessibleState', 'CmbAccessibleAction') AND
                      op.ui_id=? AND op.object_id=? AND p.owner_id = op.owner_id AND p.property_id = op.property_id
                ORDER BY op.owner_id, op.property_id
                """,
                (ui_id, object_id),
            ):
                (
                    val,
                    property_id,
                    comment,
                    translatable,
                    translation_context,
                    translation_comments,
                    is_object,
                    property_type_id,
                    owner_id,
                ) = row

                value = None

                # Ignore properties depending on metadata (Gtk4)
                if atk_object is None:
                    prefix_len, allowed_ids = a11y_data.get(owner_id, (None, None))
                    if prefix_len and allowed_ids is not None and property_id[prefix_len:] not in allowed_ids:
                        continue

                if is_object:
                    # Ignore object properties with 0/null ID or unknown object references
                    if val is not None and val.isnumeric() and int(val) == 0:
                        continue

                    obj_name = self.__get_object_name(ui_id, val, merengue=merengue)

                    # Ignore properties that reference an unknown object
                    if obj_name is None:
                        continue
                    value = obj_name
                else:
                    value = val

                # Accessible properties are prefixed to avoid name clash with other properties
                if atk_object is not None:
                    if owner_id == "CmbAccessibleProperty":
                        node = E.property(name=f"accessible-{property_id.removeprefix('cmb-a11y-property-')}")
                        atk_object.append(node)
                    elif owner_id == "CmbAccessibleRelation":
                        if value is not None:
                            node = E.relation(type=property_id.removeprefix("cmb-a11y-relation-"), target=value)
                            accessibility.append(node)

                            # Value already set as an attribute
                            value = None
                    elif owner_id == "CmbAccessibleAction":
                        node = E.action(action_name=property_id.removeprefix("cmb-a11y-action-"))
                        accessibility.append(node)
                else:
                    if owner_id == "CmbAccessibleProperty":
                        node = E.property(name=property_id.removeprefix("cmb-a11y-property-"))
                        accessibility.append(node)
                    elif owner_id == "CmbAccessibleRelation":
                        relation_name = property_id.removeprefix("cmb-a11y-relation-")

                        # Serialize reference lists as multiple nodes
                        if property_type_id == "CmbAccessibleList":
                            for ref in [v.strip() for v in value.split(",")]:
                                # Ignore object properties with 0/null ID or unknown object references
                                if ref is not None and ref.isnumeric() and int(ref) == 0:
                                    continue

                                obj_name = self.__get_object_name(ui_id, ref, merengue=merengue)

                                # Ignore properties that reference an unknown object
                                if obj_name is None:
                                    continue

                                node = E.relation(name=relation_name)
                                node.text = obj_name
                                accessibility.append(node)

                            continue
                        else:
                            node = E.relation(name=relation_name)
                    elif owner_id == "CmbAccessibleState":
                        node = E.state(name=property_id.removeprefix("cmb-a11y-state-"))
                        accessibility.append(node)

                if value is not None:
                    node.text = value

                if translatable:
                    utils.xml_node_set(node, "translatable", "yes")
                    utils.xml_node_set(node, "context", translation_context)
                    utils.xml_node_set(node, "comments", translation_comments)

                self.__node_add_comment(node, comment)

        # Append accessibility if there is anything
        if len(accessibility):
            obj.append(accessibility)

        # Append internal AtkObject if there is any property set
        if atk_object is not None and len(atk_object):
            atk_child = E.child()
            atk_child.set("internal-child", "accessible")
            atk_child.append(atk_object)
            obj.append(atk_child)

        # Find first layout properties class
        layout_class = f"{type_id}LayoutChild"
        for owner_id in hierarchy:
            owner_class = f"{owner_id}LayoutChild"
            linfo = self.type_info.get(owner_class, None)
            if linfo is not None:
                break

        # Construct Layout Child class hierarchy list
        hierarchy = [layout_class] + linfo.hierarchy if linfo else [layout_class]

        # SQL placeholder for every class in the list
        placeholders = ",".join((["?"] * len(hierarchy)))

        child_position = 0

        # FIXME: only export placeholders for GtkBox
        # This needs to be removed and handled directly in merengue by passing postion together with idi
        is_box = info.is_a("GtkBox")

        # Children
        for row in c.execute(
            """
            SELECT object_id, internal, type, comment, position, custom_child_fragment
            FROM object
            WHERE ui_id=? AND parent_id=? AND
                  object_id NOT IN (SELECT inline_object_id FROM object_property
                                    WHERE inline_object_id IS NOT NULL AND ui_id=? AND object_id=?)
            ORDER BY position;
            """,
            (ui_id, object_id, ui_id, object_id),
        ):
            child_id, internal, ctype, comment, position, custom_child_fragment = row

            # Here we try to output internal children only if nescesary
            if not merengue and internal and self.__internal_object_is_empty(ui_id, child_id):
                continue

            if merengue and is_box:
                position = position if position is not None else 0

                while child_position < position:
                    placeholder = E.object()
                    placeholder.set("class", "MrgPlaceholder")
                    obj.append(E.child(placeholder))
                    child_position += 1

                child_position += 1

            child_obj = self.__export_object(ui_id, child_id, merengue=merengue, ignore_id=ignore_id)
            child = E.child(child_obj)
            utils.xml_node_set(child, "internal-child", internal)
            utils.xml_node_set(child, "type", ctype)
            self.__node_add_comment(child_obj, comment)

            obj.append(child)

            if linfo is not None:
                # Packing / Layout
                layout = E("packing" if self.target_tk == "gtk+-3.0" else "layout")
                for prop in cc.execute(
                    f"""
                    SELECT value, property_id, comment
                    FROM object_layout_property
                    WHERE ui_id=? AND object_id=? AND child_id=?
                    UNION
                    SELECT default_value AS value, property_id, null
                    FROM property
                    WHERE save_always=1 AND owner_id IN ({placeholders}) AND property_id NOT IN
                          (SELECT property_id FROM object_layout_property WHERE ui_id=? AND object_id=? AND child_id=?)
                    ORDER BY property_id
                    """,
                    (ui_id, object_id, child_id) + tuple(hierarchy) + (ui_id, object_id, child_id),
                ):
                    value, property_id, comment = prop
                    node = E.property(value, name=property_id)
                    layout.append(node)
                    self.__node_add_comment(node, comment)

                if len(layout) > 0:
                    if self.target_tk == "gtk+-3.0":
                        child.append(layout)
                    else:
                        child_obj.append(layout)

            if custom_child_fragment is not None:
                # Dump custom child fragments
                self.__export_custom_fragment(child, custom_child_fragment)

        # Custom buildable tags
        # Iterate over all hierarchy extra data
        self.__export_type_data(ui_id, object_id, type_id, info, obj, merengue=merengue)
        for parent in info.hierarchy:
            pinfo = self.type_info.get(parent, None)
            if pinfo:
                self.__export_type_data(ui_id, object_id, parent, pinfo, obj, merengue=merengue)

        # Dump custom fragments
        self.__export_custom_fragment(obj, custom_fragment)

        c.close()
        cc.close()

        return obj

    def __export_custom_fragment(self, node, custom_fragment):
        if custom_fragment is None:
            return
        try:
            root = etree.fromstring(f"<root>{custom_fragment}</root>")
        except Exception:
            pass
        else:
            node.append(etree.Comment(f" Custom {node.tag} fragments "))
            for child in root:
                node.append(child)

    def export_ui(self, ui_id, merengue=False):
        c = self.conn.cursor()

        c.execute("SELECT translation_domain, comment, template_id, custom_fragment FROM ui WHERE ui_id=?;", (ui_id,))
        row = c.fetchone()

        if row is None:
            return None

        translation_domain, comment, template_id, custom_fragment = row

        node = E.interface()
        node.addprevious(etree.Comment(f" Created with Cambalache {config.VERSION} "))
        utils.xml_node_set(node, "domain", translation_domain)

        self.__node_add_comment(node, comment)

        # Export UI data as comments
        for key in ["name", "description", "copyright", "authors", "license_id"]:
            c.execute(f"SELECT {key} FROM ui WHERE ui_id=?;", (ui_id,))
            value = c.fetchone()[0]

            if value is not None:
                key = key.replace("_", "-")
                node.append(etree.Comment(f" interface-{key} {value} "))

        # Requires selected by the user
        for row in c.execute("SELECT library_id, version, comment FROM ui_library WHERE ui_id=?;", (ui_id,)):
            library_id, version, comment = row
            req = E.requires(lib=library_id, version=version)
            self.__node_add_comment(req, comment)
            node.append(req)

        # Ensure we output a requires lib for every used module
        # If the user did not specify a requirement version we use the minimum that meets the requirements
        if not merengue:
            for row in c.execute(
                """
                WITH lib_version(library_id, version) AS (
                    SELECT t.library_id, t.version
                      FROM object AS o, type AS t
                      WHERE o.ui_id=? AND o.type_id = t.type_id AND t.version IS NOT NULL
                    UNION
                    SELECT t.library_id, p.version
                      FROM object_property AS o, property AS p, type AS t
                      WHERE o.ui_id=? AND o.owner_id = t.type_id AND o.owner_id = p.owner_id AND p.version IS NOT NULL AND
                        p.original_owner_id IS NULL
                    UNION
                    SELECT t.library_id, p.version
                      FROM object_property AS o, property AS p, type AS t
                      WHERE o.ui_id=? AND o.owner_id = t.type_id AND o.owner_id = p.original_owner_id AND
                        p.version IS NOT NULL AND p.original_owner_id IS NOT NULL
                    UNION
                    SELECT t.library_id, s.version
                      FROM object_signal AS o, signal AS s, type AS t
                      WHERE o.ui_id=? AND o.owner_id = t.type_id AND o.owner_id = s.owner_id AND s.version IS NOT NULL
                    UNION
                    SELECT library_id, MIN_VERSION(version)
                      FROM library_version
                      WHERE library_id IN
                        (SELECT DISTINCT t.library_id FROM object AS o, type AS t WHERE o.ui_id=? AND o.type_id = t.type_id)
                    GROUP BY library_id
                )
                SELECT library_id, MAX_VERSION(version)
                FROM lib_version
                WHERE library_id NOT IN (SELECT library_id FROM ui_library WHERE ui_id=?)
                GROUP BY library_id
                ORDER BY library_id;
                """,
                (ui_id, ui_id, ui_id, ui_id, ui_id, ui_id),
            ):
                library_id, version = row
                req = E.requires(lib=library_id, version=version)
                node.append(req)

        # Iterate over toplevel objects
        for row in c.execute(
            f"""
            SELECT object_id, comment
            FROM object
            WHERE parent_id IS NULL AND type_id != '{EXTERNAL_TYPE}' AND ui_id=?;
            """,
            (ui_id,),
        ):
            object_id, comment = row
            child = self.__export_object(ui_id, object_id, merengue=merengue, template_id=template_id)
            if child is None:
                continue

            node.append(child)
            self.__node_add_comment(child, comment)

        # Dump custom fragments
        self.__export_custom_fragment(node, custom_fragment)

        c.close()

        return etree.ElementTree(node)

    def tostring(self, ui_id, merengue=False):
        ui = self.export_ui(ui_id, merengue=merengue)

        if ui is None:
            return None

        return etree.tostring(ui, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("UTF-8")

    def export_gresource(self, gresources_id):
        c = self.conn.cursor()

        c.execute(
            "SELECT gresources_filename FROM gresource WHERE resource_type='gresources' AND gresource_id=?;",
            (gresources_id, )
        )
        row = c.fetchone()

        if row is None:
            c.close()
            return None

        root = E.gresources()
        root.addprevious(etree.Comment(f" Created with Cambalache {config.VERSION} "))

        cc = self.conn.cursor()

        # Iterate over resources
        for row in c.execute(
            "SELECT gresource_id, gresource_prefix FROM gresource WHERE resource_type='gresource' AND parent_id=?;",
            (gresources_id, )
        ):
            resource_id, resource_prefix = row

            gresource = E.gresource()
            utils.xml_node_set(gresource, "prefix", resource_prefix)
            for row in cc.execute(
                """
                SELECT file_filename, file_compressed, file_preprocess, file_alias
                FROM gresource
                WHERE resource_type='file' AND parent_id=?;
                """,
                (resource_id, )
            ):
                filename, compressed, preprocess, alias = row

                file = E.file()

                if filename:
                    file.text = filename

                if compressed:
                    utils.xml_node_set(file, "compressed", "true")

                utils.xml_node_set(file, "preprocess", preprocess)
                utils.xml_node_set(file, "alias", alias)
                gresource.append(file)

            root.append(gresource)

        c.close()
        cc.close()

        return etree.ElementTree(root)

    def gresource_tostring(self, gresource_id):
        gresource = self.export_gresource(gresource_id)

        if gresource is None:
            return None

        return etree.tostring(gresource, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("UTF-8")

    def clipboard_copy(self, selection):
        self.clipboard = []
        self.clipboard_ids = []

        c = self.conn.cursor()

        # Copy data for every object in selection
        for ui_id, object_id in selection:
            node = self.__export_object(ui_id, object_id)
            self.clipboard.append(node)

            c.execute(
                """
                WITH RECURSIVE ancestor(object_id, parent_id, name) AS (
                  SELECT object_id, parent_id, name
                  FROM object
                  WHERE ui_id=? AND object_id=?
                  UNION
                  SELECT object.object_id, object.parent_id, object.name
                  FROM object JOIN ancestor ON object.parent_id=ancestor.object_id
                  WHERE ui_id=?
                )
                SELECT name FROM ancestor WHERE name IS NOT NULL;
                """,
                (ui_id, object_id, ui_id),
            )

            # Object ids that will need to be remapped
            self.clipboard_ids += tuple([x[0] for x in c.fetchall()])

        c.close()

    def clipboard_paste(self, ui_id, parent_id):
        foreign_keys = self.foreign_keys
        self.foreign_keys = False

        c = self.conn.cursor()
        object_id_map = {}
        retval = {}

        # Generate new object_id mapping
        for object_id in self.clipboard_ids:
            object_id_base = object_id

            tokens = object_id_base.rsplit("_", 1)
            if len(tokens) == 2 and tokens[1].isdigit():
                object_id_base = tokens[0]

            max_index = 0
            for row in c.execute(
                "SELECT name FROM object WHERE ui_id=? AND name IS NOT NULL AND name LIKE ?;",
                (ui_id, f"{object_id_base}%"),
            ):
                tokens = row[0].rsplit("_", 1)

                if len(tokens) == 2 and tokens[0] == object_id_base:
                    try:
                        max_index = max(max_index, int(tokens[1]))
                    except Exception:
                        pass
                elif row[0] == object_id_base:
                    max_index = 1

            object_id_map[object_id] = f"{object_id_base}_{max_index+1}" if max_index else object_id

        for node in self.clipboard:
            object_id = self.__import_object(ui_id, node, parent_id, object_id_map=object_id_map)

            c.execute(
                """
                WITH RECURSIVE ancestor(object_id, parent_id) AS (
                  SELECT object_id, parent_id
                  FROM object
                  WHERE ui_id=? AND object_id=?
                  UNION
                  SELECT object.object_id, object.parent_id
                  FROM object JOIN ancestor ON object.parent_id=ancestor.object_id
                  WHERE ui_id=?
                )
                SELECT object_id FROM ancestor;
                """,
                (ui_id, object_id, ui_id),
            )

            # Object and children ids
            retval[object_id] = tuple([x[0] for x in c.fetchall()])

        self.__fix_object_references(ui_id, fix_externals=False)

        self.foreign_keys = foreign_keys

        c.close()
        return retval

    def clear_history(self):
        self.conn.executescript(self.__clear_history)

    def update_children_position(self, ui_id, parent_id=None):
        parent_clause = "parent_id IS NULL" if parent_id is None else "parent_id=?"
        self.execute(
            f"""
            UPDATE object SET position=new.position - 1
            FROM (
                SELECT row_number() OVER (PARTITION BY parent_id ORDER BY position) position, ui_id, object_id
                FROM object
                WHERE ui_id=? AND {parent_clause}
            ) AS new
            WHERE object.ui_id=new.ui_id AND object.object_id=new.object_id;
            """,
            (ui_id, ) if parent_id is None else (ui_id, parent_id)
        )


# Function used in SQLite


# Compares two version strings
def sqlite_version_cmp(a, b):
    return utils.version_cmp(utils.parse_version(a), utils.parse_version(b))


# Aggregate class to get the MAX version
class MaxVersion:
    def __init__(self):
        self.max_ver = None
        self.max_ver_str = None

    def step(self, value):
        ver = utils.parse_version(value)

        if self.max_ver is None or utils.version_cmp(self.max_ver, ver) < 0:
            self.max_ver = ver
            self.max_ver_str = value

    def finalize(self):
        return self.max_ver_str


# Aggregate class to get the MIN version
class MinVersion:
    def __init__(self):
        self.min_ver = None
        self.min_ver_str = None

    def step(self, value):
        ver = utils.parse_version(value)

        if self.min_ver is None or utils.version_cmp(self.min_ver, ver) > 0:
            self.min_ver = ver
            self.min_ver_str = value

    def finalize(self):
        return self.min_ver_str


def cmb_object_list_remove(object_list, object_id):
    if object_list is None:
        return None

    values = [id for id in object_list.split(",") if id.isnumeric() and int(id) != object_id]
    return ",".join(values)


def cmb_print(msg):
    print(msg, file=sys.stderr)
