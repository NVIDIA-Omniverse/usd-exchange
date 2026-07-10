# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Generate deps/usd-deps.packman.xml for the active USD flavor.

USD >= 26 is vendored from one usd-exchange-local template per version under deps/usd-flavors/<ver>/ (OpenUSD plus the
now-separate onetbb/materialx). The flavor/python-specific bits are resolved here and substituted into the template:
`${usd_variant}` (OpenUSD package variant), `${materialx_variant}` (MaterialX's python-tagged flavor) and
`${python_pkg}` (python runtime package). Older flavors fall back to `repo usd --generate-usd-deps`.
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
    # default_flavor is "<usd_flavor>_<usd_ver>_py_<python_ver>", e.g. usd_26.05_py_3.12
    return default_flavor.split("_py_")[-1]


def generate_usd_deps(usd_flavor: str, usd_ver: str, python_ver: str, default_flavor: str):
    root = omni.repo.man.resolve_tokens("$root")
    template = f"{root}/deps/usd-flavors/{usd_ver}/usd-deps.packman.xml"
    target = f"{root}/deps/usd-deps.packman.xml"

    if not os.path.exists(template):
        # older flavors remain vendored by repo_usd's pinned templates
        repo = omni.repo.man.resolve_tokens("$root/repo${shell_ext}")
        omni.repo.man.run_process(
            [repo, "usd", "--generate-usd-deps", "--usd-flavor", usd_flavor, "--usd-ver", usd_ver, "--python-ver", python_ver],
            exit_on_error=True,
        )
        return

    if usd_flavor == "usd-minimal":
        # minimal has no python bindings; it still needs a python for the repo_test harness and MaterialX's
        # (python-tagged) non-python libs, so track the repo's default python for both
        default_py = _default_python_ver(default_flavor)
        usd_variant = "minimal"
        materialx_variant = f"py{default_py.replace('.', '')}"
        pkg_python_ver = default_py
    else:
        py_abi = f"py{python_ver.replace('.', '')}"
        usd_variant = f"{py_abi}.no_imaging"
        materialx_variant = py_abi
        pkg_python_ver = python_ver

    python_pkg = _PYTHON_PACKAGES.get(pkg_python_ver, "")
    if not python_pkg:
        raise omni.repo.man.exceptions.ConfigurationError(
            f"No python package pinned for python {pkg_python_ver}; add it to usd_deps._PYTHON_PACKAGES"
        )

    with open(template, "r") as f:
        content = f.read()
    content = content.replace("${usd_variant}", usd_variant)
    content = content.replace("${materialx_variant}", materialx_variant)
    content = content.replace("${python_pkg}", python_pkg)

    with open(target, "w") as f:
        f.write(content)


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    toolConfig = config.get("repo_usd_deps", {})
    if not toolConfig.get("enabled", True):
        return None

    parser.description = "Generate deps/usd-deps.packman.xml (local templates for USD >= 26, repo_usd for older)."
    parser.add_argument("--usd-flavor", dest="usd_flavor", required=True)
    parser.add_argument("--usd-ver", dest="usd_ver", required=True)
    parser.add_argument("--python-ver", dest="python_ver", required=True)

    def run_repo_tool(options: argparse.Namespace, config: Dict):
        generate_usd_deps(options.usd_flavor, options.usd_ver, options.python_ver, config["repo"]["default_flavor"])

    return run_repo_tool
