#!/usr/bin/env bash

DIRNAME=`dirname -- "$( readlink -f -- "$0"; )"`

flatpak run \
	--env=LD_LIBRARY_PATH=$DIRNAME/.local/lib \
	--filesystem=home \
	--share=ipc \
	--share=network \
	--socket=fallback-x11 \
	--socket=wayland \
	--filesystem=home \
	--device=dri \
	--own-name=ar.xjuan.* \
	--command=bash \
	--devel \
	org.gnome.Sdk//46