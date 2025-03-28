/*
 * Base Data Model for Cambalache Project
 *
 * Copyright (C) 2020  Juan Pablo Ugarte
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation;
 * version 2.1 of the License.
 *
 * library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * Authors:
 *   Juan Pablo Ugarte <juanpablougarte@gmail.com>
 *
 * SPDX-License-Identifier: LGPL-2.1-only
 */

/** Common Data Model **/

/* Library
 *
 * Support for different libraries
 */
CREATE TABLE IF NOT EXISTS library (
  library_id TEXT PRIMARY KEY,
  version TEXT NOT NULL,
  namespace TEXT NOT NULL UNIQUE,
  prefix TEXT NOT NULL,
  shared_library TEXT,
  license_id TEXT,
  license_text TEXT
) WITHOUT ROWID;


/* Library dependecies
 *
 */
CREATE TABLE IF NOT EXISTS library_dependency (
  library_id TEXT REFERENCES library,
  dependency_id TEXT REFERENCES library,
  PRIMARY KEY(library_id, dependency_id)
) WITHOUT ROWID;


/* Library targeteable versions
 *
 */
CREATE TABLE IF NOT EXISTS library_version (
  library_id TEXT REFERENCES library,
  version TEXT,
  PRIMARY KEY(library_id, version)
) WITHOUT ROWID;


/* Type
 *
 * Base table to keep type information
 */
