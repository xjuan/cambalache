#!/usr/bin/env python3

import sys
import compileall
from os import environ, path
from subprocess import call

prefix = environ.get("MESON_INSTALL_PREFIX", "/usr/local")
datadir = path.join(prefix, "share")
destdir = environ.get("DESTDIR", "")

# Package managers set this so we don't need to run
if not destdir:
    print("Updating mime database...")
    call(["update-mime-database", path.join(datadir, "mime")])

    print("Updating icon cache...")
    call(["gtk-update-icon-cache", "-qtf", path.join(datadir, "icons", "hicolor")])

    print("Updating desktop database...")
    call(["update-desktop-database", "-q", path.join(datadir, "applications")])

    print("Compiling GSettings schemas...")
    call(["glib-compile-schemas", path.join(datadir, "glib-2.0", "schemas")])


# Pre compile all .py files
compileall.compile_dir(destdir, force=True)
