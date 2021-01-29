# THIS FILE IS AUTOGENERATED, DO NOT EDIT!!!
#
# Cambalache Base Object wrappers
#
# Copyright (C) 2021  Juan Pablo Ugarte - All Rights Reserved
#
# Unauthorized copying of this file, via any medium is strictly prohibited.
#

import gi
from gi.repository import GObject


class CmbPropertyInfo(GObject.GObject):
    owner_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    property_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    type_id = GObject.Property(type=str)
    writable = GObject.Property(type=bool, default = False)
    construct_only = GObject.Property(type=bool, default = False)
    default_value = GObject.Property(type=str)
    version = GObject.Property(type=str)
    deprecated_version = GObject.Property(type=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class CmbSignalInfo(GObject.GObject):
    owner_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    signal_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    version = GObject.Property(type=str)
    deprecated_version = GObject.Property(type=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class CmbBaseTypeInfo(GObject.GObject):
    type_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    parent_id = GObject.Property(type=str)
    library_id = GObject.Property(type=str)
    get_type = GObject.Property(type=str)
    version = GObject.Property(type=str)
    deprecated_version = GObject.Property(type=str)
    abstract = GObject.Property(type=bool, default = False)
    layout = GObject.Property(type=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class CmbBaseUI(GObject.GObject):
    ui_id = GObject.Property(type=int, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    template_id = GObject.Property(type=int)
    name = GObject.Property(type=str)
    filename = GObject.Property(type=str)
    description = GObject.Property(type=str)
    copyright = GObject.Property(type=str)
    authors = GObject.Property(type=str)
    license_id = GObject.Property(type=str)
    translation_domain = GObject.Property(type=str)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class CmbProperty(GObject.GObject):
    ui_id = GObject.Property(type=int, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    object_id = GObject.Property(type=int, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    owner_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    property_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    value = GObject.Property(type=str)
    translatable = GObject.Property(type=bool, default = False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class CmbLayoutProperty(GObject.GObject):
    ui_id = GObject.Property(type=int, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    object_id = GObject.Property(type=int, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    child_id = GObject.Property(type=int, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    owner_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    property_id = GObject.Property(type=str, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    value = GObject.Property(type=str)
    translatable = GObject.Property(type=bool, default = False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class CmbSignal(GObject.GObject):
    ui_id = GObject.Property(type=int)
    object_id = GObject.Property(type=int)
    owner_id = GObject.Property(type=str)
    signal_id = GObject.Property(type=str)
    handler = GObject.Property(type=str)
    detail = GObject.Property(type=str)
    user_data = GObject.Property(type=int)
    swap = GObject.Property(type=bool, default = False)
    after = GObject.Property(type=bool, default = False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class CmbBaseObject(GObject.GObject):
    ui_id = GObject.Property(type=int, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    object_id = GObject.Property(type=int, flags = GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)
    type_id = GObject.Property(type=str)
    name = GObject.Property(type=str)
    parent_id = GObject.Property(type=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
