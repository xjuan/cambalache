import sys
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk  # noqa: E402


class Preview(Gtk.Application):
    def __init__(self, filename):
        self.filename = filename

        super().__init__(application_id="ar.xjuan.CmbPreview")
        GLib.set_application_name("Cmb Simple previewer")

    def do_activate(self):
        builder = Gtk.Builder()
        builder.add_from_file(self.filename)

        for w in builder.get_objects():
            if isinstance(w, Gtk.Window):
                self.add_window(w)
                w.present()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} file.ui")
        exit()

    app = Preview(sys.argv[1])
    app.run()
