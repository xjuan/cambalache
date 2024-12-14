#
# CmbUIEditor - Cambalache UI Editor
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
# SPDX-License-Identifier: LGPL-2.1-only
#

from gi.repository import GObject, Gtk

from .cmb_ui import CmbUI


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_ui_editor.ui")
class CmbUIEditor(Gtk.Grid):
    __gtype_name__ = "CmbUIEditor"

    filename = Gtk.Template.Child()
    template_id = Gtk.Template.Child()
    description = Gtk.Template.Child()
    copyright = Gtk.Template.Child()
    authors = Gtk.Template.Child()
    translation_domain = Gtk.Template.Child()
    comment = Gtk.Template.Child()

    fields = ["filename", "template_id", "description", "copyright", "authors", "translation_domain", "comment"]

    def __init__(self, **kwargs):
        self._object = None
        self._bindings = []

        super().__init__(**kwargs)

    @GObject.Property(type=CmbUI)
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
            for field in self.fields:
                widget = getattr(self, field)

                if type(widget.cmb_value) is int:
                    widget.cmb_value = 0
                else:
                    widget.cmb_value = None
            return

        self.set_sensitive(True)
        self.template_id.object = obj
        self.filename.dirname = obj.project.dirname

        for field in self.fields:
            binding = GObject.Object.bind_property(
                obj,
                field,
                getattr(self, field),
                "cmb-value",
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            )
            self._bindings.append(binding)


Gtk.WidgetClass.set_css_name(CmbUIEditor, "CmbUIEditor")
