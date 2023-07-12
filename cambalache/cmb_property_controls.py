#
# CmbPropertyControls - Cambalache Property Controls
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
import math

from gi.repository import GLib, GObject, Gdk, Gtk, Pango, GdkPixbuf, GtkSource

from .cmb_object import CmbObject
from .cmb_ui import CmbUI
from .cmb_type_info import CmbTypeInfo
from .cmb_translatable_popover import CmbTranslatablePopover
from .cmb_type_chooser_popover import CmbTypeChooserPopover
from .cmb_property import CmbProperty
from .icon_naming_spec import standard_icon_names, standard_icon_context
from cambalache import _


def unset_scroll_event(widget):
    def ignore_scroll_event(widget, event):
        Gtk.propagate_event(widget.get_parent(), event)
        return True

    events = widget.get_events()
    widget.set_events(events & ~(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK))

    if isinstance(widget, Gtk.ComboBox):
        widget.connect("scroll-event", ignore_scroll_event)


class CmbEntry(Gtk.Entry):
    __gtype_name__ = "CmbEntry"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::text", self.__on_text_notify)

    def make_translatable(self, target):
        self._target = target
        self.props.secondary_icon_name = "document-edit-symbolic"
        self.connect("icon-press", self.__on_icon_pressed)

    def __on_icon_pressed(self, widget, icon_pos, event):
        popover = CmbTranslatablePopover(relative_to=self)
        popover.bind_properties(self._target)
        popover.popup()

    def __on_text_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.text if self.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.text = value if value is not None else ""


class CmbTextBuffer(Gtk.TextBuffer):
    __gtype_name__ = "CmbTextBuffer"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::text", self.__on_text_notify)

    def __on_text_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.text if self.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.text = value if value is not None else ""


class CmbTextView(Gtk.ScrolledWindow):
    __gtype_name__ = "CmbTextView"

    cmb_value = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.props.shadow_type = Gtk.ShadowType.IN
        self.props.height_request = 64
        self.buffer = CmbTextBuffer()
        self.view = Gtk.TextView(visible=True, buffer=self.buffer)

        GObject.Object.bind_property(
            self,
            "cmb-value",
            self.buffer,
            "cmb-value",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
        )

        self.add(self.view)


class CmbSpinButton(Gtk.SpinButton):
    __gtype_name__ = "CmbSpinButton"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::value", self.__on_text_notify)
        self.props.halign = Gtk.Align.START
        self.props.numeric = True
        self.props.width_chars = 8

        unset_scroll_event(self)

    def __on_text_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        # FIXME: value should always use C locale
        if self.props.digits == 0:
            return str(int(self.props.value))
        else:
            # NOTE: round() to avoid setting numbers like 0.7000000000000001
            return str(round(self.props.value, 15))

    @cmb_value.setter
    def _set_cmb_value(self, value):
        value = float(value)

        if value == math.inf:
            self.props.value = GLib.MAXDOUBLE
        elif value == -math.inf:
            self.props.value = -GLib.MAXDOUBLE
        else:
            self.props.value = value


class CmbSwitch(Gtk.Switch):
    __gtype_name__ = "CmbSwitch"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::active", self.__on_notify)
        self.props.halign = Gtk.Align.START

    def __on_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return "True" if self.props.active else "False"

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if value is not None:
            val = value.lower()

            if type(val) == str:
                if val.lower() in {"1", "t", "y", "true", "yes"}:
                    self.props.active = True
                else:
                    self.props.active = False
            else:
                self.props.active = bool(value)
        else:
            self.props.active = False


