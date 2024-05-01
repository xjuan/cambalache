# GtkWindow Controller
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

from gi.repository import GObject, Gtk, CambalachePrivate

from .mrg_gtk_bin import MrgGtkBin
from .mrg_selection import MrgSelection

from merengue import getLogger

logger = getLogger(__name__)


class MrgGtkWindow(MrgGtkBin):
    object = GObject.Property(type=Gtk.Window, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        self.selection = None

        super().__init__(**kwargs)

        self.selection = MrgSelection(app=self.app, container=self.object)
        self.property_ignore_list.add("modal")

    def object_changed(self, old, new):
        super().object_changed(old, new)

        if old:
            old.destroy()

        # Handle widget selection
        if self.selection:
            self.selection.container = self.object

        if self.object:
            self._update_name()

            # Make sure the user can not close the window
            if Gtk.MAJOR_VERSION == 4:
                self.object.connect("close-request", lambda o: True)
            else:
                self.object.connect("delete-event", lambda o, e: True)

            # Disable modal at runtime
            self.object.props.modal = False

            # Always show toplevels windows
            if Gtk.MAJOR_VERSION == 4:
                self.object.show()
            else:
                self.object.show_all()

            # Add gtk version CSS class
            if Gtk.MAJOR_VERSION == 4:
                self.object.add_css_class("gtk4")
            else:
                self.object.get_style_context().add_class("gtk3")

    def _update_name(self):
        if self.object is None:
            return

        # TODO: find a way to get object name instead of ID
        type_name = GObject.type_name(self.object.__gtype__)
        self.object.props.title = type_name

        CambalachePrivate.widget_set_application_id(self.object,
                                                    f"Cmb:{self.ui_id}.{self.object_id}")
