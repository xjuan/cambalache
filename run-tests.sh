#!/usr/bin/bash

SCRIPT=$(readlink -f $0)
DIRNAME=$(dirname $SCRIPT)
ARCH_TRIPLET=$(cc -dumpmachine)
export LD_LIBRARY_PATH=$DIRNAME/.local/lib/$ARCH_TRIPLET:$LD_LIBRARY_PATH
export GI_TYPELIB_PATH=$DIRNAME/.local/lib/$ARCH_TRIPLET/girepository-1.0:$GI_TYPELIB_PATH
export PKG_CONFIG_PATH=$DIRNAME/.local/lib/$ARCH_TRIPLET/pkgconfig:$PKG_CONFIG_PATH
export GSETTINGS_SCHEMA_DIR=$DIRNAME/.local/share/glib-2.0/schemas:$GSETTINGS_SCHEMA_DIR
export XDG_DATA_DIRS=$DIRNAME/.local/share:$XDG_DATA_DIRS

pytest $@