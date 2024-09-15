/*
 * CmbPrivate - Private utility functions
 *
 * Copyright (C) 2022-2024 Juan Pablo Ugarte.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation;
 * version 2.1 of the License.
 *
 * library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
 *
 * Authors:
 *   Juan Pablo Ugarte <juanpablougarte@gmail.com>
 *
 * SPDX-License-Identifier: LGPL-2.1-only
 *
 */

#pragma once

#include <gtk/gtk.h>

G_BEGIN_DECLS

#if GTK_MAJOR_VERSION == 3

void
cmb_private_container_child_set_property_from_string (GtkContainer *container,
                                                      GtkWidget    *child,
                                                      const gchar  *property_name,
                                                      const gchar  *value);
#endif

void
cmb_private_object_set_property_from_string (GObject *object,
                                             const gchar *property_name,
                                             const gchar *value);

void
cmb_private_widget_set_application_id (GtkWidget *widget,
                                       const gchar *app_id);

G_END_DECLS

