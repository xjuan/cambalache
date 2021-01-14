#
# CmbProject - Cambalache Project
#
# Copyright (C) 2020  Juan Pablo Ugarte - All Rights Reserved
#
# Unauthorized copying of this file, via any medium is strictly prohibited.
#

import os
import sys
import sqlite3

from lxml import etree
from lxml.builder import E


class CmbProject:
    def __init__(self, filename):
        self.conn = sqlite3.connect(filename)
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def history_clear(self):
        self.conn.execute("DELETE FROM history;")
        self.conn.commit();

    def _import_object(self, builder_ver, ui_id, node, parent_id):
        c = self.conn.cursor()
        klass = node.get('class')
        name = node.get('id')

        # Insert object
        c.execute("INSERT INTO object (type_id, name, parent_id, ui_id) VALUES (?, ?, ?, ?);",
                  (klass, name, parent_id, ui_id))
        object_id = c.lastrowid

        # Properties
        for prop in node.iterfind('property'):
            property_id = prop.get('name')
            translatable = prop.get('translatable', None)

            # Find owner type for property
            c.execute("SELECT owner_id FROM property WHERE property_id=? AND owner_id IN (SELECT parent_id FROM type_tree WHERE type_id=? UNION SELECT ?);",
                      (property_id, klass, klass))
            owner_id = c.fetchone()

            # Insert property
            if owner_id:
                c.execute("INSERT INTO object_property (object_id, owner_id, property_id, value, translatable) VALUES (?, ?, ?, ?, ?);",
                          (object_id, owner_id[0], property_id, prop.text, translatable))
            else:
                print(f'Could not find owner type for {klass}:{property_id}')

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

            # Find owner type for signal
            c.execute("SELECT owner_id FROM signal WHERE signal_id=? AND owner_id IN (SELECT parent_id FROM type_tree WHERE type_id=? UNION SELECT ?);",
                      (signal_id, klass, klass))
            owner_id = c.fetchone()

            # Insert signal
            c.execute("INSERT INTO object_signal (object_id, owner_id, signal_id, handler, detail, user_data, swap, after) VALUES (?, ?, ?, ?, ?, (SELECT object_id FROM object WHERE name=?), ?, ?);",
                      (object_id, owner_id[0] if owner_id else None, signal_id, handler, detail, user_data, swap, after))

        # Children
        for child in node.iterfind('child'):
            obj = child.find('object')
            if obj is not None:
                self._import_object(builder_ver, None, obj, object_id)

        # Packing properties
        if builder_ver == 3:
            # Gtk 3, packing props are sibling to <object>
            packing = node.getnext()
            if packing is not None and packing.tag != 'packing':
                packing = None
        else:
            # Gtk 4, layout props are children of <object>
            packing = node.find('layout')

        if parent_id and packing is not None:
            c.execute("SELECT type_id FROM object WHERE object_id=?;", (parent_id, ))
            parent_type = c.fetchone()

            if parent_type is None:
                return

            if builder_ver == 3:
                # For Gtk 3 we fake a LayoutChild class for each GtkContainer
                owner_id = f'Cambalache{parent_type[0]}LayoutChild'
            else:
                # FIXME: Need to get layout-manager-type from class
                owner_id = f'{parent_type[0]}LayoutChild'

            for prop in packing.iterfind('property'):
                property_id = prop.get('name')
                translatable = prop.get('translatable', None)
                c.execute("INSERT INTO object_child_property (object_id, child_id, owner_id, property_id, value, translatable) VALUES (?, ?, ?, ?, ?, ?);",
                          (parent_id, object_id, owner_id, property_id, prop.text, translatable))
        c.close()

    def import_file(self, filename, overwrite=False):
        c = self.conn.cursor()

        basename = os.path.basename(filename)

        # Remove old UI
        if overwrite:
            c.execute("DELETE FROM ui WHERE name=?;", (basename, ))

        c.execute("INSERT INTO ui (name, filename) VALUES (?, ?);",
                  (basename, filename))
        ui_id = c.lastrowid

        tree = etree.parse(filename)
        root = tree.getroot()

        # Requires
        builder_ver = 4
        for req in root.iterfind('requires'):
            lib = req.get('lib')
            version = req.get('version')

            if lib == 'gtk+':
                builder_ver = 3;

            c.execute("INSERT INTO ui_library (ui_id, library_id, version) VALUES (last_insert_rowid(), ?, ?);",
                      (lib, version))

        for child in root.iterfind('object'):
            self._import_object(builder_ver, ui_id, child, None)
            self.conn.commit()

        c.close()

    def _get_object(self, builder_ver, object_id):
        def node_set(node, attr, val):
            if val is not None:
                node.set(attr, str(val))

        c = self.conn.cursor()
        cc = self.conn.cursor()
        obj = E.object()

        c.execute('SELECT type_id, name FROM object WHERE object_id=?;', (object_id,))
        row = c.fetchone()
        node_set(obj, 'class', row[0])
        node_set(obj, 'id', row[1])

        # Properties
        for row in c.execute('SELECT value, property_id FROM object_property WHERE object_id=?;',
                             (object_id,)):
            obj.append(E.property(row[0], name=row[1]))
            # Signals
        for row in c.execute('SELECT signal_id, handler, detail, (SELECT name FROM object WHERE object_id=user_data), swap, after FROM object_signal WHERE object_id=?;',
                             (object_id,)):
            node = E.signal(name=row[0], handler=row[1])
            node_set(node, 'object', row[3])
            node_set(node, 'swapped', row[4])
            node_set(node, 'after', row[5])
            obj.append(node)

        # Children
        for row in c.execute('SELECT object_id FROM object WHERE parent_id=?;', (object_id,)):
            child_id = row[0]
            child_obj = self._get_object(builder_ver, child_id)
            child = E.child(child_obj)

            # Packing / Layout
            layout = E('packing' if builder_ver == 3 else 'layout')

            for prop in cc.execute('SELECT value, property_id FROM object_child_property WHERE object_id=? AND child_id=?;',
                                 (object_id, child_id)):
                layout.append(E.property(prop[0], name=prop[1]))

            if len(layout) > 0:
                if builder_ver == 3:
                    child.append(layout)
                else:
                    child_obj.append(layout)

            obj.append(child)

        c.close()
        cc.close()
        return obj

    def _export_ui(self, ui_id, filename):
        c = self.conn.cursor()

        node = E.interface()

        # requires
        builder_ver = 4
        for row in c.execute('SELECT library_id, version FROM ui_library WHERE ui_id=?;', (ui_id,)):
            node.append(E.requires(lib=row[0], version=row[1]))
            if row[0] == 'gtk+':
                builder_ver = 3;

        # Iterate over toplovel objects
        for row in c.execute('SELECT object_id FROM object WHERE ui_id=?;',
                             (ui_id,)):
            child = self._get_object(builder_ver, row[0])
            node.append(child)

        c.close()

        # Dump xml to file
        with open(filename, 'wb') as xml:
            xml.write(etree.tostring(node,
                                     pretty_print=True,
                                     xml_declaration=True,
                                     encoding='UTF-8'))
            xml.close()


    def export(self):
        c = self.conn.cursor()

        for row in c.execute('SELECT ui_id, filename FROM ui;'):
            self._export_ui(row[0], row[1] + '.test.ui')

        c.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Ussage: {sys.argv[0]} db.sqlite import.ui")
        exit()

    project = CmbProject(sys.argv[1])
    project.import_file(sys.argv[2], True)
    project.history_clear()
    project.export()
