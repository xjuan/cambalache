/*
 * Data Model for Cambalache Project
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

/* Project global data
 *
 */

CREATE TABLE global (
  key TEXT PRIMARY KEY,
  value TEXT
) WITHOUT ROWID;

/* UI
 *
 */
CREATE TABLE ui (
  ui_id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id INTEGER DEFAULT NULL,

  name TEXT,
  filename TEXT UNIQUE,
  description TEXT,
  copyright TEXT,
  authors TEXT,
  license_id TEXT,
  translation_domain TEXT,
  comment TEXT,
  custom_fragment TEXT,
  FOREIGN KEY(ui_id, template_id) REFERENCES object(ui_id, object_id)
);

/* Remove old template type on update */
CREATE TRIGGER on_ui_template_id_update_remove_type AFTER UPDATE OF template_id ON ui
WHEN
  OLD.template_id IS NOT NULL AND
  (SELECT name FROM object WHERE ui_id=OLD.ui_id AND object_id=OLD.template_id) IS NOT NULL
BEGIN
  DELETE FROM type WHERE library_id IS NULL AND type_id=(SELECT name FROM object
      WHERE ui_id=OLD.ui_id AND object_id=OLD.template_id);
END;

/* Add new template type on update */
CREATE TRIGGER on_ui_template_id_update_add_type AFTER UPDATE OF template_id ON ui
WHEN
  NEW.template_id IS NOT NULL AND
  NEW.template_id IS NOT OLD.template_id AND
  (SELECT name FROM object WHERE ui_id=NEW.ui_id AND object_id=NEW.template_id) IS NOT NULL
BEGIN
  INSERT INTO type (type_id, parent_id)
    SELECT name, type_id FROM object WHERE ui_id=NEW.ui_id AND object_id=NEW.template_id
    ON CONFLICT DO NOTHING;

  INSERT INTO type_iface (type_id, iface_id)
    WITH v AS (SELECT name, type_id FROM object WHERE ui_id=NEW.ui_id AND object_id=NEW.template_id)
      SELECT v.name, t.iface_id FROM type_iface AS t, v WHERE t.type_id=v.type_id
    ON CONFLICT DO NOTHING;
END;


/* UI library version target
 *
 */
CREATE TABLE ui_library (
  ui_id INTEGER REFERENCES ui ON DELETE CASCADE,
  library_id TEXT,
  version TEXT,
  comment TEXT,
  PRIMARY KEY(ui_id, library_id),
  FOREIGN KEY(library_id, version) REFERENCES library_version
) WITHOUT ROWID;


/* CSS
 *
 */
CREATE TABLE css (
  css_id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT UNIQUE,
  priority INTEGER,
  is_global BOOLEAN
);


/* CSS UI mapping
 *
 */
CREATE TABLE css_ui (
  css_id INTEGER REFERENCES css ON DELETE CASCADE,
  ui_id INTEGER REFERENCES ui ON DELETE CASCADE,
  PRIMARY KEY(css_id, ui_id)
) WITHOUT ROWID;


/* GResource
 *
 */
CREATE TABLE gresource (
  gresource_id INTEGER PRIMARY KEY AUTOINCREMENT,
  resource_type TEXT CHECK (resource_type IN ('gresources', 'gresource', 'file')),
  parent_id INTEGER REFERENCES gresource ON DELETE CASCADE,
  position INTEGER NOT NULL CHECK (position >= 0),

  gresources_filename TEXT UNIQUE,

  gresource_prefix TEXT UNIQUE,

  file_filename TEXT,
  file_compressed BOOLEAN,
  file_preprocess TEXT,
  file_alias TEXT
);


/* Object
 *
 * TODO: check type_id is an object
 */
CREATE TABLE object (
  ui_id INTEGER REFERENCES ui ON DELETE CASCADE,
  object_id INTEGER,

  type_id TEXT NOT NULL REFERENCES type ON UPDATE CASCADE,
  name TEXT,
  parent_id INTEGER,
  internal TEXT,
  type TEXT,
  comment TEXT,
  position INTEGER NOT NULL CHECK(position >= 0),
  custom_fragment TEXT,
  custom_child_fragment TEXT,
  PRIMARY KEY(ui_id, object_id),
  FOREIGN KEY(ui_id, parent_id) REFERENCES object(ui_id, object_id) ON DELETE CASCADE
  UNIQUE(ui_id, parent_id, position)
) WITHOUT ROWID;

