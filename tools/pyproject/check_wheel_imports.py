# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Verify wheel tests import usd-exchange modules from the test venv, and that its native libraries resolve inside it."""

import importlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import sysconfig
from pathlib import Path

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
    dll_paths = [entry for entry in os.environ.get("PXR_USD_WINDOWS_DLL_PATH", "").split(os.pathsep) if entry]
    if not dll_paths:
        return ["PXR_USD_WINDOWS_DLL_PATH was not set by pxr import"]
    dll_root = dll_paths[0]

    path_entries = [entry for entry in os.environ.get("PATH", "").split(os.pathsep) if entry]
    if not any(_realpath(entry) == _realpath(dll_root) for entry in path_entries):
        failures.append(f"PXR_USD_WINDOWS_DLL_PATH is not on PATH: {dll_root}")

    try:
        from pxr import Plug
    except Exception as exc:
        return failures + [f"pxr.Plug failed to import: {type(exc).__name__}: {exc}"]

    registry = Plug.Registry()
    registry.RegisterPlugins(os.path.join(dll_root, "usd"))
    # Load the shader and validator plugins named in the Windows DLL-path regression criteria.
    for name in ("usdGeomValidators", "usdMtlx", "usdPhysicsValidators", "usdShaders"):
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


# Libraries the wheel provides, which downstream native wheels link by these same names rather than bundle.
_PROVIDED = re.compile(r"^lib(usd_|usdex_|tbb|MaterialX)")
_AUDITWHEEL_HASH = re.compile(r"-[0-9a-f]{8}(?=\.so(?:\.|$))")


def _dynamic_entries(path: Path) -> list[tuple[str, str]]:
    """The ``NEEDED`` and ``SONAME`` entries of an ELF file, as ``(kind, name)`` pairs."""
    output = subprocess.check_output(["readelf", "--dynamic", "--wide", str(path)], text=True)
    entries = []
    for line in output.splitlines():
        fields = line.split(maxsplit=2)
        if len(fields) == 3 and fields[1] in ("(NEEDED)", "(SONAME)"):
            entries.append((fields[1][1:-1], fields[2].partition("[")[2].partition("]")[0]))
    return entries


def _check_linux_libraries() -> list[str]:
    if sys.platform != "linux":
        return []

    package = importlib.metadata.distribution("usd-exchange")
    libs = Path(package.locate_file("usd_exchange.libs"))
    failures = []

    # the libraries keep the names OpenUSD, oneTBB and MaterialX were built with, so each file is named after its SONAME
    for lib in sorted(libs.glob("*.so*")):
        if _AUDITWHEEL_HASH.search(lib.name):
            failures.append(f"{lib.name}: carries an auditwheel content hash")
        if ("SONAME", lib.name) not in _dynamic_entries(lib):
            failures.append(f"{lib.name}: SONAME does not match the filename")

    binaries = [path for root in ("usd_exchange.libs", "pxr", "usdex") for path in Path(package.locate_file(root)).rglob("*.so*")]
    for binary in binaries:
        with binary.open("rb") as f:
            if f.read(4) != b"\x7fELF":
                continue
        for kind, name in _dynamic_entries(binary):
            if kind == "NEEDED" and _PROVIDED.match(name) and not (libs / name).is_file():
                failures.append(f"{binary.name}: depends on {name}, which the wheel does not provide")

    for info in libs.glob("usd/*/resources/plugInfo.json"):
        data = json.loads("".join(line for line in info.read_text().splitlines(True) if not line.lstrip().startswith("#")))
        for plugin in data.get("Plugins", []):
            # LibraryPath is relative to the plugin Root, which is itself relative to the plugInfo.json directory
            root = info.parent / plugin.get("Root", ".")
            if plugin.get("LibraryPath") and not (root / plugin["LibraryPath"]).resolve().is_file():
                failures.append(f"{info.relative_to(libs)}: unresolved LibraryPath {plugin['LibraryPath']}")

    # these load lazily by LibraryPath rather than with a pxr module import, so they prove the names resolve at runtime
    try:
        from pxr import Plug
    except Exception as exc:
        return failures + [f"pxr.Plug failed to import: {type(exc).__name__}: {exc}"]
    registry = Plug.Registry()
    for name in ("usdGeomValidators", "usdMtlx", "usdPhysicsValidators", "usdShaders"):
        plugin = registry.GetPluginWithName(name)
        if not plugin:
            failures.append(f"{name} plugin was not discovered under {libs}")
            continue
        try:
            plugin.Load()
        except Exception as exc:
            failures.append(f"{name} failed to load from {plugin.path}: {type(exc).__name__}: {exc}")

    # the loader reuses an already-loaded library by SONAME, so confirm the shared runtime is the wheel's own copy
    mapped = set()
    with open("/proc/self/maps") as f:
        for line in f:
            fields = line.split(maxsplit=5)
            if len(fields) == 6 and fields[5].startswith("/"):
                mapped.add(Path(fields[5].rstrip("\n")))
    for soname in ("libtbb.so.12", "libusd_tf.so"):
        # another provider's copy may be mapped under the versioned file name its SONAME links to
        sources = sorted({os.path.realpath(path) for path in mapped if path.name == soname or path.name.startswith(f"{soname}.")})
        if sources != [os.path.realpath(libs / soname)]:
            failures.append(f"{soname} is mapped from {sources or 'nowhere'}, expected only {libs / soname}")

    if not failures:
        print(f"  Linux libraries: {len(list(libs.glob('*.so*')))} under their SONAMEs, {len(binaries)} binaries resolve [ok]")
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
    failures.extend(_check_linux_libraries())

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
