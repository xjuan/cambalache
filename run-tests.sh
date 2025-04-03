#!/usr/bin/bash

source .local.env
SCRIPT=$(readlink -f $0)
DIRNAME=$(dirname $SCRIPT)
export GSETTINGS_BACKEND=memory
export HOME=$DIRNAME/.local/home
mkdir -p $HOME/Projects

pytest $@