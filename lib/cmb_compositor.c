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

#define WLR_USE_UNSTABLE 1

#include "cmb_compositor.h"
#include "cmb_wayland_source.h"
#include <linux/input-event-codes.h>
#include <wayland-server-core.h>
#include <wlr/backend.h>
#include <wlr/backend/interface.h>
#include <wlr/interfaces/wlr_keyboard.h>
#include <wlr/interfaces/wlr_output.h>
#include <wlr/interfaces/wlr_pointer.h>
#include <wlr/render/allocator.h>
#include <wlr/render/pixman.h>
#include <wlr/render/wlr_renderer.h>
#include <wlr/render/wlr_texture.h>
#include <wlr/types/wlr_compositor.h>
#include <wlr/types/wlr_data_device.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_output_layer.h>
#include <wlr/types/wlr_pointer.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/types/wlr_subcompositor.h>
#include <wlr/types/wlr_xcursor_manager.h>
#include <wlr/types/wlr_xdg_activation_v1.h>
#include <wlr/types/wlr_xdg_shell.h>
#include "xdg-shell-protocol.h"
#include <xkbcommon/xkbcommon.h>

#ifdef GDK_WINDOWING_WAYLAND
#include <gdk/wayland/gdkwayland.h>
#endif

#ifdef GDK_WINDOWING_X11
#include <gdk/x11/gdkx.h>
#include <X11/Xlib-xcb.h>
#include <xkbcommon/xkbcommon-x11.h>
#endif

/* Auto free helpers */
typedef struct wlr_texture WlrTexture;
typedef struct wlr_output_state WlrOutputState;
G_DEFINE_AUTOPTR_CLEANUP_FUNC(WlrTexture, wlr_texture_destroy);
G_DEFINE_AUTO_CLEANUP_CLEAR_FUNC(WlrOutputState, wlr_output_state_finish);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(cairo_surface_t, cairo_surface_destroy);
G_DEFINE_AUTOPTR_CLEANUP_FUNC(pixman_image_t, pixman_image_unref);

typedef enum
{
  CMB_POINTER_MODE_FOWARD,
  CMB_POINTER_MODE_RESIZE,
  CMB_POINTER_MODE_MOVE,
} CmbPointerMode;

typedef struct CmbCompositorToplevel CmbCompositorToplevel;

typedef struct
{
  GtkWidget *widget;

  /* wayland main loop integration */
  GSource *wl_source;

  /* Event controllers */
  GtkEventController *motion_controller;
  GtkEventController *scroll_controller;
  GtkEventController *key_controller;
  GtkGesture *click_gesture;

  /* Frame Clock state */
  GdkFrameClock *frame_clock;
  gboolean frame_clock_updating;
  gulong frame_clock_source;
  guint defered_present_event_source;
  struct wlr_output_event_present defered_present_event;

  /* Wayland display */
  struct wl_display *wl_display;

  /* wlroots objects */
  struct wlr_renderer *renderer;
  struct wlr_allocator *allocator;
  struct wlr_scene *scene;
  struct wlr_scene_output *scene_output;
  struct wlr_scene_rect *bg;

  /* Custom wlr objects */
  struct wlr_keyboard keyboard;
  struct wlr_pointer pointer;
  struct wlr_backend backend;
  struct wlr_output output;

  /* wlr interfaces */
  struct wlr_backend_impl backend_impl;
  struct wlr_output_impl output_impl;

  gboolean backend_started;

  /* XDG shell */
  struct wlr_xdg_shell *xdg_shell;
  struct wl_listener new_xdg_toplevel;
  struct wl_listener new_xdg_popup;
  GList *toplevels;

  /* XDG activation */
  struct wlr_xdg_activation_v1 *xdg_activation;
  struct wl_listener request_activate;

  GHashTable *toplevel_state;

  /* Toplevel resize state */
  gdouble pointer_x, pointer_y; /* Current pointer position */
  CmbCompositorToplevel *grabbed_toplevel;
  CmbPointerMode pointer_mode;
  gdouble grab_x, grab_y;
  struct wlr_box grab_box;
  uint32_t resize_edges;

  /* Virtual Seat */
  struct wlr_seat *seat;
  struct wl_listener request_cursor;
  struct wl_listener request_set_selection;

  struct wl_listener on_frame;
  struct wl_listener on_request_cursor;
  struct wl_listener on_cursor_surface_commit;
  gint hotspot_x;
  gint hotspot_y;
  GdkPixbuf *cursor_gdk_pixbuf;
  GdkTexture *cursor_gdk_texture;
  GdkCursor *cursor_gdk_cursor;

  /* GObject properties */
  gchar *socket;

  gchar *error_message;
  PangoLayout *error_layout;
  gint error_layout_width;
  gint error_layout_height;

} CmbCompositorPrivate;


struct _CmbCompositor
{
  GtkDrawingArea parent;
};


typedef struct
{
  gboolean maximized, fullscreen;
  gint x, y, width, height;
} CmbCompositorToplevelState;


struct CmbCompositorToplevel
{
  CmbCompositorPrivate *priv;
  struct wlr_xdg_toplevel *xdg_toplevel;
  struct wlr_scene_tree *scene_tree;

  CmbCompositorToplevelState old_state;

  /* This points to priv->toplevel_state[app_id] */
  CmbCompositorToplevelState *state;

  /* Events */
  struct wl_listener map;
  struct wl_listener unmap;
  struct wl_listener commit;
  struct wl_listener destroy;
  struct wl_listener request_move;
  struct wl_listener request_resize;
  struct wl_listener request_maximize;
  struct wl_listener request_fullscreen;
  struct wl_listener set_app_id;
};

typedef struct
{
  struct wlr_xdg_popup *xdg_popup;
  struct wl_listener commit;
  struct wl_listener destroy;
} CmbCompositorPopup;

enum
{
  PROP_0,
  PROP_SOCKET,
  PROP_ERROR_MESSAGE,

  N_PROPERTIES
};

enum
{
  CONTEXT_MENU,

  LAST_SIGNAL
};

static guint compositor_signals[LAST_SIGNAL] = { 0 };

static GParamSpec *properties[N_PROPERTIES];


G_DEFINE_TYPE_WITH_PRIVATE(CmbCompositor, cmb_compositor, GTK_TYPE_DRAWING_AREA);
#define GET_PRIVATE(d) ((CmbCompositorPrivate *) cmb_compositor_get_instance_private((CmbCompositor*)d))


static void cmb_compositor_wlr_init(CmbCompositorPrivate *priv);
static void cmb_compositor_set_error_message(CmbCompositor *compositor,
                                             const gchar   *message);


static cairo_format_t
_cairo_format_from_pixman_format (pixman_format_code_t pixman_format)
{
  switch (pixman_format)
    {
      case PIXMAN_rgba_float:
        return CAIRO_FORMAT_RGBA128F;
      case PIXMAN_rgb_float:
        return CAIRO_FORMAT_RGB96F;
      case PIXMAN_a8r8g8b8:
        return CAIRO_FORMAT_ARGB32;
      case PIXMAN_x2r10g10b10:
        return CAIRO_FORMAT_RGB30;
      case PIXMAN_x8r8g8b8:
        return CAIRO_FORMAT_RGB24;
      case PIXMAN_a8:
        return CAIRO_FORMAT_A8;
      case PIXMAN_a1:
        return CAIRO_FORMAT_A1;
      case PIXMAN_r5g6b5:
        return CAIRO_FORMAT_RGB16_565;
      default:
        return CAIRO_FORMAT_INVALID;
    }

  return CAIRO_FORMAT_INVALID;
}

