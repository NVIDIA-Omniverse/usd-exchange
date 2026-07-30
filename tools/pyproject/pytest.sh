#!/bin/bash

set -e

# Run from the repo root so relative paths match the rest of the tooling
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

VENV=./_build/tests/venv

# Isolate the wheel under test: ensure the native build tree is not imported over the pip-installed wheel
unset PYTHONPATH

# (Re)create a clean venv with uv, then install the built wheel(s) with the test extras
rm -rf "$VENV"
./repo.sh uv -- venv --python ./_build/target-deps/python/python3 "$VENV"
for wheel in _build/packages/*.whl; do
    ./repo.sh uv -- pip install --python "$VENV/bin/python" "${wheel}[test]"
done

# Verify the usd-exchange modules import from the installed wheel (test venv),
# not a build-tree leak that could mask a broken wheel binary.
"$VENV/bin/python" tools/pyproject/check_wheel_imports.py

# Run the tests with the venv interpreter
"$VENV/bin/python" -m unittest discover -v -s source/core/tests/unittest
"$VENV/bin/python" -m unittest discover -v -s source/rtx/tests/unittest
