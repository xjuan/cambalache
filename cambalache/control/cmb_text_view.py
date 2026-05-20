#
# CmbTextView
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
# SPDX-License-Identifier: LGPL-2.1-only
#

from gi.repository import GObject, Gtk
from .cmb_text_buffer import CmbTextBuffer


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/control/cmb_text_view.ui")
class CmbTextView(Gtk.Box):
    __gtype_name__ = "CmbTextView"

    __gsignals__ = {
        "edit-translatable": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    cmb_value = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    buffer = Gtk.Template.Child()
    view = Gtk.Template.Child()
    edit = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        GObject.Object.bind_property(
            self,
            "cmb-value",
            self.buffer,
            "cmb-value",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )

    @GObject.Property(type=bool, default=False)
    def translatable(self):
        return self.edit.props.visible

    @translatable.setter
    def _set_translatable(self, value):
        self.edit.props.visible = value

    @Gtk.Template.Callback("on_edit_clicked")
    def __on_edit_clicked(self, widget):
        self.emit("edit-translatable")

Gtk.WidgetClass.set_css_name(CmbTextView, "CmbTextView")
