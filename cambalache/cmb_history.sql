/*
 * Data Model for Cambalache Project History
 *
 * Copyright (C) 2020  Juan Pablo Ugarte - All Rights Reserved
 *
 * Unauthorized copying of this file, via any medium is strictly prohibited.
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
  column_name TEXT,
  message TEXT
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

