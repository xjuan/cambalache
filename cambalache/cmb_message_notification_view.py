#
# CmbMessageNotificationView
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

from cambalache import getLogger
from gi.repository import GObject, Gtk
from .cmb_notification import CmbMessageNotification

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_message_notification_view.ui")
class CmbMessageNotificationView(Gtk.Box):
    __gtype_name__ = "CmbMessageNotificationView"

    notification = GObject.Property(
        type=CmbMessageNotification, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY
    )

    # Message
    title_label = Gtk.Template.Child()
    message_label = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        notification = self.notification
        self.title_label.props.label = f"<b>{notification.title}</b>"
        self.message_label.props.label = notification.message
