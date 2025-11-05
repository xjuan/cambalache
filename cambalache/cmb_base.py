#
# Cambalache Object wrappers base class
#
# Copyright (C) 2021  Juan Pablo Ugarte
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
from cambalache import getLogger

logger = getLogger(__name__)


class CmbBase(GObject.GObject):
    project = GObject.Property(type=GObject.GObject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    display_name = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def db_get(self, query, pk):
        try:
            row = self.project.db.execute(query, pk).fetchone()
        except Exception as e:
            logger.warning(e)
            return None

        return row[0] if row is not None else None

    def db_set(self, query, pk, value):
        try:
            self.project.db.execute(query, (value,) + pk)
        except Exception as e:
            logger.warning(e)
