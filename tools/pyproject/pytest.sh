#!/bin/bash

set -e

# Setup the build environment
VENV=./_build/tests/venv
echo "Building: $VENV"
if [ -d $VENV ]; then
    rm -rf $VENV
fi
./_build/target-deps/python/python3 -m venv "$VENV"
source "$VENV/bin/activate"

# Install packages with optional private index
for wheel in _build/packages/*.whl; do
    python -m pip install "${wheel}[test]"
done

# Run the tests
python -m unittest discover -v -s source/core/tests/unittest
python -m unittest discover -v -s source/rtx/tests/unittest
