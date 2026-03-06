#
# CmbHelpWindow
#
# Copyright (C) 2026 Juan Pablo Ugarte
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

from gi.repository import Gio, GObject, GtkSource, Gtk, Adw
from cambalache import config


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/app/cmb_help_window.ui")
class CmbHelpWindow(Adw.ApplicationWindow):
    __gtype_name__ = "CmbHelpWindow"

    source_style = GObject.Property(type=GtkSource.StyleScheme, flags=GObject.ParamFlags.READWRITE)

    resource = None

    def __init__(self, **kwargs):
        self.__ensure_resources()
        super().__init__(**kwargs)

        app = self.props.application
        app.props.style_manager.connect("notify::dark", lambda o, p: self.__update_dark_mode(app.props.style_manager))
        self.__update_dark_mode(app.props.style_manager)

    def __update_dark_mode(self, style_manager):
        if style_manager.props.dark:
            self.source_style = GtkSource.StyleSchemeManager.get_default().get_scheme("Adwaita-dark")
            self.add_css_class("dark")
        else:
            self.remove_css_class("dark")
            self.source_style = GtkSource.StyleSchemeManager.get_default().get_scheme("tango")

    @classmethod
    def __ensure_resources(cls):
        if cls.resource is None:
            cls.resource = Gio.Resource.load(os.path.join(config.pkgdatadir, "help.gresource"))
            cls.resource._register()

    @Gtk.Template.Callback("on_close_request")
    def __on_close_request(self, win):
        self.hide()
        return True

