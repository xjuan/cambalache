/*
 * CmbCatalogUtils - cmb-catalog-gen utility functions
 *
 * Copyright (C) 2021-2024 Juan Pablo Ugarte.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; version 2 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * Authors:
 *   Juan Pablo Ugarte <juanpablougarte@gmail.com>
 */

#pragma once

#include <gtk/gtk.h>

G_BEGIN_DECLS

GParamSpec **cmb_catalog_utils_get_class_properties(const gchar *name);
GParamSpec **cmb_catalog_utils_get_iface_properties(const gchar *name);

gboolean cmb_catalog_utils_implements_buildable_add_child(GObject *buildable);

const gchar *cmb_catalog_utils_pspec_enum_get_default_nick (GType gtype, gint default_value);

gchar *cmb_catalog_utils_pspec_flags_get_default_nick (GType gtype, guint default_value);

#if GTK_MAJOR_VERSION == 3
gchar *cmb_catalog_utils_a11y_action_get_name (AtkObject *accessible);
#endif

G_END_DECLS
