# Constants
#
# Copyright (C) 2023  Juan Pablo Ugarte
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

# This is the name used for external objects references. See gtk_builder_expose_object()
# It is not a valid GType name on purpose since it will never be exported.
EXTERNAL_TYPE = "(external)"

# This type is used for unknown types, the xml is preserved vervatim
CUSTOM_TYPE = "(custom)"

GMENU_TYPE = "(menu)"
GMENU_SECTION_TYPE = "(section)"
GMENU_SUBMENU_TYPE = "(submenu)"
GMENU_ITEM_TYPE = "(item)"
