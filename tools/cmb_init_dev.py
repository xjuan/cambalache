#!/usr/bin/python3
#
# Cambalache UI Maker developer mode
#
# Copyright (C) 2021-2023  Juan Pablo Ugarte
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
import locale
import xml.etree.ElementTree as ET

basedir = os.path.join(os.path.split(os.path.dirname(__file__))[0])
sys.path.insert(1, basedir)

# Set GSchema dir before loading GLib
datadir = os.path.join(basedir, "data")
catalogsdir = os.path.join(basedir, ".catalogs")
cambalachedir = os.path.join(basedir, "cambalache")
xdgdatadir = os.getenv("XDG_DATA_DIRS", "/usr/local/share/:/usr/share/") + f":{datadir}"

privatedir = os.path.join(basedir, ".lib")
os.environ["GI_TYPELIB_PATH"] = privatedir
os.environ["LD_LIBRARY_PATH"] = privatedir
os.environ["GSETTINGS_SCHEMA_DIR"] = datadir
os.environ["XDG_DATA_DIRS"] = xdgdatadir
os.environ[
    "MERENGUE_DEV_ENV"
] = f"""{{
    "GI_TYPELIB_PATH": "{privatedir}",
    "LD_LIBRARY_PATH": "{privatedir}",
    "GSETTINGS_SCHEMA_DIR": "{datadir}",
    "XDG_DATA_DIRS": "{xdgdatadir}"
}}"""

from gi.repository import GLib  # noqa: E402


def find_program_in_path(program):
    retval = GLib.find_program_in_path(program)
    if retval is None:
        print(f"Could not find {program} in PATH")
    return retval


glib_compile_resources = find_program_in_path("glib-compile-resources")
glib_compile_schemas = find_program_in_path("glib-compile-schemas")
update_mime_database = find_program_in_path("update-mime-database")
msgfmt = find_program_in_path("msgfmt")

signal.signal(signal.SIGINT, signal.SIG_DFL)


def dev_config(filename, content):
    meson_mtime = os.path.getmtime(os.path.join(basedir, "meson.build"))

    abspath = os.path.join(basedir, filename)
    if not os.path.exists(abspath) or meson_mtime > os.path.getmtime(abspath):
        with open(abspath, "w") as fd:
            fd.write(content)


def get_resource_mtime(filename):
    max_mtime = os.path.getmtime(filename)
    dirname = os.path.dirname(filename)

    tree = ET.parse(filename)
    root = tree.getroot()

    for gresource in root:
        for file in gresource.findall("file"):
            mtime = os.path.getmtime(os.path.join(dirname, file.text))
            if mtime > max_mtime:
                max_mtime = mtime

    return max_mtime


def compile_resource(sourcedir, resource, resource_xml):
    glib_compile_resources = find_program_in_path("glib-compile-resources")

    if glib_compile_resources is None:
        return

    if not os.path.exists(resource) or os.path.getmtime(resource) < get_resource_mtime(resource_xml):
        print("glib-compile-resources", resource)
        GLib.spawn_sync(
            basedir,
            [glib_compile_resources, f"--sourcedir={sourcedir}", f"--target={resource}", resource_xml],
            None,
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
        )


def compile_schemas(schema_xml):
    if glib_compile_schemas is None:
        return

    schemadir = os.path.dirname(schema_xml)
    schema = os.path.join(schemadir, "gschemas.compiled")

    if not os.path.exists(schema) or os.path.getmtime(schema) < os.path.getmtime(schema_xml):
        print("glib-compile-schemas", schema)
        GLib.spawn_sync(basedir, [glib_compile_schemas, schemadir], None, GLib.SpawnFlags.DEFAULT, None, None)


def update_mime(mime_xml):
    if update_mime_database is None:
        return

    dirname = os.path.dirname(mime_xml)
    basename = os.path.basename(mime_xml)

    mimedir = os.path.join(dirname, "mime")
    packagesdir = os.path.join(mimedir, "packages")
    mimefile = os.path.join(packagesdir, basename)
    mime = os.path.join(mimedir, "mime.cache")

    if not os.path.exists(mimefile):
        GLib.mkdir_with_parents(packagesdir, 0o700)
        os.symlink(os.path.join("..", "..", basename), mimefile)

    if not os.path.exists(mime) or os.path.getmtime(mime) < os.path.getmtime(mime_xml):
        print("update-mime-database", mimedir)
        GLib.spawn_sync(basedir, [update_mime_database, mimedir], None, GLib.SpawnFlags.DEFAULT, None, None)


def configure_file(input_file, output_file, config):
    with open(input_file, "r") as fd:
        content = fd.read()

        for key in config:
            content = content.replace(f"@{key}@", config[key])

        with open(output_file, "w") as outfd:
            outfd.write(content)