CREATE INDEX object_type_id_fk ON object (type_id);
CREATE INDEX object_parent_id_fk ON object (ui_id, parent_id);
CREATE INDEX object_ui_id_parent_id_position_idx ON object (ui_id, parent_id, position);


/* Update template name:
 * References to type will be automatically updated because of ON UPDATE CASCADE
 */
CREATE TRIGGER on_object_name_update_add_type AFTER UPDATE OF name ON object
WHEN
  OLD.name IS NULL AND
  NEW.name IS NOT NULL AND
  NEW.object_id IS (SELECT template_id FROM ui WHERE ui_id=NEW.ui_id)
BEGIN
  INSERT INTO type(type_id, parent_id, derivable) VALUES (NEW.name, NEW.type_id, 1);
END;

CREATE TRIGGER on_object_name_update_rename_type AFTER UPDATE OF name ON object
WHEN
  OLD.name IS NOT NULL AND
  NEW.name IS NOT NULL AND
  OLD.name IS NOT NEW.name AND
  NEW.object_id IS (SELECT template_id FROM ui WHERE ui_id=NEW.ui_id)
BEGIN
  UPDATE type SET type_id=NEW.name WHERE library_id IS NULL AND type_id=OLD.name;
END;

CREATE TRIGGER on_object_name_update_remove_type AFTER UPDATE OF name ON object
WHEN
  OLD.name IS NOT NULL AND
  NEW.name IS NULL AND
  NEW.object_id IS (SELECT template_id FROM ui WHERE ui_id=NEW.ui_id)
BEGIN
  DELETE FROM type WHERE library_id IS NULL AND type_id=OLD.name;
END;

CREATE TRIGGER on_object_insert_add_type AFTER INSERT ON object
WHEN
  NEW.name IS NOT NULL AND
  NEW.object_id IS (SELECT template_id FROM ui WHERE ui_id=NEW.ui_id)
BEGIN
  INSERT INTO type(type_id, parent_id, derivable)
    VALUES (NEW.name, NEW.type_id, 1)
  ON CONFLICT DO NOTHING;

  INSERT INTO type_iface (type_id, iface_id)
    SELECT NEW.name, iface_id FROM type_iface WHERE type_id=NEW.type_id
  ON CONFLICT DO NOTHING;
END;

CREATE TRIGGER on_object_delete_remove_type AFTER DELETE ON object
WHEN
  OLD.name IS NOT NULL AND
  OLD.object_id IS (SELECT template_id FROM ui WHERE ui_id=OLD.ui_id)
BEGIN
  DELETE FROM type WHERE library_id IS NULL AND type_id=OLD.name;
  UPDATE ui SET template_id=NULL WHERE ui_id=OLD.ui_id AND template_id=OLD.object_id;
END;

CREATE TRIGGER on_object_before_delete BEFORE DELETE ON object
BEGIN
/*
  Clear any property binding reference, We can not set ON DELETE SET NULL
  because object_property.ui_id can not be NULL
 */
  UPDATE object_property SET bind_source_id=NULL WHERE ui_id=OLD.ui_id AND bind_source_id=OLD.object_id;

/* Clear references to object */
  UPDATE object_property SET value=NULL
  FROM property AS p
  WHERE object_property.ui_id=OLD.ui_id AND
        object_property.owner_id = p.owner_id AND
        object_property.property_id = p.property_id AND
        p.is_object AND
        object_property.value = OLD.object_id;

/* Clear CmbAccessibleList references to object */
  UPDATE object_property SET value=cmb_object_list_remove(value, OLD.object_id)
  FROM property AS p
  WHERE object_property.ui_id=OLD.ui_id AND
        object_property.owner_id = p.owner_id AND
        object_property.property_id = p.property_id AND
  	p.type_id = 'CmbAccessibleList' AND
  	value IS NOT NULL;
END;


/* Object Property
 *
 * TODO: check owner_id is in object_id.type_id type tree
 */
