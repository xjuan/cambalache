#
# CmbPixbufEntry
#
# Copyright (C) 2021-2023  Juan Pablo Ugarte
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

from cambalache import _
from gi.repository import Gtk


from .cmb_file_entry import CmbFileEntry


class CmbPixbufEntry(CmbFileEntry):
    __gtype_name__ = "CmbPixbufEntry"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.title = (_("Select Image"),)
        self.props.placeholder_text = "<GdkPixbuf>"

        # Only show images formats supported by GdkPixbuf
        self.filter = Gtk.FileFilter()
        self.filter.add_pixbuf_formats()
