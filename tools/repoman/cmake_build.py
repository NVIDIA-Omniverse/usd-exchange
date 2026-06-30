# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""Fetch dependencies and build the CMake project for the current USD flavor.

The internal flavor-matrix entry point: fetch target deps via packman, then configure + build the root
CMakeLists into the `_build/$platform/$config` tree. External customers build it against their own USD.
"""

import argparse
import os
import shutil
from typing import Callable, Dict

import omni.repo.man
import packmanapi

# release/debug token -> CMake configuration name
_CMAKE_CONFIG = {"release": "Release", "debug": "Debug"}


def _fetch_dependencies(repo: str, usd_flavor: str, usd_ver: str, python_ver: str, dep_files) -> Dict:
    # regenerate the flavor's usd-deps manifest (the one remaining repo_usd call), then pull every dep file
    omni.repo.man.run_process(
        [repo, "usd", "--generate-usd-deps", "--usd-flavor", usd_flavor, "--usd-ver", usd_ver, "--python-ver", python_ver],
        exit_on_error=True,
    )
    tokens = omni.repo.man.get_tokens()
    pulled: Dict = {}
    for dep_file in dep_files:
        path = omni.repo.man.resolve_tokens(dep_file)
        if not os.path.exists(path):  # host deps are absent on most platforms
            continue
        result = packmanapi.pull(path, platform=tokens["platform"], tokens=tokens, return_extra_info=True)
        pulled.update(result)
    return pulled


def _write_all_deps_manifest(dest: str, pulled: Dict, strip_deps):
    """Write the resolved dependency lock (concrete versions, no linkPath, sorted) shipped in dev/ for install_usdex."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    lines = ['<project toolsVersion="6.11">']
    for dep, info in sorted(pulled.items()):
        if dep in strip_deps:
            continue
        # skip host toolchain
        if not info.get("all_deps", True):
            continue
        lines.append(f'  <dependency name="{dep}">')
        if "package_name" in info:
            lines.append(f'    <package name="{info["package_name"]}" version="{info["package_version"]}" />')
        else:
            # source-linked dep
            lines.append(f'    <source path="{info["local_path"]}" />')
        lines.append("  </dependency>")
    lines.append("</project>")
    with open(dest, "w") as f:
        f.write("\n".join(lines) + "\n")


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    toolConfig = config.get("repo_cmake", {})
    if not toolConfig.get("enabled", True):
        return None

    parser.description = "Fetch deps & build the OpenUSD Exchange SDK with CMake for the current USD flavor."
    parser.add_argument(
        "--generate", action="store_true", help="configure only (emit compile_commands.json + generated headers), then exit without compiling"
    )
    parser.add_argument("--skip-post", action="store_true", dest="skip_post", help="skip post-build install_usdex/stubgen")
    parser.add_argument("-x", "--rebuild", action="store_true", help="wipe the build tree, then build")
    parser.add_argument("--clean", action="store_true", help="wipe the build tree, then exit (no build)")
    omni.repo.man.add_config_arg(parser)

    def run_repo_tool(options: argparse.Namespace, config: Dict):
        root = omni.repo.man.resolve_tokens("$root")
        repo = omni.repo.man.resolve_tokens("$root/repo${shell_ext}")
        platform = omni.repo.man.resolve_tokens("$platform")
        repo_config = omni.repo.man.resolve_tokens("$config")
        usd_flavor = omni.repo.man.resolve_tokens("${usd_flavor}")
        usd_ver = omni.repo.man.resolve_tokens("${usd_ver}")
        python_ver = omni.repo.man.resolve_tokens("${python_ver}")
        abi = omni.repo.man.resolve_tokens("${abi}")
        cmake_config = _CMAKE_CONFIG.get(repo_config, "Release")

        output_dir = f"{root}/_build/{platform}/{repo_config}"  # staged/packaged artifacts land here
        build_dir = f"{root}/_build/cmake/{platform}/{repo_config}"  # CMake intermediates (sibling of the staged tree)

        if options.clean or options.rebuild:
            omni.repo.man.logger.info(f"cmake: cleaning {root}/_build")
            shutil.rmtree(f"{root}/_build", ignore_errors=True)
        if options.clean:
            return

        fetch_cfg = config.get("repo_cmake", {}).get("fetch", {})
        dep_files = [*fetch_cfg.get("packman_target_files_to_pull", []), *fetch_cfg.get("packman_host_files_to_pull", [])]
        strip_deps = fetch_cfg.get("strip_deps", [])
        pulled = _fetch_dependencies(repo, usd_flavor, usd_ver, python_ver, dep_files)

        # generated headers, #included by the C++ sources
        omni.repo.man.run_process([repo, "version_header"], exit_on_error=True)
        omni.repo.man.run_process([repo, "feature_header", "--python", python_ver], exit_on_error=True)

        usd_root = f"{root}/_build/target-deps/usd/{repo_config}"
        python_root = f"{root}/_build/target-deps/python"
        target_deps = f"{root}/_build/target-deps"

        configure = [
            "cmake",
            "-S",
            root,
            "-B",
            build_dir,
            f"-DCMAKE_BUILD_TYPE={cmake_config}",
            "-DCMAKE_INSTALL_LIBDIR=lib",  # our package layout uses lib/, not lib64
            f"-DUSDEX_USD_ROOT={usd_root}",
            f"-DUSDEX_PYTHON_VERSION={python_ver}",
            f"-DUSDEX_PYBIND11_INCLUDE_DIR={target_deps}/pybind11/include",
            f"-DUSDEX_CXXOPTS_INCLUDE_DIR={target_deps}/cxxopts/include",
            f"-DUSDEX_DOCTEST_INCLUDE_DIR={target_deps}/doctest/include",
            # emit into the build-tree layout the downstream tools expect
            f"-DUSDEX_LIB_OUTPUT_DIR={output_dir}/lib",
            f"-DUSDEX_BIN_OUTPUT_DIR={output_dir}/bin",
            f"-DUSDEX_PYTHON_OUTPUT_DIR={output_dir}/python",
            f"-DUSDEX_INCLUDE_OUTPUT_DIR={output_dir}/include",
            f"-DUSDEX_DEV_OUTPUT_DIR={output_dir}/dev",
        ]
        if python_ver != "0":
            # locate the target python, not a system interpreter
            configure += [f"-DPython3_ROOT_DIR={python_root}", "-DPython3_FIND_STRATEGY=LOCATION"]

        omni.repo.man.logger.info(" ".join(configure))
        omni.repo.man.run_process(configure, exit_on_error=True)

        if options.generate:
            # compile_commands.json + generated headers are produced at configure; skip compiling
            return

        build = ["cmake", "--build", build_dir, "--config", cmake_config, "-j", str(os.cpu_count() or 1)]
        omni.repo.man.logger.info(" ".join(build))
        omni.repo.man.run_process(build, exit_on_error=True)

        if not options.skip_post:
            # install just the find_package config into lib/cmake/usd-exchange (libs/headers are already in the tree)
            omni.repo.man.run_process(
                ["cmake", "--install", build_dir, "--config", cmake_config, "--prefix", output_dir, "--component", "usdex_cmake_config"],
                exit_on_error=True,
            )

            # gather third-party licenses into _build/PACKAGE-LICENSES (shipped by the package)
            omni.repo.man.run_process(
                [
                    repo,
                    "--set-token",
                    f"platform_host:{platform}",  # usd-deps.packman.xml references it
                    "licensing",
                    "gather",
                    "--dir",
                    ".",
                    "--packages",
                    "deps/target-deps.packman.xml",
                    "--platform",
                    platform,
                    "--config",
                    repo_config,
                    "--output",
                    "_build/PACKAGE-LICENSES",
                    "--fail",
                ],
                exit_on_error=True,
            )
            _write_all_deps_manifest(f"{output_dir}/dev/deps/all-deps.packman.xml", pulled, strip_deps)

            # assemble the runtime tree (pxr/, plugInfo, test deps) then generate python stubs
            omni.repo.man.run_process(
                [
                    repo,
                    "--set-token",
                    f"platform_host:{platform}",
                    "--set-token",
                    f"usd_flavor:{usd_flavor}",
                    "--set-token",
                    f"usd_ver:{usd_ver}",
                    "--set-token",
                    f"python_ver:{python_ver}",
                    f"--abi={abi}",
                    "install_usdex",
                    "-c",
                    repo_config,
                    "--use-existing-build",
                    "--install-test",
                    "--staging-dir",
                    "_build",
                    "--install-dir",
                    f"_build/{platform}/{repo_config}",
                ],
                exit_on_error=True,
            )

            if python_ver != "0":
                omni.repo.man.run_process(
                    [repo, "--set-token", f"python_ver:{python_ver}", "stubgen", "-c", repo_config],
                    exit_on_error=True,
                )

    return run_repo_tool
