#
# Cambalache GResource wrapper
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

from gi.repository import GObject, Gio

from .cmb_path import CmbPath
from .cmb_base_objects import CmbBaseGResource
from .cmb_list_error import CmbListError

from cambalache import _


class CmbGResource(CmbBaseGResource, Gio.ListModel):
    __gtype_name__ = "CmbGResource"

    path_parent = GObject.Property(type=CmbPath, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self._last_known = None

        super().__init__(**kwargs)

        if self.resource_type == "gresources":
            self.update_file_monitor(self.gresources_filename)

        self.connect("notify", self.__on_notify)

    def __bool__(self):
        return True

    def __str__(self):
        return f"CmbGResource<{self.resource_type}> id={self.gresource_id}"

    def __on_notify(self, obj, pspec):
        resource_type = self.resource_type

        if resource_type == "gresources" and pspec.name == "gresources-filename":
            self.update_file_monitor(self.gresources_filename)

        if (resource_type == "gresources" and pspec.name in ["gresources-filename", "file-status"]) or \
           (resource_type == "gresource" and pspec.name in ["gresource-prefix", "file-status"]) or \
           (resource_type == "file" and pspec.name in ["file-filename", "file-status"]):
            obj.notify("display-name")

        if pspec.name not in ["file-status", "path-parent"]:
            self.project._gresource_changed(self, pspec.name)

    @GObject.Property(type=CmbBaseGResource)
    def parent(self):
        if self.resource_type in ["gresource", "file"]:
            return self.project.get_gresource_by_id(self.parent_id)

        return None

    @GObject.Property(type=CmbBaseGResource)
    def gresources_bundle(self):
        resource_type = self.resource_type
        if resource_type == "gresource":
            return self.parent
        elif resource_type == "file":
            return self.parent.parent

        return self

    @GObject.Property(type=str)
    def display_name(self):
        resource_type = self.resource_type

        if resource_type == "gresources":
            gresources_filename = self.gresources_filename
            if gresources_filename:
                basename, relpath = self.project._get_basename_relpath(self.gresources_filename)
                display_name = basename
            else:
                display_name = _("Unnamed GResource {id}").format(id=self.gresource_id)
        elif resource_type == "gresource":
            gresource_prefix = self.gresource_prefix
            display_name = gresource_prefix if gresource_prefix else _("Unprefixed resource {id}").format(id=self.gresource_id)
        elif resource_type == "file":
            file_filename = self.file_filename
            display_name = file_filename if file_filename else _("Unnamed file {id}").format(id=self.gresource_id)

        return f'<span underline="error">{display_name}</span>' if self.file_status else display_name

    def reload(self):
        if not self.project or not self.gresources_filename:
            return False

        # Disable history
        self.project.history_enabled = False

        # Import file and overwrite
        gresource = self.project.import_gresource(self.gresources_filename, overwrite=True)

        super().reload()

        # Select currently reloaded file
        self.project.set_selection([gresource])

    # GListModel helpers
    def _save_last_known_parent_and_position(self):
        self._last_known = (self.parent, self.position)

    def _update_new_parent(self):
        parent = self.parent
        position = self.position

        # Emit GListModel signal to update model
        if parent:
            parent.items_changed(position, 0, 1)
            parent.notify("n-items")

        self._last_known = None

    def _remove_from_old_parent(self):
        if self._last_known is None:
            return

        parent, position = self._last_known

        # Emit GListModel signal to update model
        if parent:
            parent.items_changed(position, 1, 0)
            parent.notify("n-items")

        self._last_known = None

    # GListModel iface
    def do_get_item(self, position):
        gresource_id = self.gresource_id
        key = self.db_get(
            "SELECT gresource_id FROM gresource WHERE parent_id=? AND position=?;",
            (gresource_id, position)
        )

        if key is not None:
            return self.project.get_gresource_by_id(key)

        # This should not happen
        return CmbListError()

    def do_get_item_type(self):
        return CmbBaseGResource

    @GObject.Property(type=int)
    def n_items(self):
        if self.resource_type in ["gresources", "gresource"]:
            retval = self.db_get("SELECT COUNT(gresource_id) FROM gresource WHERE parent_id=?;", (self.gresource_id, ))
            return retval if retval is not None else 0
        else:
            return 0

    def do_get_n_items(self):
        return self.n_items

