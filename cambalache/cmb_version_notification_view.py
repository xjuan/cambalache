#
# CmbVersionNotificationView
#
# Copyright (C) 2025  Juan Pablo Ugarte
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

from cambalache import _, getLogger
from gi.repository import GObject, Gtk
from .cmb_notification import CmbVersionNotification

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_version_notification_view.ui")
class CmbVersionNotificationView(Gtk.Box):
    __gtype_name__ = "CmbVersionNotificationView"

    notification = GObject.Property(
        type=CmbVersionNotification, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY
    )

    # Version
    version_label = Gtk.Template.Child()
    release_notes_label = Gtk.Template.Child()
    read_more_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        notification = self.notification
        self.version_label.props.label = _("<b>Version {version} is available</b>").format(version=notification.version)
        self.release_notes_label.props.label = notification.release_notes
        self.read_more_button.props.uri = notification.read_more_url
