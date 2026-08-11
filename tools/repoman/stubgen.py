# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
import glob
import logging
import os
import sys
from pathlib import Path
from typing import Callable, Dict

import omni.repo.man

logger = logging.getLogger(os.path.basename(__file__))


def generate(tool_config, options, repo_folders):
    sys.path.append(omni.repo.man.resolve_tokens(tool_config["pybind11_stubgen"]))
    import pybind11_stubgen

    pybind11_stubgen_options = argparse.Namespace(include=[], exclude=[], exec="")
    for path in tool_config.get("stubgen_include", []):
        pybind11_stubgen_options.include.append(os.path.normpath(omni.repo.man.resolve_tokens(path)))
    for path in tool_config.get("stubgen_exclude", []):
        pybind11_stubgen_options.exclude.append(os.path.normpath(omni.repo.man.resolve_tokens(path)))

    # Time check. Store last time we run, if of python libraries are older -> do nothing.
    time_check_file = os.path.join(repo_folders["build"], f".laststubgen_{options.config}")
    lastrun_time = os.path.getmtime(time_check_file) if os.path.isfile(time_check_file) and not options.force_run else 0

    def excluded(path):
        for exclude in pybind11_stubgen_options.exclude:
            if exclude in path:
                return True

    # Find modules with out of date stubs
    modules = []
    found_any_modules = False
    search_wildcard = omni.repo.man.resolve_tokens("${bindings_ext}")
    for path in pybind11_stubgen_options.include:
        search_path = path + "/**/*" + search_wildcard
        logger.info(f"Looking for python modules in '{search_path}'...")
        for filepath in glob.glob(search_path, recursive=True):
            filepath = os.path.normpath(filepath)
            if excluded(filepath):
                logger.info(f"skipping excluded module: '{filepath}'")
                continue
            if os.path.getmtime(filepath) < lastrun_time:
                logger.info(f"skipping up to date module: '{path}'")
                found_any_modules = True
                continue
            module = ".".join(Path(filepath).absolute().parts[len(Path(path).absolute().parts) : -1])
            modules.append((module, path))

    # Run pybind11_stubgen script. It will find all python modules in that repo and generate stubs for them.
    if not modules:
        if found_any_modules:
            print(f"All modules have up to date stubs. To force regeneration use --force or delete {time_check_file}")
        else:
            logger.warning("No compiled modules found for stub generation")
        return

    for module, path in modules:
        logger.info(f"importing: '{module}'")
        exec(f"import {module}")

    for module, path in pybind11_stubgen.find_all_library_modules(pybind11_stubgen_options):
        # [Hack for USD modules]
        # All USD modules have this Tf.PrepareModule() which at import time copies libs like _gf.pyd them into
        # __init__.py nearby. That doesn't work with Pylance well. Basically you need to use `Gf._gf` instead
        # of `Gf.`. As a work around just instead of generating _gf.pyi file we generate __init__.pyi file. So that
        # `Gf.` is the same as `Gf._gf` for autocompletion. We lose content of __init__.py itself in that case, but
        # it is usually empty anyway.
        init_path = Path(path).parent.joinpath("__init__.py")
        if init_path.exists():
            text = init_path.read_text()
            if "Tf.PreparePythonModule(" in text or "Tf.PrepareModule(" in text:
                path = str(Path(path).parent.joinpath("__init__.pyi"))

        print(f"Generating stubs for module: {module}, path: '{path}'")
        gen = pybind11_stubgen.ModuleStubsGenerator(module, path)
        gen.parse()
        gen.write(copy_back=False)

    # Check at least that some .pyi files were create in each of module folders
    any_missing = False
    for module, path in modules:
        if len(list(glob.glob(path + "/**/*.pyi", recursive=True))) == 0:
            logger.error(f"Couldn't find any .pyi files in '{path}'. Generation failed.")
            any_missing = True
    if any_missing:
        sys.exit(-1)
    else:
        print("python stub generation succeeded")

    # Update timestamp
    Path(time_check_file).touch()


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    tool_config = config.get("repo_stubgen", {})
    enabled = tool_config.get("enabled", False)
    if not enabled:
        return None

    parser.description = "Tool to generate stub files (.pyi) for python modules compiled with pybind11."
    omni.repo.man.add_config_arg(parser)
    parser.add_argument(
        "-r",
        "--runtimePath",
        dest="runtime_path",
        type=str,
        help="The runtime location (eg CARB_APP_PATH)",
    )
    parser.add_argument(
        "-f",
        "--force",
        dest="force_run",
        required=False,
        action="store_true",
        help="Ignore timestamp check and run stubgen regardless.",
    )

    def run_repo_tool(options: Dict, config: Dict):
        import omni.repo.man
        import omni.repo.test

        if omni.repo.man.resolve_tokens("$python_ver") == "0":
            # short-circuit for nopy flavors
            return

        repo_folders = config["repo"]["folders"]

        runtime_path = omni.repo.man.resolve_tokens(options.runtime_path or config.get("repo_stubgen", {}).get("runtime_path"))

        # use the tool_config as a suite_config for env configuration
        suite_config = config.get("repo_stubgen", {}).copy()
        for key in (
            "env_vars",
            "library_paths",
            "python_paths",
        ):
            if key not in suite_config:
                suite_config[key] = config["repo_test"].get(key, [])

        suite_config["env_vars"].append(["CARB_APP_PATH", runtime_path])
        suite_config["library_paths"].append(runtime_path)
        suite_config["python_paths"].append(os.path.join(runtime_path, "python"))
        suite_config["python_paths"].append(os.path.join(runtime_path, "bindings-python"))

        # spoof a usable runtime environment via repo_test
        omni.repo.test.set_env_paths(config, suite_config, runtime_path, options, omni.repo.man.get_host_platform())

        generate(tool_config, options, repo_folders)

    return run_repo_tool
