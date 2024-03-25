#!/usr/bin/env python3

import compileall
from os import environ

destdir = environ.get("DESTDIR", "")

# Pre compile all .py files
compileall.compile_dir(destdir, force=True)
