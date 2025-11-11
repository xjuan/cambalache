#
# CmbProject - Cambalache Project
#
# Copyright (C) 2020-2024  Juan Pablo Ugarte
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
import json
import time
import sqlite3
import hashlib

from pathlib import Path
from gi.repository import GObject, Gio, GLib
from graphlib import TopologicalSorter, CycleError

from lxml import etree
from lxml.builder import E

from .cmb_db import CmbDB
from .cmb_ui import CmbUI
from .cmb_css import CmbCSS
from .cmb_gresource import CmbGResource
from .cmb_base import CmbBase
from .cmb_object import CmbObject
from .cmb_object_data import CmbObjectData
from .cmb_path import CmbPath
from .cmb_property import CmbProperty
from .cmb_property_info import CmbPropertyInfo
from .cmb_layout_property import CmbLayoutProperty
from .cmb_library_info import CmbLibraryInfo
from .cmb_type_info import CmbTypeInfo
from .cmb_base_objects import CmbSignal
from .cmb_blueprint import cmb_blueprint_decompile, cmb_blueprint_compile
from .utils import FileHash
from . import constants, utils
from cambalache import config, getLogger, _, N_

logger = getLogger(__name__)


class CmbProject(GObject.Object, Gio.ListModel):
    __gtype_name__ = "CmbProject"

    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "ui-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbUI,)),
        "ui-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbUI,)),
        "ui-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbUI, str)),
        "ui-library-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbUI, str)),
        "css-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbCSS,)),
        "css-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbCSS,)),
        "css-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbCSS, str)),
        "gresource-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbGResource,)),
        "gresource-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbGResource,)),
        "gresource-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbGResource, str)),
        "object-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject,)),
        "object-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject,)),
        "object-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, str)),
        "object-property-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, CmbProperty)),
        "object-layout-property-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (CmbObject, CmbObject, CmbLayoutProperty),
        ),
        "object-property-binding-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, CmbProperty)),
        "object-signal-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, CmbSignal)),
        "object-signal-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, CmbSignal)),
        "object-signal-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, CmbSignal)),
        "object-child-reordered": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, CmbObject, int, int)),
        "object-data-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, CmbObjectData)),
        "object-data-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObject, CmbObjectData)),
        "object-data-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObjectData,)),
        "object-data-data-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbObjectData, CmbObjectData)),
        "object-data-data-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObjectData, CmbObjectData)),
        "object-data-arg-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObjectData, str)),
        "selection-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "type-info-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbTypeInfo,)),
        "type-info-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbTypeInfo,)),
        "type-info-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbTypeInfo,)),
    }

    target_tk = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)

    undo_msg = GObject.Property(type=str)
    redo_msg = GObject.Property(type=str)

    def __init__(self, target_tk=None, filename=None, **kwargs):
        # Type Information
        self.type_info = {}

        # Library Info
        self.library_info = {}

        # GListModel
        self.__items = []
        self.__path_items = {}
        self.__unsaved_item = None

        # Selection
        self.__selection = []
        self._ignore_selection = False

        # Objects hash tables
        self._object_id = {}
        self.__css_id = {}
        self.__gresource_id = {}

        # File state
        self.__file_state = {}

        self.__template_info = {}

        self.__filename = None

        self.icontheme_search_paths = []

        super().__init__(**kwargs)

        self.target_tk = target_tk
        self.filename = filename

        # Target from file take precedence over target_tk property
        if self.filename and os.path.isfile(self.filename):
            target_tk = CmbDB.get_target_from_file(self.filename)

            if target_tk is not None:
                self.target_tk = target_tk

        if self.target_tk is None or self.target_tk == "":
            raise Exception(_("Either target_tk or filename are required"))

        # DataModel is only used internally
        self.db = CmbDB(target_tk=self.target_tk)
        self.db.type_info = self.type_info
        self.__init_data()

        self.__load()

    def __bool__(self):
        # Ensure that CmbProject objects evaluates to True even if it does not have any ui or css
        return True

    def __str__(self):
        return f"CmbProject<{self.target_tk}> {self.filename}"

    @GObject.Property(type=bool, default=False)
    def history_enabled(self):
        return bool(self.db.get_data("history_enabled"))

    @history_enabled.setter
    def _set_history_enabled(self, value):
        self.db.set_data("history_enabled", value)

    @GObject.Property(type=int)
    def history_index_max(self):
        c = self.db.execute("SELECT MAX(history_id) FROM history;")
        row = c.fetchone()
        c.close()

        if row is None or row[0] is None:
            return 0

        return int(row[0])

    @GObject.Property(type=int)
    def history_index(self):
        history_index = int(self.db.get_data("history_index"))

        if history_index < 0:
            return self.history_index_max

        return history_index

    @history_index.setter
    def _set_history_index(self, value):
        if value == self.history_index_max:
            value = -1

        self.db.set_data("history_index", value)

    @GObject.Property(type=int)
    def history_index_version(self):
        row = self.db.execute("SELECT version FROM history WHERE history_id=?;", (self.history_index, )).fetchone()
        return row[0] if row else 0

    def _get_table_data(self, table):
        c = self.db.cursor()

        columns = []
        types = []
        pks = []

        for row in c.execute(f"PRAGMA table_info({table});"):
            col = row[1]
            col_type = row[2]
            pk = row[5]

            if col_type == "INTEGER":
                col_type = GObject.TYPE_INT
            elif col_type == "TEXT":
                col_type = GObject.TYPE_STRING
            elif col_type == "BOOLEAN":
                col_type = GObject.TYPE_BOOLEAN
            else:
                logger.warning(f"Unknown column type {col_type}")

            columns.append(col)
            types.append(col_type)

            if pk:
                pks.append(col)

        c.close()

        return {"names": columns, "types": types, "pks": pks}

    def _get_types(self):
        retval = []
        for row in self.db.execute("SELECT type_id FROM type ORDER BY type_id;"):
            retval.append(row[0])
        return retval

    def __init_type_info(self, c):
        for row in c.execute("SELECT * FROM type WHERE parent_id IS NOT NULL ORDER BY type_id;"):
            type_id = row[0]
            self.type_info[type_id] = CmbTypeInfo.from_row(self, *row)

        # Set parent back reference
        for type_id in self.type_info:
            info = self.type_info[type_id]
            info.parent = self.type_info.get(info.parent_id, None)

    def __init_library_info(self, c):
        for row in c.execute("SELECT * FROM library ORDER BY library_id;"):
            library_id = row[0]

            info = CmbLibraryInfo.from_row(self, *row)
            info.third_party = library_id not in ("gobject", "pango", "gdkpixbuf", "gio", "gdk", "gtk", "gtk+")
            self.library_info[library_id] = info

    def __init_data(self):
        if self.target_tk is None:
            return

        c = self.db.cursor()

        self.__init_type_info(c)
        self.__init_library_info(c)

        c.close()

    def __get_abs_path(self, filename):
        projectdir = os.path.dirname(self.filename) if self.filename else "."
        if os.path.isabs(filename):
            fullpath = filename
        else:
            fullpath = os.path.join(projectdir, filename)

        relpath = os.path.relpath(fullpath, projectdir)

        return fullpath, relpath

    def __parse_xml_file(self, filename):
        fullpath, relpath = self.__get_abs_path(filename)

        with open(fullpath, "rb") as fd:
            hash_file = FileHash(fd)
            tree = etree.parse(hash_file)
            hexdigest = hash_file.hexdigest()
            root = tree.getroot()

            return root, relpath, hexdigest

        return None, None, None

    def __parse_blp_file(self, filename):
        fullpath, relpath = self.__get_abs_path(filename)

        with open(fullpath, "rb") as fd:
            blueprint_decompiled = fd.read()
            m = hashlib.sha256()
            m.update(blueprint_decompiled)
            hexdigest = m.hexdigest()

            blueprint_compiled = cmb_blueprint_compile(blueprint_decompiled.decode())
            root = etree.fromstring(blueprint_compiled)

            return root, relpath, hexdigest

        return None, None, None

    def __get_version_comment_from_root(self, root):
        comment = root.getprevious()
        if comment is not None and comment.tag is etree.Comment:
            return comment
        return None

    def __load_ui_from_node(self, node):
        filename, sha256 = utils.xml_node_get(node, ["filename", "sha256"])
        if filename:
            if filename.endswith(".blp"):
                root, relpath, hexdigest = self.__parse_blp_file(filename)
            else:
                root, relpath, hexdigest = self.__parse_xml_file(filename)

            if sha256 != hexdigest:
                logger.warning(f"{filename} hash mismatch, file was modified")

            ui_id = self.db.import_from_node(root, relpath)

            cmb_version = self.__get_version_comment_from_root(root)
            self.__file_state[filename] = cmb_version, sha256
        else:
            content = node.find("content")
            if content is not None:
                root = etree.fromstring(content.text.encode())
                ui_id = self.db.import_from_node(root, None)
            else:
                raise Exception(_("content tag is missing"))

        msgs, detail_msg = self.__get_import_errors()
        self.db.errors = None
        if msgs:
            logger.warning(f"Error loading {filename}: {detail_msg}")

        row = self.db.execute("SELECT template_id FROM ui WHERE ui_id=?;", (ui_id,)).fetchone()
        template_id = row[0] if row else None
        owner_id = None

        if template_id:
            row = self.db.execute("SELECT name FROM object WHERE ui_id=? AND object_id=?;", (ui_id, template_id)).fetchone()

            owner_id = row[0] if row else None

        if owner_id:
            for property in node.findall("property"):
                property_id, type_id = utils.xml_node_get(property, "id", "type-id")

                try :
                    self.db.execute(
                        "INSERT INTO property(owner_id, property_id, type_id) VALUES (?, ?, ?);",
                        (owner_id, property_id, type_id)
                    )
                except sqlite3.IntegrityError as e:
                    logger.warning(f"Error inserting property {owner_id}::{property_id} of type {type_id}: {e}")
                    continue

                for key in [
                    "is_object",
                    "construct_only",
                    "save_always",
                    "default_value",
                    "minimum",
                    "maximum",
                    "translatable",
                    "disable_inline_object",
                    "required",
                    "original_owner_id",
                    "disabled",
                ]:
                    val = property.get(key.replace("_", "-"), None)
                    if val is not None:
                        self.db.execute(
                            f"UPDATE property SET {key}=? WHERE owner_id=? AND property_id=?;",
                            (val, owner_id, property_id)
                        )

            for signal in node.findall("signal"):
                signal_id, detailed = utils.xml_node_get(signal, "id", ["detailed"])
                self.db.execute(
                    "INSERT INTO signal(owner_id, signal_id, detailed) VALUES (?, ?, ?)", (owner_id, signal_id, detailed)
                )

        for provider in node.findall("css-provider"):
            row = self.db.execute("SELECT css_id FROM css WHERE filename=?;", (provider.text,)).fetchone()
            if row:
                (css_id,) = row
                self.db.execute("INSERT INTO css_ui VALUES (?, ?)", (css_id, ui_id))

        self.__populate_ui(ui_id)

    def __load_css_from_node(self, node):
        filename, sha256, priority, is_global = utils.xml_node_get(node, ["filename", "sha256", "priority", "is_global"])

        if filename:
            fullpath, relpath = self.__get_abs_path(filename)
            with open(fullpath) as fd:
                css = fd.read()

                m = hashlib.sha256()
                m.update(css.encode())
                hexdigest = m.hexdigest()

                if sha256 != hexdigest:
                    logger.warning(f"{filename} hash mismatch, file was modified")

                fd.close()
        else:
            content = node.find("content")
            if content:
                css = content.text.encode()
            else:
                raise Exception(_("content tag is missing"))

        css_id = self.db.add_css(filename, priority, is_global, css=css)
        self.__populate_css(css_id)

    def __load_gresource_from_node(self, node):
        filename, sha256 = utils.xml_node_get(node, ["filename", "sha256"])

        if filename:
            root, relpath, hexdigest = self.__parse_xml_file(filename)

            if sha256 != hexdigest:
                logger.warning(f"{filename} hash mismatch, file was modified")

            gresource_id = self.db.import_gresource_from_node(root, relpath)

            cmb_version = self.__get_version_comment_from_root(root)
            self.__file_state[filename] = cmb_version, sha256
        else:
            content = node.find("content")
            if content:
                root = etree.fromstring(content.text.encode())
                gresource_id = self.db.import_gresource_from_node(root, None)
            else:
                raise Exception(_("content tag is missing"))

        self.__populate_gresource(gresource_id)

    def __load(self):
        if self.filename is None or not os.path.isfile(self.filename):
            return

        self.history_enabled = False

        tree = etree.parse(self.filename)
        root = tree.getroot()

        target_tk = root.get("target_tk", None)

        if target_tk != self.target_tk:
            raise Exception(
                _("Can not load a {target} target in {project_target} project.").format(
                    target=target_tk, project_target=self.target_tk
                )
            )

        version = root.get("version", None)
        version = (0, 0, 0) if version is None else utils.parse_version(version)

        if version > self.db.version:
            version = ".".join(map(str, version))
            raise Exception(
                _("File format {version} is not supported by this release,\n"
                  "please update to a newer version to open this file.").format(version=version)
            )

        if version <= (0, 94, 0):
            raise Exception(
                _("Project format {version} is not supported, "
                  "Open/save with Cambalache 0.96.0 to migrate to the new format.").format(version=version)
            )

        ui_graph = {}
        ui_node_template = {}

        css_list = []
        gresourses_list = []

        for child in root.getchildren():
            if child.tag == "ui":
                # Collect template class <-> node relation
                template = child.get("template-class", None)
                if template:
                    ui_node_template[template] = child

                # Collect node dependencies
                dependencies = []
                for requires in child.findall("requires"):
                    dependencies.append(requires.text)

                ui_graph[child] = dependencies
            elif child.tag == "css":
                css_list.append(child)
            elif child.tag == "gresources":
                gresourses_list.append(child)
            elif child.tag == "icontheme-search-path":
                self.icontheme_search_paths.append(child.text)
            else:
                raise Exception(_("Unknown tag {tag} in project file.").format(tag=child.tag))

        for node in css_list:
            self.__load_css_from_node(node)

        for node in gresourses_list:
            self.__load_gresource_from_node(node)

        # Replace dependencies with nodes
        ui_node_graph = {}
        for node, dependencies in ui_graph.items():
            ui_node_graph[node] = [ui_node_template[key] for key in dependencies]

        try:
            ts = TopologicalSorter(ui_node_graph)
            sorted_ui_nodes = tuple(ts.static_order())
        except CycleError as e:
            logger.warning(f"Dependency cycle detected: {e}")
            raise Exception(_("Could not load project because of dependency cycle"))

        # Load UI in topological order
        for node in sorted_ui_nodes:
            self.__load_ui_from_node(node)

        self.history_enabled = True

    def __populate_ui(self, ui_id):
        row = self.db.execute("SELECT * FROM ui WHERE ui_id=?;", (ui_id,)).fetchone()
        ui = self.__add_ui(True, *row)
        ui.notify("n-items")
        return ui

    def __populate_css(self, css_id):
        row = self.db.execute("SELECT * FROM css WHERE css_id=?;", (css_id,)).fetchone()
        return self.__add_css(True, *row)

    def __populate_gresource(self, gresource_id):
        row = self.db.execute("SELECT * FROM gresource WHERE gresource_id=?;", (gresource_id,)).fetchone()
        gresource = self.__add_gresource(True, *row)
        gresource.notify("n-items")
        return gresource

    @GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    def filename(self):
        return self.__filename

    @filename.setter
    def filename(self, value):
        # Ensure extension
        if value and not value.endswith(".cmb"):
            value = value + ".cmb"

        self.__filename = value

    @GObject.Property(type=str, flags=GObject.ParamFlags.READABLE)
    def dirname(self):
        return os.path.dirname(self.__filename) if self.__filename else "."

    def __save_xml_and_update_node(self, node, root, filename, file_object):
        if root is None or filename is None:
            return

        if not os.path.isabs(filename):
            if self.filename is None:
                return

            dirname = os.path.dirname(self.filename)
            fullpath = os.path.join(dirname, filename)
        else:
            fullpath = filename

        interface = root.getroot()
        hexdigest = None
        blueprint_decompiled = None
        use_blp = filename.endswith(".blp")

        if use_blp:
            str_exported = etree.tostring(interface, pretty_print=True, encoding="UTF-8").decode("UTF-8")
            blueprint_decompiled = cmb_blueprint_decompile(str_exported)

        # Ensure directory exists
        os.makedirs(os.path.dirname(fullpath), exist_ok=True)

        original_comment, original_hash = self.__file_state.get(filename, (None, None))
        if original_comment is not None:
            if use_blp:
                m = hashlib.sha256()
                m.update(blueprint_decompiled.encode())
                hexdigest = m.hexdigest()
            else:
                comment = self.__get_version_comment_from_root(interface)
                new_comment = comment.text
                comment.text = original_comment.text

                # Calculate hash
                hash_file = FileHash()
                root.write(hash_file, pretty_print=True, xml_declaration=True, encoding="UTF-8")
                hexdigest = hash_file.hexdigest()
                hash_file.close()

                comment.text = new_comment

        if original_hash is None or original_hash != hexdigest:
            if use_blp:
                with open(fullpath, "wb") as fd:
                    fd.write(blueprint_decompiled.encode())
            else:
                if file_object:
                    file_object.saving = True

                # Dump xml to file
                with open(fullpath, "wb") as fd:
                    hash_file = FileHash(fd)
                    root.write(hash_file, pretty_print=True, xml_declaration=True, encoding="UTF-8")
                    hexdigest = hash_file.hexdigest()
                    hash_file.close()

        # Store filename and hash in node
        utils.xml_node_set(node, "filename", filename)
        utils.xml_node_set(node, "sha256", hexdigest)

    def __save_xml_in_node(self, node, root):
        xml_string = etree.tostring(root, pretty_print=True, encoding="UTF-8").decode("UTF-8")
        content = E.content(etree.CDATA(xml_string))
        node.append(content)

    def __save_ui_and_get_node(self, ui_id, template_id, filename):
        file_object = self.get_object_by_id(ui_id)

        ui = E.ui()

        # Get a list of types declared in the project used by this UI
        for row in self.db.execute(
            """
            SELECT DISTINCT(o.type_id)
            FROM object AS o, type AS t WHERE o.type_id == t.type_id AND o.ui_id=? AND t.library_id IS NULL;
            """,
            (ui_id,)
        ):
            ui.append(E.requires(row[0]))

        # Save CSS UI relation
        for row in self.db.execute(
            "SELECT css.filename FROM css_ui, css WHERE css_ui.css_id=css.css_id AND css_ui.ui_id=?;", (ui_id, )
        ):
            (css_filename,) = row
            provider = E("css-provider", css_filename)
            ui.append(provider)

        # Save custom properties and signals
        if template_id:
            owner = self.db.execute("SELECT name FROM object WHERE ui_id=? AND object_id=?;", (ui_id, template_id)).fetchone()
            owner_id = owner[0] if owner else None

            if owner_id:
                c = self.db.cursor()
                for row in c.execute("SELECT * FROM property WHERE owner_id=? ORDER BY property_id;", (owner_id,)):
                    property = dict(zip([col[0] for col in c.description], row))
                    node = E.property(id=property["property_id"])

                    for key in [
                        "type_id",
                        "is_object",
                        "construct_only",
                        "save_always",
                        "default_value",
                        "minimum",
                        "maximum",
                        "translatable",
                        "disable_inline_object",
                        "required",
                        "original_owner_id",
                        "disabled",
                    ]:
                        utils.xml_node_set(node, key.replace("_", "-"), property.get(key, None))

                    ui.append(node)
                c.close()

                for row in self.db.execute(
                    "SELECT signal_id, detailed FROM signal WHERE owner_id=? ORDER BY signal_id;", (owner_id,)
                ):
                    signal_id, detailed = row
                    node = E.signal(id=signal_id)
                    utils.xml_node_set(node, "detailed", detailed)
                    ui.append(node)

                utils.xml_node_set(ui, "template-class", owner_id)

        # Save UI file
        if filename:
            root = self.db.export_ui(ui_id)
            self.__save_xml_and_update_node(ui, root, filename, file_object)
        else:
            # Embed UI content in project as CDATA
            root = self.db.export_ui(ui_id)
            self.__save_xml_in_node(ui, root.getroot())

        return ui

    def __save_css_and_get_node(self, css_id, filename, css_text, priority, is_global):
        file_object = self.get_css_by_id(css_id)
        if file_object:
            file_object.saving = True

        css = E.css()

        utils.xml_node_set(css, "priority", priority)
        utils.xml_node_set(css, "is_global", is_global)

        if filename:
            # Load from file
            utils.xml_node_set(css, "filename", filename)

            if os.path.isabs(filename):
                fullpath = filename
            elif self.filename:
                dirname = os.path.dirname(self.filename)
                fullpath = os.path.join(dirname, filename)

            with open(fullpath, "w") as fd:
                fd.write(css_text)

                m = hashlib.sha256()
                m.update(css_text.encode())

                utils.xml_node_set(css, "sha256", m.hexdigest())
        else:
            # Load from project
            content = E.content(css_text)
            css.append(content)

        return css

    def __save_gresource_and_get_node(self, gresource_id, filename):
        file_object = self.get_gresource_by_id(gresource_id)
        gresources = E.gresources()

        if filename:
            root = self.db.export_gresource(gresource_id)
            self.__save_xml_and_update_node(gresources, root, filename, file_object)
        else:
            # Embed file contents in project as CDATA
            root = self.db.export_gresource(gresource_id)
            self.__save_xml_in_node(gresources, root.getroot())

        return gresources

    def save(self):
        if self.filename is None:
            return False

        self.db.commit()

        c = self.db.cursor()

        project = E("cambalache-project", version=config.FILE_FORMAT_VERSION, target_tk=self.target_tk)

        project.addprevious(etree.Comment(f" Created with Cambalache {config.VERSION} "))

        for path in self.icontheme_search_paths:
            project.append(E("icontheme-search-path", path))

        # Save GResources
        for row in c.execute("SELECT gresource_id, gresources_filename FROM gresource WHERE resource_type='gresources';"):
            gresource_id, gresources_filename = row
            gresources = self.__save_gresource_and_get_node(gresource_id, gresources_filename)
            project.append(gresources)

        # Save CSS files
        for row in c.execute("SELECT css_id, filename, css, priority, is_global FROM css;"):
            css_id, css_filename, css, priority, is_global = row
            css = self.__save_css_and_get_node(css_id, css_filename, css, priority, is_global)
            project.append(css)

        # Save UI files
        for row in c.execute("SELECT ui_id, template_id, filename FROM ui;"):
            ui_id, template_id, ui_filename = row
            ui = self.__save_ui_and_get_node(ui_id, template_id, ui_filename)
            project.append(ui)

        # Dump project xml to file
        with open(self.filename, "wb") as fd:
            tree = etree.ElementTree(project)
            # FIXME: update DTD
            tree.write(
                fd,
                pretty_print=True,
                xml_declaration=True,
                encoding="UTF-8",
                standalone=False,
                doctype='<!DOCTYPE cambalache-project SYSTEM "cambalache-project.dtd">',
            )
            fd.close()

        c.close()

        return True

    def __get_import_errors(self):
        errors = self.db.errors

        if not len(errors):
            return (None, None)

        msgs = []
        detail_msg = []

        msgs_strings = {
            "unknown-type": (_("one unknown class '{detail}'"), _("{n} unknown classes ({detail})")),
            "unknown-property": (_("one unknown property '{detail}'"), _("{n} unknown properties ({detail})")),
            "unknown-signal": (_("one unknown signal '{detail}'"), _("{n} unknown signals ({detail})")),
            "unknown-tag": (_("one unknown tag '{detail}'"), _("{n} unknown tags ({detail})")),
            "unknown-attr": (_("one unknown attribute '{detail}'"), _("{n} unknown attributes ({detail})")),
            "missing-tag": (_("one missing attribute '{detail}'"), _("{n} missing attributes ({detail})")),
            "not-inline-object": (_("one wrong inline object '{detail}'"), _("{n} wrong inline object ({detail})")),
        }

        detail_strings = {
            "unknown-type": _("xml:{line} unknown class '{detail}'"),
            "unknown-property": _("xml:{line} unknown property '{detail}'"),
            "unknown-signal": _("xml:{line} unknown signal '{detail}'"),
            "unknown-tag": _("xml:{line} unknown tag '{detail}'"),
            "unknown-attr": _("xml:{line} unknown attribute '{detail}'"),
            "missing-tag": _("xml:{line} missing attribute '{detail}'"),
            "not-inline-object": _("xml:{line} not an inline object '{detail}'"),
        }

        detail = []

        # Line by line details
        for error_type in errors:
            error = errors[error_type]

            # Error summary
            n = len(error)
            list = ", ".join(error.keys())
            msgs.append(N_(*msgs_strings[error_type], n).format(n=n, detail=list))

            # Error details
            for key in error:
                lines = error[key]
                for line in lines:
                    detail.append((line, error_type, key))

        # Sort errors by line
        detail = sorted(detail, key=lambda x: x[0])

        # Generate errors by line
        for line, error_type, key in detail:
            detail_msg.append(detail_strings[error_type].format(line=line, detail=key))

        return (msgs, detail_msg)

    def import_file(self, filename, overwrite=False):
        start = time.monotonic()

        self.history_push(_('Import file "{filename}"').format(filename=filename))

        self.foreign_keys = False

        # Remove old UI
        old_ui = None
        if overwrite:
            row = self.db.execute("DELETE FROM ui WHERE filename=? RETURNING ui_id;", (filename,)).fetchone()
            ui_id, = row if row else (None, )
            old_ui = self.get_object_by_id(ui_id)
            self.__file_state.pop(filename)

        # Import file
        if filename.endswith(".blp"):
            root, relpath, hexdigest = self.__parse_blp_file(filename)
        else:
            root, relpath, hexdigest = self.__parse_xml_file(filename)

        ui_id = self.db.import_from_node(root, relpath)
        self.foreign_keys = True

        import_end = time.monotonic()

        # Populate UI
        if old_ui:
            self.__remove_ui(old_ui)

        self.__populate_ui(ui_id)

        self.history_pop()

        logger.info(f"Import took: {import_end - start}")
        logger.info(f"UI update: {time.monotonic() - import_end}")

        # Get parsing errors
        msgs, detail_msg = self.__get_import_errors()
        self.db.errors = None

        ui = self.get_object_by_id(ui_id)

        return (ui, msgs, detail_msg)

    def _list_supported_files(self, dirpath, step_cb=None):
        def read_dir(path):
            retval = []

            with os.scandir(path) as it:
                for entry in it:
                    root, ext = os.path.splitext(entry.name)
                    if ext in [".ui", ".blp", ".css", ".xml"] and entry.is_file():
                        retval.append(entry.path)
                        if step_cb:
                            step_cb()
                    elif entry.is_dir():
                        retval += read_dir(entry.path)

            return retval
        ui_graph = {}
        ui_node_template = {}

        for filename in read_dir(dirpath):
            try:
                if filename.endswith(".blp"):
                    root, relpath, hexdigest = self.__parse_blp_file(filename)
                elif filename.endswith(".ui"):
                    root, relpath, hexdigest = self.__parse_xml_file(filename)
                elif filename.endswith(".css") or filename.endswith(".gresource.xml"):
                    ui_graph[filename] = []

                    if step_cb:
                        step_cb()
                    continue
                else:
                    continue
            except Exception as e:
                logger.warning(e)
                continue

            template = root.find("template")
            if template is not None:
                ui_node_template[template.get("class")] = filename

            dependencies = set()
            for node in root.iterfind(".//object"):
                klass = node.get("class", None)

                if klass in self.type_info:
                    continue

                dependencies.add(klass)

            ui_graph[filename] = list(dependencies)

            if step_cb:
                step_cb()

        # Replace dependencies with nodes
        ui_node_graph = {}
        for filename, dependencies in ui_graph.items():
            ui_node_graph[filename] = [ui_node_template[key] for key in dependencies if key in ui_node_template]

        try:
            ts = TopologicalSorter(ui_node_graph)
            sorted_ui_nodes = list(ts.static_order())
        except CycleError as e:
            logger.warning(f"Dependency cycle detected: {e}")
            raise Exception(_("Could not load project because of dependency cycle"))

        return sorted_ui_nodes

    def import_gresource(self, filename, overwrite=False):
        self.history_push(_('Import GResource "{filename}"').format(filename=filename))

        # Remove old UI
        old_gresource = None
        if overwrite:
            row = self.db.execute(
                "DELETE FROM gresource WHERE resource_type='gresources' AND gresources_filename=? RETURNING gresource_id;",
                (filename, )
            ).fetchone()
            gresource_id, = row if row else (None, )
            old_gresource = self.get_gresource_by_id(gresource_id)
            self.__file_state.pop(filename)

        root, relpath, hexdigest = self.__parse_xml_file(filename)
        gresource_id = self.db.import_gresource_from_node(root, relpath)

        # Populate UI
        if old_gresource:
            self.__remove_gresource(old_gresource)
        self.__populate_gresource(gresource_id)

        self.history_pop()
        return self.get_gresource_by_id(gresource_id)

    def __selection_remove(self, obj):
        if obj not in self.__selection:
            return

        try:
            self.__selection.remove(obj)
        except Exception:
            logger.warning(f"Error removing {obj} from selection", exc_info=True)
        else:
            self.emit("selection-changed")

    def _get_basename_relpath(self, filename):
        if filename is None:
            return (None, None)

        basename = os.path.basename(filename)
        if self.filename:
            dirname = os.path.dirname(self.filename)

            if filename != basename:
                relpath = os.path.relpath(filename, dirname)
            else:
                relpath = basename
        else:
            relpath = None

        return (basename, relpath)

    def __add_ui(
        self,
        emit,
        ui_id,
        template_id=None,
        name=None,
        filename=None,
        description=None,
        copyright=None,
        authors=None,
        license_id=None,
        translation_domain=None,
        comment=None,
        custom_fragment=None,
    ):
        ui = CmbUI(project=self, ui_id=ui_id)

        self._object_id[ui_id] = ui
        self.__update_template_type_info(ui)

        if emit:
            self.emit("ui-added", ui)

        return ui

    def add_ui(self, filename=None, requirements={}):
        basename, relpath = self._get_basename_relpath(filename)

        try:
            self.history_push(_("Add UI {basename}").format(basename=basename or ""))
            ui_id = self.db.add_ui(basename, relpath, requirements)
            self.db.commit()
            self.history_pop()
        except Exception:
            return None
        else:
            return self.__add_ui(True, ui_id, None, basename, relpath)

    def __remove_ui(self, ui):
        self._object_id.pop(ui.ui_id, None)
        self.__selection_remove(ui)
        self.emit("ui-removed", ui)

    def remove_ui(self, ui):
        try:
            self.history_push(_('Remove UI "{name}"').format(name=ui.display_name))

            # Remove template object first, to properly handle instances removal
            template_id = ui.template_id
            if template_id:
                obj = self.get_object_by_id(ui.ui_id, template_id)
                if obj:
                    self.remove_object(obj)

            self.db.execute("DELETE FROM ui WHERE ui_id=?;", (ui.ui_id,))
            self.history_pop()
            self.db.commit()
        except Exception as e:
            logger.warning(f"Error removing UI {ui}: {e}")
        else:
            self.__remove_ui(ui)

    def get_ui_list(self):
        c = self.db.cursor()

        retval = []
        for row in c.execute("SELECT ui_id FROM ui ORDER BY ui_id;"):
            ui = self.get_object_by_id(row[0])

            if ui:
                retval.append(ui)

        c.close()
        return retval

    def __add_css(self, emit, css_id, filename=None, priority=None, is_global=None, css=None):
        css_object = CmbCSS(project=self, css_id=css_id)
        self.__css_id[css_id] = css_object
        if emit:
            self.emit("css-added", css_object)

        return css_object

    def add_css(self, filename=None):
        basename, relpath = self._get_basename_relpath(filename)

        try:
            self.history_push(_("Add CSS {basename}").format(basename=basename or ""))
            if filename and os.path.exists(filename):
                with open(filename, "r") as fd:
                    css = fd.read()
            else:
                css = None

            css_id = self.db.add_css(relpath, css=css)
            self.db.commit()
            self.history_pop()
        except Exception:
            logger.warning("Tried to add CSS", exc_info=True)
            return None
        else:
            return self.__add_css(True, css_id, relpath)

    def __remove_css(self, css):
        self.__css_id.pop(css.css_id, None)
        self.__selection_remove(css)
        self.emit("css-removed", css)

    def remove_css(self, css):
        try:
            self.history_push(_('Remove CSS "{name}"').format(name=css.display_name))
            self.db.execute("DELETE FROM css WHERE css_id=?;", (css.css_id,))
            self.history_pop()
            self.db.commit()
            self.__remove_css(css)
        except Exception as e:
            logger.warning(e)

    def __add_gresource(
        self,
        emit,
        gresource_id,
        resource_type,
        parent_id=None,
        position=None,
        gresources_filename=None,
        gresource_prefix=None,
        file_filename=None,
        file_compressed=None,
        file_preprocess=None,
        file_alias=None,
    ):
        gresource = CmbGResource(project=self, gresource_id=gresource_id, resource_type=resource_type)
        self.__gresource_id[gresource_id] = gresource
        if emit:
            self.emit("gresource-added", gresource)

        return gresource

    def add_gresource(
        self,
        resource_type,
        parent_id=None,
        gresources_filename=None,
        gresource_prefix=None,
        file_filename=None,
        file_compressed=None,
        file_preprocess=None,
        file_alias=None,
    ):
        try:
            if resource_type == "gresources":
                basename, relpath = self._get_basename_relpath(gresources_filename)
                self.history_push(_("Add GResource {basename}").format(basename=basename))
            elif resource_type == "gresource":
                self.history_push(_("Add GResource prefix {prefix}").format(prefix=gresource_prefix))
            elif resource_type == "file":
                self.history_push(_("Add GResource file {filename}").format(filename=file_filename))

            gresource_id = self.db.add_gresource(
                resource_type,
                parent_id=parent_id,
                gresources_filename=gresources_filename,
                gresource_prefix=gresource_prefix,
                file_filename=file_filename,
                file_compressed=file_compressed,
                file_preprocess=file_preprocess,
                file_alias=file_alias,
            )
            self.db.commit()
            self.history_pop()
        except Exception:
            logger.warning("Tried to add GResource", exc_info=True)
            return None
        finally:
            gresource = self.__add_gresource(True, gresource_id, resource_type)
            gresource._update_new_parent()
            return gresource

    def __remove_gresource(self, gresource):
        if gresource is None:
            logger.warning("Tried to remove a None GResource", exc_info=True)
            return

        self.__selection_remove(gresource)
        self.__gresource_id.pop(gresource.gresource_id, None)
        self.emit("gresource-removed", gresource)

    def remove_gresource(self, gresource):
        try:
            parent_id = gresource.parent_id

            gresource._save_last_known_parent_and_position()
            self.history_push(_('Remove GResource "{name}"').format(name=gresource.display_name))
            self.db.execute("DELETE FROM gresource WHERE gresource_id=?;", (gresource.gresource_id,))

            # Update position
            if parent_id:
                self.db.update_gresource_children_position(parent_id)

            self.history_pop()
            self.db.commit()
        except Exception as e:
            logger.warning(f"Error removing gresource {e}", exc_info=True)
        finally:
            self.__remove_gresource(gresource)
            gresource._remove_from_old_parent()

    def get_css_providers(self):
        return list(self.__css_id.values())

    def __add_object(
        self,
        emit,
        ui_id,
        object_id,
        obj_type,
        name=None,
        parent_id=None,
        internal=None,
        child_type=None,
        comment=None,
        position=0,
        custom_fragment=None,
        custom_child_fragment=None,
    ):
        obj = CmbObject(project=self, ui_id=ui_id, object_id=object_id, info=self.type_info.get(obj_type))
        self._object_id[f"{ui_id}.{object_id}"] = obj

        if emit:
            self.emit("object-added", obj)

        return obj

    def _check_can_add(self, obj_type, parent_type):
        if constants.EXTERNAL_TYPE in [obj_type, parent_type]:
            return False

        obj_info = self.type_info.get(obj_type, None)
        parent_info = self.type_info.get(parent_type, None)

        if obj_info is None or parent_info is None:
            return False

        if parent_info.is_a("GtkWidget"):
            # In Gtk 3 only GtkWidget can be a child
            # on Gtk 4 on the other hand there are types that can have GObjects as children
            if self.target_tk == "gtk+-3.0" and not obj_info.is_a("GtkWidget"):
                return False

            # GtkWindow can not be a child
            if obj_info.is_a("GtkWindow"):
                return False

            return parent_info.layout == "container"
        else:
            return True

    def add_object(
        self,
        ui_id,
        obj_type,
        name=None,
        parent_id=None,
        layout=None,
        position=None,
        child_type=None,
        inline_property=None,
        internal=None,
        inline_binding_expression=False,
    ):
        if parent_id:
            parent = self.get_object_by_id(ui_id, parent_id)
            if parent is None:
                return None

            if not self._check_can_add(obj_type, parent.type_id):
                return None

        obj_name = name if name is not None else obj_type

        try:
            self.history_push(_("Add object {name}").format(name=obj_name))
            object_id = self.db.add_object(
                ui_id,
                obj_type,
                name,
                parent_id,
                layout=layout,
                position=position,
                inline_property=inline_property,
                child_type=child_type,
                internal=internal,
                inline_binding_expression=inline_binding_expression,
            )
            self.history_pop()
            self.db.commit()
        except Exception as e:
            logger.warning(f"Error adding object {obj_name}: {e}")
            return None
        finally:
            obj = self.__add_object(True, ui_id, object_id, obj_type, name, parent_id, position=position)
            obj._update_new_parent()
            return obj

    def __remove_object(self, obj, template_ui=None, template_instances=None):
        ui_id = obj.ui_id
        object_id = obj.object_id

        if template_ui is not None:
            self.__update_template_type_info(template_ui)

        # Remove all object of this template class
        if template_instances is not None:
            for tmpl_obj in template_instances:
                self.__remove_object(tmpl_obj)

        self.__selection_remove(obj)

        self._object_id.pop(f"{ui_id}.{object_id}", None)

        self.emit("object-removed", obj)

    def remove_object(self, obj, allow_internal_removal=False):
        if not allow_internal_removal and obj.internal:
            raise Exception(_("Internal objects can not be removed"))

        try:
            was_selected = obj in self.__selection
            parent = obj.parent

            template_ui = None
            template_instances = None

            ui_id = obj.ui_id
            object_id = obj.object_id
            parent_id = obj.parent_id

            # We need to call this before removing an object from the DB to know where is was in the GListModel
            obj._save_last_known_parent_and_position()

            if obj.ui.template_id == obj.object_id:
                template_ui = obj.ui
                template_instances = []

                for row in self.db.execute("SELECT ui_id, object_id FROM object WHERE type_id=?;", (obj.name,)):
                    obj_ui_id, obj_object_id = row
                    tmpl_obj = self.get_object_by_id(obj_ui_id, obj_object_id)
                    if tmpl_obj:
                        tmpl_obj._save_last_known_parent_and_position()
                        template_instances.append(tmpl_obj)

            name = obj.name if obj.name is not None else obj.type_id
            self.history_push(_("Remove object {name}").format(name=name))

            if template_instances is not None and len(template_instances):
                self.db.execute("DELETE FROM object WHERE type_id=?;", (obj.name,))

            self.db.execute("DELETE FROM object WHERE ui_id=? AND object_id=?;", (ui_id, object_id))

            # Update position
            self.db.update_children_position(ui_id, parent_id)

            self.history_pop()
            self.db.commit()
        except Exception as e:
            logger.warning(f"Error removing object {obj}: {e}")
        finally:
            self.__remove_object(obj, template_ui, template_instances)
            obj._remove_from_old_parent()

            # Select parent if removed object was selected
            if was_selected and parent:
                self.set_selection([parent])

    def get_selection(self):
        return self.__selection

    def set_selection(self, selection):
        if self._ignore_selection or not isinstance(selection, list) or self.__selection == selection:
            return

        for obj in selection:
            if isinstance(obj, CmbUI):
                pass
            elif isinstance(obj, CmbObject):
                pass
            elif isinstance(obj, CmbCSS):
                pass
            elif isinstance(obj, CmbGResource):
                pass
            else:
                logger.warning(f"Unknown object type {obj}")
                return

        self.__selection = selection
        self.emit("selection-changed")

    def get_object_by_key(self, key):
        if type(key) is int:
            return self._object_id.get(key, None)

        if type(key) is not str:
            logger.warning(f"Wrong key type {type(key)} {key}", exc_info=True)

        obj = self._object_id.get(key, None)

        if obj:
            return obj

        tokens = key.split(".")

        # Check all tokens are numeric
        for token in tokens:
            if not token.isnumeric():
                logger.warning(f"Error in object key {key}", exc_info=True)
                return None

        ui_id, object_id = [int(x) for x in tokens]

        row = self.db.execute("SELECT * FROM object WHERE ui_id=? AND object_id=?;", (ui_id, object_id)).fetchone()
        if row:
            return self.__add_object(False, *row)

        # FIXME: return dummy object?
        return None

    def get_object_by_id(self, ui_id, object_id=None):
        if object_id is None:
            return self.get_object_by_key(ui_id)

        return self.get_object_by_key(f"{ui_id}.{object_id}")

    def get_object_by_name(self, ui_id, name):
        c = self.db.execute("SELECT object_id FROM object WHERE ui_id=? AND name=?;", (ui_id, name))
        row = c.fetchone()
        return self.get_object_by_key(f"{ui_id}.{row[0]}") if row else None

    def get_ui_by_filename(self, filename):
        relpath = filename

        if self.filename:
            dirname = os.path.dirname(self.filename)
            relpath = os.path.relpath(filename, dirname)

        c = self.db.execute("SELECT ui_id FROM ui WHERE filename=?;", (relpath,))
        row = c.fetchone()
        return self.get_object_by_key(row[0]) if row else None

    def get_css_by_id(self, css_id):
        return self.__css_id.get(css_id, None)

    def get_gresource_by_id(self, key):
        obj = self.__gresource_id.get(key, None)

        if obj:
            return obj

        row = self.db.execute("SELECT * FROM gresource WHERE gresource_id=?;", (key,)).fetchone()
        return self.__add_gresource(False, *row) if row else None

    def __undo_redo_property_notify(self, obj, layout, prop, owner_id, property_id):
        properties = obj.layout_dict if layout else obj.properties_dict
        p = properties.get(property_id, None)

        if p and p.owner_id == owner_id and p.property_id == property_id:
            p.notify(prop)

    def __undo_redo_do(self, undo, update_objects=None):
        def get_object_position(table, row):
            if table == "object":
                ui_id, parent_id, position = row[0], row[4], row[8]
                parent = self.get_object_by_id(ui_id, parent_id)
                return parent, position
            elif table == "gresource":
                parent_id, position = row[2], row[3]
                parent = self.get_gresource_by_id(parent_id)
                return parent, position

            return None, None

        c = self.db.cursor()

        # Get last command
        command, range_id, table, columns, table_pk, old_values, new_values = c.execute(
            "SELECT command, range_id, table_name, columns, table_pk, old_values, new_values FROM history WHERE history_id=?",
            (self.history_index,),
        ).fetchone()

        columns = json.loads(columns) if columns else None
        table_pk = json.loads(table_pk) if table_pk else None
        old_values = json.loads(old_values) if old_values else None
        new_values = json.loads(new_values) if new_values else None

        # Undo or Redo command
        if command == "INSERT":
            if table in ["object", "gresource"]:
                parent, position = get_object_position(table, new_values)

                if undo:
                    update_objects.append((parent, position, 1, 0))
                else:
                    update_objects.append((parent, position, 0, 1))

            if undo:
                self.db.history_delete(table, table_pk)
            else:
                self.db.history_insert(table, new_values)

            self.__undo_redo_update_insert_delete(c, undo, command, table, columns, table_pk, old_values, new_values)
        elif command == "DELETE":
            if table in ["object", "gresource"]:
                parent, position = get_object_position(table, old_values)

                if undo:
                    update_objects.append((parent, position, 0, 1))
                else:
                    update_objects.append((parent, position, 1, 0))

            if undo:
                self.db.history_insert(table, old_values)
            else:
                self.db.history_delete(table, table_pk)

            self.__undo_redo_update_insert_delete(c, undo, command, table, columns, table_pk, old_values, new_values)
        elif command == "UPDATE":
            # parent_id and position have to change together because their are part of a unique index
            if update_objects is not None and table == "object" and "position" in columns and "parent_id" in columns:
                old_parent, old_position = get_object_position(table, old_values)
                new_parent, new_position = get_object_position(table, new_values)

                if undo:
                    if old_position >= 0:
                        update_objects.append((old_parent, old_position, 0, 1))
                    if new_position >= 0:
                        update_objects.append((new_parent, new_position, 1, 0))
                else:
                    if new_position >= 0:
                        update_objects.append((new_parent, new_position, 0, 1))
                    if old_position >= 0:
                        update_objects.append((old_parent, old_position, 1, 0))
            elif table == "gresource":
                # TODO
                pass

            if undo:
                self.db.history_update(table, columns, table_pk, old_values)
            else:
                self.db.history_update(table, columns, table_pk, new_values)

            self.__undo_redo_update_update(c, undo, command, table, columns, table_pk, old_values, new_values)
        elif command == "PUSH" or command == "POP":
            pass
        else:
            logger.warning(f"Error unknown history command {command}")

        c.close()

    def __undo_redo_update_update(self, c, undo, command, table, columns, pk, old_values, new_values):
        if table is None or command != "UPDATE":
            return

        for column in columns:
            # Update tree model and emit signals
            # We can not easily implement this using triggers because they are called
            # even if the transaction is rollback because of a FK constraint
            if table == "object":
                obj = self.get_object_by_id(pk[0], pk[1])
                if obj:
                    obj.notify(column)
            elif table == "object_property":
                obj = self.get_object_by_id(pk[0], pk[1])
                self.__undo_redo_property_notify(obj, False, column, pk[2], pk[3])
            elif table == "object_layout_property":
                child = self.get_object_by_id(pk[0], pk[2])
                self.__undo_redo_property_notify(child, True, column, pk[3], pk[4])
            elif table == "object_signal":
                obj = self.get_object_by_id(old_values[1], old_values[2])
                if obj:
                    signal = obj.signals_dict[pk[0]]
                    if signal:
                        signal.notify(column)
            elif table == "object_data":
                obj = self.get_object_by_id(pk[0], pk[1])
                if obj:
                    data = obj.data_dict.get(f"{pk[2]}.{pk[4]}", None)
                    if data:
                        data.notify(column)
            elif table == "object_data_arg":
                obj = self.get_object_by_id(pk[0], pk[1])
                if obj:
                    data = obj.data_dict.get(f"{pk[2]}.{pk[4]}", None)
                    if data:
                        data._arg_changed(pk[5])
                        data.notify(column)
            elif table == "ui":
                obj = self.get_object_by_id(pk[0])
                if obj:
                    obj.notify(column)
            elif table == "ui_library":
                ui = self.get_object_by_id(pk[0])
                if ui:
                    ui._library_changed(pk[1])
            elif table == "css":
                obj = self.get_css_by_id(pk[0])
                if obj:
                    obj.notify(column)
            elif table == "gresource":
                obj = self.get_gresource_by_id(pk[0])
                if obj:
                    obj.notify(column)

    def __undo_redo_update_insert_delete(self, c, undo, command, table, columns, pk, old_values, new_values):
        if table is None:
            return

        removing = (command == "INSERT" and undo) or (command == "DELETE") and not undo
        row = old_values if command == "DELETE" else new_values

        if table == "object_property":
            obj = self.get_object_by_id(pk[0], pk[1])
            self.__undo_redo_property_notify(obj, False, "value", pk[2], pk[3])
        elif table == "object_layout_property":
            child = self.get_object_by_id(pk[0], pk[2])
            self.__undo_redo_property_notify(child, True, "value", pk[3], pk[4])
        elif table in ["object", "ui", "css", "gresource"]:
            if removing:
                if table == "object":
                    obj = self.get_object_by_id(pk[0], pk[1])
                    self.__remove_object(obj)
                elif table == "ui":
                    obj = self.get_object_by_id(pk[0])
                    self.__remove_ui(obj)
                elif table == "css":
                    obj = self.get_css_by_id(pk[0])
                    self.__remove_css(obj)
                elif table == "gresource":
                    obj = self.get_gresource_by_id(pk[0])
                    self.__remove_gresource(obj)
            else:
                if table == "ui":
                    self.__add_ui(True, *row)
                elif table == "object":
                    obj = self.__add_object(True, *row)

                    if obj.ui.template_id == obj.object_id:
                        self.__update_template_type_info(obj.ui)
                elif table == "css":
                    self.__add_css(True, *row)
                elif table == "gresource":
                    self.__add_gresource(True, *row)
        elif table in ["object_signal", "object_data", "object_data_arg"]:
            if table == "object_signal":
                obj = self.get_object_by_id(row[1], row[2])
                if removing:
                    for signal in obj.signals:
                        if signal.signal_pk == row[0]:
                            obj._remove_signal(signal)
                            break
                else:
                    obj._add_signal(row[0], row[3], row[4], row[5], row[6], row[7], row[8], row[9])
            elif table == "object_data":
                obj = self.get_object_by_id(row[0], row[1])

                if removing:
                    data = obj.data_dict.get(f"{row[2]}.{row[4]}", None)
                    if data:
                        if data.parent:
                            data.parent._remove_child(data)
                        else:
                            obj._remove_data(data)
                else:
                    owner_id, data_id, id, parent_id = row[2], row[3], row[4], row[6]

                    parent = obj.data_dict.get(f"{owner_id}.{parent_id}", None)

                    if parent:
                        parent._add_child(owner_id, data_id, id)
                    else:
                        info = self.type_info.get(owner_id)
                        taginfo = None

                        if info:
                            r = self.db.execute(
                                "SELECT key FROM type_data WHERE owner_id=? AND data_id=?;",
                                (owner_id, data_id)
                            ).fetchone()

                            data_key = r[0] if r else None
                            if data_key:
                                taginfo = info.get_data_info(data_key)

                        obj._add_data(owner_id, data_id, id, info=taginfo)
            elif table == "object_data_arg":
                obj = self.get_object_by_id(pk[0], pk[1])
                if obj:
                    data = obj.data_dict.get(f"{pk[2]}.{pk[4]}", None)
                    if data:
                        data._arg_changed(pk[5])
        elif table == "css_ui":
            obj = self.get_css_by_id(pk[0])
            if obj:
                obj.notify("provider-for")
        elif table == "ui_library":
            ui = self.get_object_by_id(pk[0])
            if ui:
                ui._library_changed(pk[1])

    def __db_freeze(self):
        self.history_enabled = False
        self.db.foreign_keys = False
        self.db.ignore_check_constraints = True

    def __db_thaw(self):
        self.db.foreign_keys = True
        self.db.ignore_check_constraints = False
        self.history_enabled = True

    def clear_history(self):
        self.history_index = 0
        self.db.clear_history()
        self.emit("changed")

    def __undo_redo(self, undo):
        selection = self.get_selection()

        command, range_id, table = self.db.execute(
            "SELECT command, range_id, table_name FROM history WHERE history_id=?", (self.history_index,)
        ).fetchone()

        update_parents = []

        try:
            self.__db_freeze()

            if command == "POP":
                if undo:
                    self.history_index -= 1
                    while range_id < self.history_index:
                        self.__undo_redo_do(True, update_parents)
                        self.history_index -= 1
                else:
                    logger.warning("Error on undo/redo stack: we should not try to redo a POP command")
            elif command == "PUSH":
                if not undo:
                    while range_id > self.history_index:
                        self.history_index += 1
                        self.__undo_redo_do(undo, update_parents)
                else:
                    logger.warning("Error on undo/redo stack: we should not try to undo a PUSH command")
            else:
                # Undo / Redo in DB
                self.__undo_redo_do(undo, update_parents)

            self.__db_thaw()
        except sqlite3.Error as e:
            self.__db_thaw()
            self.clear_history()
            raise e

        # Compress update commands
        compressed_list = []
        prev_parent, prev_position, prev_removed, prev_added = (None, None, 0, 0)

        for i, tuples in enumerate(update_parents):
            parent, position, removed, added = tuples

            # Compress removed and added if possible
            if prev_parent == parent and prev_position == position and prev_removed + removed == 1 and prev_added + added == 1:
                # Compress
                compressed_list.pop()
                compressed_list.append((parent, position, 1, 1))
                prev_parent, prev_position, prev_removed, prev_added = (None, None, 0, 0)
            else:
                prev_parent, prev_position, prev_removed, prev_added = (parent, position, removed, added)
                compressed_list.append((parent, position, removed, added))

        if not undo:
            compressed_list.reverse()

        # Update GListModel
        for parent, position, removed, added in compressed_list:
            # Ignore negative positions, they are used to avoid unique constrain errors on reparenting
            if position < 0:
                continue

            parent.items_changed(position, removed, added)
            if removed != added:
                parent.notify("n-items")

        self.set_selection(selection)

    def _get_object_list_names(self, ui_id, object_list):
        if object_list is None or object_list == "":
            return []

        # Object list stored as a list of integers separated with a ,
        ids = [int(id.strip()) for id in object_list.split(",")]
        names = []

        for id in ids:
            obj = self.get_object_by_id(ui_id, id)
            if obj:
                names.append(obj.name)

        return names

    def get_undo_redo_msg(self):
        c = self.db.cursor()

        def get_type_data_name(owner_id, data_id):
            c.execute("SELECT key FROM type_data WHERE owner_id=? AND data_id=?;", (owner_id, data_id))
            row = c.fetchone()
            return f"{owner_id}:{row[0]}" if row is not None else f"{owner_id}:{data_id}"

        def get_msg_vars(table, column, data):
            retval = {"ui": "", "css": "", "obj": "", "prop": "", "value": "", "field": column}

            if data is None:
                return retval

            if table == "ui":
                ui_id = data[0]
                ui = self.get_object_by_id(ui_id)
                retval["ui"] = ui.display_name if ui else CmbUI.get_display_name(ui_id, data[3])
            elif table == "ui_library":
                ui_id = data[0]
                ui = self.get_object_by_id(ui_id)
                retval["ui"] = ui.display_name if ui else CmbUI.get_display_name(ui_id, None)
                retval["lib"] = data[1]
                retval["version"] = data[2]
            elif table == "css":
                retval["css"] = data[1]
            elif table == "css_ui":
                css_id = data[0]
                ui_id = data[1]

                css = self.get_css_by_id(css_id)
                ui = self.get_object_by_id(ui_id)

                retval["css"] = css.display_name if css else CmbCSS.get_display_name(css_id, None)
                retval["ui"] = ui.display_name if ui else CmbUI.get_display_name(ui_id, None)
            else:
                if table == "object_signal":
                    ui_id = data[1]
                    object_id = data[2]
                else:
                    ui_id = data[0]
                    object_id = data[1]

                if table == "object":
                    retval["obj"] = data[3] if data[3] is not None else data[2]
                else:
                    c.execute("SELECT type_id, name FROM object WHERE ui_id=? AND object_id=?", (ui_id, object_id))
                    row = c.fetchone()
                    if row is not None:
                        type_id, name = row
                        retval["obj"] = name if name is not None else type_id

                if table == "object_property":
                    property_id = data[3]

                    retval["prop"] = f'"{property_id}" {column}' if column else property_id
                    # Translators: This refers to "properties" in object property undo/redo messages
                    retval["prop_type"] = _("property")

                    if column == "translatable":
                        retval["value"] = _("True") if data[5] else _("False")
                    elif column == "comment":
                        retval["value"] = f'"{data[6]}"'
                    elif column == "translation_context":
                        retval["value"] = f'"{data[7]}"'
                    elif column == "translation_comments":
                        retval["value"] = f'"{data[8]}"'
                    else:
                        ui_id = data[0]
                        object_id = data[1]
                        owner_id = data[2]

                        value = data[4]

                        if CmbPropertyInfo.type_is_accessible(owner_id):
                            retval["prop_type"] = {
                                # Translators: This refers to accessibility properties in object property undo/redo messages
                                "CmbAccessibleProperty": _("a11y property"),
                                # Translators: This refers to accessibility relations in object property undo/redo messages
                                "CmbAccessibleRelation": _("a11y relation"),
                                # Translators: This refers to accessibility states in object property undo/redo messages
                                "CmbAccessibleState": _("a11y state"),
                                # Translators: This refers to accessibility actions in object property undo/redo messages
                                "CmbAccessibleAction": _("a11y action"),
                            }.get(owner_id, None)

                            retval["prop"] = CmbPropertyInfo.accessible_property_remove_prefix(owner_id, property_id)

                            if (
                                (info := self.type_info.get(owner_id, None))
                                and (pinfo := info.properties.get(property_id, None))
                                and pinfo.type_id == "CmbAccessibleList"
                            ):
                                names = self._get_object_list_names(ui_id, value)
                                retval["value"] = ", ".join(names)
                            else:
                                retval["value"] = value
                        else:
                            retval["prop"] = f'"{property_id}"'
                            retval["value"] = value
                elif table == "object_layout_property":
                    retval["prop"] = f'"{data[4]}" {column}'

                    if column == "translatable":
                        retval["value"] = _("True") if data[5] else _("False")
                    elif column == "comment":
                        retval["value"] = f'"{data[7]}"'
                    elif column == "translation_context":
                        retval["value"] = f'"{data[8]}"'
                    elif column == "translation_comments":
                        retval["value"] = f'"{data[9]}"'
                    else:
                        retval["prop"] = f'"{data[4]}"'
                        retval["value"] = data[5]
                elif table == "object_signal":
                    retval["signal"] = data[4]
                elif table == "object_data":
                    retval["data"] = get_type_data_name(data[2], data[3])
                    retval["value"] = data[5]
                elif table == "object_data_arg":
                    data_name = get_type_data_name(data[2], data[3])
                    retval["data"] = f"{data_name} {data[5]}"
                    retval["value"] = data[6]

            return retval

        def get_msg(index):
            cmd = c.execute(
                """
                SELECT command, range_id, table_name, columns, message, old_values, new_values
                FROM history
                WHERE history_id=?
                """,
                (index,),
            ).fetchone()

            if cmd is None:
                return None
            command, range_id, table, columns, message, old_values, new_values = cmd

            columns = json.loads(columns) if columns else []

            if message is not None:
                return message

            if command == "DELETE":
                values = json.loads(old_values) if old_values else None
            else:
                values = json.loads(new_values) if new_values else None

            msg = (
                {
                    "ui": {
                        "INSERT": _("Create UI {ui}"),
                        "DELETE": _("Remove UI {ui}"),
                        "UPDATE": _("Update {field} of UI {ui}"),
                    },
                    "ui_library": {
                        "INSERT": _("Set {ui} {lib} to {version}"),
                        "DELETE": _("Remove {ui} {lib}"),
                        "UPDATE": _("Update {lib} of UI {ui} to {version}"),
                    },
                    "css": {
                        "INSERT": _("Add CSS provider {css}"),
                        "DELETE": _("Remove CSS provider {css}"),
                        "UPDATE": _("Update {field} of CSS provider {css}"),
                    },
                    "css_ui": {
                        "INSERT": _("Add {ui} to CSS provider {css}"),
                        "DELETE": _("Remove {ui} from CSS provider {css}"),
                    },
                    "object": {
                        "INSERT": _("Create object {obj}"),
                        "DELETE": _("Remove object {obj}"),
                        "UPDATE": _("Update {field} of object {obj}"),
                    },
                    "object_property": {
                        # Translators: This text is used for object properties undo/redo messages
                        # prop_type could be "property", "a11y property", "a11y relation", "a11y state" or "a11y action"
                        "INSERT": _("Set {obj} {prop} {prop_type} to {value}"),
                        "DELETE": _("Unset {obj} {prop} {prop_type}"),
                        "UPDATE": _("Update {obj} {prop} {prop_type} to {value}"),
                    },
                    "object_layout_property": {
                        "INSERT": _("Set {obj} {prop} layout property to {value}"),
                        "DELETE": _("Unset {obj} {prop} layout property"),
                        "UPDATE": _("Update {obj} {prop} layout property to {value}"),
                    },
                    "object_signal": {
                        "INSERT": _("Add {signal} signal to {obj}"),
                        "DELETE": _("Remove {signal} signal from {obj}"),
                        "UPDATE": _("Update {signal} signal of {obj}"),
                    },
                    "object_data": {
                        "INSERT": _("Add {data}={value} to {obj}"),
                        "DELETE": _("Remove {data}={value} from {obj}"),
                        "UPDATE": _("Update {data} of {obj} to {value}"),
                    },
                    "object_data_arg": {
                        "INSERT": _("Add {data}={value} to {obj}"),
                        "DELETE": _("Remove {data}={value} from {obj}"),
                        "UPDATE": _("Update {data} of {obj} to {value}"),
                    },
                }
                .get(table, {})
                .get(command, None)
            )

            if msg is None:
                return None

            if columns:
                msgs = []
                for column in columns:
                    msgs.append(msg.format(**get_msg_vars(table, column, values)))

                return "\n".join(msgs) if len(msgs) > 1 else (msgs[0] if msgs else None)
            else:
                return msg.format(**get_msg_vars(table, None, values))

        undo_msg = get_msg(self.history_index)
        redo_msg = get_msg(self.history_index + 1)

        c.close()

        return (undo_msg, redo_msg)

    def undo(self):
        if self.history_index == 0:
            return

        self.__undo_redo(True)
        self.history_index -= 1
        self.emit("changed")

    def redo(self):
        if self.history_index >= self.history_index_max:
            return

        self.history_index += 1
        self.__undo_redo(False)

    def get_type_properties(self, name):
        info = self.type_info.get(name, None)
        return info.properties if info else None

    def __object_update_row(self, ui, object_id):
        obj = self.get_object_by_id(ui.ui_id, object_id)
        if obj:
            obj.notify("display-name")
        ui.notify("display-name")

    def __update_template_type_info(self, ui):
        template_info, template_id = self.__template_info.get(ui.ui_id, (None, None))

        if ui.template_id:
            c = self.db.execute("SELECT type_id, name FROM object WHERE ui_id=? AND object_id=?;", (ui.ui_id, ui.template_id))
            row = c.fetchone()

            if row is None:
                return

            parent_id, type_id = row

            # Ignore templates without a name set
            if type_id is None:
                return

            if template_info is None:
                parent_info = self.type_info.get(parent_id, None)

                info = CmbTypeInfo(
                    project=self,
                    type_id=type_id,
                    parent_id=parent_id,
                    # NOTE: we assume it is derivable
                    derivable=1,
                    library_id=None,
                    version=None,
                    deprecated_version=None,
                    abstract=None,
                    layout=parent_info.layout,
                    category=parent_info.category,
                    workspace_type=parent_info.workspace_type,
                )

                # Set parent back reference
                info.parent = parent_info

                self.type_info[type_id] = info
                self.__template_info[ui.ui_id] = (type_id, ui.template_id)

                self.emit("type-info-added", info)
            elif type_id and template_info != type_id:
                # name changed
                info = self.type_info.pop(template_info)

                self.type_info[type_id] = info
                self.__template_info[ui.ui_id] = (type_id, ui.template_id)

                # Update object property since its not read from DB each time
                info.type_id = type_id
                info.parent_id = parent_id
                info.parent = self.type_info.get(parent_id, None)
                self.emit("type-info-changed", info)

            self.__object_update_row(ui, ui.template_id)

        if template_info and template_info in self.type_info:
            info = self.type_info.pop(template_info)
            self.__template_info.pop(ui.ui_id)
            self.emit("type-info-removed", info)
            self.__object_update_row(ui, template_id)

    def _ui_changed(self, ui, field):
        if field == "template-id":
            self.__update_template_type_info(ui)

        self.emit("ui-changed", ui, field)

    def _ui_library_changed(self, ui, lib):
        self.emit("ui-library-changed", ui, lib)

    def _object_changed(self, obj, field):
        # Update template type id
        if field == "name":
            ui = obj.ui
            if obj.object_id == ui.template_id:
                self.__update_template_type_info(ui)

        self.emit("object-changed", obj, field)

    def _object_property_changed(self, obj, prop):
        self.emit("object-property-changed", obj, prop)

    def _object_layout_property_changed(self, obj, child, prop):
        self.emit("object-layout-property-changed", obj, child, prop)

    def _object_property_binding_changed(self, obj, prop):
        self.emit("object-property-binding-changed", obj, prop)

    def _object_signal_removed(self, obj, signal):
        self.emit("object-signal-removed", obj, signal)

    def _object_signal_added(self, obj, signal):
        self.emit("object-signal-added", obj, signal)

    def _object_signal_changed(self, obj, signal):
        self.emit("object-signal-changed", obj, signal)

    def _object_data_data_removed(self, parent, data):
        self.emit("object-data-data-removed", parent, data)

    def _object_data_data_added(self, parent, data):
        self.emit("object-data-data-added", parent, data)

    def _object_data_arg_changed(self, data, key):
        self.emit("object-data-arg-changed", data, key)

    def _object_data_removed(self, obj, data):
        self.emit("object-data-removed", obj, data)

    def _object_data_added(self, obj, data):
        self.emit("object-data-added", obj, data)

    def _object_data_changed(self, data):
        self.emit("object-data-changed", data)

    def _object_child_reordered(self, obj, child, old_position, new_position):
        self.emit("object-child-reordered", obj, child, old_position, new_position)

    def _css_changed(self, obj, field):
        self.emit("css-changed", obj, field)

    def _gresource_changed(self, obj, field):
        self.emit("gresource-changed", obj, field)

    def db_move_to_fs(self, filename):
        self.db.move_to_fs(filename)

    def history_push(self, message):
        if not self.history_enabled:
            return

        # Make sure we clear history on new push
        self.db.clear_history()

        self.db.execute(
            "INSERT INTO history (history_id, command, message) VALUES (?, 'PUSH', ?)",
            (self.history_index_max + 1, message),
        )

    def history_pop(self):
        if not self.history_enabled:
            return

        self.db.execute("INSERT INTO history (history_id, command) VALUES (?, 'POP')", (self.history_index_max + 1,))
        self.emit("changed")

    def copy(self):
        # TODO: filter children out
        selection = [(o.ui_id, o.object_id) for o in self.__selection if isinstance(o, CmbObject)]
        self.db.clipboard_copy(selection)

    def paste(self):
        if len(self.__selection) == 0:
            return

        c = self.db.cursor()

        obj = self.__selection[0]
        ui_id = obj.ui_id
        parent_id = obj.object_id if isinstance(obj, CmbObject) else None

        self.history_push(_("Paste clipboard to {name}").format(name=obj.display_name))

        new_objects = self.db.clipboard_paste(ui_id, parent_id)

        self.history_pop()
        self.db.commit()

        # Update UI objects
        for object_id in new_objects:
            for child_id in new_objects[object_id]:
                c.execute("SELECT * FROM object WHERE ui_id=? AND object_id=?;", (ui_id, child_id))
                self.__add_object(False, *c.fetchone())

            obj = self.get_object_by_id(ui_id, object_id)
            self.emit("object-added", obj)
            obj._update_new_parent()

        c.close()

    def cut(self):
        # TODO: filter children out
        selection = [o for o in self.__selection if isinstance(o, CmbObject)]

        # Copy to clipboard
        self.copy()

        # Delete from project
        try:
            n_objects = len(selection)

            if n_objects == 1:
                obj = selection[0]
                self.history_push(_("Cut object {name}").format(name=obj.display_name))
            else:
                self.history_push(_("Cut {n_objects} object").format(n_objects=n_objects))

            for obj in selection:
                self.remove_object(obj)

            self.history_pop()
            self.db.commit()
        except Exception:
            # TODO: rollback whole transaction?
            pass

    def add_parent(self, type_id, obj):
        try:
            self.history_push(_("Add {type_id} parent to {name}").format(name=obj.display_name, type_id=type_id))

            ui_id = obj.ui_id
            object_id = obj.object_id
            grand_parent_id = obj.parent_id or None
            position = obj.position
            list_position = obj.list_position
            child_type = obj.type
            inline_property_id = obj.inline_property_id
            binding_expression_property_id = obj.binding_expression_property_id

            self.db.ignore_check_constraints = True
            self.db.execute("UPDATE object SET position=-1 WHERE ui_id=? AND object_id=?;", (ui_id, object_id))

            new_parent_id = self.db.add_object(
                ui_id,
                type_id,
                None,
                grand_parent_id,
                position=position,
                child_type=child_type,
            )

            self.db.execute("UPDATE object SET parent_id=? WHERE ui_id=? AND object_id=?;", (new_parent_id, ui_id, object_id))

            self.db.execute("UPDATE object SET position=0 WHERE ui_id=? AND object_id=?;", (ui_id, object_id))

            if inline_property_id:
                self.db.execute(
                    "UPDATE object_property SET inline_object_id=? WHERE ui_id=? AND object_id=? AND property_id=?;",
                    (new_parent_id, ui_id, grand_parent_id, inline_property_id)
                )

            if binding_expression_property_id:
                self.db.execute(
                    "UPDATE object_property SET binding_expression_id=? WHERE ui_id=? AND object_id=? AND property_id=?;",
                    (new_parent_id, ui_id, grand_parent_id, binding_expression_property_id)
                )

            self.db.ignore_check_constraints = False

            # Move all layout properties from obj to parent
            if grand_parent_id is not None:
                self.db.execute(
                    "UPDATE object_layout_property SET child_id=? WHERE ui_id=? AND object_id=? AND child_id=?;",
                    (new_parent_id, ui_id, grand_parent_id, object_id),
                )

            self.history_pop()
            self.db.commit()
        except Exception as e:
            print(f"Error adding parent {type_id} to object {obj} {e}")
        finally:
            new_parent = self.__add_object(False, ui_id, new_parent_id, type_id, None, grand_parent_id, position=position)

            if new_parent.parent:
                new_parent.parent.items_changed(list_position, 1, 1)
            else:
                new_parent.ui.items_changed(list_position, 1, 1)

            self.emit("object-added", new_parent)
            new_parent.notify("n-items")
            self.set_selection([new_parent])

    def remove_parent(self, obj):
        if obj is None:
            return

        parent = obj.parent

        if parent is None or parent.n_items > 1:
            return

        try:
            self.history_push(_("Remove parent of {name}").format(name=obj.display_name))

            ui_id = obj.ui_id
            object_id = obj.object_id

            grand_parent = parent.parent
            grand_parent_id = parent.parent_id

            # Object to remove
            parent_id = obj.parent_id

            # Position where the child will be
            position = parent.position
            list_position = parent.list_position

            # Remove all object layout properties
            self.db.execute(
                "DELETE FROM object_layout_property WHERE ui_id=? AND object_id=? AND child_id=?;",
                (ui_id, parent_id, object_id),
            )

            # Move all layout properties from parent to object
            if grand_parent_id:
                self.db.execute(
                    "UPDATE object_layout_property SET child_id=? WHERE ui_id=? AND object_id=? AND child_id=?;",
                    (object_id, ui_id, grand_parent_id, parent_id),
                )

            self.db.ignore_check_constraints = True
            self.db.execute("UPDATE object SET position=-1 WHERE ui_id=? AND object_id=?;", (ui_id, parent_id))

            if grand_parent_id:
                self.db.execute(
                    "UPDATE object SET parent_id=?, position=? WHERE ui_id=? AND object_id=?;",
                    (grand_parent_id, position, ui_id, object_id),
                )
            else:
                self.db.execute(
                    "UPDATE object SET parent_id=NULL, position=? WHERE ui_id=? AND object_id=?;", (position, ui_id, object_id)
                )

            self.db.execute("DELETE FROM object WHERE ui_id=? AND object_id=?;", (ui_id, parent_id))
            self.db.ignore_check_constraints = False

            self.history_pop()
            self.db.commit()
        except Exception as e:
            logger.warning(f"Error removing parent of object {obj} {e}")
        finally:
            self.__remove_object(parent)
            if grand_parent is None:
                parent.ui.items_changed(list_position, 1, 1)
            else:
                grand_parent.items_changed(list_position, 1, 1)

            self.set_selection([obj])
            obj.notify("parent-id")

    def clipboard_count(self):
        return len(self.db.clipboard)

    @staticmethod
    def get_target_from_ui_file(filename):
        tree = etree.parse(filename)
        root = tree.getroot()

        lib, ver, inferred = CmbDB._get_target_from_node(root)

        return f"{lib}-{ver}" if lib is not None else None

    def get_path_item(self, directory):
        return self.__path_items.get(directory, None)

    def add_item(self, item):
        display_name = item.display_name
        is_path = isinstance(item, CmbPath)

        if is_path and item.path:
            self.__path_items[item.path] = item

        if item == self.__unsaved_item:
            i = len(self.__items)
        else:
            i = 0
            for list_item in self.__items:
                if list_item == self.__unsaved_item:
                    break

                if is_path:
                    if not isinstance(list_item, CmbPath):
                        break

                    if display_name < list_item.display_name:
                        break
                elif not isinstance(list_item, CmbPath) and display_name < list_item.display_name:
                    break

                i += 1

        item.path_parent = None
        self.__items.insert(i, item)
        self.items_changed(i, 0, 1)

    def __get_path_for_filename(self, filename):
        dirname = Path(os.path.dirname(filename))

        node = self
        for directory in dirname.parts:
            item = node.get_path_item(directory)

            # Ensure we have the path in it
            if item is None:
                item = CmbPath(path=directory)
                node.add_item(item)

            node = item

        return node

    # Default handlers
    def __add_item(self, item, filename):
        if filename is None:
            # Ensure folder for unsaved files
            if self.__unsaved_item is None:
                self.__unsaved_item = CmbPath()
                self.add_item(self.__unsaved_item)

            # Use unsaved special folder
            path = self.__unsaved_item
        else:
            path = self.__get_path_for_filename(filename)

        path.add_item(item)

    def __remove_item(self, item):
        path_parent = item.path_parent

        if path_parent:
            path_parent.remove_item(item)
        else:
            if self.__unsaved_item == item:
                self.__unsaved_item = None

            if isinstance(item, CmbPath) and item.path in self.__path_items:
                del self.__path_items[item.path]

            i = self.__items.index(item)
            self.__items.pop(i)
            self.items_changed(i, 1, 0)

    def __update_path(self, item, filename):
        in_selection = [item] == self.__selection

        path_parent = item.path_parent

        # Do not do anything if item has no parent
        if not path_parent and not os.path.dirname(filename):
            return

        # Do not do anything if the path is the same
        if path_parent and path_parent.path and path_parent.path == os.path.dirname(filename):
            return

        # Remove item
        self.__remove_item(item)
        # add it again
        self.__add_item(item, filename)

        if in_selection:
            GLib.idle_add(self.__set_selection_idle, item)

        # Clear unused paths
        if path_parent and path_parent.n_items == 0:
            GLib.idle_add(self.__clear_unused_paths_idle, path_parent)

    def __set_selection_idle(self, item):
        self.set_selection([item])
        return GLib.SOURCE_REMOVE

    def __clear_unused_paths_idle(self, path_parent):
        if path_parent.n_items:
            return

        while path_parent is not None:
            next_parent = path_parent.path_parent

            if path_parent.n_items != 1:
                break

            path_parent = next_parent

        if path_parent:
            if path_parent.path_parent:
                path_parent.path_parent.remove_item(path_parent)
            else:
                self.__remove_item(path_parent)

        return GLib.SOURCE_REMOVE

    def do_ui_added(self, ui):
        self.__add_item(ui, ui.filename)
        self.emit("changed")

    def do_ui_removed(self, ui):
        self.__remove_item(ui)
        self.emit("changed")

    def do_ui_changed(self, ui, field):
        if field == "filename":
            self.__update_path(ui, ui.filename)

        self.emit("changed")

    def do_ui_library_changed(self, ui, lib):
        self.emit("changed")

    def do_css_added(self, css):
        self.__add_item(css, css.filename)
        self.emit("changed")

    def do_css_removed(self, css):
        self.__remove_item(css)
        self.emit("changed")

    def do_css_changed(self, css, field):
        if field == "filename":
            self.__update_path(css, css.filename)

        self.emit("changed")

    def do_gresource_added(self, gresource):
        if gresource.resource_type == "gresources":
            self.__add_item(gresource, gresource.gresources_filename)
        self.emit("changed")

    def do_gresource_removed(self, gresource):
        if gresource.resource_type == "gresources":
            self.__remove_item(gresource)
        self.emit("changed")

    def do_gresource_changed(self, gresource, field):
        if gresource.resource_type == "gresources" and field == "gresources_filename":
            self.__update_path(gresource, gresource.gresources_filename)

        self.emit("changed")

    def do_object_added(self, obj):
        self.emit("changed")

    def do_object_removed(self, obj):
        self.emit("changed")

    def do_object_changed(self, obj, field):
        self.emit("changed")

    def do_object_property_changed(self, obj, prop):
        self.emit("changed")

    def do_object_layout_property_changed(self, obj, child, prop):
        self.emit("changed")

    def do_object_property_binding_changed(self, obj, prop):
        self.emit("changed")

    def do_object_signal_added(self, obj, signal):
        self.emit("changed")

    def do_object_signal_removed(self, obj, signal):
        self.emit("changed")

    def do_object_signal_changed(self, obj, signal):
        self.emit("changed")

    def do_object_data_added(self, obj, data):
        self.emit("changed")

    def do_object_data_removed(self, obj, data):
        self.emit("changed")

    def do_object_data_changed(self, data):
        self.emit("changed")

    def do_object_data_data_added(self, parent, data):
        self.emit("changed")

    def do_object_data_data_removed(self, parent, data):
        self.emit("changed")

    def do_object_data_arg_changed(self, data, arg):
        self.emit("changed")

    # GListModel iface
    def do_get_item(self, position):
        return self.__items[position] if position < len(self.__items) else None

    def do_get_item_type(self):
        return CmbBase

    def do_get_n_items(self):
        return len(self.__items)
