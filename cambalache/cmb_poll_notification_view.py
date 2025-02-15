#
# CmbPollNotificationView
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

from cambalache import _, getLogger
from gi.repository import GObject, Gtk
from . import utils
from .cmb_notification import CmbPollNotification
from .cmb_poll_option_check import CmbPollOptionCheck

logger = getLogger(__name__)


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_poll_notification_view.ui")
class CmbPollNotificationView(Gtk.Box):
    __gtype_name__ = "CmbPollNotificationView"

    notification = GObject.Property(
        type=CmbPollNotification, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY
    )

    # Poll
    title_label = Gtk.Template.Child()
    description_label = Gtk.Template.Child()
    option_box = Gtk.Template.Child()
    total_label = Gtk.Template.Child()
    end_date_label = Gtk.Template.Child()
    refresh_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.__option_checks = []
        self.__updating = False
        super().__init__(**kwargs)

        notification = self.notification
        poll = notification.poll
        active = utils.utcnow() < poll.end_date

        self.title_label.props.label = f"<b>{poll.title}</b>"
        self.description_label.props.label = poll.description

        close_msg = _("<small>• Closes on {date}</small>") if active else _("<small>• Closed on {date}</small>")
        end_date = datetime.datetime.fromtimestamp(poll.end_date)
        self.end_date_label.props.label = close_msg.format(date=end_date.strftime("%x"))
        self.end_date_label.props.tooltip_text = end_date.strftime("%c")

        first_check = None
        n_option = 0
        for option in poll.options:
            button = CmbPollOptionCheck(option=option, sensitive=active)

            if poll.allowed_votes == 1:
                if first_check is None:
                    first_check = button
                else:
                    button.set_group(first_check)

            button.connect("toggled", self.__on_check_button_toggled, n_option)

            self.__option_checks.append(button)
            self.option_box.append(button)
            n_option += 1

        self.__update_results()
        notification.connect("notify", self.__on_poll_notify)

    def __on_check_button_toggled(self, button, n_option):
        allowed_votes = self.notification.poll.allowed_votes

        if self.__updating or (allowed_votes == 1 and not button.props.active):
            return

        votes = []
        for i, check in enumerate(self.__option_checks):
            if check.props.active:
                votes.append(i)

        if allowed_votes > 1:
            not_done = len(votes) < allowed_votes
            for i, check in enumerate(self.__option_checks):
                if not_done:
                    check.set_sensitive(True)
                elif not check.props.active:
                    check.set_sensitive(False)

        self.notification.center.poll_vote(self.notification, votes)

    def __on_poll_notify(self, notification, pspec):
        if pspec.name in ["my-votes", "results"]:
            self.__update_results()

    def __update_results(self):
        notification = self.notification
        results = notification.results
        my_votes = notification.my_votes

        if not results or not my_votes:
            self.total_label.props.label = ""
            for check in self.__option_checks:
                check.fraction = -1
            return

        self.__updating = True

        votes = results.votes
        total = results.total

        for i, check in enumerate(self.__option_checks):
            check.set_active(i in my_votes)
            check.fraction = votes[i] / total if total else 0

        self.total_label.props.label = _("<small>• {total} vote</small>").format(total=results.total)

        self.__updating = False

    @Gtk.Template.Callback("on_refresh_button_clicked")
    def __on_refresh_button_clicked(self, button):
        self.notification.center.poll_refresh_results(self.notification)

