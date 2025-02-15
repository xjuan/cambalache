#
# CmbNotificationListView
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
from .cmb_version_notification_view import CmbVersionNotificationView
from .cmb_message_notification_view import CmbMessageNotificationView
from .cmb_poll_notification_view import CmbPollNotificationView
from .cmb_notification_list_row import CmbNotificationListRow
from .cmb_notification import CmbNotificationCenter, CmbVersionNotification, CmbMessageNotification, CmbPollNotification

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_notification_list_view.ui")
class CmbNotificationListView(Gtk.Box):
    __gtype_name__ = "CmbNotificationListView"

    notification_center = GObject.Property(type=CmbNotificationCenter, flags=GObject.ParamFlags.READWRITE)

    list_box = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect("notify::notification-center", self.__on_notification_center_notify)

    def __on_notification_center_notify(self, obj, pspec):
        self.list_box.bind_model(self.notification_center.store, self.__create_widget_func)

    def __create_widget_func(self, item):
        if isinstance(item, CmbVersionNotification):
            view = CmbVersionNotificationView(notification=item)
        elif isinstance(item, CmbMessageNotification):
            view = CmbMessageNotificationView(notification=item)
        elif isinstance(item, CmbPollNotification):
            view = CmbPollNotificationView(notification=item)

        return CmbNotificationListRow(view=view)
