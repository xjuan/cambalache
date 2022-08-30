#
# CmbObjectEditor - Cambalache Object Editor
#
# Copyright (C) 2021  Juan Pablo Ugarte
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

import gi
import math

gi.require_version('Gtk', '3.0')
from gi.repository import GLib, GObject, Gtk

from .cmb_object import CmbObject
from .cmb_object_data_editor import CmbObjectDataEditor
from .cmb_property_controls import *


class CmbObjectEditor(Gtk.Box):
    __gtype_name__ = 'CmbObjectEditor'

    layout = GObject.Property(type=bool,
                              flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY,
                              default=False)

    def __init__(self, **kwargs):
        self.__object = None
        self.__id_label = None
        self.__labels = {}

        super().__init__(**kwargs)

        self.props.orientation = Gtk.Orientation.VERTICAL

    def __create_id_editor(self):
        grid = Gtk.Grid(hexpand=True,
                        row_spacing=4,
                        column_spacing=4)

        # Label
        self.__id_label = Gtk.Label(label=_('Object Id'),
                                    halign=Gtk.Align.START)

        # Id/Class entry
        entry = CmbEntry()
        GObject.Object.bind_property(self.__object, 'name',
                                     entry, 'cmb-value',
                                     GObject.BindingFlags.SYNC_CREATE |
                                     GObject.BindingFlags.BIDIRECTIONAL)

        grid.attach(self.__id_label, 0, 0, 1, 1)
        grid.attach(entry, 1, 0, 1, 1)

        # Template check
        if self.__object and not self.__object.parent_id:
            is_template = self.__object.object_id == self.__object.ui.template_id
            tooltip_text = _('Switch between object and template')
            derivable = self.__object.info.derivable

            if not derivable:
                tooltip_text = _('{type} is not derivable.').format(type=self.__object.info.type_id)

            label = Gtk.Label(label=_('Template'),
                              halign=Gtk.Align.START,
                              tooltip_text=tooltip_text,
                              sensitive=derivable)
            switch = Gtk.Switch(active=is_template,
                                halign=Gtk.Align.START,
                                tooltip_text=tooltip_text,
                                sensitive=derivable)

            switch.connect('notify::active', self.__on_template_switch_notify)
            self.__update_template_label()

            grid.attach(label, 0, 1, 1, 1)
            grid.attach(switch, 1, 1, 1, 1)

        return grid

    def __update_template_label(self):
        istmpl = self.__object.ui.template_id == self.__object.object_id
        self.__id_label.props.label = _('Type Name') if istmpl else _('Object Id')

    def __on_template_switch_notify(self, switch, pspec):
        self.__object.ui.template_id = self.__object.object_id if switch.props.active else 0
        self.__update_template_label()

    def __on_expander_expanded(self, expander, pspec, revealer):
        expanded = expander.props.expanded

        if expanded:
            revealer.props.transition_type = Gtk.RevealerTransitionType.SLIDE_DOWN
        else:
            revealer.props.transition_type = Gtk.RevealerTransitionType.SLIDE_UP

        revealer.props.reveal_child = expanded

    def __create_child_type_editor(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                      spacing=6)

        box.add(Gtk.Label(label=_('Child Type'), width_chars=8))

        combo = CmbChildTypeComboBox(object=self.__object)

        GObject.Object.bind_property(self.__object, 'type',
                                     combo, 'cmb-value',
                                     GObject.BindingFlags.SYNC_CREATE |
                                     GObject.BindingFlags.BIDIRECTIONAL)
        box.pack_start(combo, True, True, 0)
        return box

    def __update_view(self):
        self.__labels = {}

        for child in self.get_children():
            self.remove(child)

        if self.__object is None:
            return

        parent = self.__object.parent

        if self.layout:
            if parent is None:
                return

            # Child Type input
            if parent.info.has_child_types():
                self.add(self.__create_child_type_editor())
        else:
            # ID
            self.add(self.__create_id_editor())

        info = parent.info if self.layout and parent else self.__object.info
        for owner_id in [info.type_id] + info.hierarchy:
            if self.layout:
                owner_id = f'{owner_id}LayoutChild'

            info = self.__object.project.type_info.get(owner_id, None)

            if info is None:
                continue

            # Editor count
            i = 0

            # Grid for all properties and custom data editors
            grid = Gtk.Grid(hexpand=True,
                            margin_start=16,
                            row_spacing=4,
                            column_spacing=4)

            # Properties
            properties = self.__object.layout_dict if self.layout else self.__object.properties_dict
            for property_id in info.properties:
                prop = properties.get(property_id, None)

                if prop is None or prop.info is None:
                    continue

                editor = cmb_create_editor(prop.project,
                                           prop.info.type_id,
                                           prop=prop)

                if editor is None:
                    continue

                GObject.Object.bind_property(prop, 'value',
                                             editor, 'cmb-value',
                                             GObject.BindingFlags.SYNC_CREATE |
                                             GObject.BindingFlags.BIDIRECTIONAL)

                label = Gtk.Label(label=prop.property_id,
                                  xalign=0)

                # Keep a dict of labels
                self.__labels[prop.property_id] = label

                # Update labe status
                self.__update_property_label(prop)

                grid.attach(label, 0, i, 1, 1)
                grid.attach(editor, 1, i, 1, 1)
                i += 1

            for data_key in info.data:
                data = None

                # Find data
                for d in self.__object.data:
                    if d.info.key == data_key:
                        data = d
                        break

                editor = CmbObjectDataEditor(visible=True,
                                             hexpand=True,
                                             object=self.__object,
                                             data=data,
                                             info=None if data else info.data[data_key])

                grid.attach(editor, 0, i, 2, 1)
                i += 1

            # Continue if class had no editors to add
            if i == 0:
                continue

            # Create expander/revealer to pack editor grid
            expander = Gtk.Expander(label=f'<b>{owner_id}</b>',
                                    use_markup=True,
                                    expanded=True)
            revealer = Gtk.Revealer(reveal_child=True)
            expander.connect('notify::expanded', self.__on_expander_expanded, revealer)
            revealer.add(grid)
            self.add(expander)
            self.add(revealer)

        self.show_all()

    def __on_property_changed(self, obj, prop):
        self.__update_property_label(prop)

    def __on_layout_property_changed(self, obj, child, prop):
        self.__update_property_label(prop)

    def __update_property_label(self, prop):
        label = self.__labels.get(prop.property_id, None)

        if label is None:
            return

        if prop.value != prop.info.default_value:
            label.get_style_context().add_class('modified')
        else:
            label.get_style_context().remove_class('modified')

    @GObject.Property(type=CmbObject)
    def object(self):
        return self.__object

    @object.setter
    def _set_object(self, obj):
        if obj == self.__object:
            return

        if self.__object:
            self.__object.disconnect_by_func(self.__on_property_changed)
            self.__object.disconnect_by_func(self.__on_layout_property_changed)

        self.__object = obj

        if obj:
            self.__object.connect('property-changed',
                                 self.__on_property_changed)
            self.__object.connect('layout-property-changed',
                                 self.__on_layout_property_changed)

        self.__update_view()


Gtk.WidgetClass.set_css_name(CmbObjectEditor, 'CmbObjectEditor')
