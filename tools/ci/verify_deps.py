# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import argparse
import glob
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
        abi = flavor.get("cxx_abi", "2.35")
        platforms_json = flavor.get("platforms", [])
        platforms = ",".join(platforms_json)

        omni.repo.man.logger.info(f"Using usd_flavor={usd_flavor}, usd_ver={usd_ver}, python_ver={python_ver}, abi={abi}, platforms={platforms}")

        # generate the usd-deps.packman.xml
        omni.repo.ci.launch(
            [
                repo,
                "usd",
                "--generate-usd-deps",
                "--usd-flavor",
                usd_flavor,
                "--usd-ver",
                usd_ver,
                "--python-ver",
                python_ver,
            ],
        )

        # check the specified usd flavor
        status = omni.repo.ci.launch(
            [
                repo,
                "--set-token",
                f"usd_flavor:{usd_flavor}",
                "--set-token",
                f"usd_ver:{usd_ver}",
                "--set-token",
                f"python_ver:{python_ver}",
                "--set-token",
                f"platforms:{platforms}",
                f"--abi={abi}",
                "verify_deps",
            ],
            warning_only=True,
        )

        if status != 0:
            success = False

    # assemble uber csv of all missing deps
    data = []
    for csv in glob.glob("_repo/missing_deps*.csv"):
        with open(csv, "r") as f:
            data.extend(f.read().strip("\n").split("\n"))
    if not data:
        omni.repo.man.print_log("Verification Passed for all flavors!")
    else:
        # hold the header column at the top, but sort the deps
        data = [data[0]] + sorted(set(data) - set([data[0]]))
        with open("_repo/missing_deps.csv", "w") as f:
            f.write("\n".join(data))

    if not success:
        raise omni.repo.man.exceptions.TestError("Some deps are not yet public!", emit_stack=False)
