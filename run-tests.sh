#!/usr/bin/bash

source .local.env
SCRIPT=$(readlink -f $0)
DIRNAME=$(dirname $SCRIPT)
export GSETTINGS_BACKEND=memory
export HOME=$DIRNAME/.local/home
mkdir -p $HOME/Projects

# Disable notifications by default
cat << EOF > $DIRNAME/.local/home/.config/ar.xjuan.Cambalache.conf
[ar/xjuan/Cambalache/notification]
enabled=false
EOF

pytest $@