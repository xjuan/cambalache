![Cambalache](cambalache/app/images/logo-horizontal.svg)

**Cambalache** is a sophisticated RAD tool for GTK 4 and GTK 3, featuring a clean MVC design
and a data model-first philosophy. This architectural approach translates to comprehensive
feature coverage with minimal developer intervention for basic support.

![Data Model Diagram](datamodel.svg)

To support multiple GTK versions, it renders the workspace out-of-process using a 
custom Wayland compositor widget based on **wlroots**.

![Merengue Diagram](merengue.svg)

---

## License

**Cambalache** is distributed under the [GNU Lesser General Public License](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html),
version 2.1 (LGPL) as described in the `COPYING` file.

**Tools** are distributed under the [GNU General Public License](https://www.gnu.org/licenses/gpl-2.0.en.html),
version 2 (GPL) as described in the `COPYING.GPL` file.

---

## Source Code

Source code lives on **GNOME GitLab** [here](https://gitlab.gnome.org/jpu/cambalache)

```bash
git clone https://gitlab.gnome.org/jpu/cambalache.git
```

---

## Dependencies

- **Python 3** - Cambalache is written in Python
- **[Meson](http://mesonbuild.com)** build system
- **[GTK](http://www.gtk.org)** 3 and 4
- **python-gi** - Python GTK bindings
- **python3-lxml** - Python libxml2 bindings
- **[Casilda](https://gitlab.gnome.org/jpu/casilda)** - Workspace custom compositor

---

## Flathub

**Flathub** is the place to get and distribute apps for all of desktop Linux. 
It is powered by **Flatpak**, allowing Flathub apps to run on almost any Linux distribution.

Instructions on how to install Flatpak can be found [here](https://flatpak.org/setup/).

You can get the official build [here](https://flathub.org/apps/details/ar.xjuan.Cambalache)

### Installation

```bash
flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub ar.xjuan.Cambalache
```

---

## Flatpak

### Build Dependencies

Use the following commands to install build dependencies:

```bash
flatpak remote-add --user --if-not-exists gnome-nightly https://nightly.gnome.org/gnome-nightly.flatpakrepo
flatpak install --user org.gnome.Sdk//master
flatpak install --user org.gnome.Platform//master
```

### Building Your Bundle

Build your bundle with the following commands:

```bash
flatpak-builder --force-clean --repo=repo build ar.xjuan.Cambalache.json
flatpak build-bundle repo cambalache.flatpak ar.xjuan.Cambalache
flatpak install --user cambalache.flatpak
```

Or if you have `make` installed in your host:

```bash
make install
```

This will create the Flatpak repository, then the bundle and install it.

### Running

```bash
flatpak run --user ar.xjuan.Cambalache//master
```

---

## Manual Installation

This is a regular **Meson** package and can be installed the usual way.

```bash
# Configure project in _build directory
meson setup --wipe --prefix=~/.local _build .

# Build and install in ~/.local
ninja -C _build install
```

To run it from `.local/` you might need to setup a few environment variables
depending on your distribution:

```bash
export PYTHONPATH=~/.local/lib/python3/dist-packages/
export LD_LIBRARY_PATH=~/.local/lib/x86_64-linux-gnu/
export GI_TYPELIB_PATH=~/.local/lib/x86_64-linux-gnu/girepository-1.0/
cambalache
```

---

## Docker

While Docker is not meant for UI applications, it is possible to build an image with **Cambalache** and run it.

### Build the Image

```bash
docker build -t cambalache .
```

### Running on Linux

**On Wayland:**
```bash
docker run \
    -e XDG_RUNTIME_DIR=/tmp \
    -e WAYLAND_DISPLAY=$WAYLAND_DISPLAY \
    -v $XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:/tmp/$WAYLAND_DISPLAY  \
    --user=$(id -u):$(id -g) \
    cambalache
```

**On X Server:**
```bash
xhost +local:
docker run -v /tmp/.X11-unix:/tmp/.X11-unix cambalache
```

> **Note:** There is no official support for Docker, please use Flatpak if possible.

---

## MS Windows

Instructions to run in **MS Windows** are [here](README.win.md)

> **Note:** There is no official support for Windows yet, these instructions should be taken with a grain of salt as they might not work on all Windows versions or be obsolete.

---

## MacOS

Instructions to run in **MacOS** are [here](README.mac.md)

> **Note:** There is no official support for MacOS yet, these instructions should be taken with a grain of salt as they might not work on all MacOS versions or be obsolete.

---

## Running from Sources

To run it without installing, use the `run-dev.sh` script.
It will automatically compile Cambalache under the `.local` directory and set up all environment 
variables needed to run the app from the source directory.
(Follow manual installation to ensure you have everything needed)

```bash
./run-dev.py
```

> This is meant for **Cambalache development only**.

---

## Contributing

If you are interested in contributing, you can open an issue [here](https://gitlab.gnome.org/jpu/cambalache/-/issues) 
and/or a merge request [here](https://gitlab.gnome.org/jpu/cambalache/-/merge_requests)

---

## Contact

You can hang with us and ask us questions on **Matrix** at **#cambalache:gnome.org**

**[Join us on Matrix](https://matrix.to/#/#cambalache:gnome.org)**

---

## Financial Support

You can financially support **Cambalache** development on **Liberapay** or **Patreon**
like all these [people](./SUPPORTERS.md) did.

### [Liberapay](https://liberapay.com/xjuan)
- Liberapay is a recurrent donations platform
- Run by a non-profit organization
- Source code is public
- No commission fee
- ~5% payment processing fee

### [Patreon](https://www.patreon.com/cambalache)
- Patreon is a membership platform for creators
- Run by private company
- No source code available
- ~8% commission fee
- ~8% payment processing fee

---

## cmb-catalog-gen

This tool is used to generate **Cambalache catalogs** from GIR files.

A catalog is a XML file with all the necessary data for Cambalache to produce UI files with widgets from a particular library,
this includes the different GTypes, with their properties, signals and everything else except the actual
object implementations.
