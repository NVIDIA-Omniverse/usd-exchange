#!/bin/bash

set -e

# Setup the build environment
VENV=./_build/host-deps/py_package_venv
if [[ -f "$VENV/bin/activate" ]]; then
  source "$VENV/bin/activate"
else
  echo "Building: $VENV"
  ./_build/target-deps/python/python3 -m venv "$VENV"
  source "$VENV/bin/activate"
  python -m pip install -r ./tools/pyproject/dev-requirements.txt
fi

# Do the build
poetry --version
poetry "$@"
