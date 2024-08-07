#
# Cambalache Object wrapper
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

from gi.repository import GObject, Gio

from .cmb_objects_base import CmbBaseObject, CmbSignal
from .cmb_property import CmbProperty
from .cmb_layout_property import CmbLayoutProperty
from .cmb_object_data import CmbObjectData
from .cmb_type_info import CmbTypeInfo
from .cmb_ui import CmbUI
from . import utils
from cambalache import getLogger, _

logger = getLogger(__name__)


class CmbObject(CmbBaseObject):
    info = GObject.Property(type=CmbTypeInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    __gsignals__ = {
        "property-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbProperty,)),
        "layout-property-changed": (GObject.SignalFlags.RUN_FIRST, None, (GObject.GObject, CmbLayoutProperty)),
        "signal-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbSignal,)),
        "signal-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbSignal,)),
        "signal-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbSignal,)),
        "data-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbObjectData,)),
        "data-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObjectData,)),
    }

    def __init__(self, **kwargs):
        self.properties = []
        self.properties_dict = {}
        self.layout = []
        self.layout_dict = {}
        self.signals = []
        self.signals_dict = {}
        self.data = []
        self.data_dict = {}
        self.position_layout_property = None
        self.inline_property_id = None
        self.version_warning = None

        super().__init__(**kwargs)

        self.connect("notify", self.__on_notify)

        if self.project is None:
            return

        # List of children
        self.children_model = Gio.ListStore(item_type=CmbObject)

        self._parent_id = self.parent_id

        # Append object to project automatically
        self.project._append_object(self)
        self._append()

        self.__populate_properties()
        self.__populate_layout_properties()
        self.__populate_signals()
        self.__populate_data()
        self.__update_version_warning()
        self.ui.connect("library-changed", self._on_ui_library_changed)

    def __str__(self):
        return f"CmbObject<{self.type_id}> {self.ui_id}:{self.object_id}"

    def _append(self):
        ui_id = self.ui_id
        object_id = self.object_id
        parent_id = self.parent_id
        position = self.position

        if parent_id:
            # Set which parent property makes a reference to this inline object
            row = self.project.db.execute(
                "SELECT property_id FROM object_property WHERE ui_id=? AND inline_object_id=?;", (ui_id, object_id)
            ).fetchone()
            self.inline_property_id = row[0] if row else None
            model = self.parent.children_model
        else:
            model = self.ui.children_model

        if position >= 0:
            # Map DB position to list position
            if parent_id:
                row = self.project.db.execute(
                    "SELECT count(object_id) FROM object WHERE ui_id=? AND parent_id=? AND position < ?;",
                    (ui_id, parent_id, position)
                ).fetchone()
                position = row[0]
            else:
                row = self.project.db.execute(
                    "SELECT count(object_id) FROM object WHERE ui_id=? AND parent_id IS NULL AND position < ?;",
                    (ui_id, position)
                ).fetchone()
                position = row[0]

            model.insert(position, self)
        else:
            model.append(self)

    def __populate_type_properties(self, name):
        property_info = self.project.get_type_properties(name)
        if property_info is None:
            return

        for property_name in property_info:
            info = property_info[property_name]

            prop = CmbProperty(
                object=self,
                project=self.project,
                ui_id=self.ui_id,
                object_id=self.object_id,
                owner_id=name,
                property_id=info.property_id,
                info=info,
            )

            # List of property
            self.properties.append(prop)

            # Dictionary of properties
            self.properties_dict[property_name] = prop

    def __populate_properties(self):
        self.__populate_type_properties(self.type_id)
        for parent_id in self.info.hierarchy:
            self.__populate_type_properties(parent_id)

    def __populate_layout_properties_from_type(self, name):
        property_info = self.project.get_type_properties(name)
        if property_info is None:
            return

        # parent_id is stored in the DB so its better to cache it
        parent_id = self.parent_id
        for property_name in property_info:
            info = property_info[property_name]

            prop = CmbLayoutProperty(
                object=self,
                project=self.project,
                ui_id=self.ui_id,
                object_id=parent_id,
                child_id=self.object_id,
                owner_id=name,
                property_id=info.property_id,
                info=info,
            )

            # Keep a reference to the position layout property
            if info.is_position:
                self.position_layout_property = prop

            self.layout.append(prop)

            # Dictionary of properties
            self.layout_dict[property_name] = prop

    def _property_changed(self, prop):
        self.emit("property-changed", prop)
        self.project._object_property_changed(self, prop)

    def _layout_property_changed(self, prop):
        parent = self.project.get_object_by_id(self.ui_id, self.parent_id)
        self.emit("layout-property-changed", parent, prop)
        self.project._object_layout_property_changed(parent, self, prop)

    def __add_signal_object(self, signal):
        self.signals.append(signal)
        self.signals_dict[signal.signal_pk] = signal
        self.emit("signal-added", signal)
        self.project._object_signal_added(self, signal)

        signal.connect("notify", self.__on_signal_notify)

    def __on_signal_notify(self, signal, pspec):
        self.emit("signal-changed", signal)
        self.project._object_signal_changed(self, signal)

    def __add_data_object(self, data):
        if data in self.data:
            return

        self.data.append(data)
        self.data_dict[data.get_id_string()] = data
        self.emit("data-added", data)
        self.project._object_data_added(self, data)

    def __on_notify(self, obj, pspec):
        if pspec.name == "parent-id":
            self.__populate_layout_properties()

        self.project._object_changed(self, pspec.name)

    def __populate_signals(self):
        c = self.project.db.cursor()

        # Populate signals
        for row in c.execute("SELECT * FROM object_signal WHERE ui_id=? AND object_id=?;", (self.ui_id, self.object_id)):
            self.__add_signal_object(CmbSignal.from_row(self.project, *row))

    def __populate_data(self):
        c = self.project.db.cursor()

        # Populate data
        for row in c.execute(
            "SELECT * FROM object_data WHERE ui_id=? AND object_id=? AND parent_id IS NULL;",
            (self.ui_id, self.object_id),
        ):
            self.__add_data_object(CmbObjectData.from_row(self.project, *row))

    def __populate_layout_properties(self):
        parent_id = self.parent_id

        # FIXME: delete is anything is set?
        self.layout = []
        self.layout_dict = {}

        if parent_id > 0:
            # FIXME: what about parent layout properties?
            parent = self.project.get_object_by_id(self.ui_id, parent_id)
            self.__populate_layout_properties_from_type(f"{parent.type_id}LayoutChild")

    @GObject.Property(type=int)
    def parent_id(self):
        retval = self.db_get(
            "SELECT parent_id FROM object WHERE (ui_id, object_id) IS (?, ?);",
            (
                self.ui_id,
                self.object_id,
            ),
        )
        return retval if retval is not None else 0

    @parent_id.setter
    def _set_parent_id(self, value):
        # FIXME: implement GListModel to avoid having to update children position
        if self._parent_id:
            old_parent = self.project.get_object_by_id(self.ui_id, self._parent_id)
            children_model = old_parent.children_model
        else:
            children_model = self.ui.children_model

        found, position = children_model.find(self)
        if found:
            children_model.remove(position)

        self.db_set(
            "UPDATE object SET parent_id=? WHERE (ui_id, object_id) IS (?, ?);",
            (
                self.ui_id,
                self.object_id,
            ),
            value if value != 0 else None,
        )
        self._parent_id = value if value != 0 else None

        self._append()
        self.__populate_layout_properties()

    @GObject.Property(type=CmbUI)
    def ui(self):
        return self.project.get_object_by_id(self.ui_id)

    @GObject.Property(type=GObject.Object)
    def parent(self):
        return self.project.get_object_by_id(self.ui_id, self.parent_id)

    def _add_signal(self, signal_pk, owner_id, signal_id, handler, detail=None, user_data=0, swap=False, after=False):
        signal = CmbSignal(
            project=self.project,
            signal_pk=signal_pk,
            ui_id=self.ui_id,
            object_id=self.object_id,
            owner_id=owner_id,
            signal_id=signal_id,
            handler=handler,
            detail=detail,
            user_data=user_data if user_data is not None else 0,
            swap=swap,
            after=after,
        )

        self.__add_signal_object(signal)

        return signal

    def add_signal(self, owner_id, signal_id, handler, detail=None, user_data=0, swap=False, after=False):
        try:
            c = self.project.db.cursor()
            c.execute(
                """
                INSERT INTO object_signal (ui_id, object_id, owner_id, signal_id, handler, detail, user_data, swap, after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (self.ui_id, self.object_id, owner_id, signal_id, handler, detail, user_data, swap, after),
            )
            signal_pk = c.lastrowid
            c.close()
            self.project.db.commit()
        except Exception as e:
            logger.warning(
                f"Error adding signal handler {owner_id}:{signal_id} {handler} to object {self.ui_id}.{{self.object_id}} {e}"
            )
            return None
        else:
            return self._add_signal(
                signal_pk,
                owner_id,
                signal_id,
                handler,
                detail=detail,
                user_data=user_data if user_data is not None else 0,
                swap=swap,
                after=after,
            )

    def _remove_signal(self, signal):
        self.signals.remove(signal)
        del self.signals_dict[signal.signal_pk]

        self.emit("signal-removed", signal)
        self.project._object_signal_removed(self, signal)

    def remove_signal(self, signal):
        try:
            self.project.db.execute("DELETE FROM object_signal WHERE signal_pk=?;", (signal.signal_pk,))
            self.project.db.commit()
        except Exception as e:
            handler = f"{signal.owner_id}:{signal.signal_id} {signal.handler}"
            logger.warning(f"Error removing signal handler {handler} from object {self.ui_id}.{{self.object_id}} {e}")
            return False
        else:
            self._remove_signal(signal)
            return True

    def _add_data(self, owner_id, data_id, id, info=None):
        data = CmbObjectData(
            project=self.project,
            object=self,
            info=info,
            ui_id=self.ui_id,
            object_id=self.object_id,
            owner_id=owner_id,
            data_id=data_id,
            id=id,
        )
        self.__add_data_object(data)
        return data

    def add_data(self, data_key, value=None, comment=None):
        try:
            value = str(value) if value is not None else None
            taginfo = self.info.get_data_info(data_key)
            owner_id = taginfo.owner_id
            data_id = taginfo.data_id
            id = self.project.db.object_add_data(self.ui_id, self.object_id, owner_id, data_id, value, None, comment)
        except Exception as e:
            logger.warning(f"Error adding data {data_key} {e}")
            return None
        else:
            return self._add_data(owner_id, data_id, id, info=taginfo)

    def _remove_data(self, data):
        if data not in self.data:
            return

        self.data.remove(data)
        del self.data_dict[data.get_id_string()]

        self.emit("data-removed", data)
        self.project._object_data_removed(self, data)

    def remove_data(self, data):
        try:
            assert data in self.data
            self.project.db.execute(
                "DELETE FROM object_data WHERE ui_id=? AND object_id=? AND owner_id=? AND data_id=? AND id=?;",
                (self.ui_id, self.object_id, data.owner_id, data.data_id, data.id),
            )
            self.project.db.commit()
        except Exception as e:
            logger.warning(f"{self} Error removing data {data}: {e}")
            return False
        else:
            self._remove_data(data)
            return True

    def reorder_child(self, child, position):
        if child is None:
            logger.warning("child has to be a CmbObject")
            return

        if self.ui_id != child.ui_id or self.object_id != child.parent_id:
            logger.warning(f"{child} is not children of {self}")
            return

        name = child.name if child.name is not None else child.type_id
        self.project.history_push(
            _("Reorder object {name} from position {old} to {new}").format(name=name, old=child.position, new=position)
        )

        # Reorder child in store
        found, index = self.children_model.find(child)
        if found:
            self.children_model.remove(index)

        n_items = self.children_model.get_n_items()
        if position > n_items:
            position = n_items
        self.children_model.insert(position, child)

        children = []

        # Get children in order
        c = self.project.db.cursor()
        for row in c.execute(
            """
            SELECT object_id, position
            FROM object
            WHERE ui_id=? AND parent_id=? AND internal IS NULL AND object_id!=? AND object_id NOT IN
                 (SELECT inline_object_id FROM object_property WHERE inline_object_id IS NOT NULL AND ui_id=? AND object_id=?)
            ORDER BY position;
            """,
            (self.ui_id, self.object_id, child.object_id, self.ui_id, self.object_id),
        ):
            child_id, child_position = row

            obj = self.project.get_object_by_id(self.ui_id, child_id)
            if obj:
                children.append(obj)

        # Insert child in new position
        children.insert(position, child)

        # Update all positions
        for pos, obj in enumerate(children):
            # Sync layout property
            if obj.position_layout_property:
                obj.position_layout_property.value = pos
            else:
                # Or object position
                obj.position = pos

        c.close()
        self.project.history_pop()

    def clear_properties(self):
        c = self.project.db.cursor()

        name = self.name
        name = name if name is not None else self.type_id
        self.project.history_push(_("Clear object {name} properties").format(name=name))

        properties = []
        for row in c.execute(
            "SELECT property_id FROM object_property WHERE ui_id=? AND object_id=?;", (self.ui_id, self.object_id)
        ):
            properties.append(row[0])

        # Remove all properties from this object
        c.execute("DELETE FROM object_property WHERE ui_id=? AND object_id=?;", (self.ui_id, self.object_id))

        self.project.history_pop()
        c.close()

        for prop_id in properties:
            prop = self.properties_dict[prop_id]
            prop.notify("value")
            self._property_changed(prop)

    @GObject.Property(type=str)
    def display_name(self):
        inline_prop = self.inline_property_id
        inline_prop = f"<b>{inline_prop}</b> " if inline_prop else ""
        name = f"{self.name} " if self.name else ""
        extra = _("(template)") if not self.parent_id and self.ui.template_id == self.object_id else self.type_id
        display_name = f"{inline_prop}{name}<i>{extra}</i>"

        if self.version_warning:
            return f'<span underline="error">{display_name}</span>'
        else:
            return display_name

    def __update_version_warning(self):
        target = self.ui.get_target(self.info.library_id)
        self.version_warning = utils.get_version_warning(target, self.info.version, self.info.deprecated_version, self.type_id)

    def _on_ui_library_changed(self, ui, library_id):
        self.__update_version_warning()

        # Update properties directly, to avoid having to connect too many times to this signal
        for props in [self.properties, self.layout]:
            for prop in props:
                if prop.library_id == library_id:
                    prop._update_version_warning()
