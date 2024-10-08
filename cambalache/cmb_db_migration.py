#
# CmbDBmigration - Cambalache DataBase Migration functions
#
# Copyright (C) 2021-2023  Juan Pablo Ugarte
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


def ensure_columns_for_0_7_5(table, data):
    if table == "object":
        # Append position column
        return [row + (None,) for row in data]
    elif table in ["object_property", "object_layout_property"]:
        # Append translation_context, translation_comments columns
        return [row + (None, None) for row in data]

    return data


def migrate_table_data_to_0_7_5(c, table, data):
    if table == "object":
        c.execute(
            """
            UPDATE temp.object SET position=new.position - 1
            FROM (
                SELECT row_number() OVER (PARTITION BY parent_id ORDER BY object_id) position, ui_id, object_id
                FROM temp.object
                WHERE parent_id IS NOT NULL
            ) AS new
            WHERE temp.object.ui_id=new.ui_id AND temp.object.object_id=new.object_id;
            """
        )
        c.execute(
            """
            UPDATE temp.object SET position=new.position - 1
            FROM (
                SELECT row_number() OVER (PARTITION BY ui_id ORDER BY object_id) position, ui_id, object_id
                FROM temp.object
                WHERE parent_id IS NULL
            ) AS new
            WHERE temp.object.ui_id=new.ui_id AND temp.object.object_id=new.object_id;
            """
        )


def ensure_columns_for_0_9_0(table, data):
    if table == "object_property":
        # Append inline_object_id column
        return [row + (None,) for row in data]

    return data


def migrate_table_data_to_0_9_0(c, table, data):
    if table == "object_property":
        # Remove all object properties with a 0 as value
        c.execute(
            """
            DELETE FROM temp.object_property AS op
            WHERE value = 0 AND
                (SELECT property_id FROM temp.property WHERE owner_id=op.owner_id AND property_id=op.property_id AND is_object)
            IS NOT NULL;
            """
        )


def ensure_columns_for_0_11_2(table, data):
    if table in ["object", "ui"]:
        # Append custom_text column
        return [row + (None,) for row in data]

    return data


def ensure_columns_for_0_11_4(table, data):
    if table == "object_property":
        # Append bind_[source_id owner_id property_id flags] column
        return [row + (None, None, None, None) for row in data]

    return data


def ensure_columns_for_0_13_1(table, data):
    if table == "object_data":
        # Append translatable, translation_context, translation_comments columns
        return [row + (None, None, None) for row in data]

    return data


def ensure_columns_for_0_17_3(table, data):
    if table == "object":
        # Append custom_child_fragment column
        return [row + (None,) for row in data]

    return data


def migrate_table_data_to_0_17_3(c, table, data):
    if table in ["object_property", "object_layout_property", "object_data"]:
        c.executescript(
            f"""
            UPDATE temp.{table} SET translatable=1
            WHERE translatable IS NOT NULL AND lower(translatable) IN (1, 'y', 'yes', 't', 'true');
            UPDATE temp.{table} SET translatable=NULL
            WHERE translatable IS NOT NULL AND translatable != 1;
            """
        )

    if table == "object_signal":
        for prop in ["swap", "after"]:
            c.executescript(
                f"""
                UPDATE temp.object_signal SET {prop}=1
                WHERE {prop} IS NOT NULL AND lower({prop}) IN (1, 'y', 'yes', 't', 'true');
                UPDATE temp.object_signal SET {prop}=NULL WHERE {prop} IS NOT NULL AND after != 1;
                """
            )


def migrate_table_data_to_0_91_3(c, table, data):
    # Ensure every object has a position
    if table == "object":
        c.execute(
            """
            UPDATE temp.object SET position=new.position - 1
            FROM (
                SELECT row_number() OVER (PARTITION BY ui_id, parent_id ORDER BY position, object_id) position, ui_id, object_id
                FROM temp.object
                WHERE parent_id IS NOT NULL
            ) AS new
            WHERE temp.object.ui_id=new.ui_id AND temp.object.object_id=new.object_id;
            """
        )
        c.execute(
            """
            UPDATE temp.object SET position=new.position - 1
            FROM (
                SELECT row_number() OVER (PARTITION BY ui_id ORDER BY object_id) position, ui_id, object_id
                FROM temp.object
                WHERE parent_id IS NULL
            ) AS new
            WHERE temp.object.ui_id=new.ui_id AND temp.object.object_id=new.object_id;
            """
        )
