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

#pragma once

#include "cmb_private_svg.h"

G_BEGIN_DECLS

void           cmb_private_svg_set_load_time   (CmbPrivateSvg                *self,
                                        int64_t                load_time);

void           cmb_private_svg_set_playing     (CmbPrivateSvg                *self,
                                        gboolean               playing);

void           cmb_private_svg_advance         (CmbPrivateSvg                *self,
                                        int64_t                current_time);

typedef enum
{
  CMB_PRIVATE_SVG_RUN_MODE_STOPPED,
  CMB_PRIVATE_SVG_RUN_MODE_DISCRETE,
  CMB_PRIVATE_SVG_RUN_MODE_CONTINUOUS,
} CmbPrivateSvgRunMode;

CmbPrivateSvgRunMode  cmb_private_svg_get_run_mode    (CmbPrivateSvg *self);

int64_t        cmb_private_svg_get_next_update (CmbPrivateSvg *self);

typedef enum
{
  CMB_PRIVATE_SVG_SERIALIZE_DEFAULT           = 0,
  CMB_PRIVATE_SVG_SERIALIZE_AT_CURRENT_TIME   = 1 << 0,
  CMB_PRIVATE_SVG_SERIALIZE_EXCLUDE_ANIMATION = 1 << 1,
  CMB_PRIVATE_SVG_SERIALIZE_INCLUDE_STATE     = 1 << 2,
} CmbPrivateSvgSerializeFlags;

GBytes *       cmb_private_svg_serialize_full  (CmbPrivateSvg                *self,
                                        const GdkRGBA         *colors,
                                        size_t                 n_colors,
                                        CmbPrivateSvgSerializeFlags   flags);

G_END_DECLS
