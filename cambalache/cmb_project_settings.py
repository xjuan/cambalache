#
# CmbProjectSettings - Cambalache Project Editor
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

import os

from gi.repository import GObject, Gtk, Adw, Gio
from .cmb_project import CmbProject
from .cmb_library_info import CmbLibraryInfo
from .cmb_library_row import CmbLibraryRow
from cambalache import _, getLogger


logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_project_settings.ui")
class CmbProjectSettings(Adw.PreferencesDialog):
    __gtype_name__ = "CmbProjectSettings"

    catalog_group = Gtk.Template.Child()
    icontheme_group = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self._project = None

        super().__init__(**kwargs)

    @GObject.Property(type=CmbProject)
    def project(self):
        return self._project

    @project.setter
    def _set_project(self, project):
        if project == self._project:
            return

        # TODO: clear groups

        self._project = project

        if project is None:
            return

        third_party_catalogs = Gio.ListStore(item_type=CmbLibraryInfo)

        for library_id, info in self.project.library_info.items():
            if info.third_party:
                third_party_catalogs.append(info)

        self.catalog_group.bind_model(third_party_catalogs, self.__catalog_create_row, None)
        self.icontheme_group.bind_model(project.icontheme_search_paths, self.__icontheme_create_row, None)

    def __catalog_create_row(self, item, data):
        return CmbLibraryRow(info=item)

    def __icontheme_create_row(self, item, data):
        box = Gtk.Box()
        label = Gtk.Label(label=item.props.string, hexpand=True, halign=Gtk.Align.START)
        button = Gtk.Button(icon_name="list-remove-symbolic", has_frame=False)
        box.append(label)
        box.append(button)
        button.connect("clicked", self.__on_icontheme_remove_button_clicked, item)

        return Adw.PreferencesRow(child=box)

    def __on_icontheme_remove_button_clicked(self, button, item):
        position = self.project.icontheme_search_paths.find(item.props.string)
        self.project.icontheme_search_paths.remove(position)

    @Gtk.Template.Callback("on_icontheme_add_button_clicked")
    def __on_icontheme_add_button_clicked(self, button):
        dialog = Gtk.FileDialog(
            modal=True,
            title=_("Select icon path search directory"),
        )

        if self.project and self.project.filename:
            dialog.set_initial_folder(Gio.File.new_for_path(os.path.dirname(self.project.filename)))

        def dialog_callback(dialog, res):
            try:
                iconpath = dialog.select_folder_finish(res).get_path()
                basename, relpath = self.project._get_basename_relpath(iconpath)
                self.project.icontheme_search_paths.append(relpath)
            except Exception as e:
                logger.warning(f"Error {e}")

        dialog.select_folder(self.props.root, None, dialog_callback)


Gtk.WidgetClass.set_css_name(CmbProjectSettings, "CmbProjectSettings")
