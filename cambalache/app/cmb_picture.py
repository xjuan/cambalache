#
# CmbPicture
#
# Copyright (C) 2026  Juan Pablo Ugarte
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

from gi.repository import Gtk


class CmbPicture(Gtk.Picture):
    __gtype_name__ = "CmbPicture"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_measure(self, orientation, for_size):
        if self.props.paintable:
            width = self.props.paintable.get_intrinsic_width()
            height = self.props.paintable.get_intrinsic_height()

            if width < for_size:
                return height, height, -1, -1

            h = max(height/2, height * (for_size/width))
            return (h, h, -1, -1)

        return -1, -1, -1, -1

