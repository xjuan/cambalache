#
# CmbPropertyLabel
#
# Copyright (C) 2023-2024  Juan Pablo Ugarte
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

from .cmb_property import CmbProperty
from .cmb_layout_property import CmbLayoutProperty
from .cmb_binding_popover import CmbBindingPopover


class CmbPropertyLabel(Gtk.Button):
    __gtype_name__ = "CmbPropertyLabel"

    prop = GObject.Property(type=CmbProperty, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    layout_prop = GObject.Property(
        type=CmbLayoutProperty, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY
    )
    bindable = GObject.Property(type=bool, default=True, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        if not self.prop and not self.layout_prop:
            raise Exception("CmbPropertyLabel requires prop or layout_prop to be set")
            return

        self.props.focus_on_click = False
        self.label = Gtk.Label(halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        box = Gtk.Box()

        # Update label status
        if self.prop:
            self.bind_icon = Gtk.Image(icon_size=Gtk.IconSize.NORMAL)
            box.append(self.bind_icon)

            # A11y properties are prefixed to avoid clashes, do not show prefix here
            self.label.props.label = self.prop.info.a11y_property_id if self.prop.info.is_a11y else self.prop.property_id

            self.__update_property_label()
            self.prop.connect("notify", self.__on_notify)

            if self.bindable:
                self.connect("clicked", self.__on_bind_button_clicked)
        elif self.layout_prop:
            self.bind_icon = None
            self.label.props.label = self.layout_prop.property_id
            self.__update_layout_property_label()
            self.layout_prop.connect("notify::value", lambda o, p: self.__update_layout_property_label())

        box.append(self.label)
        self.set_child(box)

    def __on_notify(self, prop, pspec):
        if pspec.name in {
            "value",
            "bind-source-id",
            "bind-owner-id",
            "bind-property-id",
            "bind-flags",
            "binding-expression-id",
            "binding-expression-object-id"
        }:
            self.__update_property_label()

    def __update_label(self, prop):
        if prop.value != prop.info.default_value:
            self.add_css_class("modified")
        else:
            self.remove_css_class("modified")

        msg = prop.version_warning
        self.set_tooltip_text(msg)

        if msg:
            self.add_css_class("warning")
        else:
            self.remove_css_class("warning")

    def __update_layout_property_label(self):
        self.__update_label(self.layout_prop)

    def __update_property_label(self):
        self.__update_label(self.prop)

        if not self.bindable:
            return

        if self.prop.bind_property_id or self.prop.binding_expression_id:
            self.bind_icon.props.icon_name = "binded-symbolic"
            self.remove_css_class("hidden")
        else:
            self.bind_icon.props.icon_name = "bind-symbolic"
            self.add_css_class("hidden")

    def __on_bind_button_clicked(self, button):
        popover = CmbBindingPopover(prop=self.prop)
        popover.set_parent(self)

        # Destroy popup on close
        popover.connect("closed", lambda p: p.unparent())
        popover.popup()


Gtk.WidgetClass.set_css_name(CmbPropertyLabel, "CmbPropertyLabel")
