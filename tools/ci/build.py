# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import argparse
import os
import platform
import shutil

import omni.repo.ci
import omni.repo.man


def main(arguments: argparse.Namespace):
    repo = omni.repo.man.resolve_tokens("$root/repo${shell_ext}")
    usd_flavor = omni.repo.man.resolve_tokens("${usd_flavor}")
    usd_ver = omni.repo.man.resolve_tokens("${usd_ver}")
    python_ver = omni.repo.man.resolve_tokens("${python_ver}")
    abi = omni.repo.man.resolve_tokens("${abi}")
    default_usd_flavor, default_usd_ver, _, default_python_ver = arguments.merged_tool_config["repo"]["default_flavor"].split("_")

    omni.repo.man.logger.info(f"Using usd_flavor={usd_flavor}, usd_ver={usd_ver}, python_ver={python_ver}, abi={abi}")

    # copy internal configs into place
    if omni.repo.ci.is_running_on_ci():
        shutil.copyfile("usd-exchange-ci/configs/config.packman.xml", "tools/packman/config.packman.xml")
        if omni.repo.man.is_windows():
            shutil.copyfile("usd-exchange-ci/configs/host-deps.packman.xml", "deps/host-deps.packman.xml")

    # clean build of the specified usd & python flavors, in docker when on linux, with licensing force enabled
    build = [
        repo,
        "--set-token",
        f"usd_flavor:{usd_flavor}",
        "--set-token",
        f"usd_ver:{usd_ver}",
        "--set-token",
        f"python_ver:{python_ver}",
        f"--abi={abi}",
        "build",
        "--rebuild",
        "--config",
        arguments.build_config,
        "--verbose",
        "--/repo_build/licensing/enabled=true",
    ]
    if omni.repo.man.is_linux():
        build.append("--/repo_build/docker/enabled=true")
        image = os.environ.get("REPO_BUILD_IMAGE")
        if abi and image:
            build.append(f"--/repo_build/docker/image_url={image}")
    elif omni.repo.man.is_windows():
        build.append("--/repo_build/msbuild/link_host_toolchain=")

    build = [omni.repo.man.resolve_tokens(x) for x in build]
    omni.repo.ci.launch(build)

    # some parts should only build for the default flavor in release mode
    if arguments.build_config == "release":
        # generate the python wheel only for the default USD flavor, but for all python versions and platforms
        if usd_flavor == default_usd_flavor and usd_ver == default_usd_ver and python_ver != "0":
            omni.repo.ci.launch(
                [
                    repo,
                    "--set-token",
                    f"usd_flavor:{usd_flavor}",
                    "--set-token",
                    f"usd_ver:{usd_ver}",
                    "--set-token",
                    f"python_ver:{python_ver}",
                    f"--abi={abi}",
                    "py_package",
                ]
            )
        # build the docs only for the default USD flavor & python version but for all platforms
        arch = platform.machine()
        if usd_flavor == default_usd_flavor and usd_ver == default_usd_ver and python_ver == default_python_ver and arch not in ["aarch64", "arm64"]:
            omni.repo.ci.launch([repo, "docs"])
            # package the docs for linux only as we don't want overlapping packages once all flavors are assembled
            if omni.repo.man.is_linux():
                omni.repo.ci.launch([repo, "package", "--mode", "docs"])

    # generate the packman package
    omni.repo.ci.launch(
        [
            repo,
            "--set-token",
            f"usd_flavor:{usd_flavor}",
            "--set-token",
            f"usd_ver:{usd_ver}",
            "--set-token",
            f"python_ver:{python_ver}",
            f"--abi={abi}",
            "package",
            "--mode",
            "usdex",
            "--config",
            arguments.build_config,
        ]
    )

    # clean the build so it can't influence the tests,
    # but retain the packages and the sidecar binaries
    shutil.move("_build/packages", "packages")
    shutil.move(omni.repo.man.resolve_tokens(f"_build/$platform/{arguments.build_config}/bin"), "bin")
    omni.repo.ci.launch([repo, "build", "--clean", "--config", arguments.build_config])
    shutil.move("bin", omni.repo.man.resolve_tokens(f"_build/$platform/{arguments.build_config}/bin"))
    shutil.move("packages", "_build/packages")
