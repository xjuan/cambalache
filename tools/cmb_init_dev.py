#!/usr/bin/python3
#
# Cambalache UI Maker developer mode
#
# Copyright (C) 2021-2024  Juan Pablo Ugarte
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
import stat
import signal
import subprocess

basedir = os.path.join(os.path.split(os.path.dirname(__file__))[0])
sys.path.insert(1, basedir)

cambalachedir = os.path.join(basedir, "cambalache")
localdir = os.path.join(basedir, ".local")
localpkgdatadir = os.path.join(localdir, "share", "cambalache")
catalogsdir = os.path.join(localpkgdatadir, "catalogs")

from gi.repository import GLib  # noqa: E402


def find_program_in_path(program):
    retval = GLib.find_program_in_path(program)
    if retval is None:
        print(f"Could not find {program} in PATH")
    return retval


signal.signal(signal.SIGINT, signal.SIG_DFL)


def dev_config(filename, content):
    meson_mtime = os.path.getmtime(os.path.join(basedir, "meson.build"))

    abspath = os.path.join(basedir, filename)
    if not os.path.exists(abspath) or meson_mtime > os.path.getmtime(abspath):
        with open(abspath, "w") as fd:
            fd.write(content)


def configure_file(input_file, output_file, config):
    with open(input_file, "r") as fd:
        content = fd.read()

        for key in config:
            content = content.replace(f"@{key}@", config[key])

        with open(output_file, "w") as outfd:
            outfd.write(content)


def get_version():
    meson = open(os.path.join(basedir, "meson.build"))
    version = None
    fileformatversion = None

    for line in meson:
        line = line.strip()
        if version is None and line.startswith("version"):
            tokens = line.split(":")
            version = tokens[1].strip().replace("'", "").replace(",", "")
        elif fileformatversion is None and line.startswith("fileformatversion"):
            tokens = line.split("=")
            fileformatversion = tokens[1].strip().replace("'", "")

    meson.close()

    return (version, fileformatversion)


def run_meson():
    for prog in ["meson", "ninja", "cc", "pkg-config", "g-ir-compiler", "g-ir-scanner"]:
        if GLib.find_program_in_path(prog) is None:
            print(f"{prog} is needed to compile Cambalache private library")
            return -1

    builddir = os.path.join(localdir, "build")
    ninja = os.path.join(builddir, "build.ninja")

    if not os.path.exists(ninja):
        GLib.mkdir_with_parents(builddir, 0o700)
        os.system(f"meson setup --wipe --buildtype=debug --prefix={localdir} {builddir}")

    result = subprocess.run(['ninja', '-C', builddir], stdout=subprocess.PIPE)
    if result.returncode == 0:
        if "ninja: no work to do." not in result.stdout.decode('utf-8'):
            os.system(f"ninja -C {builddir} install")
    else:
        print(result.stdout.decode('utf-8'))

    return result.returncode


def cmb_init_dev():
    version, fileformatversion = get_version()

    # Create config files pointing to source directories
    dev_config(
        os.path.join(cambalachedir, "config.py"),
        f"""VERSION = '{version}'
FILE_FORMAT_VERSION = '{fileformatversion}'
pkgdatadir = '{localpkgdatadir}'
merenguedir = '{cambalachedir}'
catalogsdir = '{catalogsdir}'
""",
    )

    # Create config files pointing to source directories
    dev_config(
        os.path.join(cambalachedir, "merengue/config.py"),
        f"""VERSION = '{version}'
pkgdatadir = '{localpkgdatadir}'
merenguedir = '{cambalachedir}'
privatecambalachedir = '{localdir}'
""",
    )

    coverage_bin = GLib.find_program_in_path("python3-coverage")

    # Create merengue bin script
    if coverage_bin and os.getenv("COVERAGE_PROCESS_START", None):
        merengue_shebang = coverage_bin + " run"
    else:
        merengue_shebang = GLib.find_program_in_path("python3")

    configure_file(
        os.path.join(cambalachedir, "merengue", "merengue.in"),
        os.path.join(cambalachedir, "merengue", "merengue"),
        {"PYTHON": merengue_shebang, "merenguedir": cambalachedir},
    )
    os.chmod(os.path.join(cambalachedir, "merengue", "merengue"), stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)

    return run_meson()


if __name__ == "__main__":
    exit(cmb_init_dev())
