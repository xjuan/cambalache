install_data([
    'glib/gobject-2.0.xml',
    'glib/gio-2.0.xml',
    'gdkpixbuf/gdkpixbuf-2.0.xml',
    'pango/pango-1.0.xml',
    'gtk/gdk-4.0.xml',
    'gtk/gsk-4.0.xml',
    'gtk/gtk-4.0.xml',
    'gnome/libadwaita-1.xml'
    ],
    install_dir: catalogsdir)

foreach data: [
    [gtk3_dep, ['atk/atk-1.0.xml', 'gtk/gdk-3.0.xml', 'gtk/gtk+-3.0.xml']],
    [handy_dep, ['gnome/libhandy-1.xml']],
    [webkit_dep, ['gnome/webkitgtk-6.0.xml']],
    [webkit2_dep, ['gnome/webkit2gtk-4.1.xml']],
]
    if data[0].found()
        install_data(data[1], install_dir: catalogsdir)
    endif
endforeach