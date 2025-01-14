#!/usr/bin/bash

source .local.env

if python3 $DIRNAME/tools/cmb_init_dev.py; then
    python3 - $@ << EOF
import sys
import locale
locale.bindtextdomain("cambalache", "$DIRNAME/.local/share/locale")
locale.textdomain("cambalache")
from cambalache.app import CmbApplication
CmbApplication().run(sys.argv)
EOF
else
    echo Could not initialize dev environment
fi