static void
cmb_compositor_draw (GtkDrawingArea *area,
                     cairo_t        *cr,
                     int             width,
                     int             height,
                     G_GNUC_UNUSED gpointer data)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (area);
  struct wlr_scene_output *scene_output = priv->scene_output;
  g_autoptr(WlrTexture) texture = NULL;
  g_autoptr(cairo_surface_t) surface = NULL;
  pixman_image_t *image = NULL;
  cairo_format_t format;
  struct timespec now;
  g_auto(WlrOutputState) state = {0, };

  if (priv->error_message)
    {
      cairo_move_to (cr,
                     width/2 - priv->error_layout_width/2,
                     height/2 - priv->error_layout_height/2);
      pango_cairo_show_layout (cr, priv->error_layout);
      return;
    }

  wlr_output_state_init(&state);

  if (!wlr_scene_output_build_state(scene_output, &state, NULL))
    return;

  if (!(texture = wlr_texture_from_buffer(priv->renderer, state.buffer)))
    return;

  if (!(image = wlr_pixman_texture_get_image(texture)))
    return;

  format = _cairo_format_from_pixman_format (pixman_image_get_format (image));

  if (format == CAIRO_FORMAT_INVALID)
    return;

  surface = cairo_image_surface_create_for_data((gpointer)pixman_image_get_data (image),
                                                format,
                                                pixman_image_get_width (image),
                                                pixman_image_get_height (image),
                                                pixman_image_get_stride (image));

  /* Use buffer as source and blit */
  cairo_set_source_surface(cr, surface, 0, 0);
  cairo_paint (cr);

  /* TODO: try using a dmabuf
   * https://docs.gtk.org/gdk4/method.DmabufTextureBuilder.set_update_region.html
   */

  wlr_output_commit_state(scene_output->output, &state);

  clock_gettime(CLOCK_MONOTONIC, &now);
  wlr_scene_output_send_frame_done(scene_output, &now);
}

static void
on_cmb_compositor_output_frame(struct wl_listener *listener,
                               G_GNUC_UNUSED void *data)
{
  CmbCompositorPrivate *priv = wl_container_of(listener, priv, on_frame);
  struct wlr_scene_output *scene_output = priv->scene_output;

  if (!scene_output->output->needs_frame && !pixman_region32_not_empty(
      &scene_output->pending_commit_damage))
    {
      if (priv->frame_clock_updating)
        {
          gdk_frame_clock_end_updating(priv->frame_clock);
          priv->frame_clock_updating = FALSE;
        }
     return;
    }

  if (!priv->frame_clock_updating)
    {
      priv->frame_clock_updating = TRUE;
      gdk_frame_clock_begin_updating(priv->frame_clock);
    }

  gtk_widget_queue_draw(priv->widget);
}

static void
cmb_compositor_size_allocate(GtkWidget *widget, int w, int h, int b)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (widget);
  struct wlr_output_state state;

  GTK_WIDGET_CLASS (cmb_compositor_parent_class)->size_allocate (widget, w, h, b);

  /* Update background rectangle size */
  wlr_scene_rect_set_size(priv->bg, w, h);

  wlr_output_state_init(&state);
  wlr_output_state_set_enabled(&state, true);
  wlr_output_state_set_custom_mode(&state, w, h, 0);
  wlr_output_commit_state(&priv->output, &state);
  wlr_output_state_finish(&state);
}

static void
cmb_composite_cursor_handler_remove(CmbCompositorPrivate *priv)
{
  if (priv->on_cursor_surface_commit.link.next)
    {
      wl_list_remove(&priv->on_cursor_surface_commit.link);
      memset(&priv->on_cursor_surface_commit, 0, sizeof(struct wl_listener));
    }
}

static void
cmb_composite_reset_cursor(CmbCompositorPrivate *priv)
{
  if (priv->widget)
    gtk_widget_set_cursor(priv->widget, NULL);

  g_clear_object(&priv->cursor_gdk_cursor);
  g_clear_object(&priv->cursor_gdk_texture);
  g_clear_object(&priv->cursor_gdk_pixbuf);

  cmb_composite_cursor_handler_remove(priv);
}

static void
cmb_compositor_reset_pointer_mode(CmbCompositorPrivate *priv)
{
  priv->pointer_mode = CMB_POINTER_MODE_FOWARD;
  priv->grabbed_toplevel = NULL;
}


static CmbCompositorToplevel *
cmb_compositor_get_toplevel_at_pointer(CmbCompositorPrivate *priv,
                                       struct wlr_surface **surface,
                                       double *sx,
                                       double *sy)
{
  struct wlr_scene_node *node;
  struct wlr_scene_buffer *scene_buffer;
  struct wlr_scene_surface *scene_surface;
  struct wlr_scene_tree *parent;

  if (surface)
    *surface = NULL;

  node = wlr_scene_node_at(&priv->scene->tree.node,
                           priv->pointer_x,
                           priv->pointer_y,
                           sx,
                           sy);

  if (!node || node->type != WLR_SCENE_NODE_BUFFER)
    return NULL;

  if (!(scene_buffer = wlr_scene_buffer_from_node(node)))
    return NULL;

  if (!(scene_surface = wlr_scene_surface_try_from_buffer(scene_buffer)))
    return NULL;

  if (surface)
    *surface = scene_surface->surface;

  parent = node->parent;
  while (parent && !parent->node.data)
    parent = parent->node.parent;

  return parent ? parent->node.data : NULL;
}

static void
cmb_compositor_toplevel_configure(CmbCompositorToplevel *toplevel,
                                  gint x,
                                  gint y,
                                  gint width,
                                  gint height)
{
  wlr_scene_node_set_position(&toplevel->scene_tree->node, x, y);

  if (width && height)
    {
      toplevel->xdg_toplevel->scheduled.width = width;
      toplevel->xdg_toplevel->scheduled.height = height;
      wlr_xdg_surface_schedule_configure(toplevel->xdg_toplevel->base);
    }
}

static void
cmb_compositor_toplevel_save_position(CmbCompositorToplevel *toplevel)
{
  CmbCompositorToplevelState *state = toplevel->state;

  if (!state)
    return;

  /* Get position from scene node */
  state->x = toplevel->scene_tree->node.x;
  state->y = toplevel->scene_tree->node.y;

  g_debug("%s %s %dx%d %dx%d maximized=%d fullscreen=%d",
          __func__,
          toplevel->xdg_toplevel->app_id,
          state->x,
          state->y,
          state->width,
          state->height,
          state->maximized,
          state->fullscreen);
}

static void
cmb_compositor_toplevel_save_size(CmbCompositorToplevel *toplevel,
                                  gint width,
                                  gint height)
{
  CmbCompositorToplevelState *state = toplevel->state;

  if (!state)
    return;

  /* Assign current state from toplevel */
  state->width = width;
  state->height = height;

  g_debug("%s %s %dx%d %dx%d maximized=%d fullscreen=%d",
          __func__,
          toplevel->xdg_toplevel->app_id,
          state->x,
          state->y,
          state->width,
          state->height,
          state->maximized,
          state->fullscreen);
}

