#
# CmbGResourceEditor - Cambalache GResource Editor
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

from gi.repository import GObject, Gtk

from .cmb_gresource import CmbGResource
from cambalache import getLogger

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_gresource_editor.ui")
class CmbGResourceEditor(Gtk.Box):
    __gtype_name__ = "CmbGResourceEditor"

    stack = Gtk.Template.Child()

    gresources_filename = Gtk.Template.Child()
    gresource_prefix = Gtk.Template.Child()
    file_filename = Gtk.Template.Child()
    file_compressed = Gtk.Template.Child()
    file_preprocess = Gtk.Template.Child()
    file_alias = Gtk.Template.Child()

    fields = [
        ("gresources", "gresources_filename", "cmb-value"),
        ("gresource", "gresource_prefix", "cmb-value"),
        ("file", "file_filename", "cmb-value"),
        ("file", "file_compressed", "active"),
        ("file", "file_preprocess", "cmb-value"),
        ("file", "file_alias", "cmb-value"),
    ]

    def __init__(self, **kwargs):
        self._object = None
        self._bindings = []

        super().__init__(**kwargs)

    @GObject.Property(type=CmbGResource)
    def object(self):
        return self._object

    @object.setter
    def _set_object(self, obj):
        if obj == self._object:
            return

        for binding in self._bindings:
            binding.unbind()

        self._bindings = []
        self._object = obj

        if obj is None:
            self.set_sensitive(False)
            for for_type, field, target in self.fields:
                widget = getattr(self, field)
                target_prop = getattr(widget, target)

                if isinstance(target_prop, int):
                    setattr(widget, target, 0)
                else:
                    setattr(widget, target, None)
            return

        resource_type = obj.resource_type
        self.set_sensitive(True)
        self.stack.set_visible_child_name(resource_type)

        for for_type, field, target in self.fields:
            if resource_type != for_type:
                continue

            binding = GObject.Object.bind_property(
                obj,
                field,
                getattr(self, field),
                target,
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            )
            self._bindings.append(binding)

    @Gtk.Template.Callback("on_add_gresource_button_clicked")
    def __on_add_gresource_button_clicked(self, button):
        self._object.project.add_gresource("gresource", parent_id=self._object.gresource_id)

    @Gtk.Template.Callback("on_add_file_button_clicked")
    def __on_add_file_button_clicked(self, button):
        self._object.project.add_gresource("file", parent_id=self._object.gresource_id)


Gtk.WidgetClass.set_css_name(CmbGResourceEditor, "CmbGResourceEditor")
