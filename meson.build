project(
    'cambalache', 'c',
    version: '0.99.8',
    meson_version: '>= 1.1.0',
    default_options: [
        'c_std=c11',
        'warning_level=2',
        'werror=true',
    ],
)

# File format version follows app version and only changes when there is a
# change that prevents older versions to load it.
fileformatversion = '0.99.0'

python = import('python')
python_bin = python.find_installation('python3')
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), 'cambalache')
modulesdir = join_paths(get_option('prefix'), python_bin.get_install_dir())
catalogsdir = join_paths(pkgdatadir, 'catalogs')
localedir = join_paths(get_option('prefix'), get_option('localedir'))
gnome = import('gnome')

i18n = import('i18n')
privatecambalachedir = join_paths(get_option('prefix'), get_option('libdir'), 'cambalache')
privatecmb_catalog_gendir = join_paths(get_option('prefix'), get_option('libdir'), 'cmb_catalog_gen')

# Hard dependencies
libxml2_dep = dependency('libxml-2.0', version: '>= 2.9.0')
pygobject_dep = dependency('pygobject-3.0', version: '>= 3.52.0')
gtk4_dep = dependency('gtk4', version: '>= 4.18.0')
casilda_dep = dependency('casilda-1.0', version: '>= 1.0.0', fallback: ['casilda', 'casilda_dep'])
adw_dep = dependency('libadwaita-1', version: '>= 1.7.0')
gtksource_dep = dependency('gtksourceview-5', version: '>= 5.16.0')

gtk3_dep = dependency('gtk+-3.0', version: '>= 3.24.0', required: get_option('with-gtk-3'))
handy_dep = dependency('libhandy-1', version: '>= 1.8.0', required: get_option('with-handy'))
webkit_dep = dependency('webkitgtk-6.0', version: '>= 2.48.0', required: get_option('with-webkitgtk-6'))
webkit2_dep = dependency('webkit2gtk-4.1', version: '>= 2.48.0', required: get_option('with-webkit2gtk-4_1'))

# Python requirements ['module', 'version', 'gi required version]
modules = [
    ['lxml', ''],
    ['gi', ''],
    ['gi.repository.GLib', '2.0'],
    ['gi.repository.Gtk', '4.0'],
    ['gi.repository.GtkSource', '5'],
    ['gi.repository.Adw', '1'],

    ['gi.repository.Gtk', '3.0', gtk3_dep.found()],
    ['gi.repository.Handy', '1', handy_dep.found()],
    ['gi.repository.WebKit', '6.0', webkit_dep.found()],
    ['gi.repository.WebKit2', '4.1', webkit2_dep.found()],
]

# Python script to check for gi repository module
gi_check_py = '''
import gi
if @1@:
  gi.require_version('@0@', '@1@')
from gi.repository import @0@
if hasattr(@0@, "MAJOR_VERSION"):
  print("{}.{}.{}".format(@0@.MAJOR_VERSION, @0@.MINOR_VERSION, @0@.MICRO_VERSION))
'''

all_required = true

foreach mod_ver: modules
    mod = mod_ver[0]
    gi_req = (mod_ver.length() > 1) ? mod_ver[1] : 'None'
    is_required = (mod_ver.length() > 2) ? mod_ver[2] : true

    if not is_required
        continue
    endif

    if mod.startswith('gi.repository.')
        mod = mod.split('.')[2]
        m = run_command(python_bin, '-c', gi_check_py.format(mod, gi_req), check: false)
    else
        m = run_command(python_bin, '-c', 'import @0@\nprint(@0@.__version__)'.format(mod), check: false)
    endif

    ver = m.stdout().strip()
    found = m.returncode() == 0
    found_msg = found ? '\u001b[32mYES\u001b[0m' : '\u001b[31mNO\u001b[0m'

    message('Python module \u001b[1m@0@ @1@\u001b[0m found: @2@ @3@'.format(mod, gi_req, found_msg, ver))

    if all_required
        all_required = found
    endif
endforeach

assert(all_required, 'One or more required modules where not found')

subdir('data')
subdir('cambalache')
subdir('catalogs')
subdir('po')
subdir('tools')
subdir('tests')

gnome.post_install(
  glib_compile_schemas: true,
  update_desktop_database: true,
  update_mime_database: true,
  gtk_update_icon_cache: true,
)

meson.add_install_script('postinstall.py', modulesdir)
