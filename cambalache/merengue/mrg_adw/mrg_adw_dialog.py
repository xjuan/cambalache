# AdwDialog Controller
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

from gi.repository import GObject, Adw, Gtk


class MgrAdwDialogProxy(Gtk.Window):
    __gtype_name__ = "MgrAdwDialogProxy"

    focus_widget = GObject.Property(type=Gtk.Widget, flags=GObject.ParamFlags.READWRITE)
    can_close = GObject.Property(type=bool, default=True, flags=GObject.ParamFlags.READWRITE)
    follows_content_size = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    content_height = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)
    content_width = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)
    presentation_mode = GObject.Property(
        type=Adw.DialogPresentationMode,
        default=Adw.DialogPresentationMode.AUTO,
        flags=GObject.ParamFlags.READWRITE
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
