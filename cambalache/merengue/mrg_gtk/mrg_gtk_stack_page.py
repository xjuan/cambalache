# GtkStack Controller
#
# Copyright (C) 2022  Juan Pablo Ugarte
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

from gi.repository import GObject, Gtk

from merengue import MrgController


class MrgGtkStackPage(MrgController):
    object = GObject.Property(type=Gtk.StackPage, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::selected", self.__on_selected_changed)

    def __on_selected_changed(self, obj, pspec):
        if not self.selected or self.object is None:
            return

        child = self.object.props.child
        if child is None:
            return
        stack = child.props.parent

        if stack and stack.props.visible_child != child:
            stack.set_visible_child(child)
