#
# utils - Cambalache utilities
#
# Copyright (C) 2023-2024  Juan Pablo Ugarte
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

from gi.repository import Gdk, Gtk


def parse_version(version):
    return tuple([int(x) for x in version.split(".")])


def version_cmp(a, b):
    an = len(a)
    bn = len(a)

    for i in range(0, max(an, bn)):
        val_a = a[i] if i < an else 0
        val_b = b[i] if i < bn else 0
        retval = val_a - val_b

        if retval != 0:
            return retval

    return 0


def version_cmp_str(a, b):
    return version_cmp(parse_version(a), parse_version(b))


def get_version_warning(target, version, deprecated_version, this):
    if not target:
        return None

    if version and version_cmp_str(target, version) < 0:
        return f"UI targets {target} but {this} was introduced in {version}"
    elif deprecated_version and version_cmp_str(target, deprecated_version) >= 0:
        return f"UI targets {target} but {this} was deprecated in {deprecated_version}"

    return None


def widget_get_children(widget):
    retval = []

    child = widget.get_first_child()
    while child is not None:
        retval.append(child)
        child = child.get_next_sibling()

    return retval


def get_pointer(widget):
    root = widget.get_root()
    pointer = widget.get_display().get_default_seat().get_pointer()
    valid, x, y, mask = root.get_surface().get_device_position(pointer)

    if valid:
        return root.translate_coordinates(widget, x, y)

    return (None, None)


def get_pointing_to(widget):
    r = Gdk.Rectangle()
    r.x, r.y = get_pointer(widget)
    r.width = r.height = 0
    return r
