#
# CmbSuggestionEntry
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

from gi.repository import GObject, Gtk
from .cmb_entry import CmbEntry


class CmbSuggestionEntry(CmbEntry):
    __gtype_name__ = "CmbSuggestionEntry"

    def __init__(self, **kwargs):
        self._filters = {}

        super().__init__(**kwargs)

        # GObject.Object.bind_property(self, "cmb-value", self.props.buffer, "text", GObject.BindingFlags.SYNC_CREATE)

        self.type_model = Gtk.ListStore(str)

        # Completion
        self.__completion = Gtk.EntryCompletion()
        self.__completion.props.model = self.type_model
        self.__completion.props.text_column = 0
        self.__completion.props.inline_completion = True
        self.__completion.props.inline_selection = True
        self.__completion.props.popup_set_width = True
        self.props.completion = self.__completion

        # self.__completion.set_match_func(lambda o, key, iter, d: key in self.type_model[iter][0], None)

        # String
        renderer_text = Gtk.CellRendererText()
        self.__completion.pack_start(renderer_text, False)
        self.__completion.add_attribute(renderer_text, "text", 0)

    def set_suggestions(self, suggestions):
        self.type_model.clear()
        for suggestion in suggestions:
            self.type_model.append([suggestion])

    def __model_filter_func(self, model, iter, data):
        return model[iter][0] == data
