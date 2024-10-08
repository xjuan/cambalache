project(
    'cambalache', 'c',
    version: '0.92.0',
    meson_version: '>= 0.64.0',
    default_options: [
        'c_std=c11',
        'warning_level=2',
        'werror=true',
    ],
)

# File format version follows app version and only changes when there is a
# change that prevents older versions to load it.
fileformatversion = '0.92.0'

python = import('python')
python_bin = python.find_installation('python3')
pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), 'cambalache')
modulesdir = join_paths(get_option('prefix'), python_bin.get_install_dir())
catalogsdir = join_paths(pkgdatadir, 'catalogs')
localedir = join_paths(get_option('prefix'), get_option('localedir'))
gnome = import('gnome')

i18n = import('i18n')


# Python requirements ['module', 'version', 'gi required version]
modules = [
    ['lxml', '>= 4.5.0'],
    ['gi', '>= 3.48.0'],
    ['gi.repository.GLib', '>= 2.80.0'],
    ['gi.repository.Gtk', '>= 3.24.0', '3.0'],
    ['gi.repository.Gtk', '>= 4.16.0', '4.0'],
    ['gi.repository.WebKit2', '>= 2.44.0', '4.1'],
    ['gi.repository.WebKit', '>= 2.44.0', '6.0'],
    ['gi.repository.GtkSource', '', '5'],
    ['gi.repository.Handy'],
    ['gi.repository.Adw'],
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
    version = (mod_ver.length() > 1) ? mod_ver[1] : ''
    gi_req = (mod_ver.length() > 2) ? mod_ver[2] : 'None'

    if mod.startswith('gi.repository.')
        mod = mod.split('.')[2]
        m = run_command(python_bin, '-c', gi_check_py.format(mod, gi_req), check: false)
    else
        m = run_command(python_bin, '-c', 'import @0@\nprint(@0@.__version__)'.format(mod), check: false)
    endif

    ver = m.stdout().strip()

    if version != ''
        found = m.returncode() == 0 and ver.version_compare(version)
    else
        found = m.returncode() == 0
    endif

    found_msg = found ? '\u001b[32mYES\u001b[0m' : '\u001b[31mNO\u001b[0m'

    message('Python module \u001b[1m@0@\u001b[0m @1@ found: @2@ @3@ @4@'.format(mod, version, found_msg, ver, gi_req))

    if all_required
        all_required = found
    endif
endforeach

assert(all_required, 'One or more required modules where not found')

gtk3_dep = dependency('pygobject-3.0', version: '>= 3.48.0')
gtk3_dep = dependency('gtk+-3.0', version: '>= 3.24.0')
gtk4_dep = dependency('gtk4', version: '>= 4.16.0')
casilda_dep = dependency('casilda-0.1', version: '>= 0.2.0', fallback: ['casilda', 'casilda_dep'])
handy_dep = dependency('libhandy-1', version: '>= 1.8.0')
adw_dep = dependency('libadwaita-1', version: '>= 1.6.0')

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
