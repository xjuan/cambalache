#
# CmbTreeView - Cambalache Tree View
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

from gi.repository import Gtk, Pango

from .cmb_object import CmbObject
from .cmb_context_menu import CmbContextMenu
from cambalache import _


class CmbTreeView(Gtk.TreeView):
    __gtype_name__ = "CmbTreeView"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.props.has_tooltip = True

        self._project = None
        self._selection = self.get_selection()
        self.__in_selection_change = False
        self._selection.connect("changed", self.__on_selection_changed)
        self.set_headers_visible(False)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Object(Type)", renderer)
        column.set_cell_data_func(renderer, self.__name_cell_data_func, None)
        self.append_column(column)

        self.connect("notify::model", self.__on_model_notify)
        self.connect("row-activated", self.__on_row_activated)

        gesture = Gtk.GestureClick(button=3)
        gesture.connect("pressed", self.__on_button_press)
        self.add_controller(gesture)

        self.set_reorderable(True)

    def __on_button_press(self, widget, npress, x, y):
        retval = self.get_path_at_pos(x, y)

        if retval is None:
            return False

        path, col, xx, yy = retval
        self.get_selection().select_path(path)

        menu = CmbContextMenu()

        if self._project is not None:
            menu.target_tk = self._project.target_tk

        # Use parent instead of self to avoid warning and focus not working properly
        # (run-dev.py:188589): Gtk-CRITICAL **: 16:45:12.790: gtk_css_node_insert_after: assertion 'previous_sibling == NULL ||
        # previous_sibling->parent == parent' failed
        menu.set_parent(self.props.parent)
        menu.popup_at(x, y)

        return True

    def __name_cell_data_func(self, column, cell, model, iter_, data):
        obj = model.get_value(iter_, 0)
        msg = None

        if type(obj) is CmbObject:
            inline_prop = obj.inline_property_id
            inline_prop = f"<b>{inline_prop}</b> " if inline_prop else ""
            name = f"{obj.name} " if obj.name else ""
            extra = _("(template)") if not obj.parent_id and obj.ui.template_id == obj.object_id else obj.type_id
            msg = obj.version_warning

            text = f"{inline_prop}{name}<i>{extra}</i>"
        else:
            text = f"<b>{obj.get_display_name()}</b>"

        cell.set_property("markup", text)
        cell.set_property("underline", Pango.Underline.ERROR if msg else Pango.Underline.NONE)

    def __on_project_ui_library_changed(self, project, ui, library_id):
        self.queue_draw()

    def __on_model_notify(self, treeview, pspec):
        if self._project is not None:
            self._project.disconnect_by_func(self.__on_project_selection_changed)
            self._project.disconnect_by_func(self.__on_project_ui_library_changed)

        self._project = self.props.model

        if self._project:
            self._project.connect("selection-changed", self.__on_project_selection_changed)
            self._project.connect("ui-library-changed", self.__on_project_ui_library_changed)

    def __on_row_activated(self, view, path, column):
        if self.row_expanded(path):
            self.collapse_row(path)
        else:
            self.expand_row(path, True)

    def __on_project_selection_changed(self, p):
        project, _iter = self._selection.get_selected()
        current = [project.get_value(_iter, 0)] if _iter is not None else []
        selection = project.get_selection()

        if selection == current:
            return

        self.__in_selection_change = True

        if len(selection) > 0:
            obj = selection[0]
            _iter = project.get_iter_from_object(obj)
            path = project.get_path(_iter)
            self.expand_to_path(path)
            self._selection.select_iter(_iter)
        else:
            self._selection.unselect_all()

        self.__in_selection_change = False

    def __on_selection_changed(self, selection):
        if self.__in_selection_change:
            return

        project, _iter = selection.get_selected()

        if _iter is not None:
            obj = project.get_value(_iter, 0)
            project.set_selection([obj])

    def do_query_tooltip(self, x, y, keyboard_mode, tooltip):
        retval, model, path, iter_ = self.get_tooltip_context(x, y, keyboard_mode)

        if not retval:
            return False

        obj = model.get_value(iter_, 0)

        if type(obj) is CmbObject:
            msg = obj.version_warning
            if msg:
                tooltip.set_text(msg)
                return True

        return False
