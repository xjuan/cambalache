wlroots_dep = dependency('wlroots-0.18', version: '>= 0.18.0')
wayland_server_dep = dependency('wayland-server', version: '>=1.22')
epoxy_dep = dependency('epoxy', version: '>=1.5')
xkbcommon = dependency(
    'xkbcommon',
    fallback: 'libxkbcommon',
    default_options: [
        'enable-tools=false',
        'enable-x11=false',
        'enable-docs=false',
        'enable-xkbregistry=false',
    ],
)

wayland_server_dep = dependency('wayland-server', version: '>=1.22')
pixman_dep = dependency('pixman-1', version: '>=0.42.0')
xkbcommon_x11_dep = dependency('xkbcommon-x11', version: '>=1.5')
x11_xcb_dep = dependency('x11-xcb', version: '>=1.8.7')

wayland_protos = dependency('wayland-protocols',
  version: '>=1.32',
  fallback: 'wayland-protocols',
  default_options: ['tests=false'],
)
wl_protocol_dir = wayland_protos.get_variable('pkgdatadir')

wayland_scanner_dep = dependency('wayland-scanner', native: true)
wayland_scanner = find_program(
  wayland_scanner_dep.get_variable('wayland_scanner'),
  native: true,
)

xdg_shell_c = custom_target(
  'xdg_shell_c',
  input: wl_protocol_dir / 'stable/xdg-shell/xdg-shell.xml',
  output: '@BASENAME@-protocol.c',
  command: [wayland_scanner, 'private-code', '@INPUT@', '@OUTPUT@'],
)

xdg_shell_server_h = custom_target(
  'xdg_shell_server_h',
  input: wl_protocol_dir / 'stable/xdg-shell/xdg-shell.xml',
  output: '@BASENAME@-protocol.h',
  command: [wayland_scanner, 'server-header', '@INPUT@', '@OUTPUT@'],
)

wayland_protocol_sources = [
  xdg_shell_c,
  xdg_shell_server_h,
 ]

sources = [
  'cmb_compositor.c',
  'cmb_wayland_source.c',
]

headers = [
  'cambalache.h',
  'cmb_wayland_source.h',
  'cmb_compositor.h',
]

cambalache = shared_library('cambalache-1',
  sources + wayland_protocol_sources,
  dependencies: [
    gtk4_dep,
    wlroots_dep,
    xkbcommon,
    wayland_server_dep,
    epoxy_dep,
    wayland_server_dep,
    pixman_dep,
    xkbcommon_x11_dep,
    x11_xcb_dep
  ],
  install: true,
)

gnome.generate_gir(
  cambalache,
  sources: sources + headers,
  includes: 'Gtk-4.0',
  nsversion: '1.0',
  namespace: 'Cambalache',
  identifier_prefix: 'Cmb',
  symbol_prefix: 'cmb',
  header: 'cambalache.h',
  install: true,
)