void
cmb_compositor_toplevel_toggle_maximize_fullscreen(CmbCompositorToplevel *toplevel,
                                                   gboolean fullscreen)
{
  CmbCompositorPrivate *priv = toplevel->priv;
  struct wlr_xdg_toplevel *xdg_toplevel = toplevel->xdg_toplevel;
  CmbCompositorToplevelState *state = toplevel->state;
  gboolean value;

  if (!xdg_toplevel->base->initialized || !xdg_toplevel->base->configured)
      return;

  if (fullscreen)
    {
      value = xdg_toplevel->requested.fullscreen;
      if (xdg_toplevel->current.fullscreen == value)
        return;

      xdg_toplevel->scheduled.fullscreen = value;

      if (state)
        state->fullscreen = value;
    }
  else
    {
      value = xdg_toplevel->requested.maximized;
      if (xdg_toplevel->current.maximized == value)
        return;

      xdg_toplevel->scheduled.maximized = value;

      if (state)
        state->maximized = value;
    }

  if (value)
    {
      GtkWidget *widget = priv->widget;

      toplevel->old_state.x = toplevel->scene_tree->node.x;
      toplevel->old_state.y = toplevel->scene_tree->node.y;
      toplevel->old_state.width = xdg_toplevel->current.width;
      toplevel->old_state.height = xdg_toplevel->current.height;

      cmb_compositor_toplevel_configure(toplevel,
                                        0, 0,
                                        gtk_widget_get_width(widget),
                                        gtk_widget_get_height(widget));
    }
  else
    {
      cmb_compositor_toplevel_configure(toplevel,
                                        toplevel->old_state.x,
                                        toplevel->old_state.y,
                                        toplevel->old_state.width,
                                        toplevel->old_state.height);
    }
}

static void
cmb_compositor_handle_pointer_resize_toplevel(CmbCompositorPrivate *priv)
{
  CmbCompositorToplevel *toplevel = priv->grabbed_toplevel;
  struct wlr_xdg_toplevel *xdg_toplevel = toplevel->xdg_toplevel;
  struct wlr_box box;
  gint border_x = priv->pointer_x - priv->grab_x;
  gint border_y = priv->pointer_y - priv->grab_y;
  gint new_left = priv->grab_box.x;
  gint new_right = priv->grab_box.x + priv->grab_box.width;
  gint new_top = priv->grab_box.y;
  gint new_bottom = priv->grab_box.y + priv->grab_box.height;
  gint new_width, new_height, min_width, min_height;

  min_width = xdg_toplevel->current.min_width;
  min_height = xdg_toplevel->current.min_height;

  if (priv->resize_edges & WLR_EDGE_TOP)
    {
      new_top = border_y;
      if (new_top >= new_bottom)
        new_top = new_bottom - 1;
    }
  else if (priv->resize_edges & WLR_EDGE_BOTTOM)
    {
      new_bottom = border_y;
      if (new_bottom <= new_top)
        new_bottom = new_top + 1;
    }

  if (priv->resize_edges & WLR_EDGE_LEFT)
    {
      new_left = border_x;
      if (new_left >= new_right)
        new_left = new_right - 1;
    }
  else if (priv->resize_edges & WLR_EDGE_RIGHT)
    {
      new_right = border_x;
      if (new_right <= new_left)
        new_right = new_left + 1;
    }

  new_width = new_right - new_left;
  new_height = new_bottom - new_top;

  if (new_width < min_width && new_height < min_height)
    return;

  if (new_width < min_width)
    {
      if (priv->resize_edges & WLR_EDGE_LEFT)
        new_left -= min_width - new_width;
      new_width = min_width;
    }

  if (new_height < min_height)
    {
      if (priv->resize_edges & WLR_EDGE_TOP)
        new_top -= min_height - new_height;
      new_height = min_height;
    }

  wlr_xdg_surface_get_geometry(toplevel->xdg_toplevel->base, &box);

  wlr_xdg_toplevel_set_size(toplevel->xdg_toplevel, new_width, new_height);

  /* FIXME: we probably need to wait for the new size to be in effect
   * before setting the position
   */
  wlr_scene_node_set_position(&toplevel->scene_tree->node,
                              new_left - box.x,
                              new_top - box.y);

  cmb_compositor_toplevel_save_position(toplevel);
  cmb_compositor_toplevel_save_size(toplevel, new_width, new_height);
}

static void
cmb_compositor_handle_pointer_motion(CmbCompositorPrivate *priv)
{
  if (priv->pointer_mode == CMB_POINTER_MODE_MOVE)
    {
      wlr_scene_node_set_position(&priv->grabbed_toplevel->scene_tree->node,
                                  priv->pointer_x - priv->grab_x,
                                  priv->pointer_y - priv->grab_y);

      cmb_compositor_toplevel_save_position(priv->grabbed_toplevel);
    }
  else if (priv->pointer_mode == CMB_POINTER_MODE_RESIZE)
    {
      cmb_compositor_handle_pointer_resize_toplevel(priv);
    }
  else
    {
      CmbCompositorToplevel *toplevel;
      struct wlr_surface *surface;
      double sx, sy;

      toplevel = cmb_compositor_get_toplevel_at_pointer(priv, &surface, &sx, &sy);

      if (!toplevel)
        cmb_composite_reset_cursor(priv);

      if (surface)
        {
          uint32_t time = gtk_event_controller_get_current_event_time(priv->motion_controller);
          wlr_seat_pointer_notify_enter(priv->seat, surface, sx, sy);
          wlr_seat_pointer_notify_motion(priv->seat, time, sx, sy);
        }
      else
        wlr_seat_pointer_clear_focus(priv->seat);
    }
}

static void
on_motion_controller_enter (G_GNUC_UNUSED GtkEventControllerMotion *self,
                            gdouble x,
                            gdouble y,
                            CmbCompositorPrivate *priv)
{
  priv->pointer_x = x;
  priv->pointer_y = y;
  cmb_compositor_handle_pointer_motion(priv);
  wlr_seat_pointer_notify_frame(priv->seat);
}

static void
on_motion_controller_leave (G_GNUC_UNUSED GtkEventControllerMotion *self,
                            CmbCompositorPrivate *priv)
{
  wlr_seat_pointer_clear_focus(priv->seat);
}

static void
on_motion_controller_motion (G_GNUC_UNUSED GtkEventControllerMotion *self,
                             gdouble x,
                             gdouble y,
                             CmbCompositorPrivate *priv)
{
  priv->pointer_x = x;
  priv->pointer_y = y;
  cmb_compositor_handle_pointer_motion(priv);
  wlr_seat_pointer_notify_frame(priv->seat);
}

static gboolean
on_scroll_controller_scroll (GtkEventControllerScroll *self,
                             gdouble dx,
                             gdouble dy,
                             CmbCompositorPrivate *priv)
{
  uint32_t time_msec = gtk_event_controller_get_current_event_time(GTK_EVENT_CONTROLLER(self));
  gint idx, idy;

  idx = dx * WLR_POINTER_AXIS_DISCRETE_STEP;
  idy = dy * WLR_POINTER_AXIS_DISCRETE_STEP;

  if (idx != 0)
    wlr_seat_pointer_notify_axis(priv->seat,
                                 time_msec,
                                 WL_POINTER_AXIS_HORIZONTAL_SCROLL,
                                 idx,
                                 idx,
                                 WL_POINTER_AXIS_SOURCE_WHEEL,
                                 WL_POINTER_AXIS_RELATIVE_DIRECTION_IDENTICAL);

  if (idy != 0)
    wlr_seat_pointer_notify_axis(priv->seat,
                                 time_msec,
                                 WL_POINTER_AXIS_VERTICAL_SCROLL,
                                 idy,
                                 idy,
                                 WL_POINTER_AXIS_SOURCE_WHEEL,
                                 WL_POINTER_AXIS_RELATIVE_DIRECTION_IDENTICAL);

  wlr_seat_pointer_notify_frame(priv->seat);

  return TRUE;
}

static void
cmb_compositor_focus_toplevel(CmbCompositorToplevel *toplevel,
                              struct wlr_surface    *surface)
{
  CmbCompositorPrivate *priv = toplevel->priv;
  struct wlr_surface *focused_surface = priv->seat->keyboard_state.focused_surface;

  if (focused_surface == surface)
    return;