CREATE TABLE IF NOT EXISTS type (
  type_id TEXT PRIMARY KEY,

  parent_id TEXT REFERENCES type ON UPDATE CASCADE,
  library_id TEXT REFERENCES library,
  version TEXT,
  deprecated_version TEXT,
  abstract BOOLEAN,
  derivable BOOLEAN,
  layout TEXT CHECK (layout IN ('container', 'manager', 'child')),
  category TEXT CHECK (category IN ('toplevel', 'layout', 'control', 'display', 'model', 'hidden')),
  workspace_type TEXT
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS type_parent_id_fk ON type (parent_id);
CREATE INDEX IF NOT EXISTS type_library_id_fk ON type (library_id);

/* Add fundamental types */
INSERT INTO type (type_id) VALUES
 ('object'), ('interface'), ('enum'), ('flags'), ('gtype'), ('boxed'), ('variant'),
 ('gchar'), ('guchar'), ('gunichar'), ('gchararray'),
 ('gboolean'),
 ('gint'), ('guint'), ('glong'), ('gulong'), ('gint64'), ('guint64'),
 ('gfloat'), ('gdouble');


/* Type Interfaces
 *
 * Keep a list of interfaces implemented by type
 */
CREATE TABLE IF NOT EXISTS type_iface (
  type_id TEXT REFERENCES type ON UPDATE CASCADE ON DELETE CASCADE,
  iface_id TEXT REFERENCES type ON UPDATE CASCADE ON DELETE CASCADE,
  PRIMARY KEY(type_id, iface_id)
) WITHOUT ROWID;


/* Enumerations
 *
 */
CREATE TABLE IF NOT EXISTS type_enum (
  type_id TEXT REFERENCES type ON UPDATE CASCADE,
  name TEXT,
  nick TEXT,
  value INTEGER,
  doc TEXT,
  PRIMARY KEY(type_id, name)
) WITHOUT ROWID;


/* Flags
 *
 */
CREATE TABLE IF NOT EXISTS type_flags (
  type_id TEXT REFERENCES type ON UPDATE CASCADE,
  name TEXT,
  nick TEXT,
  value INTEGER,
  doc TEXT,
  PRIMARY KEY(type_id, name)
) WITHOUT ROWID;


/* Type Data
 *
 * This table allow us to store extra data for each type in a hierarchical way.
 * It does not have any particular restrictions which means it is responsibility
 * of the editor to create a valid structure.
 */
CREATE TABLE IF NOT EXISTS type_data (
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  data_id INTEGER,
  parent_id INTEGER,
  key TEXT NOT NULL,
  type_id TEXT REFERENCES type ON UPDATE CASCADE,
  translatable BOOLEAN CHECK (type_id IN (NULL, 'gchararray')),
  PRIMARY KEY(owner_id, data_id),
  FOREIGN KEY(owner_id, parent_id) REFERENCES type_data(owner_id, data_id)
) WITHOUT ROWID;


/* Type Data Args
 *
 */
CREATE TABLE IF NOT EXISTS type_data_arg (
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  data_id INTEGER,
  key TEXT NOT NULL,
  type_id TEXT REFERENCES type ON UPDATE CASCADE,
  PRIMARY KEY(owner_id, data_id, key),
  FOREIGN KEY(owner_id, data_id) REFERENCES type_data(owner_id, data_id)
) WITHOUT ROWID;


/* Type Child constraints
 *
 */
CREATE TABLE IF NOT EXISTS type_child_constraint (
  type_id TEXT REFERENCES type ON UPDATE CASCADE,
  child_type_id TEXT REFERENCES type ON UPDATE CASCADE,
  allowed BOOLEAN DEFAULT 1,
  shortcut BOOLEAN,
  PRIMARY KEY(type_id, child_type_id)
) WITHOUT ROWID;


/* Type Internal Child
 *
 */
CREATE TABLE IF NOT EXISTS type_internal_child (
  type_id TEXT REFERENCES type ON UPDATE CASCADE,
  internal_child_id TEXT,
  internal_parent_id TEXT,
  internal_type TEXT REFERENCES type ON UPDATE CASCADE,
  creation_property_id TEXT,
  PRIMARY KEY(type_id, internal_child_id),
  FOREIGN KEY(type_id, internal_parent_id) REFERENCES type_internal_child(type_id, internal_child_id)
  FOREIGN KEY(type_id, creation_property_id) REFERENCES property(owner_id, property_id)
) WITHOUT ROWID;


/* Property
 *
 */
CREATE TABLE IF NOT EXISTS property (
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  property_id TEXT NOT NULL,

  type_id TEXT REFERENCES type ON UPDATE CASCADE,
  is_object BOOLEAN,
  construct_only BOOLEAN,
  save_always BOOLEAN,
  default_value TEXT,
  minimum TEXT,
  maximum TEXT,
  version TEXT,
  deprecated_version TEXT,
  translatable BOOLEAN CHECK (type_id IN (NULL, 'gchararray')),
  disable_inline_object BOOLEAN DEFAULT 0,
  deprecated TEXT,
  required BOOLEAN DEFAULT 0,
  workspace_default TEXT,
  original_owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  disabled BOOLEAN DEFAULT 0,
  PRIMARY KEY(owner_id, property_id)
  FOREIGN KEY(original_owner_id, property_id) REFERENCES property(owner_id, property_id)
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS property_type_id_fk ON property (type_id);

/* Check property:owner_id is not fundamental */
CREATE TRIGGER IF NOT EXISTS on_property_before_insert_check BEFORE INSERT ON property
BEGIN
  SELECT
    CASE
      WHEN (SELECT parent_id FROM type WHERE type_id=NEW.owner_id) IS NULL THEN
            RAISE (ABORT,'owner_id is not an object type')
    END;
END;


/* Signal
 *
 */
CREATE TABLE IF NOT EXISTS signal (
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  signal_id TEXT NOT NULL,

  version TEXT,
  deprecated_version TEXT,
  detailed BOOLEAN,
  PRIMARY KEY(owner_id, signal_id)
) WITHOUT ROWID;

/* Check signal:owner_id is not fundamental */
CREATE TRIGGER IF NOT EXISTS on_signal_before_insert_check BEFORE INSERT ON signal
BEGIN
  SELECT
    CASE
      WHEN (SELECT parent_id FROM type WHERE type_id=NEW.owner_id) IS NULL THEN
            RAISE (ABORT,'owner_id is not an object type')
    END;
END;


/* Type Child types
 *
 */
CREATE TABLE IF NOT EXISTS type_child_type (
  type_id TEXT REFERENCES type ON UPDATE CASCADE,
  child_type TEXT,
  max_children INTEGER,
  linked_property_id TEXT,
  PRIMARY KEY(type_id, child_type),
  FOREIGN KEY(type_id, linked_property_id) REFERENCES property(owner_id, property_id)
) WITHOUT ROWID;
