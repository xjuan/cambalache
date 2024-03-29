#
# CmbWindow
#
# Copyright (C) 2021-2023  Juan Pablo Ugarte
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
import traceback
import locale
import tempfile

from gi.repository import GLib, GObject, Gio, Gdk, Gtk, Pango
from .cmb_tutor import CmbTutor, CmbTutorState
from . import cmb_tutorial

from cambalache import CmbProject, CmbUI, CmbCSS, CmbObject, CmbTypeChooserPopover, getLogger, config, _

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/app/cmb_window.ui")
class CmbWindow(Gtk.ApplicationWindow):
    __gtype_name__ = "CmbWindow"

    __gsignals__ = {"open-project": (GObject.SignalFlags.RUN_FIRST, None, (str, str, str))}

    open_filter = Gtk.Template.Child()
    import_filter = Gtk.Template.Child()

    open_button_box = Gtk.Template.Child()
    import_button_box = Gtk.Template.Child()

    headerbar = Gtk.Template.Child()
    undo_button = Gtk.Template.Child()
    redo_button = Gtk.Template.Child()
    stack = Gtk.Template.Child()

    # Start screen
    version_label = Gtk.Template.Child()

    # New Project
    np_name_entry = Gtk.Template.Child()
    np_ui_entry = Gtk.Template.Child()
    np_location_chooser = Gtk.Template.Child()
    np_gtk3_radiobutton = Gtk.Template.Child()
    np_gtk4_radiobutton = Gtk.Template.Child()

    # Window message
    message_revealer = Gtk.Template.Child()
    message_label = Gtk.Template.Child()

    # Workspace
    view = Gtk.Template.Child()
    tree_view = Gtk.Template.Child()
    type_chooser = Gtk.Template.Child()
    preview_button = Gtk.Template.Child()
    editor_stack = Gtk.Template.Child()
    ui_editor = Gtk.Template.Child()
    ui_requires_editor = Gtk.Template.Child()
    ui_fragment_editor = Gtk.Template.Child()
    fragment_editor = Gtk.Template.Child()
    object_editor = Gtk.Template.Child()
    object_layout_editor = Gtk.Template.Child()
    signal_editor = Gtk.Template.Child()
    css_editor = Gtk.Template.Child()

    about_dialog = Gtk.Template.Child()

    # Tutor widgets
    intro_button = Gtk.Template.Child()
    main_menu = Gtk.Template.Child()
    export_all = Gtk.Template.Child()

    # Settings
    completed_intro = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.__project = None
        self.__last_saved_index = None

        super().__init__(**kwargs)

        self.editor_stack.set_size_request(420, -1)

        self.actions = {}
        self.open_button_box.props.homogeneous = False
        self.import_button_box.props.homogeneous = False

        for action in [
            "open",
            "create_new",
            "new",
            "undo",
            "redo",
            "intro",
            "save",
            "save_as",
            "add_ui",
            "add_css",
            "copy",
            "paste",
            "cut",
            "delete",
            "add_object",
            "add_object_toplevel",
            "clear",
            "add_placeholder",
            "remove_placeholder",
            "add_placeholder_row",
            "remove_placeholder_row",
            "import",
            "export",
            "close",
            "debug",
            "show_workspace",
            "donate",
            "liberapay",
            "patreon",
            "contact",
            "about",
        ]:
            gaction = Gio.SimpleAction.new(action, None)
            gaction.connect("activate", getattr(self, f"_on_{action}_activate"))
            self.actions[action] = gaction
            self.add_action(gaction)

        # Add global accelerators
        action_map = [
            ("win.save", ["<Primary>s"]),
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
        ]

        app = Gio.Application.get_default()
        for action, accelerators in action_map:
            app.set_accels_for_action(action, accelerators)

        # Set shortcuts window
        builder = Gtk.Builder()
        builder.add_from_resource("/ar/xjuan/Cambalache/app/cmb_shortcuts.ui")
        self.set_help_overlay(builder.get_object("shortcuts"))

        self.version_label.props.label = f"version {config.VERSION}"
        self.about_dialog.props.version = config.VERSION
        self.__update_translators()
        self.__populate_about_dialog_supporters()

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
        self.turor_waiting_for_user_action = False

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

        settings = Gtk.Settings.get_default()
        settings.connect("notify::gtk-theme-name", lambda o, p: self.__update_dark_mode())
        self.__update_dark_mode()

        # Bind preview
        GObject.Object.bind_property(
            self.preview_button,
            "active",
            self.view,
            "preview",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )

    @GObject.Property(type=CmbProject)
    def project(self):
        return self.__project

    @project.setter
    def _set_project(self, project):
        if self.__project is not None:
            self.__project.disconnect_by_func(self.__on_project_filename_notify)
            self.__project.disconnect_by_func(self.__on_project_selection_changed)
            self.__project.disconnect_by_func(self.__on_project_filename_required)
            self.__project.disconnect_by_func(self.__on_project_changed)

        self.__project = project
        self.view.project = project
        self.tree_view.props.model = project
        self.type_chooser.project = project

        # Clear Editors
        self.ui_editor.object = None
        self.ui_requires_editor.object = None
        self.ui_fragment_editor.object = None
        self.object_editor.object = None
        self.object_layout_editor.object = None
        self.signal_editor.object = None
        self.fragment_editor.object = None

        if project is not None:
            self.__on_project_filename_notify(None, None)
            self.__project.connect("notify::filename", self.__on_project_filename_notify)
            self.__project.connect("selection-changed", self.__on_project_selection_changed)
            self.__project.connect("filename-required", self.__on_project_filename_required)
            self.__project.connect("changed", self.__on_project_changed)
        else:
            self.headerbar.set_subtitle(None)

        self.__update_actions()

    def __on_project_filename_notify(self, obj, pspec):
        if self.project.filename:
            path = self.project.filename.replace(GLib.get_home_dir(), "~")
        else:
            path = _("Untitled")
        self.headerbar.set_subtitle(path)

    @Gtk.Template.Callback("on_about_dialog_delete_event")
    def __on_about_dialog_delete_event(self, widget, event):
        return True

    @Gtk.Template.Callback("on_about_dialog_response")
    def __on_about_dialog_response(self, widget, response_id):
        widget.hide()

    @Gtk.Template.Callback("on_type_chooser_type_selected")
    def __on_type_chooser_type_selected(self, popover, info):
        selection = self.project.get_selection()
        obj = selection[0] if len(selection) else None

        if obj and type(obj) not in [CmbObject, CmbUI]:
            return

        valid, state = Gtk.get_current_event_state()

        # If alt is pressed, force adding object to selection
        if valid and bool(state & Gdk.ModifierType.MOD1_MASK):
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
        r = Gdk.Rectangle()
        r.x, r.y = self.view.get_pointer()
        r.width = r.height = 4

        obj = self.project.get_object_by_id(ui_id, object_id)
        popover = CmbTypeChooserPopover(relative_to=self.view, pointing_to=r, parent_type_id=obj.type_id)

        popover.project = self.project

        popover.connect(
            "type-selected",
            lambda o, info: self.project.add_object(ui_id, info.type_id, None, object_id, layout, position, child_type),
        )
        popover.popup()

    @Gtk.Template.Callback("on_open_recent_action_item_activated")
    def __on_open_recent_action_item_activated(self, recent):
        uri = recent.get_current_uri()
        if uri is not None:
            filename, host = GLib.filename_from_uri(uri)
            self.emit("open-project", filename, None, None)

    @Gtk.Template.Callback("on_ui_editor_remove_ui")
    def __on_ui_editor_remove_ui(self, editor):
        self.__remove_object_with_confirmation(editor.object)
        return True

    @Gtk.Template.Callback("on_css_editor_remove_ui")
    def __on_css_editor_remove_ui(self, editor):
        self.__remove_object_with_confirmation(editor.object)
        return True

    @Gtk.Template.Callback("on_window_set_focus")
    def __on_window_set_focus(self, window, widget):
        types = [Gtk.Entry, Gtk.TextView, Gtk.SpinButton]
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

    def __update_translators(self):
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
            self.about_dialog.props.translator_credits = "\n".join(translator_list)

    def __update_dark_mode(self):
        # https://en.wikipedia.org/wiki/Relative_luminance
        def linear(c):
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

        def luminance(c):
            r, g, b = (linear(c.red), linear(c.green), linear(c.blue))
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        ctx = self.get_style_context()

        # Get foreground color
        fg = ctx.get_color(Gtk.StateFlags.NORMAL)

        # If foreground luminance is closer to 1 then the background must be dark
        if luminance(fg) > 0.5:
            ctx.add_class("dark")
        else:
            ctx.remove_class("dark")

    def __np_name_to_ui(self, binding, value):
        if len(value):
            return value.lower().rsplit(".", 1)[0] + ".ui"
        else:
            return _("<Choose a UI filename to create>")

    def __is_project_visible(self):
        page = self.stack.get_visible_child_name()
        return self.project is not None and page == "workspace"

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

        if type(obj) == CmbUI:
            self.ui_editor.object = obj
            self.ui_requires_editor.object = obj
            self.ui_fragment_editor.object = obj
            self.editor_stack.set_visible_child_name("ui")
            obj = None
        elif type(obj) == CmbObject:
            self.editor_stack.set_visible_child_name("object")
            if obj:
                self.__user_message_by_type(obj.info)
        elif type(obj) == CmbCSS:
            self.css_editor.object = obj
            self.editor_stack.set_visible_child_name("css")
            obj = None

        self.object_editor.object = obj

        is_not_builtin = not obj.info.is_builtin if obj else True
        for editor in [self.object_layout_editor, self.signal_editor, self.fragment_editor]:
            editor.object = obj
            editor.props.visible = is_not_builtin

        self.__update_action_add_object()

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

    def __update_action_save(self):
        has_project = self.__is_project_visible()
        self.actions["save"].set_enabled(has_project and self.project.history_index != self.__last_saved_index)

    def __update_actions(self):
        has_project = self.__is_project_visible()

        for action in ["save_as", "add_ui", "add_css", "delete", "import", "export", "close", "debug"]:
            self.actions[action].set_enabled(has_project)

        self.__update_action_save()
        self.__update_action_intro()
        self.__update_action_clipboard()
        self.__update_action_undo_redo()
        self.__update_action_add_object()

    def __file_open_dialog_new(
        self, title, action=Gtk.FileChooserAction.OPEN, filter_obj=None, select_multiple=False, accept_label=None
    ):
        dialog = Gtk.FileChooserNative(
            title=title,
            transient_for=self,
            action=action,
            filter=filter_obj,
            select_multiple=select_multiple,
            accept_label=accept_label,
        )

        if self.project and self.project.filename:
            dialog.set_current_folder(os.path.dirname(self.project.filename))

        return dialog

    def __populate_about_dialog_supporters(self):
        gbytes = Gio.resources_lookup_data("/ar/xjuan/Cambalache/app/SUPPORTERS.md", Gio.ResourceLookupFlags.NONE)
        supporters = gbytes.get_data().decode("UTF-8").splitlines()
        sponsors = []

        for name in supporters:
            if name.startswith(" - "):
                sponsors.append(name[3:])

        self.about_dialog.add_credit_section(_("Supporters"), sponsors)

    def present_message_to_user(self, message, secondary_text=None, details=None):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message,
            secondary_text=secondary_text,
        )

        if details:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

            for detail in details:
                box.add(
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

            box.show_all()
            dialog.props.message_area.add(box)

        dialog.run()
        dialog.destroy()

    def import_file(self, filename):
        if self.project is None:
            dirname = os.path.dirname(filename)
            basename = os.path.basename(filename)
            name, ext = os.path.splitext(basename)
            target_tk = CmbProject.get_target_from_ui_file(filename)
            self.project = CmbProject(filename=os.path.join(dirname, f"{name}.cmb"), target_tk=target_tk)
            self.__set_page("workspace")
            self.__update_actions()

        # Check if its already imported
        ui = self.project.get_ui_by_filename(filename)

        if ui is not None:
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

    def open_project(self, filename, target_tk=None, uiname=None):
        try:
            self.project = CmbProject(filename=filename, target_tk=target_tk)

            if uiname or (filename is None and uiname is None):
                ui = self.project.add_ui(uiname)
                self.project.set_selection([ui])

            self.__last_saved_index = self.project.history_index
            self.__set_page("workspace")
            self.__update_actions()
        except Exception as e:
            logger.warning(f"Error loading {filename} {traceback.format_exc()}")
            self.present_message_to_user(
                _("Error loading {filename}").format(filename=os.path.basename(filename)), secondary_text=str(e)
            )

    def _on_open_activate(self, action, data):
        dialog = self.__file_open_dialog_new(_("Choose project to open"), filter_obj=self.open_filter)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            self.emit("open-project", dialog.get_filename(), None, None)

        dialog.destroy()

    def _on_create_new_activate(self, action, data):
        self.__set_page("new_project")
        self.set_focus(self.np_name_entry)

        home = GLib.get_home_dir()
        projects = os.path.join(home, "Projects")
        directory = projects if os.path.isdir(projects) else home

        self.np_location_chooser.set_current_folder(directory)

    def _on_new_activate(self, action, data):
        name = self.np_name_entry.props.text
        location = self.np_location_chooser.get_filename() or "."
        uiname = self.np_ui_entry.props.text
        filename = None
        uipath = None

        if self.np_gtk3_radiobutton.get_active():
            target_tk = "gtk+-3.0"
        elif self.np_gtk4_radiobutton.get_active():
            target_tk = "gtk-4.0"

        if len(name):
            name, ext = os.path.splitext(name)
            filename = os.path.join(location, name + ".cmb")

            if len(uiname) == 0:
                uiname = self.np_ui_entry.props.placeholder_text

            if os.path.exists(filename):
                self.present_message_to_user(_("File name already exists, choose a different name."))
                self.set_focus(self.np_name_entry)
                return

            uipath = os.path.join(location, uiname)

        self.emit("open-project", filename, target_tk, uipath)
        self.__set_page("workspace" if self.project is not None else "cambalache")

    def _on_undo_activate(self, action, data):
        if self.project is not None:
            self.project.undo()
            self.__update_action_undo_redo()

    def _on_redo_activate(self, action, data):
        if self.project is not None:
            self.project.redo()
            self.__update_action_undo_redo()

    def __on_project_filename_required(self, project):
        filename = None

        if project.filename is None:
            dialog = self.__file_open_dialog_new(_("Choose a file to save the project"), Gtk.FileChooserAction.SAVE)
            if dialog.run() == Gtk.ResponseType.ACCEPT:
                filename = dialog.get_filename()
            dialog.destroy()

        return filename

    def _on_save_activate(self, action, data):
        self.__save_project()

    def _on_save_as_activate(self, action, data):
        if self.project is None:
            return

        dialog = self.__file_open_dialog_new(_("Choose a new file to save the project"), Gtk.FileChooserAction.SAVE)
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            self.project.filename = dialog.get_filename()
            self.__save_project()

        dialog.destroy()

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
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Do you really want to remove {name}?").format(name=obj.get_display_name()),
        )

        if dialog.run() == Gtk.ResponseType.YES:
            if type(obj) == CmbUI:
                self.project.remove_ui(obj)
            elif type(obj) == CmbCSS:
                self.project.remove_css(obj)

        dialog.destroy()

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
            if type(obj) == CmbObject:
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

        dialog = self.__file_open_dialog_new(
            _("Choose file to import"), filter_obj=self.import_filter, select_multiple=True, accept_label=_("Import")
        )

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            filenames = dialog.get_filenames()
            dialog.destroy()

            for filename in filenames:
                self.import_file(filename)
        else:
            dialog.destroy()

    def __save_project(self):
        if self.project is not None:
            if self.project.save():
                self.__last_saved_index = self.project.history_index
                self.__update_action_save()

    def _on_export_activate(self, action, data):
        if self.project is None:
            return

        self.__save_project()

        n = self.project.export()

        self._show_message(_("{n} files exported").format(n=n) if n > 1 else _("File exported"))

    def _on_close_activate(self, action, data):
        self.project = None
        self.__set_page("cambalache")

    def _on_debug_activate(self, action, data):
        if self.project.filename:
            filename = self.project.filename + ".db"
        else:
            fd, filename = tempfile.mkstemp(".db", "cmb")

        self.project.db_move_to_fs(filename)
        Gtk.show_uri_on_window(self, f"file://{filename}", Gdk.CURRENT_TIME)

    def _on_about_activate(self, action, data):
        self.about_dialog.present()

    def _on_donate_activate(self, action, data):
        self.__set_page("donate")

    def _on_liberapay_activate(self, action, data):
        Gtk.show_uri_on_window(self, "https://liberapay.com/xjuan/donate", Gdk.CURRENT_TIME)

    def _on_patreon_activate(self, action, data):
        Gtk.show_uri_on_window(self, "https://www.patreon.com/cambalache", Gdk.CURRENT_TIME)

    def _on_contact_activate(self, action, data):
        Gtk.show_uri_on_window(self, "https://matrix.to/#/#cambalache:gnome.org", Gdk.CURRENT_TIME)

    def _on_add_placeholder_activate(self, action, data):
        self.view.add_placeholder()

    def _on_remove_placeholder_activate(self, action, data):
        self.view.remove_placeholder()

    def _on_add_placeholder_row_activate(self, action, data):
        self.view.add_placeholder(modifier=True)

    def _on_remove_placeholder_row_activate(self, action, data):
        self.view.remove_placeholder(modifier=True)

    def _on_show_workspace_activate(self, action, data):
        self.__set_page("workspace" if self.project is not None else "cambalache")

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
            self.turor_waiting_for_user_action = False
            self.tutor.play()
            self.disconnect_by_func(self.__on_project_notify)

    def __on_object_added(self, project, obj, data):
        if obj.info.is_a(data):
            project.disconnect_by_func(self.__on_object_added)
            self.turor_waiting_for_user_action = False
            self.tutor.play()

    def __on_ui_added(self, project, ui):
        self.turor_waiting_for_user_action = False
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
        elif node == "main-menu":
            self.main_menu.props.modal = False
        elif node == "show-type-popover":
            widget.props.popover.modal = False
            widget.props.popover.popup()
        elif node == "show-type-popover-gtk":
            child = widget.get_children()[0]
            child.props.popover.props.modal = False
            child.props.popover.popup()

    def __on_tutor_hide_node(self, tutor, node, widget):
        if node == "intro-end":
            self.completed_intro = True
            self.__clear_tutor()
        elif node == "add-project":
            if self.__project is None:
                self.turor_waiting_for_user_action = True
                self.tutor.pause()
        elif node in ["add-ui", "add-window", "add-grid", "add-button"]:
            self.turor_waiting_for_user_action = True
            self.tutor.pause()
        elif node == "main-menu":
            self.export_all.get_style_context().remove_class("cmb-tutor-highlight")
        elif node == "donate":
            self.main_menu.props.modal = True
            self.main_menu.popdown()
        elif node == "show-type-popover":
            widget.props.popover.modal = True
            widget.props.popover.popdown()
        elif node == "show-type-popover-gtk":
            child = widget.get_children()[0]
            child.props.popover.props.modal = True
            child.props.popover.popdown()

        self.__update_actions()

    def _on_intro_activate(self, action, data):
        if self.turor_waiting_for_user_action:
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

    def __load_window_state(self):
        state = self.window_settings.get_uint("state")

        if state & Gdk.WindowState.MAXIMIZED:
            self.maximize()
        else:
            size = self.window_settings.get_value("size").unpack()
            self.set_default_size(*size)

    def __save_window_state(self):
        state = self.props.window.get_state()

        fullscreen = state & Gdk.WindowState.FULLSCREEN
        maximized = state & Gdk.WindowState.MAXIMIZED

        self.window_settings.set_uint("state", state)

        size = (0, 0) if fullscreen or maximized else self.get_size()

        self.window_settings.set_value("size", GLib.Variant("(ii)", size))

    def do_delete_event(self, event):
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


Gtk.WidgetClass.set_css_name(CmbWindow, "CmbWindow")
