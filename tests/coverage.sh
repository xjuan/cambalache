#!/bin/bash

BASEDIR=`realpath $(dirname "$0")`

source .local.env
export COVERAGE_PROCESS_START=$BASEDIR/pyproject.toml

#Run tests with coverage if available
if command -v python3-coverage &> /dev/null
then
  python3-coverage run --rcfile=$BASEDIR/../pyproject.toml -m pytest $@
  python3-coverage combine
  python3-coverage report -m
else
  echo "python3-coverage not found;\n sudo apt install python3-coverage"
fi