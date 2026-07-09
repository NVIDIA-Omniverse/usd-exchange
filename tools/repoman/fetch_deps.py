# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Fetch the packman dependencies configured under [repo_fetch_deps].

Shared tool for pulling packman dependency files with the platform/abi/config tokens resolved.
"""

import argparse
import os
from typing import Callable, Dict

import omni.repo.man
import packmanapi


def fetch_dependencies(config: Dict, build_config: str) -> Dict:
    """Pull the configured packman files, returning packman's resolved package info keyed by dependency name.

    Target dependencies resolve for the abi-tagged target platform; host tools (cmake, msvc, ...) resolve for the
    host platform. This is why the target and host file lists are kept separate.
    """
    fetch_cfg = config.get("repo_fetch_deps", {}).get("fetch", {})

    tokens = omni.repo.man.get_tokens()
    tokens["config"] = build_config
    tokens["platform_host"] = tokens["platform"]
    tokens["platform_target"] = tokens["platform"]
    tokens["platform_target_abi"] = omni.repo.man.get_abi_platform_translation(tokens["platform"], tokens.get("abi", "2.35"))

    targets = [(f, tokens["platform_target_abi"]) for f in fetch_cfg.get("packman_target_files_to_pull", [])]
    hosts = [(f, tokens["platform_host"]) for f in fetch_cfg.get("packman_host_files_to_pull", [])]

    pulled: Dict = {}
    for dep_file, platform in targets + hosts:
        path = omni.repo.man.resolve_tokens(dep_file, extra_tokens=tokens)
        if not os.path.exists(path):  # some dependency files are optional
            continue
        result = packmanapi.pull(path, platform=platform, tokens=tokens, return_extra_info=True)
        pulled.update(result)
    return pulled


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    toolConfig = config.get("repo_fetch_deps", {})
    if not toolConfig.get("enabled", True):
        return None

    parser.description = "Fetch the packman dependencies configured under [repo_fetch_deps]."
    omni.repo.man.add_config_arg(parser)

    def run_repo_tool(options: argparse.Namespace, config: Dict):
        fetch_dependencies(config, options.config)

    return run_repo_tool
