# SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

import argparse
import shutil

import omni.repo.ci
import omni.repo.man


def main(arguments: argparse.Namespace):
    repo = omni.repo.man.resolve_tokens("$root/repo${shell_ext}")
    usd_flavor = omni.repo.man.resolve_tokens("${usd_flavor}")
    usd_ver = omni.repo.man.resolve_tokens("${usd_ver}")
    python_ver = omni.repo.man.resolve_tokens("${python_ver}")

    omni.repo.man.logger.info(f"Using usd_flavor={usd_flavor}, usd_ver={usd_ver}, python_ver={python_ver}")

    # copy internal packman config into place
    if omni.repo.ci.is_running_on_ci():
        shutil.copyfile("usd-exchange-ci/configs/config.packman.xml", "tools/packman/config.packman.xml")

    # clean build of the specified usd & python flavors, in docker when on linux, with licensing force enabled
    build = [
        repo,
        "--set-token", f"usd_flavor:{usd_flavor}",
        "--set-token", f"usd_ver:{usd_ver}",
        "--set-token", f"python_ver:{python_ver}",
        "build",
        "--rebuild",
        "--config", arguments.build_config,
        "--/repo_build/licensing/enabled=true",
    ]
    if not omni.repo.ci.is_windows():
        build.append("--/repo_build/docker/enabled=true")
    build = [omni.repo.man.resolve_tokens(x) for x in build]
    omni.repo.ci.launch(build)

    # build the docs for the default flavor in release mode only
    if arguments.build_config == "release" and omni.repo.man.resolve_tokens("${usd_flavor}_${usd_ver}_py_${python_ver}") == "usd_24.05_py_3.10":
        omni.repo.ci.launch([repo, "docs"])
        # package the docs for linux only as we don't want overlapping packages once all flavors are assembled
        if not omni.repo.ci.is_windows():
            omni.repo.ci.launch([repo, "package", "-m", "docs"])

    # generate the package
    omni.repo.ci.launch(
        [
            repo,
            "--set-token", f"usd_flavor:{usd_flavor}",
            "--set-token", f"usd_ver:{usd_ver}",
            "--set-token", f"python_ver:{python_ver}",
            "package",
            "--mode", "usdex",
            "--config", arguments.build_config,
        ]
    )

    # clean the build so it can't influence the tests, but retain the packages
    shutil.move("_build/packages", "packages")
    omni.repo.ci.launch([repo, "build", "--clean", "--config", arguments.build_config])
    shutil.move("packages", "_build/packages")
