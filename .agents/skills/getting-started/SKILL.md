---
name: getting-started
description: Bootstrap a project using the OpenUSD Exchange SDK (install via wheel or install_usdex; project layout; smoke test). Do NOT use for authoring.
version: "2.3.0"
license: Apache-2.0
metadata:
  author: "NVIDIA Corporation"
  tags: [openusd, usdex, getting-started, install]
---
<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Getting Started — OpenUSD Exchange SDK

## When to apply

Apply the first time a task asks to install OpenUSD Exchange, set up a new project, run a script that imports `usdex.core` / `usdex.rtx` / `usdex.test`, or stand up a native (C++) build that links `usdex_core` / `usdex_rtx`. Stop applying once the project layout, virtual environment, and smoke test pass.

## Hard rules — read first

Two recurring failures must be prevented before any other work happens.

1. **Never build the `usd-exchange` repository yourself to use it.** The SDK ships as Python wheels on [PyPI](https://pypi.org/project/usd-exchange/) and [PyPI NVIDIA](https://pypi.nvidia.com/usd-exchange/), and as precompiled C++ binaries via the `install_usdex` script. Building from source is only for contributors changing the SDK itself. If a task says "use the OpenUSD Exchange SDK", install the wheel (Python) or run `install_usdex` (C++).
2. **Never place your new project inside the `usd-exchange` repository directory.** Create the project in its own directory, with its own virtual environment. The `usd-exchange` clone (if any) is a *read-only reference*; the user's converter / pipeline / sample lives elsewhere and pulls in the SDK as a dependency. Do not `cd` into the `usd-exchange` checkout to create files for the user's project.

## Choose the install path

| Path | Use when | Mechanism |
| --- | --- | --- |
| Python wheel | Pure-Python converter, scripting, prototyping, CI. No C++ to compile. | `pip install usd-exchange` (add `[test]` for `usdex.test` + Asset Validator). |
| Native (C++) install | C++ application, plugin, or mixed C++/Python with a controlled OpenUSD version. | `repo install_usdex` from a clone of `usd-exchange` *or* the [Exchange Samples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples). |

Pick the wheel unless the user explicitly needs C++, a non-default OpenUSD version, or a non-default Python version. The wheel locks the OpenUSD version per release; only `install_usdex` exposes `--usd-version`, `--usd-flavor`, `--python-version`, `--install-rtx`, `--install-test`, `--install-extra-plugins`.

## Project layout

Create a fresh directory anywhere *outside* the `usd-exchange` clone. Recommended layout for a Python project:

- `.venv/` — virtual environment.
- `src/` — converter / pipeline source.
- `tests/` — unittest suite using `usdex.test` (optional).
- `output/` — generated USD assets and textures.
- `pyproject.toml` or `requirements.txt` — dependencies.

For a native C++ project, follow the layout in [`docs/native-application.md`](../../../docs/native-application.md): a project root with the SDK installed under `usdex/` (alongside `target-deps/usd`, `target-deps/python`, and `<platform>/<config>/lib`).

## Python install (wheel)

Linux (bash):

- `python -m venv .venv`
- `source .venv/bin/activate`
- `pip install "usd-exchange[test]"` — drop `[test]` if you do not need `usdex.test` / Asset Validator

Windows (PowerShell):

- `python -m venv .venv`
- `.venv\Scripts\Activate.ps1`
- `pip install "usd-exchange[test]"`

Verify: `python -c "import usdex.core; print(usdex.core.version())"` should print a version string.

## Native (C++) install via `install_usdex`

Run from a clone of either `usd-exchange` *or* the [Exchange Samples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples). When run from the Samples repo, run `./repo.sh build --fetch-only` (or `.\repo.bat build --fetch-only`) first.

- Release: `./repo.sh install_usdex --config release --install-python-libs`
- Debug: `./repo.sh install_usdex --config debug --install-python-libs`
- Pin OpenUSD: add `--usd-version 25.05` (and `--python-version 3.11` if needed)
- RTX MDL helpers (`usdex_rtx`): add `--install-rtx`
- Test helpers + Asset Validator: add `--install-test`
- Monolithic / no-Python OpenUSD: `--usd-flavor usd-minimal --python-version 0`

The output goes to `_install/`. Deep-copy it (preserving symlinks/junctions) into the project's `usdex/` folder:

- Linux: `cp -Lr _install $project_root/usdex`
- Windows: `robocopy /s _install $project_root\usdex > NUL`

Do **not** copy without preserving links — `target-deps/` contains soft links on Linux and junctions on Windows.

For include paths, libraries, preprocessor defines, and runtime path setup, follow `docs/native-application.md` (Makefile and Visual Studio settings included). The `Makefile` and `repo.toml` snippets there are the canonical reference; do not invent build flags.

## Smoke test

Run from inside the project directory with the venv active before writing converter code. Exercises stage creation, naming, transforms, save, and the diagnostic delegate — failures here mean the install is wrong. Names go through `getValidPrimName` / `NameCache` rather than literal `name=` arguments, matching the authoring rules.

```python
import usdex.core
from pxr import Gf, UsdGeom

AUTHORING_METADATA = "my-converter smoke test, version 0.1"
asset_name, probe_name = "World", "Probe"

usdex.core.activateDiagnosticsDelegate()
cache = usdex.core.NameCache()
stage = usdex.core.createStage("smoke.usda", usdex.core.getValidPrimName(asset_name),
    UsdGeom.GetFallbackUpAxis(), UsdGeom.LinearUnits.centimeters, AUTHORING_METADATA)
assert stage
root = usdex.core.defineXform(stage.GetDefaultPrim()).GetPrim()
usdex.core.defineXform(root, cache.getPrimName(root, probe_name),
    Gf.Transform(Gf.Matrix4d().SetTranslate(Gf.Vec3d(0, 100, 0))))
usdex.core.saveStage(stage, AUTHORING_METADATA)
print(f"OK: usdex {usdex.core.version()}")
```

If this runs and writes `smoke.usda`, the install is healthy. If `usdex.core` fails to import, you are running the wrong interpreter — re-activate the venv.

## Next

After the smoke test passes, move to the `usd-authoring` skill for authoring rules and the topical reference index. The samples repo ([usd-exchange-samples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples)) is the canonical end-to-end reference; clone it for working examples and run them via `./run.sh <sample>` (C++) or `python source/python/<sample>.py`.
