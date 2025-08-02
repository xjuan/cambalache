# Cambalache Property Controls
#
# Copyright (C) 2021-2023  Juan Pablo Ugarte
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
import math

from gi.repository import GLib, Gtk
from .cmb_boolean_undefined import CmbBooleanUndefined
from .cmb_entry import CmbEntry
from .cmb_file_entry import CmbFileEntry
from .cmb_icon_name_entry import CmbIconNameEntry
from .cmb_pixbuf_entry import CmbPixbufEntry
from .cmb_spin_button import CmbSpinButton
from .cmb_color_entry import CmbColorEntry
from .cmb_enum_combo_box import CmbEnumComboBox
from .cmb_flags_entry import CmbFlagsEntry
from .cmb_object_chooser import CmbObjectChooser
from .cmb_object_list_editor import CmbObjectListEditor
from .cmb_switch import CmbSwitch
from .cmb_text_view import CmbTextView
from .cmb_suggestion_entry import CmbSuggestionEntry


def cmb_create_editor(project, type_id, prop=None, data=None, parent=None):
    def get_min_max_for_type(type_id):
        if type_id == "gchar":
            return (GLib.MININT8, GLib.MAXINT8)
        elif type_id == "guchar":
            return (0, GLib.MAXUINT8)
        elif type_id == "gint":
            return (GLib.MININT, GLib.MAXINT)
        elif type_id == "guint":
            return (0, GLib.MAXUINT)
        elif type_id == "glong":
            return (GLib.MINLONG, GLib.MAXLONG)
        elif type_id == "gulong":
            return (0, GLib.MAXULONG)
        elif type_id == "gint64":
            return (GLib.MININT64, GLib.MAXINT64)
        elif type_id == "guint64":
            return (0, GLib.MAXUINT64)
        elif type_id == "gfloat":
            return (-GLib.MAXFLOAT, GLib.MAXFLOAT)
        elif type_id == "gdouble":
            return (-GLib.MAXDOUBLE, GLib.MAXDOUBLE)

    def get_dirname():
        if project.filename:
            return os.path.dirname(project.filename)
        else:
            return os.getcwd()

    editor = None
    info = project.type_info.get(type_id, None)

    if prop:
        translatable = prop.info.translatable
    elif data:
        translatable = data.info.translatable
    else:
        translatable = False

    if type_id == "gboolean":
        editor = CmbSwitch()
    if type_id == "gunichar":
        editor = CmbEntry(hexpand=True, max_length=1, placeholder_text=f"<{type_id}>")
    elif (
        type_id == "gchar"
        or type_id == "guchar"
        or type_id == "gint"
        or type_id == "guint"
        or type_id == "glong"
        or type_id == "gulong"
        or type_id == "gint64"
        or type_id == "guint64"
        or type_id == "gfloat"
        or type_id == "gdouble"
    ):
        digits = 0
        step_increment = 1
        minimum, maximum = get_min_max_for_type(type_id)

        pinfo = prop.info if prop else None

        # FIXME: is there a better way to handle inf -inf values other
        # than casting to str?
        if pinfo and pinfo.minimum is not None:
            value = float(minimum)
            minimum = value if value != -math.inf else -GLib.MAXDOUBLE
        if pinfo and pinfo.maximum is not None:
            value = float(maximum)
            maximum = value if value != math.inf else GLib.MAXDOUBLE

        if type_id == "gfloat" or type_id == "gdouble":
            digits = 4
            step_increment = 0.1

        adjustment = Gtk.Adjustment(lower=minimum, upper=maximum, step_increment=step_increment, page_increment=10)

        editor = CmbSpinButton(digits=digits, adjustment=adjustment)
    elif type_id == "GBytes":
        editor = CmbTextView(hexpand=True)
    elif type_id == "GStrv":
        editor = CmbTextView(hexpand=True)
    elif type_id == "GdkRGBA":
        editor = CmbColorEntry()
    elif type_id == "GdkColor":
        editor = CmbColorEntry(use_color=True)
    elif type_id == "GdkPixbuf":
        editor = CmbPixbufEntry(hexpand=True, dirname=get_dirname())
    elif type_id == "GFile":
        editor = CmbFileEntry(hexpand=True, dirname=get_dirname())
    elif type_id == "CmbIconName":
        editor = CmbIconNameEntry(hexpand=True, placeholder_text="<Icon Name>")
    elif type_id in ["GtkShortcutTrigger", "GtkShortcutAction"]:
        editor = CmbEntry(hexpand=True, placeholder_text=f"<{type_id}>")
    elif type_id == "CmbBooleanUndefined":
        editor = CmbBooleanUndefined()
    elif type_id == "CmbAccessibleList":
        editor = CmbObjectListEditor(
            parent=prop.object if prop else parent,
            type_id="GtkAccessible",
        )
    elif type_id == "gtype":
        editor = CmbSuggestionEntry()
        editor.set_suggestions(project._get_types())
    elif info:
        if info.is_object or info.parent_id == "interface" or type_id == "GtkExpression":
            if prop is None:
                editor = CmbObjectChooser(
                    parent=parent,
                    type_id=type_id,
                )
            else:
                editor = CmbObjectChooser(
                    parent=prop.object,
                    is_inline=project.target_tk == "gtk-4.0" and not prop.info.disable_inline_object,
                    inline_object_id=prop.inline_object_id,
                    inline_property_id=prop.property_id,
                    type_id=type_id,
                )
        elif info.parent_id == "enum":
            editor = CmbEnumComboBox(info=info)
        elif info.parent_id == "flags":
            editor = CmbFlagsEntry(info=info)

    if editor is None:
        editor = CmbEntry(hexpand=True, placeholder_text=f"<{type_id}>")
        if translatable:
            target = prop if prop else data
            if target:
                editor.make_translatable(target=target)

    editor.show()

    return editor
