#!/bin/bash

BASEDIR=`realpath $(dirname "$0")`
COMPOSITOR_SOCKET="/tmp/cmb-weston.sock"

# Run Compositor
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/.local/lib/x86_64-linux-gnu/
weston --config=$BASEDIR/tests/weston.ini -S $COMPOSITOR_SOCKET --width=1280 --height=720 >> /dev/null 2>&1 &
COMPOSITOR_PID=$!

# Test environment
export GDK_BACKEND="wayland"
export WAYLAND_DISPLAY=$COMPOSITOR_SOCKET
source .env.local

# Do not store settings
export GSETTINGS_BACKEND=memory
export COVERAGE_PROCESS_START=$BASEDIR/pyproject.toml

# Init dev
python3 -c "from tests.cmb_init_dev import cmb_init_dev; cmb_init_dev()"

#Run tests
if command -v python3-coverage &> /dev/null
then
  python3-coverage run -m pytest $@
  python3-coverage combine
  python3-coverage report -m
else
  pytest $@
fi

# Close Weston
kill -9 $COMPOSITOR_PID
rm -rf $WAYLAND_DISPLAY