def create_catalogs_dir():
    def link_plugin(filename):
        fullpath = os.path.join(basedir, filename)
        basename = os.path.basename(filename)
        link = os.path.join(catalogsdir, basename)
        if not os.path.islink(link):
            print(f"Setting up {basename} catalog link")
            os.symlink(os.path.abspath(fullpath), os.path.abspath(link))

    if not os.path.exists(catalogsdir):
        GLib.mkdir_with_parents(catalogsdir, 0o700)

    link_plugin("catalogs/glib/gobject-2.0.xml")
    link_plugin("catalogs/glib/gio-2.0.xml")
    link_plugin("catalogs/gdkpixbuf/gdkpixbuf-2.0.xml")
    link_plugin("catalogs/pango/pango-1.0.xml")
    link_plugin("catalogs/gtk/gdk-3.0.xml")
    link_plugin("catalogs/gtk/gdk-4.0.xml")
    link_plugin("catalogs/gtk/gsk-4.0.xml")
    link_plugin("catalogs/gtk/gtk-4.0.xml")
    link_plugin("catalogs/gtk/gtk+-3.0.xml")
    link_plugin("catalogs/gnome/webkit2gtk-4.1.xml")
    link_plugin("catalogs/gnome/webkitgtk-6.0.xml")
    link_plugin("catalogs/gnome/libhandy-1.xml")
    link_plugin("catalogs/gnome/libadwaita-1.xml")


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


def check_init_locale():
    localedir = os.path.join(basedir, "po", ".lc_messages")

    if not os.path.exists(localedir):
        GLib.mkdir_with_parents(localedir, 0o700)

    linguas = open(os.path.join(basedir, "po", "LINGUAS"))

    for lang in linguas:
        lang = lang.strip()
        po_file = os.path.join(basedir, "po", f"{lang}.po")
        mo_dir = os.path.join(basedir, "po", ".lc_messages", lang, "LC_MESSAGES")
        mo_file = os.path.join(mo_dir, "cambalache.mo")

        if not os.path.exists(mo_dir):
            GLib.mkdir_with_parents(mo_dir, 0o700)

        if not os.path.exists(mo_file) or os.path.getmtime(mo_file) < os.path.getmtime(po_file):
            print("msgfmt", po_file, mo_file)
            GLib.spawn_sync(".", [msgfmt, po_file, "-o", mo_file], None, GLib.SpawnFlags.DEFAULT, None, None)

    locale.bindtextdomain("cambalache", localedir)
    locale.textdomain("cambalache")


def compile_private():
    srcdir = os.path.join(basedir, "cambalache", "private")

    for prog in ["cc", "pkg-config", "g-ir-compiler", "g-ir-scanner"]:
        if GLib.find_program_in_path(prog) is None:
            print(f"{prog} is needed to compile Cambalache private library")
            return

    if not os.path.exists(privatedir):
        GLib.mkdir_with_parents(privatedir, 0o700)

    for v, pkg in [("3", "gtk+-3.0"), ("4", "gtk4")]:
        srcfile = f"{srcdir}/cmb_private.c"
        typelib = f"{privatedir}/CambalachePrivate-{v}.0.typelib"

        if os.path.exists(typelib) and os.path.getmtime(srcfile) < os.path.getmtime(typelib):
            continue

        os.system(f"cc -c -fpic -Wall `pkg-config {pkg} --cflags` -I{srcdir} {srcfile} -o {privatedir}/cmb_private.o")
        os.system(
            f"cc -shared -o {privatedir}/libcambalacheprivate-{v}.so {privatedir}/cmb_private.o `pkg-config {pkg} --libs`"
        )
        os.system(
            f"""
            g-ir-scanner -i Gtk-{v}.0 -n CambalachePrivate --nsversion={v}.0 --identifier-prefix=cmb_private -L {privatedir} \
                         -l cambalacheprivate-{v} --symbol-prefix=cmb_private --identifier-prefix=CmbPrivate \
                         {srcdir}/*.c {srcdir}/*.h --warn-all -o {privatedir}/CambalachePrivate-{v}.0.gir
            """
        )
        os.system(f"g-ir-compiler {privatedir}/CambalachePrivate-{v}.0.gir --output={typelib}")


def cmb_init_dev():
    version, fileformatversion = get_version()

    check_init_locale()

    # Create config files pointing to source directories
    dev_config(
        os.path.join(cambalachedir, "config.py"),
        f"""VERSION = '{version}'
FILE_FORMAT_VERSION = '{fileformatversion}'
pkgdatadir = '{cambalachedir}'
merenguedir = '{cambalachedir}'
catalogsdir = '{catalogsdir}'
""",
    )

    # Create config files pointing to source directories
    dev_config(
        os.path.join(cambalachedir, "merengue/config.py"),
        f"""VERSION = '{version}'
pkgdatadir = '{cambalachedir}'
merenguedir = '{cambalachedir}'
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

    # Ensure gresources are up to date
    compile_resource(
        cambalachedir,
        os.path.join(cambalachedir, "cambalache.gresource"),
        os.path.join(cambalachedir, "cambalache.gresource.xml"),
    )
    compile_resource(
        os.path.join(cambalachedir, "merengue"),
        os.path.join(cambalachedir, "merengue.gresource"),
        os.path.join(cambalachedir, "merengue", "merengue.gresource.xml"),
    )
    compile_resource(
        os.path.join(cambalachedir, "app"),
        os.path.join(cambalachedir, "app.gresource"),
        os.path.join(cambalachedir, "app", "app.gresource.xml"),
    )

    compile_schemas(os.path.join(datadir, "ar.xjuan.Cambalache.gschema.xml"))
    update_mime(os.path.join(datadir, "ar.xjuan.Cambalache.mime.xml"))

    create_catalogs_dir()

    compile_private()


if __name__ == "__main__":
    cmb_init_dev()
