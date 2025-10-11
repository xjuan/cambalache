#
# Cambalache File Monitor Interface
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

import os
from gi.repository import GObject, Gio


# FIXME: this should inherit from a GInterface
class CmbFileMonitor():

    def init_monitor(self, filename):
        self.changed_on_disk = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
        self.gfile = None
        self.monitor = None
        self.update_file_monitor(filename)

    def update_file_monitor(self, filename):
        if self.monitor:
            self.monitor.cancel()

        if self.gfile:
            self.gfile = None

        if not filename:
            return

        if not os.path.isabs(filename):
            if self.project.filename is None:
                return

            dirname = os.path.dirname(self.project.filename)
            fullpath = os.path.join(dirname, filename)
        else:
            fullpath = filename

        if os.path.exists(fullpath):
            def on_file_changed(file_monitor, file, other_file, event_type):
                if event_type == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
                    self.changed_on_disk = True

            self.gfile = Gio.File.new_for_path(fullpath)
            self.monitor = self.gfile.monitor(Gio.FileMonitorFlags.NONE, None)
            self.monitor.connect("changed", on_file_changed)
