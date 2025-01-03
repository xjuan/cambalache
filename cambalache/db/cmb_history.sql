/*
 * Data Model for Cambalache Project History
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

/*
 * Implement undo/redo stack with triggers
 *
 * We should be able to store the whole project history if we want to.
 *
 * history_* tables and triggers are auto generated to avoid copy/paste errors
 */

INSERT INTO global VALUES('history_enabled', TRUE);
INSERT INTO global VALUES('history_index', -1);

/* Main history table */

CREATE TABLE history (
  history_id INTEGER PRIMARY KEY,
  command TEXT NOT NULL,
  range_id INTEGER REFERENCES history,
  table_name TEXT,
  columns JSON,
  message TEXT,
  table_pk JSON,
  new_values JSON,
  old_values JSON
);

/* This trigger will update PUSH/POP range and data automatically on POP */
CREATE TRIGGER on_history_pop_insert AFTER INSERT ON history
WHEN
  NEW.command is 'POP'
BEGIN
/* Update range_id and message from last PUSH command */
  UPDATE history
  SET (range_id, message)=(SELECT history_id, message FROM history WHERE command='PUSH' AND range_id IS NULL ORDER BY history_id DESC LIMIT 1)
  WHERE history_id = NEW.history_id;

/* Update range_id in last PUSH command */
  UPDATE history
  SET range_id=NEW.history_id
  WHERE history_id=(SELECT range_id FROM history WHERE history_id = NEW.history_id);
END;

