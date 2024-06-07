pytests = [
    ['test_cmb_object.py', 30],
    ['test_import_export.py', 30],
    ['test_merengue_xml.py', 30],
    ['test_project_catalogs.py', 30],
    ['test_undo_redo.py', 30],
    ['test_cmb_window.py', 60],
]

test('Ensuring dev env', files(meson.global_source_root() / 'tools' / 'cmb_init_dev.py'), is_parallel: false)

foreach data: pytests
    test('Pytest @0@'.format(data[0]), files(data[0]), timeout: data[1])
endforeach