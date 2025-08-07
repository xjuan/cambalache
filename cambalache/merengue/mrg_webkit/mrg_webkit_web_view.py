# MrgWebKitWebView Controller
#
# Copyright (C) 2022  Juan Pablo Ugarte
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation;
# version 2.1 of the License.
#
# library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
# Authors:
#   Juan Pablo Ugarte <juanpablougarte@gmail.com>
#
# SPDX-License-Identifier: LGPL-2.1-only
#

from gi.repository import GObject, WebKit

from merengue.mrg_gtk import MrgGtkWidget

from merengue import getLogger

logger = getLogger(__name__)


class MrgWebKitWebView(MrgGtkWidget):
    object = GObject.Property(type=WebKit.WebView, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def object_changed(self, old, new):
        super().object_changed(old, new)

        if self.object:
            self.object.load_html(
                """
<!DOCTYPE html>
<html>
  <head>
    <title>Cambalache WebKit</title>

    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>

div.content {
  text-align: center;
  vertical-align: middle;
  border: 3px solid lightgray;
  border-radius: 1em;
  padding: 1em;
}

body {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  min-height: calc(100vh - 2em);
}

    </style>
  </head>

  <script>

function open_url() {
  const url = document.querySelector('#url_entry').value;
  window.location.href = (url.startsWith('http')) ? url : 'http://' + url;
}

  </script>

  <body>
    <div class="content">
      <h3>WebKit Test Page</h3>
      <span>URL:</span>
      <input type="text" id="url_entry" placeholder="Enter a URL" />
      <input type="button" value="Open" onclick="open_url()" />

      <br/>
      <br/>

      <a href="https://gitlab.gnome.org/jpu/cambalache" title="gitlab.gnome.org/jpu/cambalache">Cambalache</a>
      <a href="https://webkitgtk.org"  title="webkitgtk.org">WebKitGtk</a>
      <a href="https://browserbench.org/Speedometer3.1"  title="browserbench.org/Speedometer3.1">Speedometer</a>
    </div>
  </body>
</html>
                """,
                ".",
            )

