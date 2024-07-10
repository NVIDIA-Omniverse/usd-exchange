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
import json
import shutil

import omni.repo.ci
import omni.repo.man


def main(_: argparse.Namespace):
    repo = omni.repo.man.resolve_tokens("$root/repo${shell_ext}")

    # copy internal packman config into place
    if omni.repo.ci.is_running_on_ci():
        shutil.copyfile("usd-exchange-ci/configs/config.packman.xml", "tools/packman/config.packman.xml")

    with open("deps/usd_flavors.json", "r") as f:
        flavors = json.load(f)["flavors"]

    success = True
    for flavor in flavors:
        if flavor.get("internal", False):  # only verify public flavors
            continue

        usd_flavor = flavor["usd_flavor"]
        usd_ver = flavor["usd_ver"]
        python_ver = flavor["python_ver"]

        omni.repo.man.logger.info(f"Verifying usd_flavor={usd_flavor}, usd_ver={usd_ver}, python_ver={python_ver}")

        # generate the usd-deps.packman.xml
        omni.repo.ci.launch(
            [
                repo,
                "usd",
                "--generate-usd-deps",
                "--usd-flavor", usd_flavor,
                "--usd-ver", usd_ver,
                "--python-ver", python_ver,
            ],
        )

        # check the specified usd flavor
        status = omni.repo.ci.launch(
            [
                repo,
                "--set-token", f"usd_flavor:{usd_flavor}",
                "--set-token", f"usd_ver:{usd_ver}",
                "--set-token", f"python_ver:{python_ver}",
                "verify_deps",
            ],
            warning_only=True,
        )

        if status != 0:
            success = False

    if not success:
        raise omni.repo.man.exceptions.TestError("Some deps are not yet public!", emit_stack=False)
