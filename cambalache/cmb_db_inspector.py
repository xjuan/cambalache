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
        # TODO: read from DB directly
        if prop.name not in self.__properties_set__:
            raise AttributeError('unknown property %s' % prop.name)
        return self.__properties[prop.name]

    def do_set_property(self, prop, value):
        # TODO: only store PK values when using DB
        if prop.name not in self.__properties_set__:
            raise AttributeError('unknown property %s' % prop.name)
        self.__properties[prop.name] = value
        self.notify(prop.name)


class CmbDBStore(GObject.GObject, Gio.ListModel):
    __gtype_name__ = 'CmbDBStore'

    project = GObject.Property(type=CmbProject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, ItemClass, **kwargs):
        super().__init__(**kwargs)

        self.__item_class = ItemClass
        self.__history_index = None
        self._objects = []

    def do_get_item(self, position):
        self.__check_refresh()
        return self._objects[position] if position < len(self._objects) else None

    def do_get_item_type(self):
        return self.__item_class

    def do_get_n_items(self):
        self.__check_refresh()
        return len(self._objects)

    def __check_refresh(self):
        history_index = self.project.history_index

        # Nothing to update if history did not changed
        if history_index == self.__history_index:
            return

        ItemClass = self.__item_class
        properties = ItemClass.__properties__
        table = ItemClass.__table__
        needs_update = False

        # Basic optimization, only update if something changed in this table
        # TODO: this could be optimized more by check command to know exactly which row changed
        if self.__history_index is None or table in ["history", "global"]:
            needs_update = True
        else:
            change_table = table[7:] if table.startswith("history_") else table

            # TODO: detect command compression
            for row in self.project.db.execute(
                "SELECT table_name FROM history WHERE history_id >= ? ORDER BY history_id;", (self.__history_index, )
            ):
                table_name, = row
                if table_name == change_table:
                    needs_update = True
                    break

        self.__history_index = history_index

        if not needs_update:
            return

        # Emit signal to clear model
        n_items = len(self._objects)
        if n_items:
            self._objects = []
            self.items_changed(0, n_items, 0)

        if len(ItemClass.__pk__):
            pk_columns = ",".join(ItemClass.__pk__)
        else:
            pk_columns = "rowid"

        for row in self.project.db.execute(f"SELECT * FROM {table} ORDER BY {pk_columns};"):
            item = ItemClass()
            for i, val in enumerate(row):
                item.set_property(properties[i], val)

            self._objects.append(item)

        # Emit signal to populate model
        self.items_changed(0, 0, len(self._objects))


class TableView(Gtk.ColumnView):
    project = GObject.Property(type=CmbProject, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, ItemClass, **kwargs):
        super().__init__(**kwargs)

        self.props.show_row_separators = True
        self.props.show_column_separators = True
        self.props.reorderable = False
        self.__model = None
        self.__item_class = ItemClass

        for property_id in ItemClass.__properties__:
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", self._on_factory_setup)
            factory.connect("bind", self._on_factory_bind, property_id)
            factory.connect("unbind", self._on_factory_unbind)

            col = Gtk.ColumnViewColumn(title=property_id, factory=factory)
            col.props.resizable = True
            self.append_column(col)

        # TODO: keep track of project changes only while we are showing this model
        self.connect("map", self.__on_map)
        self.project.connect("changed", self.__on_project_changed)

    def __update_label(self, item, label, property_id):
        val = str(item.get_property(property_id))
        label.set_text(val if val else "")

    def __on_item_notify(self, item, pspec, label):
        self.__update_label(item, label, pspec.name)

    def _on_factory_setup(self, factory, list_item):
        label = Gtk.Label(xalign=0)
        list_item.set_child(label)

    def _on_factory_bind(self, factory, list_item, property_id):
        label = list_item.get_child()
        item = list_item.get_item()

        self.__update_label(item, label, property_id)
        item.connect(f"notify::{property_id}", self.__on_item_notify, label)

    def _on_factory_unbind(self, factory, list_item):
        item = list_item.get_item()
        item.disconnect_by_func(self.__on_item_notify)

    def __on_map(self, w):
        # Trigger check refresh
        if self.__model is not None:
            self.__model.get_n_items()
            return

        # Load model when widget is shown
        self.__model = CmbDBStore(self.__item_class, project=self.project)
        self.set_model(Gtk.NoSelection(model=self.__model))

    def __on_project_changed(self, project):
        # Trigger check refresh
        if self.__model is not None and self.is_visible():
            self.__model.get_n_items()


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

    def _metadata_from_table(self, table):
        db = self.project.db
        properties = []
        gproperties = {}
        pk_list = []

        for row in db.execute(f"PRAGMA table_info({table});"):
            col = row[1]
            pk = row[5]

            name = col.replace("_", "-")
            properties.append(name)
            gproperties[name] = (str, "", "", None, GObject.ParamFlags.READWRITE)

            if pk:
                pk_list.append(col)

        return properties, gproperties, pk_list

    def __class_from_table(self, table):
        class_name = f"CmbDBTable_{table}"
        properties, gproperties, pk = self._metadata_from_table(table)
        klass = type(class_name, (CmbDBTable,), dict(
            __table__=table,
            __gproperties__=gproperties,
            __properties__=properties,
            __properties_set__=set(properties),
            __pk__=pk)
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
