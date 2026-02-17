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
import locale
import tempfile

from gi.repository import GLib, GObject, Gio, Gdk, Gtk, Pango, Adw, GtkSource, CambalachePrivate
from .cmb_tutor import CmbTutor, CmbTutorState
from .cmb_np_dialog import CmbNewProjectDialog
from .cmb_donate_dialog import CmbDonateDialog
from . import cmb_tutorial

from cambalache import (
    CmbBaseFileMonitor,
    CmbCSS,
    CmbGResource,
    CmbGResourceEditor,
    CmbObject,
    CmbProject,
    CmbProjectSettings,
    CmbTypeChooserPopover,
    CmbUI,
    _,
    config,
    getLogger,
    ngettext,
    notification_center,
    utils,
)

from cambalache.cmb_blueprint import CmbBlueprintError

logger = getLogger(__name__)

GObject.type_ensure(CmbGResourceEditor.__gtype__)
GObject.type_ensure(CambalachePrivate.Svg.__gtype__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/app/cmb_window.ui")
class CmbWindow(Adw.ApplicationWindow):
    __gtype_name__ = "CmbWindow"

    __gsignals__ = {
        "project-closed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "project-saved": (GObject.SignalFlags.RUN_FIRST, None, (CmbProject,)),
    }

    open_filter = Gtk.Template.Child()
    gtk4_filter = Gtk.Template.Child()
    gtk3_filter = Gtk.Template.Child()
    gtk_builder_filter = Gtk.Template.Child()
    blueprint_filter = Gtk.Template.Child()
    glade_filter = Gtk.Template.Child()
    css_filter = Gtk.Template.Child()
    gresource_filter = Gtk.Template.Child()

    headerbar = Gtk.Template.Child()
    title = Gtk.Template.Child()
    recent_menu = Gtk.Template.Child()
    open_button = Gtk.Template.Child()
    undo_button = Gtk.Template.Child()
    redo_button = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    # Start screen
    logo = Gtk.Template.Child()
    version_label = Gtk.Template.Child()
    front_notification_list_view = Gtk.Template.Child()

    # Notification
    notification_button = Gtk.Template.Child()
    notification_list_view = Gtk.Template.Child()

    # Window message
    message_revealer = Gtk.Template.Child()
    message_label = Gtk.Template.Child()

    # Workspace
    workspace_stack = Gtk.Template.Child()
    view = Gtk.Template.Child()
    source_view = Gtk.Template.Child()
    list_view = Gtk.Template.Child()
    type_chooser = Gtk.Template.Child()
    editor_stack = Gtk.Template.Child()
    ui_editor = Gtk.Template.Child()
    object_editor = Gtk.Template.Child()
    css_editor = Gtk.Template.Child()
    gresource_editor = Gtk.Template.Child()

    # Tutor widgets
    intro_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()

    # Properties
    current_file_object = GObject.Property(type=CmbBaseFileMonitor, flags=GObject.ParamFlags.READWRITE)
    source_style = GObject.Property(type=GtkSource.StyleScheme, flags=GObject.ParamFlags.READWRITE)

    # Settings
    completed_intro = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    MAXIMIZED = 1 << 2
    FULLSCREEN = 1 << 4

    __portal_access_msg = _(
        "Cambalache will not have access to the file for save because it is outside of your home directory. "
        "Consider using Flatseal or flatpak to give permissions to the host directory."
    )

    def __init__(self, **kwargs):
        self.__project = None
        self.__last_saved_index = None
        self.__last_saved_index_version = None

        super().__init__(**kwargs)

        # Logo animation
        def toggle_animation(gesture, n_press, x, y):
            self.logo.props.paintable.props.state = 0 if self.logo.props.paintable.props.state else 2

        click = Gtk.GestureClick()
        click.connect("released", toggle_animation)
        self.logo.add_controller(click)

        self.gtk4_import_filters = Gio.ListStore()

        for filter in [
            self.gtk4_filter,
            self.gtk_builder_filter,
            self.blueprint_filter,
            self.css_filter,
            self.gresource_filter
        ]:
            self.gtk4_import_filters.append(filter)

        self.gtk3_import_filters = Gio.ListStore()
        for filter in [self.gtk3_filter, self.gtk_builder_filter, self.glade_filter, self.css_filter, self.gresource_filter]:
            self.gtk3_import_filters.append(filter)

        self.__recent_manager = self.__get_recent_manager()

        self.actions = {}

        for action in [
            "about",
            "add_css",
            "add_gresource",
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
            "import",
            "import_directory",
            "inspect",
            "intro",
            "liberapay",
            "open",
            "open_inspector",
            "paste",
            "patreon",
            "redo",
            "remove_parent",
            "remove_placeholder",
            "remove_placeholder_row",
            "save",
            "save_as",
            "settings",
            "show_workspace",
            "undo",
            "workspace_restart",
        ]:
            gaction = Gio.SimpleAction.new(action, None)
            gaction.connect("activate", getattr(self, f"_on_{action}_activate"))
            self.actions[action] = gaction
            self.add_action(gaction)

        # Actions with parameters and state
        for action, parameter_type, state_type, state in [
            ("add_parent", "s", None, None),
            ("open_recent", "s", None, None),
            ("workspace_theme", "s", "s", ""),
        ]:
            if state_type is None:
                gaction = Gio.SimpleAction.new(action, GLib.VariantType.new(parameter_type))
            else:
                gaction = Gio.SimpleAction.new_stateful(
                    action, GLib.VariantType.new(parameter_type), GLib.Variant(state_type, state)
                )
            gaction.connect("activate", getattr(self, f"_on_{action}_activate"))
            self.actions[action] = gaction
            self.add_action(gaction)

        # Add global accelerators
        action_map = [
            ("win.save", ["<Primary>s"]),
            ("win.save_as", ["<Shift><Primary>s"]),
            ("win.import", ["<Primary>i"]),
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

        app = self.props.application
        for action, accelerators in action_map:
            app.set_accels_for_action(action, accelerators)

        # Set shortcuts window
        builder = Gtk.Builder()
        builder.add_from_resource("/ar/xjuan/Cambalache/app/cmb_shortcuts.ui")
        self.shortcut_window = builder.get_object("shortcuts")
        self.set_help_overlay(self.shortcut_window)

        # New project dialog
        self.new_project_dialog = None

        self.version_label.props.label = f"version {config.VERSION}"

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

        # Force minimum fize
        self.set_default_size(320, 240)
        self.__load_window_state()
        self.__update_actions()

        self.source_style_manager = GtkSource.StyleSchemeManager.get_default()
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

        self.notification_list_view.notification_center = notification_center
        self.front_notification_list_view.notification_center = notification_center
        notification_center.store.connect("items-changed", self.__on_notification_center_store_items_changed)
        self.__update_notification_status()

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
            self.__project.disconnect_by_func(self.__on_project_gresource_changed)
            self.__project.disconnect_by_func(self.__on_project_changed)

        self.__project = project
        self.view.project = project
        self.type_chooser.project = project
        self.list_view.project = project

        # Clear Editors
        self.ui_editor.object = None
        self.object_editor.object = None

        if project:
            self.__project.connect("notify::filename", self.__on_project_filename_notify)
            self.__project.connect("selection-changed", self.__on_project_selection_changed)
            self.__project.connect("gresource-changed", self.__on_project_gresource_changed)
            self.__project.connect("changed", self.__on_project_changed)
            self.__on_project_selection_changed(project)

        self.__update_window_title()
        self.__update_actions()

    def __on_project_filename_notify(self, obj, pspec):
        self.__update_window_title()

    def __update_window_title(self):
        if self.project is None:
            self.title.props.title = "Cambalache"
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

    def __update_dark_mode(self, style_manager):
        if style_manager.props.dark:
            self.source_style = self.source_style_manager.get_scheme("Adwaita-dark")
            paintable = CambalachePrivate.Svg(resource="/ar/xjuan/Cambalache/app/images/logo-dark.gpa")
            self.add_css_class("dark")
        else:
            paintable = CambalachePrivate.Svg(resource="/ar/xjuan/Cambalache/app/images/logo.gpa")
            self.remove_css_class("dark")
            self.source_style = self.source_style_manager.get_scheme("tango")

        paintable.props.playing = True
        paintable.props.state = 2
        self.logo.props.paintable = paintable

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

    def __update_gresource_view(self):
        if self.workspace_stack.get_visible_child_name() != "gresource":
            return

        sel = self.project.get_selection()
        if len(sel) < 1:
            return

        obj = sel[0]

        if isinstance(obj, CmbGResource):
            gresource_id = obj.gresources_bundle.gresource_id
            resource_xml = self.project.db.gresource_tostring(gresource_id)
        else:
            resource_xml = ""

        self.source_view.buffer.set_text(resource_xml)

    def __on_project_gresource_changed(self, project, gresource, field):
        self.__update_gresource_view()

    def __on_project_selection_changed(self, project):
        sel = project.get_selection()
        self.__update_action_clipboard()

        obj = sel[0] if len(sel) > 0 else None

        if isinstance(obj, CmbUI):
            self.ui_editor.object = obj
            self.current_file_object = obj
            self.workspace_stack.set_visible_child_name("ui")
            self.editor_stack.set_visible_child_name("ui")
            obj = None
        elif isinstance(obj, CmbObject):
            self.current_file_object = obj.ui
            self.workspace_stack.set_visible_child_name("ui")
            self.editor_stack.set_visible_child_name("object")
            if obj:
                self.__user_message_by_type(obj.info)
        elif isinstance(obj, CmbCSS):
            self.current_file_object = None
            self.css_editor.object = obj
            self.editor_stack.set_visible_child_name("css")
            obj = None
        elif isinstance(obj, CmbGResource):
            self.current_file_object = obj
            self.gresource_editor.object = obj
            self.workspace_stack.set_visible_child_name("gresource")
            self.editor_stack.set_visible_child_name("gresource")
            self.__update_gresource_view()
            obj = None

        self.object_editor.object = obj

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
        if self.project is None:
            return False

        return self.__is_project_visible() and (
            self.project.history_index != self.__last_saved_index or
            self.project.history_index_version != self.__last_saved_index_version
        )

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

        for action in [
            "add_css",
            "add_gresource",
            "add_ui",
            "close",
            "debug",
            "delete",
            "import",
            "import_directory",
            "save_as",
            "settings",
        ]:
            self.actions[action].set_enabled(has_project)

        self.__update_action_save()
        self.__update_action_intro()
        self.__update_action_clipboard()
        self.__update_action_undo_redo()
        self.__update_action_add_object()
        self.__update_action_remove_parent()

    def __file_open_dialog_new(self, title, filter_obj=None, accept_label=None, use_project_dir=False, filters=None):
        dialog = Gtk.FileDialog(
            modal=True,
            title=title,
            default_filter=filter_obj,
            filters=filters,
            accept_label=accept_label,
        )

        if use_project_dir and self.project and self.project.filename:
            dialog.set_initial_folder(Gio.File.new_for_path(os.path.dirname(self.project.filename)))

        return dialog

    def present_message_to_user(self, message, secondary_text=None, details=None):
        # TODO: replace with custom widget

        dialog = Gtk.MessageDialog(
            transient_for=self,
            text=message,
            secondary_text=secondary_text,
            modal=True,
        )

        dialog.add_button(_("Copy to clipboard"), 1)
        dialog.add_button(_("Close"), Gtk.ResponseType.CLOSE)

        if details:
            sw = Gtk.ScrolledWindow(
                vexpand=True,
                propagate_natural_width=True,
                propagate_natural_height=True,
                max_content_width=800,
                max_content_height=480,
            )
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            sw.set_child(box)

            for detail in details:
                box.append(
                    Gtk.Label(
                        label=detail,
                        use_markup=True,
                        halign=Gtk.Align.START,
                        xalign=0.0,
                        max_width_chars=120,
                        wrap_mode=Pango.WrapMode.WORD,
                    )
                )
            dialog.props.message_area.append(sw)

        def on_response(dialog, response):
            if response == 1:
                clip = self.get_clipboard()
                clip.set(f"{message}\n{secondary_text}\n{'\n'.join(details or [])}")
            else:
                dialog.destroy()

        dialog.connect("response", on_response)
        dialog.present()

    def __check_if_filename_is_in_portal(self, filename):
        if os.environ.get("FLATPAK_ID", None) != "ar.xjuan.Cambalache":
            return False

        return filename.startswith(f"/run/user/{os.getuid()}/doc/")

    def import_ui(self, filename, target_tk=None, autoselect=True, present_errors=True):
        if self.project is None:
            dirname = os.path.dirname(filename)
            basename = os.path.basename(filename)
            name, ext = os.path.splitext(basename)

            if not target_tk:
                target_tk = CmbProject.get_target_from_ui_file(filename)

            if not target_tk:
                self.ask_gtk_version(filename)
                return (None, None)

            self.project = CmbProject(filename=os.path.join(dirname, f"{name}.cmb"), target_tk=target_tk)
            self.__set_page("workspace")
            self.__update_actions()

        # Check if its already imported
        ui = self.project.get_ui_by_filename(filename)

        if ui:
            if autoselect:
                self.project.set_selection([ui])
            return (None, None)

        try:
            if self.__check_if_filename_is_in_portal(filename):
                raise Exception(self.__portal_access_msg)

            ui, msg, detail = self.project.import_file(filename)

            if autoselect:
                self.project.set_selection([ui])

            if msg:
                details = "\n".join(detail)
                logger.warning(f"Error parsing {filename}\n{details}")

                filename = os.path.basename(filename)
                name, ext = os.path.splitext(filename)
                title = _("Error importing {filename}").format(filename=os.path.basename(filename))

                if len(msg) > 1:
                    # Translators: This is used to create a unordered list of unsupported features to show the user
                    list = [_("    • {message}").format(message=message) for message in msg]

                    # Translators: This will be the heading of a list of unsupported features
                    first_msg = _("Cambalache encounter the following issues:")

                    # Translators: this is the last message after the list of unsupported features
                    last_msg = _("Your file will be saved as '{name}.cmb.ui' to avoid data loss.").format(name=name)

                    unsupported_features_list = [first_msg] + list + [last_msg]
                    if present_errors:
                        self.present_message_to_user(title, details=unsupported_features_list)

                    return (title, "\n".join(unsupported_features_list))
                else:
                    unsupported_feature = msg[0]
                    text = _(
                        "Cambalache encounter {unsupported_feature}\n"
                        "Your file will be saved as '{name}.cmb.ui' to avoid data loss."
                    ).format(unsupported_feature=unsupported_feature, name=name)

                    if present_errors:
                        self.present_message_to_user(title, secondary_text=text)

                    return (title, text)

            # All good!
            return (None, None)
        except Exception as e:
            filename = os.path.basename(filename)
            logger.warning(f"Error loading {filename}", exc_info=True)

            title = _("Exception importing {filename}").format(filename=filename)
            msg = str(e)

            if present_errors:
                self.present_message_to_user(title, secondary_text=msg)

            return (title, msg)

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
            self.import_ui(filename, target_tk=target_tk)
            d.destroy()

        dialog.connect("response", on_ask_gtk_version_response)
        dialog.present()

    def create_project(self, target_tk, filename, uipath):
        if self.project:
            return

        self.project = CmbProject(filename=filename, target_tk=target_tk)
        self.__last_saved_index = self.project.history_index
        self.__last_saved_index_version = self.project.history_index_version

        # Create UI and select it
        ui = self.project.add_ui(uipath)
        self.project.set_selection([ui])

        self.__set_page("workspace")
        self.__update_actions()

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

                    self.import_ui(filename, target_tk=target_tk)
                elif content_type != "application/x-cambalache-project":
                    raise Exception(_("Unknown file type {content_type}").format(content_type=content_type))

            if self.project is None:
                self.project = CmbProject(filename=filename, target_tk=target_tk)

            self.__last_saved_index = self.project.history_index
            self.__last_saved_index_version = self.project.history_index_version
            self.__set_page("workspace")
            self.__update_actions()
        except Exception as e:
            filename = os.path.basename(filename)
            logger.warning(f"Error loading {filename}", exc_info=True)
            self.present_message_to_user(
                _("Error loading {filename}").format(filename=filename), secondary_text=str(e)
            )

    def __app_activate_open(self, filename, target_tk=None):
        if self.__check_if_filename_is_in_portal(filename):
            self.present_message_to_user(
                _("Error opening {filename}").format(filename=os.path.basename(filename)),
                secondary_text=self.__portal_access_msg
            )
            return

        self.props.application.activate_action("open", GLib.Variant("(ss)", (filename, target_tk or "")))

    def _on_open_activate(self, action, data):
        def dialog_callback(dialog, res):
            try:
                file = dialog.open_finish(res)
                self.__app_activate_open(file.get_path())
            except Exception as e:
                logger.warning(f"Error {e}")

        dialog = self.__file_open_dialog_new(_("Choose project to open"), filter_obj=self.open_filter)
        dialog.open(self, None, dialog_callback)

    def _on_create_new_activate(self, action, data):
        self.new_project_dialog = CmbNewProjectDialog()
        self.new_project_dialog.connect("create-new-project", self.__on_create_new_project)
        self.new_project_dialog.present(self)

    def __on_create_new_project(self, dialog, target_tk, filename, uipath):
        # Close dialog
        self.new_project_dialog.close()
        self.new_project_dialog = None

        # Emit application new action
        self.props.application.activate_action("new", GLib.Variant("(sss)", (target_tk, filename, uipath)))

        # Switch to workspace page if project was created
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
            logger.warning("Undo/Redo error", exc_info=True)
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
        filename = None
        try:
            file = dialog.save_finish(res)
            filename = file.get_path()
        except Exception:
            return

        if not filename:
            return

        try:
            if self.__check_if_filename_is_in_portal(filename):
                raise Exception(self.__portal_access_msg)

            self.project.filename = filename
            self.__save()
        except Exception as e:
            filename = os.path.basename(filename) if filename else filename
            logger.warning(f"Error saving {filename}", exc_info=True)
            self.present_message_to_user(
                _("Error importing {filename}").format(filename=filename),
                secondary_text=str(e)
            )

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
                if isinstance(obj, CmbUI):
                    self.project.remove_ui(obj)
                elif isinstance(obj, CmbCSS):
                    self.project.remove_css(obj)
                elif isinstance(obj, CmbGResource):
                    self.project.remove_gresource(obj)

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
            try:
                if isinstance(obj, CmbObject):
                    self.project.remove_object(obj)
                elif isinstance(obj, CmbGResource):
                    if obj.resource_type == "gresources":
                        self.__remove_object_with_confirmation(obj)
                    else:
                        self.project.remove_gresource(obj)
                else:
                    self.__remove_object_with_confirmation(obj)
            except Exception as e:
                self.present_message_to_user(_("Error deleting {name}").format(name=obj.display_name_type), secondary_text=str(e))

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
            last_msg = _("Your file will be saved as '{name}.cmb.ui' to avoid data loss.").format(name=name)

            unsupported_features_list = [first_msg] + list + [last_msg]
        else:
            unsupported_feature = msg[0]
            text = _(
                "Cambalache encounter {unsupported_feature}\nYour file will be saved as '{name}.cmb.ui' to avoid data loss."
            ).format(unsupported_feature=unsupported_feature, name=name)

        self.present_message_to_user(
            _("Error importing {filename}").format(filename=filename),
            secondary_text=text,
            details=unsupported_features_list,
        )

    def import_file(self, path, autoselect=True, present_errors=True):
        content_type = utils.content_type_guess(path)

        if content_type in ["application/x-gtk-builder", "application/x-glade", "text/x-blueprint"]:
            return self.import_ui(path, autoselect=autoselect, present_errors=present_errors)
        elif content_type == "text/css":
            self.project.add_css(path)
        elif content_type == "application/xml" and path.endswith("gresource.xml"):
            self.project.import_gresource(path)

        return (None, None)

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
            import_filters = self.gtk4_import_filters
        else:
            import_filters = self.gtk3_import_filters

        dialog = self.__file_open_dialog_new(
            _("Choose file to import"),
            filters=import_filters,
            accept_label=_("Import"),
            use_project_dir=True
        )
        dialog.open_multiple(self, None, dialog_callback)

    def _on_import_directory_activate(self, action, data):
        if self.project is None:
            return

        def progress_dialog_new():
            dialog = Gtk.Window(
                title="Importing directory",
                transient_for=self,
                default_width=640,
                modal=True
            )
            progressbar = Gtk.ProgressBar(
                text=_("Loading directory contents"),
                ellipsize=Pango.EllipsizeMode.START,
                show_text=True,
                vexpand=True,
                margin_top=32,
                margin_bottom=32,
                margin_start=16,
                margin_end=16,
            )
            dialog.set_child(progressbar)
            dialog.present()

            return dialog, progressbar

        def dialog_callback(dialog, res):
            main_loop = GLib.MainContext.default()

            try:
                dir = dialog.select_folder_finish(res)
                dirpath = dir.get_path()

                progress, progressbar = progress_dialog_new()

                def pulse():
                    progressbar.pulse()
                    while main_loop.pending():
                        main_loop.iteration(False)

                files = self.project._list_supported_files(dirpath, pulse)
                n_files = len(files)

                self.project.history_push(_('Import {n} directory "{dirpath}"').format(dirpath=dirpath, n=n_files))

                basedir = self.project.dirname + "/"

                errors = []

                for i, path in enumerate(files):
                    progressbar.set_text(path.removeprefix(basedir))
                    progressbar.set_fraction(i/n_files)
                    error, error_details = self.import_file(path, autoselect=False, present_errors=False)

                    if error:
                        errors.append(f"\n<b>{error}</b>\n{error_details}")

                    while main_loop.pending():
                        main_loop.iteration(False)

                self.project.history_pop()

                if errors:
                    text = _("{errors} files out of {n} had errors while loading").format(errors=len(errors), n=n_files)
                    self.present_message_to_user(
                        _("Error importing directory {basename}").format(basename=os.path.basename(dirpath)),
                        secondary_text=text,
                        details=errors
                    )
                else:
                    self._show_message(_("Imported {n} files").format(n=n_files))

                progress.close()

            except Exception as e:
                logger.warning(f"Error {e}")

        dialog = self.__file_open_dialog_new(
            _("Choose directory to import"),
            accept_label=_("Import directory"),
            use_project_dir=True
        )
        dialog.select_folder(self, None, dialog_callback)

    def _on_add_gresource_activate(self, action, data):
        if self.project is None:
            return

        gresource = self.project.add_gresource("gresources")
        self.project.set_selection([gresource])

    def __save(self):
        retval = False

        try :
            retval = self.project.save()
        except CmbBlueprintError as e:
            self.present_message_to_user(
                _("Error saving project"),
                secondary_text=ngettext("blueprintcompiler encounter the following error:", "blueprintcompiler encounter the following errors:", len(e.errors)),
                details=[str(e)]
            )
        finally:
            if retval:
                self.__last_saved_index = self.project.history_index
                self.__last_saved_index_version = self.project.history_index_version
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
            self.emit("project-closed")

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

    def _on_settings_activate(self, action, data):
        if self.project is None:
            return

        settings = CmbProjectSettings(project=self.project)
        settings.present(self)

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
            "cs": ["Daniel Rusek", "Vojtěch Perník"],
            "de": ["PhilProg", "Philipp Unger"],
            "es": ["Juan Pablo Ugarte"],
            "fi": ["Erwinjitsu", "Ilmari Lauhakangas"],
            "fr": ["rene-coty"],
            "it": ["Lorenzo Capalbo"],
            "nl": ["Gert"],
            "pt_BR": ["John peter sa"],
            "ro": ["Vlad"],
            "sv": ["Anders Jonsson"],
            "uk": ["Volodymyr M. Lisivka"],
            "zh_CN": ["xu-haozhe"],
        }

        translator_list = translators.get(lang, None)

        if translator_list:
            about.props.translator_credits = "\n".join(translator_list)

    def _on_about_activate(self, action, data):
        about = Adw.AboutDialog.new_from_appdata("/ar/xjuan/Cambalache/app/metainfo.xml", config.VERSION)

        about.props.artists = [
            "Franco Dodorico",
            "Juan Pablo Ugarte",
        ]
        about.props.copyright = "© 2020-2025 Juan Pablo Ugarte"
        about.props.license_type = Gtk.License.LGPL_2_1_ONLY

        self.__update_translators(about)
        self.__populate_supporters(about)

        about.present(self)

    def _on_add_parent_activate(self, action, data):
        obj = self.project.get_selection()[0]
        self.project.add_parent(data.get_string(), obj)

    def _on_donate_activate(self, action, data):
        dialog = CmbDonateDialog()
        dialog.present(self)

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
        elif node in ["donate"]:
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

    def _on_open_inspector_activate(self, action, data):
        self.view.set_interactive_debugging(True)

    def _on_open_recent_activate(self, action, data):
        self.__app_activate_open(data.get_string(), "")

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
            item.set_label(recent.get_display_name().replace("_", "__"))
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
            w, h = self.window_settings.get_value("size").unpack()
            if w and h:
                self.set_default_size(w, h)

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

    @Gtk.Template.Callback("on_notification_close_button")
    def __on_notification_close_button(self, button):
        self.notification_button.props.popover.props.autohide = True
        self.notification_button.popdown()

    def __on_notification_popover_timeout(self, data):
        self.notification_button.props.popover.props.autohide = True
        self.notification_button.popdown()
        return GLib.SOURCE_REMOVE

    def __on_notification_center_store_items_changed(self, store, position, removed, added):
        self.__update_notification_status()

        if added and self.stack.get_visible_child_name() != "cambalache":
            # Set autohide to false, otherwise popover is immediately closed and input does not work anymore
            self.notification_button.props.popover.props.autohide = False
            self.notification_button.popup()
            GLib.timeout_add_seconds(60, self.__on_notification_popover_timeout, None)

    def __update_notification_status(self):
        enabled = bool(notification_center.store.props.n_items > 0)

        if enabled:
            self.notification_button.remove_css_class("hidden")
            self.notification_button.set_visible(True)
            self.notification_button.set_sensitive(True)
        else:
            self.notification_button.add_css_class("hidden")
            self.notification_button.set_sensitive(False)
            self.notification_button.popdown()


