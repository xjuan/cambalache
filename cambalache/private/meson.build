
sources = [
  'cmb_private.c',
  'cmb_private_svg.c',
]

headers = [
  'cmb_private.h',
  'cmb_private_svg.h',
]

cc = meson.get_compiler('c')
m_dep = cc.find_library('m')

# Build private library against Gtk 3 and 4
foreach d : [['3', gtk3_dep], ['4', [gtk4_dep, m_dep]]]
  ver = d[0]
  dep = d[1]
  libcmbprivate = shared_library('cambalacheprivate-@0@'.format(ver),
    sources,
    dependencies: dep,
    install: true,
    install_dir: privatecambalachedir,
    override_options: [
        'werror=false',
    ],
  )

  gnome.generate_gir(
    libcmbprivate,
    sources: sources + headers,
    includes: 'Gtk-@0@.0'.format(ver),
    nsversion: '@0@.0'.format(ver),
    namespace: 'CambalachePrivate',
    identifier_prefix: 'CmbPrivate',
    symbol_prefix: 'cmb_private',
    header: 'cmb_private.h',
    install: true,
    install_dir_typelib: privatecambalachedir,
  )
endforeach
