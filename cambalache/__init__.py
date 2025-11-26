# Cambalache
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
import logging
import locale
import gettext
import builtins

from . import config

gi.require_version("GIRepository", "3.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("GtkSource", "5")
gi.require_version("WebKit", "6.0")
gi.require_version('Adw', '1')

# Ensure _() builtin
if "_" not in builtins.__dict__:
    _ = locale.gettext

if "ngettext" not in builtins.__dict__:
    ngettext = gettext.ngettext


# noqa: E402,E401
from gi.repository import Gio, Gdk, Gtk


resource = Gio.Resource.load(os.path.join(config.pkgdatadir, "cambalache.gresource"))
resource._register()

provider = Gtk.CssProvider()
provider.load_from_resource("/ar/xjuan/Cambalache/cambalache.css")
display = Gdk.Display.get_default()
Gtk.StyleContext.add_provider_for_display(display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION - 1)

# FIXME: this is needed in flatpak for icons to work
Gtk.IconTheme.get_for_display(display).add_search_path("/app/share/icons")


def getLogger(name):
    formatter = logging.Formatter("%(levelname)s:%(name)s %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(os.environ.get("CAMBALACHE_LOGLEVEL", "WARNING").upper())
    logger.addHandler(ch)

    return logger


from .cmb_base_objects import CmbBaseObject
from .cmb_base_file_monitor import CmbBaseFileMonitor
from .cmb_css import CmbCSS
from .cmb_ui import CmbUI
from .cmb_object import CmbObject
from .cmb_gresource import CmbGResource

# from .cmb_object_data import CmbObjectData
from .cmb_property import CmbProperty
from .cmb_property_label import CmbPropertyLabel
from .cmb_layout_property import CmbLayoutProperty
from .cmb_type_info import CmbTypeInfo
from .cmb_project import CmbProject

from .cmb_db_inspector import CmbDBInspector
from .cmb_file_changed_bar import CmbFileChangedBar
from .cmb_view import CmbView
from .cmb_list_view import CmbListView
from .cmb_notification import notification_center, CmbNotification, CmbNotificationCenter
from .cmb_notification_list_view import CmbNotificationListView
from .cmb_object_property_editor import CmbObjectPropertyEditor
from .cmb_object_editor import CmbObjectEditor
from .cmb_signal_editor import CmbSignalEditor
from .cmb_ui_property_editor import CmbUIPropertyEditor
from .cmb_ui_requires_editor import CmbUIRequiresEditor
from .cmb_ui_editor import CmbUIEditor
from .cmb_css_editor import CmbCSSEditor
from .cmb_gresource_editor import CmbGResourceEditor
from .cmb_fragment_editor import CmbFragmentEditor
from .cmb_accessible_editor import CmbAccessibleEditor
from .cmb_type_chooser import CmbTypeChooser
from .cmb_type_chooser_widget import CmbTypeChooserWidget
from .cmb_type_chooser_popover import CmbTypeChooserPopover
