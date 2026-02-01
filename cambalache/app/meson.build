moduledir = join_paths(modulesdir, 'cambalache', 'app')

gnome.compile_resources('app',
  'app.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', python_bin.full_path())
conf.set('localedir', localedir)
conf.set('pkgdatadir', pkgdatadir)
conf.set('merenguedir', merenguedir)

configure_file(
  input: 'cambalache.in',
  output: 'cambalache',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

install_data([
    '__init__.py',
    'cmb_application.py',
    'cmb_donate_dialog.py',
    'cmb_scrolled_window.py',
    'cmb_window.py',
    'cmb_tutor.py',
    'cmb_tutorial.py',
    'cmb_np_dialog.py',
    ],
    install_dir: moduledir)