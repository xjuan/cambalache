/*
 * CmbPrivate - Private utility functions
 *
 * Copyright (C) 2022-2024 Juan Pablo Ugarte.
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

#include "cmb_private.h"

#if GTK_MAJOR_VERSION == 4
#include <gdk/wayland/gdkwayland.h>
#else
#include <gdk/gdkwayland.h>
#endif


static gboolean
_value_from_string(GParamSpec *pspec, const gchar *string, GValue *value)
{
  static GtkBuilder *builder = NULL;

  if (string == NULL) {
    g_param_value_set_default (pspec, value);
    return TRUE;
  }

  if (builder == NULL)
    builder = gtk_builder_new ();

  return gtk_builder_value_from_string (builder, pspec, string, value, NULL);
}

/**
 * cmb_private_object_set_property_from_string:
 * @object:
 * @property_name:
 * @value: (nullable):
 *
 */
void
cmb_private_object_set_property_from_string (GObject *object,
                                             const gchar *property_name,
                                             const gchar *value)
{
  GParamSpec *pspec = g_object_class_find_property (G_OBJECT_GET_CLASS(object), property_name);
  GValue gvalue = G_VALUE_INIT;

  if (pspec == NULL)
    return;

  if (_value_from_string(pspec, value, &gvalue)) {
    g_object_set_property (object, property_name, &gvalue);
    g_value_unset (&gvalue);
  }
}

/**
 * cmb_private_widget_set_application_id:
 * @widget:
 * @app_id:
 *
 */
void
cmb_private_widget_set_application_id (GtkWidget *widget, const gchar *app_id)
{
  GdkDisplay *display = gtk_widget_get_display(widget);

  if (!GDK_IS_WAYLAND_DISPLAY (display))
    {
      g_warning("%s only work on wayland", __func__);
      return;
    }

#if GTK_MAJOR_VERSION == 4
  GtkNative *native = gtk_widget_get_native(widget);
  GdkSurface *surface = gtk_native_get_surface(native);

  if (surface && GDK_IS_WAYLAND_TOPLEVEL(surface))
    gdk_wayland_toplevel_set_application_id(GDK_WAYLAND_TOPLEVEL(surface),
                                            app_id);
#else
  GdkWindow *window = gtk_widget_get_window(widget);

  if (window)
    gdk_wayland_window_set_application_id(window, app_id);
#endif
}



#if GTK_MAJOR_VERSION == 3

/**
 * cmb_private_container_child_set_property_from_string:
 * @container:
 * @child:
 * @property_name:
 * @value: (nullable):
 *
 */
void
cmb_private_container_child_set_property_from_string (GtkContainer *container,
                                                      GtkWidget    *child,
                                                      const gchar  *property_name,
                                                      const gchar  *value)
{
  GParamSpec *pspec = gtk_container_class_find_child_property (G_OBJECT_GET_CLASS(container), property_name);
  GValue gvalue = G_VALUE_INIT;

  if (pspec == NULL)
    return;

  if (_value_from_string(pspec, value, &gvalue)) {
    gtk_container_child_set_property (container, child, property_name, &gvalue);
    g_value_unset (&gvalue);
  }
}

#endif
