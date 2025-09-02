# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import argparse
import glob
import inspect
import json
import os
import shutil
from typing import Callable, Dict

import omni.repo.man
import packmanapi
import toml


def __resolve_oav_version() -> str:
    tokens = {
        "platform_target_abi": omni.repo.man.resolve_tokens("${platform_target_abi}"),
        "platform_host": omni.repo.man.resolve_tokens("${platform}"),
        "platform": omni.repo.man.resolve_tokens("${platform}"),
        "config": omni.repo.man.resolve_tokens("${config}"),
    }

    try:
        info = packmanapi.resolve_dependency(
            "omni_asset_validator",
            "deps/target-deps.packman.xml",
            platform=tokens["platform_target_abi"],
            remotes=["packman:cloudfront"],
            tokens=tokens,
        )
        return info["remote_filename"].partition("@")[-1].partition("+")[0]
    except Exception as e:
        raise omni.repo.man.ExpectedError(f"Failed to resolve omni-asset-validator version: {e}")


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    toolConfig = config.get("repo_py_package", {})
    if not toolConfig.get("enabled", True):
        return None

    parser.description = "Tool to build a wheel for the precompiled OpenUSD Exchange modules and all of its runtime dependencies."
    omni.repo.man.add_config_arg(parser)

    def run_repo_tool(_: Dict, config: Dict):
        toolConfig = config["repo_py_package"]
        stagingDir = toolConfig["staging_dir"]
        installDir = toolConfig["install_dir"]
        exclusions = toolConfig.get("exclude", [])
        ignore_callable = shutil.ignore_patterns(*exclusions)
        repoVersionFile = config["repo"]["folders"]["version_file"]
        usdFlavor = omni.repo.man.resolve_tokens("${usd_flavor}")
        usdVer = omni.repo.man.resolve_tokens("${usd_ver}")
        usdIdentifier = f"{usdFlavor}{usdVer}".replace(".", "").replace("-", "")
        oav_version = __resolve_oav_version()
        fullVersion = omni.repo.man.build_number.generate_build_number_from_file(repoVersionFile)
        realVersion, label = fullVersion.split("+")
        if os.environ.get("CI_COMMIT_TAG"):
            # use the version without the USD flavor as public PyPi servers only support simple versioning
            packageVersion = realVersion
        else:
            # use the version with the USD flavor as private PyPi servers support extra identifiers
            packageVersion = f"{realVersion}+{usdIdentifier}.{label.lower()}"

        # copy artifacts so they can be packaged by with a reasonable name
        source = omni.repo.man.resolve_tokens("_build/$platform/$config")
        if os.path.exists(stagingDir):
            shutil.rmtree(stagingDir)
        shutil.copytree(f"{source}/python/usdex/core", f"{stagingDir}/usdex/core", ignore=ignore_callable)
        shutil.copytree(f"{source}/python/usdex/rtx", f"{stagingDir}/usdex/rtx", ignore=ignore_callable)
        shutil.copytree(f"{source}/python/usdex/test", f"{stagingDir}/usdex/test", ignore=ignore_callable)
        shutil.copytree(f"{source}/python/pxr", f"{stagingDir}/pxr", ignore=ignore_callable)
        if omni.repo.man.is_windows():
            # DLLS and plugInfo
            shutil.copytree(f"{source}/lib", f"{stagingDir}/usd_exchange.libs", ignore=ignore_callable)
        else:
            # Only plugInfo (auditwheel will handle libs)
            shutil.copytree(f"{source}/lib/usd", f"{stagingDir}/usd_exchange.libs/usd", ignore=ignore_callable)

        # generate pyproject file
        pyproject_source = omni.repo.man.resolve_tokens("$root/tools/pyproject/pyproject.toml")
        pyproject_target = f"{stagingDir}/pyproject.toml"
        with open(pyproject_source, "r") as f:
            data = toml.load(f)
        data["project"]["version"] = packageVersion
        # inject the specific USD flavor we are building against
        data["project"]["optional-dependencies"].update(
            {
                usdIdentifier: [],
                "test": [f"omniverse-asset-validator=={oav_version}"],
            }
        )
        with open(pyproject_target, "w") as f:
            toml.dump(data, f)

        # generate the README
        readme_source = omni.repo.man.resolve_tokens("$root/README.md")
        readme_target = f"{stagingDir}/README.md"
        with open(readme_source, "r") as f:
            data = f.readlines()
        with open(readme_target, "w") as f:
            f.writelines(data[4:7])

        if omni.repo.man.is_linux():
            # All plugInfo LibraryPath values are going to be incorrect, because auditwheel appends hashes to lib names
            # Fortunately, auditwheel also bakes rpaths into each module & the per plugin LibraryPath is unnecessary
            # Rather than produce plugInfo with false data, we can set empty string to indicate the path is not used.
            # This matches OpenUSD's approach for usd monolithic builds.
            for plugInfo in glob.glob(f"{stagingDir}/usd_exchange.libs/usd/*/resources/plugInfo.json"):
                with open(plugInfo, "r") as f:
                    # remove illegal python style comments from json
                    plugContents = "".join([x for x in f.readlines() if not x.startswith("#")])
                plugData = json.loads(plugContents)
                for plug in plugData.get("Plugins", []):
                    if "LibraryPath" in plug:
                        plug["LibraryPath"] = ""
                with open(plugInfo, "w") as f:
                    json.dump(plugData, f, indent=4)
        elif omni.repo.man.is_windows():
            # On Windows, the plugInfo LibraryPaths values are correct, but in order to auto-locate them the python modules
            # need to be configured to look in the usd_exchange.libs folder using the PXR_USD_WINDOWS_DLL_PATH environment variable.
            with open(f"{stagingDir}/pxr/__init__.py", "w") as f:
                f.write(
                    inspect.cleandoc(
                        """
                        import os

                        # Set environment variable for USD Windows DLL path
                        dll_path = os.path.join(os.path.dirname(__file__), "../usd_exchange.libs")
                        os.environ["PXR_USD_WINDOWS_DLL_PATH"] = os.path.abspath(dll_path)
                        """
                    )
                )
        else:
            raise omni.repo.man.ExpectedError("Unsupported platform")

        # copy the pyproject setup script
        shutil.copyfile(omni.repo.man.resolve_tokens("$root/tools/pyproject/pybuild.py"), f"{stagingDir}/pybuild.py")

        # build the wheel
        build_cmd = omni.repo.man.resolve_tokens("$root/tools/pyproject/pybuild${shell_ext}")
        build_args = [build_cmd, "build", "--format=wheel", f"--directory={stagingDir}", f"--output={stagingDir}/dist"]
        omni.repo.man.logger.info(" ".join(build_args))
        omni.repo.man.run_process(build_args, exit_on_error=True)

        wheel = glob.glob(f"{stagingDir}/dist/*.whl")[0]
        if omni.repo.man.is_windows():
            result = f"{installDir}/{os.path.basename(wheel)}"
            os.makedirs(os.path.dirname(result), exist_ok=True)
            shutil.copyfile(wheel, result)
            print(f"Packaged wheel installed to {result}")
        else:
            # repair the wheel by baking in the shared libraries
            tokens = omni.repo.man.get_tokens()
            platform_target_abi = omni.repo.man.get_abi_platform_translation(tokens["platform"], tokens.get("abi", "2.35"))
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = os.path.abspath(os.path.realpath(f"{source}/lib"))
            auditwheel_cmd = omni.repo.man.resolve_tokens("$root/tools/pyproject/auditwheel${shell_ext}")
            auditwheel_args = [auditwheel_cmd, "repair", wheel, "--plat", platform_target_abi, "--strip", "-w", installDir]
            omni.repo.man.logger.info(" ".join(auditwheel_args))
            omni.repo.man.run_process(auditwheel_args, exit_on_error=True, env=env)

    return run_repo_tool
