#
# CmbView - Cambalache View
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

import gi
import os
import json
import time
import atexit
import socket

gi.require_version('Casilda', '0.1')
from gi.repository import GObject, GLib, Gio, Gdk, Gtk, Casilda

from . import config
from .cmb_ui import CmbUI
from .cmb_object import CmbObject
from .cmb_context_menu import CmbContextMenu
from cambalache.cmb_blueprint import cmb_blueprint_decompile
from . import utils
from cambalache import getLogger, _, N_

logger = getLogger(__name__)

basedir = os.path.dirname(__file__) or "."

GObject.type_ensure(Casilda.Compositor.__gtype__)


class CmbMerengueProcess(GObject.Object):
    __gsignals__ = {
        "handle-command": (GObject.SignalFlags.RUN_LAST, None, (str,)),
        "exit": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    gtk_version = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    compositor = GObject.Property(type=GObject.Object, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.__file = os.path.join(config.merenguedir, "merengue", "merengue")
        self.__command = None
        self.__command_socket = None
        self.__on_command_in_source = None
        self.__pid = 0

        super().__init__(**kwargs)

    @GObject.Property(type=int)
    def pid(self):
        return self.__pid

    def cleanup(self):
        self.stop()

    def __on_command_in(self, channel, condition):
        if condition == GLib.IOCondition.HUP or self.__command is None:
            self.stop()
            return GLib.SOURCE_REMOVE

        payload = self.__command.readline()
        if payload is not None and payload != "":
            self.emit("handle-command", payload)

        return GLib.SOURCE_CONTINUE

    def start(self):
        if self.__file is None or self.__pid > 0:
            return

        # Create socketpair for commands comunication
        client, server = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)

        # Keep a reference in python to avoid socket close
        self.__command_socket = server

        # Create IOChannel to integrate into glib loop
        self.__command = GLib.IOChannel.unix_new(server.fileno())
        self.__on_command_in_source = GLib.io_add_watch(self.__command,
                                                        GLib.PRIORITY_DEFAULT_IDLE,
                                                        GLib.IOCondition.IN | GLib.IOCondition.HUP,
                                                        self.__on_command_in)

        # Get a socket already connected to the compositor
        wayland_socket = self.compositor.get_client_socket_fd()

        # Create Merengue environment, dont include variables that interfere with backend choice
        ignore_vars = {"GDK_BACKEND", "WAYLAND_SOCKET", "WAYLAND_DISPLAY"}

        envp = [f"{var}={val}" for var, val in os.environ.items() if var not in ignore_vars]

        # Force Gdk backend to wayland
        envp.append("GDK_BACKEND=wayland")

        # Use WAYLAND_SOCKET instead of WAYLAND_DISPLAY
        envp.append(f"WAYLAND_SOCKET={wayland_socket}")

        # Spawn merengue with wayland_socket and client file descriptors
        # TODO: send stdout and error to some place useful for the user
        valid, pid, stdin, stdout, stderr = GLib.spawn_async_with_pipes_and_fds(
            None,
            [self.__file, self.gtk_version, str(client.fileno())],
            envp,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD |
            GLib.SpawnFlags.CHILD_INHERITS_STDIN |
            GLib.SpawnFlags.CHILD_INHERITS_STDERR |
            GLib.SpawnFlags.CHILD_INHERITS_STDOUT,
            None, None,
            -1, -1, -1,
            [wayland_socket, client.fileno()],
            [wayland_socket, client.fileno()]
        )

        # Close file descriptors passed to the client.
        # If we do not close wayland_socket then the client wont be destroyed if its process is killed.
        os.close(wayland_socket)
        client.close()

        if valid:
            self.__pid = pid
            GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE, pid, self.__on_exit, None)

    def __cleanup(self):
        if self.__on_command_in_source:
            GLib.source_remove(self.__on_command_in_source)
            self.__on_command_in_source = None

        if self.__command:
            self.__command.shutdown(True)
            self.__command = None

        self.__command_socket = None

    def stop(self):
        self.__cleanup()

        if self.__pid:
            try:
                GLib.spawn_close_pid(self.__pid)
                os.kill(self.__pid, 9)
            except Exception as e:
                logger.warning(f"Error stopping {self.__file} {e}")
            finally:
                self.__pid = 0

    def write_command(self, command, payload=None, args=None):
        cmd = {"command": command}

        if payload is not None:
            # Encode to binary first, before calculating lenght
            payload = payload.encode()
            cmd["payload_length"] = len(payload)
            logger.debug(f"write_command {command} {len(payload)}")

        if args is not None:
            cmd["args"] = args

        self.__socket_write_command(cmd, payload)

    def __socket_write_command(self, cmd, payload=None):
        # Send command in one line as json

        def write_data(data):
            total_bytes = len(data)
            total_sent = 0
            while total_sent < total_bytes:
                total_sent += self.__command.write(data[total_sent:])

        write_data(json.dumps(cmd).encode())
        write_data(b"\n")

        if payload is not None:
            write_data(payload)

        # Flush
        self.__command.flush()

    def __on_exit(self, pid, status, data):
        self.__cleanup()
        self.__pid = 0
        self.emit("exit")


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_view.ui")
class CmbView(Gtk.Box):
    __gtype_name__ = "CmbView"

    __gsignals__ = {
        "placeholder-selected": (GObject.SignalFlags.RUN_LAST, None, (int, int, object, int, str)),
        "placeholder-activated": (GObject.SignalFlags.RUN_LAST, None, (int, int, object, int, str)),
    }

    show_merengue = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    preview = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    stack = Gtk.Template.Child()
    compositor = Gtk.Template.Child()
    compositor_offload = Gtk.Template.Child()
    compositor_box = Gtk.Template.Child()
    error_box = Gtk.Template.Child()
    error_message = Gtk.Template.Child()
    text_view = Gtk.Template.Child()
    db_inspector = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.__project = None
        self.__ui = None
        self.__theme = None

        self.menu = self.__create_context_menu()

        super().__init__(**kwargs)

        self.__click_gesture = Gtk.GestureClick(propagation_phase=Gtk.PropagationPhase.CAPTURE, button=3)
        self.__click_gesture.connect("pressed", self.__on_click_gesture_pressed)
        self.compositor_box.add_controller(self.__click_gesture)

        self.__merengue = CmbMerengueProcess(compositor=self.compositor)
        self.__merengue.connect("exit", self.__on_process_exit)
        self.__merengue_last_exit = None
        self.__merengue_started = None

        self.connect("notify::preview", self.__on_preview_notify)

        # Ensure we delete all socket files when exiting
        atexit.register(self.__atexit)

    @Gtk.Template.Callback("on_restart_button_clicked")
    def __on_restart_button_clicked(self, button):
        self.restart_workspace()

    def __atexit(self):
        self.__merengue_command("quit")
        self.__merengue.cleanup()

    def __merengue_command(self, command, payload=None, args=None):
        if not self.__merengue_started:
            return

        self.__merengue.write_command(command, payload, args)

    def __get_ui_xml(self, ui_id, merengue=False):
        if self.show_merengue:
            merengue = True

        return self.__project.db.tostring(ui_id, merengue=merengue)

    def __update_view(self):
        if self.__project and self.__ui:
            if self.stack.props.visible_child_name == "ui_xml":
                ui_source = self.__get_ui_xml(self.__ui.ui_id)

                if self.__ui.filename and self.__ui.filename.endswith(".blp"):
                    try:
                        ui_source = cmb_blueprint_decompile(ui_source)
                        self.text_view.lang = "blueprint"
                    except Exception as e:
                        ui_source = _("Error exporting project")
                        ui_source += "\n"
                        ui_source += N_(
                            "blueprintcompiler encounter the following error:",
                            "blueprintcompiler encounter the following errors:",
                            len(e.errors)
                        )
                        ui_source += "\n"
                        ui_source += str(e)
                        self.text_view.lang = ""
                        # TODO: forward error to parent to show to user
                else:
                    self.text_view.lang = "xml"

                self.text_view.buffer.set_text(ui_source)
            return

        self.text_view.buffer.set_text("")
        self.__ui = None

    def __get_ui_dirname(self, ui_id):
        dirname = GLib.get_home_dir()

        # Use project dir as default base directory
        if self.__project.filename:
            dirname = os.path.dirname(self.__project.filename)
        else:
            dirname = os.getcwd()

        # Use UI directory
        ui = self.__project.get_object_by_id(ui_id)
        if ui and ui.filename:
            dirname = os.path.join(dirname, os.path.dirname(ui.filename))

        return dirname

    def __merengue_update_ui(self, ui_id):
        ui = self.__get_ui_xml(ui_id, merengue=True) if ui_id else None
        toplevels = self.__project.db.get_toplevels(ui_id)
        selection = self.__project.get_selection()
        objects = self.__get_selection_objects(selection, ui_id)

        self.__merengue_command(
            "update_ui",
            payload=ui,
            args={
                "ui_id": ui_id,
                "dirname": self.__get_ui_dirname(ui_id),
                "toplevels": toplevels,
                "selection": objects,
            },
        )

    def __on_changed(self, project):
        self.__update_view()

    def __on_ui_changed(self, project, ui, field):
        if field in ["custom-fragment", "filename"]:
            self.__merengue_update_ui(ui.ui_id)

    def __on_object_added(self, project, obj):
        self.__merengue_update_ui(obj.ui_id)

    def __on_object_removed(self, project, obj):
        self.__merengue_update_ui(obj.ui_id)

    def __on_object_changed(self, project, obj, field):
        if field in ["type", "position", "custom-fragment", "parent-id"]:
            self.__merengue_update_ui(obj.ui_id)

    def __on_object_property_changed(self, project, obj, prop):
        info = prop.info

        # FIXME: implement new merengue command for updating a11y props
        if info.is_a11y:
            return

        if obj.info.workspace_type is None and info.construct_only:
            self.__merengue_update_ui(obj.ui_id)
            return

        self.__merengue_command(
            "object_property_changed",
            args={
                "ui_id": obj.ui_id,
                "object_id": obj.object_id,
                "property_id": prop.property_id,
                "is_object": prop.info.is_object,
                "value": prop.value,
            },
        )

    def __on_object_layout_property_changed(self, project, obj, child, prop):
        self.__merengue_command(
            "object_layout_property_changed",
            args={
                "ui_id": obj.ui_id,
                "object_id": obj.object_id,
                "child_id": child.object_id,
                "property_id": prop.property_id,
                "value": prop.value,
            },
        )

    def __on_object_property_binding_changed(self, project, obj, prop):
        self.__merengue_update_ui(obj.ui_id)

    def __get_selection_objects(self, selection, ui_id):
        objects = []

        for obj in selection:
            if type(obj) is CmbObject and obj.ui_id == ui_id:
                objects.append(obj.object_id)

        return objects

    def __on_project_selection_changed(self, project):
        selection = project.get_selection()

        if len(selection) > 0:
            obj = selection[0]

            if isinstance(obj, CmbUI):
                ui = obj
            elif isinstance(obj, CmbObject):
                ui = obj.ui
            else:
                return

            ui_id = obj.ui_id

            if self.__ui != ui:
                self.__ui = ui
                self.__merengue_update_ui(ui.ui_id)

            objects = self.__get_selection_objects(selection, ui.ui_id)
            self.__merengue_command("selection_changed", args={"ui_id": ui_id, "selection": objects})
        else:
            self.__ui = None
            self.__merengue_update_ui(0)

        self.__update_view()

    def __on_css_added(self, project, obj):
        if self.project.filename and obj.filename:
            dirname = os.path.dirname(self.project.filename)
            filename = os.path.join(dirname, obj.filename)
        else:
            filename = None

        self.__merengue_command(
            "add_css_provider",
            args={
                "css_id": obj.css_id,
                "filename": filename,
                "priority": obj.priority,
                "is_global": obj.is_global,
                "provider_for": obj.provider_for,
            },
        )

    def __on_css_removed(self, project, obj):
        self.__merengue_command("remove_css_provider", args={"css_id": obj.css_id})

    def __on_css_changed(self, project, obj, field):
        value = obj.get_property(field)

        if field == "filename" and value:
            dirname = os.path.dirname(self.project.filename)
            value = os.path.join(dirname, value)

        self.__merengue_command("update_css_provider", args={"css_id": obj.css_id, "field": field, "value": value})

    def __on_object_data_changed(self, project, data):
        self.__merengue_update_ui(data.ui_id)

    def __on_object_data_removed(self, project, obj, data):
        self.__merengue_update_ui(data.ui_id)

    def __on_object_data_data_removed(self, project, parent, data):
        self.__merengue_update_ui(data.ui_id)

    def __on_object_data_arg_changed(self, project, data, value):
        self.__merengue_update_ui(data.ui_id)

    def __on_object_child_reordered(self, project, obj, child, old_position, new_position):
        self.__merengue_update_ui(obj.ui_id)

    def __set_error_message(self, message):
        if message:
            self.error_message.props.label = message
            self.compositor_offload.set_visible(False)
            self.error_box.set_visible(True)
        else:
            self.error_message.props.label = ""
            self.compositor_offload.set_visible(True)
            self.error_box.set_visible(False)

    @GObject.Property(type=GObject.GObject)
    def project(self):
        return self.__project

    @project.setter
    def _set_project(self, project):
        if self.__project:
            self.__project.disconnect_by_func(self.__on_changed)
            self.__project.disconnect_by_func(self.__on_ui_changed)
            self.__project.disconnect_by_func(self.__on_object_added)
            self.__project.disconnect_by_func(self.__on_object_removed)
            self.__project.disconnect_by_func(self.__on_object_changed)
            self.__project.disconnect_by_func(self.__on_object_property_changed)
            self.__project.disconnect_by_func(self.__on_object_layout_property_changed)
            self.__project.disconnect_by_func(self.__on_object_property_binding_changed)
            self.__project.disconnect_by_func(self.__on_object_data_changed)
            self.__project.disconnect_by_func(self.__on_object_data_removed)
            self.__project.disconnect_by_func(self.__on_object_data_data_removed)
            self.__project.disconnect_by_func(self.__on_object_data_arg_changed)
            self.__project.disconnect_by_func(self.__on_object_child_reordered)
            self.__project.disconnect_by_func(self.__on_project_selection_changed)
            self.__project.disconnect_by_func(self.__on_css_added)
            self.__project.disconnect_by_func(self.__on_css_removed)
            self.__project.disconnect_by_func(self.__on_css_changed)
            self.__merengue.disconnect_by_func(self.__on_merengue_handle_command)
            self.__merengue.stop()

        self.__project = project
        self.db_inspector.project = project

        self.__update_view()

        if project:
            project.connect("changed", self.__on_changed)
            project.connect("ui-changed", self.__on_ui_changed)
            project.connect("object-added", self.__on_object_added)
            project.connect("object-removed", self.__on_object_removed)
            project.connect("object-changed", self.__on_object_changed)
            project.connect("object-property-changed", self.__on_object_property_changed)
            project.connect("object-layout-property-changed", self.__on_object_layout_property_changed)
            project.connect("object-property-binding-changed", self.__on_object_property_binding_changed)
            project.connect("object-data-changed", self.__on_object_data_changed)
            project.connect("object-data-removed", self.__on_object_data_removed)
            project.connect("object-data-data-removed", self.__on_object_data_data_removed)
            project.connect("object-data-arg-changed", self.__on_object_data_arg_changed)
            project.connect("object-child-reordered", self.__on_object_child_reordered)
            project.connect("selection-changed", self.__on_project_selection_changed)
            project.connect("css-added", self.__on_css_added)
            project.connect("css-removed", self.__on_css_removed)
            project.connect("css-changed", self.__on_css_changed)
            self.__merengue.connect("handle-command", self.__on_merengue_handle_command)

            # Run view process
            if project.target_tk == "gtk+-3.0":
                self.__merengue.gtk_version = "3.0"
            elif project.target_tk == "gtk-4.0":
                self.__merengue.gtk_version = "4.0"

            # Clear any error
            self.__set_error_message(None)
            self.__merengue.start()

            # Update css themes
            self.menu.target_tk = project.target_tk

    @GObject.Property(type=str)
    def gtk_theme(self):
        return self.__theme

    @gtk_theme.setter
    def _set_theme(self, theme):
        self.__theme = theme
        self.__merengue_command("gtk_settings_set", args={"property": "gtk-theme-name", "value": theme})

    def __on_click_gesture_pressed(self, gesture, n_press, x, y):
        if gesture.get_current_button() == 3:
            self.menu.popup_at(x, y)

    def inspect(self):
        self.stack.props.visible_child_name = "ui_xml"
        self.__update_view()

    def restart_workspace(self):
        # Clear last exit timestamp
        self.__merengue_last_exit = None
        self.__merengue_started = None

        if self.__merengue.pid:
            # Let __on_process_exit() restart Merengue
            self.__merengue.stop()
        else:
            self.__set_error_message(None)
            self.__merengue.start()

    def __create_context_menu(self):
        retval = CmbContextMenu(enable_theme=True)
        retval.set_parent(self)

        retval.main_section.append(_("Restart workspace"), "win.workspace_restart")
        retval.main_section.append(_("Inspect UI definition"), "win.inspect")

        return retval

    def __on_process_exit(self, process):
        self.__merengue_started = None

        if self.__merengue_last_exit is None:
            self.__merengue_last_exit = time.monotonic()
        else:
            # Stop auto restart if Merengue exited less than 2 seconds ago
            if (time.monotonic() - self.__merengue_last_exit) < 2:
                self.__set_error_message(_("Workspace process error\nStopping auto restart"))
                self.__merengue_last_exit = None
                return

        self.__ui = None
        self.__merengue.start()

    def __command_selection_changed(self, selection):
        objects = []

        for key in selection:
            obj = self.__project.get_object_by_key(key)
            objects.append(obj)

        self.__project.set_selection(objects)

    def __load_namespaces(self):
        if self.project is None:
            return

        for id, info in self.project.library_info.items():
            # Only load 3rd party libraries, Gtk ones are already loaded
            if not info.third_party:
                continue

            self.__merengue_command(
                "load_namespace",
                args={
                    "namespace": info.namespace,
                    "version": info.version,
                    "object_types": info.object_types,
                },
            )

    def __set_icontheme_search_paths(self):
        if self.project is None or self.project.filename is None:
            return

        dirname = os.path.dirname(self.project.filename)

        self.__merengue_command(
            "set_icontheme_search_paths",
            args={"paths": [os.path.join(dirname, path) for path in self.project.icontheme_search_paths]}
        )

    def __on_preview_notify(self, obj, pspec):
        self.__merengue_command("set_app_property", args={"property": "preview", "value": self.preview})

    def __load_css_providers(self):
        providers = self.project.get_css_providers()

        for css in providers:
            self.__on_css_added(self.project, css)

    def __on_merengue_handle_command(self, merengue, payload):
        try:
            cmd = json.loads(payload)
            command = cmd.get("command", None)
            args = cmd.get("args", {})
        except Exception as e:
            logger.warning(f"Merengue command error: {e}")
            self.__merengue.stop()
            return

        if command == "selection_changed":
            self.__command_selection_changed(**args)
        elif command == "started":
            self.__merengue_started = True
            self.__merengue_command("gtk_settings_get", args={"property": "gtk-theme-name"})

            self.__set_icontheme_search_paths()

            self.__load_namespaces()

            self.__load_css_providers()

            self.__ui = None
            self.__on_project_selection_changed(self.__project)
        elif command == "placeholder_selected":
            self.emit(
                "placeholder-selected",
                args["ui_id"],
                args["object_id"],
                args["layout"],
                args["position"],
                args["child_type"],
            )
        elif command == "placeholder_activated":
            self.emit(
                "placeholder-activated",
                args["ui_id"],
                args["object_id"],
                args["layout"],
                args["position"],
                args["child_type"],
            )
        elif command == "gtk_settings_get":
            if args["property"] == "gtk-theme-name":
                self.__theme = args["value"]
                self.notify("gtk_theme")

    def __add_remove_placeholder(self, command, modifier):
        if self.project is None:
            return

        selection = self.project.get_selection()
        if len(selection) < 0:
            return

        obj = selection[0]
        self.__merengue_command(command, args={"ui_id": obj.ui_id, "object_id": obj.object_id, "modifier": modifier})

    def add_placeholder(self, modifier=False):
        self.__add_remove_placeholder("add_placeholder", modifier)

    def remove_placeholder(self, modifier=False):
        self.__add_remove_placeholder("remove_placeholder", modifier)


Gtk.WidgetClass.set_css_name(CmbView, "CmbView")


