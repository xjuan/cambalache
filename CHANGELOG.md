# Changelog

This documents user relevant changes which are also included in
data/ar.xjuan.Cambalache.metainfo.xml.in, closed issues from
(Gitlab)[https://gitlab.gnome.org/jpu/cambalache/-/issues/] and 
packaging changes like new dependencies or build system changes.

Cambalache used even/odd minor numbers to differentiate between stable and
development releases.

## Unreleased

 - Add GtkExpression support
 - Add Blueprint support
 - Make workspace scrollable
 - Deprecate project format 0.94 and older
 - Add Brazilian Portuguese translation. John Peter Sa
 - Fix GResource list model update
 - Fix object data editor

### Packaging changes

 - Bump Casilda dependency to 1.0.
   This new version has a small API break (removed bg-color property) so the
   soname version was bumped from 0.1 to 1.0

### Issues

 - #80 "Support for blueprint file format"
 - #276 "Signal loses reference to object if defined later in the XML"
 - #257 "Add GtkExpression support"
 - #281 "new add language" John Peter Sa

## 0.96.0

2025-04-20 - GResource Release!

 - Add GResource support
 - Add internal children support
 - New project format
 - Save directly to .ui files
 - Show directory structure in navigation
 - Unified import dialog for all file types
 - Add Finnish translation. Erwinjitsu
 - Use AdwAboutDialog lo-vely
 - Add action child type to GtkDialog

### Packaging changes

 - pygobject-3.0 dependency bumped to 3.52 which depends on the new gi repository from GLib
 - libcambalacheprivate-[3|4] and its typelib are now installed under libdir/cambalache
 - libcmbcatalogutils-[3|4] and its typelib are now installed under libdir/cmb_catalog_gen
 - Gtk 3, Handy, webkit2gtk and webkitgtk are now optional dependencies

### Issues

 - #253 "Error updating UI 1: gtk-builder-error-quark: .:8:1 Invalid object type 'AdwApplicationWindow' (6)"
 - #145 "Consider Cambalache to manage resource description file for building the resource bundle"
 - #54 "Add support for internal children"
 - #255 "Unable to open files via the UI in a KDE Plasma session"
 - #260 "Wrong default for Swap setting in signals"
 - #259 "Install private shared libraries in sub directories of the main library path"
 - #263 "Translatable setting resets when label field is empty"
 - #264 "Error undoing removal of parent GtkGrid"
 - #266 "Error "Unknown internal child: entry (6)" with particular GTK 3 UI file"
 - #265 "GtkButtonBox shows too many buttons"
 - #267 "Make drag'n'drop of top-level more intuitive"
 - #269 "Failed to display some element of a validated ui file"
 - #272 "Background of compositor does not change colors, when adwaita colors are changed"
 - #273 "GtkComboBoxText items gets their translatable property removed"

## 0.94.0

2024-11-25 - Accessibility release

 - Gtk 4 and Gtk 3 accessibility support
 - Support property subclass override defaults
 - AdwDialog placeholder support
 - Improved object description in hierarchy
 - Lots of bug fixes and minor UI improvements

### Issues

 - #252 "Workspace process error / "Error updating UI 1: gtk-builder-error-quark: .:185:38 Object with ID reset not found (13)" with specific UI file"
 - #251 "GTK 3 message dialog from specific .ui file rendered incorrectly"
 - #250 "Error trying to import specific (LibreOffice) GTK 3 .ui file: "'NoneType has no attribute 'type_id'""
 - #240 "Do not show cryptic paths for imported ui files (flatpak)"
 - #202 "cambalache crashes when using"
 - #203 "AdwActionRow : wrong default for activatable property"
 - #241 "Handle adding widgets in empty workspace"
 - #234 "Hold <alt> to create object in place is not clear"
 - #242 "Support quit via Ctrl + Q"
 - #239 "Preview feature is not clear"
 - #235 "Remember last saved / open location"
 - #236 "`Import` menu operation is not clear"
 - #233 "Widget tree is confusing"
 - #137 "Add accessibility support"
 - #232 "Crashes when restarting workspace"

## 0.92.0

2024-09-27 - Adwaita + Casilda release

 - Support 3rd party libraries
 - Improved Drag&Drop support
 - Streamline headerbar
 - Replaced widget hierarchy treeview with column view
 - New custom wayland compositor for workspace
 - Improve workspace performance
 - Fix window ordering
 - Enable workspace animations
 - Basic port to Adwaita
 - Support new desktop dark style
 - Many thanks to emersion, kennylevinsen, vyivel and the wlroots community for their support and awesome project
 
### Packaging changes

 - New dependency on [casilda 0.2.0](https://gitlab.gnome.org/jpu/casilda)
   Used for workspace compositor, depends on wlroots 0.18
 - New python tool cmb-catalog-gen
 - New shared library cmbcatalogutils-[3|4] used by cmb-catalog-gen
   This library is built twice once linked with Gtk 3 and one with Gtk 4
 - Depends on Gtk 4.16 and Adwaita 1.6

### Issues

 - #231 "Workspace will crash with inserting Some Adw objects"
 - #230 "Exporting byte data messes encoding (libxml)"
 - #227 "Add casilda as meson subproject" (sid)
 - #220 "BUG: Typing cursor for style classes always in the front of style entries."
 - #222 "cannot create instance of abstract (non-instantiatable) type 'GtkWidget'"
 - #223 "Cannot add widgets to GtkSizeGroup"
 - #225 "Cambalache crashes"
 - #219 "Move existing widgets / hierarchy sections into property fields"
 - #224 "GtkPicture:file property does not work out of the box"
 - #11 "Support 3rd party libraries"
 - #216 "Cambalache 0.90.2 Segment faults"
 - #213 "Cannot open .ui file created using Gnome Builder"
 - #215 "Port UI to LibAdwaita"


## 0.90.4 

2024-03-29 - Gtk 4 port

 - Migrate main application to Gtk 4
 - Update widget catalogs to SDK 46
 - Add support for child custom fragments
 - Add add parent context menu action
 - Mark AdwSplitButton.dropdown-tooltip translatable. (Danial Behzadi)
 - Bumped version to 0.90 to better indicate we are close to version 1.0
 - Add WebKitWebContext class
 - Add brand colors

### Issues

 - #184 "Headerbar save button not enabled when "translatable" checkbox's state is changed"
 - #207 "Adding or changing data to signal doesn't activate 'Save' button"
 - #212 "[Feature] add parent"
 - #199 "Copy and pasting messes references between widgets"
 - #196 "postinstall.py is trying to modify files in prefix."
 - #201 "AdwToolbarView needs special child types"
 - #220 "BUG: Typing cursor for style classes always in the front of style entries."


## 0.16.0 

2023-09-24: GNOME 45 Release!

 - Bump SDK dependency to SDK 45
 - Add support for types and properties added in SDK 45
 - Marked various missing translatable properties

### Issues

 - #190 "Missing translatable property for Gtk.ColumnViewColumn.title"
 - #190 "Unassigned local variable"


## 0.14.0 

2023-09-07: GMenu release!

 - Add GMenu support
 - Add UI requirements edit support
 - Add Swedish translation. Anders Jonsson
 - Updated Italian translation. Lorenzo Capalbo
 - Show deprecated and not available warnings for Objects, properties and signals
 - Output minimum required library version instead of latest one
 - Fix output for templates with inline object properties
 - Various optimizations and bug fixes
 - Bump test coverage to 66%

### Issues

 - #185 "Unable to import certain files converted from GTK3 to GTK4""
 - #177 "Panel is not derivable"
 - #173 "Cambalache 0.12.0 can't open 0.10.3 project"


## 0.12.0 

2023-06-16: New Features release!

 - User Templates: use your templates anywhere in your project
 - Workspace CSS support: see your CSS changes live
 - GtkBuildable Custom Tags: support for styles, items, etc
 - Property Bindings: bind your property to any source property
 - XML Fragments: add any xml to any object or UI as a fallback
 - Preview mode: hide placeholders in workspace
 - WebKit support: new widget catalog available
 - External objects references support
 - Add support for GdkPixbuf, GListModel and GListStore types
 - Add missing child type attributes to Gtk4 GtkActionBar (B. Teeuwen)
 - Added French Translation (rene-coty)

### Issues

 - #121 "Adding handy fails silently without libhandy installed"
 - #113 "Add button/toggle to disable the placeholders and make the window look like it would look as an app"
 - #123 "Export should be more user-friendly"
 - #130 "GtkAboutDialog missing properties"
 - #135 "List of string properties that should be translatable in Adw"
 - #136 "Can't build via Flatpak"
 - #138 "libadwaita widgets aren't categorized"
 - #122 "Handy widgets not correctly categorized."
 - #96 "Window resize itself when cut content of notebook tab and go to first tab"
 - #101 "Right clicking after deselcting button, brokes mouse input"
 - #120 "Box doesn't remove empty space"
 - #147 "The "Close" button doesn't close the "About" dialog."
 - #146 "Scrolling a properties pane conflicts with mousewheel handling of property widgets"
 - #143 "Support for nested files"
 - #148 "bug: preview display"
 - #156 "GDK_BACKEND leaks to workspace process"
 - #154 "GtkPaned: for properties to be set consistently, need to use start-child and end-child instead of child
 - #160 "Faster prototyping"
 - #166 "Allow external Widget or/and from another ui template"
 - #163 "Add named object to Gtk.Stack"
 - #170 "Support for actions (GtkActionable, menu models)"
 - #169 "[main] GtkOrientable is missing in GtkBox properties (maybe in others too)"
 - #167 "Gtk*Selection models are missing the model property"
 - #168 "Is there a way to add string items to a GtkStringList?"
 - #171 "Extended support for inline objects"
 - #172 "Certain Adw widgets are not availabe (AdwEntryRow)"


## 0.10.0 

2022-06-15: 3rd party libs release!

 - Add Adwaita and Handy library support
 - Add inline object properties support (only Gtk 4)
 - Add special child type support (GtkWindow title widget)
 - Improve clipboard functionality
 - Add support for reordering children position
 - Add/Improve worspace support for GtkMenu, GtkNotebook, GtkPopover, GtkStack, GtkAssistant, GtkListBox, GtkMenuItem and GtkCenterBox
 - New property editors for icon name and color properties
 - Add support for GdkPixbuf, Pango, Gio, Gdk and Gsk flags/enums types
 - Add Ukrainian translation (Volodymyr M. Lisivka)
 - Add Italian translation (capaz)
 - Add Dutch translation (Gert)

### Issues

 - #47 "Proper ui file(which compile properly), fails to open in cambalache and show error"
 - #79 "Change column/row count of GtkBox and GtkGrid"
 - #81 "No way to add rows to GtkListBox"
 - #68 "Trouble with GtkHeaderBar"
 - #82 "Can't change x and y values of widgets in Gtk4 when using GtkFixed"
 - #62 "Many widget-specific properties appear to be missing"
 - #83 "Gettext domain is not initialized properly"
 - #66 "Allow adding new items directly in tree view instead of (only) through preview view"
 - #86 "Automatically restart merengue when merengue crashes"
 - #89 "Error `AttributeError: 'NoneType' object has no attribute 'info'` when deleting UI file"
 - #90 "Cambalache fails to import valid glade/ui files"
 - #75 "How to use GtkStack"
 - #78 "How to use GTKAssistant"
 - #63 "Allow automatically exporting on save (or make it easier to do so)"
 - #91 "Unable to export"
 - #85 "Provide icon selection for Button / Image"
 - #92 "'Debug Project Data' does nothing"
 - #9 "Support for libadwaita and libhandy"
 - #59 "Reordering children in a parent"
 - #100 "Signals get broken"
 - #105 "Child layout properties not available when parent is a subclass (AdwHeaderBar)"
 - #102 "Popovers are not visible"
 - #104 "Error when trying to add children to buttonbox"
 - #98 "No way to add tab in Notebook"
 - #108 "Popovers stay on scene after deleting file which contains them"
 - #109 "Cambalache adds to container GtkRecentChooserMenu even if prints that this won't happen"
 - #110 "Screen flashing when creating GBinding"
 - #116 "Error when trying to click at Notebook content"
 - #117 "Error `'NoneType' object has no attribute 'props'` when changing notebook tab"
 - #115 "Cannot copy/paste widget"
 - #69 "Undo and redo operations don't always match up"


## 0.8.0 

2021-12-09: UX improvements Release!

 - New Type chooser bar
 - Workspace placeholder support
 - Translatable properties support (Philipp Unger)
 - Clipboard actions support (Copy, Paste, Cut)
 - Better unsupported features report
 - New Matrix channel #cambalache:gnome.org
 - You can now also support Cambalache on Liberapay

### Issues

 - #22: Gtk.AboutDialog: license bug
 - #10: Export widgets layout data packed in GtkGrid
 - #23: Better appdata summary
 - #25: Error about target version mismatch
 - #29: Error opening project
 - #27: Needs a better icon
 - #31: Newest ver (git) doesn't display loaded UI
 - #34: Translations aren't working in the interactive tour
 - #35: Interactive tour isn't working anymore
 - #30: Gtk types listed in Cambalache
 - #36: Can't build Flatpak after the update of the german translation
 - #38: Add translatable metadata to CmbPropertyInfo
 - #37: Add support for translatable properties
 - #39: Save window state (Philipp Unger)
 - #41: Add clipboard support
 - #33: No context menu on left pane, the "project view"


## 0.7.0 

2021-08-08: New translations release!

 - Add Czech translation. Vojtěch Perník
 - Add German translation. PhilProg
 - Add x-cambalache mimetype with icon


## 0.6.0 

2021-07-21: First public release!

 - Suport for both Gtk 3 and 4 versions
 - Import and export multiple UI at once
 - Support plain (no custom tags) GtkBuilder features 
 - Undo / Redo stack
 - LGPL version 2.1
