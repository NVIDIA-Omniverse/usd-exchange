# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import argparse
from typing import Callable, Dict

import omni.repo.man
import packmanapi


def run_verify_deps(options: argparse.Namespace, toolConfig: Dict):
    if options.verbose:
        packmanapi.set_verbosity_level(packmanapi.VERBOSITY_HIGH)

    depsFiles = ["deps/repo-deps.packman.xml", toolConfig["repo"]["folders"]["host_deps_xml"]]
    depsFiles.extend(toolConfig["repo_build"]["fetch"]["packman_target_files_to_pull"])
    buildConfigs = ["release", "debug"]
    remotes = ["cloudfront"]

    usd_flavor = omni.repo.man.resolve_tokens("${usd_flavor}")
    usd_ver = omni.repo.man.resolve_tokens("${usd_ver}")
    python_ver = omni.repo.man.resolve_tokens("${python_ver}")
    platforms = omni.repo.man.resolve_tokens("${platforms}").split(",")

    csv = []
    for platform in platforms:
        platform_target_abi = omni.repo.man.get_abi_platform_translation(platform, abi_version=omni.repo.man.resolve_tokens("$abi"))
        tokens = omni.repo.man.get_tokens(platform=platform)
        tokens["platform_host"] = platform
        tokens["platform_target_abi"] = platform_target_abi
        for config in buildConfigs:
            tokens["config"] = config
            for depsFile in depsFiles:
                omni.repo.man.print_log(f"Verifying deps `{depsFile}` for platform={platform} config={config}")
                (_, missing) = packmanapi.verify(
                    depsFile,
                    platform=platform_target_abi,
                    tokens=tokens,
                    exclude_local=True,
                    remotes=remotes,
                    tags={"public": "true"},
                )

                for remote, package in missing:
                    omni.repo.man.logger.log(
                        level=omni.repo.man.logging.ERROR,
                        msg=f"Failed: {package.name}@{package.version} is missing from {remote}",
                    )
                    csv.append(f"{package.name},{package.version},{remote.partition('packman:')[-1]}")

    if not csv:
        omni.repo.man.print_log(f"Verification Passed for {usd_flavor}_{usd_ver}_py_{python_ver}")
    else:
        with open(f"_repo/missing_deps_{usd_flavor}_{usd_ver}_py_{python_ver}.csv", "w") as f:
            f.write("\n".join(["name,version,remote"] + sorted(csv)))
        raise omni.repo.man.RepoToolError("Verification Failed")


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    parser.description = "Tool to verify whether packman dependencies are public"
    tool_config = config.get("repo_verify_deps", {})
    if not tool_config.get("enabled", True):
        return None

    return run_verify_deps
