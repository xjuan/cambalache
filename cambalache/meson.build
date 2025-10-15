moduledir = join_paths(modulesdir, 'cambalache')
merenguedir = join_paths(moduledir, 'priv')

gnome.compile_resources('cambalache',
  'cambalache.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

conf = configuration_data()
conf.set('VERSION', meson.project_version())
conf.set('fileformatversion', fileformatversion)
conf.set('pkgdatadir', pkgdatadir)
conf.set('merenguedir', merenguedir)
conf.set('catalogsdir', catalogsdir)

configure_file(
  input: 'config.py.in',
  output: 'config.py',
  configuration: conf,
  install: true,
  install_dir: moduledir
)

install_data([
    '__init__.py',
    'cmb_accessible_editor.py',
    'cmb_base.py',
    'cmb_base_file_monitor.py',
    'cmb_binding_popover.py',
    'cmb_blueprint.py',
    'cmb_context_menu.py',
    'cmb_css.py',
    'cmb_css_editor.py',
    'cmb_db.py',
    'cmb_db_inspector.py',
    'cmb_db_profile.py',
    'cmb_file_changed_bar.py',
    'cmb_fragment_editor.py',
    'cmb_gresource.py',
    'cmb_gresource_editor.py',
    'cmb_layout_property.py',
    'cmb_library_info.py',
    'cmb_list_error.py',
    'cmb_list_view.py',
    'cmb_message_notification_view.py',
    'cmb_notification.py',
    'cmb_notification_list_row.py',
    'cmb_notification_list_view.py',
    'cmb_object.py',
    'cmb_object_data.py',
    'cmb_object_data_editor.py',
    'cmb_object_editor.py',
    'cmb_object_property_editor.py',
    'cmb_base_objects.py',
    'cmb_path.py',
    'cmb_poll_notification_view.py',
    'cmb_poll_option_check.py',
    'cmb_project.py',
    'cmb_property.py',
    'cmb_property_info.py',
    'cmb_property_label.py',
    'cmb_signal_editor.py',
    'cmb_tree_expander.py',
    'cmb_type_chooser.py',
    'cmb_type_chooser_popover.py',
    'cmb_type_chooser_widget.py',
    'cmb_type_info.py',
    'cmb_ui.py',
    'cmb_ui_editor.py',
    'cmb_ui_property_editor.py',
    'cmb_ui_requires_editor.py',
    'cmb_version_notification_view.py',
    'cmb_view.py',
    'constants.py',
    'utils.py',
    ],
    install_dir: moduledir)

subdir('private')
subdir('control')
subdir('merengue')
subdir('app')