  if (focused_surface)
    {
      struct wlr_xdg_toplevel *focused_toplevel =
        wlr_xdg_toplevel_try_from_wlr_surface(focused_surface);

      if (focused_toplevel)
        wlr_xdg_toplevel_set_activated(focused_toplevel, false);
    }

  /* Move it to the front */
  wlr_scene_node_raise_to_top(&toplevel->scene_tree->node);
  wlr_xdg_toplevel_set_activated(toplevel->xdg_toplevel, true);

  priv->toplevels = g_list_remove(priv->toplevels, toplevel);
  priv->toplevels = g_list_prepend(priv->toplevels, toplevel);

  wlr_seat_keyboard_notify_enter(priv->seat,
                                 toplevel->xdg_toplevel->base->surface,
                                 priv->keyboard.keycodes,
                                 priv->keyboard.num_keycodes,
                                 &priv->keyboard.modifiers);
}

static void
cmb_compositor_seat_pointer_notify(GtkGestureClick       *self,
                                   CmbCompositorPrivate  *priv,
                                   gint                   button,
                                   enum wl_pointer_button_state state)
{
  uint32_t time_msec, wl_button;
  struct wlr_surface *surface = NULL;
  CmbCompositorToplevel *toplevel;
  double sx, sy;

  button = gtk_gesture_single_get_current_button(GTK_GESTURE_SINGLE(self));

  if (button == 1)
      wl_button = BTN_LEFT;
  else if (button == 2)
      wl_button = BTN_MIDDLE;
  else if (button == 3)
      wl_button = BTN_RIGHT;
  else
    {
      g_message("%s unknown button %u", __func__, button);
      return;
    }

  time_msec = gtk_event_controller_get_current_event_time(GTK_EVENT_CONTROLLER(self));

  wlr_seat_pointer_notify_button(priv->seat, time_msec, wl_button, state);
  wlr_seat_pointer_notify_frame(priv->seat);

  toplevel = cmb_compositor_get_toplevel_at_pointer(priv, &surface, &sx, &sy);

  if (state == WL_POINTER_BUTTON_STATE_RELEASED)
    cmb_compositor_reset_pointer_mode(priv);
  else if (toplevel)
    cmb_compositor_focus_toplevel(toplevel, surface);
}

static void
on_click_gesture_pressed (GtkGestureClick *self,
                          G_GNUC_UNUSED gint n_press,
                          gdouble x,
                          gdouble y,
                          CmbCompositorPrivate *priv)
{
  gint button = gtk_gesture_single_get_current_button(GTK_GESTURE_SINGLE(self));

  gtk_widget_grab_focus (priv->widget);

  if (button == 3)
    {
      g_signal_emit (priv->widget,
                     compositor_signals[CONTEXT_MENU],
                     0,
                     (gint)x,
                     (gint)y);
      return;
    }

  cmb_compositor_seat_pointer_notify(self, priv, button, WL_POINTER_BUTTON_STATE_PRESSED);
}

static void
on_click_gesture_released (GtkGestureClick* self,
                           G_GNUC_UNUSED gint n_press,
                           G_GNUC_UNUSED gdouble x,
                           G_GNUC_UNUSED gdouble y,
                           CmbCompositorPrivate *priv)
{
  gint button = gtk_gesture_single_get_current_button(GTK_GESTURE_SINGLE(self));
  if (button == 3)
    return;

  cmb_compositor_seat_pointer_notify(self, priv, button, WL_POINTER_BUTTON_STATE_RELEASED);
}

static void
cmb_compositor_seat_key_notify(GtkEventControllerKey *self,
                               CmbCompositorPrivate  *priv,
                               uint32_t key,
                               uint32_t state)
{
  uint32_t time_msec = gtk_event_controller_get_current_event_time(GTK_EVENT_CONTROLLER(self));
  wlr_seat_keyboard_notify_key(priv->seat, time_msec, key - 8, state);
}

static gboolean
on_key_controller_key_pressed (GtkEventControllerKey* self,
                               G_GNUC_UNUSED guint keyval,
                               guint keycode,
                               G_GNUC_UNUSED GdkModifierType state,
                               CmbCompositorPrivate *priv)
{
  cmb_compositor_seat_key_notify(self, priv, keycode, WL_KEYBOARD_KEY_STATE_PRESSED);
  return TRUE;
}

static void
on_key_controller_key_released (GtkEventControllerKey* self,
                                G_GNUC_UNUSED guint keyval,
                                guint keycode,
                                G_GNUC_UNUSED GdkModifierType state,
                                CmbCompositorPrivate *priv)
{
  cmb_compositor_seat_key_notify(self, priv, keycode, WL_KEYBOARD_KEY_STATE_RELEASED);
}

static gboolean
on_key_controller_modifiers (G_GNUC_UNUSED GtkEventControllerKey *self,
                             GdkModifierType state,
                             CmbCompositorPrivate *priv)
{
  struct wlr_keyboard_modifiers modifiers = { 0, };
  guint wl_state = 0;

  if (state & GDK_SHIFT_MASK)
    wl_state |= WLR_MODIFIER_SHIFT;
  else if (state & GDK_LOCK_MASK)
    wl_state |= WLR_MODIFIER_CAPS;
  else if (state & GDK_CONTROL_MASK)
    wl_state |= WLR_MODIFIER_CTRL;
  else if (state & GDK_ALT_MASK)
    wl_state |= WLR_MODIFIER_ALT;
  else if (state & GDK_SUPER_MASK)
    wl_state |= WLR_MODIFIER_LOGO;
  else if (state & GDK_HYPER_MASK)
    wl_state |= WLR_MODIFIER_MOD2;
  else if (state & GDK_META_MASK)
    wl_state |= WLR_MODIFIER_MOD3;

  modifiers.depressed = wl_state;

  wlr_seat_keyboard_notify_modifiers(priv->seat, &modifiers);

  return TRUE;
}

static void
_on_pixbuf_destroy_notify (guchar *pixels, G_GNUC_UNUSED gpointer data)
{
  g_free(pixels);
}

static void
cursor_handle_surface_commit(struct wl_listener *listener, void *data)
{
  CmbCompositorPrivate *priv = wl_container_of(listener, priv, on_cursor_surface_commit);
  struct wlr_surface *surface = data;
  WlrTexture *texture = NULL;
  pixman_image_t *image = NULL;

  if (!(texture = wlr_surface_get_texture(surface)))
    return;

  if (!(image = wlr_pixman_texture_get_image(texture)))
    return;

  priv->hotspot_x -= surface->current.dx;
  priv->hotspot_y -= surface->current.dy;

  if (pixman_image_get_format (image) != PIXMAN_a8r8g8b8)
    {
      cmb_composite_reset_cursor(priv);
      return;
    }

  gint height, stride;

  height = pixman_image_get_height (image);
  stride = pixman_image_get_stride (image);

  /* Create a GdkPixbuf with a copy of surface data */
  if(!(priv->cursor_gdk_pixbuf = gdk_pixbuf_new_from_data (
      g_memdup2(pixman_image_get_data (image), height * stride),
      GDK_COLORSPACE_RGB,
      TRUE,
      8,
      pixman_image_get_width (image),
      height,
      stride,
      _on_pixbuf_destroy_notify,
      NULL
  )))
    return;

  /* Create texture from pixbuf */
  if (!(priv->cursor_gdk_texture = gdk_texture_new_for_pixbuf(priv->cursor_gdk_pixbuf)))
    return;

  /* Finally create cursor from texture */
  priv->cursor_gdk_cursor = gdk_cursor_new_from_texture(priv->cursor_gdk_texture,
                                                        priv->hotspot_x,
                                                        priv->hotspot_y,
                                                        NULL);

  /* Set cursor */
  if (priv->cursor_gdk_cursor)
    gtk_widget_set_cursor(priv->widget, priv->cursor_gdk_cursor);

  /* Unlink handler */
  cmb_composite_cursor_handler_remove(priv);
}

