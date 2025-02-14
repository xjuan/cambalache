#
# CmbSignalEditor - Cambalache Signal Editor
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

from gi.repository import GObject, Gtk, Pango

from .cmb_object import CmbObject
from . import utils

from enum import Enum


class Col(Enum):
    SIGNAL = 0
    OWNER_ID = 1
    SIGNAL_ID = 2
    DETAIL = 3
    HANDLER = 4
    USER_DATA = 5
    SWAP = 6
    AFTER = 7
    INFO = 8
    WARNING_MESSAGE = 9


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_signal_editor.ui")
class CmbSignalEditor(Gtk.Box):
    __gtype_name__ = "CmbSignalEditor"

    treeview = Gtk.Template.Child()
    treestore = Gtk.Template.Child()

    signal_id_column = Gtk.Template.Child()
    signal_id = Gtk.Template.Child()
    handler_column = Gtk.Template.Child()
    handler = Gtk.Template.Child()
    user_data_column = Gtk.Template.Child()
    user_data = Gtk.Template.Child()
    swap_column = Gtk.Template.Child()
    swap = Gtk.Template.Child()
    after_column = Gtk.Template.Child()
    after = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self._object = None
        super().__init__(**kwargs)

        self.signal_id_column.set_cell_data_func(self.signal_id, self.__signal_id_data_func, None)
        self.handler_column.set_cell_data_func(self.handler, self.__data_func, Col.HANDLER.value)
        self.user_data_column.set_cell_data_func(self.user_data, self.__data_func, Col.USER_DATA.value)
        self.swap_column.set_cell_data_func(self.swap, self.__data_func, Col.SWAP.value)
        self.after_column.set_cell_data_func(self.after, self.__data_func, Col.AFTER.value)

    @GObject.Property(type=CmbObject)
    def object(self):
        return self._object

    @object.setter
    def _set_object(self, obj):
        if self._object:
            self.treestore.clear()
            self._object.disconnect_by_func(self.__on_signal_added)
            self._object.disconnect_by_func(self.__on_signal_removed)
            self._object.disconnect_by_func(self.__on_signal_changed)

        self._object = obj

        if obj:
            self.__populate_treestore()
            self._object.connect("signal-added", self.__on_signal_added)
            self._object.connect("signal-removed", self.__on_signal_removed)
            self._object.connect("signal-changed", self.__on_signal_changed)

    @Gtk.Template.Callback("on_handler_edited")
    def __on_handler_edited(self, renderer, path, new_text):
        iter_ = self.treestore.get_iter(path)
        signal = self.treestore[iter_][Col.SIGNAL.value]

        if signal is None:
            if len(new_text) > 0:
                owner_id = self.treestore[iter_][Col.OWNER_ID.value]
                signal_id = self.treestore[iter_][Col.SIGNAL_ID.value]
                self._object.add_signal(owner_id, signal_id, new_text)
        else:
            self.treestore[iter_][Col.HANDLER.value] = new_text
            if len(new_text) > 0:
                signal.handler = new_text
            else:
                self._object.remove_signal(signal)

    @Gtk.Template.Callback("on_detail_edited")
    def __on_detail_edited(self, renderer, path, new_text):
        iter_ = self.treestore.get_iter(path)
        signal = self.treestore[iter_][Col.SIGNAL.value]

        if signal is not None:
            if len(new_text) > 0:
                tokens = new_text.split("::")
                if len(tokens) == 2 and len(tokens[1]) > 0:
                    signal.detail = tokens[1]
                else:
                    signal.detail = None
            else:
                signal.detail = None

            self.treestore[iter_][Col.DETAIL.value] = signal.detail

    @Gtk.Template.Callback("on_user_data_edited")
    def __on_user_data_edited(self, renderer, path, new_text):
        iter_ = self.treestore.get_iter(path)
        signal = self.treestore[iter_][Col.SIGNAL.value]

        if signal is not None:
            if len(new_text) > 0:
                data_obj = self._object.project.get_object_by_name(signal.ui_id, new_text)

                if data_obj:
                    signal.user_data = data_obj.object_id
                    name = data_obj.name
                    signal.swap = True
                else:
                    signal.user_data = 0
                    signal.swap = False
                    self.treestore[iter_][Col.SWAP.value] = signal.swap
                    name = ""

                self.treestore[iter_][Col.USER_DATA.value] = name
            else:
                signal.user_data = 0
                signal.swap = False
                self.treestore[iter_][Col.USER_DATA.value] = ""

    @Gtk.Template.Callback("on_swap_toggled")
    def __on_swap_toggled(self, renderer, path):
        iter_ = self.treestore.get_iter(path)
        signal = self.treestore[iter_][Col.SIGNAL.value]

        if signal is not None:
            signal.swap = not self.treestore[iter_][Col.SWAP.value]
            self.treestore[iter_][Col.SWAP.value] = signal.swap

    @Gtk.Template.Callback("on_after_toggled")
    def __on_after_toggled(self, renderer, path):
        iter_ = self.treestore.get_iter(path)
        signal = self.treestore[iter_][Col.SIGNAL.value]

        if signal is not None:
            signal.after = not self.treestore[iter_][Col.AFTER.value]
            self.treestore[iter_][Col.AFTER.value] = signal.after

    def __on_signal_added(self, obj, signal):
        for row in self.treestore:
            if row[Col.OWNER_ID.value] == signal.owner_id:
                for child in row.iterchildren():
                    if child[Col.SIGNAL.value] is None and child[Col.SIGNAL_ID.value] == signal.signal_id:
                        self.treestore.insert_before(
                            row.iter,
                            child.iter,
                            (
                                signal,
                                signal.owner_id,
                                signal.signal_id,
                                signal.detail,
                                signal.handler,
                                str(signal.user_data),
                                signal.swap,
                                signal.after,
                                child[Col.INFO.value],
                                None,
                            ),
                        )
                break

    def __on_signal_removed(self, obj, signal):
        for row in self.treestore:
            for child in row.iterchildren():
                if child[Col.SIGNAL.value] == signal:
                    self.treestore.remove(child.iter)
                    return

    def __on_signal_changed(self, obj, signal):
        for row in self.treestore:
            for child in row.iterchildren():
                if child[Col.SIGNAL.value] == signal:
                    child[Col.DETAIL.value] = signal.detail
                    child[Col.HANDLER.value] = signal.handler
                    child[Col.USER_DATA.value] = str(signal.user_data)
                    child[Col.SWAP.value] = signal.swap
                    child[Col.AFTER.value] = signal.after
                    return

    def __populate_from_type(self, info, target):
        if len(info.signals) == 0:
            return None

        parent = self.treestore.append(None, (None, info.type_id, info.type_id, None, None, None, False, False, None, None))
        for signal_id in info.signals:
            signal = info.signals[signal_id]
            msg = utils.get_version_warning(target, signal.version, signal.deprecated_version, signal.signal_id)
            self.treestore.append(parent, (None, info.type_id, signal.signal_id, None, None, None, False, False, signal, msg))
        return parent

    def __populate_treestore(self):
        target = self._object.ui.get_target(self._object.info.library_id)

        # Populate object type signals
        parent = self.__populate_from_type(self._object.info, target)

        # Expand object type signals
        if parent:
            self.treeview.expand_row(self.treestore.get_path(parent), True)

        # Populate all hierarchy signals
        for type_id in self._object.info.hierarchy:
            info = self._object.project.type_info.get(type_id, None)
            if info:
                self.__populate_from_type(info, target)

        # Populate object signals
        for signal in self._object.signals:
            self.__on_signal_added(self._object, signal)

    def __signal_id_data_func(self, tree_column, cell, tree_model, iter_, column):
        info = tree_model[iter_][Col.INFO.value]
        signal_id = tree_model[iter_][Col.SIGNAL_ID.value]
        warning = tree_model[iter_][Col.WARNING_MESSAGE.value]

        if info and info.detailed:
            detail = tree_model[iter_][Col.DETAIL.value]
            signal = tree_model[iter_][Col.SIGNAL.value]

            cell.props.editable = False if signal is None else True
            cell.props.text = f"{signal_id}::{detail}" if detail is not None else signal_id
        else:
            cell.props.editable = False
            cell.props.text = signal_id

        cell.props.underline = Pango.Underline.ERROR if warning else Pango.Underline.NONE

    def __data_func(self, tree_column, cell, tree_model, iter_, column):
        info = tree_model[iter_][Col.INFO.value]
        signal = tree_model[iter_][Col.SIGNAL.value]

        if info is None:
            cell.props.visible = False
            return

        cell.props.visible = True

        if signal is None and column != Col.HANDLER.value:
            cell.props.sensitive = False
        else:
            cell.props.sensitive = True

        if signal and column == Col.USER_DATA.value:
            user_data = signal.user_data
            if user_data:
                data_obj = self._object.project.get_object_by_id(signal.ui_id, user_data)
                cell.props.text = data_obj.name if data_obj else ""
            else:
                cell.props.text = ""
