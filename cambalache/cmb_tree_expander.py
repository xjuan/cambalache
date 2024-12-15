#
# CmbTreeExpander
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
# SPDX-License-Identifier: LGPL-2.1-only
#

from gi.repository import GObject, Gdk, Gtk, Graphene

from .cmb_ui import CmbUI
from .cmb_object import CmbObject
from .cmb_css import CmbCSS
from .cmb_path import CmbPath
from cambalache import _


class CmbTreeExpander(Gtk.TreeExpander):
    __gtype_name__ = "CmbTreeExpander"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.__project = None
        self.__drop_before = None

        self.label = Gtk.Inscription(hexpand=True)
        self.set_child(self.label)

        self.__parent = None
        self.__drag_source = None
        self.__drop_target = None

    def update_bind(self):
        item = self.props.item

        self.__parent = self.props.parent
        # Drag source
        self.__drag_source = Gtk.DragSource()
        self.__drag_source.connect("prepare", self.__on_drag_prepare)
        self.__drag_source.connect("drag-begin", self.__on_drag_begin)
        self.__parent.add_controller(self.__drag_source)

        # Drop target
        self.__drop_target = Gtk.DropTarget.new(type=GObject.TYPE_NONE, actions=Gdk.DragAction.COPY)
        self.__drop_target.set_gtypes([CmbObject, CmbUI])
        self.__drop_target.connect("accept", self.__on_drop_accept)
        self.__drop_target.connect("motion", self.__on_drop_motion)
        self.__drop_target.connect("drop", self.__on_drop_drop)
        self.__parent.add_controller(self.__drop_target)

        # Handle label
        self.__update_label(item)
        item.connect("notify::display-name", self.__on_item_display_name_notify)

        self.__project = item.project

        if isinstance(item, CmbCSS):
            self.props.hide_expander = True
            return
        elif isinstance(item, CmbPath):
            self.props.hide_expander = False
            self.add_css_class("cmb-path" if item.path else "cmb-unsaved-path")
            return

        self.props.hide_expander = item.props.n_items == 0
        item.connect("notify::n-items", self.__on_item_n_items_notify)

    def clear_bind(self):
        item = self.props.item

        if self.__parent:
            self.__parent.remove_controller(self.__drag_source)
            self.__parent.remove_controller(self.__drop_target)
            self.__parent = None
            self.__drag_source = None
            self.__drop_target = None

        self.remove_css_class("cmb-path")
        self.remove_css_class("cmb-unsaved-path")

        item.disconnect_by_func(self.__on_item_display_name_notify)

        if isinstance(item, CmbCSS) or isinstance(item, CmbPath):
            return

        item.disconnect_by_func(self.__on_item_n_items_notify)

    def __on_item_n_items_notify(self, item, pspec):
        self.props.hide_expander = item.props.n_items == 0

    def __on_item_display_name_notify(self, item, pspec):
        self.__update_label(item)

    def __update_label(self, item):
        self.label.set_markup(item.props.display_name or "")

    # Drop target callbacks
    def __get_drop_before(self, widget, x, y):
        h = widget.get_height()

        if y < h/4:
            return True

        if y > h * 0.8:
            return False

        return None

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

    def __on_drop_accept(self, target, drop):
        item = self.props.item
        origin_item = drop.get_drag()._item

        if isinstance(item, CmbObject):
            origin_item = self.__on_object_drop_accept(drop, item)

            self.__drop_before = None

            if origin_item is None or item.parent is None:
                return False

            return self.__project._check_can_add(origin_item.type_id, item.parent.type_id)
        elif isinstance(item, CmbUI):
            if origin_item == item:
                return False

            # Ignore if its the same UI and item is already a toplevel
            if origin_item.ui_id == item.ui_id and origin_item.parent_id is None:
                return False

            return True

    def __on_drop_motion(self, target, x, y):
        item = self.props.item

        if isinstance(item, CmbObject):
            row_widget = target.get_widget()

            drop_before = self.__get_drop_before(row_widget, x, y)

            if self.__drop_before == drop_before:
                return Gdk.DragAction.COPY

            row_widget.remove_css_class("drop-before")
            row_widget.remove_css_class("drop-after")

            self.__drop_before = drop_before

            if drop_before is not None:
                row_widget.add_css_class("drop-before" if drop_before else "drop-after")

        return Gdk.DragAction.COPY

    def __on_drop_drop(self, target, origin_item, x, y):
        row_widget = target.get_widget()
        item = self.props.item

        if isinstance(item, CmbObject):
            drop_before = self.__get_drop_before(row_widget, x, y)

            if drop_before is None:
                # TODO: handle dragging from one UI to another
                if origin_item.ui_id != item.ui_id:
                    return

                if origin_item.parent_id != item.object_id:
                    self.__project.history_push(
                        _("Move {name} to {target}").format(name=origin_item.display_name, target=item.display_name)
                    )
                    origin_item.parent_id = item.object_id
                    self.__project.history_pop()

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
        elif isinstance(item, CmbUI):
            if origin_item.ui_id == item.ui_id:
                self.__project.history_push(_("Move {name} as toplevel").format(name=origin_item.display_name))
                origin_item.parent_id = 0
                self.__project.history_pop()
            else:
                # TODO: Use copy/paste to move across UI files
                pass

    # Drag Source callbacks
    def __on_drag_prepare(self, drag_source, x, y):
        item = self.props.item

        # Only CmbObject start a drag
        if not isinstance(item, CmbObject):
            return None

        self.__drag_point = Graphene.Point()
        self.__drag_point.x = x
        self.__drag_point.y = y
        return Gdk.ContentProvider.new_for_value(self.props.item)

    def __on_drag_begin(self, drag_source, drag):
        drag._item = self.props.item
        valid, p = self.__parent.compute_point(self.label, self.__drag_point)
        if valid:
            drag_source.set_icon(Gtk.WidgetPaintable.new(self.label), p.x, p.y)