static void
on_seat_request_cursor(struct wl_listener *listener, void *data)
{
  CmbCompositorPrivate *priv = wl_container_of(listener, priv, on_request_cursor);
  struct wlr_seat_pointer_request_set_cursor_event *event = data;
  struct wlr_seat_client *focused_client =
    priv->seat->pointer_state.focused_client;
  struct wlr_surface *surface = event->surface;

  if (focused_client != event->seat_client)
    return;

  if (!surface)
    return;

  priv->hotspot_x = event->hotspot_x;
  priv->hotspot_y = event->hotspot_y;

  wlr_surface_send_enter(surface, &priv->output);

  /* We only keep track of the last cursor change */
  cmb_composite_cursor_handler_remove(priv);

  /* Update cursor once the surface has been committed */
  wl_signal_add(&surface->events.commit, &priv->on_cursor_surface_commit);
  priv->on_cursor_surface_commit.notify = cursor_handle_surface_commit;
}

static bool
cmb_compositor_backend_start(struct wlr_backend *wlr_backend)
{
  CmbCompositorPrivate *priv = wl_container_of(wlr_backend, priv, backend);
  g_info("Starting cmb backend");
  priv->backend_started = true;
  return true;
}

static void
cmb_compositor_backend_destroy(struct wlr_backend *wlr_backend)
{
  CmbCompositorPrivate *priv = wl_container_of(wlr_backend, priv, backend);
  wlr_backend_finish(&priv->backend);
  wlr_output_destroy(&priv->output);
}

static uint32_t
cmb_compositor_backend_get_buffer_caps(G_GNUC_UNUSED struct wlr_backend *wlr_backend)
{
  return WLR_BUFFER_CAP_DATA_PTR | WLR_BUFFER_CAP_DMABUF | WLR_BUFFER_CAP_SHM;
}

static bool
cmb_compositor_output_commit(G_GNUC_UNUSED struct wlr_output *wlr_output,
                             G_GNUC_UNUSED const struct wlr_output_state *state)
{
  return true;
}

static void cmb_compositor_output_destroy(G_GNUC_UNUSED struct wlr_output *wlr_output)
{
  /* TODO: disconnect from GdkFrameClock */
}

static void
cmb_compositor_backend_init(CmbCompositorPrivate *priv)
{
  priv->backend_impl.start = cmb_compositor_backend_start;
  priv->backend_impl.destroy = cmb_compositor_backend_destroy;
  priv->backend_impl.get_buffer_caps = cmb_compositor_backend_get_buffer_caps;
  wlr_backend_init(&priv->backend, &priv->backend_impl);
}

static void
cmb_compositor_output_init(CmbCompositorPrivate *priv)
{
  struct wlr_output_state state;

  wlr_output_state_init(&state);

  /* Initialize custom output iface */
  priv->output_impl.commit = cmb_compositor_output_commit;
  priv->output_impl.destroy = cmb_compositor_output_destroy;

  /* Actual size will be set on size_allocate() */
  wlr_output_state_set_custom_mode(&state, 0, 0, 0);

  /* Init wlr output */
  wlr_output_init(&priv->output,
                  &priv->backend,
                  &priv->output_impl,
                  wl_display_get_event_loop(priv->wl_display),
                  &state);

  /* Set a name */
  wlr_output_set_name(&priv->output, "CmbCompositor");
  wlr_output_set_description(&priv->output, "CmbCompositor output");

  /* Init output rendering */
  wlr_output_init_render(&priv->output, priv->allocator, priv->renderer);

  /* Sets up a listener for the frame event. */
  priv->on_frame.notify = on_cmb_compositor_output_frame;
  wl_signal_add(&priv->output.events.frame, &priv->on_frame);

  /* Create a scene output */
  priv->scene_output = wlr_scene_output_create(priv->scene, &priv->output);

  /* Make output global */
  wlr_output_create_global(&priv->output, priv->wl_display);

  wlr_output_state_finish(&state);
}

static void
cmb_pointer_mode_init(CmbCompositorPrivate *priv)
{
  wlr_pointer_init(&priv->pointer, NULL, "cmb-pointer");

  priv->on_request_cursor.notify = on_seat_request_cursor;
  wl_signal_add(&priv->seat->events.request_set_cursor,
                &priv->on_request_cursor);

  priv->motion_controller = gtk_event_controller_motion_new();
  priv->scroll_controller = gtk_event_controller_scroll_new(GTK_EVENT_CONTROLLER_SCROLL_BOTH_AXES |
                                                            GTK_EVENT_CONTROLLER_SCROLL_DISCRETE);
  priv->click_gesture = gtk_gesture_click_new();
  gtk_gesture_single_set_button(GTK_GESTURE_SINGLE(priv->click_gesture), 0);

  g_signal_connect(priv->motion_controller, "enter",
                   G_CALLBACK(on_motion_controller_enter),
                   priv);
  g_signal_connect(priv->motion_controller, "leave",
                   G_CALLBACK(on_motion_controller_leave),
                   priv);
  g_signal_connect(priv->motion_controller, "motion",
                   G_CALLBACK(on_motion_controller_motion),
                   priv);

  g_signal_connect(priv->scroll_controller, "scroll",
                   G_CALLBACK(on_scroll_controller_scroll),
                   priv);

  g_signal_connect(priv->click_gesture, "pressed",
                   G_CALLBACK(on_click_gesture_pressed),
                   priv);
  g_signal_connect(priv->click_gesture, "released",
                   G_CALLBACK(on_click_gesture_released),
                   priv);

  gtk_widget_add_controller(priv->widget, priv->motion_controller);
  gtk_widget_add_controller(priv->widget, priv->scroll_controller);
  gtk_widget_add_controller(priv->widget, GTK_EVENT_CONTROLLER(priv->click_gesture));
}

