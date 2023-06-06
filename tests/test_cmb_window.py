#!/usr/bin/pytest
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
import cairo

from . import utils

basedir = os.path.dirname(__file__)


# Global GtkApplication and CmbWindow
app = None
window = None


def setup_module(module):
    global app, window
    app, window = utils.cmb_create_app()


def teardown_module(module):
    global app, window
    utils.cmb_destroy_app(app, window)
    app = None
    window = None


def window_assert_screenshot(original_basename, target=None, ui_basename=None):
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

    # Get Screenshot
    screenshot = utils.window_screenshot(window)

    # Get original image to compare
    if os.path.exists(original_path):
        original = cairo.ImageSurface.create_from_png(original_path)
    else:
        # Write window surface as original if file is not found and return
        screenshot.write_to_png(original_path)
        return

    # NOTE: Saving or Loading the image as PNG slightly changes the pixel values (premultiplication, etc)
    # So in order to avoid any difference we always compare data processed in exactly the same way
    screenshot = utils.image_reload_as_png(screenshot)

    # Get MSE
    ignore_color = (0xF5, 0x00, 0xF5)
    r, g, b, total = utils.mean_squared_error(original, screenshot, ignore_color)

    assert r is not None

    # Save difference image if its not the same
    if total != 0:
        screenshot.write_to_png(os.path.splitext(original_path)[0] + ".screenshot.png")

    # Check its the same image
    # TODO: find a good value
    assert (r, g, b, total) == (0, 0, 0, 0)


def window_activate_action(action_name):
    window.activate_action(action_name, None)
    utils.process_all_pending_gtk_events()


def window_button_clicked(button_name):
    button = utils.find_by_buildable_id(window, button_name)
    assert button
    button.clicked()
    utils.process_all_pending_gtk_events()
    return button


def window_entry_set_text(entry_name, text):
    entry = utils.find_by_buildable_id(window, entry_name)
    assert entry
    entry.set_text(text)
    utils.process_all_pending_gtk_events()
    return entry


def window_stack_set_page(stack_name, page):
    stack = utils.find_by_buildable_id(window, stack_name)
    assert stack

    stack.set_visible_child_name(page)
    utils.process_all_pending_gtk_events()

    return stack


def window_widget_grab_focus(widget):
    widget = utils.find_by_buildable_id(window, widget)
    assert widget
    widget.grab_focus()


def window_add_object(klass, obj_id, ui_id=1):
    project = window.project

    window.type_chooser.select_type_id(klass)
    window.activate_action("add_object", None)
    utils.process_all_pending_gtk_events()

    obj = project.get_object_by_id(ui_id, obj_id)
    project.set_selection([obj])


# TESTS
def _test_new_button(target):
    # New project view
    window_button_clicked("new_button")
    window_entry_set_text("np_name_entry", "test_project")

    button = "np_gtk3_radiobutton" if target == "gtk+-3.0" else "np_gtk4_radiobutton"
    window_button_clicked(button)
    window_widget_grab_focus(button)

    window_assert_screenshot("cambalache_new_button.png", target)


def _test_np_create_button(target):
    window_button_clicked("np_create_button")
    window_assert_screenshot("cambalache_np_create_button.png", target)


def _test_cmb_window_ui_stack_fragment(target):
    ui = window.project.get_object_by_id(1)

    ui.custom_fragment = """<menu id="menubar">
  <submenu>
    <attribute name="label">File</attribute>
  </submenu>
  <submenu>
    <attribute name="label">Edit</attribute>
  </submenu>
  <submenu>
    <attribute name="label">Help</attribute>
  </submenu>
</menu>"""

    window_stack_set_page("ui_stack", "fragment")
    window_assert_screenshot("cambalache_ui_stack_fragment.png", target)


def _test_cmb_window_add_window(target):
    window_add_object("GtkWindow", 1)
    window_assert_screenshot("cambalache_add_window.png", target)


def _test_cmb_window_object_stack_layout(target):
    window_add_object("GtkGrid", 2)
    window_add_object("GtkButton", 3)

    window_stack_set_page("object_stack", "layout")
    window_assert_screenshot("cambalache_object_stack_layout.png", target)


def _test_cmb_window_object_stack_signals(target):
    button = window.project.get_object_by_id(1, 3)

    button.add_signal("GtkButton", "clicked", "on_button_clicked")

    window_stack_set_page("object_stack", "signals")
    window_assert_screenshot("cambalache_object_stack_signals.png", target)


def _test_cmb_window_object_stack_fragment(target):
    button = window.project.get_object_by_id(1, 3)
    button.custom_fragment = '<styles><style name="acustomstyle"></styles>'

    window_stack_set_page("object_stack", "fragment")
    window_assert_screenshot("cambalache_object_stack_fragment.png", target)


# Common Tests
def test_cmb_window():
    window_assert_screenshot("cambalache.png")


# Gtk 3
def test_gtk3_new_button():
    _test_new_button("gtk+-3.0")


def test_gtk3_np_create_button():
    _test_np_create_button("gtk+-3.0")


def test_gtk3_cmb_window_ui_stack_fragment():
    _test_cmb_window_ui_stack_fragment("gtk+-3.0")


def test_gtk3_cmb_window_add_window():
    _test_cmb_window_add_window("gtk+-3.0")


def test_gtk3_cmb_window_object_stack_layout():
    _test_cmb_window_object_stack_layout("gtk+-3.0")


def test_gtk3_cmb_window_object_stack_signals():
    _test_cmb_window_object_stack_signals("gtk+-3.0")


def test_gtk3_cmb_window_object_stack_fragment():
    _test_cmb_window_object_stack_fragment("gtk+-3.0")


# Reset UI to start with the same tests for Gtk 4
def test_cmb_window_close():
    global window

    window.destroy()
    app.open_project(None)

    windows = app.get_windows()
    assert len(windows)

    window = windows[0]

    window_assert_screenshot("cambalache.png")


# Gtk 4
def test_gtk4_new_button():
    _test_new_button("gtk-4.0")


def test_gtk4_np_create_button():
    _test_np_create_button("gtk-4.0")


def test_gtk4_cmb_window_ui_stack_fragment():
    _test_cmb_window_ui_stack_fragment("gtk-4.0")


def test_gtk4_cmb_window_add_window():
    _test_cmb_window_add_window("gtk-4.0")


def test_gtk4_cmb_window_object_stack_layout():
    _test_cmb_window_object_stack_layout("gtk-4.0")


def test_gtk4_cmb_window_object_stack_signals():
    _test_cmb_window_object_stack_signals("gtk-4.0")


def test_gtk4_cmb_window_object_stack_fragment():
    _test_cmb_window_object_stack_fragment("gtk-4.0")
