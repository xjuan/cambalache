import os
import gi

basedir = os.path.join(os.path.split(os.path.dirname(__file__))[0])

# Ensure home directory
homedir = os.path.join(basedir, ".local", "home")
os.makedirs(os.path.join(homedir, "Projects"), exist_ok=True)

os.environ["GSETTINGS_BACKEND"] = "memory"
os.environ["HOME"] = homedir

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk # noqa E402
from tools.cmb_init_dev import cmb_init_dev # noqa E402

# Disable animations
settings = Gtk.Settings.get_default()
settings.props.gtk_enable_animations = False

# Make sure we can run Cambalache from sources
cmb_init_dev()

