#
# CmbPropertyChooser
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

from ..cmb_object import CmbObject
from ..cmb_property_info import CmbPropertyInfo


class CmbPropertyChooser(Gtk.ComboBoxText):
    __gtype_name__ = "CmbPropertyChooser"

    object = GObject.Property(type=CmbObject, flags=GObject.ParamFlags.READWRITE)
    target_info = GObject.Property(type=CmbPropertyInfo, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__populate()
        self.connect("notify", self.__on_notify)

    def __on_notify(self, obj, pspec):
        if pspec.name in ["object", "target-info"]:
            self.__populate()

    def __populate(self):
        self.remove_all()

        if self.object is None or self.target_info is None:
            return

        target_info = self.target_info
        target_type = target_info.type_id
        target_type_info = self.object.project.type_info.get(target_type, None)
        target_is_object = target_info.is_object
        target_is_iface = target_type_info.parent_id == "interface" if target_type_info else False

        for prop in sorted(self.object.properties, key=lambda p: p.property_id):
            info = prop.info

            if info.is_a11y:
                continue

            # Ignore construct only properties
            if info.construct_only:
                continue

            source_type_info = self.object.project.type_info.get(info.type_id, None)
            source_is_object = info.is_object
            source_is_iface = source_type_info.parent_id == "interface" if source_type_info else False

            if target_is_object or target_is_iface:
                # Ignore non object properties
                if not source_is_object and not source_is_iface:
                    continue

                # Ignore object properties of a different type
                if source_type_info and not source_type_info.is_a(target_info.type_id):
                    continue
            elif source_is_object or source_is_iface:
                continue

            # Enums and Flags has to be the same type
            if target_type_info and target_type_info.parent_id in ["flags", "enum"] and info.type_id != target_type:
                continue

            if source_type_info and source_type_info.parent_id in ["flags", "enum"] and info.type_id != target_type:
                continue

            compatible = info.type_id == target_type

            if not compatible:
                try:
                    gtype_id = GObject.type_from_name(info.type_id)
                    gtarget_id = GObject.type_from_name(target_type)
                    if gtype_id and gtarget_id:
                        compatible = GObject.Value.type_compatible(gtype_id, gtarget_id)
                        if not compatible:
                            compatible = GObject.Value.type_transformable(gtype_id, gtarget_id)
                except Exception as e:  # noqa F841
                    self.append(prop.property_id, prop.property_id + "*")
                    continue

            if compatible:
                self.append(prop.property_id, prop.property_id)
