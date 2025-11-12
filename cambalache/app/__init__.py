# Cambalache Application
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
import gi

gi.require_version('GIRepository', '3.0')
from cambalache import config
from gi.repository import Gio

resource = Gio.Resource.load(os.path.join(config.pkgdatadir, "app.gresource"))
resource._register()

repository = gi.Repository.get_default()
repository.prepend_search_path(config.privatecambalachedir)
repository.prepend_library_path(config.privatecambalachedir)

from .cmb_application import CmbApplication
from .cmb_scrolled_window import CmbScrolledWindow
