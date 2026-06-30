# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Verify wheel tests import usd-exchange modules from the test venv."""

import importlib
import os
import sys
import sysconfig

MODULES = [
    "pxr",
    "pxr.Ar",
    "pxr.Tf",
    "usdex",
    "usdex.core",
]


def _realpath(path: str) -> str:
    return os.path.normcase(os.path.realpath(path))


def _module_path(module) -> str:
    path = getattr(module, "__file__", None)
    if path:
        return path
    paths = list(getattr(module, "__path__", []) or [])
    return paths[0] if paths else ""


def _is_relative_to(path: str, root: str) -> bool:
    try:
        common = os.path.commonpath([_realpath(path), _realpath(root)])
    except ValueError:
        return False
    return common == _realpath(root)


def _check_windows_usd_plugins() -> list[str]:
    if sys.platform != "win32":
        return []

    failures = []
    dll_root = os.environ.get("PXR_USD_WINDOWS_DLL_PATH")
    if not dll_root:
        return ["PXR_USD_WINDOWS_DLL_PATH was not set by pxr import"]

    path_entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    if not any(_realpath(entry) == _realpath(dll_root) for entry in path_entries):
        failures.append(f"PXR_USD_WINDOWS_DLL_PATH is not on PATH: {dll_root}")

    try:
        from pxr import Plug
    except Exception as exc:
        return failures + [f"pxr.Plug failed to import: {type(exc).__name__}: {exc}"]

    registry = Plug.Registry()
    registry.RegisterPlugins(os.path.join(dll_root, "usd"))
    for name in ("usdMtlx", "usdShaders"):
        plugin = registry.GetPluginWithName(name)
        if not plugin:
            failures.append(f"{name} plugin was not discovered under {dll_root}")
            continue
        if not _is_relative_to(plugin.path, dll_root):
            failures.append(f"{name} plugin resolved outside the wheel: {plugin.path}")
            continue
        try:
            plugin.Load()
        except Exception as exc:
            failures.append(f"{name} failed to load from {plugin.path}: {type(exc).__name__}: {exc}")
            continue
        print(f"  {name}: {plugin.path} [ok]")

    return failures


def main() -> int:
    site_roots = {
        sysconfig.get_path("purelib"),
        sysconfig.get_path("platlib"),
    }
    site_roots = {path for path in site_roots if path}

    print("Wheel import provenance:")
    print(f"  executable: {sys.executable}")
    print(f"  prefix: {sys.prefix}")
    print(f"  site roots: {os.pathsep.join(sorted(site_roots))}")
    print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")
    print(f"  LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', '')}")

    failures = []
    for name in MODULES:
        try:
            module = importlib.import_module(name)
        except Exception as exc:
            print(f"  {name}: import failed: {type(exc).__name__}: {exc} [failed]")
            failures.append(f"{name} failed to import: {type(exc).__name__}: {exc}")
            continue
        path = _module_path(module)
        in_site = any(_is_relative_to(path, root) for root in site_roots)
        status = "ok" if in_site else "not from test venv"
        print(f"  {name}: {path} [{status}]")
        if not in_site:
            failures.append(f"{name} imported from {path}")

    failures.extend(_check_windows_usd_plugins())

    if failures:
        print("")
        print("Wheel import provenance check failed:")
        for failure in failures:
            print(f"  {failure}")
        print("")
        print("The whl suite must import usd-exchange modules from the test venv site-packages.")
        print("A build-tree PYTHONPATH/LD_LIBRARY_PATH leak can hide broken wheel binaries.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
