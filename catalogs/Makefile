CAMBALACHE_DB=flatpak run \
	--env=LD_LIBRARY_PATH=../tools \
	--env=GI_TYPELIB_PATH=../tools \
	--share=ipc \
	--socket=fallback-x11 \
	--socket=wayland \
	--device=all \
	--filesystem=host \
	--command=python3 \
	org.gnome.Sdk//46 \
	../tools/cambalache-db.py

BASE_CATALOG_FILES = \
	glib/gobject-2.0.xml \
	glib/gio-2.0.xml \
	gdkpixbuf/gdkpixbuf-2.0.xml \
	pango/pango-1.0.xml

GTK3_DEPS = \
	${BASE_CATALOG_FILES} \
	gtk/gdk-3.0.xml

GTK4_DEPS = \
	${BASE_CATALOG_FILES} \
	gtk/gdk-4.0.xml \
	gtk/gsk-4.0.xml

CATALOG_FILES = \
	${BASE_CATALOG_FILES} \
	${GTK3_DEPS} \
	${GTK4_DEPS} \
	gtk/gtk-4.0.xml \
	gtk/gtk+-3.0.xml \
	gnome/webkitgtk-6.0.xml \
	gnome/webkit2gtk-4.1.xml \
	gnome/libhandy-1.xml \
	gnome/libadwaita-1.xml \
	$(NULL)


all: ${CATALOG_FILES}

glib/gobject-2.0.xml: glib/GObject.xml
	${CAMBALACHE_DB} \
		--gir /usr/share/gir-1.0/GObject-2.0.gir \
		--types GObject GBinding GBindingFlags \
		--boxed-types GStrv GBytes\
		--extra-data glib/GObject.xml \
		--skip-types GBinding \
		--output $@

glib/gio-2.0.xml: glib/Gio.xml
	${CAMBALACHE_DB} \
		--dependencies gobject-2.0 \
		--gir /usr/share/gir-1.0/Gio-2.0.gir \
		--types GFile GListStore GListModel GMenuModel \
		--extra-data glib/Gio.xml \
		--exclude-objects \
		--output $@

gdkpixbuf/gdkpixbuf-2.0.xml:
	${CAMBALACHE_DB} \
		--dependencies gio-2.0 \
		--gir /usr/share/gir-1.0/GdkPixbuf-2.0.gir \
		--types GdkPixbuf \
		--exclude-objects \
		--output $@

pango/pango-1.0.xml:
	${CAMBALACHE_DB} \
		--dependencies gio-2.0 \
		--gir /usr/share/gir-1.0/Pango-1.0.gir \
		--exclude-objects \
		--output $@

gtk/gdk-3.0.xml:
	${CAMBALACHE_DB} \
		--dependencies pango-1.0 gdkpixbuf-2.0 \
		--gir /usr/share/gir-1.0/Gdk-3.0.gir \
		--boxed-types GdkColor GdkRGBA \
		--exclude-objects \
		--output $@

gtk/gdk-4.0.xml:
	${CAMBALACHE_DB} \
		--target-gtk4 \
		--dependencies pango-1.0 gdkpixbuf-2.0 \
		--gir /usr/share/gir-1.0/Gdk-4.0.gir \
		--boxed-types GdkRGBA GdkContentFormats\
		--exclude-objects \
		--output $@

gtk/gsk-4.0.xml:
	${CAMBALACHE_DB} \
		--target-gtk4 \
		--dependencies pango-1.0 gdkpixbuf-2.0 \
		--gir /usr/share/gir-1.0/Gsk-4.0.gir \
		--boxed-types GskTransform \
		--exclude-objects \
		--output $@

gtk/gtk+-3.0.xml: gtk/Gtk.xml ${GTK3_DEPS}
	${CAMBALACHE_DB} \
		--dependencies gdk-3.0 \
		--gir /usr/share/gir-1.0/Gtk-3.0.gir \
		--external-catalogs ${GTK3_DEPS} \
		--extra-data gtk/Gtk.xml \
		--output $@

gtk/gtk-4.0.xml: gtk/Gtk.xml ${GTK4_DEPS}
	${CAMBALACHE_DB} \
		--target-gtk4 \
		--dependencies gdk-4.0 gsk-4.0 \
		--gir /usr/share/gir-1.0/Gtk-4.0.gir \
		--external-catalogs ${GTK4_DEPS} \
		--extra-data gtk/Gtk.xml \
		--skip-types GtkActivateAction GtkMnemonicAction GtkNamedAction GtkNeverTrigger GtkNothingAction GtkSignalAction GtkPrintJob GtkStackPage \
		--output $@ && true

gnome/libhandy-1.xml: gtk/gtk+-3.0.xml
	${CAMBALACHE_DB} \
		--dependencies gtk+-3.0 \
		--gir /usr/share/gir-1.0/Handy-1.gir \
		--external-catalogs ${GTK3_DEPS} gtk/gtk+-3.0.xml \
		--extra-data gnome/Handy.xml \
		--skip-types HdySwipeTracker HdyValueObject \
		--output $@

gnome/webkit2gtk-4.1.xml: gtk/gtk+-3.0.xml
	${CAMBALACHE_DB} \
		--dependencies gtk+-3.0 \
		--gir /usr/share/gir-1.0/WebKit2-4.1.gir \
		--external-catalogs ${GTK3_DEPS} gtk/gtk+-3.0.xml \
		--types WebKitWebViewBase WebKitWebView WebKitSettings WebKitWebContext \
		--extra-data gnome/WebKit2.xml \
		--skip-types WebKitWebViewBase \
		--output $@

gnome/libadwaita-1.xml: gtk/gtk-4.0.xml
	${CAMBALACHE_DB} \
		--target-gtk4 \
		--dependencies gtk-4.0 \
		--gir /usr/share/gir-1.0/Adw-1.gir \
		--external-catalogs ${GTK4_DEPS} gtk/gtk-4.0.xml \
		--extra-data gnome/Adwaita.xml \
		--skip-types AdwAnimation AdwSwipeTracker AdwPropertyAnimationTarget \
		--output $@

gnome/webkitgtk-6.0.xml: gtk/gtk-4.0.xml
	${CAMBALACHE_DB} \
		--target-gtk4 \
		--dependencies gtk-4.0 \
		--gir /usr/share/gir-1.0/WebKit-6.0.gir \
		--external-catalogs ${GTK4_DEPS} gtk/gtk-4.0.xml \
		--types WebKitWebViewBase WebKitWebView WebKitSettings WebKitWebContext \
		--extra-data gnome/WebKit2.xml \
		--skip-types WebKitWebViewBase \
		--output $@

.PHONY: all clean

clean:
	rm -rf ${CATALOG_FILES}


