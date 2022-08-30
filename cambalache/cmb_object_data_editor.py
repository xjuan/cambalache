#
# CmbObjectDataEditor - Cambalache Object Data Editor
#
# Copyright (C) 2022  Juan Pablo Ugarte
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

import gi
import traceback

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, GObject, Gtk

from .cmb_type_info import CmbTypeDataInfo
from .cmb_object_data import CmbObjectData
from .cmb_property_controls import *


@Gtk.Template(resource_path='/ar/xjuan/Cambalache/cmb_object_data_editor.ui')
class CmbObjectDataEditor(Gtk.Box):
    __gtype_name__ = 'CmbObjectDataEditor'

    info = GObject.Property(type=CmbTypeDataInfo, flags = GObject.ParamFlags.READWRITE)

    label = Gtk.Template.Child()
    top_box = Gtk.Template.Child()
    add_child = Gtk.Template.Child()
    add_only_child = Gtk.Template.Child()
    remove_button = Gtk.Template.Child()
    grid = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.__object = None
        self.__data = None

        self.__size_group = None
        self.__value_editor = None
        self.__arg_editors = {}
        self.__editors = []
        self.__editor_margin_end = None

        super().__init__(**kwargs)

        self.__update_view()

    @Gtk.Template.Callback('on_add_only_child_clicked')
    def __on_add_only_child_clicked(self, button):
        info = self.data.info if self.data else self.info

        # Do not add a menu if there is only one child type
        child_info = list(info.children.values())[0]
        self.__on_child_button_clicked(button, child_info)

    @Gtk.Template.Callback('on_remove_clicked')
    def __on_remove_clicked(self, button):
        if self.info:
            self.object.remove_data(self.__data)
        else:
            self.__data.parent.remove_data(self.__data)

    @Gtk.Template.Callback('on_remove_size_allocate')
    def __on_remove_size_allocate(self, button, alloc):
        info = self.data.info if self.data else self.info

        if info is None or info.type_id is None:
            return

        self.__editor_margin_end = alloc.width + self.top_box.props.spacing

        for editor in self.__editors:
            editor.props.margin_end = self.__editor_margin_end

    @GObject.Property(type=GObject.Object)
    def object(self):
        return self.__object

    @object.setter
    def _set_object(self, value):
        if self.__object:
            self.__object.disconnect_by_func(self.__on_data_added)
            self.__object.disconnect_by_func(self.__on_data_removed)

        self.__object = value

        if self.__object:
            self.__object.connect('data-added', self.__on_data_added)
            self.__object.connect('data-removed', self.__on_data_removed)

    @GObject.Property(type=CmbObjectData)
    def data(self):
        return self.__data

    @data.setter
    def _set_data(self, value):
        if self.__data:
            self.__data.disconnect_by_func(self.__on_data_data_added)
            self.__data.disconnect_by_func(self.__on_data_data_removed)
            self.__data.disconnect_by_func(self.__on_data_arg_changed)

        self.__data = value

        # Clear old editors
        for editor in self.__editors:
            self.grid.remove(editor)
        self.__editors = []

        if self.__data:
            self.__data.connect('data-added', self.__on_data_data_added)
            self.__data.connect('data-removed', self.__on_data_data_removed)
            self.__data.connect('arg-changed', self.__on_data_arg_changed)

    def __update_arg(self, key):
        if not self.data:
            return

        editor = self.__arg_editors.get(key, None)
        val = self.data.get_arg(key)

        if val and editor:
            editor.cmb_value = val

    def __on_data_data_added(self, parent, data):
        self.__add_data_editor(data)

    def __on_data_data_removed(self, parent, data):
        self.__remove_data_editor(data)

    def __on_data_arg_changed(self, data, key):
        self.__update_arg(key)

    def __on_data_added(self, obj, data):
        if self.info and self.data is None and self.info == data.info:
            self.data = data
            self.__update_view()

    def __on_data_removed(self, obj, data):
        if self.object and self.info:
            self.__remove_data_editor(data)

    def __ensure_object_data(self, history_message):
        if self.data:
            return False

        self.object.project.history_push(history_message)
        self.data = self.object.add_data(self.info.key)

        if self.__value_editor:
            GObject.Object.bind_property(self.data, 'value',
                                         self.__value_editor, 'cmb-value',
                                         GObject.BindingFlags.SYNC_CREATE |
                                         GObject.BindingFlags.BIDIRECTIONAL)
        return True

    def __on_child_button_clicked(self, button, info):
        msg = _('Add {key}').format(key=info.key)
        history_pushed = self.__ensure_object_data(msg)
        self.data.add_data(info.key)
        if history_pushed:
            self.object.project.history_pop()

    def __context_menu_new(self, info):
        popover = Gtk.Popover(position=Gtk.PositionType.BOTTOM)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                      visible=True,
                      spacing=4,
                      border_width=4)

        # Add children types
        for child in info.children:
            child_info = info.children[child]
            button = Gtk.ModelButton(label=_('Add {key}').format(key=child_info.key),
                                     visible=True)
            button.connect('clicked', self.__on_child_button_clicked, child_info)
            box.add(button)

        popover.add(box)

        return popover

    def __on_arg_notify(self, obj, pspec, info):
        msg = _('Set {key} to {value}').format(key=info.key, value=obj.cmb_value)
        history_pushed = self.__ensure_object_data(msg)
        self.data.set_arg(info.key, obj.cmb_value)
        if history_pushed:
            self.object.project.history_pop()

    def __add(self, editor, label=None):
        neditors = len(self.__editors)

        if label:
            self.grid.attach(label, 0, neditors, 1, 1)
            self.__size_group.add_widget(label)

        self.grid.attach(editor, 1, neditors, 1, 1)

        if self.__editor_margin_end:
            editor.props.margin_end = self.__editor_margin_end

        self.__editors.append(editor)

    def __add_data_editor(self, data):
        editor = CmbObjectDataEditor(visible=True,
                                     hexpand=True,
                                     margin_start=16,
                                     object=self.object,
                                     data=data)
        self.__add(editor)

    def __remove_data_editor(self, data):
        if self.__data == data:
            self.data = None
            return

        for editor in self.__editors:
            if data == editor.data:
                self.grid.remove(editor)
                self.__editors.remove(editor)
                break

    def __update_view(self):
        if self.data is None and self.info is None:
            return

        info = self.data.info if self.data else self.info

        if info is None:
            return

        nchildren = len(info.children)

        self.remove_button.set_tooltip_text(_('Remove {key}').format(key=info.key))

        # Add a menu if there is more than one child type
        if nchildren > 1:
            self.add_child.props.popover = self.__context_menu_new(info)
            self.add_child.set_visible(True)
        elif nchildren:
            key = list(info.children.keys())[0]
            self.add_only_child.set_tooltip_text(_('Add {key}').format(key=key))
            self.add_only_child.set_visible(True)

        # Item name
        self.label.props.label = info.key

        self.__size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self.__size_group.add_widget(self.label)

        # Value
        if info.type_id:
            editor = cmb_create_editor(self.data.project, info.type_id)
            self.__value_editor = editor

            if self.data:
                GObject.Object.bind_property(self.data, 'value',
                                             self.__value_editor, 'cmb-value',
                                             GObject.BindingFlags.SYNC_CREATE |
                                             GObject.BindingFlags.BIDIRECTIONAL)

            self.top_box.add(editor)

        # Arguments
        for arg in info.args:
            arg_info = info.args[arg]

            label = Gtk.Label(visible=True,
                              label=arg_info.key,
                              xalign=1)

            editor = cmb_create_editor(self.data.project, arg_info.type_id)
            self.__arg_editors[arg_info.key] = editor

            # Initialize value
            self.__update_arg(arg_info.key)

            # Listen for editor value changes and update argument
            editor.connect('notify::cmb-value', self.__on_arg_notify, arg_info)

            self.__add(editor, label)

        # Current children
        if self.data:
            for child in self.data.children:
                self.__add_data_editor(child)

