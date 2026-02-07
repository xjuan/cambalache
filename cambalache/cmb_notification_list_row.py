#
# CmbNotificationListRow
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

import datetime

from cambalache import getLogger
from gi.repository import GObject, Gtk

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_notification_list_row.ui")
class CmbNotificationListRow(Gtk.ListBoxRow):
    __gtype_name__ = "CmbNotificationListRow"

    view = GObject.Property(type=Gtk.Widget, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    box = Gtk.Template.Child()
    date_label = Gtk.Template.Child()
    close_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.props.activatable = False

        notification = self.view.notification
        start_date = datetime.datetime.utcfromtimestamp(notification.start_date).strftime("%x")
        self.date_label.set_label(f"<small>{start_date}</small>")
        self.box.prepend(self.view)

        self.add_css_class("cmb-notification-list-row")

    @Gtk.Template.Callback("on_map")
    def __on_map(self, w):
        self.props.child.props.reveal_child = True

    @Gtk.Template.Callback("on_close_button_clicked")
    def __on_close_button_clicked(self, button):
        notification = self.view.notification
        notification.center.remove(notification)
