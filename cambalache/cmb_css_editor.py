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

from gi.repository import GObject, Gio, Gtk, GtkSource, Pango
from cambalache import utils, _
from .cmb_css import CmbCSS


class CmbCSSPriority(GObject.Object):
    __gtype_name__ = "CmbCSSPriority"

    value = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)
    name = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)


class CmbCSSHoverProvider(GObject.Object, GtkSource.HoverProvider):
    __gtype_name__ = "CmbCSSHoverProvider"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def do_populate(self, context, display):
        valid, pos = context.get_iter()
        if not valid:
            return False

        # Get a list of error tags using parsing_error attribute
        if errors := [tag.parsing_error for tag in pos.get_tags() if hasattr(tag, "parsing_error")]:
            display.append(Gtk.Label(label="\n".join(errors)))
            display.props.visible = True
            return True

        # FIXME: returning False gives a warning
        # (run-dev.py:167985): GLib-GIO-CRITICAL **: 09:28:07.517: g_task_return_error: assertion 'error != NULL' failed
        # (run-dev.py:167985): GLib-GIO-CRITICAL **: 09:28:07.517: GTask gtk_source_hover_provider_real_populate_async
        #   (source object: 0x1d15adf0, source tag: 0x7ff2c684c060) finalized without ever returning (using g_task_return_*()).
        #   This potentially indicates a bug in the program.
        # As a workaround hide display and return true
        display.props.visible = False
        return True


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_css_editor.ui")
class CmbCSSEditor(Gtk.Box):
    __gtype_name__ = "CmbCSSEditor"

    filename = Gtk.Template.Child()
    priority = Gtk.Template.Child()
    priority_dropdown = Gtk.Template.Child()
    is_global = Gtk.Template.Child()

    ui_menu_button = Gtk.Template.Child()
    ui_box = Gtk.Template.Child()
    view = Gtk.Template.Child()

    fields = [("filename", "cmb-value"), ("priority", "value"), ("is_global", "active")]

    def __init__(self, **kwargs):
        self._object = None
        self._bindings = []
        self.__tags = []

        super().__init__(**kwargs)

        self.priority.set_range(0, 10000)
        self.priority.set_increments(10, 100)

        self.priority_list = Gio.ListStore(item_type=CmbCSSPriority)

        for name, value in [
            # Translators: GTK_STYLE_PROVIDER_PRIORITY_FALLBACK
            (_("Fallback (1)"), 1),
            # Translators: GTK_STYLE_PROVIDER_PRIORITY_THEME
            (_("Theme (200)"), 200),
            # Translators: GTK_STYLE_PROVIDER_PRIORITY_SETTINGS
            (_("Settings (400)"), 400),
            # Translators: GTK_STYLE_PROVIDER_PRIORITY_APPLICATION
            (_("Application (600)"), 600),
            # Translators: GTK_STYLE_PROVIDER_PRIORITY_USER
            (_("User (800)"), 800),
            # Translators: label for custom GtkStyleProvider priority
            (_("Custom"), -1),
        ]:
            self.priority_list.append(CmbCSSPriority(name=name, value=value))

        self.priority_dropdown.props.model = self.priority_list
        self.__expression = Gtk.PropertyExpression.new(CmbCSSPriority, None, "name")
        self.priority_dropdown.props.expression = self.__expression

        # Add provider for parsing error tooltip
        hover = self.view.get_hover()
        self.__hover_provider = CmbCSSHoverProvider()
        hover.add_provider(self.__hover_provider)

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

        def transform_to(b, value):
            return {
                1: 0,
                200: 1,
                400: 2,
                600: 3,
                800: 4,
            }.get(value, 5)

        def transform_from(b, value):

            self.priority.props.visible = value == 5

            return {
                0: 1,
                1: 200,
                2: 400,
                3: 600,
                4: 800,
            }.get(value, self.priority.props.value)

        binding = GObject.Object.bind_property(
            self.priority,
            "value",
            self.priority_dropdown,
            "selected",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            transform_to=transform_to,
            transform_from=transform_from
        )
        self._bindings.append(binding)
        self.priority.props.visible = transform_to(binding, obj.priority) == 5

        obj.project.connect("ui-added", self.__on_ui_added_removed)
        obj.project.connect("ui-removed", self.__on_ui_added_removed)
        obj.connect("notify::provider-for", self.__on_provider_for_notify)
        obj.connect("parsing-status", self.__on_parsing_status)

        self.__update_provider_for()
        self.__update_ui_button_label()

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

    def __on_parsing_status(self, obj, error_count, message, start, end):
        buffer = self.view.buffer

        # Clear tags if there is no error or is the first error
        if error_count <= 1:
            buffer_start, buffer_end = buffer.get_bounds()

            # Remove all error tags
            for tag in self.__tags:
                buffer.remove_tag(tag, buffer_start, buffer_end)

            self.__tags = []

        if error_count and message:
            tag = buffer.create_tag(None, underline=Pango.Underline.ERROR)

            # Set error message in parsing_error attribute
            setattr(tag, "parsing_error", message)

            # Apply tag in buffer
            buffer.apply_tag(tag, buffer.get_iter_at_offset(start), buffer.get_iter_at_offset(end))

            # Keep a list of error tags to delete
            self.__tags.append(tag)

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
