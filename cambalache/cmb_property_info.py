#
# Cambalache Property Type Info wrapper
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

from gi.repository import GObject
from .cmb_base_objects import CmbBasePropertyInfo

from cambalache import getLogger

logger = getLogger(__name__)


class CmbPropertyInfo(CmbBasePropertyInfo):
    internal_child = GObject.Property(type=GObject.GObject, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.is_a11y = CmbPropertyInfo.type_is_accessible(self.owner_id)
        self.a11y_property_id = CmbPropertyInfo.accessible_property_remove_prefix(self.owner_id, self.property_id)

    @classmethod
    def type_is_accessible(cls, owner_id):
        return owner_id in [
            "CmbAccessibleProperty",
            "CmbAccessibleRelation",
            "CmbAccessibleState",
            "CmbAccessibleAction"
        ]

    @classmethod
    def accessible_property_remove_prefix(cls, owner_id, property_id):
        prefix = {
                "CmbAccessibleProperty": "cmb-a11y-property-",
                "CmbAccessibleRelation": "cmb-a11y-relation-",
                "CmbAccessibleState": "cmb-a11y-state-",
                "CmbAccessibleAction": "cmb-a11y-action-"
            }.get(owner_id, None)

        if prefix is None:
            return None

        # A11y property name without prefix
        return property_id.removeprefix(prefix)

