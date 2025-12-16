#
# Cambalache notification system
#
# Copyright (C) 2025  Juan Pablo Ugarte
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

import os
import json
import threading
import http.client
import time
import platform

from uuid import uuid4
from urllib.parse import urlparse
from .config import VERSION
from gi.repository import GObject, GLib, Gio, Gdk, Gtk, Adw, HarfBuzz
from cambalache import getLogger
from . import utils

logger = getLogger(__name__)


class CmbBaseData(GObject.GObject):
    def __init__(self, **kwargs):
        for prop in self.list_properties():
            name = prop.name.replace("-", "_")

            if name not in kwargs:
                continue

            value = kwargs[name]

            if isinstance(value, dict) and prop.value_type in GTYPE_PTYHON:
                Klass = GTYPE_PTYHON[prop.value_type]
                kwargs[name] = Klass(**value)

        super().__init__(**kwargs)

    def dict(self):
        retval = {}

        for prop in self.list_properties():
            name = prop.name.replace("-", "_")

            value = self.get_property(prop.name)

            if prop.value_type in GTYPE_PTYHON:
                retval[name] = value.dict() if value else None
            elif not isinstance(value, GObject.Object):
                retval[name] = value

        return retval


class CmbPollData(CmbBaseData):
    id = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    title = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    description = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    options = GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)
    allowed_votes = GObject.Property(type=int, default=1, flags=GObject.ParamFlags.READWRITE)
    start_date = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)
    end_date = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)


class CmbPollResult(CmbBaseData):
    votes = GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)
    total = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)


GTYPE_PTYHON = {CmbPollData.__gtype__: CmbPollData, CmbPollResult.__gtype__: CmbPollResult}


class CmbNotification(CmbBaseData):
    center = GObject.Property(type=GObject.Object, flags=GObject.ParamFlags.READWRITE | GObject.ParamFlags.CONSTRUCT_ONLY)

    type = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    start_date = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)
    end_date = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)


class CmbVersionNotification(CmbNotification):
    version = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    release_notes = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    read_more_url = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)


class CmbMessageNotification(CmbNotification):
    title = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    message = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)


class CmbPollNotification(CmbNotification):
    poll = GObject.Property(type=CmbPollData, flags=GObject.ParamFlags.READWRITE)
    results = GObject.Property(type=CmbPollResult, flags=GObject.ParamFlags.READWRITE)
    my_votes = GObject.Property(type=object, flags=GObject.ParamFlags.READWRITE)


