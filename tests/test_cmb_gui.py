#
# GUI Unit Tests
#
# Copyright (C) 2023  Juan Pablo Ugarte
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

import os
import time
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from . import utils


basedir = os.path.join(os.path.dirname(__file__))

app = None


def setup_module(module):
    global app

    wayland_display = os.environ.get("WAYLAND_DISPLAY", None)

    # Wait for compositor to startup
    if utils.wait_for_file(wayland_display, 2):
        assert False
        return

    # load module that setup everything locally to run cambalache
    from cambalache.app import CmbApplication

    app = CmbApplication()
    app.register()
    app.activate()

    # Spin until we get the main window
    while Gtk.events_pending() and not len(app.get_windows()):
        Gtk.main_iteration_do(False)


def app_get_window():
    windows = app.get_windows()
    assert len(windows)
    return windows[0]


def app_window_activate_action(action_name):
    window = app_get_window()
    assert window

    window.activate_action(action_name, None)
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)


def cmb_run(original_basename, target=None, ui_basename=None):
    assert original_basename

    # Ensure Image directory
    if target:
        imagedir = os.path.join(basedir, "images", target)
    else:
        imagedir = os.path.join(basedir, "images")
    os.makedirs(imagedir, exist_ok=True)

    # Import UI file
    if ui_basename and target:
        path = os.path.join(basedir, target, ui_basename)
        app.import_file(path)

        original_path = os.path.join(imagedir, f"{ui_basename}.png")
    else:
        original_path = os.path.join(imagedir, original_basename)

    # Get MSE
    ignore_color = (0xf5, 0x00, 0xf5)
    r, g, b, total, screenshot = utils.mean_squared_error(app_get_window(), original_path, ignore_color)

    # File did not exist and it was created
    assert r is not None

    # Save difference image if its not the same
    if total != 0:
        screenshot.write_to_png(os.path.splitext(original_path)[0] + ".screenshot.png")

    # Check its the same image
    # TODO: find a good value
    assert (r, g, b, total) == (0, 0, 0, 0)


def cmb_window_new(target):
    # Newly created project, should show UI editor
    app_window_activate_action("new")
    cmb_run("cambalache_new.png", target)


def cmb_window_add_window(target):
    window = app_get_window()
    project = window.project

    # Select GtkWindow type and add new object
    window.type_chooser.select_type_id("GtkWindow")
    app_window_activate_action("add_object")

    # Select newly created window, should show property editor
    win = project.get_object_by_id(1, 1)
    project.set_selection([win])

    cmb_run("cambalache_add_window.png", target)


# TESTS
def test_cmb_window():
    # Main window, TODO add mask for version
    cmb_run("cambalache.png")


def test_cmb_window_create_new():
    # New project view
    app_window_activate_action("create_new")
    cmb_run("cambalache_create_new.png")

# Gtk 3
def test_gtk3_cmb_window_new():
    cmb_window_new("gtk+-3.0")


def test_gtk3_cmb_window_add_window():
    cmb_window_add_window("gtk+-3.0")


# Gtk 4
def test_gtk4_cmb_window_new():
    app_window_activate_action("close")
    cmb_window_new("gtk-4.0")


def test_gtk4_cmb_window_add_window():
    cmb_window_add_window("gtk-4.0")
