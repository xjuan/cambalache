#!/bin/python3
#
# run-dev - Script to run Cambalache from sources
#
# Copyright (C) 2025  Juan Pablo Ugarte
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as
# published by the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Authors:
#   Juan Pablo Ugarte <juanpablougarte@gmail.com>
#

import os
import sys
import locale
import gettext

from tools.cmb_init_dev import cmb_init_dev

# Compile deps and install things in .local
cmb_init_dev()

basedir = os.path.join(os.path.split(os.path.dirname(__file__))[0])

# Setup gettext for GtkBuilder
locale.bindtextdomain("cambalache", os.path.join(basedir, ".local", "share", "locale"))
locale.textdomain("cambalache")

# Setup for python code
gettext.bindtextdomain("cambalache", os.path.join(basedir, ".local", "share", "locale"))
gettext.textdomain("cambalache")

from cambalache.app import CmbApplication  # noqa E402

CmbApplication().run(sys.argv)
