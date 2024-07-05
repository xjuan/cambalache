#
# CmbDBInspector
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

from gi.repository import GObject, Gio, Gtk
from cambalache import CmbProject


class CmbDBTable(GObject.Object):
    def __init__(self, **kwargs):
        self.__properties = {}
        super().__init__(**kwargs)

    def do_get_property(self, prop):
        if prop.name not in self.__properties_set__:
            raise AttributeError('unknown property %s' % prop.name)
        return self.__properties[prop.name]

    def do_set_property(self, prop, value):
        if prop.name not in self.__properties_set__:
            raise AttributeError('unknown property %s' % prop.name)
        self.__properties[prop.name] = value
        self.notify(prop.name)


class TableView(Gtk.ColumnView):
    project = GObject.Property(type=CmbProject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, ItemClass, **kwargs):
        super().__init__(**kwargs)

        self.props.show_row_separators = True
        self.props.show_column_separators = True
        self.props.reorderable = False

        self.__item_class = ItemClass
        self.__table__ = ItemClass.__table__
        self.model = Gio.ListStore(item_type=ItemClass)

        self.set_model(Gtk.NoSelection(model=self.model))

        for prop in ItemClass.__properties__:
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self._on_factory_setup)
            factory.connect("bind", self._on_factory_bind, prop)
            factory.connect("unbind", self._on_factory_unbind, prop)
            factory.connect("teardown", self._on_factory_teardown)

            col = Gtk.ColumnViewColumn(title=prop, factory=factory)
            col.props.resizable = True
            self.append_column(col)

        self.connect("map", self.__on_map)

    def _on_factory_setup(self, factory, list_item):
        cell = Gtk.Label(xalign=0)
        cell._binding = None
        list_item.set_child(cell)

    def _on_factory_bind(self, factory, list_item, what):
        cell = list_item.get_child()
        item = list_item.get_item()
        cell._binding = item.bind_property(what, cell, "label", GObject.BindingFlags.SYNC_CREATE)

    def _on_factory_unbind(self, factory, list_item, what):
        cell = list_item.get_child()
        if cell._binding:
            cell._binding.unbind()
            cell._binding = None

    def _on_factory_teardown(self, factory, list_item):
        cell = list_item.get_child()
        cell._binding = None

    def refresh(self):
        ItemClass = self.__item_class
        properties = ItemClass.__properties__
        self.model.remove_all()

        for row in self.project.db.execute(f"SELECT * FROM {ItemClass.__table__};"):
            item = ItemClass()
            for i, val in enumerate(row):
                item.set_property(properties[i], val)

            self.model.append(item)

    def __on_map(self, w):
        self.refresh()


@Gtk.Template(resource_path="/ar/xjuan/Cambalache/cmb_db_inspector.ui")
class CmbDBInspector(Gtk.Box):
    __gtype_name__ = "CmbDBInspector"

    stack = Gtk.Template.Child()

    def __init__(self, **kwargs):
        self.__project = None
        self.__table_classes = None
        super().__init__(**kwargs)

        self.connect("map", self.__on_map)

    @GObject.Property(type=CmbProject)
    def project(self):
        return self.__project

    @project.setter
    def _set_project(self, project):
        self.__project = project

    def __init_tables(self):
        db = self.project.db
        self.__table_classes = {}

        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"):
            table, = row

            if table.startswith("sqlite_"):
                continue

            klass = self.__class_from_table(table)
            self.__table_classes[table] = klass

    def _gproperties_from_table(self, table):
        db = self.project.db
        properties = []
        gproperties = {}

        for row in db.execute(f"PRAGMA table_info({table});"):
            col = row[1]
            name = col.replace("_", "-")
            properties.append(name)
            gproperties[name] = (str, "", "", None, GObject.ParamFlags.READWRITE)

        return properties, gproperties

    def __class_from_table(self, table):
        class_name = f"CmbDBTable_{table}"
        properties, gproperties = self._gproperties_from_table(table)
        klass = type(class_name, (CmbDBTable,), dict(
            __table__=table,
            __gproperties__=gproperties,
            __properties__=properties,
            __properties_set__=set(properties))
        )
        return klass

    def __populate_stack(self):
        for table, klass in self.__table_classes.items():
            sw = Gtk.ScrolledWindow(
                hexpand=True,
                vexpand=True,
                propagate_natural_width=True,
                propagate_natural_height=True)
            view = TableView(klass, project=self.__project)
            sw.set_child(view)
            self.stack.add_titled(sw, table, table)

    def __on_map(self, w):
        if self.__table_classes is None and self.__project is not None:
            self.__init_tables()
            self.__populate_stack()
