#
# CmbFileChangedBar - Cambalache File Changed Bar
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

from gi.repository import GObject, Gtk, Gio

from .cmb_base_file_monitor import CmbBaseFileMonitor, FileStatus
from cambalache import _, CmbUI, CmbCSS, CmbGResource


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_file_status_bar.ui")
class CmbFileStatusBar(Gtk.Box):
    __gtype_name__ = "CmbFileStatusBar"

    revealer = Gtk.Template.Child()
    label = Gtk.Template.Child()
    button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self._object = None
        self.__binding = None

        super().__init__(**kwargs)

    @GObject.Property(type=CmbBaseFileMonitor)
    def object(self):
        return self._object

    @object.setter
    def _set_object(self, obj):
        if self._object:
            self._object.disconnect_by_func(self.__on_file_status_notify)

        self._object = obj

        if obj:
            obj.connect("notify::file-status", self.__on_file_status_notify)
            self.__on_file_status_notify(obj, None)

    @Gtk.Template.Callback("on_close_clicked")
    def __on_close_clicked(self, button):
        if self._object:
            self._object.file_status = FileStatus.NONE
        else:
            self.revealer.props.reveal_child = False

    @Gtk.Template.Callback("on_button_clicked")
    def __on_button_clicked(self, button):
        if self._object is None:
            return

        if self._object.file_status == FileStatus.CHANGED:
            self._object.reload()
        elif self._object.file_status in [FileStatus.NOT_FOUND, FileStatus.DELETED]:
            if isinstance(self._object, CmbUI):
                self._object.project.remove_ui(self._object)
            elif isinstance(self._object, CmbCSS):
                self._object.project.remove_css(self._object)
            elif isinstance(self._object, CmbGResource):
                self._object.project.remove_gresource(self._object)

            self._object.file_status = FileStatus.NONE
            self._object.project.clear_history()
            self.object = None
        elif self._object.file_status == FileStatus.RENAMED:
            if isinstance(self._object, CmbGResource):
                self._object.gresources_filename = self._object.new_filename
            else:
                self._object.filename = self._object.new_filename

            self._object.file_status = FileStatus.NONE
            self._object.project.clear_history()

    def __on_file_status_notify(self, obj, pspec):
        if obj.file_status == FileStatus.CHANGED:
            self.label.props.label = _(
                "<b>File Has Changed on Disk</b>\n<small>The file has been modified by another application.</small>"
            )
            self.button.props.label = _("Discard Changes and Reload")
        elif obj.file_status == FileStatus.NOT_FOUND:
            self.label.props.label = _("<b>File Not Found</b>\n<small>The file does not exists.</small>")
            self.button.props.label = _("Remove")
        elif obj.file_status == FileStatus.DELETED:
            self.label.props.label = _("<b>File Deleted</b>\n<small>The file has been deleted by another application.</small>")
            self.button.props.label = _("Remove")
        elif obj.file_status == FileStatus.RENAMED:
            self.label.props.label = _(
                "<b>File Renamed</b>\n<small>The file has been renamed to {filename} by another application.</small>"
            ).format(filename=obj.new_filename)
            self.button.props.label = _("Update")

        self.revealer.props.reveal_child = obj.file_status


