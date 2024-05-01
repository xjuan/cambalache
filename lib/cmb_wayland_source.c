/*
 * Cambalache Wayland GLib Integration
 *
 * Copyright (C) 2024  Juan Pablo Ugarte
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
 */

#include "cmb_wayland_source.h"
#include <wayland-server-core.h>

typedef struct
{
  GSource source;
  struct wl_display *display;
} CmbWaylandSource;

#define CMB_WAYLAND_SOURCE(s) ((CmbWaylandSource *)s)

static gboolean
cmb_wayland_source_prepare (GSource *base, int *timeout)
{
  CmbWaylandSource *source = CMB_WAYLAND_SOURCE(base);

  *timeout = -1;

  wl_display_flush_clients (source->display);

  return FALSE;
}

static gboolean
cmb_wayland_source_check (GSource *base)
{
  CmbWaylandSource *source = CMB_WAYLAND_SOURCE(base);
  struct wl_event_loop *loop = wl_display_get_event_loop (source->display);

  /* Since there is no way to know if there are idle source, dispatch them! */
  wl_event_loop_dispatch_idle (loop);

  return FALSE;
}


static gboolean
cmb_wayland_source_dispatch (GSource *base,
                             GSourceFunc callback,
                             void *data)
{
  CmbWaylandSource *source = CMB_WAYLAND_SOURCE(base);
  struct wl_event_loop *loop = wl_display_get_event_loop (source->display);

  wl_event_loop_dispatch (loop, 0);

  return TRUE;
}


static GSourceFuncs cmb_wayland_source_funcs =
{
  cmb_wayland_source_prepare,
  cmb_wayland_source_check,
  cmb_wayland_source_dispatch,
  NULL
};


GSource *
cmb_wayland_source_new (struct wl_display *display)
{
  struct wl_event_loop *loop = wl_display_get_event_loop (display);
  GSource *source = g_source_new (&cmb_wayland_source_funcs,
                                  sizeof (CmbWaylandSource));

  CMB_WAYLAND_SOURCE(source)->display = display;

  g_source_add_unix_fd (source,
                        wl_event_loop_get_fd (loop),
                        G_IO_IN | G_IO_ERR);

  return source;
}
