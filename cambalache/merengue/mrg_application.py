#
# Merengue: Cambalache view process
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
import sys
import json

from gi.repository import GLib, Gio, Gdk, Gtk

from .mrg_controller_registry import MrgControllerRegistry
from .mrg_placeholder import MrgPlaceholder
from . import utils

from merengue import getLogger

logger = getLogger(__name__)


class MrgApplication(Gtk.Application):
    def __init__(self):
        self.stdin = None

        super().__init__(application_id='ar.xjuan.Merengue',
                         flags=Gio.ApplicationFlags.NON_UNIQUE)

        # Needed to parse values from strings
        self.builder = Gtk.Builder()

        # List of available controler classes for objects
        self.registry = MrgControllerRegistry()

        # List of controllers
        self.controllers = {}

        # The widget that got the last button press this is used to select
        # a widget on button release
        self.preselected_widget = None

        self.settings = Gtk.Settings.get_default()

    def get_controller(self, ui_id, object_id):
        return self.controllers.get(f'{ui_id}.{object_id}', None)

    def get_controller_from_object(self, obj):
        object_id = utils.object_get_id(obj)
        return self.controllers.get(object_id, None)

    def clear_all(self, clear_selection=False):
        self.preselected_widget = None

        # Unset controllers objects
        for key in self.controllers:
            controller = self.controllers[key]
            controller.object = None
            if clear_selection:
                controller.selected = False

    def update_ui(self, ui_id, toplevels=[], payload=None):
        self.clear_all(clear_selection=ui_id == 0)

        if payload == None:
            return

        # Build everything
        builder = Gtk.Builder()

        try:
            builder.add_from_string(payload)
        except Exception as e:
            logger.warning(f'Error updating UI {ui_id}: {e}')

        objects = builder.get_objects()
        placeholders = []

        # Keep dict of all object controllers by id
        for obj in objects:
            if isinstance(obj, MrgPlaceholder):
                placeholders.append(obj)

            object_id = utils.object_get_id(obj)

            if object_id is None:
                continue

            if issubclass(type(obj), Gtk.Expander):
                obj.props.expanded = True

            controller = self.controllers.get(object_id, None)
            pspec = controller.find_property('object') if controller else None

            # FIXME: object_id could be reused for a different object type
            # if you undo the creation of a widget and create a different type
            # As a workaround if the types do not match we create a new controller
            # This could be fixed if we alway auto increment object_id but then
            # we would have to clean up unussed controllers
            if pspec is None or pspec.value_type != obj.__gtype__:
                controller = self.registry.new_controller_for_type(obj.__gtype__, self)

            controller.toplevel = object_id in toplevels
            controller.object = obj
            self.controllers[object_id] = controller

        # Set controller for placeholders created by Builder
        for obj in placeholders:
            parent_id = utils.object_get_id(obj.props.parent)
            obj.controller = self.controllers.get(parent_id, None)

    def object_property_changed(self, ui_id, object_id, property_id, is_object, value):
        controller = self.get_controller(ui_id, object_id)

        if controller is None:
            return

        if is_object:
            target_controller = self.get_controller(ui_id, value)

            if target_controller:
                controller.set_object_property(property_id,
                                               target_controller.object)

            return

        if controller.object is None:
            return

        pspec = controller.object.find_property(property_id)

        if pspec:
            try:
                status, val = self.builder.value_from_string_type(pspec.value_type, value)
                if status:
                    controller.set_object_property(property_id, val)
            except:
                pass

    def object_layout_property_changed(self, ui_id, object_id, child_id, property_id, value):
        controller = self.get_controller(ui_id, object_id)
        child = self.get_controller(ui_id, child_id)

        if controller is None or child is None:
            return

        pspec = controller.find_child_property(child.object, property_id)

        if pspec:
            try:
                status, val = self.builder.value_from_string_type(pspec.value_type, value)
                if status:
                    controller.set_object_child_property(child.object, property_id, val)
            except:
                pass

    def selection_changed(self, ui_id, selection):
        # Clear objects
        for object_id in self.controllers:
            self.controllers[object_id].selected = False

        length = len(selection)

        # Add class to selected objects
        for object_id in selection:
            controller = self.get_controller(ui_id, object_id)
            if controller is None:
                continue

            obj = controller.object

            if obj and issubclass(type(obj), Gtk.Widget):
                controller.selected = True

                if length == 1 and issubclass(type(obj), Gtk.Window):
                    # TODO: fix broadway for this to work
                    obj.present()

    def gtk_settings_set(self, property, value):
        self.settings.set_property(property, value)

    def gtk_settings_get(self, property):
        utils.write_command('gtk_settings_get',
                            args={
                                'property': property,
                                'value': self.settings.get_property(property)
                            })

    def add_placeholder(self, ui_id, object_id, modifier):
        controller = self.get_controller(ui_id, object_id)
        if controller:
            controller.add_placeholder(modifier)

    def remove_placeholder(self, ui_id, object_id, modifier):
        controller = self.get_controller(ui_id, object_id)
        if controller:
            controller.remove_placeholder(modifier)

    def run_command(self, command, args, payload):
        logger.debug(f'{command} {args}')

        if command == 'clear_all':
            self.clear_all()
        elif command == 'update_ui':
            self.update_ui(**args, payload=payload)
        elif command == 'selection_changed':
            self.selection_changed(**args)
        elif command == 'object_property_changed':
            self.object_property_changed(**args)
        elif command == 'object_layout_property_changed':
            self.object_layout_property_changed(**args)
        elif command == 'gtk_settings_set':
            self.gtk_settings_set(**args)
        elif command == 'gtk_settings_get':
            self.gtk_settings_get(**args)
        elif command == 'add_placeholder':
            self.add_placeholder(**args)
        elif command == 'remove_placeholder':
            self.remove_placeholder(**args)
        else:
            logger.warning(f'Unknown command {command}')

    def on_stdin(self, channel, condition):
        if condition == GLib.IOCondition.HUP:
            sys.exit(-1)
            return GLib.SOURCE_REMOVE

        # We receive a command in each line
        retval = self.stdin.readline()

        try:
            # Command is a Json string with a command, args and payload fields
            cmd = json.loads(retval)
        except Exception as e:
            logger.warning(f'Error parsing command {e}')
        else:
            command = cmd.get('command', None)
            args = cmd.get('args', {})
            has_payload = cmd.get('payload', False)

            # Read payload
            payload = GLib.strcompress(self.stdin.readline()) if has_payload else None

            # Run command
            self.run_command(command, args, payload)

        return GLib.SOURCE_CONTINUE

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # TODO: support multiples plugins
        from merengue import mrg_gtk
        self.registry.load_module(mrg_gtk)

        self.stdin = GLib.IOChannel.unix_new(sys.stdin.fileno())
        GLib.io_add_watch(self.stdin, GLib.PRIORITY_DEFAULT_IDLE,
                          GLib.IOCondition.IN | GLib.IOCondition.HUP,
                          self.on_stdin)

        provider = Gtk.CssProvider()
        provider.load_from_resource('/ar/xjuan/Merengue/merengue.css')

        if Gtk.MAJOR_VERSION == 4:
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        elif Gtk.MAJOR_VERSION == 3:
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        settings = Gtk.Settings.get_default()
        settings.props.gtk_enable_animations = False

        # We need to add at least a window for the app not to exit!
        self.add_window(Gtk.Window())

    def do_activate(self):
        utils.write_command('started')