static void
cmb_compositor_keyboard_init(CmbCompositorPrivate *priv)
{
  struct xkb_keymap *keymap = NULL;
  struct xkb_state *state = NULL;
  GdkDevice *gkeyboard;
  GdkDisplay *gdisplay;
  GdkSeat *gseat;

  wlr_keyboard_init(&priv->keyboard, NULL, "cmb-keyboard");

  gdisplay = gtk_widget_get_display(priv->widget);
  gseat = gdk_display_get_default_seat(gdisplay);
  gkeyboard = gdk_seat_get_keyboard(gseat);

#ifdef GDK_WINDOWING_WAYLAND
  if (GDK_IS_WAYLAND_DEVICE (gkeyboard))
    {
      keymap = gdk_wayland_device_get_xkb_keymap (gkeyboard);

      /* TODO: add a way to get keymap state from gtk wayland backend
       * Or even better add a way to get the layout directly
       */

      xkb_keymap_ref(keymap);
    }
#endif

#ifdef GDK_WINDOWING_X11
  if (GDK_IS_X11_DEVICE_XI2 (gkeyboard))
    {
      struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
      Display *dpy = gdk_x11_display_get_xdisplay(GDK_X11_DISPLAY(gdisplay));

      keymap = xkb_x11_keymap_new_from_device(context,
                                              XGetXCBConnection(dpy),
                                              gdk_x11_device_get_id(gkeyboard),
                                              XKB_KEYMAP_COMPILE_NO_FLAGS);
      state = xkb_x11_state_new_from_device (keymap,
                                             XGetXCBConnection(dpy),
                                             gdk_x11_device_get_id(gkeyboard));
      xkb_context_unref(context);
    }
#endif

  /* Fallback to US */
  if (keymap == NULL)
    {
      struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
      keymap = xkb_keymap_new_from_names(context, NULL, XKB_KEYMAP_COMPILE_NO_FLAGS);
      xkb_context_unref(context);
    }

  /* Set keymap */
  wlr_keyboard_set_keymap(&priv->keyboard, keymap);

  /* Update layout if present */
  if (state)
    {
      gint active_layout = -1;

      for (guint i = 0; i < xkb_keymap_num_layouts (keymap); i++)
        {
          if (xkb_state_layout_index_is_active(state,
                                               i,
                                               XKB_STATE_LAYOUT_EFFECTIVE))
            active_layout = i;

          g_debug("\t %i %s", i, xkb_keymap_layout_get_name (keymap, i));
        }

      if (active_layout >= 0)
        wlr_keyboard_notify_modifiers(&priv->keyboard,
                                      priv->keyboard.modifiers.depressed,
                                      priv->keyboard.modifiers.latched,
                                      priv->keyboard.modifiers.locked,
                                      active_layout);
      xkb_state_unref(state);
    }

  xkb_keymap_unref(keymap);

  wlr_seat_set_keyboard(priv->seat, &priv->keyboard);

  priv->key_controller = gtk_event_controller_key_new();
  g_signal_connect(priv->key_controller, "key-pressed",
                   G_CALLBACK(on_key_controller_key_pressed),
                   priv);
  g_signal_connect(priv->key_controller, "key-released",
                   G_CALLBACK(on_key_controller_key_released),
                   priv);
  g_signal_connect(priv->key_controller, "modifiers",
                   G_CALLBACK(on_key_controller_modifiers),
                   priv);
  gtk_widget_add_controller(priv->widget, priv->key_controller);
}

static void
cmb_compositor_init (CmbCompositor *object)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (object);

  gtk_drawing_area_set_draw_func(GTK_DRAWING_AREA(object),
                                 cmb_compositor_draw,
                                 NULL,
                                 NULL);
  priv->widget = GTK_WIDGET(object);
  gtk_widget_set_focusable(priv->widget, TRUE);

  /* Toplevel state */
  priv->toplevel_state = g_hash_table_new_full(g_str_hash,
                                               g_str_equal,
                                               g_free,
                                               g_free);

  cmb_compositor_backend_init(priv);
  cmb_compositor_wlr_init (priv);
  cmb_compositor_output_init(priv);
  cmb_pointer_mode_init(priv);
  cmb_compositor_keyboard_init(priv);

  cmb_compositor_reset_pointer_mode(priv);

  priv->wl_source = cmb_wayland_source_new(priv->wl_display);
  g_source_attach (priv->wl_source, NULL);

  /* Start the backend. */
  if (!wlr_backend_start(&priv->backend))
    {
      /* TODO: handle error */
      return;
    }
}

void
cmb_compositor_cleanup (CmbCompositor *object)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (object);

  g_clear_pointer(&priv->toplevel_state, g_hash_table_destroy);
  g_clear_pointer(&priv->socket, g_free);

  g_clear_object(&priv->error_layout);
  g_clear_object(&priv->motion_controller);
  g_clear_object(&priv->scroll_controller);
  g_clear_object(&priv->key_controller);
  g_clear_object(&priv->click_gesture);

  priv->widget = NULL;
  cmb_composite_reset_cursor(priv);

  wl_display_destroy_clients(priv->wl_display);

  wlr_keyboard_finish(&priv->keyboard);
  wlr_pointer_finish(&priv->pointer);
  wlr_scene_node_destroy(&priv->scene->tree.node);
  wlr_allocator_destroy(priv->allocator);
  wlr_renderer_destroy(priv->renderer);
  wlr_backend_destroy(&priv->backend);
  wl_display_destroy(priv->wl_display);

  g_source_destroy (priv->wl_source);
}

void
cmb_compositor_finalize (GObject *object)
{
  cmb_compositor_cleanup(CMB_COMPOSITOR(object));
  G_OBJECT_CLASS (cmb_compositor_parent_class)->finalize (object);
}


static void
cmb_compositor_set_property (GObject      *object,
                             guint         prop_id,
                             const GValue *value,
                             GParamSpec   *pspec)
{
  g_return_if_fail (CMB_IS_COMPOSITOR (object));

  switch (prop_id)
    {
      case PROP_ERROR_MESSAGE:
        cmb_compositor_set_error_message (CMB_COMPOSITOR (object),
                                          g_value_get_string (value));
      break;
      default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

static void
cmb_compositor_get_property (GObject    *object,
                             guint       prop_id,
                             GValue     *value,
                             GParamSpec *pspec)
{
  CmbCompositorPrivate *priv;

  g_return_if_fail (CMB_IS_COMPOSITOR (object));
  priv = GET_PRIVATE (object);

  switch (prop_id)
    {
      case PROP_SOCKET:
        g_value_set_string (value, priv->socket);
      break;
      case PROP_ERROR_MESSAGE:
        g_value_set_string (value, pango_layout_get_text (priv->error_layout));
      break;
      default:
        G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
    }
}

static void
on_cmb_compositor_frame_clock_update (G_GNUC_UNUSED GdkFrameClock *self,
                                      CmbCompositorPrivate *priv)
{
  wlr_output_send_frame(&priv->output);
}

static void
cmb_compositor_realize(GtkWidget *widget)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (widget);

  GTK_WIDGET_CLASS (cmb_compositor_parent_class)->realize (widget);

  priv->frame_clock = gtk_widget_get_frame_clock(widget);
  priv->frame_clock_source =
    g_signal_connect(priv->frame_clock, "update",
                     G_CALLBACK(on_cmb_compositor_frame_clock_update),
                     priv);
}

static void
cmb_compositor_unrealize(GtkWidget *widget)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (widget);

  if (priv->frame_clock && priv->frame_clock_source)
    {
      g_signal_handler_disconnect(priv->frame_clock, priv->frame_clock_source);
      priv->frame_clock_source = 0;
    }

  GTK_WIDGET_CLASS (cmb_compositor_parent_class)->unrealize (widget);
}

static void
cmb_compositor_class_init (CmbCompositorClass *klass)
{
  GObjectClass *object_class = G_OBJECT_CLASS (klass);
  GtkWidgetClass *widget_class = GTK_WIDGET_CLASS (klass);

  object_class->finalize = cmb_compositor_finalize;
  object_class->set_property = cmb_compositor_set_property;
  object_class->get_property = cmb_compositor_get_property;

  widget_class->size_allocate = cmb_compositor_size_allocate;
  widget_class->realize = cmb_compositor_realize;
  widget_class->unrealize = cmb_compositor_unrealize;

  /* Properties */
  properties[PROP_SOCKET] =
    g_param_spec_string ("socket", "Unix Socket",
                         "The unix socket file to connect to this compositor",
                         NULL,
                         G_PARAM_READABLE);

  properties[PROP_ERROR_MESSAGE] =
    g_param_spec_string ("error-message", "Error message",
                         "Error message to show instead of compositor",
                         NULL,
                         G_PARAM_READWRITE);

  /* Signals */
  compositor_signals[CONTEXT_MENU] =
    g_signal_new ("context-menu",
                  G_OBJECT_CLASS_TYPE (klass),
                  0, 0,
                  NULL, NULL, NULL,
                  G_TYPE_NONE, 2,
                  G_TYPE_INT,
                  G_TYPE_INT);

  g_object_class_install_properties (object_class, N_PROPERTIES, properties);
}


CmbCompositor *
cmb_compositor_new (const gchar *socket)
{
  return g_object_new (CMB_COMPOSITOR_TYPE, "socket", socket, NULL);
}

