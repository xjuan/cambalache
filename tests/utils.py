#
# Unit Tests utils
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

import io
import cairo
import struct

from gi.repository import GLib, Gtk


# Based on Gtk sources gtk-reftest.c
def wait_for_drawing(window):
    def on_window_draw(widget, cr, loop):
        loop.quit()
        return False

    def quit_when_idle(loop):
        loop.quit()
        return GLib.SOURCE_REMOVE

    loop = GLib.MainLoop()

    # We wait until the widget is drawn for the first time.
    # We are running in a dedicated compositor so the window should not be obstructed by other windows
    window.connect("draw", on_window_draw, loop)
    loop.run()
    window.disconnect_by_func(on_window_draw)

    # give the WM/server some time to sync. They need it.
    window.get_display().sync()
    GLib.timeout_add(500, quit_when_idle, loop)
    loop.run()


def surface_write_ppm(surface, path):
    data = surface.get_data()
    w = surface.get_width()
    h = surface.get_height()

    with open(path, "wb") as fd:
        fd.write(bytes(f"P6\n#Created by Cambalache tests/utils.py\n#\n{w} {h}\n255\n", "utf-8"))
        for r, g, b, a in struct.iter_unpack("BBBB", data):
            fd.write(bytes([r, g, b]))
        fd.close()


def window_screenshot(window):
    if window is None:
        return None

    # Wait for window to finish drawing
    wait_for_drawing(window)

    w = window.get_allocated_width()
    h = window.get_allocated_height()

    # Draw widget to cairo surface
    surface = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    cr = cairo.Context(surface)
    window.draw(cr)

    surface.flush()

    return surface


def image_reload_as_png(surface):
    screenshot_png_bytes = io.BytesIO()
    surface.write_to_png(screenshot_png_bytes)
    screenshot_png_bytes.seek(0)
    return cairo.ImageSurface.create_from_png(screenshot_png_bytes)


def mean_squared_error(original, screenshot, ignore_color=None):
    original_data = original.get_data()
    screenshot_data = screenshot.get_data()

    n = original.get_width() * original.get_height()

    if len(original_data) != len(screenshot_data):
        raise ValueError("Screenshot has different size")

    # Calculate mean squared error for each channel
    red = 0.0
    green = 0.0
    blue = 0.0
    for i in range(0, n):
        offset = i * 4
        r, g, b, a = struct.unpack_from("BBBB", original_data, offset)
        rr, gg, bb, aa = struct.unpack_from("BBBB", screenshot_data, offset)

        if ignore_color is not None:
            ir, ig, ib = ignore_color
            if r == ir and g == ig and b == ib:
                continue

        red += (r / 255.0 - rr / 255.0) ** 2
        green += (g / 255.0 - gg / 255.0) ** 2
        blue += (b / 255.0 - bb / 255.0) ** 2

    total = 0.2126 * red + 0.7152 * green + 0.0722 * blue

    return red / n, green / n, blue / n, total / n


def process_all_pending_gtk_events():
    while Gtk.events_pending():
        Gtk.main_iteration_do(False)


def find_by_buildable_id(widget, name):
    retval = None

    if isinstance(widget, Gtk.Buildable) and Gtk.Buildable.get_name(widget) == name:
        return widget

    if not isinstance(widget, Gtk.Container):
        return None

    for child in widget.get_children():
        if isinstance(child, Gtk.Container):
            retval = find_by_buildable_id(child, name)
            if retval:
                return retval

        if isinstance(child, Gtk.Buildable) and Gtk.Buildable.get_name(child) == name:
            return child

    return retval


def cmb_create_app():
    from cambalache.app import CmbApplication

    app = CmbApplication()
    app.register()
    app.activate()

    window = None

    # Spin until we get the main window
    while Gtk.events_pending() and not window:
        Gtk.main_iteration_do(False)

        # Get window if any
        windows = app.get_windows()
        if len(windows):
            window = windows[0]

    return app, window


def cmb_destroy_app(app, window):
    window.activate_action("close", None)
    process_all_pending_gtk_events()
    window.destroy()
    app.quit()

    process_all_pending_gtk_events()
