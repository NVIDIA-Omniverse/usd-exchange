# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import argparse
import shutil

import omni.repo.ci
import omni.repo.man


def main(arguments: argparse.Namespace):
    repo = omni.repo.man.resolve_tokens("$root/repo${shell_ext}")
    usd_flavor = omni.repo.man.resolve_tokens("${usd_flavor}")
    usd_ver = omni.repo.man.resolve_tokens("${usd_ver}")
    python_ver = omni.repo.man.resolve_tokens("${python_ver}")
    abi = omni.repo.man.resolve_tokens("${abi}")
    default_usd_flavor, default_usd_ver, _, _ = arguments.merged_tool_config["repo"]["default_flavor"].split("_")

    omni.repo.man.logger.info(f"Using usd_flavor={usd_flavor}, usd_ver={usd_ver}, python_ver={python_ver}, abi={abi}")

    # copy internal packman config into place
    if omni.repo.ci.is_running_on_ci():
        shutil.copyfile("usd-exchange-ci/configs/config.packman.xml", "tools/packman/config.packman.xml")

    # generate the usd-deps.packman.xml
    omni.repo.ci.launch(
        [
            repo,
            "usd_deps",
            "--usd-flavor",
            usd_flavor,
            "--usd-ver",
            usd_ver,
            "--python-ver",
            python_ver,
        ],
    )

    test = [
        repo,
        "--set-token",
        f"usd_flavor:{usd_flavor}",
        "--set-token",
        f"usd_ver:{usd_ver}",
        "--set-token",
        f"python_ver:{python_ver}",
        f"--abi={abi}",
        "test",
        "--from-package",
        "--config",
        arguments.build_config,
        "--/repo_test/suites/main/verbosity=2",
    ]
    suites = ["--suite", "cpp"]
    if python_ver != "0":
        suites.append("main")
        # test the python wheel only for the default USD flavor
        if arguments.build_config == "release" and usd_flavor == default_usd_flavor and usd_ver == default_usd_ver:
            suites.append("whl")
    test.extend(suites)

    omni.repo.ci.launch(test)
