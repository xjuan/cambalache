#
# CmbIconNameEntry
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

from cambalache import _
from gi.repository import GLib, Gio, GdkPixbuf, GObject, Gdk, Gtk, Pango
from .cmb_entry import CmbEntry
from .icon_naming_spec import standard_icon_context, standard_icon_names


class CmbIconNameEntry(CmbEntry):
    __gtype_name__ = "CmbIconNameEntry"

    object = GObject.Property(type=GObject.Object, flags=GObject.ParamFlags.READWRITE)

    standard_only = GObject.Property(type=bool, default=True, flags=GObject.ParamFlags.READWRITE)
    symbolic_only = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    COL_ICON_NAME = 0
    COL_MARKUP = 1
    COL_CONTEXT = 2
    COL_STANDARD = 3
    COL_SYMBOLIC = 4
    COL_STANDARD_SYMBOLIC = 5
    COL_PIXBUF = 6

    # Model, store it in a Python class variable to share between all instances
    icon_model = None

    iconlist = []

    def __init__(self, **kwargs):
        self._filters = {}

        super().__init__(**kwargs)

        GObject.Object.bind_property(self, "cmb-value", self, "primary-icon-name", GObject.BindingFlags.SYNC_CREATE)

        self.props.secondary_icon_name = "document-edit-symbolic"
        self.connect("icon-press", self.__on_icon_pressed)

        CmbIconNameEntry.ensure_icon_model()

        # Completion
        self.__completion = Gtk.EntryCompletion()
        self.__completion.props.model = self.icon_model
        self.__completion.props.text_column = self.COL_ICON_NAME
        self.__completion.props.inline_completion = True
        self.__completion.props.inline_selection = True
        self.__completion.props.popup_set_width = True
        self.props.completion = self.__completion

        self.__completion.set_match_func(lambda o, key, iter, d: key in self.icon_model[iter][0], None)

        # Icon
        renderer_text = Gtk.CellRendererPixbuf(xpad=4)
        self.__completion.pack_start(renderer_text, False)
        self.__completion.add_attribute(renderer_text, "icon-name", 0)

        # Icon Name
        renderer_text = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        self.__completion.pack_start(renderer_text, False)
        self.__completion.add_attribute(renderer_text, "markup", 1)

    @classmethod
    def ensure_icon_model(cls):
        if cls.icon_model:
            return

        # icon-name markup context standard symbolic standard_symbolic pixbuf
        cls.icon_model = Gtk.ListStore(str, str, str, bool, bool, bool, GdkPixbuf.Pixbuf)

        iconlist = []

        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

        # FIXME: get the context/category of each icon
        for icon in theme.get_icon_names():
            iconlist.append((icon, "cmb_all", icon in standard_icon_names))

        for icon, context, standard in sorted(iconlist, key=lambda i: i[0].lower()):
            if icon.endswith(".symbolic"):
                continue

            icon_paintable = theme.lookup_icon(icon, None, 32, 1, Gtk.TextDirection.NONE, Gtk.IconLookupFlags.PRELOAD)
            symbolic = icon_paintable.is_symbolic()

            icon_file = icon_paintable.get_file()
            if icon_file is None:
                continue

            icon_path = icon_file.get_path()
            if icon_path is None or not os.path.exists(icon_path):
                continue

            standard_symbolic = symbolic and icon.removesuffix("-symbolic") in standard_icon_names

            try:
                iter = cls.icon_model.append(
                    [icon, icon if standard else f"<i>{icon}</i>", context, standard, symbolic, standard_symbolic, None]
                )
                cls.iconlist.append((icon_file, iter))
            except Exception as e:
                print(e)

        # Kickoff async loading
        file, iter = cls.iconlist.pop()
        file.read_async(GLib.PRIORITY_DEFAULT, None, cls.__load_file_finish, iter)

    @classmethod
    def __load_file_finish(cls, obj, res, iter):
        stream = obj.read_finish(res)
        GdkPixbuf.Pixbuf.new_from_stream_at_scale_async(stream, 32, 32, True, None, cls.__load_icon_finish, iter)

    @classmethod
    def __load_icon_finish(cls, obj, res, iter):
        try:
            cls.icon_model[iter][cls.COL_PIXBUF] = GdkPixbuf.Pixbuf.new_from_stream_finish(res)
        except Exception as e:
            print(e)

        if len(cls.iconlist):
            file, iter = cls.iconlist.pop()
            file.read_async(GLib.PRIORITY_DEFAULT, None, cls.__load_file_finish, iter)

    def __model_filter_func(self, model, iter, data):
        if self.standard_only and self.symbolic_only:
            if not model[iter][self.COL_STANDARD_SYMBOLIC]:
                return False
        elif self.standard_only and not model[iter][self.COL_STANDARD]:
            return False
        elif self.symbolic_only and not model[iter][self.COL_SYMBOLIC]:
            return False

        if data == "cmb_all":
            return True

        return model[iter][self.COL_CONTEXT] == data

    def __on_check_active_notify(self, button, pspec):
        for filter in self._filters:
            self._filters[filter].refilter()

    def __on_view_selection_changed(self, view):
        selection = view.get_selected_items()

        if selection:
            model = view.props.model
            iter = model.get_iter(selection[0])
            self.cmb_value = model[iter][self.COL_ICON_NAME]
        else:
            self.cmb_value = None

    def __on_icon_pressed(self, widget, icon_pos):
        # Create popover with icon chooser
        popover = Gtk.Popover()
        popover.set_parent(self)

        hbox = Gtk.Box(visible=True)
        vbox = Gtk.Box(visible=True, orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        stack = Gtk.Stack(visible=True, transition_type=Gtk.StackTransitionType.CROSSFADE)
        sidebar = Gtk.StackSidebar(visible=True, stack=stack, vexpand=True)
        vbox.append(sidebar)
        hbox.append(vbox)
        hbox.append(stack)

        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

        # sorted_contexts = sorted(theme.list_contexts())
        sorted_contexts = []
        sorted_contexts.insert(0, "cmb_all")

        # Add one icon view per context
        for context in sorted_contexts:
            filter = self._filters.get(context, None)

            if filter is None:
                self._filters[context] = Gtk.TreeModelFilter(child_model=self.icon_model)
                filter = self._filters[context]
                filter.set_visible_func(self.__model_filter_func, data=context)
                filter.refilter()

            sw = Gtk.ScrolledWindow(visible=True, min_content_width=600, min_content_height=480)
            view = Gtk.IconView(visible=True, model=filter, pixbuf_column=self.COL_PIXBUF, text_column=self.COL_ICON_NAME)
            view.connect("selection-changed", self.__on_view_selection_changed)
            sw.set_child(view)
            stack.add_titled(sw, context, standard_icon_context.get(context, context))

        # Add filters
        for prop, label in [("standard_only", _("Only standard")), ("symbolic_only", _("Only symbolic"))]:
            check = Gtk.CheckButton(visible=True, label=label)
            GObject.Object.bind_property(
                self, prop, check, "active", GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL
            )
            check.connect_after("notify::active", self.__on_check_active_notify)
            vbox.append(check)

        popover.add_css_class("cmb-icon-chooser")
        popover.set_child(hbox)
        popover.popup()