/* wlroots */

static void
seat_request_set_selection(struct wl_listener *listener, void *data)
{
  CmbCompositorPrivate *priv = wl_container_of(listener, priv, request_set_selection);
  struct wlr_seat_request_set_selection_event *event = data;

  wlr_seat_set_selection(priv->seat, event->source, event->serial);
  /* TODO: integrate with Gtk clipboard */
}

static void
xdg_toplevel_map(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorToplevel *toplevel = wl_container_of(listener, toplevel, map);
  struct wlr_xdg_toplevel *xdg_toplevel = toplevel->xdg_toplevel;
  CmbCompositorToplevelState *state = toplevel->state;

  toplevel->priv->toplevels = g_list_prepend(toplevel->priv->toplevels, toplevel);

  cmb_compositor_focus_toplevel(toplevel, xdg_toplevel->base->surface);

  if (state)
    {
      /* Restore this window state */
      xdg_toplevel->scheduled.fullscreen = state->fullscreen;
      xdg_toplevel->scheduled.maximized = state->maximized;

      g_debug("%s %s %dx%d %dx%d maximized=%d fullscreen=%d",
              __func__,
              xdg_toplevel->app_id,
              state->x,
              state->y,
              state->width,
              state->height,
              state->maximized,
              state->fullscreen);

      if (state->fullscreen || state->maximized)
        {
          GtkWidget *widget = toplevel->priv->widget;

          toplevel->old_state = *state;

          cmb_compositor_toplevel_configure(toplevel,
                                            0, 0,
                                            gtk_widget_get_width(widget),
                                            gtk_widget_get_height(widget));
        }
      else
        cmb_compositor_toplevel_configure(toplevel,
                                          state->x,
                                          state->y,
                                          state->width,
                                          state->height);
    }
}

static void
xdg_toplevel_unmap(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorToplevel *toplevel = wl_container_of(listener, toplevel, unmap);

  if (toplevel == toplevel->priv->grabbed_toplevel)
    cmb_compositor_reset_pointer_mode(toplevel->priv);

  toplevel->state = NULL;

  toplevel->priv->toplevels = g_list_remove(toplevel->priv->toplevels, toplevel);
}

static void
xdg_toplevel_commit(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorToplevel *toplevel = wl_container_of(listener, toplevel, commit);

  if (toplevel->xdg_toplevel->base->initial_commit)
    wlr_xdg_toplevel_set_size(toplevel->xdg_toplevel, 0, 0);
}

static void
xdg_toplevel_destroy(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorToplevel *toplevel = wl_container_of(listener, toplevel, destroy);

  wl_list_remove(&toplevel->map.link);
  wl_list_remove(&toplevel->unmap.link);
  wl_list_remove(&toplevel->commit.link);
  wl_list_remove(&toplevel->destroy.link);
  wl_list_remove(&toplevel->request_move.link);
  wl_list_remove(&toplevel->request_resize.link);
  wl_list_remove(&toplevel->request_maximize.link);
  wl_list_remove(&toplevel->request_fullscreen.link);

  g_free(toplevel);
}

static gboolean
cmb_compositor_toplevel_has_focus(CmbCompositorToplevel *toplevel)
{
  CmbCompositorPrivate *priv = toplevel->priv;
  struct wlr_surface *focused_surface =
    priv->seat->pointer_state.focused_surface;

  return toplevel->xdg_toplevel->base->surface ==
    wlr_surface_get_root_surface(focused_surface);
}

static void
xdg_toplevel_request_move(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorToplevel *toplevel = wl_container_of(listener, toplevel, request_move);
  CmbCompositorPrivate *priv = toplevel->priv;

  if (!cmb_compositor_toplevel_has_focus(toplevel))
    return;

  priv->grabbed_toplevel = toplevel;
  priv->pointer_mode = CMB_POINTER_MODE_MOVE;
  priv->grab_x = priv->pointer_x - toplevel->scene_tree->node.x;
  priv->grab_y = priv->pointer_y - toplevel->scene_tree->node.y;
}

static void
xdg_toplevel_request_resize(struct wl_listener *listener, void *data)
{
  CmbCompositorToplevel *toplevel = wl_container_of(listener, toplevel, request_resize);
  CmbCompositorPrivate *priv = toplevel->priv;
  struct wlr_scene_tree *scene_tree = toplevel->scene_tree;
  struct wlr_xdg_toplevel_resize_event *event = data;
  struct wlr_box box;
  double border_x, border_y;

  if (!cmb_compositor_toplevel_has_focus(toplevel))
    return;

  priv->grabbed_toplevel = toplevel;
  priv->pointer_mode = CMB_POINTER_MODE_RESIZE;
  priv->resize_edges = event->edges;

  wlr_xdg_surface_get_geometry(toplevel->xdg_toplevel->base, &box);

  border_x = scene_tree->node.x + box.x +
        ((event->edges & WLR_EDGE_RIGHT) ? box.width : 0);
  border_y = scene_tree->node.y + box.y +
        ((event->edges & WLR_EDGE_BOTTOM) ? box.height : 0);
  priv->grab_x = priv->pointer_x - border_x;
  priv->grab_y = priv->pointer_y - border_y;

  priv->grab_box = box;
  priv->grab_box.x += scene_tree->node.x;
  priv->grab_box.y += scene_tree->node.y;
}

static void
xdg_toplevel_request_maximize(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorToplevel *toplevel =
    wl_container_of(listener, toplevel, request_maximize);

  cmb_compositor_toplevel_toggle_maximize_fullscreen(toplevel, FALSE);
}

static void
xdg_toplevel_request_fullscreen(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorToplevel *toplevel =
    wl_container_of(listener, toplevel, request_fullscreen);

  cmb_compositor_toplevel_toggle_maximize_fullscreen(toplevel, TRUE);
}

static void
xdg_toplevel_set_app_id(struct wl_listener *listener,G_GNUC_UNUSED  void *data)
{
  CmbCompositorToplevel *toplevel =
    wl_container_of(listener, toplevel, set_app_id);
  const gchar *app_id = toplevel->xdg_toplevel->app_id;

  toplevel->state = NULL;

  if (!g_str_has_prefix (app_id, "Cmb:"))
    return;

  toplevel->state = g_hash_table_lookup(toplevel->priv->toplevel_state, app_id);

  if (!toplevel->state)
    {
      /* Allocate new state struct */
      toplevel->state = g_new0(CmbCompositorToplevelState, 1);

      /* Start new windows in the top left corner */
      toplevel->state->x = 32;
      toplevel->state->y = 32;

      /* Insert it in out server hash table */
      g_hash_table_insert(toplevel->priv->toplevel_state,
                          g_strdup(app_id),
                          toplevel->state);
    }

    g_debug("%s %s %dx%d %dx%d",
            __func__,
            toplevel->xdg_toplevel->app_id,
            toplevel->state->x,
            toplevel->state->y,
            toplevel->state->width,
            toplevel->state->height);
}

