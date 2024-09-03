moduledir = join_paths(modulesdir, 'cmb_catalog_gen')

conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', python_bin.full_path())
conf.set('localedir', localedir)
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'cmb-catalog-gen.in',
  output: 'cmb-catalog-gen',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

install_data([
    '__init__.py',
    'cmb_catalog_db.py',
    'cmb_gir_data.py',
    ],
    install_dir: moduledir)


sources = [
  'cmb_catalog_utils.c',
]

headers = [
  'cmb_catalog_utils.h',
]

# Build private library against Gtk 3 and 4
foreach d : [['3', gtk3_dep], ['4', gtk4_dep]]
  ver = d[0]
  dep = d[1]
  libcmbcatalogutils = shared_library('cmbcatalogutils-@0@'.format(ver),
    sources,
    dependencies: dep,
    install: true,
  )

  gnome.generate_gir(
    libcmbcatalogutils,
    sources: sources + headers,
    includes: 'Gtk-@0@.0'.format(ver),
    nsversion: '@0@.0'.format(ver),
    namespace: 'CmbCatalogUtils',
    identifier_prefix: 'CmbCatalogUtils',
    symbol_prefix: 'cmb_catalog_utils',
    header: 'cmb_catalog_utils.h',
    install: true,
  )
endforeach