class CmbNotificationCenter(GObject.GObject):
    __gsignals__ = {
        "new-notification": (GObject.SignalFlags.RUN_FIRST, None, (CmbNotification,)),
    }

    # Settings
    enabled = GObject.Property(type=bool, default=True, flags=GObject.ParamFlags.READWRITE)
    uuid = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)
    next_request = GObject.Property(type=int, flags=GObject.ParamFlags.READWRITE)
    notifications = GObject.Property(type=str, flags=GObject.ParamFlags.READWRITE)

    store = GObject.Property(type=Gio.ListStore, flags=GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.retry_interval = 2
        self.user_agent = self.__get_user_agent()
        self.store = Gio.ListStore(item_type=CmbNotification)
        self.settings = Gio.Settings(schema_id="ar.xjuan.Cambalache.notification")

        for prop in ["enabled", "uuid", "next-request", "notifications"]:
            self.settings.bind(prop, self, prop.replace("-", "_"), Gio.SettingsBindFlags.DEFAULT)

        backend = urlparse(os.environ.get("CMB_NOTIFICATION_URL", "https://xjuan.ar:1934"))
        if backend.hostname == "localhost":
            self.REQUEST_INTERVAL = 4
            self.enabled = True
        else:
            self.REQUEST_INTERVAL = 24 * 60 * 60

            # Disable notifications if settings backend is ephemeral
            if GObject.type_name(Gio.SettingsBackend.get_default()) == "GMemorySettingsBackend":
                logger.info("Disabling notifications")
                self.enabled = False

        self.__load_notifications()

        if backend.scheme == "https":
            logger.info(f"Backend: {backend.scheme}://{backend.hostname}:{backend.port}")
            self.connection = http.client.HTTPSConnection(backend.hostname, backend.port, timeout=8)
        else:
            self.connection = None
            logger.warning(f"{backend.scheme} is not supported, only HTTPS")
            return

        # Ensure we have a UUID
        if not self.uuid:
            self.uuid = str(uuid4())

        logger.info(f"User Agent: {self.user_agent}")
        logger.info(f"UUID: {self.uuid}")

        self._get_notification()

    def __get_container(self):
        if "FLATPAK_ID" in os.environ:
            return "flatpak"
        elif "APPIMAGE" in os.environ:
            return "appimage"
        elif "SNAP" in os.environ:
            return "snap"
        return None

    def __get_user_agent(self):
        u = platform.uname()
        platform_strings = []
        table = str.maketrans({",": "\\,"})

        if u.system == "Linux":
            release = platform.freedesktop_os_release()
            system = f"Linux {release['ID']}"

            if "VERSION_ID" in release:
                system += f" {release['VERSION_ID']}"
            if "VERSION_CODENAME" in release:
                system += f" {release['VERSION_CODENAME']}"
        else:
            system = u.system

        display_type = GObject.type_name(Gdk.Display.get_default())
        backend = display_type.removeprefix("Gdk").removesuffix("Display")
        lang = HarfBuzz.language_to_string(HarfBuzz.language_get_default())
        extra = []

        # Container type
        container = self.__get_container()
        if container:
            extra.append(f"container {container}")

        # GSettings backend
        settings_backend = Gio.SettingsBackend.get_default()
        gsettings_backend = GObject.type_name(settings_backend).removesuffix("SettingsBackend")

        for name, lib in [("GLib", GLib), ("Gtk", Gtk), ("Adw", Adw)]:
            extra.append(f"{name} {lib.MAJOR_VERSION}.{lib.MINOR_VERSION}.{lib.MICRO_VERSION}")

        # Ignore node name as that is private and irrelevant information
        for string in [system, u.release, u.version, u.machine, backend, gsettings_backend]:
            if not string:
                continue
            platform_strings.append(string.translate(table))

        return f"Cambalache/{VERSION} ({', '.join(platform_strings)}; {'; '.join(extra)}; {lang})"

    def __load_notifications(self):
        self.store.remove_all()

        if not self.notifications:
            return

        notifications = json.loads(self.notifications)
        now = utils.utcnow()

        for data in notifications:
            if "end_date" in data and now > data["end_date"]:
                continue

            self.store.append(self.__notification_from_dict(data))

    def __save_notifications(self):
        notifications = []

        for notification in self.store:
            notifications.append(notification.dict())

        # Store in GSettings
        self.notifications = json.dumps(notifications, indent=2, sort_keys=True)

    def __notification_from_dict(self, data):
        ntype = data.get("type", None)

        if ntype == "version":
            return CmbVersionNotification(center=self, **data)
        elif ntype == "message":
            return CmbMessageNotification(center=self, **data)
        elif ntype == "poll":
            return CmbPollNotification(center=self, **data)

    def __get_notification_idle(self, data):
        logger.debug(f"Got notification response {json.dumps(data, indent=2, sort_keys=True)}")

        if "notification" in data:
            notification = self.__notification_from_dict(data["notification"])
            self.store.insert(0, notification)
            self.__save_notifications()
            self.emit("new-notification", notification)

        now = int(time.time())
        self.next_request = now + self.REQUEST_INTERVAL
        self._get_notification()

        return GLib.SOURCE_REMOVE

    def __get_notification_thread(self):
        headers = {
            "User-Agent": self.user_agent,
            "x-cambalache-uuid": self.uuid,
        }

        try:
            logger.info(f"GET /notification {headers=}")

            self.connection.request("GET", "/notification", headers=headers)
            response = self.connection.getresponse()
            assert response.status == 200

            # Reset retry interval
            self.retry_interval = 8

            data = response.read().decode()

            logger.info(f"response={data}")

            if data:
                GLib.idle_add(self.__get_notification_idle, json.loads(data))
        except Exception as e:
            # If it fails we just wait a bit before retrying
            self.retry_interval *= 2
            self.retry_interval = min(self.retry_interval, 256)

            logger.info(f"Request error {e}, retrying in {self.retry_interval}s")
            GLib.timeout_add_seconds(self.retry_interval, self._get_notification)

        self.connection.close()

    def __run_in_thread(self, function, *args, **kwargs):
        if not self.connection:
            logger.warning("No connection defined")
            return

        if not self.enabled:
            logger.info("Notifications disabled")
            return

        thread = threading.Thread(target=function, args=args, kwargs=kwargs, daemon=True)
        thread.start()

    def _get_notification(self):
        now = int(time.time())

        if now >= self.next_request:
            self.__run_in_thread(self.__get_notification_thread)
        else:
            GLib.timeout_add_seconds(self.next_request - now, self._get_notification)

    def __poll_vote_idle(self, data):
        logger.debug(f"Got vote response {data}")

        poll_uuid = data["uuid"]
        results = data["results"]

        for notification in self.store:
            if isinstance(notification, CmbPollNotification) and notification.poll.id == poll_uuid:
                notification.results = CmbPollResult(**results)
                self.__save_notifications()
                break
        return GLib.SOURCE_REMOVE

    def __poll_vote_exception_idle(self, poll_uuid):
        for notification in self.store:
            if isinstance(notification, CmbPollNotification) and notification.poll.id == poll_uuid:
                notification.my_votes = []
                break
        return GLib.SOURCE_REMOVE

    def __poll_vote_thread(self, method, poll_uuid, votes=None):
        headers = {"User-Agent": self.user_agent, "x-cambalache-uuid": self.uuid, "Content-type": "application/json"}

        try:
            payload = json.dumps({"votes": votes}) if method == "POST" else None
            self.connection.request(method, f"/poll/{poll_uuid}", payload, headers)
            response = self.connection.getresponse()
            assert response.status == 200

            data = response.read().decode()
            GLib.idle_add(self.__poll_vote_idle, json.loads(data))
        except Exception as e:
            logger.warning(f"Error voting {e}")
            GLib.idle_add(self.__poll_vote_exception_idle, poll_uuid)

        self.connection.close()

    def poll_vote(self, notification: CmbPollNotification, votes: list[int]):
        if self.uuid is None:
            return

        notification.my_votes = votes

        self.__run_in_thread(self.__poll_vote_thread, "POST", notification.poll.id, votes)

    def poll_refresh_results(self, notification: CmbPollNotification):
        if self.uuid is None:
            return

        self.__run_in_thread(self.__poll_vote_thread, "GET", notification.poll.id)

    def remove(self, notification: CmbNotification):
        valid, position = self.store.find(notification)
        if valid:
            self.store.remove(position)
            self.__save_notifications()

    def remove_all(self):
        self.store.remove_all()
        self.__save_notifications()


notification_center = CmbNotificationCenter()
