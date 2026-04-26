# Merengue Application
#
# Copyright (C) 2021  Juan Pablo Ugarte
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
import gi
import logging

gi.require_version('GIRepository', '3.0')

from . import config
from gi.repository import GLib, Gio, Gtk


resource = Gio.Resource.load(os.path.join(config.pkgdatadir, "merengue.gresource"))
resource._register()

repository = gi.Repository.get_default()
repository.prepend_search_path(config.privatecambalachedir)
repository.prepend_library_path(config.privatecambalachedir)

gi.require_version("CambalachePrivate", "4.0" if Gtk.MAJOR_VERSION == 4 else "3.0")
from gi.repository import CambalachePrivate

def __log_writer_handler(level, field_list, data):
    fields = {f.key: CambalachePrivate.log_field_get_string(f) for f in field_list if f.length < 0}

    if fields.get("GLIB_DOMAIN") == "GLib-GIO":
        if fields.get("MESSAGE").startswith("Adding GResources overlay") or \
           fields.get("MESSAGE").startswith("Mapped file") or \
           fields.get("MESSAGE").startswith("Can't mmap overlay file"):
            return GLib.LogWriterOutput.HANDLED

    return GLib.log_writer_default(level, field_list, data)


GLib.log_set_writer_func(__log_writer_handler)


def getLogger(name):
    formatter = logging.Formatter("%(levelname)s:%(name)s %(message)s")

    ch = logging.StreamHandler()
    ch.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(os.environ.get("MERENGUE_LOGLEVEL", "WARNING").upper())
    logger.addHandler(ch)

    return logger


from .mrg_application import MrgApplication
from .mrg_controller import MrgController
from .mrg_placeholder import MrgPlaceholder
from . import utils

