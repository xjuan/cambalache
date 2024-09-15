#
# IconNameSpec - Standard Icon Names
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

from cambalache import _

# Icon Naming Specification: http://standards.freedesktop.org/icon-naming-spec

standard_icon_context = {
    "cmb_all": _("All"),
    "Actions": _("Actions"),
    "Animations": _("Animations"),
    "Applications": _("Applications"),
    "Categories": _("Categories"),
    "Devices": _("Devices"),
    "Emblems": _("Emblems"),
    "Emotes": _("Emotes"),
    "International": _("International"),
    "MimeTypes": _("MIME Types"),
    "Places": _("Places"),
    "Status": _("Status"),
}

standard_icon_names = {
    # Action Icons
    "address-book-new",
    "application-exit",
    "appointment-new",
    "call-start",
    "call-stop",
    "contact-new",
    "document-new",
    "document-open",
    "document-open-recent",
    "document-page-setup",
    "document-print",
    "document-print-preview",
    "document-properties",
    "document-revert",
    "document-save",
    "document-save-as",
    "document-send",
    "edit-clear",
    "edit-copy",
    "edit-cut",
    "edit-delete",
    "edit-find",
    "edit-find-replace",
    "edit-paste",
    "edit-redo",
    "edit-select-all",
    "edit-undo",
    "folder-new",
    "format-indent-less",
    "format-indent-more",
    "format-justify-center",
    "format-justify-fill",
    "format-justify-left",
    "format-justify-right",
    "format-text-direction-ltr",
    "format-text-direction-rtl",
    "format-text-bold",
    "format-text-italic",
    "format-text-underline",
    "format-text-strikethrough",
    "go-bottom",
    "go-down",
    "go-first",
    "go-home",
    "go-jump",
    "go-last",
    "go-next",
    "go-previous",
    "go-top",
    "go-up",
    "help-about",
    "help-contents",
    "help-faq",
    "insert-image",
    "insert-link",
    "insert-object",
    "insert-text",
    "list-add",
    "list-remove",
    "mail-forward",
    "mail-mark-important",
    "mail-mark-junk",
    "mail-mark-notjunk",
    "mail-mark-read",
    "mail-mark-unread",
    "mail-message-new",
    "mail-reply-all",
    "mail-reply-sender",
    "mail-send",
    "mail-send-receive",
    "media-eject",
    "media-playback-pause",
    "media-playback-start",
    "media-playback-stop",
    "media-record",
    "media-seek-backward",
    "media-seek-forward",
    "media-skip-backward",
    "media-skip-forward",
    "object-flip-horizontal",
    "object-flip-vertical",
    "object-rotate-left",
    "object-rotate-right",
    "process-stop",
    "system-lock-screen",
    "system-log-out",
    "system-run",
    "system-search",
    "system-reboot",
    "system-shutdown",
    "tools-check-spelling",
    "view-fullscreen",
    "view-refresh",
    "view-restore",
    "view-sort-ascending",
    "view-sort-descending",
    "window-close",
    "window-new",
    "zoom-fit-best",
    "zoom-in",
    "zoom-original",
    "zoom-out",
    # Animation Icon
    "process-working",
    # Application Icons
    "accessories-calculator",
    "accessories-character-map",
    "accessories-dictionary",
    "accessories-text-editor",
    "help-browser",
    "multimedia-volume-control",
    "preferences-desktop-accessibility",
    "preferences-desktop-font",
    "preferences-desktop-keyboard",
    "preferences-desktop-locale",
    "preferences-desktop-multimedia",
    "preferences-desktop-screensaver",
    "preferences-desktop-theme",
    "preferences-desktop-wallpaper",
    "system-file-manager",
    "system-software-install",
    "system-software-update",
    "utilities-system-monitor",
    "utilities-terminal",
    # Category Icons
    "applications-accessories",
    "applications-development",
    "applications-engineering",
    "applications-games",
    "applications-graphics",
    "applications-internet",
    "applications-multimedia",
    "applications-office",
    "applications-other",
    "applications-science",
    "applications-system",
    "applications-utilities",
    "preferences-desktop",
    "preferences-desktop-peripherals",
    "preferences-desktop-personal",
    "preferences-other",
    "preferences-system",
    "preferences-system-network",
    "system-help",
    # Device Icons
    "audio-card",
    "audio-input-microphone",
    "battery",
    "camera-photo",
    "camera-video",
    "camera-web",
    "computer",
    "drive-harddisk",
    "drive-optical",
    "drive-removable-media",
    "input-gaming",
    "input-keyboard",
    "input-mouse",
    "input-tablet",
    "media-flash",
    "media-floppy",
    "media-optical",
    "media-tape",
    "modem",
    "multimedia-player",
    "network-wired",
    "network-wireless",
    "pda",
    "phone",
    "printer",
    "scanner",
    "video-display",
    # Emblem Icons
    "emblem-default",
    "emblem-documents",
    "emblem-downloads",
    "emblem-favorite",
    "emblem-important",
    "emblem-mail",
    "emblem-photos",
    "emblem-readonly",
    "emblem-shared",
    "emblem-symbolic-link",
    "emblem-synchronized",
    "emblem-system",
    "emblem-unreadable",
    # Emotion Icons
    "face-angel",
    "face-angry",
    "face-cool",
    "face-crying",
    "face-devilish",
    "face-embarrassed",
    "face-kiss",
    "face-laugh",
    "face-monkey",
    "face-plain",
    "face-raspberry",
    "face-sad",
    "face-sick",
    "face-smile",
    "face-smile-big",
    "face-smirk",
    "face-surprise",
    "face-tired",
    "face-uncertain",
    "face-wink",
    "face-worried",
    # International Icons
    "flag-aa",
    # MIME Type Icons
    "application-x-executable",
    "audio-x-generic",
    "font-x-generic",
    "image-x-generic",
    "package-x-generic",
    "text-html",
    "text-x-generic",
    "text-x-generic-template",
    "text-x-script",
    "video-x-generic",
    "x-office-address-book",
    "x-office-calendar",
    "x-office-document",
    "x-office-presentation",
    "x-office-spreadsheet",
    # Place Icons
    "folder",
    "folder-remote",
    "network-server",
    "network-workgroup",
    "start-here",
    "user-bookmarks",
    "user-desktop",
    "user-home",
    "user-trash",
    # Status Icons
    "appointment-missed",
    "appointment-soon",
    "audio-volume-high",
    "audio-volume-low",
    "audio-volume-medium",
    "audio-volume-muted",
    "battery-caution",
    "battery-low",
    "dialog-error",
    "dialog-information",
    "dialog-password",
    "dialog-question",
    "dialog-warning",
    "folder-drag-accept",
    "folder-open",
    "folder-visiting",
    "image-loading",
    "image-missing",
    "mail-attachment",
    "mail-unread",
    "mail-read",
    "mail-replied",
    "mail-signed",
    "mail-signed-verified",
    "media-playlist-repeat",
    "media-playlist-shuffle",
    "network-error",
    "network-idle",
    "network-offline",
    "network-receive",
    "network-transmit",
    "network-transmit-receive",
    "printer-error",
    "printer-printing",
    "security-high",
    "security-medium",
    "security-low",
    "software-update-available",
    "software-update-urgent",
    "sync-error",
    "sync-synchronizing",
    "task-due",
    "task-past-due",
    "user-available",
    "user-away",
    "user-idle",
    "user-offline",
    "user-trash-full",
    "weather-clear",
    "weather-clear-night",
    "weather-few-clouds",
    "weather-few-clouds-night",
    "weather-fog",
    "weather-overcast",
    "weather-severe-alert",
    "weather-showers",
    "weather-showers-scattered",
    "weather-snow",
    "weather-storm",
}
