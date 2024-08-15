#!/usr/bin/bash

source .local.env
export GSETTINGS_BACKEND=memory

pytest $@