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
import stat
from typing import Callable, Dict

import fetch_deps
import omni.repo.man
import usd_deps

# release/debug token -> CMake configuration name
_CMAKE_CONFIG = {"release": "Release", "debug": "Debug"}


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
        python_pkg = omni.repo.man.resolve_tokens("${python_pkg}")
        abi = omni.repo.man.resolve_tokens("${abi}")
        cmake_config = _CMAKE_CONFIG.get(repo_config, "Release")

        output_dir = f"{root}/_build/{platform}/{repo_config}"  # staged/packaged artifacts land here
        build_dir = f"{root}/_build/cmake/{platform}/{repo_config}"  # CMake intermediates (sibling of the staged tree)

        if options.clean or options.rebuild:
            omni.repo.man.logger.info(f"cmake: cleaning {root}/_build")
            shutil.rmtree(f"{root}/_build", ignore_errors=True)
        if options.clean:
            return

        # regenerate the flavor's usd-deps manifest and fetch the packages
        usd_deps.generate_usd_deps(usd_flavor, usd_ver, python_ver, config["repo"]["default_flavor"])
        pulled = fetch_deps.fetch_dependencies(config, repo_config)
        strip_deps = config.get("repo_cmake", {}).get("strip_deps", [])

        build_string = omni.repo.man.build_number.generate_build_number_from_file(config["repo"]["folders"]["version_file"])
        version_string = build_string.split("+")[0]

        # repo_docs reads the version from a $root/VERSION stub (it does not honor repo.folders.version_file)
        with open(f"{root}/VERSION", "w") as f:
            f.write(version_string)

        usd_root = f"{root}/_build/target-deps/usd/{repo_config}"
        python_root = f"{root}/_build/target-deps/python"
        target_deps = f"{root}/_build/target-deps"

        # prefer the packman-provided cmake; fall back to a system cmake otherwise
        exe_ext = omni.repo.man.resolve_tokens("${exe_ext}")
        cmake_exe = f"{root}/_build/host-deps/cmake/bin/cmake{exe_ext}"
        if os.path.exists(cmake_exe):
            # packman zip packages can drop the executable bit on extraction; restore owner-execute before invoking
            # (we run cmake as the current user, so there's no need to grant group/other execute)
            os.chmod(cmake_exe, os.stat(cmake_exe).st_mode | stat.S_IXUSR)
        else:
            cmake_exe = "cmake"

        configure = [
            cmake_exe,
            "-S",
            root,
            "-B",
            build_dir,
            f"-DCMAKE_BUILD_TYPE={cmake_config}",
            "-DCMAKE_INSTALL_LIBDIR=lib",  # our package layout uses lib/, not lib64
            f"-DUSDEX_USD_ROOT={usd_root}",
            f"-DUSDEX_TBB_ROOT={target_deps}/tbb/{repo_config}",
            f"-DUSDEX_MATERIALX_ROOT={target_deps}/materialx/{repo_config}",
            f"-DUSDEX_PYTHON_VERSION={python_ver}",
            f"-DUSDEX_VERSION_STRING={version_string}",
            f"-DUSDEX_BUILD_STRING={build_string}",
            "-DUSDEX_COMPANY_NAME=NVIDIA",  # this is an official NVIDIA build; external builds leave CompanyName empty
            f"-DUSDEX_PYBIND11_INCLUDE_DIR={target_deps}/pybind11/include",
            "-DUSDEX_BUILD_TESTS=ON",
            f"-DUSDEX_CXXOPTS_INCLUDE_DIR={target_deps}/cxxopts/include",
            f"-DUSDEX_DOCTEST_INCLUDE_DIR={target_deps}/doctest/include",
        ]
        if python_ver != "0":
            # locate the target python, not a system interpreter
            configure += [f"-DPython3_ROOT_DIR={python_root}", "-DPython3_FIND_STRATEGY=LOCATION"]
        if platform.startswith("windows"):
            # on windows the abi is the MSVC toolset (e.g. v143); pin it so our binaries match the toolset of the openusd packages we link
            configure += ["-T", abi]

        omni.repo.man.logger.info(" ".join(configure))
        omni.repo.man.run_process(configure, exit_on_error=True)

        if options.generate:
            # compile_commands.json + generated headers are produced at configure; skip compiling
            return

        build = [cmake_exe, "--build", build_dir, "--config", cmake_config, "-j", str(os.cpu_count() or 1)]
        omni.repo.man.logger.info(" ".join(build))
        omni.repo.man.run_process(build, exit_on_error=True)

        if not options.skip_post:
            # assemble the relocatable tree (libs, headers, python, dev/, find_package config) into output_dir
            install = [cmake_exe, "--install", build_dir, "--config", cmake_config, "--prefix", output_dir]
            omni.repo.man.logger.info(" ".join(install))
            omni.repo.man.run_process(install, exit_on_error=True)

            # gather third-party licenses into _build/PACKAGE-LICENSES (shipped by the package)
            omni.repo.man.run_process(
                [
                    repo,
                    "--set-token",
                    f"platform_host:{platform}",  # usd-deps.packman.xml references it
                    "--set-token",
                    f"python_pkg:{python_pkg}",  # the python side-car imported by target-deps.packman.xml references it
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
