#
# CmbCSSEditor - Cambalache CSS Editor
#
# Copyright (C) 2022-2024  Juan Pablo Ugarte
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
from cambalache import utils, _
from .cmb_css import CmbCSS


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_css_editor.ui")
class CmbCSSEditor(Gtk.Grid):
    __gtype_name__ = "CmbCSSEditor"

    filename = Gtk.Template.Child()
    priority = Gtk.Template.Child()
    is_global = Gtk.Template.Child()

    ui_menu_button = Gtk.Template.Child()
    ui_box = Gtk.Template.Child()
    infobar = Gtk.Template.Child()
    save_button = Gtk.Template.Child()
    view = Gtk.Template.Child()

    fields = [("filename", "cmb-value"), ("priority", "value"), ("is_global", "active")]

    def __init__(self, **kwargs):
        self._object = None
        self._bindings = []

        super().__init__(**kwargs)

        self.save_button.set_sensitive(False)

        self.priority.set_range(0, 10000)
        self.priority.set_increments(10, 100)

    @GObject.Property(type=CmbCSS)
    def object(self):
        return self._object

    @object.setter
    def _set_object(self, obj):
        if obj == self._object:
            return

        for binding in self._bindings:
            binding.unbind()

        if self._object:
            self._object.project.disconnect_by_func(self.__on_ui_added_removed)
            self._object.disconnect_by_func(self.__on_provider_for_notify)
            self._object.disconnect_by_func(self.__on_css_notify)
            self._object.disconnect_by_func(self.__on_file_changed)

        self._bindings = []

        self._object = obj

        if obj is None:
            self.set_sensitive(False)
            return

        self.filename.dirname = obj.project.dirname
        self.set_sensitive(True)

        for field, target in self.fields:
            binding = GObject.Object.bind_property(
                obj,
                field,
                getattr(self, field),
                target,
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            )
            self._bindings.append(binding)

        binding = GObject.Object.bind_property(
            obj, "css", self.view, "text", GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL
        )
        self._bindings.append(binding)

        obj.project.connect("ui-added", self.__on_ui_added_removed)
        obj.project.connect("ui-removed", self.__on_ui_added_removed)
        obj.connect("notify::provider-for", self.__on_provider_for_notify)
        obj.connect("notify::css", self.__on_css_notify)
        obj.connect("file-changed", self.__on_file_changed)

        self.__update_provider_for()
        self.__update_ui_button_label()

    @Gtk.Template.Callback("on_save_button_clicked")
    def __on_save_button_clicked(self, button):
        self._object.save_css()
        self.infobar.set_revealed(False)
        self.save_button.set_sensitive(False)

    @Gtk.Template.Callback("on_infobar_response")
    def __on_infobar_response(self, infobar, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.__load_filename()

        self.infobar.set_revealed(False)

    def __update_provider_for(self):
        # Remove all css_ui check buttons
        for child in utils.widget_get_children(self.ui_box):
            self.ui_box.remove(child)

        if self._object is None:
            return

        ui_list = self._object.project.get_ui_list()
        provider_for = self._object.provider_for

        # Generate a check button for each UI
        for ui in ui_list:
            check = Gtk.CheckButton(
                label=ui.display_name, active=ui.ui_id in provider_for, halign=Gtk.Align.START, visible=True
            )
            check.connect("toggled", self.__on_check_button_toggled, ui)
            self.ui_box.append(check)

    def __on_file_changed(self, obj):
        self.infobar.set_revealed(True)
        self.save_button.set_sensitive(True)

    def __load_filename(self):
        if not self.object or not self.object.load_css():
            self.save_button.set_sensitive(False)

    def __on_check_button_toggled(self, button, ui):
        if button.props.active:
            self.object.add_ui(ui)
        else:
            self.object.remove_ui(ui)

        self.__update_ui_button_label()

    def __update_ui_button_label(self):
        n = 0
        first_one = None
        child = self.ui_box.get_first_child()

        while child is not None:
            if child.props.active:
                n += 1

                if first_one is None:
                    first_one = child

            child = child.get_next_sibling()

        if first_one is None:
            self.ui_menu_button.props.label = _("None")
        else:
            self.ui_menu_button.props.label = f"{first_one.props.label} + {n - 1}" if n > 1 else first_one.props.label

    def __on_ui_added_removed(self, project, ui):
        self.__update_provider_for()

    def __on_provider_for_notify(self, obj, pspec):
        self.__update_provider_for()

    def __on_css_notify(self, obj, pspec):
        self.save_button.set_sensitive(True)

    @GObject.Signal(
        flags=GObject.SignalFlags.RUN_LAST,
        return_type=bool,
        arg_types=(),
        accumulator=GObject.signal_accumulator_true_handled,
    )
    def remove_css(self):
        if self.object:
            self.object.project.remove_css(self.object)

        return True


Gtk.WidgetClass.set_css_name(CmbCSSEditor, "CmbCSSEditor")
