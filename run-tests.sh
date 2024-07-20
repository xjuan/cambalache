#!/usr/bin/bash

SCRIPT=$(readlink -f $0)
DIRNAME=$(dirname $SCRIPT)
export LD_LIBRARY_PATH=$DIRNAME/.local/lib/x86_64-linux-gnu
export GI_TYPELIB_PATH=$DIRNAME/.local/lib/x86_64-linux-gnu/girepository-1.0
export PKG_CONFIG_PATH=$DIRNAME/.local/lib/x86_64-linux-gnu/pkgconfig

pytest $@