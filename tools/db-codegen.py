#
# DbCodegen - Cambalache DB Code Generator
#
# Copyright (C) 2021  Juan Pablo Ugarte
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
import sys
import sqlite3


class CambalacheDb:
    def __init__(self):
        # Create DB file
        self.conn = sqlite3.connect(":memory:")

        dirname = os.path.dirname(__file__) or '.'

        # Create DB tables
        with open(os.path.join(dirname, '../cambalache/db/cmb_base.sql'), 'r') as sql:
            self.conn.executescript(sql.read())

        with open(os.path.join(dirname, '../cambalache/db/cmb_project.sql'), 'r') as sql:
            self.conn.executescript(sql.read())

        self.conn.commit()

    def _get_table_data(self, table):
        c = self.conn.cursor()
        columns = []

        for row in c.execute(f'PRAGMA table_info({table});'):
            col = row[1]
            col_type =  row[2]
            pk = row[5]

            if col_type == 'INTEGER':
                col_type = 'int'
            elif col_type == 'TEXT':
                col_type = 'str'
            elif col_type == 'BOOLEAN':
                col_type = 'bool'
            elif col_type == 'REAL':
                col_type = 'float'
            else:
                print('Error unknown type', col_type)

            columns.append({
                'name': col,
                'type': col_type,
                'pk': pk
            })

        c.close()

        return columns

    def dump_table(self, fd, table, klass, mutable=False):
        c = self.conn.cursor()
        columns = self._get_table_data(table)

        fd.write(f"\n\nclass {klass}(CmbBase):\n")
        fd.write(f"    __gtype_name__ = '{klass}'\n\n")

        # PKs
        all_pk_columns = ''
        pks = []
        for col in columns:
            if mutable and not col['pk']:
                continue

            fd.write(f"    {col['name']} = GObject.Property(type={col['type']}")
            fd.write(f", flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY")

            if col['type'] == 'bool':
                fd.write(f", default = False")

            fd.write(")\n")

            pks.append(col['name'])
            all_pk_columns += f"self.{col['name']}, "

        all_columns = ''
        all_columns_assign = ''
        for col in columns:
            all_columns += ', ' + col['name']
            if mutable and not col['pk']:
                continue
            all_columns_assign += f",\n                   {col['name']}={col['name']}"

        _pk_columns = f"({', '.join(pks)})"
        _pk_values = f"({', '.join(['?' for i in range(len(pks))])})"

        # Init
        fd.write("\n    def __init__(self, **kwargs):\n")
        fd.write("        super().__init__(**kwargs)\n")

        # Class from_row()
        fd.write(f"\n    @classmethod\n")
        fd.write(f"    def from_row(cls, project{all_columns}):\n")
        fd.write(f"        return cls(project=project{all_columns_assign})\n")

        if mutable:
            for col in columns:
                if col['pk']:
                    continue

                fd.write(f"\n    @GObject.Property(type={col['type']}")
                if col['type'] == 'bool':
                    fd.write(f", default = False")
                fd.write(")\n")
                fd.write(f"    def {col['name']}(self):\n")
                fd.write(f"        return self.db_get('SELECT {col['name']} FROM {table} WHERE {_pk_columns} IS {_pk_values};',\n")
                fd.write(f"                           ({all_pk_columns}))\n")

                fd.write(f"\n    @{col['name']}.setter\n")
                fd.write(f"    def _set_{col['name']}(self, value):\n")
                fd.write(f"        self.db_set('UPDATE {table} SET {col['name']}=? WHERE {_pk_columns} IS {_pk_values};',\n")
                fd.write(f"                    ({all_pk_columns}), value)\n")

        c.close()

    def dump(self, filename):
        with open(filename, 'w') as fd:
            fd.write("""# THIS FILE IS AUTOGENERATED, DO NOT EDIT!!!
#
# Cambalache Base Object wrappers
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

import gi
from gi.repository import GObject
from .cmb_base import *
""")

            # Base Objects
            self.dump_table(fd, 'library', 'CmbBaseLibraryInfo')
            self.dump_table(fd, 'property', 'CmbPropertyInfo')
            self.dump_table(fd, 'signal', 'CmbSignalInfo')
            self.dump_table(fd, 'type', 'CmbBaseTypeInfo')
            self.dump_table(fd, 'type_data', 'CmbBaseTypeDataInfo')
            self.dump_table(fd, 'type_data_arg', 'CmbBaseTypeDataArgInfo')
            self.dump_table(fd, 'type_child_type', 'CmbTypeChildInfo')

            # Project Objects
            self.dump_table(fd, 'ui', 'CmbBaseUI',
                            mutable=True)
            self.dump_table(fd, 'object_property', 'CmbBaseProperty',
                            mutable=True)
            self.dump_table(fd, 'object_layout_property', 'CmbBaseLayoutProperty',
                            mutable=True)
            self.dump_table(fd, 'object_signal', 'CmbSignal',
                            mutable=True)
            self.dump_table(fd, 'object', 'CmbBaseObject',
                            mutable=True)
            self.dump_table(fd, 'object_data', 'CmbBaseObjectData',
                            mutable=True)
            fd.close();


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Ussage: {sys.argv[0]} output.py")
        exit()

    db = CambalacheDb()
    db.dump(sys.argv[1])
