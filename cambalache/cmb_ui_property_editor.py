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

import os

from gi.repository import GObject, Gtk

from cambalache import _
from .cmb_ui import CmbUI


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_ui_property_editor.ui")
class CmbUIPropertyEditor(Gtk.Grid):
    __gtype_name__ = "CmbUIPropertyEditor"

    filename = Gtk.Template.Child()
    format = Gtk.Template.Child()
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

        # Set some default name
        self.filename.unnamed_filename = _("unnamed.ui")
        if not obj.filename and obj.template_id:
            template = obj.project.get_object_by_id(obj.ui_id, obj.template_id)
            if template:
                self.filename.unnamed_filename = f"{template.name}.ui".lower()

        for field in self.fields:
            binding = obj.bind_property(
                field,
                getattr(self, field),
                "cmb-value",
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
            )
            self._bindings.append(binding)

        if obj.project.target_tk == "gtk-4.0":
            self.filename.mime_types = "application/x-gtk-builder;text/x-blueprint"

            # filename -> format
            binding = obj.bind_property(
                "filename",
                self.format,
                "selected",
                GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.BIDIRECTIONAL,
                transform_to=self.__filename_to_format,
                transform_from=self.__format_to_filename,
                user_data=obj
            )
            self._bindings.append(binding)

            self.format.show()
            self.format.set_sensitive(bool(obj.filename))
        else:
            self.filename.mime_types = "application/x-gtk-builder;application/x-glade"
            self.format.hide()

    def __filename_to_format(self, binding, source_value, ui):
        if not source_value:
            self.format.props.sensitive = False
            return 0
        self.format.props.sensitive = True

        return 1 if source_value.endswith(".blp") else 0

    def __format_to_filename(self, binding, target_value, ui):
        if not ui.filename:
            self.format.props.sensitive = False
            return None
        self.format.props.sensitive = True

        return os.path.splitext(ui.filename)[0] + (".blp" if target_value == 1 else ".ui")


Gtk.WidgetClass.set_css_name(CmbUIPropertyEditor, "CmbUIPropertyEditor")
