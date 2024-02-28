import os
import gi
import atexit
import signal
import time
import tempfile

from gi.repository import GLib
from tools.cmb_init_dev import cmb_init_dev

basedir = os.path.dirname(__file__)

# We want a clean state for tests
os.environ["GSETTINGS_BACKEND"] = "memory"

tmpdirname = tempfile.TemporaryDirectory()
COMPOSITOR_SOCKET = os.path.join(tmpdirname.name, "cmb-weston.sock")
compositor_pid = None


def wait_for_file(path, seconds):
    i = 0
    while not os.path.exists(path):
        time.sleep(0.1)
        i += 1
        if i >= seconds * 10:
            return True

    return False


def run_compositor():
    global compositor_pid

    compositor = GLib.find_program_in_path("weston")

    compositor_pid, stdin, stdout, stderr = GLib.spawn_async(
        [compositor, f"--config={basedir}/weston.ini", "-S", COMPOSITOR_SOCKET, "--width=1280", "--height=720"],
        envp=[f"{var}={val}" for var, val in os.environ.items()],
        flags=GLib.SpawnFlags.DEFAULT | GLib.SpawnFlags.STDOUT_TO_DEV_NULL | GLib.SpawnFlags.STDERR_TO_DEV_NULL,
        standard_input=False,
        standard_output=False,
    )

    # Setup environment to use compositor
    os.environ["GDK_BACKEND"] = "wayland"
    os.environ["WAYLAND_DISPLAY"] = COMPOSITOR_SOCKET

    # Wait for compositor to startup
    if wait_for_file(COMPOSITOR_SOCKET, 2):
        assert False


def close_compositor():
    try:
        GLib.spawn_close_pid(compositor_pid)
        os.kill(compositor_pid, signal.SIGTERM)
        tmpdirname.cleanup()
    except Exception:
        pass


# Make sure the right gtk version is loaded
gi.require_version("Gtk", "4.0")

# Make sure we can run Cambalache from sources
cmb_init_dev()

# Start a compositor
#run_compositor()

# Close compositor at exit
#atexit.register(close_compositor)
