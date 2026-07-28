# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Generate deps/usd-deps.packman.xml for the active USD flavor.

Each supported USD version has a template under deps/usd-flavors/<ver>/. This tool resolves the flavor-specific package
variants: ${usd_variant} selects the OpenUSD build (py<tag>.no_imaging for the usd flavor, minimal for usd-minimal) and
${materialx_variant} selects MaterialX's python-tagged build.
"""

import argparse
import os
from typing import Callable, Dict

import omni.repo.man


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
    # minimal has no python bindings, so its py-tagged variants track the repo default python
    py_tag = (_default_python_ver(default_flavor) if is_minimal else python_ver).replace(".", "")

    with open(template, "r") as f:
        content = f.read()
    content = content.replace("${usd_variant}", "minimal" if is_minimal else f"py{py_tag}.no_imaging")
    content = content.replace("${materialx_variant}", f"py{py_tag}")

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
