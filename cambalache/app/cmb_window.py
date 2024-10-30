#
# CmbWindow
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

import os
import traceback
import locale
import tempfile

from gi.repository import GLib, GObject, Gio, Gdk, Gtk, Pango, Adw
from .cmb_tutor import CmbTutor, CmbTutorState
from . import cmb_tutorial

from cambalache import CmbProject, CmbUI, CmbCSS, CmbObject, CmbTypeChooserPopover, getLogger, config, utils, _

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/app/cmb_window.ui")
class CmbWindow(Adw.ApplicationWindow):
    __gtype_name__ = "CmbWindow"

    __gsignals__ = {
        "open-project": (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        "project-saved": (GObject.SignalFlags.RUN_FIRST, None, (CmbProject,)),
    }

    open_filter = Gtk.Template.Child()
    gtk3_import_filter = Gtk.Template.Child()
    gtk4_import_filter = Gtk.Template.Child()

    headerbar = Gtk.Template.Child()
    title = Gtk.Template.Child()
    recent_menu = Gtk.Template.Child()
    open_button = Gtk.Template.Child()
    undo_button = Gtk.Template.Child()
    redo_button = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    # Start screen
    version_label = Gtk.Template.Child()

    # New Project
    np_name_entry = Gtk.Template.Child()
    np_ui_entry = Gtk.Template.Child()
    np_location_chooser = Gtk.Template.Child()
    np_location_chooser_label = Gtk.Template.Child()
    np_gtk3_radiobutton = Gtk.Template.Child()
    np_gtk4_radiobutton = Gtk.Template.Child()

    # Window message
    message_revealer = Gtk.Template.Child()
    message_label = Gtk.Template.Child()

    # Workspace
    view = Gtk.Template.Child()
    column_view = Gtk.Template.Child()
    type_chooser = Gtk.Template.Child()
    editor_stack = Gtk.Template.Child()
    ui_editor = Gtk.Template.Child()
    ui_requires_editor = Gtk.Template.Child()
    ui_fragment_editor = Gtk.Template.Child()
    fragment_editor = Gtk.Template.Child()
    object_editor = Gtk.Template.Child()
    object_layout_editor = Gtk.Template.Child()
    accessible_editor = Gtk.Template.Child()
    signal_editor = Gtk.Template.Child()
    css_editor = Gtk.Template.Child()

    # Tutor widgets
    intro_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()

    # Settings
    completed_intro = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    MAXIMIZED = 1 << 2
    FULLSCREEN = 1 << 4

    def __init__(self, **kwargs):
        self.__project = None
        self.__last_saved_index = None
        self.__np_location = None

        super().__init__(**kwargs)

        self.__recent_manager = self.__get_recent_manager()

        self.editor_stack.set_size_request(420, -1)

        self.actions = {}

        for action in [
            "about",
            "add_css",
            "add_object",
            "add_object_toplevel",
            "add_placeholder",
            "add_placeholder_row",
            "add_ui",
            "clear",
            "close",
            "contact",
            "copy",
            "create_new",
            "cut",
            "debug",
            "delete",
            "donate",
            "export",
            "import",
            "inspect",
            "intro",
            "liberapay",
            "new",
            "open",
            "paste",
            "patreon",
            "redo",
            "remove_parent",
            "remove_placeholder",
            "remove_placeholder_row",
            "save",
            "save_as",
            "select_project_location",
            "show_workspace",
            "undo",
            "workspace_restart",
        ]:
            gaction = Gio.SimpleAction.new(action, None)
            gaction.connect("activate", getattr(self, f"_on_{action}_activate"))
            self.actions[action] = gaction
            self.add_action(gaction)

        # Stateful actions
        for action, parameter_type, state in [
            ("add_parent", "s", None),
            ("open_recent", "s", None),
            ("workspace_theme", "s", "")
        ]:
            if state is None:
                gaction = Gio.SimpleAction.new(action, GLib.VariantType.new(parameter_type))
            else:
                gaction = Gio.SimpleAction.new_stateful(
                    action, GLib.VariantType.new(parameter_type), GLib.Variant(parameter_type, state)
                )
            gaction.connect("activate", getattr(self, f"_on_{action}_activate"))
            self.actions[action] = gaction
            self.add_action(gaction)

        # Add global accelerators
        action_map = [
            ("win.save", ["<Primary>s"]),
            ("win.save_as", ["<Shift><Primary>s"]),
            ("win.import", ["<Primary>i"]),
            ("win.export", ["<Primary>e"]),
            ("win.close", ["<Primary>w"]),
            ("win.undo", ["<Primary>z"]),
            ("win.redo", ["<Primary><shift>z"]),
            ("win.copy", ["<Primary>c"]),
            ("win.paste", ["<Primary>v"]),
            ("win.cut", ["<Primary>x"]),
            ("win.delete", ["Delete"]),
            ("win.create_new", ["<Primary>n"]),
            ("win.open", ["<Primary>o"]),
            ("win.add_placeholder", ["<Primary>Insert", "<Primary>KP_Insert", "<Primary>KP_Add", "<Primary>plus"]),
            (
                "win.remove_placeholder",
                ["<Primary>Delete", "<Primary>KP_Delete", "<Primary>KP_Subtract", "<Primary>minus"],
            ),
            (
                "win.add_placeholder_row",
                [
                    "<Primary><shift>Insert",
                    "<Primary><shift>KP_Insert",
                    "<Primary><shift>KP_Add",
                    "<Primary><shift>plus",
                ],
            ),
            (
                "win.remove_placeholder_row",
                [
                    "<Primary><shift>Delete",
                    "<Primary><shift>KP_Delete",
                    "<Primary><shift>KP_Subtract",
                    "<Primary><shift>minus",
                ],
            ),
            ("win.show-help-overlay", ["<Primary>question"]),
            ("win.debug", ["<Shift><Primary>d"]),
        ]

        app = Gio.Application.get_default()
        for action, accelerators in action_map:
            app.set_accels_for_action(action, accelerators)

        # Set shortcuts window
        builder = Gtk.Builder()
        builder.add_from_resource("/ar/xjuan/Cambalache/app/cmb_shortcuts.ui")
        self.shortcut_window = builder.get_object("shortcuts")
        self.set_help_overlay(self.shortcut_window)

        self.version_label.props.label = f"version {config.VERSION}"

        GObject.Object.bind_property(
            self.np_name_entry,
            "text",
            self.np_ui_entry,
            "placeholder-text",
            GObject.BindingFlags.SYNC_CREATE,
            self.__np_name_to_ui,
            None,
        )

        self.tutor = None
        self.tutor_waiting_for_user_action = False

        self.__clipboard_enabled = True
        self.__message_timeout_id = None

        # Create settings object
        self.settings = Gio.Settings(schema_id="ar.xjuan.Cambalache")
        self.window_settings = Gio.Settings(schema_id="ar.xjuan.Cambalache.state.window")

        # Settings list
        settings = ["completed-intro"]

        # Bind settings
        for prop in settings:
            self.settings.bind(prop, self, prop.replace("-", "_"), Gio.SettingsBindFlags.DEFAULT)

        self.__load_window_state()
        self.__update_actions()

        app.props.style_manager.connect("notify::dark", lambda o, p: self.__update_dark_mode(app.props.style_manager))
        self.__update_dark_mode(app.props.style_manager)

        # Bind preview
        hide_placeholders_button = Gtk.ToggleButton(tooltip_text=_("Hide placeholders"), icon_name="view-conceal-symbolic")
        self.type_chooser.content.append(hide_placeholders_button)

        GObject.Object.bind_property(
            hide_placeholders_button,
            "active",
            self.view,
            "preview",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )

        self.view.connect("notify::gtk-theme", self.__on_view_gtk_theme_notify)
        self.connect("notify::focus-widget", self.__on_focus_widget_notify)
        self.connect("close-request", self.__on_close_request)

        self.__recent_manager.connect("changed", lambda rm: self.__update_recent_menu())
        self.__update_recent_menu()

    def __get_recent_manager(self):
        # Load the user host recently used file
        if os.environ.get("container", None) == "flatpak":
            recently_used = os.path.join(GLib.get_home_dir(), ".local", "share", "recently-used.xbel")
            if os.path.exists(recently_used):
                return Gtk.RecentManager(filename=recently_used)

        # Fallback to default
        return Gtk.RecentManager.get_default()

    def __on_view_gtk_theme_notify(self, obj, pspec):
        self.actions["workspace_theme"].set_state(GLib.Variant("s", obj.props.gtk_theme))

    @GObject.Property(type=CmbProject)
    def project(self):
        return self.__project

    @project.setter
    def _set_project(self, project):
        if self.__project:
            self.__project.disconnect_by_func(self.__on_project_filename_notify)
            self.__project.disconnect_by_func(self.__on_project_selection_changed)
            self.__project.disconnect_by_func(self.__on_project_changed)

        self.__project = project
        self.view.project = project
        self.type_chooser.project = project
        self.column_view.project = project

        # Clear Editors
        self.ui_editor.object = None
        self.ui_requires_editor.object = None
        self.ui_fragment_editor.object = None
        self.object_editor.object = None
        self.object_layout_editor.object = None
        self.accessible_editor.object = None
        self.signal_editor.object = None
        self.fragment_editor.object = None

        if project:
            self.__project.connect("notify::filename", self.__on_project_filename_notify)
            self.__project.connect("selection-changed", self.__on_project_selection_changed)
            self.__project.connect("changed", self.__on_project_changed)
            self.__on_project_selection_changed(project)

        self.__update_window_title()
        self.__update_actions()

    def __on_project_filename_notify(self, obj, pspec):
        self.__update_window_title()

    def __update_window_title(self):
        if self.project is None:
            self.title.props.title = _("Cambalache")
            self.title.props.subtitle = None
            return

        if self.project.filename:
            path = self.project.filename.replace(GLib.get_home_dir(), "~")
        else:
            path = _("Untitled")

        prefix = "*" if self.__needs_saving() else ""

        self.title.props.title = prefix + os.path.basename(path)
        self.title.props.subtitle = os.path.dirname(path)

    @Gtk.Template.Callback("on_type_chooser_type_selected")
    def __on_type_chooser_type_selected(self, popover, info):
        selection = self.project.get_selection()
        obj = selection[0] if len(selection) else None

        if obj and not isinstance(obj, CmbObject) and not isinstance(obj, CmbUI):
            return

        device = self.get_display().get_default_seat().get_keyboard()

        # If alt is pressed, force adding object to selection
        if device and bool(device.props.modifier_state & Gdk.ModifierType.ALT_MASK):
            if obj:
                parent_id = obj.object_id if isinstance(obj, CmbObject) else None
                self.project.add_object(obj.ui_id, info.type_id, None, parent_id)
                return

        # Windows and non widgets do not need a parent
        if info.is_a("GtkWidget") and not info.is_a("GtkWindow") and info.category != "toplevel":
            # Select type and let user choose which placeholder to use
            self.type_chooser.props.selected_type = info
            self.__update_action_add_object()
        elif obj:
            # Create toplevel object/window
            self.project.add_object(obj.ui_id, info.type_id)

    @Gtk.Template.Callback("on_type_chooser_chooser_popup")
    def __on_type_chooser_chooser_popup(self, chooser, popup):
        self._show_message(_("Hold <alt> to create object in place"))

    @Gtk.Template.Callback("on_type_chooser_chooser_popdown")
    def __on_type_chooser_chooser_popdown(self, chooser, popup):
        self._show_message(None)

    @Gtk.Template.Callback("on_view_placeholder_selected")
    def __on_view_placeholder_selected(self, view, ui_id, object_id, layout, position, child_type):
        info = self.type_chooser.selected_type

        if info is not None:
            self.project.add_object(ui_id, info.type_id, None, object_id, layout, position, child_type)

        self.type_chooser.selected_type = None

    @Gtk.Template.Callback("on_view_placeholder_activated")
    def __on_view_placeholder_activated(self, view, ui_id, object_id, layout, position, child_type):
        obj = self.project.get_object_by_id(ui_id, object_id)
        popover = CmbTypeChooserPopover(pointing_to=utils.get_pointing_to(self.view), parent_type_id=obj.type_id)
        popover.set_parent(self.view)

        popover.project = self.project

        popover.connect(
            "type-selected",
            lambda o, info: self.project.add_object(ui_id, info.type_id, None, object_id, layout, position, child_type),
        )
        popover.popup()

    @Gtk.Template.Callback("on_ui_editor_remove_ui")
    def __on_ui_editor_remove_ui(self, editor):
        self.__remove_object_with_confirmation(editor.object)
        return True

    @Gtk.Template.Callback("on_css_editor_remove_ui")
    def __on_css_editor_remove_ui(self, editor):
        self.__remove_object_with_confirmation(editor.object)
        return True

    def __on_focus_widget_notify(self, obj, pspec):
        widget = self.props.focus_widget

        types = [Gtk.Text, Gtk.TextView]
        focused_widget_needs = True

        for type in types:
            if isinstance(widget, type):
                focused_widget_needs = False
                break

        self.__clipboard_enabled = focused_widget_needs
        self.__update_action_clipboard()

    @Gtk.Template.Callback("on_np_name_entry_changed")
    def __on_np_name_entry_changed(self, editable):
        sensitive = len(editable.get_chars(0, -1)) != 0
        self.np_location_chooser.set_sensitive(sensitive)
        self.np_ui_entry.set_sensitive(sensitive)

    def __update_dark_mode(self, style_manager):
        if style_manager.props.dark:
            self.add_css_class("dark")
            self.view._set_dark_mode(True)
        else:
            self.remove_css_class("dark")
            self.view._set_dark_mode(False)

    def __np_name_to_ui(self, binding, value):
        if len(value):
            return value.lower().rsplit(".", 1)[0] + ".ui"
        else:
            return _("<Choose a UI filename to create>")

    def __is_project_visible(self):
        page = self.stack.get_visible_child_name()
        return self.project and page == "workspace"

    def __set_page(self, page):
        self.stack.set_visible_child_name(page)
        self.__update_actions()

    def __update_action_undo_redo(self):
        if self.__is_project_visible():
            undo_msg, redo_msg = self.project.get_undo_redo_msg()
            self.undo_button.set_tooltip_text(f"Undo: {undo_msg}" if undo_msg is not None else None)
            self.redo_button.set_tooltip_text(f"Redo: {redo_msg}" if redo_msg is not None else None)

            history_index = self.project.history_index
            history_index_max = self.project.history_index_max
            self.actions["undo"].set_enabled(history_index > 0)
            self.actions["redo"].set_enabled(history_index < history_index_max)
        else:
            self.actions["undo"].set_enabled(False)
            self.actions["redo"].set_enabled(False)

    def __update_action_clipboard(self):
        has_selection = False

        if self.__clipboard_enabled and self.__is_project_visible():
            sel = self.project.get_selection()
            if sel:
                # We can delete a UI too
                self.actions["delete"].set_enabled(True)

                for obj in sel:
                    if isinstance(obj, CmbObject):
                        has_selection = True
                        break

            # FIXME: Should we enable copy for CmbUI?
            for action in ["copy", "cut"]:
                self.actions[action].set_enabled(has_selection)
        else:
            for action in ["copy", "cut", "delete"]:
                self.actions[action].set_enabled(False)

        self.__update_action_clipboard_paste()

    def __update_action_clipboard_paste(self):
        if self.__clipboard_enabled and self.__is_project_visible():
            self.actions["paste"].set_enabled(self.project.clipboard_count() > 0)
        else:
            self.actions["paste"].set_enabled(False)

    def __on_project_changed(self, project):
        self.__update_action_undo_redo()
        self.__update_action_save()

    def __on_project_selection_changed(self, project):
        sel = project.get_selection()
        self.__update_action_clipboard()

        obj = sel[0] if len(sel) > 0 else None

        if type(obj) is CmbUI:
            self.ui_editor.object = obj
            self.ui_requires_editor.object = obj
            self.ui_fragment_editor.object = obj
            self.editor_stack.set_visible_child_name("ui")
            obj = None
        elif type(obj) is CmbObject:
            self.editor_stack.set_visible_child_name("object")
            if obj:
                self.__user_message_by_type(obj.info)
        elif type(obj) is CmbCSS:
            self.css_editor.object = obj
            self.editor_stack.set_visible_child_name("css")
            obj = None

        self.object_editor.object = obj

        is_not_builtin = not obj.info.is_builtin if obj else True
        for editor in [self.object_layout_editor, self.signal_editor, self.fragment_editor, self.accessible_editor]:
            editor.object = obj
            editor.props.visible = is_not_builtin

        self.__update_action_add_object()
        self.__update_action_remove_parent()

    def __update_action_intro(self):
        enabled = False

        if not self.completed_intro:
            enabled = True
            self.intro_button.props.tooltip_text = _("Start interactive introduction")

        self.intro_button.set_visible(enabled)

    def __update_action_add_object(self):
        has_project = self.__is_project_visible()
        has_selection = True if self.project and len(self.project.get_selection()) > 0 else False
        has_info = self.type_chooser.props.selected_type is not None
        enabled = has_project and has_selection and has_info

        for action in ["add_object", "add_object_toplevel"]:
            self.actions[action].set_enabled(enabled)

    def __update_action_remove_parent(self):
        if self.project is None:
            self.actions["remove_parent"].set_enabled(False)
            return

        selection = self.project.get_selection()
        obj = selection[0] if len(selection) else None

        if obj and isinstance(obj, CmbObject) and obj.parent_id and obj.parent.n_items == 1:
            self.actions["remove_parent"].set_enabled(True)
            return

        self.actions["remove_parent"].set_enabled(False)

    def __needs_saving(self):
        has_project = self.__is_project_visible()
        changed = has_project and self.project.history_index != self.__last_saved_index

        return has_project and changed

    def __update_action_save(self):
        changed = self.__needs_saving()

        self.__update_window_title()

        self.actions["save"].set_enabled(changed)
        if changed:
            self.title.add_css_class("changed")
        else:
            self.title.remove_css_class("changed")

    def __update_actions(self):
        has_project = self.__is_project_visible()

        for action in ["save_as", "add_ui", "add_css", "delete", "import", "export", "close", "debug"]:
            self.actions[action].set_enabled(has_project)

        self.__update_action_save()
        self.__update_action_intro()
        self.__update_action_clipboard()
        self.__update_action_undo_redo()
        self.__update_action_add_object()
        self.__update_action_remove_parent()

    def __file_open_dialog_new(self, title, filter_obj=None, accept_label=None, use_project_dir=False):
        dialog = Gtk.FileDialog(
            modal=True,
            title=title,
            default_filter=filter_obj,
            accept_label=accept_label,
        )

        if use_project_dir and self.project and self.project.filename:
            dialog.set_initial_folder(Gio.File.new_for_path(os.path.dirname(self.project.filename)))

        return dialog

    def present_message_to_user(self, message, secondary_text=None, details=None):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message,
            secondary_text=secondary_text,
            modal=True,
        )

        if details:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

            for detail in details:
                box.append(
                    Gtk.Label(
                        label=detail,
                        halign=Gtk.Align.START,
                        xalign=0.0,
                        lines=2,
                        max_width_chars=80,
                        wrap_mode=Pango.WrapMode.CHAR,
                        ellipsize=Pango.EllipsizeMode.END,
                    )
                )
            dialog.props.message_area.append(box)

        dialog.connect("response", lambda d, r: dialog.destroy())
        dialog.present()

    def import_file(self, filename, target_tk=None):
        if self.project is None:
            dirname = os.path.dirname(filename)
            basename = os.path.basename(filename)
            name, ext = os.path.splitext(basename)

            if target_tk is None:
                target_tk = CmbProject.get_target_from_ui_file(filename)

            self.project = CmbProject(filename=os.path.join(dirname, f"{name}.cmb"), target_tk=target_tk)
            self.__set_page("workspace")
            self.__update_actions()

        # Check if its already imported
        ui = self.project.get_ui_by_filename(filename)

        if ui:
            self.project.set_selection([ui])
            return

        try:
            ui, msg, detail = self.project.import_file(filename)

            self.project.set_selection([ui])

            if msg:
                details = "\n".join(detail)
                logger.warning(f"Error parsing {filename}\n{details}")

                filename = os.path.basename(filename)
                name, ext = os.path.splitext(filename)
                unsupported_features_list = None
                text = None

                if len(msg) > 1:
                    # Translators: This is used to create a unordered list of unsupported features to show the user
                    list = [_("    • {message}").format(message=message) for message in msg]

                    # Translators: This will be the heading of a list of unsupported features
                    first_msg = _("Cambalache encounter the following issues:")

                    # Translators: this is the last message after the list of unsupported features
                    last_msg = _("Your file will be exported as '{name}.cmb.ui' to avoid data loss.").format(name=name)

                    unsupported_features_list = [first_msg] + list + [last_msg]
                else:
                    unsupported_feature = msg[0]
                    text = _(
                        "Cambalache encounter {unsupported_feature}\n"
                        "Your file will be exported as '{name}.cmb.ui' to avoid data loss."
                    ).format(unsupported_feature=unsupported_feature, name=name)

                self.present_message_to_user(
                    _("Error importing {filename}").format(filename=os.path.basename(filename)),
                    secondary_text=text,
                    details=unsupported_features_list,
                )
        except Exception as e:
            filename = os.path.basename(filename)
            logger.warning(f"Error loading {filename} {traceback.format_exc()}")
            self.present_message_to_user(
                _("Error importing {filename}").format(filename=os.path.basename(filename)), secondary_text=str(e)
            )

    def ask_gtk_version(self, filename):
        basename = os.path.basename(filename)

        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.QUESTION,
            text=_("Which is the target Gtk version of {filename}?").format(filename=basename),
            modal=True,
        )

        dialog.add_button("Gtk 3", 3)
        dialog.add_button("Gtk 4", 4)
        dialog.set_default_response(4)

        def on_ask_gtk_version_response(d, r):
            target_tk = "gtk-4.0" if r == 4 else "gtk+-3.0"
            self.import_file(filename, target_tk=target_tk)
            d.destroy()

        dialog.connect("response", on_ask_gtk_version_response)
        dialog.present()

    def open_project(self, filename, target_tk):
        try:
            if filename is not None:
                content_type = utils.content_type_guess(filename)

                if content_type in ["application/x-gtk-builder", "application/x-glade"]:
                    if target_tk is None:
                        target_tk = CmbProject.get_target_from_ui_file(filename)

                    if target_tk is None and filename is not None:
                        self.ask_gtk_version(filename)
                        return

                    self.import_file(filename, target_tk=target_tk)
                elif content_type != "application/x-cambalache-project":
                    raise Exception(_("Unknown file type {content_type}").format(content_type=content_type))

            if self.project is None:
                self.project = CmbProject(filename=filename, target_tk=target_tk)

            self.__last_saved_index = self.project.history_index
            self.__set_page("workspace")
            self.__update_actions()
        except Exception as e:
            logger.warning(f"Error loading {filename} {traceback.format_exc()}")
            self.present_message_to_user(
                _("Error loading {filename}").format(filename=os.path.basename(filename)), secondary_text=str(e)
            )

    def _on_open_activate(self, action, data):
        def dialog_callback(dialog, res):
            try:
                file = dialog.open_finish(res)
                self.emit("open-project", file.get_path(), None)
            except Exception as e:
                logger.warning(f"Error {e}")

        dialog = self.__file_open_dialog_new(_("Choose project to open"), filter_obj=self.open_filter)
        dialog.open(self, None, dialog_callback)

    def _on_select_project_location_activate(self, action, data):
        def dialog_callback(dialog, res):
            try:
                self.__np_location = dialog.select_folder_finish(res).get_path()
                self.np_location_chooser_label.props.label = os.path.basename(self.__np_location)

            except Exception as e:
                logger.warning(f"Error {e}")

        dialog = self.__file_open_dialog_new(_("Select project location"))
        dialog.select_folder(self, None, dialog_callback)

    def _on_create_new_activate(self, action, data):
        self.__set_page("new_project")
        self.set_focus(self.np_name_entry)

        if self.__np_location is None:
            home = GLib.get_home_dir()
            projects = os.path.join(home, "Projects")
            self.__np_location = projects if os.path.isdir(projects) else home

        self.np_location_chooser_label.props.label = os.path.basename(self.__np_location)

    def _on_new_activate(self, action, data):
        name = self.np_name_entry.props.text
        uiname = self.np_ui_entry.props.text
        filename = None
        uipath = None

        if self.np_gtk3_radiobutton.get_active():
            target_tk = "gtk+-3.0"
        elif self.np_gtk4_radiobutton.get_active():
            target_tk = "gtk-4.0"

        if len(name):
            name, ext = os.path.splitext(name)
            filename = os.path.join(self.__np_location, name + ".cmb")

            if len(uiname) == 0:
                uiname = self.np_ui_entry.props.placeholder_text

            if os.path.exists(filename):
                self.present_message_to_user(_("File name already exists, choose a different name."))
                self.set_focus(self.np_name_entry)
                return

            uipath = os.path.join(self.__np_location, uiname)

        self.emit("open-project", filename, target_tk)

        # Create Ui and select it
        ui = self.project.add_ui(uipath)
        self.project.set_selection([ui])
        self.__set_page("workspace" if self.project else "cambalache")

    def __on_undo_redo_activate(self, undo):
        if self.project is None:
            return
        try:
            if undo:
                self.project.undo()
            else:
                self.project.redo()
        except Exception as e:
            logger.warning(f"Undo/Redo error {traceback.format_exc()}")
            self.present_message_to_user(
                _("Undo/Redo stack got corrupted"),
                secondary_text=_("Please try to reproduce and file an issue\n Error: {msg}").format(msg=str(e))
            )
        self.__update_action_undo_redo()

    def _on_undo_activate(self, action, data):
        self.__on_undo_redo_activate(True)

    def _on_redo_activate(self, action, data):
        self.__on_undo_redo_activate(False)

    def _on_save_activate(self, action, data):
        self.save_project()

    def __save_dialog_callback(self, dialog, res):
        try:
            file = dialog.save_finish(res)
            self.project.filename = file.get_path()
            self.__save()
        except Exception as e:
            logger.warning(f"Error {e}")

    def _on_save_as_activate(self, action, data):
        if self.project is None:
            return

        dialog = self.__file_open_dialog_new(_("Choose a new file to save the project"))
        dialog.save(self, None, self.__save_dialog_callback)

    def _on_add_ui_activate(self, action, data):
        if self.project is None:
            return

        ui = self.project.add_ui()
        self.project.set_selection([ui])

    def _on_add_css_activate(self, action, data):
        if self.project is None:
            return

        css = self.project.add_css()
        self.project.set_selection([css])

    def __remove_object_with_confirmation(self, obj):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Do you really want to remove {name}?").format(name=obj.display_name),
        )

        def on_dialog_response(dialog, response):
            if response == Gtk.ResponseType.YES:
                if type(obj) is CmbUI:
                    self.project.remove_ui(obj)
                elif type(obj) is CmbCSS:
                    self.project.remove_css(obj)

            dialog.destroy()

        dialog.connect("response", on_dialog_response)
        dialog.present()

    def _on_copy_activate(self, action, data):
        if self.project:
            self.project.copy()
            self.__update_action_clipboard_paste()

    def _on_paste_activate(self, action, data):
        if self.project:
            self.project.paste()
            self.__update_action_clipboard_paste()

    def _on_cut_activate(self, action, data):
        if self.project:
            self.project.cut()
            self.__update_action_clipboard_paste()

    def _on_delete_activate(self, action, data):
        if self.project is None:
            return

        selection = self.project.get_selection()
        for obj in selection:
            if type(obj) is CmbObject:
                self.project.remove_object(obj)
            else:
                self.__remove_object_with_confirmation(obj)

    def _on_add_object_activate(self, action, data):
        info = self.type_chooser.props.selected_type
        if self.project is None or info is None:
            return

        selection = self.project.get_selection()
        if len(selection) > 0:
            obj = selection[0]
            parent_id = obj.object_id if isinstance(obj, CmbObject) else None
            self.project.add_object(obj.ui_id, info.type_id, None, parent_id)
            return

    def _on_add_object_toplevel_activate(self, action, data):
        info = self.type_chooser.props.selected_type
        if self.project is None or info is None:
            return

        selection = self.project.get_selection()
        if len(selection) > 0:
            obj = selection[0]
            self.project.add_object(obj.ui_id, info.type_id)
            return

    def _on_clear_activate(self, action, data):
        selection = self.project.get_selection()
        if len(selection) > 0:
            for obj in selection:
                if isinstance(obj, CmbObject):
                    obj.clear_properties()

    def __present_import_error(self, filename, msg, detail):
        details = "\n".join(detail)
        logger.warning(f"Error parsing {filename}\n{details}")

        filename = os.path.basename(filename)
        name, ext = os.path.splitext(filename)
        unsupported_features_list = None
        text = None

        if len(msg) > 1:
            # Translators: This is used to create a unordered list of unsupported features to show the user
            list = [_("    • {message}").format(message=message) for message in msg]

            # Translators: This will be the heading of a list of unsupported features
            first_msg = _("Cambalache encounter the following issues:")

            # Translators: this is the last message after the list of unsupported features
            last_msg = _("Your file will be exported as '{name}.cmb.ui' to avoid data loss.").format(name=name)

            unsupported_features_list = [first_msg] + list + [last_msg]
        else:
            unsupported_feature = msg[0]
            text = _(
                "Cambalache encounter {unsupported_feature}\nYour file will be exported as '{name}.cmb.ui' to avoid data loss."
            ).format(unsupported_feature=unsupported_feature, name=name)

        self.present_message_to_user(
            _("Error importing {filename}").format(filename=filename),
            secondary_text=text,
            details=unsupported_features_list,
        )

    def _on_import_activate(self, action, data):
        if self.project is None:
            return

        def dialog_callback(dialog, res):
            try:
                for file in dialog.open_multiple_finish(res):
                    self.import_file(file.get_path())
            except Exception as e:
                logger.warning(f"Error {e}")

        if self.project.target_tk == "gtk-4.0":
            import_filter = self.gtk4_import_filter
        else:
            import_filter = self.gtk3_import_filter

        dialog = self.__file_open_dialog_new(
            _("Choose file to import"),
            filter_obj=import_filter,
            accept_label=_("Import")
        )
        dialog.open_multiple(self, None, dialog_callback)

    def __save(self):
        if self.project.save():
            self.__last_saved_index = self.project.history_index
            self.__update_action_save()
            self.emit("project-saved", self.project)

    def save_project(self):
        if self.project is None:
            return False

        if self.project.filename is None:
            dialog = self.__file_open_dialog_new(_("Choose a file to save the project"))
            dialog.save(self, None, self.__save_dialog_callback)
            return True

        # Save project and update last saved index
        self.__save()

        return False

    def _on_export_activate(self, action, data):
        if self.project is None:
            return

        self.save_project()

        n = self.project.export()

        self._show_message(_("{n} files exported").format(n=n) if n > 1 else _("File exported"))

    def _close_project_dialog_new(self):
        text = _("Save changes before closing?")
        dialog = Gtk.MessageDialog(
            transient_for=self,
            message_type=Gtk.MessageType.QUESTION,
            text=f"<b><big>{text}</big></b>",
            use_markup=True,
            modal=True,
        )

        # Add buttons
        dialog.add_buttons(
            _("Close without Saving"),
            Gtk.ResponseType.CLOSE,
            _("Cancel"),
            Gtk.ResponseType.CANCEL,
            _("Save"),
            Gtk.ResponseType.ACCEPT,
        )

        dialog.set_default_response(Gtk.ResponseType.ACCEPT)
        return dialog

    def _on_close_activate(self, action, data):
        def close_project():
            self.project = None
            self.__set_page("cambalache")

        if self.actions["save"].get_enabled():
            dialog = self._close_project_dialog_new()

            def callback(dialog, response, window):
                dialog.destroy()

                if response == Gtk.ResponseType.ACCEPT:
                    if self.project.filename is None:
                        def save_callback(dialog, res):
                            try:
                                file = dialog.save_finish(res)
                                self.project.filename = file.get_path()
                                self.save_project()
                                close_project()
                            except Exception as e:
                                logger.warning(f"Error {e}")

                        file_dialog = self.__file_open_dialog_new(_("Choose a new file to save the project"))
                        file_dialog.save(self, None, save_callback)
                    else:
                        self.save_project()
                        close_project()
                elif response == Gtk.ResponseType.CLOSE:
                    close_project()

            dialog.connect("response", callback, self)
            dialog.present()
        else:
            close_project()

    def _on_debug_activate(self, action, data):
        if self.project.filename:
            filename = self.project.filename + ".db"
        else:
            fd, filename = tempfile.mkstemp(".db", "cmb")

        self.project.db_move_to_fs(filename)
        Gtk.show_uri(self, f"file://{filename}", Gdk.CURRENT_TIME)

    def __populate_supporters(self, about):
        gbytes = Gio.resources_lookup_data("/ar/xjuan/Cambalache/app/SUPPORTERS.md", Gio.ResourceLookupFlags.NONE)
        supporters = gbytes.get_data().decode("UTF-8").splitlines()
        sponsors = []

        for name in supporters:
            if name.startswith(" - "):
                sponsors.append(name[3:])

        about.add_credit_section(_("Supporters"), sponsors)

    def __update_translators(self, about):
        lang_country, encoding = locale.getlocale()
        lang = lang_country.split("_")[0]

        translators = {
            "cs": ["Vojtěch Perník"],
            "de": ["PhilProg", "Philipp Unger"],
            "es": ["Juan Pablo Ugarte"],
            "fr": ["rene-coty"],
            "it": ["Lorenzo Capalbo"],
            "nl": ["Gert"],
            "uk": ["Volodymyr M. Lisivka"],
        }

        translator_list = translators.get(lang, None)

        if translator_list:
            about.props.translator_credits = "\n".join(translator_list)

    def _on_about_activate(self, action, data):
        about = Adw.AboutWindow.new_from_appdata("/ar/xjuan/Cambalache/app/metainfo.xml", config.VERSION)

        about.props.transient_for = self
        about.props.artists = [
            "Franco Dodorico",
            "Juan Pablo Ugarte",
        ]
        about.props.copyright = "© 2020-2024 Juan Pablo Ugarte"
        about.props.license_type = Gtk.License.LGPL_2_1_ONLY

        self.__update_translators(about)
        self.__populate_supporters(about)

        about.present()

    def _on_add_parent_activate(self, action, data):
        obj = self.project.get_selection()[0]
        self.project.add_parent(data.get_string(), obj)

    def _on_donate_activate(self, action, data):
        self.__set_page("donate")

    def _on_liberapay_activate(self, action, data):
        Gtk.show_uri(self, "https://liberapay.com/xjuan/donate", Gdk.CURRENT_TIME)

    def _on_patreon_activate(self, action, data):
        Gtk.show_uri(self, "https://www.patreon.com/cambalache", Gdk.CURRENT_TIME)

    def _on_contact_activate(self, action, data):
        Gtk.show_uri(self, "https://matrix.to/#/#cambalache:gnome.org", Gdk.CURRENT_TIME)

    def _on_add_placeholder_activate(self, action, data):
        self.view.add_placeholder()

    def _on_remove_placeholder_activate(self, action, data):
        self.view.remove_placeholder()

    def _on_add_placeholder_row_activate(self, action, data):
        self.view.add_placeholder(modifier=True)

    def _on_remove_placeholder_row_activate(self, action, data):
        self.view.remove_placeholder(modifier=True)

    def _on_remove_parent_activate(self, action, data):
        selection = self.project.get_selection()
        if selection is None or len(selection) == 0:
            return

        self.project.remove_parent(selection[0])

    def _on_show_workspace_activate(self, action, data):
        self.__set_page("workspace" if self.project else "cambalache")

    def __clear_tutor(self):
        try:
            self.disconnect_by_func(self.__on_project_notify)
            self.project.disconnect_by_func(self.__on_ui_added)
            self.project.disconnect_by_func(self.__on_object_added)
        except Exception:
            pass
        self.tutor = None

    def __on_project_notify(self, obj, pspec):
        if self.project:
            self.tutor_waiting_for_user_action = False
            self.tutor.play()
            self.disconnect_by_func(self.__on_project_notify)

    def __on_object_added(self, project, obj, data):
        if obj.info.is_a(data):
            project.disconnect_by_func(self.__on_object_added)
            self.tutor_waiting_for_user_action = False
            self.tutor.play()

    def __on_ui_added(self, project, ui):
        self.tutor_waiting_for_user_action = False
        project.disconnect_by_func(self.__on_ui_added)
        self.tutor.play()

    def __on_tutor_show_node(self, tutor, node, widget):
        if node == "add-project":
            if self.project is None:
                self.connect("notify::project", self.__on_project_notify)
        elif node == "add-ui":
            self.project.connect("ui-added", self.__on_ui_added)
        elif node == "add-window":
            self.project.connect("object-added", self.__on_object_added, "GtkWindow")
        elif node == "add-grid":
            self.project.connect("object-added", self.__on_object_added, "GtkGrid")
        elif node == "add-button":
            self.project.connect("object-added", self.__on_object_added, "GtkButton")
        elif node == "show-type-popover":
            widget.props.popover.popup()
        elif node == "show-type-popover-gtk":
            child = utils.widget_get_children(widget)[0]
            child.props.popover.popup()

    def __on_tutor_hide_node(self, tutor, node, widget):
        if node == "intro-end":
            self.completed_intro = True
            self.__clear_tutor()
        elif node == "add-project":
            if self.__project is None:
                self.tutor_waiting_for_user_action = True
                self.tutor.pause()
        elif node in ["add-ui", "add-window", "add-grid", "add-button"]:
            self.tutor_waiting_for_user_action = True
            self.tutor.pause()
        elif node in ["donate", "export_all"]:
            self.menu_button.popdown()
        elif node == "show-type-popover":
            widget.props.popover.popdown()
        elif node == "show-type-popover-gtk":
            child = utils.widget_get_children(widget)[0]
            child.props.popover.popdown()

        self.__update_actions()

    def _on_intro_activate(self, action, data):
        if self.tutor_waiting_for_user_action:
            return

        if self.tutor:
            if self.tutor.state == CmbTutorState.PLAYING:
                self.tutor.pause()
            else:
                self.tutor.play()
            return

        # Ensure button is visible and reset config flag since we are playing
        # the tutorial from start
        self.intro_button.set_visible(True)
        self.completed_intro = False

        self.tutor = CmbTutor(script=cmb_tutorial.intro, window=self)
        self.tutor.connect("show-node", self.__on_tutor_show_node)
        self.tutor.connect("hide-node", self.__on_tutor_hide_node)
        self.tutor.play()

    def _on_workspace_restart_activate(self, action, data):
        self.view.restart_workspace()

    def _on_workspace_theme_activate(self, action, data):
        self.view.props.gtk_theme = data.get_string()
        action.set_state(data)

    def _on_inspect_activate(self, action, data):
        self.view.inspect()

    def _on_open_recent_activate(self, action, data):
        self.emit("open-project", data.get_string(), None)

    def __update_recent_menu(self):
        mime_types = ["application/x-cambalache-project"]

        self.recent_menu.remove_all()

        for recent in self.__recent_manager.get_items():
            if recent.get_mime_type() not in mime_types:
                continue

            if not recent.exists() or recent.get_age() > 7:
                continue

            filename, host = GLib.filename_from_uri(recent.get_uri())

            item = Gio.MenuItem()
            item.set_label(recent.get_display_name())
            item.set_action_and_target_value("win.open_recent", GLib.Variant("s", filename))
            self.recent_menu.append_item(item)

        # set menu if there is anything
        self.open_button.props.menu_model = self.recent_menu if self.recent_menu.get_n_items() else None

    def __load_window_state(self):
        state = self.window_settings.get_uint("state")

        if state & self.MAXIMIZED:
            self.maximize()
        elif state & self.FULLSCREEN:
            self.fullscreen()
        else:
            size = self.window_settings.get_value("size").unpack()
            self.set_default_size(*size)

    def __save_window_state(self):
        fullscreen = self.props.fullscreened
        maximized = self.props.maximized
        state = 0

        if fullscreen:
            state = state | self.FULLSCREEN

        if maximized:
            state = state | self.MAXIMIZED

        # Maintain compatibility with Gtk 3 state
        self.window_settings.set_uint("state", state)

        size = (0, 0) if fullscreen or maximized else (self.props.default_width, self.props.default_height)

        self.window_settings.set_value("size", GLib.Variant("(ii)", size))

    def __on_close_request(self, window):
        self.__save_window_state()
        return False

    def __user_message_by_type(self, info):
        msg = None

        # TODO: Move this strings to the database, so it can be defined in 3rd party plugins too
        if info.is_a("GtkBox"):
            msg = _("<Ctrl>+Ins/Del to add/remove placeholders")
        elif info.is_a("GtkGrid"):
            msg = _("<Ctrl>+Ins/Del to add/remove columns\n<Shift>+<Ctrl>+Ins/Del to add/remove rows")
        elif info.is_a("GtkAssistant") or info.is_a("GtkStack"):
            msg = _("<Ctrl>+Ins/Del to add/remove pages")

        self._show_message(msg)

    def __on_message_timeout(self, data):
        self.__message_timeout_id = None
        self.message_revealer.props.reveal_child = False
        return GLib.SOURCE_REMOVE

    def _show_message(self, msg):
        if self.__message_timeout_id:
            GLib.source_remove(self.__message_timeout_id)
            self.__message_timeout_id = None

        if msg:
            self.message_label.props.label = msg
            self.message_revealer.props.reveal_child = True
            self.__message_timeout_id = GLib.timeout_add(len(msg) * 100, self.__on_message_timeout, None)
        else:
            self.message_revealer.props.reveal_child = False

