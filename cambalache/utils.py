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
# SPDX-License-Identifier: LGPL-2.1-only
#

import hashlib

from lxml import etree
from gi.repository import Gdk, Gio


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

    if not valid:
        return (None, None)

    sx, sy = root.get_surface_transform()
    return root.translate_coordinates(widget, x - sx, y - sy)


def get_pointing_to(widget):
    r = Gdk.Rectangle()
    r.x, r.y = get_pointer(widget)
    r.width = r.height = 0
    return r


def content_type_guess(path):
    content_type, uncertain = Gio.content_type_guess(path, None)
    if uncertain:
        with open(path, "rb") as fd:
            data = fd.read(1024)
        content_type, uncertain = Gio.content_type_guess(path, data)

    return content_type


# XML utilities

def xml_node_get(node, *args, errors=None):
    keys = node.keys()
    knowns = []
    retval = []

    def get_key_val(node, attr):
        tokens = attr.split(":")
        key = tokens[0]
        val = node.get(key, None)

        if len(tokens) > 1:
            t = tokens[1]
            if t == "bool":
                return (key, val.lower() in {"1", "t", "y", "true", "yes"} if val else False)
            elif t == "int":
                return (key, int(val))

        return (key, val)

    for attr in args:
        if isinstance(attr, list):
            for opt in attr:
                key, val = get_key_val(node, opt)
                retval.append(val)
                knowns.append(key)
        elif attr in keys:
            key, val = get_key_val(node, attr)
            retval.append(val)
            knowns.append(key)
        elif errors is not None:
            errors.append(("missing-attr", node, attr))

    if errors is not None:
        unknown = list(set(keys) - set(knowns))
        for attr in unknown:
            errors.append(("unknown-attr", node, attr))

    return retval


def xml_node_get_comment(node):
    prev = node.getprevious()
    if prev is not None and prev.tag is etree.Comment:
        return prev.text if not prev.text.strip().startswith("interface-") else None
    return None


def xml_node_set(node, attr, val):
    if val is not None:
        node.set(attr, str(val))


# Duck typing Classes


class FileHash():
    def __init__(self, fd):
        self.__fd = fd
        self.__hash = hashlib.sha256()

    def close(self):
        self.__fd.close()

    def peek(self, size):
        return self.__fd.peek(size)

    def read(self, size):
        data = self.__fd.read(size)
        self.__hash.update(data)
        return data

    def flush(self):
        self.__fd.flush()

    def write(self, data):
        self.__hash.update(data)
        self.__fd.write(data)

    def hexdigest(self):
        return self.__hash.hexdigest()
