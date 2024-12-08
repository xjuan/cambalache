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
# SPDX-License-Identifier: LGPL-2.1-only
#

from gi.repository import GObject, Gio

from .cmb_list_error import CmbListError
from .cmb_objects_base import CmbBaseObject, CmbSignal
from .cmb_property import CmbProperty
from .cmb_layout_property import CmbLayoutProperty
from .cmb_object_data import CmbObjectData
from .cmb_type_info import CmbTypeInfo
from .cmb_ui import CmbUI
from .constants import GMENU_SECTION_TYPE,  GMENU_SUBMENU_TYPE, GMENU_ITEM_TYPE
from . import utils
from cambalache import getLogger, _

logger = getLogger(__name__)


class CmbObject(CmbBaseObject, Gio.ListModel):
    info = GObject.Property(type=CmbTypeInfo, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    __gsignals__ = {
        "property-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbProperty,)),
        "layout-property-changed": (GObject.SignalFlags.RUN_FIRST, None, (GObject.GObject, CmbLayoutProperty)),
        "signal-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbSignal,)),
        "signal-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbSignal,)),
        "signal-changed": (GObject.SignalFlags.RUN_FIRST, None, (CmbSignal,)),
        "data-added": (GObject.SignalFlags.RUN_FIRST, None, (CmbObjectData,)),
        "data-removed": (GObject.SignalFlags.RUN_FIRST, None, (CmbObjectData,)),
        "child-reordered": (GObject.SignalFlags.RUN_FIRST, None, (CmbBaseObject, int, int)),
    }

    def __init__(self, **kwargs):
        self.__properties = None
        self.__properties_dict = None
        self.__layout = None
        self.__layout_dict = None
        self.__signals = None
        self.__signals_dict = None
        self.__data = None
        self.__data_dict = None
        self.position_layout_property = None
        self.inline_property_id = None
        self.version_warning = None
        self.__is_template = False

        self._last_known = None

        super().__init__(**kwargs)

        self.connect("notify", self.__on_notify)

        if self.project is None:
            return

        self.__update_inline_property_id()
        self.__update_version_warning()
        self.ui.connect("notify", self._on_ui_notify)
        self.ui.connect("library-changed", self._on_ui_library_changed)

    def __bool__(self):
        # Override Truth Value Testing to ensure that CmbObject objects evaluates to True even if it does not have children
        return True

    def __str__(self):
        return f"CmbObject<{self.display_name_type}> {self.ui_id}:{self.object_id}"

    @property
    def properties(self):
        self.__populate_properties()
        return self.__properties

    @property
    def properties_dict(self):
        self.__populate_properties()
        return self.__properties_dict

    @property
    def layout(self):
        self.__populate_layout()
        return self.__layout

    @property
    def layout_dict(self):
        self.__populate_layout()
        return self.__layout_dict

    @property
    def signals(self):
        self.__populate_signals()
        return self.__signals

    @property
    def signals_dict(self):
        self.__populate_signals()
        return self.__signals_dict

    @property
    def data(self):
        self.__populate_data()
        return self.__data

    @property
    def data_dict(self):
        self.__populate_data()
        return self.__data_dict

    def __update_inline_property_id(self):
        ui_id = self.ui_id
        object_id = self.object_id
        parent_id = self.parent_id

        if parent_id:
            # Set which parent property makes a reference to this inline object
            row = self.project.db.execute(
                "SELECT property_id FROM object_property WHERE ui_id=? AND inline_object_id=?;", (ui_id, object_id)
            ).fetchone()
            self.inline_property_id = row[0] if row else None

    def __populate_type_properties(self, name):
        property_info = self.project.get_type_properties(name)
        if property_info is None:
            return

        for property_name, info in property_info.items():
            # Check if this property was already installed by a derived class
            if property_name in self.__properties_dict:
                continue

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
            self.__properties.append(prop)

            # Dictionary of properties
            self.__properties_dict[property_name] = prop

    def __populate_properties(self):
        if self.__properties is not None:
            return
        self.__properties = []
        self.__properties_dict = {}

        self.__populate_type_properties(self.type_id)
        for parent_id in self.info.hierarchy:
            self.__populate_type_properties(parent_id)

            # Add accessible properties for GtkWidgets
            if parent_id == "GtkWidget":
                for accessible_id in [
                    "CmbAccessibleProperty",
                    "CmbAccessibleRelation",
                    "CmbAccessibleState",
                    "CmbAccessibleAction"
                ]:
                    self.__populate_type_properties(accessible_id)

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

            self.__layout.append(prop)

            # Dictionary of properties
            self.__layout_dict[property_name] = prop

    def _property_changed(self, prop):
        self.emit("property-changed", prop)
        self.project._object_property_changed(self, prop)

    def _layout_property_changed(self, prop):
        parent = self.project.get_object_by_id(self.ui_id, self.parent_id)
        self.emit("layout-property-changed", parent, prop)
        self.project._object_layout_property_changed(parent, self, prop)

    def __add_signal_object(self, signal):
        self.__populate_signals()
        self.__signals.append(signal)
        self.__signals_dict[signal.signal_pk] = signal
        self.emit("signal-added", signal)
        self.project._object_signal_added(self, signal)

        signal.connect("notify", self.__on_signal_notify)

    def __on_signal_notify(self, signal, pspec):
        self.emit("signal-changed", signal)
        self.project._object_signal_changed(self, signal)

    def __add_data_object(self, data):
        if data.get_id_string() in self.data_dict:
            return

        self.__data.append(data)
        self.__data_dict[data.get_id_string()] = data
        self.emit("data-added", data)
        self.project._object_data_added(self, data)

    def __on_notify(self, obj, pspec):
        if pspec.name == "parent-id":
            self.__populate_layout_properties()

        self.project._object_changed(self, pspec.name)

    def __populate_signals(self):
        if self.__signals is not None:
            return
        self.__signals = []
        self.__signals_dict = {}

        c = self.project.db.cursor()

        # Populate signals
        for row in c.execute("SELECT * FROM object_signal WHERE ui_id=? AND object_id=?;", (self.ui_id, self.object_id)):
            self.__add_signal_object(CmbSignal.from_row(self.project, *row))

    def __populate_data(self):
        if self.__data is not None:
            return
        self.__data = []
        self.__data_dict = {}

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
        self.__layout = []
        self.__layout_dict = {}

        if parent_id > 0:
            parent = self.project.get_object_by_id(self.ui_id, parent_id)
            for owner_id in [parent.type_id] + parent.info.hierarchy:
                self.__populate_layout_properties_from_type(f"{owner_id}LayoutChild")

    def __populate_layout(self):
        if self.__layout is None:
            self.__populate_layout_properties()

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
        new_parent_id = value if value != 0 else None
        old_parent_id = self.parent_id if self.parent_id != 0 else None

        if old_parent_id == new_parent_id:
            return

        # Save old parent and position
        self._save_last_known_parent_and_position()

        project = self.project
        ui_id = self.ui_id
        object_id = self.object_id

        if new_parent_id is None:
            new_position = self.db_get(
                "SELECT MAX(position)+1 FROM object WHERE ui_id=? AND parent_id IS NULL",
                (ui_id, )
            )
        else:
            new_position = self.db_get(
                "SELECT MAX(position)+1 FROM object WHERE ui_id=? AND parent_id=?",
                (ui_id, new_parent_id)
            )

        project.db.execute(
            "UPDATE object SET parent_id=?, position=? WHERE ui_id=? AND object_id=?;",
            (new_parent_id, new_position or 0, ui_id, object_id)
        )

        # Update children positions in old parent
        project.db.update_children_position(ui_id, old_parent_id)

        # Update GListModel
        self._remove_from_old_parent()
        self._update_new_parent()

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
        self.__signals.remove(signal)
        del self.__signals_dict[signal.signal_pk]

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
        if data.get_id_string() not in self.data_dict:
            return

        self.__data.remove(data)
        del self.__data_dict[data.get_id_string()]

        self.emit("data-removed", data)
        self.project._object_data_removed(self, data)

    def remove_data(self, data):
        try:
            assert data.get_id_string() in self.data_dict
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

        old_position = child.position
        old_list_position = child.list_position
        if old_position == position:
            return

        name = child.name if child.name is not None else child.type_id
        self.project.history_push(
            _("Reorder object {name} from position {old} to {new}").format(name=name, old=old_position, new=position)
        )

        db = self.project.db

        # Consider this children
        #
        # label   0
        # button  1
        # entry   2
        # switch  3
        # toggle  4

        # Disable check so we can set position temporally to -1
        db.ignore_check_constraints = True
        db.execute("UPDATE object SET position=-1 WHERE ui_id=? AND object_id=?;", (self.ui_id, child.object_id))

        # Make room for new position
        for select_stmt, update_stmt in [
            (
                """
                SELECT ui_id, object_id
                FROM object
                WHERE ui_id=? AND parent_id=? AND position <= ? AND position > ?
                ORDER BY position ASC
                """,
                "UPDATE object SET position=position - 1 WHERE ui_id=? AND object_id=?;"
            ),
            (
                """
                SELECT ui_id, object_id
                FROM object
                WHERE ui_id=? AND parent_id=? AND position >= ? AND position < ?
                ORDER BY position DESC
                """,
                "UPDATE object SET position=position + 1 WHERE ui_id=? AND object_id=?;"
            ),
        ]:
            for row in db.execute(select_stmt, (self.ui_id, self.object_id, position, old_position)):
                db.execute(update_stmt, tuple(row))

        # Set new position
        db.execute("UPDATE object SET position=? WHERE ui_id=? AND object_id=?;", (position, self.ui_id, child.object_id))

        # Update position layout property (Example GtkBox position in Gtk3)
        if child.position_layout_property:
            db.execute(
                """
                UPDATE object_layout_property AS olp SET value=o.position
                FROM object AS o
                WHERE
                    o.ui_id=? AND
                    o.parent_id=? AND
                    olp.ui_id=o.ui_id AND
                    olp.object_id=o.parent_id AND
                    olp.child_id=o.object_id AND
                    olp.property_id=?;
                """,
                (self.ui_id, self.object_id, child.position_layout_property.property_id)
            )

        db.ignore_check_constraints = False

        list_position = child.list_position

        self.project._ignore_selection = True
        # Emit GListModel signals
        if position < old_position:
            self.items_changed(list_position, 0, 1)
            self.items_changed(old_list_position+1, 1, 0)
        else:
            self.items_changed(old_list_position, 1, 0)
            self.items_changed(list_position, 0, 1)
        self.project._ignore_selection = False

        self.project.history_pop()
        self.emit("child-reordered", child, old_position, position)
        self.project._object_child_reordered(self, child, old_position, position)

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
            prop = self.__properties_dict[prop_id]
            prop.notify("value")
            self._property_changed(prop)

    @GObject.Property(type=str)
    def display_name_type(self):
        return f"{self.type_id} {self.name}" if self.name else self.type_id

    @GObject.Property(type=str)
    def display_name(self):
        name = self.name or ""
        type_id = self.type_id
        parent_id = self.parent_id

        if type_id in [GMENU_SECTION_TYPE, GMENU_SUBMENU_TYPE, GMENU_ITEM_TYPE]:
            prop = self.properties_dict["label"]
            label = prop.value or ""
            display_name = f"{type_id} <i>{label}</i>"
        elif not parent_id and self.ui.template_id == self.object_id:
            # Translators: This is used for Template classes in the object tree
            display_name = _("{name} (template)").format(name=name)
        else:
            inline_prop = self.inline_property_id
            if inline_prop:
                display_name = f"{type_id} <b>{inline_prop}</b> <i>{name}</i>"
            else:
                display_name = f"{type_id} <i>{name}</i>"

        if self.version_warning:
            return f'<span underline="error">{display_name}</span>'
        else:
            return display_name

    def __update_version_warning(self):
        target = self.ui.get_target(self.info.library_id)
        self.version_warning = utils.get_version_warning(target, self.info.version, self.info.deprecated_version, self.type_id)

    def _on_ui_notify(self, obj, pspec):
        property_id = pspec.name

        if property_id == "template-id":
            was_template = self.__is_template
            self.__is_template = obj.template_id == self.object_id

            if was_template or self.__is_template:
                self.notify("display-name")
                self.notify("display-name-type")

    def _on_ui_library_changed(self, ui, library_id):
        self.__update_version_warning()

        self.__populate_properties()
        self.__populate_layout()

        # Update properties directly, to avoid having to connect too many times to this signal
        for props in [self.__properties, self.__layout]:
            for prop in props:
                if prop.library_id == library_id:
                    prop._update_version_warning()

    # GListModel helpers
    def _save_last_known_parent_and_position(self):
        self._last_known = (self.parent, self.list_position)

    def _update_new_parent(self):
        parent = self.parent
        position = self.list_position

        # Emit GListModel signal to update model
        if parent:
            parent.items_changed(position, 0, 1)
            parent.notify("n-items")
        else:
            ui = self.ui
            ui.items_changed(position, 0, 1)
            ui.notify("n-items")

        self._last_known = None

    def _remove_from_old_parent(self):
        if self._last_known is None:
            return

        parent, position = self._last_known

        # Emit GListModel signal to update model
        if parent:
            parent.items_changed(position, 1, 0)
            parent.notify("n-items")
        else:
            ui = self.ui
            ui.items_changed(position, 1, 0)
            ui.notify("n-items")

        self._last_known = None

    @GObject.Property(type=int)
    def list_position(self):
        ui_id = self.ui_id

        if self.parent_id:
            retval = self.db_get(
                """
                SELECT rownum-1
                FROM (
                    SELECT ROW_NUMBER() OVER (ORDER BY position ASC) rownum, object_id
                    FROM object
                    WHERE ui_id=? AND parent_id=?
                )
                WHERE object_id=?;
                """,
                (ui_id, self.parent_id, self.object_id)
            )
        else:
            retval = self.db_get(
                """
                SELECT rownum-1
                FROM (
                    SELECT ROW_NUMBER() OVER (ORDER BY position ASC) rownum, object_id
                    FROM object
                    WHERE ui_id=? AND parent_id IS NULL
                )
                WHERE object_id=?;
                """,
                (ui_id, self.object_id)
            )

        return retval

    # GListModel iface
    def do_get_item(self, position):
        ui_id = self.ui_id

        # This query should use index object_ui_id_parent_id_position_idx
        retval = self.db_get(
            """
            SELECT object_id
            FROM (
                SELECT ROW_NUMBER() OVER (ORDER BY position ASC) rownum, object_id
                FROM object
                WHERE ui_id=? AND parent_id=?
            )
            WHERE rownum=?;
            """,
            (ui_id, self.object_id, position+1)
        )
        if retval is not None:
            return self.project.get_object_by_id(ui_id, retval)

        # This should not happen
        return CmbListError()

    def do_get_item_type(self):
        return CmbBaseObject

    @GObject.Property(type=int)
    def n_items(self):
        if self.project is None:
            return 0

        retval = self.db_get("SELECT COUNT(object_id) FROM object WHERE ui_id=? AND parent_id=?;", (self.ui_id, self.object_id))
        return retval if retval is not None else 0

    def do_get_n_items(self):
        return self.n_items
