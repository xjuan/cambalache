#
# CmbTutorial
#
# Copyright (C) 2021-2024  Juan Pablo Ugarte
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

from .cmb_tutor import CmbTutorPosition
from cambalache import _

intro = [
    (_("Hi, I will show you around Cambalache"), "intro_button", 5),
    (_("You can open a project and find recently used"), "open_button", 5),
    (_("Common actions like Undo"), "undo_button", 4),
    (_("Redo"), "redo_button", 2),
    (_("and Add new UI are directly accessible in the headerbar"), "add_button", 3),
    (_("together with the main menu"), "menu_button", 3),
    (
        _("Where you can create a new project"),
        _("New Project"),
        5,
        None,
        CmbTutorPosition.LEFT,
    ),
    (
        _("Import UI files"),
        _("Import"),
        3,
        None,
        CmbTutorPosition.LEFT,
    ),
    (_("Create a project to continue"), "intro_button", 2, "add-project"),
    (_("Great!"), "intro_button", 2),
    (
        _("This is the project workspace, where you can see and select the widgets to edit"),
        "view",
        6,
        None,
        CmbTutorPosition.CENTER,
    ),
    (_("Project tree, with multiple UI support"), "tree_view", 4, None, CmbTutorPosition.CENTER),
    (
        _("Class selector bar"),
        "type_chooser_box",
        3,
    ),
    (_("And the object editor"), "editor_stack", 3, None, CmbTutorPosition.CENTER),
    (_("You can search all supported classes here"), "type_chooser_all", 4, "show-type-popover", CmbTutorPosition.LEFT),
    (_("or investigate what is in each group"), "type_chooser_gtk", 4, "show-type-popover-gtk", CmbTutorPosition.LEFT),
    (_("Now let's add a new UI file"), "add_button", 5, "add-ui"),
    (_("Good, now try to create a window"), "intro_button", 4, "add-window"),
    (_("Excellent!"), "intro_button", 2),
    (_("BTW, did you know you can double click on any placeholder to create widgets?"), "intro_button", 5),
    (_("Try adding a grid"), "intro_button", 3, "add-grid"),
    (_("and a button"), "intro_button", 3, "add-button"),
    (_("Quite easy! Isn't it?"), "intro_button", 3),
    (
        _("Once you finish, you can export all UI files to xml here"),
        _("Export all"),
        5,
        None,
        CmbTutorPosition.LEFT,
    ),
    (
        _("If you have any question, contact us on Matrix!"),
        _("Contact"),
        7,
        None,
        CmbTutorPosition.LEFT,
    ),
    (
        _("That is all for now.\nIf you find Cambalache useful please consider donating"),
        _("Donate"),
        7,
        "donate",
        CmbTutorPosition.LEFT,
    ),
    (_("Have a nice day!"), "intro_button", 3, "intro-end"),
]
