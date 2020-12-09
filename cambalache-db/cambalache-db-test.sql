/*
 * CambalacheDB - Data Model for Cambalache
 *
 * Copyright (C) 2020  Juan Pablo Ugarte - All Rights Reserved
 *
 * Unauthorized copying of this file, via any medium is strictly prohibited.
 */

/* Test model */

INSERT INTO type (type_id, parent) VALUES
('GtkWidget', 'object'),
('GtkWindow', 'GtkWidget'),
('GtkImage', 'GtkWidget'),
('GtkBox', 'GtkWidget'),
('GtkLabel', 'GtkWidget'),
('GtkButton', 'GtkWidget'),
('GtkToggleButton', 'GtkButton');

INSERT INTO property (owner_id, property_id, type_id) VALUES
('GtkWidget', 'name', 'string'),
('GtkWidget', 'parent', 'GtkWidget'),
('GtkImage', 'file', 'string'),
('GtkBox', 'orientation', 'enum'),
('GtkLabel', 'label', 'string'),
('GtkButton', 'label', 'string'),
('GtkButton', 'image', 'GtkImage'),
('GtkToggleButton', 'active', 'boolean');

INSERT INTO child_property (owner_id, property_id, type_id) VALUES
('GtkBox', 'position', 'int'),
('GtkBox', 'expand', 'boolean'),
('GtkBox', 'fill', 'boolean');


INSERT INTO signal (owner_id, signal_id) VALUES
('GtkWidget', 'event'),
('GtkBox', 'add'),
('GtkBox', 'remove'),
('GtkButton', 'clicked'),
('GtkToggleButton', 'toggled');

/* Test Project */

INSERT INTO object (type_id, name, parent_id) VALUES
('GtkWindow', 'main', NULL),
('GtkBox', 'box', 1),
('GtkLabel', 'label', 2),
('GtkButton', 'button', 2);

INSERT INTO object_property (object_id, owner_id, property_id, value) VALUES
(3, 'GtkLabel', 'label', 'Hello World'),
(4, 'GtkButton', 'label', 'Click Me');

INSERT INTO object_child_property (object_id, child_id, owner_id, property_id, value) VALUES
(1, 3, 'GtkBox', 'position', 1),
(1, 3, 'GtkBox', 'expand', 1),
(1, 4, 'GtkBox', 'position', 2),
(1, 4, 'GtkBox', 'fill', 0);

INSERT INTO object_signal (object_id, owner_id, signal_id, handler) VALUES
(4, 'GtkButton', 'clicked', 'on_button_clicked');

INSERT INTO interface (name, filename) VALUES ('Test UI', 'test.ui');

INSERT INTO interface_object (interface_id, object_id) VALUES (1, 1);

