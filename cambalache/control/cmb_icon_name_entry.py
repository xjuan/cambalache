#
# CmbIconNameEntry
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

from cambalache import _
from gi.repository import GdkPixbuf, GObject, Gtk, Pango
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

    def __init__(self, **kwargs):
        self._filters = {}

        super().__init__(**kwargs)

        GObject.Object.bind_property(self, "cmb-value", self, "primary-icon-name", GObject.BindingFlags.SYNC_CREATE)

        self.props.secondary_icon_name = "document-edit-symbolic"
        self.connect("icon-press", self.__on_icon_pressed)

        # Model, store it in a Python variable to make sure we hold a reference
        # icon-name markup context standard symbolic standard_symbolic pixbuf
        self.__model = Gtk.ListStore(str, str, str, bool, bool, bool, GdkPixbuf.Pixbuf)

        # Completion
        self.__completion = Gtk.EntryCompletion()
        self.__completion.props.model = self.__model
        self.__completion.props.text_column = self.COL_ICON_NAME
        self.__completion.props.inline_completion = True
        self.__completion.props.inline_selection = True
        self.__completion.props.popup_set_width = True
        self.props.completion = self.__completion

        self.__completion.set_match_func(lambda o, key, iter, d: key in self.__model[iter][0], None)

        # Icon
        renderer_text = Gtk.CellRendererPixbuf(xpad=4)
        self.__completion.pack_start(renderer_text, False)
        self.__completion.add_attribute(renderer_text, "icon-name", 0)

        # Icon Name
        renderer_text = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END)
        self.__completion.pack_start(renderer_text, False)
        self.__completion.add_attribute(renderer_text, "markup", 1)

        self.__populate_model()

    def __populate_model(self):
        iconlist = []

        self.__model.clear()

        theme = Gtk.IconTheme.get_default()

        for context in theme.list_contexts():
            for icon in theme.list_icons(context):
                iconlist.append((icon, context, icon in standard_icon_names))

        for icon, context, standard in sorted(iconlist, key=lambda i: i[0].lower()):
            if icon.endswith(".symbolic"):
                continue

            info = theme.lookup_icon(icon, 32, Gtk.IconLookupFlags.FORCE_SIZE)
            symbolic = info.is_symbolic()

            if not os.path.exists(info.get_filename()):
                continue

            standard_symbolic = symbolic and icon.removesuffix("-symbolic") in standard_icon_names

            iter = self.__model.append(
                [icon, icon if standard else f"<i>{icon}</i>", context, standard, symbolic, standard_symbolic, None]
            )
            info.load_icon_async(None, self.__load_icon_finish, iter)

    def __load_icon_finish(self, info, res, data):
        self.__model[data][6] = info.load_icon_finish(res)

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

    def __on_icon_pressed(self, widget, icon_pos, event):
        # Create popover with icon chooser
        popover = Gtk.Popover(relative_to=self)
        hbox = Gtk.Box(visible=True)
        vbox = Gtk.Box(visible=True, orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        stack = Gtk.Stack(visible=True, transition_type=Gtk.StackTransitionType.CROSSFADE)
        sidebar = Gtk.StackSidebar(visible=True, stack=stack, vexpand=True)
        vbox.pack_start(sidebar, True, True, 4)
        hbox.pack_start(vbox, False, True, 4)
        hbox.pack_start(stack, True, True, 4)

        theme = Gtk.IconTheme.get_default()

        sorted_contexts = sorted(theme.list_contexts())
        sorted_contexts.insert(0, "cmb_all")

        # Add one icon view per context
        for context in sorted_contexts:
            filter = self._filters.get(context, None)

            if filter is None:
                self._filters[context] = Gtk.TreeModelFilter(child_model=self.__model)
                filter = self._filters[context]
                filter.set_visible_func(self.__model_filter_func, data=context)
                filter.refilter()

            sw = Gtk.ScrolledWindow(visible=True, min_content_width=600, min_content_height=480)
            view = Gtk.IconView(visible=True, model=filter, pixbuf_column=self.COL_PIXBUF, text_column=self.COL_ICON_NAME)
            view.connect("selection-changed", self.__on_view_selection_changed)
            sw.add(view)
            stack.add_titled(sw, context, standard_icon_context.get(context, context))

        # Add filters
        for prop, label in [("standard_only", _("Only standard")), ("symbolic_only", _("Only symbolic"))]:
            check = Gtk.CheckButton(visible=True, label=label)
            GObject.Object.bind_property(
                self, prop, check, "active", GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL
            )
            check.connect_after("notify::active", self.__on_check_active_notify)
            vbox.pack_start(check, False, True, 4)

        popover.get_style_context().add_class("cmb-icon-chooser")
        popover.add(hbox)
        popover.popup()
