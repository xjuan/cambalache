#
# CmbContextMenu - Cambalache UI Editor
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

from gi.repository import GObject, GLib, Gio, Gdk, Gtk
from cambalache import _


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_context_menu.ui")
class CmbContextMenu(Gtk.PopoverMenu):
    __gtype_name__ = "CmbContextMenu"

    enable_theme = GObject.Property(
        type=bool,
        default=False,
        flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY
    )
    target_tk = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    main_section = Gtk.Template.Child()
    add_submenu = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.theme_submenu = None

        super().__init__(**kwargs)

        self.connect("notify::target-tk", self.__on_target_tk_notify)

    def __on_target_tk_notify(self, obj, pspec):
        self.__populate_css_theme_box()
        self.__update_add_submenu()

    def __update_add_submenu(self):
        if self.target_tk not in ["gtk-4.0", "gtk+-3.0"]:
            return

        types = [
            "GtkBox",
            "GtkGrid",
            "GtkExpander",
            "GtkRevealer",
            "GtkOverlay",
            "GtkScrolledWindow",
        ]

        if self.target_tk == "gtk+-3.0":
            types += [
                "GtkAligment",
                "GtkEventBox"
            ]
        else:
            types += [
                "GtkGraphicsOffload",
            ]

        self.add_submenu.remove_all()

        for gtype in sorted(types):
            item = Gio.MenuItem()
            item.set_label(gtype)
            item.set_action_and_target_value("win.add_parent", GLib.Variant("s", gtype))
            self.add_submenu.append_item(item)

    def __populate_css_theme_box(self):
        gtk_path = "gtk-3.0"

        if not self.enable_theme or self.target_tk not in ["gtk-4.0", "gtk+-3.0"]:
            return

        if self.target_tk == "gtk-4.0":
            gtk_path = "gtk-4.0"
            # FIXME: whats the real default theme for gtk4?
            themes = ["Default"]
        else:
            themes = ["Adwaita", "HighContrast", "HighContrastInverse"]

        if self.theme_submenu is None:
            self.theme_submenu = Gio.Menu()
            self.main_section.prepend_submenu(_("CSS theme"), self.theme_submenu)

        # Remove all items from theme submenu
        self.theme_submenu.remove_all()

        dirs = []

        dirs += GLib.get_system_data_dirs()
        dirs.append(GLib.get_user_data_dir())

        # Add /themes to every dir
        dirs = list(map(lambda d: os.path.join(d, "themes"), dirs))

        # Append ~/.themes
        dirs.append(os.path.join(GLib.get_home_dir(), ".themes"))

        for path in dirs:
            if not os.path.isdir(path):
                continue

            for theme in os.listdir(path):
                tpath = os.path.join(path, theme, gtk_path, "gtk.css")
                if os.path.exists(tpath):
                    themes.append(theme)

        # Dedup and sort
        themes = list(dict.fromkeys(themes))

        for theme in sorted(themes):
            item = Gio.MenuItem()
            item.set_label(theme)
            item.set_action_and_target_value("win.workspace_theme", GLib.Variant("s", theme))
            self.theme_submenu.append_item(item)

    def popup_at(self, x, y):
        r = Gdk.Rectangle()
        r.x, r.y = (x, y)
        r.width = r.height = 0
        self.set_pointing_to(r)
        self.popup()
