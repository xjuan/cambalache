# GtkDialog Controller
#
# Copyright (C) 2024  Juan Pablo Ugarte
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

from gi.repository import GLib, GObject, Gtk

from .mrg_gtk_window import MrgGtkWindow
from merengue import getLogger

logger = getLogger(__name__)


class MrgGtkDialog(MrgGtkWindow):
    object = GObject.Property(type=Gtk.Dialog, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __queue_resize(self, data):
        if self.object:
            self.object.props.border_width = data
        return GLib.SOURCE_REMOVE

    def object_changed(self, old, new):
        super().object_changed(old, new)

        if Gtk.MAJOR_VERSION == 3 and new:
            # FIXME: Hack, force dialog to resize properly
            # GtkDialog gets allocated too much space or not enough for messages, setting message or container border fix it.
            # Probably a bug in Casilda or a workaround in gnome-shell
            GLib.timeout_add(100, self.__queue_resize, new.props.border_width)
            new.props.border_width = 1
