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

import gi

from gi.repository import GObject, Gtk, WebKit2

from merengue.mrg_gtk import MrgGtkWidget

from merengue import getLogger

logger = getLogger(__name__)


class MrgWebKitWebView(MrgGtkWidget):
    object = GObject.Property(type=WebKit2.WebView,
                              flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.warning('MrgWebKitWebView __init__')

    def object_changed(self, old, new):
        super().object_changed(old, new)

        if self.object:
            self.object.load_html("""
<!DOCTYPE html>
<html>
  <head>
    <title>Cambalache WebKit</title>

    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>

html, body {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  display: table;
}

div.content {
  display: table-cell;
  text-align: center;
  vertical-align: middle;
  border: 3px groove lightgray;
  border-radius: 1em;
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
      <input type="text" id="url_entry" />
      <input type="button" value="Open" onclick="open_url()" />

      <br/>
      <br/>

      <a href="https://gitlab.gnome.org/jpu/cambalache">Cambalache</a>
      <a href="https://webkitgtk.org/">WebKitGtk</a>
    </div>
  </body>
</html>
                """,
                '.')


class MrgDummyWebViewProxy(Gtk.Label):
    __gtype_name__ = 'MrgDummyWebViewProxy'

    automation_presentation_type = GObject.Property(type=WebKit2.AutomationBrowsingContextPresentation, default=WebKit2.AutomationBrowsingContextPresentation.WINDOW, flags=GObject.ParamFlags.READWRITE)
    camera_capture_state = GObject.Property(type=WebKit2.MediaCaptureState, default=WebKit2.MediaCaptureState.NONE, flags=GObject.ParamFlags.READWRITE)
    default_content_security_policy = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    display_capture_state = GObject.Property(type=WebKit2.MediaCaptureState, default=WebKit2.MediaCaptureState.NONE, flags=GObject.ParamFlags.READWRITE)
    editable = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    is_controlled_by_automation = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    is_ephemeral = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    is_muted = GObject.Property(type=bool, default=False, flags=GObject.ParamFlags.READWRITE)
    microphone_capture_state = GObject.Property(type=WebKit2.MediaCaptureState, default=WebKit2.MediaCaptureState.NONE, flags=GObject.ParamFlags.READWRITE)
    related_view = GObject.Property(type=WebKit2.WebView, flags=GObject.ParamFlags.READWRITE)
    settings = GObject.Property(type=WebKit2.Settings, flags=GObject.ParamFlags.READWRITE)
    user_content_manager = GObject.Property(type=WebKit2.UserContentManager, flags=GObject.ParamFlags.READWRITE)
    web_context = GObject.Property(type=WebKit2.WebContext, flags=GObject.ParamFlags.READWRITE)
    web_extension_mode = GObject.Property(type=WebKit2.WebExtensionMode, default=WebKit2.WebExtensionMode.NONE, flags=GObject.ParamFlags.READWRITE)
    website_policies = GObject.Property(type=WebKit2.WebsitePolicies, flags=GObject.ParamFlags.READWRITE)
    zoom_level = GObject.Property(type=float, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.props.label = 'WebKit2.WebView\nplaceholder'
        self.props.justify = Gtk.Justification.CENTER


class MrgDummyWebView(MrgGtkWidget):
    object = GObject.Property(type=MrgDummyWebViewProxy,
                              flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
