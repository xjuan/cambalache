#
# CmbUIEditor - Cambalache UI Editor
#
# Copyright (C) 2025  Juan Pablo Ugarte
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

from gi.repository import GObject, Gtk

from .cmb_object import CmbObject


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_object_editor.ui")
class CmbObjectEditor(Gtk.Box):
    __gtype_name__ = "CmbObjectEditor"

    switcher = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    property_editor = Gtk.Template.Child()
    layout_editor = Gtk.Template.Child()
    signal_editor = Gtk.Template.Child()
    fragment_editor = Gtk.Template.Child()
    accessible_editor = Gtk.Template.Child()

    layout_page = Gtk.Template.Child()
    signals_page = Gtk.Template.Child()
    fragment_page = Gtk.Template.Child()
    accessible_page = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self._object = None

        super().__init__(**kwargs)

    @GObject.Property(type=CmbObject)
    def object(self):
        return self._object

    @object.setter
    def _set_object(self, obj):
        self._object = obj

        is_not_builtin = not obj.info.is_builtin if obj else True
        self.property_editor.object = obj

        for editor, page in [
            (self.layout_editor, self.layout_page),
            (self.signal_editor, self.signals_page),
            (self.accessible_editor, self.accessible_page),
            (self.fragment_editor, self.fragment_page),
        ]:
            editor.object = obj
            page.props.visible = is_not_builtin


Gtk.WidgetClass.set_css_name(CmbObjectEditor, "CmbObjectEditor")
