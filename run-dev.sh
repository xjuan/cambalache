#!/usr/bin/bash

SCRIPT=$(readlink -f $0)
DIRNAME=$(dirname $SCRIPT)
export LD_LIBRARY_PATH=$DIRNAME/.local/lib/x86_64-linux-gnu
export GI_TYPELIB_PATH=$DIRNAME/.local/lib/x86_64-linux-gnu/girepository-1.0
export PKG_CONFIG_PATH=$DIRNAME/.local/lib/x86_64-linux-gnu/pkgconfig

if python3 $DIRNAME/tools/cmb_init_dev.py; then
    python3 - << EOF
import sys
from cambalache.app import CmbApplication
CmbApplication().run(sys.argv)
EOF
else
    echo Could not initialize dev environment
fi