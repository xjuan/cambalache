#
# CmbColumnView
#
# Copyright (C) 2024  Juan Pablo Ugarte
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

from gi.repository import GObject, Gdk, Gtk
from .cmb_ui import CmbUI
from .cmb_object import CmbObject
from .cmb_context_menu import CmbContextMenu
from .cmb_project import CmbProject
from cambalache import _


class CmbColumnView(Gtk.ColumnView):
    __gtype_name__ = "CmbColumnView"

    def __init__(self, **kwargs):
        self.__project = None
        self.__tree_model = None
        self.__in_selection_change = False
        self.single_selection = Gtk.SingleSelection()

        super().__init__(**kwargs)

        self.props.has_tooltip = True
        self.props.hexpand = True
        self.props.show_row_separators = False
        self.props.show_column_separators = False
        self.props.reorderable = False

        self.__add_column("display-name")
        self.single_selection.connect("notify::selected-item", self.__on_selected_item_notify)
        self.set_model(self.single_selection)

        gesture = Gtk.GestureClick(button=Gdk.BUTTON_SECONDARY)
        gesture.connect("pressed", self.__on_button_press)
        self.add_controller(gesture)

        self.connect("activate", self.__on_activate)

    def __add_column(self, property_id):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind, property_id)
        factory.connect("unbind", self._on_factory_unbind)

        column = Gtk.ColumnViewColumn(factory=factory, expand=True)
        self.append_column(column)

        # FIXME: Add api to Gtk to hide column title widget
        column_view = column.get_column_view()
        child = column_view.get_first_child()
        if GObject.type_name(child.__gtype__) == "GtkColumnViewRowWidget":
            child.set_visible(False)

    def __on_button_press(self, gesture, npress, x, y):
        expander = self.__get_tree_expander(x, y)

        if expander is None or npress != 1:
            return False

        # Select row at x,y
        list_row = expander.get_list_row()
        self.single_selection.set_selected(list_row.get_position())

        menu = CmbContextMenu()

        if self.__project:
            menu.target_tk = self.__project.target_tk

        menu.set_parent(self)
        menu.popup_at(x, y)
        return True

    def __get_object_ancestors(self, obj):
        if isinstance(obj, CmbObject):
            ancestors = {obj.ui}
            parent = obj.parent
            while parent:
                ancestors.add(parent)
                parent = parent.parent

            return ancestors

        # CmbUI and CmbCSS do not have ancestors
        return {}

    def __object_ancestor_expand(self, obj):
        ancestors = self.__get_object_ancestors(obj)
        i = 0

        # Iterate over tree model
        # NOTE: only visible/expanded rows are returned
        list_row = self.__tree_model.get_row(i)
        while list_row:
            item = list_row.get_item()

            # Return position if we reached the object row
            if item == obj:
                return i
            elif item in ancestors:
                # Expand row if its part of the hierarchy
                list_row.set_expanded(True)

            i += 1
            list_row = self.__tree_model.get_row(i)

        return None

    def __on_project_selection_changed(self, p):
        list_row = self.single_selection.get_selected_item()
        current_selection = [list_row.get_item()] if list_row else []
        selection = self.__project.get_selection()

        if selection == current_selection:
            return

        self.__in_selection_change = True

        if len(selection) > 0:
            position = self.__object_ancestor_expand(selection[0])
            if position is not None:
                self.single_selection.select_item(position, True)
            else:
                self.single_selection.unselect_all()
        else:
            self.single_selection.unselect_all()

        self.__in_selection_change = False

    @GObject.Property(type=CmbProject)
    def project(self):
        return self.__project

    @project.setter
    def _set_project(self, project):
        if self.__project:
            self.__project.disconnect_by_func(self.__on_project_selection_changed)

        self.__project = project

        if project:
            self.__tree_model = Gtk.TreeListModel.new(
                project,
                False,
                False,
                self.__tree_model_create_func,
                None
            )
            self.single_selection.props.model = self.__tree_model
            self.__project.connect("selection-changed", self.__on_project_selection_changed)
        else:
            self.single_selection.props.model = None

    def __tree_model_create_func(self, item, data):
        if isinstance(item, CmbObject):
            return item
        elif isinstance(item, CmbUI):
            return item

        return None

    def __on_selected_item_notify(self, single_selection, pspec):
        if self.__in_selection_change or self.__project is None:
            return

        list_item = single_selection.get_selected_item()

        if list_item:
            item = list_item.get_item()
            self.__project.set_selection([item])
        else:
            self.__project.set_selection([])

    def __on_item_notify(self, item, pspec, label):
        self.__update_label(item, label, pspec.name)

    def __update_label(self, item, label, property_id):
        val = str(item.get_property(property_id))
        label.set_markup(val if val else "")

    def _on_factory_setup(self, factory, list_item):
        expander = Gtk.TreeExpander()
        label = Gtk.Inscription(hexpand=True)
        expander.set_child(label)
        list_item.set_child(expander)

    def __on_list_store_n_items_notify(self, list_store, pspec, expander):
        expander.props.hide_expander = list_store.props.n_items == 0

    def __drop_target_new(self):
        drop_target = Gtk.DropTarget.new(
            type=GObject.TYPE_NONE, actions=Gdk.DragAction.COPY
        )
        drop_target.set_gtypes([CmbObject, CmbUI])

        return drop_target

    def _on_factory_bind(self, factory, list_item, property_id):
        row = list_item.get_item()
        expander = list_item.get_child()
        row_widget = expander.props.parent.props.parent
        expander.set_list_row(row)
        item = row.get_item()
        label = expander.get_child()

        # ensure drag&drop variables
        row_widget._drop_target = None
        row_widget._drag_source = None
        expander._drop_target = None

        # Handle label
        self.__update_label(item, label, property_id)
        item.connect(f"notify::{property_id}", self.__on_item_notify, label)

        # Add controllers and drag sources
        if isinstance(item, CmbObject):
            # Drag source, only objects can be dragged
            drag_source = Gtk.DragSource()
            drag_source.connect("prepare", self.__on_drag_prepare)
            drag_source.connect("drag-begin", self.__on_drag_begin)
            row_widget.add_controller(drag_source)
            row_widget._drag_source = drag_source

            # Expander Drop target
            drop_target = self.__drop_target_new()
            drop_target.connect("accept", self.__on_expander_drop_accept)
            drop_target.connect("drop", self.__on_expander_drop_drop)
            expander.add_controller(drop_target)
            expander._drop_target = drop_target

            # Row Drop target
            drop_target = self.__drop_target_new()
            drop_target.connect("accept", self.__on_row_drop_accept)
            drop_target.connect("motion", self.__on_row_drop_motion)
            drop_target.connect("drop", self.__on_row_drop_drop)
            row_widget.add_controller(drop_target)
            row_widget._drop_target = drop_target
        elif isinstance(item, CmbUI):
            # Expander Drop target
            drop_target = self.__drop_target_new()
            drop_target.connect("accept", self.__on_ui_expander_drop_accept)
            drop_target.connect("drop", self.__on_ui_expander_drop_drop)
            expander.add_controller(drop_target)
            expander._drop_target = drop_target

            # Row Drop target
            drop_target = self.__drop_target_new()
            drop_target.connect("accept", self.__on_ui_row_drop_accept)
            drop_target.connect("drop", self.__on_ui_row_drop_drop)
            row_widget.add_controller(drop_target)
            row_widget.__drop_target = drop_target
        else:
            expander.props.hide_expander = True
            return

        expander.props.hide_expander = item.props.n_items == 0
        item.connect("notify::n-items", self.__on_list_store_n_items_notify, expander)

    def _on_factory_unbind(self, factory, list_item):
        row = list_item.get_item()
        item = row.get_item()
        expander = list_item.get_child()

        item.disconnect_by_func(self.__on_item_notify)

        if isinstance(item, CmbObject) or isinstance(item, CmbUI):
            item.disconnect_by_func(self.__on_list_store_n_items_notify)

        if expander is None:
            return

        # Clear controllers
        if expander._drop_target:
            expander.remove_controller(expander._drop_target)
            expander._drop_target = None

        row_widget = expander.props.parent.props.parent
        if row_widget:
            if row_widget._drop_target:
                row_widget.remove_controller(row_widget._drop_target)
                row_widget._drop_target = None
            if row_widget._drag_source:
                row_widget.remove_controller(row_widget._drag_source)
                row_widget._drag_source = None

    def __get_item_from_target(self, target):
        target_widget = target.get_widget()

        if isinstance(target_widget, Gtk.TreeExpander):
            expander = target_widget
        else:
            cell = target_widget.get_first_child()
            expander = cell.get_first_child()

        list_row = expander.get_list_row()
        item = list_row.get_item()

        return item

    def __on_drag_prepare(self, drag_source, x, y):
        item = self.__get_item_from_target(drag_source)
        return Gdk.ContentProvider.new_for_value(item)

    def __on_drag_begin(self, drag_source, drag):
        expander = drag_source.get_widget().get_first_child().get_first_child()
        drag._item = self.__get_item_from_target(drag_source)
        drag_source.set_icon(Gtk.WidgetPaintable.new(expander.get_first_child()), 0, 0)

    def __get_drop_before(self, widget, x, y):
        return True if y < widget.get_height()/2 else False

    def __ui_drop_accept(self, drop, item):
        origin_item = drop.get_drag()._item

        if origin_item == item:
            return False

        # Ignore if its the same UI and item is already a toplevel
        if origin_item.ui_id == item.ui_id and origin_item.parent_id is None:
            return False

        return True

    def __on_ui_expander_drop_accept(self, target, drop):
        item = self.__get_item_from_target(target)
        return self.__ui_drop_accept(drop, item)

    def __on_ui_row_drop_accept(self, target, drop):
        item = self.__get_item_from_target(target)
        return self.__ui_drop_accept(drop, item)

    def __on_object_drop_accept(self, drop, item):
        origin_item = drop.get_drag()._item

        if origin_item == item:
            return None

        if not isinstance(item, CmbObject):
            return None

        # Ignore if its the same parent
        if origin_item.parent_id == item.object_id:
            return None

        return origin_item

    def __on_expander_drop_accept(self, target, drop):
        item = self.__get_item_from_target(target)
        origin_item = self.__on_object_drop_accept(drop, item)

        if origin_item is None:
            return False

        return self.__project._check_can_add(origin_item.type_id, item.type_id)

    def __on_row_drop_accept(self, target, drop):
        item = self.__get_item_from_target(target)
        origin_item = self.__on_object_drop_accept(drop, item)

        if origin_item is None or item.parent is None:
            return False

        return self.__project._check_can_add(origin_item.type_id, item.parent.type_id)

    def __on_row_drop_motion(self, target, x, y):
        row_widget = target.get_widget()

        drop_before = self.__get_drop_before(row_widget, x, y)

        row_widget.remove_css_class("drop-before")
        row_widget.remove_css_class("drop-after")

        if drop_before:
            row_widget.add_css_class("drop-before")
        else:
            row_widget.add_css_class("drop-after")

        return Gdk.DragAction.COPY

    def __on_drop_drop(self, origin_item, item):
        if not isinstance(item, CmbUI):
            return

        if origin_item.ui_id == item.ui_id:
            self.__project.history_push(_("Move {name} as toplevel").format(name=origin_item.display_name))
            origin_item.parent_id = 0
            self.__project.history_pop()
        else:
            # TODO: Use copy/paste to move across UI files
            pass

    def __on_ui_row_drop_drop(self, target, origin_item, x, y):
        item = self.__get_item_from_target(target)
        self.__on_drop_drop(origin_item, item)

    def __on_ui_expander_drop_drop(self, target, origin_item, x, y):
        item = self.__get_item_from_target(target)
        self.__on_drop_drop(origin_item, item)

    def __on_expander_drop_drop(self, target, origin_item, x, y):
        item = self.__get_item_from_target(target)

        if not isinstance(item, CmbObject):
            return

        # TODO: handle dragging from one UI to another
        if origin_item.ui_id != item.ui_id:
            return

        if origin_item.parent_id != item.object_id:
            self.__project.history_push(
                _("Move {name} to {target}").format(name=origin_item.display_name, target=item.display_name)
            )
            origin_item.parent_id = item.object_id
            self.__project.history_pop()

    def __on_row_drop_drop(self, target, origin_item, x, y):
        row_widget = target.get_widget()
        item = self.__get_item_from_target(target)

        drop_before = self.__get_drop_before(row_widget, x, y)

        if not isinstance(item, CmbObject):
            return

        # TODO: handle dragging from one UI to another
        if origin_item.ui_id != item.ui_id:
            return

        if origin_item.parent_id != item.parent_id:
            if drop_before:
                msg = _("Move {name} before {target}").format(name=origin_item.display_name, target=item.display_name)
            else:
                msg = _("Move {name} after {target}").format(name=origin_item.display_name, target=item.display_name)

            self.__project.history_push(msg)

            origin_item.parent_id = item.parent_id
        else:
            msg = None

        parent = item.parent

        origin_position = origin_item.position
        target_position = item.position

        if origin_position > target_position:
            if drop_before:
                position = item.position
            else:
                position = item.position + 1
        else:
            if drop_before:
                position = item.position - 1
            else:
                position = item.position

        parent.reorder_child(origin_item, position)

        if msg:
            self.__project.history_pop()

        self.__project.set_selection([origin_item])

    def __get_tree_expander(self, x, y):
        pick = self.pick(x, y, Gtk.PickFlags.DEFAULT)

        if pick is None:
            return None

        if isinstance(pick, Gtk.TreeExpander):
            return pick

        child = pick.get_first_child()

        if child and isinstance(child, Gtk.TreeExpander):
            return child

        parent = pick.props.parent
        if parent and isinstance(parent, Gtk.TreeExpander):
            return parent

        return None

    def __on_activate(self, column_view, position):
        item = self.__tree_model.get_item(position)
        item.set_expanded(not item.get_expanded())

    def do_query_tooltip(self, x, y, keyboard_mode, tooltip):
        expander = self.__get_tree_expander(x, y)

        if expander is None:
            return False

        obj = expander.get_item()

        if isinstance(obj, CmbObject):
            msg = obj.version_warning
            if msg:
                tooltip.set_text(msg)
                return True

        return False
