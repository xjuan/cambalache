datadir = get_option('datadir')

desktop_file = i18n.merge_file(
  input: 'ar.xjuan.Cambalache.desktop.in',
  output: 'ar.xjuan.Cambalache.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(datadir, 'applications')
)

appstream_file = i18n.merge_file(
  input: 'ar.xjuan.Cambalache.metainfo.xml.in',
  output: 'ar.xjuan.Cambalache.metainfo.xml',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(datadir, 'metainfo')
)

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test('Validating desktop file', desktop_file_validate, args: [desktop_file])
endif

appstreamcli = find_program('appstreamcli', required: false, disabler: true)
test('Validate appstream file', appstreamcli,
     args: ['validate', '--no-net', '--explain', appstream_file])

compile_schemas = find_program('glib-compile-schemas', required: false, disabler: true)
test('Validate schema file',
     compile_schemas,
     args: ['--strict', '--dry-run', meson.current_source_dir()])


install_data('ar.xjuan.Cambalache.mime.xml',
    install_dir: join_paths(datadir, 'mime', 'packages')
)

install_data('ar.xjuan.Cambalache.gschema.xml',
  install_dir: join_paths(datadir, 'glib-2.0', 'schemas')
)

subdir('icons')