static void
server_new_xdg_toplevel(struct wl_listener *listener, void *data)
{
  CmbCompositorPrivate *priv = wl_container_of(listener, priv, new_xdg_toplevel);
  struct wlr_xdg_toplevel *xdg_toplevel = data;
  CmbCompositorToplevel *toplevel;

  toplevel = g_new0(CmbCompositorToplevel, 1);
  toplevel->priv = priv;
  toplevel->xdg_toplevel = xdg_toplevel;
  toplevel->scene_tree =
    wlr_scene_xdg_surface_create(&priv->scene->tree,
                                 xdg_toplevel->base);
  toplevel->scene_tree->node.data = toplevel;
  xdg_toplevel->base->data = toplevel->scene_tree;

  toplevel->map.notify = xdg_toplevel_map;
  wl_signal_add(&xdg_toplevel->base->surface->events.map, &toplevel->map);
  toplevel->unmap.notify = xdg_toplevel_unmap;
  wl_signal_add(&xdg_toplevel->base->surface->events.unmap, &toplevel->unmap);
  toplevel->commit.notify = xdg_toplevel_commit;
  wl_signal_add(&xdg_toplevel->base->surface->events.commit, &toplevel->commit);

  toplevel->destroy.notify = xdg_toplevel_destroy;
  wl_signal_add(&xdg_toplevel->events.destroy, &toplevel->destroy);

  toplevel->request_move.notify = xdg_toplevel_request_move;
  wl_signal_add(&xdg_toplevel->events.request_move, &toplevel->request_move);
  toplevel->request_resize.notify = xdg_toplevel_request_resize;
  wl_signal_add(&xdg_toplevel->events.request_resize, &toplevel->request_resize);
  toplevel->request_maximize.notify = xdg_toplevel_request_maximize;
  wl_signal_add(&xdg_toplevel->events.request_maximize, &toplevel->request_maximize);
  toplevel->request_fullscreen.notify = xdg_toplevel_request_fullscreen;
  wl_signal_add(&xdg_toplevel->events.request_fullscreen, &toplevel->request_fullscreen);

  toplevel->set_app_id.notify = xdg_toplevel_set_app_id;
  wl_signal_add(&xdg_toplevel->events.set_app_id, &toplevel->set_app_id);
}

static void
xdg_popup_commit(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorPopup *popup = wl_container_of(listener, popup, commit);

  if (popup->xdg_popup->base->initial_commit)
    wlr_xdg_surface_schedule_configure(popup->xdg_popup->base);
}

static void
xdg_popup_destroy(struct wl_listener *listener, G_GNUC_UNUSED void *data)
{
  CmbCompositorPopup *popup = wl_container_of(listener, popup, destroy);

  wl_list_remove(&popup->commit.link);
  wl_list_remove(&popup->destroy.link);
  g_free(popup);
}

static void
server_new_xdg_popup(G_GNUC_UNUSED struct wl_listener *listener, void *data)
{
  CmbCompositorPopup *popup = g_new0(CmbCompositorPopup, 1);
  struct wlr_xdg_popup *xdg_popup = data;
  struct wlr_xdg_surface *parent;

  popup->xdg_popup = xdg_popup;

  if(!(parent = wlr_xdg_surface_try_from_wlr_surface(xdg_popup->parent)))
    return;

  xdg_popup->base->data = wlr_scene_xdg_surface_create(parent->data,
                                                       xdg_popup->base);

  popup->commit.notify = xdg_popup_commit;
  wl_signal_add(&xdg_popup->base->surface->events.commit, &popup->commit);

  popup->destroy.notify = xdg_popup_destroy;
  wl_signal_add(&xdg_popup->events.destroy, &popup->destroy);
}

static void
server_request_activate(struct wl_listener *listener, void *data)
{
  CmbCompositorPrivate *priv = wl_container_of(listener, priv, request_activate);
  struct wlr_xdg_activation_v1_request_activate_event *event = data;
  struct wlr_xdg_toplevel *xdg_toplevel =
    wlr_xdg_toplevel_try_from_wlr_surface(event->surface);

  if (!xdg_toplevel)
    return;

  for (GList *l = priv->toplevels; l; l = g_list_next(l))
    {
      CmbCompositorToplevel *toplevel = l->data;

      if (toplevel->xdg_toplevel != xdg_toplevel)
        continue;

      wlr_scene_node_raise_to_top(&toplevel->scene_tree->node);
    }
}

static gchar *
cmb_compositor_get_socket()
{
  gchar *tmp = g_dir_make_tmp("cmb-compositor-XXXXXX", NULL);
  gchar *retval = g_build_filename(tmp, "wayland.sock", NULL);
  g_free(tmp);
  return retval;
}

static void
cmb_compositor_wlr_init(CmbCompositorPrivate *priv)
{
  priv->wl_display = wl_display_create();

  priv->renderer = wlr_pixman_renderer_create();
  if (priv->renderer == NULL)
    {
      g_warning("failed to create wlr_renderer");
      return;
    }

  wlr_renderer_init_wl_display(priv->renderer, priv->wl_display);

  priv->allocator = wlr_allocator_autocreate(&priv->backend, priv->renderer);
  if (priv->allocator == NULL)
    {
      g_warning("failed to create wlr_allocator");
      return;
    }

  wlr_compositor_create(priv->wl_display, 5, priv->renderer);
  wlr_subcompositor_create(priv->wl_display);
  wlr_data_device_manager_create(priv->wl_display);

  /* Create a scene graph a wlroots abstraction that handles all rendering */
  priv->scene = wlr_scene_create();

  /* Disable direct scanout */
  priv->scene->direct_scanout = FALSE;

  /* Background color */
  priv->bg = wlr_scene_rect_create(&priv->scene->tree,
                                   100, 100,
                                   (float[4]){ 1.0f, 1.f, 1.f, 1 });
  wlr_scene_node_set_position(&priv->bg->node, 0, 0);

  /* Set up xdg-shell version 3 */
  priv->xdg_shell = wlr_xdg_shell_create(priv->wl_display, 3);
  priv->new_xdg_toplevel.notify = server_new_xdg_toplevel;
  wl_signal_add(&priv->xdg_shell->events.new_toplevel, &priv->new_xdg_toplevel);
  priv->new_xdg_popup.notify = server_new_xdg_popup;
  wl_signal_add(&priv->xdg_shell->events.new_popup, &priv->new_xdg_popup);

  /* Set up xdg-activation */
  priv->xdg_activation = wlr_xdg_activation_v1_create(priv->wl_display);
  priv->request_activate.notify = server_request_activate;
  wl_signal_add(&priv->xdg_activation->events.request_activate, &priv->request_activate);

  /* Configure seat */
  priv->seat = wlr_seat_create(priv->wl_display, "seat0");
  priv->request_set_selection.notify = seat_request_set_selection;
  wl_signal_add(&priv->seat->events.request_set_selection,
                &priv->request_set_selection);

  wlr_seat_set_capabilities(priv->seat,
                            WL_SEAT_CAPABILITY_POINTER |
                            WL_SEAT_CAPABILITY_KEYBOARD);

  priv->socket = cmb_compositor_get_socket();

  if (wl_display_add_socket(priv->wl_display, priv->socket))
    g_warning("Error adding socket file %s\n", priv->socket);
}

void
cmb_compositor_set_bg_color(CmbCompositor *compositor,
                            gdouble red,
                            gdouble green,
                            gdouble blue)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (compositor);
  wlr_scene_rect_set_color(priv->bg, (float[4]){ red, green, blue, 1 });
}


void
cmb_compositor_forget_toplevel_state(CmbCompositor *compositor)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (compositor);
  g_hash_table_remove_all(priv->toplevel_state);
}

static void
cmb_compositor_set_error_message(CmbCompositor *compositor,
                                 const gchar   *message)
{
  CmbCompositorPrivate *priv = GET_PRIVATE (compositor);

  priv->error_message = g_strdup(message);

  if (!priv->error_layout)
    priv->error_layout = pango_layout_new(gtk_widget_get_pango_context (priv->widget));

  if (message)
    {
      gint width, height;

      pango_layout_set_text(priv->error_layout, message, -1);
      pango_layout_get_size(priv->error_layout, &width, &height);

      priv->error_layout_width = PANGO_PIXELS(width);
      priv->error_layout_height = PANGO_PIXELS(height);
    }

  gtk_widget_queue_draw (priv->widget);
}
