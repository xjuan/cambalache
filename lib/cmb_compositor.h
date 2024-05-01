/*
 * Cambalache Wayland Compositor Widget
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

#pragma once

#include <gtk/gtk.h>

#define CMB_COMPOSITOR_TYPE (cmb_compositor_get_type ())
G_DECLARE_FINAL_TYPE (CmbCompositor, cmb_compositor, CMB, COMPOSITOR, GtkDrawingArea)

CmbCompositor *cmb_compositor_new ();
void           cmb_compositor_cleanup (CmbCompositor *object);
void           cmb_compositor_set_bg_color (CmbCompositor *compositor,
                                            gdouble red,
                                            gdouble green,
                                            gdouble blue);
void           cmb_compositor_forget_toplevel_state (CmbCompositor *compositor);
