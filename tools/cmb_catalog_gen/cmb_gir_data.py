#
# CmbGirData - Gir helper
#
# Copyright (C) 2020-2024  Juan Pablo Ugarte
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Authors:
#   Juan Pablo Ugarte <juanpablougarte@gmail.com>
#

import gi
import re
import importlib

# We need to use lxml to get access to nsmap
from lxml import etree
from graphlib import TopologicalSorter, CycleError
from gi.repository import GLib, GObject

CmbCatalogUtils = None

# Global XML name space
nsmap = {}


# Helper function to get a namespaced attribute
def ns(namespace, name):
    return f"{{{nsmap[namespace]}}}{name}"


class CmbGirData:
    def __init__(
        self,
        gir_file,
        libname=None,
        types=None,
        flag_types=None,
        enum_types=None,
        boxed_types=[],
        skip_types=[],
        target_gtk4=False,
        exclude_objects=False,
        external_types=None,
        enable_property_overrides=False,
    ):
        self._instances = {}

        # Supported param specs
        self.pspec_map = {
            "GParamBoolean": "gboolean",
            "GParamChar": "gchar",
            "GParamUChar": "guchar",
            "GParamInt": "gint",
            "GParamUInt": "guint",
            "GParamLong": "glong",
            "GParamULong": "gulong",
            "GParamInt64": "gint64",
            "GParamUInt64": "guint64",
            "GParamFloat": "gfloat",
            "GParamDouble": "gdouble",
            "GParamEnum": "enum",
            "GParamFlags": "flags",
            "GParamString": "gchararray",
            "GParamObject": "object",
            "GParamUnichar": "gunichar",
            "GParamGType": "gtype",
            "GParamBoxed": "boxed",
            "GParamVariant": "variant",
        }

        # GtkBuilder native object types
        self.builder_native_object_types = ["GdkPixbuf", "GFile", "GtkShortcutTrigger", "GtkShortcutAction"]

        tree = etree.parse(gir_file)
        root = tree.getroot()

        # Set global NS map
        global nsmap
        nsmap = root.nsmap

        # Get <namespace/>
        namespace = root.find("namespace", nsmap)

        # Get module/name space data
        self.name = namespace.get("name")
        self.prefix = namespace.get(ns("c", "identifier-prefixes"))
        self.lib = libname
        self.version = namespace.get("version")
        self.shared_library = namespace.get("shared-library")
        self.target_tk = "Gtk-4.0" if target_gtk4 else "Gtk+-3.0"

        self.external_types = external_types if external_types else {}
        self.enable_property_overrides = enable_property_overrides

        self.external_nstypes = {}
        for t in self.external_types:
            self.external_nstypes[self.external_types[t]] = t

        self.ignored_pspecs = set()
        self.ignored_types = set()
        self.ignored_boxed_types = set()

        # Load Module described by gir
        try:
            print(f"Loading {self.name} {self.version}")
            gi.require_version(self.name, self.version)
            self.mod = importlib.import_module(f"gi.repository.{self.name}")

            if hasattr(self.mod, "init"):
                init_function = getattr(self.mod, "init")
                if len(init_function.get_arguments()) == 0:
                    init_function()

        except ValueError as e:
            print(f"Oops! Could not load {self.name} {self.version} module: {e}")

        gi.require_version("CmbCatalogUtils", "4.0" if target_gtk4 else "3.0")

        global CmbCatalogUtils
        from gi.repository import CmbCatalogUtils

        # Dictionary of all enumerations
        self.enumerations = self._get_enumerations(namespace, enum_types)

        # Dictionary of all flags
        self.flags = self._get_flags(namespace, flag_types)

        # Include Boxed types
        self.types = self._get_boxed_types(boxed_types)

        # Dictionary of all interfaces
        self.ifaces = self._get_ifaces(namespace, types, exclude_objects)

        # Dictionary of all classes/types
        obj_types = self._get_types(namespace, types, skip_types, exclude_objects)
        self.types.update(obj_types)

        self._cmb_types_init()

        if target_gtk4:
            self._gtk4_init()
        else:
            self._gtk3_init()

        # Types dependency graph
        types_deps = {}
        for gtype in self.types:
            dep = self.types[gtype]["parent"]
            if dep:
                types_deps[gtype] = {dep}

        # Types in topological order, to avoid FK errors
        try:
            ts = TopologicalSorter(types_deps)
            self.sorted_types = tuple(ts.static_order())
        except CycleError as e:
            raise Exception(f"WEIRD! Found dependency cycle sorting types {e}")

    def _type_is_a(self, type, is_a_type):
        if type == is_a_type:
            return True

        parent = self.types.get(type, None)

        while parent:
            if parent["parent"] == is_a_type:
                return True
            else:
                parent = self.types.get(parent["parent"], None)

        return False

    def _get_instance_from_type(self, name):
        retval = self._instances.get(name, None)

        if retval is not None:
            return retval

        if name.startswith(self.prefix):
            InstanceClass = getattr(self.mod, name[len(self.prefix) :], None)
        else:
            InstanceClass = getattr(self.mod, name, None)

        gtype = GObject.type_from_name(name)
        if InstanceClass is not None and GObject.type_is_a(gtype, GObject.GObject):
            if GObject.type_test_flags(gtype, GObject.TypeFlags.ABSTRACT):
                # Ensure class is instantiable
                class ChildClass(InstanceClass):
                    pass

                if ChildClass is not None:
                    retval = ChildClass()
            else:
                retval = InstanceClass()

        # keep the instance for later
        if retval is not None:
            self._instances[name] = retval

        return retval

    def _container_list_child_properties(self, name):
        instance = self._get_instance_from_type(name)

        if instance is not None:
            props = instance.list_child_properties()
            return props if len(props) > 0 else None

        return None

    def _type_get_properties_overrides(self, name):
        if name == "GObject":
            return []

        class_type = GObject.type_from_name(name)
        parent_type = GObject.type_parent(class_type)
        parent_name = GObject.type_name(parent_type)

        class_interfaces = GObject.type_interfaces(class_type)
        parent_interfaces = GObject.type_interfaces(parent_type)

        instance = self._get_instance_from_type(name)
        if instance is None:
            return []

        parent_instance = self._get_instance_from_type(parent_name)
        retval = []

        for pspec in instance.list_properties():
            writable = pspec.flags & GObject.ParamFlags.WRITABLE
            readable = pspec.flags & GObject.ParamFlags.READABLE
            owner = pspec.owner_type

            # Ignore properties that can not be written or read
            if not writable or not readable:
                continue

            # Object, Boxed and GType params do not have a default value
            if GObject.type_is_a(pspec.value_type, GObject.TYPE_BOXED):
                continue

            if GObject.type_is_a(pspec.value_type, GObject.TYPE_GTYPE):
                continue

            value_type = GObject.type_name(pspec.value_type)
            if GObject.type_is_a(pspec.value_type, GObject.TYPE_OBJECT) and value_type not in self.types:
                continue

            instance_default = getattr(instance.props, pspec.name)
            if pspec.get_default_value() == instance_default:
                continue

            if owner == class_type or (owner in class_interfaces and owner not in parent_interfaces):
                # This is a property declared in this class
                # We need to make sure the default declared in the pspec is the same as the instance
                retval.append(
                    {"property_id": pspec.name, "instance_default": self._get_default_value_from_pspec(pspec, instance_default)}
                )
            else:
                parent_instance_default = getattr(parent_instance.props, pspec.name) if parent_instance else None

                # Ignore GObject properties for now
                # if a subclass sets a parent object property that probably means we should disable it because its being used.
                if GObject.type_is_a(pspec.value_type, GObject.TYPE_OBJECT):
                    if parent_instance_default is None and instance_default is not None:
                        retval.append({"property_id": pspec.name, "non_null_object": True})
                    continue

                if parent_instance_default == instance_default:
                    continue

                retval.append(
                    {"property_id": pspec.name, "new_default": self._get_default_value_from_pspec(pspec, instance_default)}
                )

        return retval

    def _get_default_value_from_pspec(self, pspec, use_instance_default=False, instance_default=None, owner=None):
        if pspec is None:
            return None

        pspec_type_name = GObject.type_name(pspec)
        default_value = instance_default if use_instance_default else pspec.default_value

        if pspec.value_type == GObject.TYPE_BOOLEAN:
            return "True" if default_value != 0 else "False"
        elif GObject.type_is_a(pspec.value_type, GObject.TYPE_ENUM):
            return CmbCatalogUtils.pspec_enum_get_default_nick(pspec.value_type, default_value)
        elif GObject.type_is_a(pspec.value_type, GObject.TYPE_FLAGS):
            return CmbCatalogUtils.pspec_flags_get_default_nick(pspec.value_type, default_value)
        elif GObject.type_is_a(pspec.value_type, GObject.TYPE_GTYPE):
            return GObject.type_name(default_value)
        elif GObject.type_is_a(pspec.value_type, GLib.strv_get_type()):
            return "\n".join(default_value) if default_value and len(default_value) else None
        elif pspec_type_name == "GParamUnichar":
            return default_value

        return default_value

    def _cmb_types_init(self):
        if self.lib not in ["gtk+", "gtk"]:
            return

        extra_types = {}

        # Extra types for Gtk 3 and 4
        extra_types["CmbIconName"] = {"parent": "gchararray"}

        if self.lib == "gtk+":
            extra_types["CmbStockId"] = {"parent": "gchararray"}
        else:
            extra_types["CmbBooleanUndefined"] = {"parent": None}

        self.types.update(extra_types)

    def _gtk3_init(self):
        def get_properties(name, props):
            retval = {}

            if not props:
                return {}

            for pspec in props:
                owner = GObject.type_name(pspec.owner_type)
                type_name = GObject.type_name(pspec.value_type)
                writable = pspec.flags & GObject.ParamFlags.WRITABLE

                if owner != name or type_name.startswith("Gdk") or not writable:
                    continue

                retval[pspec.name] = {
                    "type": type_name,
                    "is_object": "GParamObject" == GObject.type_name(pspec),
                    "version": None,
                    "deprecated_version": None,
                    "construct": 1 if pspec.flags & GObject.ParamFlags.CONSTRUCT_ONLY else None,
                    "default_value": self._get_default_value_from_pspec(pspec),
                    "minimum": pspec.minimum if hasattr(pspec, "minimum") else None,
                    "maximum": pspec.maximum if hasattr(pspec, "maximum") else None,
                }

            return retval

        layout_types = {}

        # Create LayoutChild classes for GtkContainer child properties
        for name in self.types:
            if not self._type_is_a(name, "GtkContainer"):
                continue

            data = self.types[name]

            # Mark class as a container type
            data["layout"] = "container"
            props = self._container_list_child_properties(name)
            properties = get_properties(name, props)

            if len(properties) > 0:
                layout_types[f"{name}LayoutChild"] = {
                    "parent": "GObject",
                    "layout": "child",
                    "properties": properties,
                    "abstract": 1,
                }

        self.types.update(layout_types)

        # Remove Accessible derived classes
        toremove = []
        for name in self.types:
            if self._type_is_a(name, "GtkAccessible"):
                toremove.append(name)

        for key in toremove:
            del self.types[key]

    def _gtk4_init(self):
        # Mark Layout classes
        for name in self.types:
            data = self.types[name]

            if self._type_is_a(name, "GtkLayoutManager"):
                data["layout"] = "manager"
            elif self._type_is_a(name, "GtkLayoutChild"):
                data["layout"] = "child"

        # Accessibility support
        # Map GtkAccessibleProperty, GtkAccessibleRelation and GtkAccessibleState to Cmb prefixed types and properties
        accessible_types = {}

        # Dupe Enums that need an extra undefined value
        for enum_name, member_name, values in [
            ("Orientation", "ORIENTATION", [
                (None, "undefined", "Value is undefined"),
                (0, "horizontal", "The element is in horizontal orientation."),
                (1, "vertical", "The element is in vertical orientation.")
            ]),
            ("AccessibleTristate", "ACCESSIBLE_TRISTATE", [
                (None, "undefined", "Value is undefined"),
                (0, "false", "The state is false."),
                (1, "true", "The state is true."),
                (2, "mixed", "The state is mixed.")
            ])
        ]:
            # members = {}
            # for val, nick, doc in values:
            #     members[f"CMB_{member_name}_UNDEFINED"] = {"value": val, "nick": nick, "doc": doc}

            self.enumerations[f"Cmb{enum_name}Undefined"] = {
                "parent": "enum",
                "members": {f"CMB_{member_name}_{n.upper()}": {"value": v, "nick": n, "doc": d} for (v, n, d) in values}
            }

        # Property name: (type, default value, since version)
        accessible_attr = {
            "Property": {
                "autocomplete": ["GtkAccessibleAutocomplete", "none", None],
                "description": ["gchararray", None, None],
                "has-popup": ["gboolean", "False", None],
                "key-shortcuts": ["gchararray", None, None],
                "label": ["gchararray", None, None],
                "level": ["gint64", 0, None],
                "modal": ["gboolean", "False", None],
                "multi-line": ["gboolean", "False", None],
                "multi-selectable": ["gboolean", "False", None],
                "orientation": ["CmbOrientationUndefined", "undefined", None],  # Undefined default undefined
                "placeholder": ["gchararray", None, None],
                "read-only": ["gboolean", "False", None],
                "required": ["gboolean", "False", None],
                "role-description": ["gchararray", None, None],
                "sort": ["GtkAccessibleSort", "none", None],
                "value-max": ["gdouble", 0, None],
                "value-min": ["gdouble", 0, None],
                "value-now": ["gdouble", 0, None],
                "value-text": ["gchararray", None, None],
                "help-text": ["gchararray", None, None],
            },
            "Relation": {
                "active-descendant": ["GtkAccessible", None, None],
                "col-count": ["gint64", 0, None],
                "col-index": ["gint64", 0, None],
                "col-index-text": ["gchararray", None, None],
                "col-span": ["gint64", 0, None],
                "controls": ["GtkAccessible", None, None],  # Reference List
                "described-by": ["GtkAccessible", None, None],  # Reference List
                "details": ["GtkAccessible", None, None],  # Reference List
                "error-message": ["GtkAccessible", None, None],
                "flow-to": ["GtkAccessible", None, None],  # Reference List
                "labelled-by": ["GtkAccessible", None, None],  # Reference List
                "owns": ["GtkAccessible", None, None],  # Reference List
                "pos-in-set": ["gint64", 0, None],
                "row-count": ["gint64", 0, None],
                "row-index": ["gint64", 0, None],
                "row-index-text": ["gchararray", None, None],
                "row-span": ["gint64", 0, None],
                "set-size": ["gint64", 0, None],
            },
            "State": {
                "busy": ["gboolean", "False", None],
                "checked": ["CmbAccessibleTristateUndefined", "undefined", None],
                "disabled": ["gboolean", "False", None],
                "expanded": ["CmbBooleanUndefined", "undefined", None],  # Undefined
                "hidden": ["gboolean", "False", None],
                "invalid": ["GtkAccessibleInvalidState", "false", None],
                "pressed": ["CmbAccessibleTristateUndefined", "undefined", None],
                "selected": ["CmbBooleanUndefined", "undefined", None],  # Undefined
                "visited": ["CmbBooleanUndefined", "undefined", "4.12"],  # Undefined
            }
        }

        # Create a custom interface for each Accessibility enumeration
        for enumeration in ["Property", "Relation", "State"]:
            data = self.enumerations[f"GtkAccessible{enumeration}"]

            attr = accessible_attr[enumeration]

            # Generate a list of properties for each enumeration member
            properties = {}
            for member in data["members"].values():
                nick = member["nick"]

                if nick not in attr:
                    doc = member["doc"]
                    print(f"Missing type value for {enumeration}:{nick} {doc}")
                    continue

                type_name, default_value, since_version = attr[nick]

                # Add property to list with prefix to avoid name clashes
                properties[f"cmb-a11y-{enumeration.lower()}-{nick}"] = {
                    "type": type_name,
                    "is_object": type_name == "GtkAccessible",
                    "disable_inline_object": type_name == "GtkAccessible",
                    "default_value": default_value,
                    "version": since_version,
                    "deprecated_version": None,
                    "construct": None,
                    "translatable": type_name == "gchararray",
                }

            # Add custom interface type
            accessible_types[f"CmbAccessible{enumeration}"] = {
                "parent": "interface",
                "properties": properties,
            }

        # Add all accessible types
        self.types.update(accessible_types)

    def _type_get_properties(self, element, props, owner=None):
        retval = {}
        pspecs = {}

        if props is not None:
            for p in props:
                pspecs[p.name] = p

        for child in element.iterfind("property", nsmap):
            if child.get("writable") != "1":
                continue

            name = child.get("name")
            type_node = child.find("type", nsmap)

            # <type> might be inside an <array>
            if type_node is None:
                type_node = child.find("array", nsmap)

            if type_node is None:
                continue

            # Property pspec
            pspec = pspecs.get(name, None)

            pspec_type_name = GObject.type_name(pspec) if pspec else None

            type_name = self.pspec_map.get(pspec_type_name, None)
            if type_name is None:
                self.ignored_pspecs.add(pspec_type_name)
                self.ignored_types.add(type_name)
                continue

            is_object = type_name == "object"
            if type_name == "object" or type_name == "enum" or type_name == "flags":
                type_name = type_node.get("name", "GObject")

                if type_name.find(".") >= 0:
                    nstype_name = self.external_types.get(type_name, None)

                    if nstype_name is None:
                        self.ignored_types.add(type_name)
                        continue

                    type_name = nstype_name
                elif type_name != "GObject":
                    type_name = self.prefix + type_name
            elif type_name == "boxed":
                type_name = GObject.type_name(pspec.value_type)

                if type_name not in self.external_nstypes:
                    self.ignored_boxed_types.add(type_name)
                    continue

            retval[name] = {
                "type": type_name,
                "is_object": is_object,
                "version": child.get("version"),
                "deprecated_version": child.get("deprecated-version"),
                "construct": child.get("construct-only"),
                "default_value": self._get_default_value_from_pspec(pspec, owner=owner),
                "minimum": pspec.minimum if hasattr(pspec, "minimum") else None,
                "maximum": pspec.maximum if hasattr(pspec, "maximum") else None,
            }

        return retval

    def _type_get_signals(self, element):
        retval = {}

        for child in element.iterfind(ns("glib", "signal")):
            name = child.get("name").replace("_", "-")
            retval[name] = {
                "version": child.get("version"),
                "deprecated_version": child.get("deprecated-version"),
                "detailed": child.get("detailed"),
            }

        return retval

    def _type_get_interfaces(self, element):
        retval = []

        for child in element.iterfind("implements", nsmap):
            name = child.get("name")
            if name.find(".") < 0:
                retval.append(self.prefix + name)
            elif name in self.external_types:
                retval.append(self.external_types[name])

        return retval

    def _get_type_data(self, element, name, use_instance=True, skip_types=[]):
        parent = element.get("parent")

        if parent and parent.find(".") < 0:
            parent = self.prefix + parent
        elif parent is None:
            parent = "object"
        else:
            parent = self.external_types.get(parent, "GObject")

        # Get version and deprecated-version from constructor if possible
        constructor = element.find("constructor", nsmap)
        if constructor is None:
            constructor = element

        is_container = False
        overrides = None

        nons_name = name.removeprefix(self.prefix)
        GObject.type_ensure(getattr(self.mod, nons_name).__gtype__)
        props = CmbCatalogUtils.get_class_properties(name)

        if use_instance:
            instance = self._get_instance_from_type(name)
            if instance is not None:
                is_container = CmbCatalogUtils.implements_buildable_add_child(instance)
                if self.enable_property_overrides and parent not in skip_types:
                    overrides = self._type_get_properties_overrides(name)

        return {
            "parent": parent,
            "layout": "container" if is_container else None,
            "abstract": element.get("abstract"),
            "derivable": True if element.get(ns("glib", "type-struct")) else None,
            "version": constructor.get("version"),
            "deprecated_version": constructor.get("deprecated-version"),
            "properties": self._type_get_properties(element, props, owner=name),
            "signals": self._type_get_signals(element),
            "interfaces": self._type_get_interfaces(element),
            "overrides": overrides,
        }

    def _get_boxed_types(self, boxed_types=[]):
        retval = {}

        for name in boxed_types:
            retval[name] = {
                "parent": "boxed",
                "abstract": 0,
            }

        return retval

    def _get_types(self, namespace, types=None, skip_types=[], exclude_objects=False):
        retval = {}

        for child in namespace.iterfind("class", nsmap):
            name = child.get(ns("glib", "type-name"))

            if name is None or (exclude_objects and types is None):
                continue

            if types is None or name in types:
                data = self._get_type_data(child, name, name not in skip_types, skip_types=skip_types)
                if name and data is not None:
                    retval[name] = data

        return retval

    def _get_enumerations(self, namespace, types=None):
        retval = {}

        for child in namespace.iterfind("enumeration", nsmap):
            name = child.get(ns("glib", "type-name"))
            if name and (types is None or name in types):
                retval[name] = {"parent": "enum", "members": self._enum_flags_get_members(child)}

        return retval

    def _enum_flags_get_members(self, element):
        retval = {}

        for child in element.iterfind("member", nsmap):
            doc = child.find("doc", nsmap)
            doc_text = None

            if doc is not None:
                doc_text = " ".join(doc.text.split())

            # GLib uses the C identifier as the enum/flag name
            retval[child.get(ns("c", "identifier"))] = {
                "value": child.get("value"),
                "nick": child.get(ns("glib", "nick")),
                "doc": doc_text,
            }

        return retval

    def _get_flags(self, namespace, types=None):
        retval = {}

        for child in namespace.iterfind("bitfield", nsmap):
            name = child.get(ns("glib", "type-name"))
            if name and (types is None or name in types):
                retval[name] = {"parent": "flags", "members": self._enum_flags_get_members(child)}

        return retval

    def _get_ifaces(self, namespace, types=None, exclude_objects=False):
        retval = {}

        for child in namespace.iterfind("interface", nsmap):
            name = child.get(ns("glib", "type-name"))

            if name is None or (exclude_objects and types is None):
                continue

            if types is None or name in types:
                # NOTE: this method is needed because
                # g_object_interface_list_properties bindings do not work
                props = CmbCatalogUtils.get_iface_properties(name)

                retval[name] = {
                    "parent": "interface",
                    "version": child.get("version"),
                    "deprecated_version": child.get("deprecated-version"),
                    "properties": self._type_get_properties(child, props),
                    "signals": self._type_get_signals(child),
                }

        return retval

    def populate_db(self, conn):
        def major_minor_from_string(string):
            if string is None:
                return (0, 0)

            tokens = string.split(".")

            major = int(tokens[0])
            minor = int(tokens[1]) if len(tokens) > 1 else 0

            return (major, minor)

        mod_major, mod_minor = major_minor_from_string(self.version)

        def clean_ver(version):
            major, minor = major_minor_from_string(version)
            return version if major >= mod_major else None

        def db_insert_enum_flags(conn, name, data):
            parent = data.get("parent", None)
            conn.execute("INSERT INTO type (library_id, type_id, parent_id) VALUES (?, ?, ?);", (self.lib, name, parent))

            members = data.get("members", [])
            for member in members:
                m = members[member]
                conn.execute(
                    f"INSERT INTO type_{parent} (type_id, name, value, nick, doc) VALUES (?, ?, ?, ?, ?);",
                    (name, member, m["value"], m["nick"], m["doc"]),
                )

        def db_insert_iface(conn, name, data):
            parent = data.get("parent", None)
            conn.execute("INSERT INTO type (library_id, type_id, parent_id) VALUES (?, ?, ?);", (self.lib, name, parent))

        def db_insert_type(conn, name, data):
            parent = data.get("parent", None)

            if parent and parent.find(".") >= 0:
                parent = "object"

            conn.execute(
                """
                INSERT INTO type (library_id, type_id, parent_id, version, deprecated_version, abstract, derivable, layout)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    self.lib,
                    name,
                    parent,
                    clean_ver(data.get("version", None)),
                    clean_ver(data.get("deprecated_version", None)),
                    data.get("abstract", None),
                    data.get("derivable", None),
                    data.get("layout", None),
                ),
            )

        def db_insert_type_data(conn, name, data):
            properties = data.get("properties", [])
            for prop in properties:
                p = properties[prop]
                prop_type = p["type"]

                # Ignore unknown types (Probably GBoxed)
                if (
                    prop_type.startswith(self.name)
                    and prop_type not in self.types
                    and prop_type not in self.flags
                    and prop_type not in self.enumerations
                    and prop_type not in self.ifaces
                ):
                    continue

                conn.execute(
                    """
                    INSERT INTO property (owner_id, property_id, type_id, is_object, construct_only, default_value, minimum,
                                          maximum, version, deprecated_version, disable_inline_object, translatable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        name,
                        prop,
                        prop_type,
                        p["is_object"] if prop_type not in self.builder_native_object_types else False,
                        p["construct"],
                        p.get("default_value", None),
                        p.get("minimum", None),
                        p.get("maximum", None),
                        clean_ver(p["version"]),
                        clean_ver(p["deprecated_version"]),
                        p.get("disable_inline_object", None),
                        p.get("translatable", None),
                    ),
                )

            signals = data.get("signals", {})
            for signal in signals:
                s = signals[signal]
                conn.execute(
                    "INSERT INTO signal (owner_id, signal_id, version, deprecated_version, detailed) VALUES (?, ?, ?, ?, ?);",
                    (name, signal, clean_ver(s["version"]), clean_ver(s["deprecated_version"]), s["detailed"]),
                )

            for iface in data.get("interfaces", []):
                conn.execute("INSERT INTO type_iface (type_id, iface_id) VALUES (?, ?);", (name, iface))

        # Import library
        conn.execute(
            "INSERT INTO library (library_id, version, namespace, prefix, shared_library) VALUES (?, ?, ?, ?, ?);",
            (self.lib, self.version, self.name, self.prefix, self.shared_library),
        )

        # Import ifaces
        for name in self.ifaces:
            db_insert_iface(conn, name, self.ifaces[name])

        # Import enumeration
        for name in self.enumerations:
            db_insert_enum_flags(conn, name, self.enumerations[name])

        # Import bitfield
        for name in self.flags:
            db_insert_enum_flags(conn, name, self.flags[name])

        # Import types in topological order
        for name in self.sorted_types:
            if name not in self.types:
                continue
            db_insert_type(conn, name, self.types[name])

        # Now insert type data (properties, signals, etc)
        for name in self.sorted_types:
            if name not in self.types:
                continue
            db_insert_type_data(conn, name, self.types[name])

        # Now insert iface data (properties, signals, etc)
        for name in self.ifaces:
            db_insert_type_data(conn, name, self.ifaces[name])

        # Get versions from all types, properties and signal of this library
        versions = [(mod_major, mod_minor)]
        for row in conn.execute(
            """
            SELECT version FROM type WHERE version IS NOT NULL AND library_id=?
            UNION
            SELECT p.version
            FROM property AS p, type AS t WHERE p.version IS NOT NULL AND p.owner_id = t.type_id AND t.library_id=?
            UNION
            SELECT s.version
            FROM signal AS s, type AS t WHERE s.version IS NOT NULL AND s.owner_id = t.type_id AND t.library_id=?;
            """,
            (self.lib, self.lib, self.lib),
        ):
            major, minor = major_minor_from_string(row[0])

            if major >= mod_major:
                versions.append((major, minor))

        versions = sorted(list(dict.fromkeys(versions)))

        # Save target versions
        for major, minor in versions:
            conn.execute("INSERT INTO library_version (library_id, version) VALUES (?, ?);", (self.lib, f"{major}.{minor}"))
