#
# CmbColumnView
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

from gi.repository import GLib, GObject, Gdk, Gtk

from .cmb_ui import CmbUI
from .cmb_object import CmbObject
from .cmb_gresource import CmbGResource
from .cmb_context_menu import CmbContextMenu
from .cmb_path import CmbPath
from .cmb_project import CmbProject


class CmbListView(Gtk.ListView):
    __gtype_name__ = "CmbListView"

    def __init__(self, **kwargs):
        self.__project = None
        self.__tree_model = None
        self.__in_selection_change = False
        self.single_selection = Gtk.SingleSelection()

        super().__init__(**kwargs)

        self.props.has_tooltip = True
        self.props.hexpand = True

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)
        factory.connect("unbind", self._on_factory_unbind)
        self.props.factory = factory

        self.single_selection.connect("notify::selected-item", self.__on_selected_item_notify)
        self.set_model(self.single_selection)

        gesture = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", self.__on_button_press)
        self.add_controller(gesture)

        self.connect("activate", self.__on_activate)

        self.add_css_class("cmb-list-view")

    def __on_button_press(self, gesture, npress, x, y):
        expander = self.__get_tree_expander(x, y)

        if expander is None or npress != 1:
            return False

        # Select row at x,y
        list_row = expander.get_list_row()
        self.single_selection.set_selected(list_row.get_position())

        menu = CmbContextMenu()

        if self.__project:
            menu.target_tk = self.__project.target_tk

        menu.set_parent(self)
        menu.popup_at(x, y)
        return True

    def __get_path_parent(self, obj):
        if isinstance(obj, CmbObject):
            parent = obj.parent
            return parent if parent else obj.ui
        elif isinstance(obj, CmbGResource):
            return obj.path_parent if obj.resource_type == "gresources" else obj.parent

        return obj.path_parent

    def __get_object_ancestors(self, obj):
        ancestors = set()

        parent = self.__get_path_parent(obj)
        while parent:
            ancestors.add(parent)
            parent = self.__get_path_parent(parent)

        return ancestors

    def __object_ancestor_expand(self, obj):
        ancestors = self.__get_object_ancestors(obj)
        i = 0

        # Iterate over tree model
        # NOTE: only visible/expanded rows are returned
        list_row = self.__tree_model.get_row(i)
        while list_row:
            item = list_row.get_item()

            # Return position if we reached the object row
            if item == obj:
                return i
            elif item in ancestors:
                # Expand row if its part of the hierarchy
                list_row.set_expanded(True)

            i += 1
            list_row = self.__tree_model.get_row(i)

        return None

    def __on_project_selection_changed(self, p):
        list_row = self.single_selection.get_selected_item()
        current_selection = [list_row.get_item()] if list_row else []
        selection = self.__project.get_selection()

        if selection == current_selection:
            return

        self.__in_selection_change = True

        if len(selection) > 0:
            position = self.__object_ancestor_expand(selection[0])
            if position is not None:
                self.single_selection.select_item(position, True)
            else:
                self.single_selection.unselect_all()
        else:
            self.single_selection.unselect_all()

        self.__in_selection_change = False

    @GObject.Property(type=CmbProject)
    def project(self):
        return self.__project

    @project.setter
    def _set_project(self, project):
        if self.__project:
            self.__project.disconnect_by_func(self.__on_project_selection_changed)

        self.__project = project

        if project:
            self.__tree_model = Gtk.TreeListModel.new(
                project,
                False,
                False,
                self.__tree_model_create_func,
                None
            )
            self.single_selection.props.model = self.__tree_model
            self.__project.connect("selection-changed", self.__on_project_selection_changed)
        else:
            self.single_selection.props.model = None

    def __tree_model_create_func(self, item, data):
        if isinstance(item, CmbObject):
            return item
        elif isinstance(item, CmbUI):
            return item
        elif isinstance(item, CmbGResource):
            return item
        elif isinstance(item, CmbPath):
            return item

        return None

    def __on_selected_item_notify(self, single_selection, pspec):
        if self.__in_selection_change or self.__project is None:
            return

        list_item = single_selection.get_selected_item()
        position = single_selection.get_selected()

        if list_item is None:
            self.__project.set_selection([])
            return

        item = list_item.get_item()
        self.activate_action("list.activate-item", GLib.Variant("u", position))

        if item and not isinstance(item, CmbPath):
            item = list_item.get_item()
            self.__project.set_selection([item])
        else:
            self.__project.set_selection([])

    def _on_factory_setup(self, factory, list_item):
        expander = CmbTreeExpander()
        list_item.set_child(expander)

    def _on_factory_bind(self, factory, list_item):
        row = list_item.get_item()
        expander = list_item.get_child()
        expander.set_list_row(row)
        expander.update_bind()

    def _on_factory_unbind(self, factory, list_item):
        expander = list_item.get_child()
        expander.clear_bind()

    def __get_tree_expander(self, x, y):
        pick = self.pick(x, y, Gtk.PickFlags.DEFAULT)

        if pick is None:
            return None

        if isinstance(pick, Gtk.TreeExpander):
            return pick

        child = pick.get_first_child()

        if child and isinstance(child, Gtk.TreeExpander):
            return child

        parent = pick.props.parent
        if parent and isinstance(parent, Gtk.TreeExpander):
            return parent

        return None

    def __on_activate(self, column_view, position):
        item = self.__tree_model.get_item(position)
        item.set_expanded(not item.get_expanded())

    def do_query_tooltip(self, x, y, keyboard_mode, tooltip):
        expander = self.__get_tree_expander(x, y)

        if expander is None:
            return False

        obj = expander.get_item()

        if isinstance(obj, CmbObject):
            msg = obj.version_warning
            if msg:
                tooltip.set_text(msg)
                return True

        return False
