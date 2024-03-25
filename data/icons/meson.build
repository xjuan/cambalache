application_id = 'ar.xjuan.Cambalache'

scalable_dir = 'hicolor' / 'scalable' / 'apps'
install_data(
  scalable_dir / ('@0@.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / scalable_dir
)

mimetypes_dir = 'hicolor' / 'scalable' / 'mimetypes'
install_data(
  mimetypes_dir / ('@0@.mime.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / mimetypes_dir
)

symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  symbolic_dir / ('@0@-symbolic.svg').format(application_id),
  install_dir: get_option('datadir') / 'icons' / symbolic_dir
)
