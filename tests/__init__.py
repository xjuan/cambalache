import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk # noqa E402
from tools.cmb_init_dev import cmb_init_dev # noqa E402

# Disable animations
settings = Gtk.Settings.get_default()
settings.props.gtk_enable_animations = False

# Make sure we can run Cambalache from sources
cmb_init_dev()

