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

from gi.repository import GObject, Gio

from lxml import etree

from .cmb_db import CmbDB
from .cmb_ui import CmbUI
from .cmb_css import CmbCSS
from .cmb_base import CmbBase
from .cmb_object import CmbObject
from .cmb_object_data import CmbObjectData
from .cmb_property import CmbProperty
from .cmb_layout_property import CmbLayoutProperty
from .cmb_library_info import CmbLibraryInfo
from .cmb_type_info import CmbTypeInfo
from .cmb_objects_base import CmbSignal
from . import constants
from cambalache import getLogger, _, N_

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
    __filename = None

    undo_msg = GObject.Property(type=str)
    redo_msg = GObject.Property(type=str)

    def __init__(self, target_tk=None, filename=None, **kwargs):
        # Type Information
        self.type_info = {}

        # Library Info
        self.library_info = {}

        # GListModel
        self.__items = []

        # Selection
        self.__selection = []
        self._ignore_selection = False

        # Objects hash tables
        # FIXME: Use an int key instead of a string (ui_id << 18 || object_id)
        self._object_id = {}
        self.__css_id = {}

        self.__template_info = {}

        super().__init__(**kwargs)

        self.target_tk = target_tk
        self.filename = filename

        # Target from file take precedence over target_tk property
        if self.filename and os.path.isfile(self.filename):
            target_tk = CmbDB.get_target_from_file(self.filename)

            if target_tk is not None:
                self.target_tk = target_tk

        if self.target_tk is None or self.target_tk == "":
            raise Exception("Either target_tk or filename are required")

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

    def __load(self):
        if self.filename is None or not os.path.isfile(self.filename):
            return

        self.history_enabled = False
        self.db.load(self.filename)
        self.history_enabled = True

        self.__populate_items()

    def __populate_items(self, ui_id=None):
        c = self.db.cursor()

        if ui_id:
            rows = c.execute("SELECT * FROM ui WHERE ui_id=?;", (ui_id,))
        else:
            rows = c.execute("SELECT * FROM ui;")

        # Populate tree view ui first
        for row in rows:
            ui = self.__add_ui(True, *row)
            ui.notify("n-items")

        # Populate CSS
        if ui_id is None:
            rows = c.execute("SELECT * FROM css;")

            # Populate tree view
            for row in rows:
                self.__add_css(True, *row)

        c.close()

    @GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT)
    def filename(self):
        return self.__filename

    @filename.setter
    def filename(self, value):
        # Ensure extension
        if value and not value.endswith(".cmb"):
            value = value + ".cmb"

        self.__filename = value

    def save(self):
        if self.filename:
            self.db.save(self.filename)
            return True

        return False

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

        # Remove old UI
        if overwrite:
            self.db.execute("DELETE FROM ui WHERE filename=?;", (filename,))

        # Import file
        dirname = os.path.dirname(self.filename if self.filename else filename)
        ui_id = self.db.import_file(filename, dirname)

        import_end = time.monotonic()

        # Populate UI
        self.__populate_items(ui_id)

        self.history_pop()

        logger.info(f"Import took: {import_end - start}")
        logger.info(f"UI update: {time.monotonic() - import_end}")

        # Get parsing errors
        msgs, detail_msg = self.__get_import_errors()
        self.db.errors = None

        ui = self.get_object_by_id(ui_id)

        return (ui, msgs, detail_msg)

    def __export(self, ui_id, filename, dirname=None):
        if filename is None:
            return

        if not os.path.isabs(filename):
            if dirname is None:
                dirname = os.path.dirname(self.filename)
            filename = os.path.join(dirname, filename)

        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Get XML tree
        ui = self.db.export_ui(ui_id)

        # Dump xml to file
        with open(filename, "wb") as fd:
            ui.write(fd, pretty_print=True, xml_declaration=True, encoding="UTF-8")
            fd.close()

    def export_ui(self, ui):
        self.__export(ui.ui_id, ui.filename)

    def export(self):
        c = self.db.cursor()

        dirname = os.path.dirname(self.filename)

        n_files = 0

        for row in c.execute("SELECT ui_id, filename FROM ui WHERE filename IS NOT NULL;"):
            ui_id, filename = row
            self.__export(ui_id, filename, dirname=dirname)
            n_files += 1

        c.close()

        return n_files

    def __selection_remove(self, obj):
        try:
            self.__selection.remove(obj)
        except Exception:
            pass
        else:
            self.emit("selection-changed")

    def __get_basename_relpath(self, filename):
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
        template_id,
        name,
        filename,
        description,
        copyright,
        authors,
        license_id,
        translation_domain,
        comment,
        custom_fragment,
    ):
        ui = CmbUI(project=self, ui_id=ui_id)

        self._object_id[ui_id] = ui
        self.__update_template_type_info(ui)

        if emit:
            self.emit("ui-added", ui)

        return ui

    def add_ui(self, filename=None, requirements={}):
        basename, relpath = self.__get_basename_relpath(filename)

        try:
            self.history_push(_("Add UI {basename}").format(basename=basename))
            ui_id = self.db.add_ui(basename, relpath, requirements)
            self.db.commit()
            self.history_pop()
        except Exception:
            return None
        else:
            return self.__add_ui(True, ui_id, None, basename, relpath, None, None, None, None, None, None, None)

    def __remove_ui(self, ui):
        self._object_id.pop(ui.ui_id, None)
        self.__selection_remove(ui)
        self.emit("ui-removed", ui)

    def remove_ui(self, ui):
        try:
            self.history_push(_('Remove UI "{name}"').format(name=ui.name))

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
            retval.append(ui)

        c.close()
        return retval

    def __add_css(self, emit, css_id, filename=None, priority=None, is_global=None):
        css = CmbCSS(project=self, css_id=css_id)
        self.__css_id[css_id] = css
        if emit:
            self.emit("css-added", css)

        return css

    def add_css(self, filename=None):
        basename, relpath = self.__get_basename_relpath(filename)

        try:
            self.history_push(_("Add CSS {basename}").format(basename=basename))
            css_id = self.db.add_css(relpath)
            self.db.commit()
            self.history_pop()
        except Exception:
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
            print(e)

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
        internal_child=None,
        child_type=None,
        comment=None,
        position=0,
        custom_fragment=None,
        custom_child_fragment=None,
    ):
        obj = CmbObject(project=self, ui_id=ui_id, object_id=object_id, info=self.type_info[obj_type])
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
        self, ui_id, obj_type, name=None, parent_id=None, layout=None, position=None, child_type=None, inline_property=None
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
            )
            self.history_pop()
            self.db.commit()
        except Exception as e:
            logger.warning(f"Error adding object {obj_name}: {e}")
            return None
        else:
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

    def remove_object(self, obj):
        try:
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

                for row in self.db.execute("SELECT ui_id, object_id FROM object WHERE type_id=?;", (obj.name, )):
                    obj_ui_id, obj_object_id = row
                    tmpl_obj = self.get_object_by_id(obj_ui_id, obj_object_id)
                    if tmpl_obj:
                        tmpl_obj._save_last_known_parent_and_position()
                        template_instances.append(tmpl_obj)

            name = obj.name if obj.name is not None else obj.type_id
            self.history_push(_("Remove object {name}").format(name=name))

            if template_instances is not None and len(template_instances):
                self.db.execute("DELETE FROM object WHERE type_id=?;", (obj.name, ))

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

    def get_selection(self):
        return self.__selection

    def set_selection(self, selection):
        if self._ignore_selection or type(selection) is not list or self.__selection == selection:
            return

        for obj in selection:
            if isinstance(obj, CmbUI):
                pass
            elif isinstance(obj, CmbObject):
                pass
            elif isinstance(obj, CmbCSS):
                pass
            else:
                return

        self.__selection = selection
        self.emit("selection-changed")

    def get_object_by_key(self, key):
        if type(key) is int:
            return self._object_id.get(key, None)

        obj = self._object_id.get(key, None)

        if obj:
            return obj

        ui_id, object_id = [int(x) for x in key.split(".")]
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

    def __undo_redo_property_notify(self, obj, layout, prop, owner_id, property_id):
        properties = obj.layout_dict if layout else obj.properties_dict
        p = properties.get(property_id, None)

        if p and p.owner_id == owner_id and p.property_id == property_id:
            p.notify(prop)
            if layout:
                obj._layout_property_changed(p)
            else:
                obj._property_changed(p)

    def __undo_redo_do(self, undo, update_objects=None):
        def get_object_position(c, row):
            ui_id, parent_id, position = row[0], row[4], row[8]
            parent = self.get_object_by_id(ui_id, parent_id)
            return parent, position

        c = self.db.cursor()

        # Get last command
        command, range_id, table, column, table_pk, old_values, new_values = c.execute(
            "SELECT command, range_id, table_name, column_name, table_pk, old_values, new_values FROM history WHERE history_id=?",
            (self.history_index, )
        ).fetchone()

        table_pk = json.loads(table_pk) if table_pk else None
        old_values = json.loads(old_values) if old_values else None
        new_values = json.loads(new_values) if new_values else None

        # Undo or Redo command
        if command == "INSERT":
            if table == "object":
                parent, position = get_object_position(c, new_values)

                if undo:
                    update_objects.append((parent, position, 1, 0))
                else:
                    update_objects.append((parent, position, 0, 1))

            if undo:
                self.db.history_delete(table, table_pk)
            else:
                self.db.history_insert(table, new_values)

            self.__undo_redo_update_insert_delete(c, undo, command, table, column, table_pk, old_values, new_values)
        elif command == "DELETE":
            if table == "object":
                parent, position = get_object_position(c, old_values)

                if undo:
                    update_objects.append((parent, position, 0, 1))
                else:
                    update_objects.append((parent, position, 1, 0))

            if undo:
                self.db.history_insert(table, old_values)
            else:
                self.db.history_delete(table, table_pk)

            self.__undo_redo_update_insert_delete(c, undo, command, table, column, table_pk, old_values, new_values)
        elif command == "UPDATE":
            # Ignore parent_id since its changed together with position
            if update_objects is not None and table == "object" and column == "position":
                old_parent, old_position = get_object_position(c, old_values)
                new_parent, new_position = get_object_position(c, new_values)

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

            if undo:
                self.db.history_update(table, column, table_pk, old_values)
            else:
                self.db.history_update(table, column, table_pk, new_values)

            self.__undo_redo_update_update(c, undo, command, table, column, table_pk, old_values, new_values)
        elif command == "PUSH" or command == "POP":
            pass
        else:
            logger.warning(f"Error unknown history command {command}")

        c.close()

    def __undo_redo_update_update(self, c, undo, command, table, column, pk, old_values, new_values):
        if table is None:
            return

        # Update tree model and emit signals
        # We can not easily implement this using triggers because they are called
        # even if the transaction is rollback because of a FK constraint

        if command == "UPDATE":
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

    def __undo_redo_update_insert_delete(self, c, undo, command, table, column, pk, old_values, new_values):
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
        elif table in ["object", "ui", "css"]:
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
            else:
                if table == "ui":
                    self.__add_ui(True, *row)
                elif table == "object":
                    obj = self.__add_object(True, *row)

                    if obj.ui.template_id == obj.object_id:
                        self.__update_template_type_info(obj.ui)
                elif table == "css":
                    self.__add_css(True, *row)
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
                    parent = obj.data_dict.get(f"{row[2]}.{row[6]}", None)

                    if parent:
                        parent._add_child(row[2], row[3], row[4])
                    else:
                        obj._add_data(row[2], row[3], row[4])
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

    def __undo_redo(self, undo):
        selection = self.get_selection()

        command, range_id, table, column = self.db.execute(
            "SELECT command, range_id, table_name, column_name FROM history WHERE history_id=?",
            (self.history_index, )
        ).fetchone()

        update_parents = []

        try:
            self.history_enabled = False
            self.db.foreign_keys = False
            self.db.ignore_check_constraints = True

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

            self.db.foreign_keys = True
            self.db.ignore_check_constraints = False
            self.history_enabled = True
        except sqlite3.Error as e:
            self.history_enabled = True
            self.db.foreign_keys = True
            self.db.ignore_check_constraints = False

            self.history_index = 0
            self.db.clear_history()
            raise e

        # Compress update commands
        compressed_list = []
        prev_parent, prev_position, prev_removed, prev_added = (None, None, 0, 0)

        for i, tuples in enumerate(update_parents):
            parent, position, removed, added = tuples

            # Compress removed and added if possible
            if prev_parent == parent and prev_position == position and \
               prev_removed + removed == 1 and prev_added + added == 1:
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
            parent.items_changed(position, removed, added)
            if removed != added:
                parent.notify("n-items")

        self.set_selection(selection)

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
                retval["ui"] = ui.display_name
            elif table == "ui_library":
                ui_id = data[0]
                ui = self.get_object_by_id(ui_id)
                retval["ui"] = ui.display_name
                retval["lib"] = data[1]
                retval["version"] = data[2]
            elif table == "css":
                retval["css"] = data[1]
            elif table == "css_ui":
                css_id = data[0]
                ui_id = data[1]

                css = self.get_css_by_id(css_id)
                ui = self.get_object_by_id(ui_id)

                retval["css"] = css.display_name
                retval["ui"] = ui.display_name
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
                    if column == "translatable":
                        retval["value"] = _("True") if data[5] else _("False")
                    elif column == "comment":
                        retval["value"] = f'"{data[6]}"'
                    elif column == "translation_context":
                        retval["value"] = f'"{data[7]}"'
                    elif column == "translation_comments":
                        retval["value"] = f'"{data[8]}"'
                    else:
                        retval["prop"] = f'"{data[3]}"'
                        retval["value"] = data[4]

                    if column != "value":
                        retval["prop"] = f'"{data[3]}" {column}'
                elif table == "object_layout_property":
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

                    if column != "value":
                        retval["prop"] = f'"{data[4]}" {column}'
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
                "SELECT command, range_id, table_name, column_name, message, old_values FROM history WHERE history_id=?",
                (index,)
            ).fetchone()

            if cmd is None:
                return None
            command, range_id, table, column, message, old_values = cmd

            if message is not None:
                return message

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
                        "INSERT": _('Set property {prop} of {obj} to {value}'),
                        "DELETE": _('Unset property {prop} of {obj}'),
                        "UPDATE": _('Update property {prop} of {obj} to {value}'),
                    },
                    "object_layout_property": {
                        "INSERT": _('Set layout property {prop} of {obj} to {value}'),
                        "DELETE": _('Unset layout property {prop}" of {obj}'),
                        "UPDATE": _('Update layout property {prop} of {obj} to {value}'),
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

            if msg is not None:
                msg = msg.format(**get_msg_vars(table, column, old_values))

            return msg

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
                    layout=None,
                    category=None,
                    workspace_type=None,
                )

                # Set parent back reference
                info.parent = self.type_info.get(parent_id, None)

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
                obj._save_last_known_parent_and_position()
                self.db.execute("DELETE FROM object WHERE ui_id=? AND object_id=?;", (obj.ui_id, obj.object_id))

            self.history_pop()
            self.db.commit()
        except Exception:
            pass
        finally:
            for obj in selection:
                self.__remove_object(obj)

    def add_parent(self, type_id, obj):
        try:
            self.history_push(_("Add {type_id} parent to {name}").format(name=obj.display_name, type_id=type_id))

            ui_id = obj.ui_id
            object_id = obj.object_id
            grand_parent_id = obj.parent_id or None
            position = obj.position
            list_position = obj.list_position
            child_type = obj.type

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

            self.db.execute(
                "UPDATE object SET parent_id=? WHERE ui_id=? AND object_id=?;",
                (new_parent_id, ui_id, object_id)
            )

            self.db.execute("UPDATE object SET position=0 WHERE ui_id=? AND object_id=?;", (ui_id, object_id))
            self.db.ignore_check_constraints = False

            # Move all layout properties from obj to parent
            if grand_parent_id is not None:
                self.db.execute(
                    "UPDATE object_layout_property SET child_id=? WHERE ui_id=? AND object_id=? AND child_id=?;",
                    (new_parent_id, ui_id, grand_parent_id, object_id)
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
                (ui_id, parent_id, object_id)
            )

            # Move all layout properties from parent to object
            if grand_parent_id:
                self.db.execute(
                    "UPDATE object_layout_property SET child_id=? WHERE ui_id=? AND object_id=? AND child_id=?;",
                    (object_id, ui_id, grand_parent_id, parent_id)
                )

            self.db.ignore_check_constraints = True
            self.db.execute("UPDATE object SET position=-1 WHERE ui_id=? AND object_id=?;", (ui_id, parent_id))

            if grand_parent_id:
                self.db.execute(
                    "UPDATE object SET parent_id=?, position=? WHERE ui_id=? AND object_id=?;",
                    (grand_parent_id, position, ui_id, object_id)
                )
            else:
                self.db.execute(
                    "UPDATE object SET parent_id=NULL, position=? WHERE ui_id=? AND object_id=?;",
                    (position, ui_id, object_id)
                )

            self.db.execute("DELETE FROM object WHERE ui_id=? AND object_id=?;", (ui_id, parent_id))
            self.db.ignore_check_constraints = False

            self.history_pop()
            self.db.commit()
        except Exception as e:
            print(f"Error removing parent of object {obj} {e}")
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

    def __get_object_from_path(self, path):
        try:
            iter = self.get_iter(path)
        except Exception:
            return None

        return self[iter][0] if iter else None

    # Default handlers
    def do_ui_added(self, ui):
        nitems = len(self.__items)
        self.__items.append(ui)
        self.items_changed(nitems, 0, 1)
        self.emit("changed")

    def do_ui_removed(self, ui):
        i = self.__items.index(ui)
        self.__items.pop(i)
        self.items_changed(i, 1, 0)
        self.emit("changed")

    def do_ui_changed(self, ui, field):
        self.emit("changed")

    def do_ui_library_changed(self, ui, lib):
        self.emit("changed")

    def do_css_added(self, css):
        nitems = len(self.__items)
        self.__items.append(css)
        self.items_changed(nitems, 0, 1)
        self.emit("changed")

    def do_css_removed(self, css):
        i = self.__items.index(css)
        self.__items.pop(i)
        self.items_changed(i, 1, 0)
        self.emit("changed")

    def do_css_changed(self, css, field):
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



