# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Generate deps/usd-deps.packman.xml for the active USD flavor.

Every supported USD version has one usd-exchange-local template under deps/usd-flavors/<ver>/, and this tool resolves the
flavor/python-specific bits into it. Two dialects exist:
- USD >= 26 (unbundled OpenUSD + separate onetbb/materialx): `${usd_variant}` (OpenUSD package variant) and
  `${materialx_variant}` (MaterialX's python-tagged flavor).
- USD < 26 (OpenUSD bundles onetbb/materialx): `${usd_prefix}` (e.g. usd.py312 / usd-minimal.nopy) and
  `${usd_buildtype}` (exchange / stock).
Both dialects share `${python_pkg}` (the python runtime package): the `usd` flavor tracks its own python, while
`usd-minimal` (no python bindings) tracks the repo's default python for the repo_test harness.
"""

import argparse
import os
from typing import Callable, Dict

import omni.repo.man

# the python runtime packages keyed by python minor version; the ${platform_target_abi} suffix is applied in the
# template. These do not vary by USD flavor or version.
_PYTHON_PACKAGES = {
    "3.10": "3.10.20+nv6",
    "3.11": "3.11.15+nv6",
    "3.12": "3.12.13+nv6",
    "3.13": "3.13.14+nv1",
}


def _default_python_ver(default_flavor: str) -> str:
    # default_flavor is "<usd_flavor>_<usd_ver>_py_<python_ver>"
    return default_flavor.split("_py_")[-1]


def generate_usd_deps(usd_flavor: str, usd_ver: str, python_ver: str, default_flavor: str):
    root = omni.repo.man.resolve_tokens("$root")
    template = f"{root}/deps/usd-flavors/{usd_ver}/usd-deps.packman.xml"
    target = f"{root}/deps/usd-deps.packman.xml"

    if not os.path.exists(template):
        raise omni.repo.man.exceptions.ConfigurationError(f"Unsupported USD version {usd_ver}: no template at {template}")

    is_minimal = usd_flavor == "usd-minimal"
    # minimal has no python bindings, so it tracks the repo default python; the usd flavor tracks its requested python
    pkg_python_ver = _default_python_ver(default_flavor) if is_minimal else python_ver
    python_pkg = _PYTHON_PACKAGES.get(pkg_python_ver, "")
    if not python_pkg:
        raise omni.repo.man.exceptions.ConfigurationError(
            f"No python package pinned for python {pkg_python_ver}; add it to usd_deps._PYTHON_PACKAGES"
        )
    py_tag = pkg_python_ver.replace(".", "")

    with open(template, "r") as f:
        content = f.read()
    content = content.replace("${python_pkg}", python_pkg)

    if int(usd_ver.split(".", 1)[0]) >= 26:
        content = content.replace("${usd_variant}", "minimal" if is_minimal else f"py{py_tag}.no_imaging")
        content = content.replace("${materialx_variant}", f"py{py_tag}")
    else:
        content = content.replace("${usd_prefix}", "usd-minimal.nopy" if is_minimal else f"usd.py{py_tag}")
        content = content.replace("${usd_buildtype}", "stock" if is_minimal else "exchange")

    with open(target, "w") as f:
        f.write(content)


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    toolConfig = config.get("repo_usd_deps", {})
    if not toolConfig.get("enabled", True):
        return None

    parser.description = "Generate deps/usd-deps.packman.xml from the local per-version template in deps/usd-flavors/."
    parser.add_argument("--usd-flavor", dest="usd_flavor", required=True)
    parser.add_argument("--usd-ver", dest="usd_ver", required=True)
    parser.add_argument("--python-ver", dest="python_ver", required=True)

    def run_repo_tool(options: argparse.Namespace, config: Dict):
        generate_usd_deps(options.usd_flavor, options.usd_ver, options.python_ver, config["repo"]["default_flavor"])

    return run_repo_tool