CREATE TABLE object_property (
  ui_id INTEGER REFERENCES ui ON DELETE CASCADE,
  object_id INTEGER,
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  property_id TEXT,

  value TEXT,
  translatable BOOLEAN CHECK (translatable IS NULL OR (translatable IN (1, 0))),
  comment TEXT,
  translation_context TEXT,
  translation_comments TEXT,
  inline_object_id INTEGER,
  bind_source_id INTEGER,
  bind_owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  bind_property_id TEXT,
  bind_flags TEXT,
  PRIMARY KEY(ui_id, object_id, owner_id, property_id),
  FOREIGN KEY(ui_id, object_id) REFERENCES object(ui_id, object_id) ON DELETE CASCADE,
  FOREIGN KEY(ui_id, inline_object_id) REFERENCES object(ui_id, object_id) ON DELETE CASCADE,
  FOREIGN KEY(owner_id, property_id) REFERENCES property,
  FOREIGN KEY(ui_id, bind_source_id) REFERENCES object(ui_id, object_id),
  FOREIGN KEY(bind_owner_id, bind_property_id) REFERENCES property(owner_id, property_id) ON DELETE SET NULL
) WITHOUT ROWID;

CREATE INDEX object_property_object_fk ON object_property (ui_id, object_id);
CREATE INDEX object_property_property_fk ON object_property (owner_id, property_id);


/* Object Child Property
 *
 * TODO: check owner_id is in object_id.type_id type tree
 */
CREATE TABLE object_layout_property (
  ui_id INTEGER REFERENCES ui ON DELETE CASCADE,
  object_id INTEGER,
  child_id INTEGER,
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  property_id TEXT,

  value TEXT,
  translatable BOOLEAN CHECK (translatable IS NULL OR (translatable IN (1, 0))),
  comment TEXT,
  translation_context TEXT,
  translation_comments TEXT,
  PRIMARY KEY(ui_id, object_id, child_id, owner_id, property_id),
  FOREIGN KEY(ui_id, object_id) REFERENCES object ON DELETE CASCADE,
  FOREIGN KEY(ui_id, child_id) REFERENCES object(ui_id, object_id) ON DELETE CASCADE,
  FOREIGN KEY(owner_id, property_id) REFERENCES property
) WITHOUT ROWID;

CREATE INDEX object_layout_property_child_property_fk ON object_layout_property (owner_id, property_id);


/* Object Signal
 *
 * TODO: check owner_id is in object_id.type_id type tree
 */
CREATE TABLE object_signal (
  signal_pk INTEGER PRIMARY KEY AUTOINCREMENT,
  ui_id INTEGER REFERENCES ui ON DELETE CASCADE,
  object_id INTEGER,
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  signal_id TEXT,

  handler TEXT NOT NULL,
  detail TEXT,
  user_data INTEGER,
  swap BOOLEAN CHECK (swap IS NULL OR (swap IN (1, 0))),
  after BOOLEAN CHECK (after IS NULL OR (after IN (1, 0))),
  comment TEXT,
  FOREIGN KEY(ui_id, object_id) REFERENCES object ON DELETE CASCADE,
  FOREIGN KEY(owner_id, signal_id) REFERENCES signal
);

CREATE INDEX object_signal_object_fk ON object (ui_id, object_id);
CREATE INDEX object_signal_signal_fk ON object_signal (owner_id, signal_id);


/* Object Data
 *
 * This store any extra data defined in type_data table.
 * It allows generic loading and saving of custom type data without validation.
 */
CREATE TABLE object_data (
  ui_id INTEGER REFERENCES ui ON DELETE CASCADE,
  object_id INTEGER,
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  data_id INTEGER,
  id INTEGER,
  value TEXT,
  parent_id INTEGER,
  comment TEXT,
  translatable BOOLEAN CHECK (translatable IS NULL OR (translatable IN (1, 0))),
  translation_context TEXT,
  translation_comments TEXT,
  PRIMARY KEY(ui_id, object_id, owner_id, data_id, id),
  FOREIGN KEY(ui_id, object_id) REFERENCES object ON DELETE CASCADE,
  FOREIGN KEY(owner_id, data_id) REFERENCES type_data
);


/* Object Data Arg
 *
 */
CREATE TABLE object_data_arg (
  ui_id INTEGER REFERENCES ui ON DELETE CASCADE,
  object_id INTEGER,
  owner_id TEXT REFERENCES type ON UPDATE CASCADE,
  data_id INTEGER,
  id INTEGER,
  key TEXT,
  value TEXT,
  PRIMARY KEY(ui_id, object_id, owner_id, data_id, id, key),
  FOREIGN KEY(ui_id, object_id, owner_id, data_id, id) REFERENCES object_data ON DELETE CASCADE,
  FOREIGN KEY(owner_id, data_id, key) REFERENCES type_data_arg
);

