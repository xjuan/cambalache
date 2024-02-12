#
# CmbScrolledWindow
#
# Copyright (C) 2024  Juan Pablo Ugarte
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

from gi.repository import GObject, Gtk


class CmbScrolledWindow(Gtk.ScrolledWindow):
    __gtype_name__ = "CmbScrolledWindow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Do not let children get scroll events!
        sroll = Gtk.EventControllerScroll(
            flags=Gtk.EventControllerScrollFlags.VERTICAL, propagation_phase=Gtk.PropagationPhase.CAPTURE
        )
        sroll.connect("scroll", self.handle_scroll_capture)
        self.add_controller(sroll)

    def handle_scroll_capture(self, ec, dx, dy):
        self.props.vadjustment.props.value += self.props.vadjustment.props.step_increment * dy
        return True
