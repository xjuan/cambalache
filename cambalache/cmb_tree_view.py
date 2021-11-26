#
# CmbTreeView - Cambalache Tree View
#
# Copyright (C) 2021  Juan Pablo Ugarte
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

import os
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gdk, Gtk

from .cmb_ui import CmbUI
from .cmb_object import CmbObject
from .cmb_context_menu import CmbContextMenu


class CmbTreeView(Gtk.TreeView):
    __gtype_name__ = 'CmbTreeView'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._project = None
        self._selection = self.get_selection()
        self._selection.connect('changed', self.__on_selection_changed)
        self.set_headers_visible (False)
        self.__right_click = False

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn('Object(Type)', renderer)
        column.set_cell_data_func(renderer, self.__name_cell_data_func, None)
        self.append_column(column)

        self.connect('notify::model', self.__on_model_notify)
        self.connect('row-activated', self.__on_row_activated)

        self.menu = CmbContextMenu(relative_to=self)

        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect('button-press-event', self.__on_button_press_event)
        self.connect('button-release-event', self.__on_button_release_event)

    def __on_button_press_event(self, widget, event):
        if event.window != self.get_bin_window() or event.button != 3:
            return False

        self.__right_click = True
        return True

    def __on_button_release_event(self, widget, event):
        if event.window != self.get_bin_window() or event.button != 3:
            return False

        if not self.__right_click:
            return

        self.__right_click = False

        path, col, xx, yy = self.get_path_at_pos(event.x, event.y)
        self.get_selection().select_path(path)

        self.menu.popup_at(event.x, event.y)

        return True

    def __name_cell_data_func(self, column, cell, model, iter_, data):
        obj = model.get_value(iter_, 0)

        if type(obj) == CmbObject:
            name = obj.name or ''
            extra = '(template)' if not obj.parent_id and obj.ui.template_id == obj.object_id else obj.type_id
            cell.set_property('markup', f'{name} <i>{extra}</i>')
        elif type(obj) == CmbUI:
            cell.set_property('markup', f'<b>{obj.filename}</b>')

    def __on_model_notify(self, treeview, pspec):
        if self._project is not None:
            self._project.disconnect_by_func(self.__on_project_selection_changed)

        self._project = self.props.model

        if self._project:
            self._project.connect('selection-changed', self.__on_project_selection_changed)

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

        if len(selection) > 0:
            _iter = project.get_iter_from_object(selection[0])
            path = project.get_path(_iter)
            self.expand_to_path(path)
            self._selection.select_iter(_iter)
        else:
            self._selection.unselect_all()

    def __on_selection_changed(self, selection):
        project, _iter = selection.get_selected()

        if _iter is not None:
            obj = project.get_value(_iter, 0)
            project.set_selection([obj])
