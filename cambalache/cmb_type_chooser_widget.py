#
# CmbTypeChooserWidget - Cambalache Type Chooser Widget
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

from .cmb_project import CmbProject
from .cmb_type_info import CmbTypeInfo
from . import constants
from cambalache import getLogger, _

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_type_chooser_widget.ui")
class CmbTypeChooserWidget(Gtk.Box):
    __gtype_name__ = "CmbTypeChooserWidget"

    __gsignals__ = {
        "type-selected": (GObject.SignalFlags.RUN_LAST, None, (CmbTypeInfo,)),
    }

    category = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    uncategorized_only = GObject.Property(type=bool, flags=GObject.ParamFlags.READWRITE, default=False)
    show_categories = GObject.Property(type=bool, flags=GObject.ParamFlags.READWRITE, default=False)
    parent_type_id = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    derived_type_id = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    scrolledwindow = Gtk.Template.Child()
    treeview = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.__project = None
        self.__model = None
        self._search_text = ""
        self._filter = None

        super().__init__(**kwargs)

        self.connect("map", self.__on_map)

    def __on_map(self, widget):
        root = widget.get_root()

        if root is not None:
            height = root.get_allocated_height() - 100
            if height > 460:
                height = height * 0.7

            self.scrolledwindow.set_max_content_height(height)
        return False

    def __type_info_should_append(self, info):
        retval = False

        if not info.instantiable or info.layout not in [None, "container"]:
            return False

        if info.category == "hidden":
            return False

        if self.parent_type_id != "":
            retval = self.project._check_can_add(info.type_id, self.parent_type_id)
        else:
            retval = (
                info.category is None
                if self.uncategorized_only
                else (self.category != "" and info.category == self.category) or self.category == ""
            )

        if retval and self.derived_type_id != "":
            retval = info.is_a(self.derived_type_id)

        return retval

    def __store_append_info(self, store, info):
        if store:
            store.append([info.type_id, info.type_id.lower(), info, True])

    def __model_from_project(self, project):
        if project is None:
            return None

        categories = {
            "toplevel": _("Toplevel"),
            "layout": _("Layout"),
            "control": _("Control"),
            "display": _("Display"),
            "model": _("Model"),
        }

        order = {"toplevel": 0, "layout": 1, "control": 2, "display": 3, "model": 4}

        # type_id, type_id.lower(), CmbTypeInfo, sensitive
        store = Gtk.ListStore(str, str, CmbTypeInfo, bool)
        infos = []

        for key in project.type_info:
            # Ignore types with no name, just in case
            if key:
                infos.append(project.type_info[key])
            else:
                logger.warning("Tried to create a TypeInfo without a name")

        infos = sorted(infos, key=lambda i: (order.get(i.category, 99), i.type_id))
        show_categories = self.show_categories
        last_category = None

        for i in infos:
            if not self.__type_info_should_append(i):
                continue

            # Append category
            if show_categories and last_category != i.category:
                last_category = i.category
                category = categories.get(i.category, _("Others"))
                store.append([f"<i>▾ {category}</i>", "", None, False])

            self.__store_append_info(store, i)

        # Special case External object type
        if show_categories or self.uncategorized_only:
            self.__store_append_info(store, project.type_info[constants.EXTERNAL_TYPE])

        return store

    @GObject.Property(type=CmbProject)
    def project(self):
        return self.__project

    @project.setter
    def _set_project(self, project):
        if self.__project:
            self.__project.disconnect_by_func(self.__on_type_info_added)
            self.__project.disconnect_by_func(self.__on_type_info_removed)
            self.__project.disconnect_by_func(self.__on_type_info_changed)

        self.__project = project

        self.__model = self.__model_from_project(project)
        self._filter = Gtk.TreeModelFilter(child_model=self.__model) if self.__model else None
        if self._filter:
            self._filter.set_visible_func(self.__visible_func)

        self.treeview.props.model = self._filter

        if project:
            project.connect("type-info-added", self.__on_type_info_added)
            project.connect("type-info-removed", self.__on_type_info_removed)
            project.connect("type-info-changed", self.__on_type_info_changed)

    @Gtk.Template.Callback("on_searchentry_activate")
    def __on_searchentry_activate(self, entry):
        search_text = entry.props.text

        info = self.project.type_info.get(search_text, None)
        if info:
            self.emit("type-selected", info)

    @Gtk.Template.Callback("on_searchentry_search_changed")
    def __on_searchentry_search_changed(self, entry):
        self._search_text = entry.props.text.lower()
        self._filter.refilter()

    @Gtk.Template.Callback("on_treeview_row_activated")
    def __on_treeview_row_activated(self, treeview, path, column):
        model = treeview.props.model
        info = model[model.get_iter(path)][2]

        if info is not None:
            self.emit("type-selected", info)

    def __visible_func(self, model, iter, data):
        type_id, type_id_lower, info, sensitive = model[iter]

        # Always show categories if we are not searching
        if self._search_text == "" and info is None:
            return True

        return type_id_lower.find(self._search_text) >= 0

    def __on_type_info_added(self, project, info):
        if self.__model is None:
            return

        # Append new type info
        # TODO: insert in order
        if self.__type_info_should_append(info):
            self.__store_append_info(self.__model, info)

    def __on_type_info_removed(self, project, info):
        if self.__model is None:
            return

        # Find info and remove it from model
        for row in self.__model:
            if info == row[2]:
                self.__model.remove(row.iter)

    def __on_type_info_changed(self, project, info):
        if self.__model is None:
            return

        info_row = None

        # Find info and update it from model
        for row in self.__model:
            if info == row[2]:
                info_row = row
                break

        if info_row is None:
            return

        # Update Type Name
        info_row[0] = info.type_id
        info_row[1] = info.type_id.lower()


Gtk.WidgetClass.set_css_name(CmbTypeChooserWidget, "CmbTypeChooserWidget")
