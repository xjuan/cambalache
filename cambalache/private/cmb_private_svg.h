/*
 * Copyright © 2025 Red Hat, Inc
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library. If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: LGPL-2.1-or-later
 *
 * Authors: Matthias Clasen <mclasen@redhat.com>
 */
#include "cmb_private.h"

#if GTK_MAJOR_VERSION == 4

#pragma once

#include <gdk/gdk.h>

#define __GTK_H_INSIDE__ 1

G_BEGIN_DECLS

#define CMB_PRIVATE_TYPE_SVG (cmb_private_svg_get_type ())

G_DECLARE_FINAL_TYPE (CmbPrivateSvg, cmb_private_svg, CMB_PRIVATE, SVG, GObject)

CmbPrivateSvg *         cmb_private_svg_new               (void);

CmbPrivateSvg *         cmb_private_svg_new_from_bytes    (GBytes        *bytes);

CmbPrivateSvg *         cmb_private_svg_new_from_resource (const char    *path);

void             cmb_private_svg_load_from_bytes   (CmbPrivateSvg        *self,
                                            GBytes        *bytes);

GBytes *         cmb_private_svg_serialize         (CmbPrivateSvg        *self);

gboolean         cmb_private_svg_write_to_file     (CmbPrivateSvg        *self,
                                            const char    *filename,
                                            GError       **error);

void             cmb_private_svg_set_weight        (CmbPrivateSvg        *self,
                                            double         weight);
double           cmb_private_svg_get_weight        (CmbPrivateSvg        *self);

#define CMB_PRIVATE_SVG_STATE_EMPTY ((unsigned int) -1)

void             cmb_private_svg_set_state         (CmbPrivateSvg        *self,
                                            unsigned int   state);
unsigned int     cmb_private_svg_get_state         (CmbPrivateSvg        *self);

unsigned int     cmb_private_svg_get_n_states      (CmbPrivateSvg        *self);

void             cmb_private_svg_set_frame_clock   (CmbPrivateSvg        *self,
                                            GdkFrameClock *clock);

void             cmb_private_svg_play              (CmbPrivateSvg        *self);

void             cmb_private_svg_pause             (CmbPrivateSvg        *self);

typedef enum
{
  CMB_PRIVATE_SVG_ERROR_INVALID_ELEMENT,
  CMB_PRIVATE_SVG_ERROR_INVALID_ATTRIBUTE,
  CMB_PRIVATE_SVG_ERROR_MISSING_ATTRIBUTE,
  CMB_PRIVATE_SVG_ERROR_INVALID_REFERENCE,
  CMB_PRIVATE_SVG_ERROR_FAILED_UPDATE,
  CMB_PRIVATE_SVG_ERROR_FAILED_RENDERING,
} CmbPrivateSvgError;

typedef struct
{
  size_t bytes;
  size_t lines;
  size_t line_chars;
} CmbPrivateSvgLocation;

#define CMB_PRIVATE_SVG_ERROR (cmb_private_svg_error_quark ())

GQuark       cmb_private_svg_error_quark               (void);
const char * cmb_private_svg_error_get_element     (const GError *error);
const char * cmb_private_svg_error_get_attribute   (const GError *error);
const CmbPrivateSvgLocation *
              cmb_private_svg_error_get_start      (const GError *error);
const CmbPrivateSvgLocation *
              cmb_private_svg_error_get_end        (const GError *error);

G_END_DECLS

#endif
