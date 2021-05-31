#
# CmbDB - Cambalache DataBase
#
# Copyright (C) 2021  Juan Pablo Ugarte - All Rights Reserved
#
# Unauthorized copying of this file, via any medium is strictly prohibited.
#

import os
import sys
import sqlite3
import gi

from lxml import etree
from lxml.builder import E
from locale import gettext as _

gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, GObject, Gtk
from .config import *


def _get_text_resource(name):
    gbytes = Gio.resources_lookup_data(f'/ar/xjuan/Cambalacheui/{name}',
                                       Gio.ResourceLookupFlags.NONE)
    return gbytes.get_data().decode('UTF-8')

BASE_SQL = _get_text_resource('cmb_base.sql')
PROJECT_SQL = _get_text_resource('cmb_project.sql')
HISTORY_SQL = _get_text_resource('cmb_history.sql')
GOBJECT_SQL = _get_text_resource('gobject-2.0.sql')
GTK3_SQL = _get_text_resource('gtk+-3.0.sql')
GTK4_SQL = _get_text_resource('gtk-4.0.sql')


class CmbDB(GObject.GObject):
    __gtype_name__ = 'CmbDB'

    target_tk = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        self._target_tk = None

        self.history_commands = {}

        self.conn = sqlite3.connect(':memory:')

        super().__init__(**kwargs)

        c = self.conn.cursor()

        # Create type system tables
        c.executescript(BASE_SQL)

        # Create project tables
        c.executescript(PROJECT_SQL)

        # Initialize history (Undo/Redo) tables
        self._init_history_and_triggers()

        self._init_data(c)

        c.execute("PRAGMA foreign_keys = ON;")

        self.conn.commit()
        c.close()

    def __del__(self):
        self.conn.commit()
        self.conn.close()

    def _create_support_table(self, c, table):
        _table = table.replace('_', '-')

        # Create a history table to store data for INSERT and DELETE commands
        c.executescript(f'''
    CREATE TABLE history_{table} AS SELECT * FROM {table} WHERE 0;
    ALTER TABLE history_{table} ADD COLUMN history_old BOOLEAN;
    ALTER TABLE history_{table} ADD COLUMN history_id INTERGER REFERENCES history ON DELETE CASCADE;
    CREATE INDEX history_{table}_history_id_fk ON history_{table} (history_id);
    ''')

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
        clear_history = '''
            DELETE FROM history WHERE (SELECT value FROM global WHERE key='history_index') > 0 AND history_id > (SELECT value FROM global WHERE key='history_index');
            UPDATE global SET value=-1 WHERE key='history_index' AND value >= 0
        '''

        for row in c.execute(f'PRAGMA table_info({table});'):
            col = row[1]
            col_type =  row[2]
            pk = row[5]

            if columns == None:
                columns = col
                old_values = 'OLD.' + col
                new_values = 'NEW.' + col
            else:
                columns += ', ' + col
                old_values += ', OLD.' + col
                new_values += ', NEW.' + col

            all_columns.append(col)
            if pk:
                pk_columns.append(col)
            else:
                non_pk_columns.append(col)

        pkcolumns = ', '.join(pk_columns)
        nonpkcolumns = ', '.join(non_pk_columns)

        command = {
            'PK': f"SELECT {pkcolumns} FROM history_{table} WHERE history_id=?;",
            'COUNT': f"SELECT count(1) FROM {table} WHERE ({pkcolumns}) IS (SELECT {pkcolumns} FROM history_{table} WHERE history_id=?);",
            'DATA': f"SELECT {columns} FROM history_{table} WHERE history_id=?;",
            'DELETE': f"DELETE FROM {table} WHERE ({pkcolumns}) IS (SELECT {pkcolumns} FROM history_{table} WHERE history_id=?);",
            'INSERT': f"INSERT INTO {table} ({columns}) SELECT {columns} FROM history_{table} WHERE history_id=?;",
            'UPDATE': f'UPDATE {table} SET ({nonpkcolumns}) = (SELECT {nonpkcolumns} FROM history_{table} WHERE history_id=? AND history_old=?) \
                        WHERE ({pkcolumns}) IS (SELECT {pkcolumns} FROM history_{table} WHERE history_id=? AND history_old=?);'
        }
        self.history_commands[table] = command

        # INSERT Trigger
        c.execute(f'''
    CREATE TRIGGER on_{table}_insert AFTER INSERT ON {table}
    WHEN
      {history_is_enabled}
    BEGIN
      {clear_history};
      INSERT INTO history (history_id, command, table_name) VALUES ({history_next_seq}, 'INSERT', '{table}');
      INSERT INTO history_{table} (history_id, history_old, {columns})
        VALUES (last_insert_rowid(), 0, {new_values});
    END;
        ''')

        c.execute(f'''
    CREATE TRIGGER on_{table}_delete AFTER DELETE ON {table}
    WHEN
      {history_is_enabled}
    BEGIN
      {clear_history};
      INSERT INTO history (history_id, command, table_name) VALUES ({history_next_seq}, 'DELETE', '{table}');
      INSERT INTO history_{table} (history_id, history_old, {columns})
        VALUES (last_insert_rowid(), 1, {old_values});
    END;
        ''')

        pkcolumns_values = None
        for col in pk_columns:
            if pkcolumns_values == None:
                pkcolumns_values = 'NEW.' + col
            else:
                pkcolumns_values += ', NEW.' + col

        if len(pk_columns) == 0:
            return

        # UPDATE Trigger for each non PK column
        for column in non_pk_columns:
            c.execute(f'''
    CREATE TRIGGER on_{table}_update_{column} AFTER UPDATE OF {column} ON {table}
    WHEN
      NEW.{column} IS NOT OLD.{column} AND {history_is_enabled} AND
      ((SELECT command, table_name, column_name FROM history WHERE history_id = {history_seq})
         IS NOT ('UPDATE', '{table}', '{column}')
         OR
       (SELECT {pkcolumns} FROM history_{table} WHERE history_id = {history_seq} AND history_old=0)
         IS NOT ({pkcolumns_values}))
    BEGIN
      {clear_history};
      INSERT INTO history (history_id, command, table_name, column_name) VALUES ({history_next_seq}, 'UPDATE', '{table}', '{column}');
      INSERT INTO history_{table} (history_id, history_old, {columns})
        VALUES (last_insert_rowid(), 1, {old_values}),
               (last_insert_rowid(), 0, {new_values});
    END;
            ''')

            c.execute(f'''
    CREATE TRIGGER on_{table}_update_{column}_compress AFTER UPDATE OF {column} ON {table}
    WHEN
      NEW.{column} IS NOT OLD.{column} AND {history_is_enabled} AND
      ((SELECT command, table_name, column_name FROM history WHERE history_id = {history_seq})
         IS ('UPDATE', '{table}', '{column}')
         AND
       (SELECT {pkcolumns} FROM history_{table} WHERE history_id = {history_seq} AND history_old=0)
         IS ({pkcolumns_values}))
    BEGIN
      UPDATE history_{table} SET {column}=NEW.{column} WHERE history_id = {history_seq} AND history_old=0;
    END;
            ''')

    def _init_history_and_triggers(self):
        c = self.conn.cursor()

        # Create history main tables
        c.executescript(HISTORY_SQL)

        # Create history tables for each tracked table
        self._create_support_table(c, 'ui')
        self._create_support_table(c, 'ui_library')
        self._create_support_table(c, 'object')
        self._create_support_table(c, 'object_property')
        self._create_support_table(c, 'object_layout_property')
        self._create_support_table(c, 'object_signal')

        self.conn.commit()
        c.close()

    def _init_data(self, c):
        if self.target_tk not in ['gtk+-3.0', 'gtk-4.0']:
            raise Exception(f'Unknown target tk {self.target_tk}')

        # Add GObject data
        c.executescript(GOBJECT_SQL)

        # Add gtk data
        # TODO: implement own format instead of sql
        if self.target_tk == 'gtk+-3.0':
            c.executescript(GTK3_SQL)
        elif self.target_tk == 'gtk-4.0':
            c.executescript(GTK4_SQL)

        # TODO: Load all libraries that depend on self.target_tk

    @staticmethod
    def get_target_from_file(filename):
        try:
            with open(filename, 'r') as sql:
                cmb = sql.readline()

                if cmb.startswith('/* Cambalache target=gtk-4.0 */'):
                    return 'gtk-4.0'
                elif cmb.startswith('/* Cambalache target=gtk+-3.0 */'):
                    return 'gtk+-3.0'
        except:
            pass

        return None

    def get_data(self, key):
        c = self.execute("SELECT value FROM global WHERE key=?;", (key, ))
        row = c.fetchone()
        c.close()
        return row[0] if row is not None else None

    def set_data(self, key, value):
        self.execute("UPDATE global SET value=? WHERE key=?;", (value, key))

    def load(self, filename):
        # TODO: drop all data before loading?

        if filename is None or not os.path.isfile(filename):
            return

        target_tk = CmbDB.get_target_from_file(filename)

        if target_tk != self.target_tk:
            return

        # TODO: implement own format instead of sql
        with open(filename, 'r') as sql:
            self.conn.executescript(sql.read())

    def save(self, filename):
        def get_row(row):
            r = '('
            first = True

            for c in row:
                if first:
                    first = False
                else:
                    r += ', '

                if type(c)  == str:
                    val = c.replace("'", "''")
                    r += f"'{val}'"
                elif c is None:
                    r += 'NULL'
                else:
                    r += str(c)

            r += ')'

            return r

        def _dump_table(fd, table):
            c = self.conn.cursor()

            c.execute(f"SELECT * FROM {table};")
            row = c.fetchone()

            if row is not None:
                fd.write(f"INSERT INTO {table} VALUES\n")

            while row is not None:
                fd.write(get_row(row))
                row = c.fetchone()
                if row is not None:
                    fd.write(',\n')
                else:
                    fd.write(';\n\n')

            c.close()

        self.conn.commit()

        # TODO: create custom XML file format with all the data from project tables
        with open(filename, 'w') as fd:
            fd.write(f'/* Cambalache target={self.target_tk} */\n')

            for table in ['ui', 'ui_library', 'object', 'object_property',
                          'object_layout_property', 'object_signal']:
                _dump_table(fd, table)
            fd.close();

    def backup(self, filename):
        self.conn.commit()
        bck = sqlite3.connect(filename)

        with bck:
            self.conn.backup(bck)

        bck.close()

    def cursor(self):
        return self.conn.cursor()

    def commit(self):
        return self.conn.commit()

    def execute(self, *args):
        return self.conn.execute(*args)

    def add_ui(self, name, filename, requirements={}, comment=None):
        c = self.conn.cursor()
        c.execute("INSERT INTO ui (name, filename, comment) VALUES (?, ?, ?);",
                  (name, filename, comment))
        ui_id = c.lastrowid

        for key in requirements:
            req = requirements[key]
            c.execute('INSERT INTO ui_library (ui_id, library_id, version, comment) VALUES (?, ?, ?, ?);',
                      (ui_id, key, req['version'], req['comment']))
        c.close()

        return ui_id

    def add_object(self, ui_id, obj_type, name=None, parent_id=None, comment=None):
        c = self.conn.cursor()

        c.execute("SELECT coalesce((SELECT object_id FROM object WHERE ui_id=? ORDER BY object_id DESC LIMIT 1), 0) + 1;", (ui_id, ))
        object_id = c.fetchone()[0]

        c.execute("INSERT INTO object (ui_id, object_id, type_id, name, parent_id, comment) VALUES (?, ?, ?, ?, ?, ?);",
                  (ui_id, object_id, obj_type, name, parent_id, comment))
        c.close()

        return object_id

    def _import_object(self, type_info, ui_id, node, parent_id):
        klass = node.get('class')
        name = node.get('id')
        comment = self._node_get_comment(node)
        info = type_info.get(klass, None)

        # Insert object
        try:
            assert info
            object_id = self.add_object(ui_id, klass, name, parent_id, comment)
        except:
            print('Error importing', klass)
            return

        c = self.conn.cursor()

        # Properties
        for prop in node.iterfind('property'):
            property_id = prop.get('name').replace('_', '-')
            translatable = prop.get('translatable', None)
            comment = self._node_get_comment(prop)

            owner_id = None

            # Find owner type for property
            if property_id in info.properties:
                owner_id = klass
            else:
                for parent in info.hierarchy:
                    pinfo = type_info[parent]
                    if property_id in pinfo.properties:
                        owner_id = parent
                        break

            # Insert property
            if owner_id:
                try:
                    c.execute("INSERT INTO object_property (ui_id, object_id, owner_id, property_id, value, translatable, comment) VALUES (?, ?, ?, ?, ?, ?, ?);",
                              (ui_id, object_id, owner_id, property_id, prop.text, translatable, comment))
                except Exception as e:
                    raise Exception(f'Can not save object {object_id} {owner_id}:{property_id} property: {e}')
            else:
                print(f'Could not find owner type for {klass}:{property_id} property')

        # Signals
        for signal in node.iterfind('signal'):
            tokens = signal.get('name').split('::')

            if len(tokens) > 1:
                signal_id = tokens[0]
                detail = tokens[1]
            else:
                signal_id = tokens[0]
                detail = None

            handler = signal.get('handler')
            user_data = signal.get('object')
            swap = signal.get('swapped')
            after = signal.get('after')
            comment = self._node_get_comment(signal)

            # Find owner type for signal
            if signal_id in info.signals:
                owner_id = klass
            else:
                for parent in info.hierarchy:
                    pinfo = type_info[parent]
                    if signal_id in pinfo.signals:
                        owner_id = parent
                        break

            # Insert signal
            if owner_id:
                try:
                    c.execute("INSERT INTO object_signal (ui_id, object_id, owner_id, signal_id, handler, detail, user_data, swap, after, comment) VALUES (?, ?, ?, ?, ?, ?, (SELECT object_id FROM object WHERE ui_id=? AND name=?), ?, ?, ?);",
                              (ui_id, object_id, owner_id, signal_id, handler, detail, ui_id, user_data, swap, after, comment))
                except Exception as e:
                    raise Exception(f'Can not save object {object_id} {owner_id}:{signal_id} signal: {e}')
            else:
                print(f'Could not find owner type for {klass}:{signal_id} signal')

        # Children
        for child in node.iterfind('child'):
            obj = child.find('object')
            if obj is not None:
                self._import_object(type_info, ui_id, obj, object_id)

        # Packing properties
        if self.target_tk == 'gtk+-3.0':
            # Gtk 3, packing props are sibling to <object>
            packing = node.getnext()
            if packing is not None and packing.tag != 'packing':
                packing = None
        else:
            # Gtk 4, layout props are children of <object>
            packing = node.find('layout')

        if parent_id and packing is not None:
            c.execute("SELECT type_id FROM object WHERE ui_id=? AND object_id=?;", (ui_id, parent_id))
            parent_type = c.fetchone()

            if parent_type is None:
                return

            if self.target_tk == 'gtk+-3.0':
                # For Gtk 3 we fake a LayoutChild class for each GtkContainer
                owner_id = f'{parent_type[0]}LayoutChild'
            else:
                # FIXME: Need to get layout-manager-type from class
                owner_id = f'{parent_type[0]}LayoutChild'

            for prop in packing.iterfind('property'):
                comment = self._node_get_comment(prop)
                property_id = prop.get('name').replace('_', '-')
                translatable = prop.get('translatable', None)
                try:
                    c.execute("INSERT INTO object_layout_property (ui_id, object_id, child_id, owner_id, property_id, value, translatable, comment) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                              (ui_id, parent_id, object_id, owner_id, property_id, prop.text, translatable, comment))
                except Exception as e:
                    raise Exception(f'Can not save object {object_id} {owner_id}:{property_id} layout property: {e}')
        c.close()

    def _node_get_comment(self, node):
        prev = node.getprevious()
        if prev is not None and prev.tag is etree.Comment:
            return prev.text
        return None

    def _node_get_requirements(self, root):
        retval = {}

        # Collect requirements and comments
        for req in root.iterfind('requires'):
            lib = req.get('lib')
            version = req.get('version')

            retval[lib] = {
              'version': version,
              'comment': self._node_get_comment(req)
            }

        return retval

    def import_file(self, type_info, filename, projectdir='.'):
        tree = etree.parse(filename)
        root = tree.getroot()

        requirements = self._node_get_requirements(root)

        # TODO: look for layout properties tag to infer if its for gtk 4 or 3
        if self.target_tk == 'gtk-4.0' and 'gtk' not in requirements:
            raise Exception(_('Target version mismatch'))

        c = self.conn.cursor()

        # Update interface comment
        comment = self._node_get_comment(root)
        if comment and comment.startswith('Created with Cambalache'):
            comment = None

        basename = os.path.basename(filename)
        relpath = os.path.relpath(filename, projectdir)
        ui_id = self.add_ui(basename, relpath, requirements, comment)

        # Import objects
        for child in root.iterfind('object'):
            self._import_object(type_info, ui_id, child, None)

            while Gtk.events_pending():
                Gtk.main_iteration_do(False)

        self.conn.commit()
        c.close()

        return ui_id

    def _node_add_comment(self, node, comment):
        if comment:
            node.addprevious(etree.Comment(comment))

    def _get_object(self, ui_id, object_id, use_id=False):
        def node_set(node, attr, val):
            if val is not None:
                node.set(attr, str(val))

        c = self.conn.cursor()
        cc = self.conn.cursor()
        obj = E.object()

        c.execute('SELECT type_id, name FROM object WHERE ui_id=? AND object_id=?;', (ui_id, object_id))
        type_id, name = c.fetchone()
        node_set(obj, 'class', type_id)

        if use_id and name:
            name = GLib.uri_escape_string(name, None, True)
            node_set(obj, 'id', f'__cambalache__{ui_id}.{object_id}+{name}')
        else:
            node_set(obj, 'id', f'__cambalache__{ui_id}.{object_id}' if use_id else name)

        # Properties
        for row in c.execute('SELECT value, property_id, comment FROM object_property WHERE ui_id=? AND object_id=?;',
                             (ui_id, object_id,)):
            val, name, comment = row
            node = E.property(val, name=name)
            obj.append(node)
            self._node_add_comment(node, comment)

        # Signals
        for row in c.execute('SELECT signal_id, handler, detail, (SELECT name FROM object WHERE ui_id=? AND object_id=user_data), swap, after, comment FROM object_signal WHERE ui_id=? AND object_id=?;',
                             (ui_id, ui_id, object_id,)):
            signal_id, handler, detail, data, swap, after, comment = row
            name = f'{signal_id}::{detail}' if detail is not None else signal_id
            node = E.signal(name=name, handler=handler)
            node_set(node, 'object', data)
            if swap:
                node_set(node, 'swapped', 'yes')
            if after:
                node_set(node, 'after', 'yes')
            obj.append(node)
            self._node_add_comment(node, comment)

        # Children
        for row in c.execute('SELECT object_id, comment FROM object WHERE ui_id=? AND parent_id=?;', (ui_id, object_id)):
            child_id, comment = row
            child_obj = self._get_object(ui_id, child_id, use_id=use_id)
            child = E.child(child_obj)
            self._node_add_comment(child_obj, comment)

            # Packing / Layout
            layout = E('packing' if self.target_tk == 'gtk+-3.0' else 'layout')

            for prop in cc.execute('SELECT value, property_id, comment FROM object_layout_property WHERE ui_id=? AND object_id=? AND child_id=?;',
                                 (ui_id, object_id, child_id)):
                value, property_id, comment = prop
                node = E.property(value, name=property_id)
                layout.append(node)
                self._node_add_comment(node, comment)

            if len(layout) > 0:
                if self.target_tk == 'gtk+-3.0':
                    child.append(layout)
                else:
                    child_obj.append(layout)

            obj.append(child)

        c.close()
        cc.close()
        return obj

    def export_ui(self, ui_id, filename=None, use_id=False):
        c = self.conn.cursor()

        node = E.interface()
        node.addprevious(etree.Comment(f" Created with Cambalache {VERSION} "))

        c.execute('SELECT comment FROM ui WHERE ui_id=?;', (ui_id,))
        comment, = c.fetchone()
        self._node_add_comment(node, comment)

        # requires
        for row in c.execute('SELECT library_id, version, comment FROM ui_library WHERE ui_id=?;', (ui_id,)):
            library_id, version, comment = row
            req = E.requires(lib=library_id, version=version)
            self._node_add_comment(req, comment)
            node.append(req)

        # Iterate over toplovel objects
        for row in c.execute('SELECT object_id, comment FROM object WHERE parent_id IS NULL AND ui_id=?;',
                             (ui_id,)):
            object_id, comment = row
            child = self._get_object(ui_id, object_id, use_id)
            node.append(child)
            self._node_add_comment(child, comment)

        c.close()

        tree = etree.ElementTree(node)

        if filename is not None:
            # Dump xml to file
            with open(filename, 'wb') as fd:
                tree.write(fd,
                           pretty_print=True,
                           xml_declaration=True,
                           encoding='UTF-8')
                fd.close()
        else:
            return etree.tostring(tree,
                                  pretty_print=True,
                                  xml_declaration=True,
                                  encoding='UTF-8').decode('UTF-8')