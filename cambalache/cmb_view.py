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

import os
import json
import socket
import time

from gi.repository import GObject, GLib, Gtk, WebKit

from . import config
from .cmb_ui import CmbUI
from .cmb_object import CmbObject
from .cmb_context_menu import CmbContextMenu
from . import utils
from cambalache import getLogger, _

logger = getLogger(__name__)

basedir = os.path.dirname(__file__) or "."

GObject.type_ensure(WebKit.Settings.__gtype__)
GObject.type_ensure(WebKit.WebView.__gtype__)


class CmbProcess(GObject.Object):
    __gsignals__ = {
        "stdout": (GObject.SignalFlags.RUN_LAST, bool, (GLib.IOCondition,)),
        "exit": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    file = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.pid = 0
        self.stdin = None
        self.stdout = None

    def stop(self):
        if self.stdin:
            self.stdin.shutdown(False)
            self.stdin = None

        if self.stdout:
            self.stdout.shutdown(False)
            self.stdout = None

        if self.pid:
            try:
                GLib.spawn_close_pid(self.pid)
                os.kill(self.pid, 9)
            except Exception as e:
                logger.warning(f"Error stopping {self.file} {e}")

            self.pid = 0

    def run(self, args, env={}):
        if self.file is None or self.pid > 0:
            return

        envp = [f"{var}={val}" for var, val in os.environ.items() if var not in env]

        # Append extra vars
        for var in env:
            envp.append(f"{var}={env[var]}")

        pid, stdin, stdout, stderr = GLib.spawn_async(
            [self.file] + args,
            envp=envp,
            flags=GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            standard_input=True,
            standard_output=True,
        )
        self.pid = pid

        self.stdin = GLib.IOChannel.unix_new(stdin)
        self.stdout = GLib.IOChannel.unix_new(stdout)

        GLib.io_add_watch(self.stdout, GLib.PRIORITY_DEFAULT_IDLE, GLib.IOCondition.IN | GLib.IOCondition.HUP, self.__on_stdout)

        GLib.child_watch_add(GLib.PRIORITY_DEFAULT_IDLE, pid, self.__on_exit, None)

    def __on_exit(self, pid, status, data):
        self.stop()
        self.emit("exit")

    def __on_stdout(self, channel, condition):
        return self.emit("stdout", condition)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_view.ui")
class CmbView(Gtk.Box):
    __gtype_name__ = "CmbView"

    __gsignals__ = {
        "placeholder-selected": (GObject.SignalFlags.RUN_LAST, None, (int, int, object, int, str)),
        "placeholder-activated": (GObject.SignalFlags.RUN_LAST, None, (int, int, object, int, str)),
    }

    preview = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    stack = Gtk.Template.Child()
    webview = Gtk.Template.Child()
    text_view = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.__project = None
        self.__restart_project = None
        self.__ui_id = 0
        self.__theme = None
        self.__dark = False

        self.menu = self.__create_context_menu()

        super().__init__(**kwargs)

        self.__merengue_bin = os.path.join(config.merenguedir, "merengue", "merengue")
        self.__broadwayd_bin = GLib.find_program_in_path("broadwayd")
        self.__gtk4_broadwayd_bin = GLib.find_program_in_path("gtk4-broadwayd")

        self.webview.connect("load-changed", self.__on_load_changed)

        self.__merengue = None
        self.__broadwayd = None
        self.__port = None
        self.__merengue_last_exit = None

        if self.__broadwayd_bin is None:
            logger.warning("broadwayd not found, Gtk 3 workspace wont work.")

        if self.__gtk4_broadwayd_bin is None:
            logger.warning("gtk4-broadwayd not found, Gtk 4 workspace wont work.")

        self.connect("notify::preview", self.__on_preview_notify)

    def do_destroy(self):
        if self.__merengue:
            self.__merengue_command("quit")

        if self.__broadwayd:
            self.__broadwayd.stop()

    def __evaluate_js(self, script):
        self.webview.evaluate_javascript(script, -1, None, None, None, None, None, None)

    def _set_dark_mode(self, dark):
        self.__dark = dark
        self.__evaluate_js(f"document.body.style.background = '{'#222' if dark else 'inherit'}';")

    def __on_load_changed(self, webview, event):
        if event != WebKit.LoadEvent.FINISHED:
            return

        self._set_dark_mode(self.__dark)

        # Disable alert() function used when broadwayd get disconnected
        # Monkey pat ch setupDocument() to avoid disabling document.oncontextmenu
        self.__evaluate_js(
            """
window.alert = function (message) {
    console.log (message);
}

window.merengueSetupDocument = setupDocument;

window.setupDocument = function (document) {
    var cb = oncontextmenu
    merengueSetupDocument(document);
    document.oncontextmenu = cb;
}
"""
        )

    def __merengue_command(self, command, payload=None, args=None):
        if self.__merengue is None or self.__merengue.stdin is None:
            return

        cmd = {"command": command, "payload": payload is not None}

        if args is not None:
            cmd["args"] = args

        # Send command in one line as json
        self.__merengue.stdin.write(json.dumps(cmd))
        self.__merengue.stdin.write("\n")

        if payload is not None:
            self.__merengue.stdin.write(GLib.strescape(payload))
            self.__merengue.stdin.write("\n")

        # Flush
        self.__merengue.stdin.flush()

    def __get_ui_xml(self, ui_id, merengue=False):
        return self.__project.db.tostring(ui_id, merengue=merengue)

    def __update_view(self):
        if self.__project is not None and self.__ui_id > 0:
            if self.stack.props.visible_child_name == "ui_xml":
                ui = self.__get_ui_xml(self.__ui_id)
                self.text_view.buffer.set_text(ui)
            return

        self.text_view.buffer.set_text("")
        self.__ui_id = 0

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
        ui = self.__get_ui_xml(ui_id, merengue=True)
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
        if obj.info.workspace_type is None and prop.info.construct_only:
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

            if type(obj) not in [CmbUI, CmbObject]:
                return

            ui_id = obj.ui_id

            if self.__ui_id != ui_id:
                self.__ui_id = ui_id
                self.__merengue_update_ui(ui_id)

            objects = self.__get_selection_objects(selection, ui_id)
            self.__merengue_command("selection_changed", args={"ui_id": ui_id, "selection": objects})
        else:
            self.__ui_id = 0
            self.__merengue_update_ui(0)

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

    @GObject.Property(type=GObject.GObject)
    def project(self):
        return self.__project

    @project.setter
    def _set_project(self, project):
        if self.__project is not None:
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
            self.__project.disconnect_by_func(self.__on_project_selection_changed)
            self.__merengue.disconnect_by_func(self.__on_merengue_stdout)
            self.__project.disconnect_by_func(self.__on_css_added)
            self.__project.disconnect_by_func(self.__on_css_removed)
            self.__project.disconnect_by_func(self.__on_css_changed)
            self.__merengue.stop()
            self.__broadwayd.stop()

        self.__project = project

        self.__update_view()

        if project is not None:
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
            project.connect("selection-changed", self.__on_project_selection_changed)
            project.connect("css-added", self.__on_css_added)
            project.connect("css-removed", self.__on_css_removed)
            project.connect("css-changed", self.__on_css_changed)

            self.__merengue = CmbProcess(file=self.__merengue_bin)
            self.__merengue.connect("stdout", self.__on_merengue_stdout)
            self.__merengue.connect("exit", self.__on_process_exit)

            self.__broadwayd_check(self.__project.target_tk)

            broadwayd = self.__gtk4_broadwayd_bin if self.__project.target_tk == "gtk-4.0" else self.__broadwayd_bin
            self.__broadwayd = CmbProcess(file=broadwayd)
            self.__broadwayd.connect("stdout", self.__on_broadwayd_stdout)
            self.__broadwayd.connect("exit", self.__on_process_exit)

            self.__port = self.__find_free_port()
            display = self.__port - 8080
            self.__broadwayd.run([f":{display}"])

            # Update css themes
            self.menu.target_tk = self.__project.target_tk

    @GObject.Property(type=str)
    def gtk_theme(self):
        return self.__theme

    @gtk_theme.setter
    def _set_theme(self, theme):
        self.__theme = theme
        self.__merengue_command("gtk_settings_set", args={"property": "gtk-theme-name", "value": theme})

    @Gtk.Template.Callback("on_context_menu")
    def __on_context_menu(self, webview, menu, hit_test_result):
        self.menu.popup_at(*utils.get_pointer(self))
        return True

    def __webview_set_msg(self, msg):
        self.webview.load_html(
            f"""
            <html>
              <body>
                <h3 style="white-space: pre; text-align: center; margin-top: 45vh; opacity: 50%">{msg}</h3>
              </body>
            </html>
            """
        )

    def __broadwayd_check(self, target_tk):
        bin = None

        if target_tk == "gtk-4.0" and self.__gtk4_broadwayd_bin is None:
            bin = "gtk4-broadwayd"
        if target_tk == "gtk+-3.0" and self.__broadwayd_bin is None:
            bin = "broadwayd"

        if bin is not None:
            self.__webview_set_msg(_("Workspace not available\n{bin} executable not found").format(bin=bin))

    def inspect(self):
        self.stack.props.visible_child_name = "ui_xml"
        self.__update_view()

    def restart_workspace(self):
        self.__restart_project = self.__project
        self.project = None

    def __create_context_menu(self):
        retval = CmbContextMenu(enable_theme=True)
        retval.set_parent(self)

        retval.main_section.append(_("Restart workspace"), "win.workspace_restart")
        retval.main_section.append(_("Inspect UI definition"), "win.inspect")

        return retval

    def __on_process_exit(self, process):
        if process == self.__merengue:
            if self.__merengue_last_exit is None:
                self.__merengue_last_exit = time.monotonic()
            else:
                if (time.monotonic() - self.__merengue_last_exit) < 1:
                    self.__webview_set_msg(_("Workspace process error\nStopping auto restart"))
                    self.__merengue_last_exit = None
                    return

        if self.__broadwayd.pid == 0 and self.__merengue.pid == 0:
            self.project = self.__restart_project
            self.__restart_project = None
            self.__ui_id = 0
        else:
            self.__restart_project = self.__project
            self.project = None

    def __command_selection_changed(self, selection):
        objects = []

        for key in selection:
            obj = self.__project.get_object_by_key(key)
            objects.append(obj)

        self.__project.set_selection(objects)

    def __load_namespaces(self):
        if self.project is None:
            return

        for id in self.project.library_info:
            info = self.project.library_info[id]
            self.__merengue_command(
                "load_namespace",
                args={
                    "namespace": info.namespace,
                    "version": info.version,
                    "object_types": info.object_types,
                },
            )

    def __on_preview_notify(self, obj, pspec):
        self.__merengue_command("set_app_property", args={"property": "preview", "value": self.preview})

    def __load_css_providers(self):
        providers = self.project.get_css_providers()

        for css in providers:
            self.__on_css_added(self.project, css)

    def __on_merengue_stdout(self, process, condition):
        if condition == GLib.IOCondition.HUP:
            self.__merengue.stop()
            return GLib.SOURCE_REMOVE

        if self.__merengue.stdout is None:
            return GLib.SOURCE_REMOVE

        retval = self.__merengue.stdout.readline()
        cmd = None

        try:
            cmd = json.loads(retval)
            command = cmd.get("command", None)
            args = cmd.get("args", {})

            if command == "selection_changed":
                self.__command_selection_changed(**args)
            elif command == "started":
                self.__merengue_command("gtk_settings_get", args={"property": "gtk-theme-name"})

                self.__load_namespaces()

                self.__load_css_providers()

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

        except Exception as e:
            logger.warning(f"Merenge output error: {e}")
            self.__merengue.stop()
            return GLib.SOURCE_REMOVE

        return GLib.SOURCE_CONTINUE

    def __on_broadwayd_stdout(self, process, condition):
        if condition == GLib.IOCondition.HUP:
            self.__broadwayd.stop()
            return GLib.SOURCE_REMOVE

        if self.__broadwayd.stdout is None:
            return GLib.SOURCE_REMOVE

        status, retval, length, terminator = self.__broadwayd.stdout.read_line()
        # path = retval.replace("Listening on ", "").strip()

        # Run view process
        if self.__project.target_tk == "gtk+-3.0":
            version = "3.0"
        elif self.__project.target_tk == "gtk-4.0":
            version = "4.0"

        display = self.__port - 8080

        env = json.loads(os.environ.get("MERENGUE_DEV_ENV", "{}"))
        self.__merengue.run(
            [version],
            env
            | {
                "GDK_BACKEND": "broadway",
                # 'GTK_DEBUG': 'interactive',
                "BROADWAY_DISPLAY": f":{display}",
            },
        )

        # Load broadway desktop
        self.webview.load_uri(f"http://127.0.0.1:{self.__port}")

        self.__broadwayd.stdout.shutdown(False)
        self.__broadwayd.stdout = None
        return GLib.SOURCE_REMOVE

    def __find_free_port(self):
        for port in range(8080, 8180):
            s = socket.socket()
            retval = s.connect_ex(("127.0.0.1", port))
            s.close()

            if retval != 0:
                return port

        return 0

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
