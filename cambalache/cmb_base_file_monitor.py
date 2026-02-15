#
# Cambalache Base File Monitor
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

from .cmb_base import CmbBase
from cambalache import getLogger

logger = getLogger(__name__)


class FileStatus(GObject.GEnum):
    NONE = 0
    DELETED = 1
    CHANGED = 2
    NOT_FOUND = 3
    RENAMED = 4


# FIXME: this should be a GInterface
class CmbBaseFileMonitor(CmbBase):
    __gtype_name__ = "CmbBaseFileMonitor"

    file_status = GObject.Property(type=FileStatus, default=FileStatus.NONE, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.saving = False
        self.monitor = None
        self.gfile = None
        self.new_filename = None

    def __on_file_changed(self, file_monitor, file, other_file, event_type):
        if self.saving:
            return

            self.file_status = FileStatus.CHANGED
        elif event_type in [Gio.FileMonitorEvent.DELETED, Gio.FileMonitorEvent.MOVED_OUT]:
            # TODO: if moved out but still inside the directory hierarchy we should update the path
            self.file_status = FileStatus.DELETED
        elif event_type == Gio.FileMonitorEvent.RENAMED:
            if self.file_status == FileStatus.NOT_FOUND:
                self.file_status = FileStatus.CHANGED
                return

            filename = other_file.get_path()
            projectdir = os.path.dirname(self.project.filename) if self.project.filename else "."
            self.new_filename = os.path.relpath(filename, projectdir)
            self.file_status = FileStatus.RENAMED

    def update_file_monitor(self, filename):
        if self.monitor:
            self.monitor.cancel()

        old_path = None
        if self.gfile:
            old_path = self.gfile.get_path()
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

        if old_path and os.path.exists(old_path) and old_path != fullpath:
            # Clear file state
            if filename in self.project._file_state:
                self.project._file_state.pop(filename)

            # Rename and force project save
            os.rename(old_path, fullpath)
            self.project.save()

        self.gfile = Gio.File.new_for_path(fullpath)
        self.monitor = self.gfile.monitor(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.monitor.connect("changed", self.__on_file_changed)

    def reload(self):
        self.file_status = FileStatus.NONE

        # Clear history
        self.project.history_enabled = True
        self.project.clear_history()
