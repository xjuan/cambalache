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

from .cmb_objects_base import CmbBasePropertyInfo

from cambalache import getLogger

logger = getLogger(__name__)


class CmbPropertyInfo(CmbBasePropertyInfo):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_a11y = self.owner_id in ["CmbAccessibleProperty", "CmbAccessibleRelation", "CmbAccessibleState"]

        if self.is_a11y:
            prefix = {
                "CmbAccessibleProperty": "cmb-a11y-property-",
                "CmbAccessibleRelation": "cmb-a11y-relation-",
                "CmbAccessibleState": "cmb-a11y-state-"
            }.get(self.owner_id, "")

            # A11y property name without prefix
            self.a11y_property_id = self.property_id.removeprefix(prefix)
        else:
            self.a11y_property_id = None