class CmbEnumComboBox(Gtk.ComboBox):
    __gtype_name__ = "CmbEnumComboBox"

    info = GObject.Property(type=CmbTypeInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    text_column = GObject.Property(type=int, default=1, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("changed", self.__on_changed)

        renderer_text = Gtk.CellRendererText()
        self.pack_start(renderer_text, True)
        self.add_attribute(renderer_text, "text", self.text_column)

        self.props.id_column = self.text_column
        self.props.model = self.info.enum

        unset_scroll_event(self)

    def __on_changed(self, obj):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.active_id

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.active_id = None

        for row in self.info.enum:
            enum_name = row[0]
            enum_nick = row[1]

            # Always use nick as value
            if value == enum_name or value == enum_nick:
                self.props.active_id = enum_nick


class CmbFlagsEntry(Gtk.Entry):
    __gtype_name__ = "CmbFlagsEntry"

    info = GObject.Property(type=CmbTypeInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    id_column = GObject.Property(type=int, default=1, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    text_column = GObject.Property(type=int, default=1, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    value_column = GObject.Property(type=int, default=2, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        self.flags = {}
        self._checks = {}

        super().__init__(**kwargs)

        self.props.editable = False
        self.props.secondary_icon_name = "document-edit-symbolic"

        self.connect("icon-release", self.__on_icon_release)

        self.__init_popover()

    def __init_popover(self):
        self._popover = Gtk.Popover(relative_to=self)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(Gtk.Label(label=f"<b>{self.info.type_id}</b>", use_markup=True), False, True, 4)
        box.pack_start(Gtk.Separator(), False, False, 0)
        sw = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, propagate_natural_height=True, max_content_height=360)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sw.add(vbox)
        box.pack_start(sw, True, True, 0)

        for row in self.info.flags:
            flag = row[self.text_column]
            flag_id = row[self.id_column]

            check = Gtk.CheckButton(label=flag)
            check.connect("toggled", self.__on_check_toggled, flag_id)
            vbox.pack_start(check, False, True, 4)
            self._checks[flag_id] = check

        box.show_all()
        self._popover.add(box)

    def __on_check_toggled(self, check, flag_id):
        self.flags[flag_id] = check.props.active
        self.props.text = self.__to_string()
        self.notify("cmb-value")

    def __on_icon_release(self, obj, pos, event):
        self._popover.popup()

    def __to_string(self):
        retval = None
        for row in self.info.flags:
            flag_id = row[self.id_column]
            if self.flags.get(flag_id, False):
                retval = flag_id if retval is None else f"{retval} | {flag_id}"

        return retval if retval is not None else ""

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.text if self.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.text = value if value is not None else ""

        self.flags = {}
        for check in self._checks:
            self._checks[check].props.active = False

        if value:
            tokens = [t.strip() for t in value.split("|")]

            for row in self.info.flags:
                flag_id = row[self.id_column]
                flag_name = row[0]
                flag_nick = row[1]

                check = self._checks.get(flag_id, None)
                if check:
                    val = flag_name in tokens or flag_nick in tokens
                    check.props.active = val
                    self.flags[flag_id] = val


class CmbFileEntry(Gtk.Entry):
    __gtype_name__ = "CmbFileEntry"

    dirname = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.title = (_("Select File"),)
        self.filter = None
        self.props.placeholder_text = "<GFile>"
        self.props.secondary_icon_name = "document-open-symbolic"

        self.connect("notify::text", self.__on_text_notify)
        self.connect("icon-press", self.__on_icon_pressed)

    def __on_icon_pressed(self, widget, icon_pos, event):
        # Create Open Dialog
        dialog = Gtk.FileChooserDialog(
            title=self.title, parent=self.get_toplevel(), action=Gtk.FileChooserAction.OPEN, filter=self.filter
        )
        dialog.add_buttons(_("_Cancel"), Gtk.ResponseType.CANCEL, _("_Open"), Gtk.ResponseType.OK)

        if self.dirname is not None:
            dialog.set_current_folder(self.dirname)

        if dialog.run() == Gtk.ResponseType.OK:
            self.props.text = os.path.relpath(dialog.get_filename(), start=self.dirname)

        dialog.destroy()

    def __on_text_notify(self, obj, pspec):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.text if self.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.text = value if value is not None else ""


class CmbPixbufEntry(CmbFileEntry):
    __gtype_name__ = "CmbPixbufEntry"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.title = (_("Select Image"),)
        self.props.placeholder_text = "<GdkPixbuf>"

        # Only show images formats supported by GdkPixbuf
        self.filter = Gtk.FileFilter()
        self.filter.add_pixbuf_formats()


class CmbObjectChooser(Gtk.Entry):
    __gtype_name__ = "CmbObjectChooser"

    parent = GObject.Property(type=CmbObject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    prop = GObject.Property(type=CmbProperty, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        self._value = None
        super().__init__(**kwargs)
        self.connect("notify::text", self.__on_text_notify)

        if self.prop is None:
            self.props.placeholder_text = "<GObject>"
            return

        self.__is_inline_object = self.prop.project.target_tk == "gtk-4.0" and not self.prop.info.disable_inline_object

        if self.__is_inline_object:
            self.connect("icon-press", self.__on_icon_pressed)
            self.parent.connect("property-changed", lambda o, p: self.__update_icons())
            self.__update_icons()
        else:
            self.props.placeholder_text = f"<{self.prop.info.type_id}>"

    def __on_text_notify(self, obj, pspec):
        if self.prop and self.prop.inline_object_id:
            return

        obj = self.parent.project.get_object_by_name(self.parent.ui_id, self.props.text)
        self._value = obj.object_id if obj else None

        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self._value

    @cmb_value.setter
    def _set_cmb_value(self, value):
        parent = self.parent

        self._value = int(value) if value else None

        if self._value:
            obj = parent.project.get_object_by_id(parent.ui_id, self._value)
            self.props.text = obj.name if obj else ""
        else:
            self.props.text = ""

    def __update_icons(self):
        if not self.__is_inline_object:
            return

        if self.prop.inline_object_id:
            obj = self.parent.project.get_object_by_id(self.parent.ui_id, self.prop.inline_object_id)
            type = obj.type_id
            self.props.secondary_icon_name = "edit-clear-symbolic"
            self.props.secondary_icon_tooltip_text = _("Clear property")
            self.props.placeholder_text = f"<inline {type}>"
            self.props.editable = False
            self.props.can_focus = False
        else:
            self.props.secondary_icon_name = "list-add-symbolic"
            self.props.secondary_icon_tooltip_text = _("Add inline object")
            self.props.placeholder_text = f"<{self.prop.info.type_id}>"
            self.props.editable = True
            self.props.can_focus = True

    def __get_name_for_object(self, obj):
        name = obj.name
        return obj.type_id.lower() if name is None else name

    def __on_type_selected(self, popover, info):
        parent = self.parent
        parent.project.add_object(parent.ui_id, info.type_id, parent_id=parent.object_id, inline_property=self.prop.property_id)
        self.__update_icons()

    def __on_icon_pressed(self, widget, icon_pos, event):
        parent = self.parent
        project = parent.project
        prop = self.prop

        if self.prop.inline_object_id:
            obj = project.get_object_by_id(self.parent.ui_id, prop.inline_object_id)
            project.remove_object(obj)
            self.__update_icons()
        else:
            chooser = CmbTypeChooserPopover(relative_to=self, parent_type_id=parent.type_id, derived_type_id=prop.info.type_id)
            chooser.project = project
            chooser.connect("type-selected", self.__on_type_selected)
            chooser.popup()


class CmbToplevelChooser(Gtk.ComboBox):
    __gtype_name__ = "CmbToplevelChooser"

    object = GObject.Property(type=CmbUI, flags=GObject.ParamFlags.READWRITE)
    derivable_only = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.filter = None

        super().__init__(**kwargs)
        self.connect("notify::object", self.__on_object_notify)
        self.connect("changed", self.__on_changed)

        renderer = Gtk.CellRendererText()
        self.pack_start(renderer, True)
        self.set_cell_data_func(renderer, self.__name_cell_data_func, None)

    def __name_cell_data_func(self, column, cell, model, iter_, data):
        obj = model.get_value(iter_, 0)

        if type(obj) != CmbObject:
            return

        name = f"{obj.name} " if obj.name else ""
        extra = _("(template)") if not obj.parent_id and obj.ui.template_id == obj.object_id else obj.type_id
        cell.set_property("markup", f"{name}<i>{extra}</i>")

    def __filter_func(self, model, iter, data):
        obj = model[iter][0]

        if self.object.ui_id != obj.ui_id:
            return False

        if type(obj) == CmbObject:
            if self.derivable_only:
                return obj.info.derivable and obj.parent_id == 0
            else:
                return obj.parent_id == 0

        return False

    def __on_object_notify(self, obj, pspec):
        self.props.model = None
        self.filter = None

        if self.object is None:
            return

        project = self.object.project
        iter = project.get_iter_from_object(self.object)
        path = project.get_path(iter)

        # Create filter and set visible function before using it
        self.filter = project.filter_new(path)
        self.filter.set_visible_func(self.__filter_func)

        # Use filter as model
        self.props.model = self.filter

    def __on_changed(self, combo):
        self.notify("cmb-value")

    @GObject.Property(type=int)
    def cmb_value(self):
        if self.filter is None:
            return 0

        iter = self.get_active_iter()
        if iter is None:
            return 0

        row = self.filter[iter]
        return row[0].object_id if row else 0

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if self.object is None:
            return

        iter = self.object.project.get_iter_from_object_id(self.object.ui_id, value)
        valid, filter_iter = self.filter.convert_child_iter_to_iter(iter)
        self.set_active_iter(filter_iter if valid else None)


class CmbChildTypeComboBox(Gtk.ComboBox):
    __gtype_name__ = "CmbChildTypeComboBox"

    object = GObject.Property(type=GObject.Object, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        unset_scroll_event(self)

        self.connect("changed", self.__on_changed)

        # Model, store it in a Python variable to make sure we hold a reference
        # First column is the ID and the second is if you can select the child or not
        self.__model = Gtk.ListStore(str, bool)
        self.props.model = self.__model
        self.props.id_column = 0

        # Simple cell renderer
        renderer_text = Gtk.CellRendererText()
        self.pack_start(renderer_text, True)
        self.add_attribute(renderer_text, "text", 0)
        self.add_attribute(renderer_text, "sensitive", 1)

        self.__populate_model()

    def __populate_model(self):
        self.__model.clear()

        parent = self.object.parent
        if parent is None:
            return

        self.__model.append([None, True])

        pinfo = parent.info
        while pinfo:
            if pinfo.child_types:
                for t in pinfo.child_types:
                    self.__model.append([t, True])
            pinfo = pinfo.parent

    def __on_changed(self, obj):
        self.notify("cmb-value")

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.props.active_id

    @cmb_value.setter
    def _set_cmb_value(self, value):
        self.props.active_id = value


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


class CmbColorEntry(Gtk.Box):
    __gtype_name__ = "CmbColorEntry"

    use_color = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.__ignore_notify = False

        super().__init__(**kwargs)

        self.entry = Gtk.Entry(visible=True, width_chars=14, editable=False)
        self.button = Gtk.ColorButton(visible=True, use_alpha=True)

        self.__default_color = self.button.props.color
        self.__default_rgba = self.button.props.rgba

        self.pack_start(self.entry, False, True, 0)
        self.pack_start(self.button, False, True, 4)

        self.button.connect("color-set", self.__on_color_set)
        self.entry.connect("icon-press", self.__on_entry_icon_pressed)

    def __on_entry_icon_pressed(self, widget, icon_pos, event):
        self.cmb_value = None

    def __on_color_set(self, obj):
        if self.use_color:
            self.cmb_value = self.button.props.color.to_string() if self.button.props.color else None
        else:
            self.cmb_value = self.button.props.rgba.to_string() if self.button.props.rgba else None

    @GObject.Property(type=str)
    def cmb_value(self):
        return self.entry.props.text if self.entry.props.text != "" else None

    @cmb_value.setter
    def _set_cmb_value(self, value):
        if value:
            self.entry.props.text = value
            self.entry.props.secondary_icon_name = "edit-clear-symbolic"
        else:
            self.entry.props.text = ""
            self.entry.props.secondary_icon_name = None

        valid = False

        if self.use_color:
            color = None
            if value:
                valid, color = Gdk.Color.parse(value)

            self.button.set_color(color if valid else self.__default_color)
        else:
            rgba = Gdk.RGBA()

            if value:
                valid = rgba.parse(value)

            self.button.set_rgba(rgba if valid else self.__default_rgba)


class CmbSourceView(GtkSource.View):
    __gtype_name__ = "CmbSourceView"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.manager = GtkSource.LanguageManager.get_default()

        self.buffer = GtkSource.Buffer()
        self.props.buffer = self.buffer
        self.buffer.connect("changed", self.__on_buffer_changed)

    @GObject.Property(type=str)
    def lang(self):
        return self.buffer.get_language()

    @lang.setter
    def _set_lang(self, value):
        lang = self.manager.get_language(value)
        self.buffer.set_language(lang)

    @GObject.Property(type=str)
    def text(self):
        return self.buffer.props.text

    @text.setter
    def _set_text(self, value):
        self.buffer.set_text(value if value else "")

    def __on_buffer_changed(self, buffer):
        self.notify("text")


# Functions
def cmb_create_editor(project, type_id, prop=None, data=None):
    def get_min_max_for_type(type_id):
        if type_id == "gchar":
            return (GLib.MININT8, GLib.MAXINT8)
        elif type_id == "guchar":
            return (0, GLib.MAXUINT8)
        elif type_id == "gint":
            return (GLib.MININT, GLib.MAXINT)
        elif type_id == "guint":
            return (0, GLib.MAXUINT)
        elif type_id == "glong":
            return (GLib.MINLONG, GLib.MAXLONG)
        elif type_id == "gulong":
            return (0, GLib.MAXULONG)
        elif type_id == "gint64":
            return (GLib.MININT64, GLib.MAXINT64)
        elif type_id == "guint64":
            return (0, GLib.MAXUINT64)
        elif type_id == "gfloat":
            return (-GLib.MAXFLOAT, GLib.MAXFLOAT)
        elif type_id == "gdouble":
            return (-GLib.MAXDOUBLE, GLib.MAXDOUBLE)

    def get_dirname():
        if project.filename:
            return os.path.dirname(project.filename)
        else:
            return os.getcwd()

    editor = None
    info = project.type_info.get(type_id, None)

    if prop:
        translatable = prop.info.translatable
    elif data:
        translatable = data.info.translatable
    else:
        translatable = False

    if type_id == "gboolean":
        editor = CmbSwitch()
    if type_id == "gunichar":
        editor = CmbEntry(hexpand=True, max_length=1, placeholder_text=f"<{type_id}>")
    elif (
        type_id == "gchar"
        or type_id == "guchar"
        or type_id == "gint"
        or type_id == "guint"
        or type_id == "glong"
        or type_id == "gulong"
        or type_id == "gint64"
        or type_id == "guint64"
        or type_id == "gfloat"
        or type_id == "gdouble"
    ):
        digits = 0
        step_increment = 1
        minimum, maximum = get_min_max_for_type(type_id)

        pinfo = prop.info if prop else None

        # FIXME: is there a better way to handle inf -inf values other
        # than casting to str?
        if pinfo and pinfo.minimum is not None:
            value = float(minimum)
            minimum = value if value != -math.inf else -GLib.MAXDOUBLE
        if pinfo and pinfo.maximum is not None:
            value = float(maximum)
            maximum = value if value != math.inf else GLib.MAXDOUBLE

        if type_id == "gfloat" or type_id == "gdouble":
            digits = 4
            step_increment = 0.1

        adjustment = Gtk.Adjustment(lower=minimum, upper=maximum, step_increment=step_increment, page_increment=10)

        editor = CmbSpinButton(digits=digits, adjustment=adjustment)
    elif type_id == "GStrv":
        editor = CmbTextView(hexpand=True)
    elif type_id == "GdkRGBA":
        editor = CmbColorEntry()
    elif type_id == "GdkColor":
        editor = CmbColorEntry(use_color=True)
    elif type_id == "GdkPixbuf":
        editor = CmbPixbufEntry(hexpand=True, dirname=get_dirname())
    elif type_id == "GFile":
        editor = CmbFileEntry(hexpand=True, dirname=get_dirname())
    elif type_id == "CmbIconName":
        editor = CmbIconNameEntry(hexpand=True, placeholder_text="<Icon Name>")
    elif type_id in ["GtkShortcutTrigger", "GtkShortcutAction"]:
        editor = CmbEntry(hexpand=True, placeholder_text=f"<{type_id}>")
    elif info:
        if info.is_object or info.parent_id == "interface":
            # TODO: replace prop with project and is_inline
            editor = CmbObjectChooser(parent=prop.object, prop=prop)
        if info.parent_id == "enum":
            editor = CmbEnumComboBox(info=info)
        elif info.parent_id == "flags":
            editor = CmbFlagsEntry(info=info)

    if editor is None:
        editor = CmbEntry(hexpand=True, placeholder_text=f"<{type_id}>")
        if translatable:
            target = prop if prop else data
            if target:
                editor.make_translatable(target=target)

    editor.show()

    return editor
