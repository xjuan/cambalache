#
# CmbCatalogRow - Cambalache Catalog Row
#
# Copyright (C) 2025  Juan Pablo Ugarte
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

from gi.repository import GObject, Gtk, Adw
from .cmb_library_info import CmbLibraryInfo
from cambalache import ngettext


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_library_row.ui")
class CmbLibraryRow(Adw.PreferencesRow):
    __gtype_name__ = "CmbLibraryRow"

    info = GObject.Property(type=CmbLibraryInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    label = Gtk.Template.Child()
    description = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    clear = Gtk.Template.Child()
    switch = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.n_objects = 0

        super().__init__(**kwargs)

        self.switch.props.active = self.info.enabled
        self.__init_n_objects()

    def __init_n_objects(self):
        info = self.info

        self.n_objects = info.project.db.execute(
            "SELECT COUNT(object_id) FROM object, type WHERE object.type_id = type.type_id AND type.library_id=?;",
            (info.library_id, )
        ).fetchone()[0]

        if self.n_objects > 0:
            self.label.props.label = ngettext(
                "<b>{catalog}-{version}</b> <small>(used by {n} object)</small>",
                "<b>{catalog}-{version}</b> <small>(used by {n} objects)</small>",
                self.n_objects
            ).format(
                catalog=info.library_id,
                version=info.version,
                n=self.n_objects
            )
            self.stack.set_visible_child(self.clear)
        else:
            self.label.props.label = f"{info.library_id}-{info.version}"
            self.stack.set_visible_child(self.switch)

    @Gtk.Template.Callback("on_clear_clicked")
    def __on_clear_clicked(self, button):
        dialog = Adw.AlertDialog(
            heading=ngettext(
                "Delete {n} object?",
                "Delete {n} objects?",
                self.n_objects
            ).format(n=self.n_objects),
            body=ngettext(
                "This project contains {n} object from {catalog}",
                "This project contains {n} objects from {catalog}",
                self.n_objects
            ).format(
                catalog=self.info.library_id,
                n=self.n_objects
            ),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_dialog_response(obj, response):
            if response == "delete":
                self.info.project.remove_library_objects(self.info)
                self.__init_n_objects()

        dialog.connect("response", on_dialog_response)
        dialog.present(self.props.root)

    @Gtk.Template.Callback("on_switch_notify")
    def __on_switch_notify(self, switch, pspec):
        # Load/Unload catalog
        self.info.enabled = switch.props.active

        # Sync status in case unload failed
        if switch.props.active != self.info.enabled:
            switch.props.active = self.info.enabled


Gtk.WidgetClass.set_css_name(CmbLibraryRow, "CmbLibraryRow")
