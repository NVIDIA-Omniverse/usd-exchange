# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import argparse
import glob
import inspect
import json
import os
import re
import shutil
import tempfile
from typing import Callable, Dict

import omni.repo.man
import toml


def __patch_usd_pluginfo(uv: str, wheel_path: str, out_dir: str, wheel_version: str):
    """Patch each OpenUSD plugin's plugInfo ``LibraryPath`` to point at its auditwheel-hashed shared library.

    auditwheel grafts the bundled USD libraries into the wheel with a content-hash suffix appended to each
    filename, which invalidates the ``LibraryPath`` values OpenUSD ships in its plugInfo files. An incorrect
    path happens to work for plugins whose library is already loaded by importing the matching ``pxr`` module,
    but on-demand Ndr/Sdr discovery & parser plugins (e.g. ``usdMtlx``) are never imported, so OpenUSD's
    ``Plug`` system cannot instantiate them.

    ``wheel unpack`` / ``wheel pack`` are used so the wheel's ``RECORD`` is regenerated correctly.
    """
    with tempfile.TemporaryDirectory() as tmp:
        omni.repo.man.run_process(
            [uv, "tool", "run", "--from", f"wheel=={wheel_version}", "wheel", "unpack", wheel_path, "--dest", tmp],
            exit_on_error=True,
        )
        unpacked = glob.glob(f"{tmp}/*/")[0].rstrip("/")
        libs_root = f"{unpacked}/usd_exchange.libs"

        # Map the original lib name to its auditwheel-hashed name
        hashed_libs = {}
        for lib in glob.glob(f"{libs_root}/*.so*"):
            match = re.match(r"^(lib.+?)-[0-9a-f]{6,}\.so", os.path.basename(lib))
            if match:
                hashed_libs[match.group(1)] = os.path.basename(lib)

        for plugInfo in glob.glob(f"{libs_root}/usd/*/resources/plugInfo.json"):
            with open(plugInfo, "r") as f:
                # plugInfo.json files use python-style `#` comments that are not valid JSON
                data = json.loads("".join(line for line in f if not line.lstrip().startswith("#")))
            modified = False
            for plug in data.get("Plugins", []):
                lib = hashed_libs.get(f"libusd_{plug.get('Name')}")
                if lib and "LibraryPath" in plug:
                    # LibraryPath is resolved relative to the plugin dir (the parent of `resources/`), so `../..`
                    # reaches the `usd_exchange.libs/` root where auditwheel places the hashed libraries.
                    plug["LibraryPath"] = f"../../{lib}"
                    modified = True
            if modified:
                with open(plugInfo, "w") as f:
                    json.dump(data, f, indent=4)

        # repack (regenerates dist-info/RECORD) in place of the original repaired wheel
        os.remove(wheel_path)
        omni.repo.man.run_process(
            [uv, "tool", "run", "--from", f"wheel=={wheel_version}", "wheel", "pack", unpacked, "--dest-dir", out_dir],
            exit_on_error=True,
        )


def __strip_shared_objects(lib_globs):
    """Strip symbols (in place) from the shared objects matched by ``lib_globs``.

    This must run *before* auditwheel's ``patchelf`` does: for the staged python extension modules that means
    before ``uv build``, and for the grafted external libraries that means before ``auditwheel repair``.
    Stripping *after* patchelf -- which is exactly what ``auditwheel repair --strip`` does -- rewrites the
    patchelf-extended ELF and can leave ``LOAD`` segments that are no longer page-aligned, so the dynamic
    loader rejects the library at import time with "ELF load command address/offset not page-aligned". This
    only reproduces on some USD flavors (e.g. 25.11) whose binaries trigger the misalignment.

    Symlinks are resolved and de-duplicated so versioned ``.so`` chains (e.g. ``libFoo.so -> libFoo.so.1.2.3``)
    keep their links intact and only the real ELF files are stripped.
    """
    stripped = set()
    for pattern in lib_globs:
        for path in glob.glob(pattern, recursive=True):
            real = os.path.realpath(path)
            if real in stripped or not os.path.isfile(real):
                continue
            with open(real, "rb") as binary:
                if binary.read(4) != b"\x7fELF":
                    continue
            stripped.add(real)
            omni.repo.man.run_process(["strip", real], exit_on_error=True)


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
        auditwheelVersion = toolConfig["auditwheel_version"]
        patchelfVersion = toolConfig["patchelf_version"]
        wheelVersion = toolConfig["wheel_version"]
        exclusions = toolConfig.get("exclude", [])
        # "cmake": keep the lib/cmake find_package config out of the wheel (it's for native consumers)
        ignore_callable = shutil.ignore_patterns(*exclusions, "cmake")
        repoVersionFile = config["repo"]["folders"]["version_file"]
        usdFlavor = omni.repo.man.resolve_tokens("${usd_flavor}")
        usdVer = omni.repo.man.resolve_tokens("${usd_ver}")
        usdIdentifier = f"{usdFlavor}{usdVer}".replace(".", "").replace("-", "")
        validatorVersion = config["repo_install_usdex"]["usd_validation_version"]
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
                "test": [f"usd-validation-nvidia=={validatorVersion}"],
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

        # gather the license files
        license_files = [
            ("$root/LICENSE.md", f"{stagingDir}/usd-exchange-LICENSE.md"),
            ("$root/_build/target-deps/pybind11/PACKAGE-LICENSES/pybind11-LICENSE.txt", None),
            ("$root/tools/internal-licenses/pyboost11-LICENSE.txt", None),
            ("$root/_build/target-deps/usd/release/PACKAGE-LICENSES/*tbb-LICENSE*", None),
            ("$root/_build/target-deps/usd/release/PACKAGE-LICENSES/usd-license.txt", None),
            ("$root/_build/target-deps/usd/release/PACKAGE-LICENSES/zlib-LICENSE*", None),
            # Workaround for hwloc as the license file only applies to oneTBB packages, some wheels build with older TBB
            ("$root/tools/extra-licenses/hwloc-COPYING.txt*", None),
        ]
        for src, target in license_files:
            resolved_src = omni.repo.man.resolve_tokens(src)
            matches = glob.glob(resolved_src)
            if matches:
                source_file = matches[0]
                if target is None:
                    target = f"{stagingDir}/{os.path.basename(source_file)}"
                shutil.copyfile(source_file, target)
            else:
                raise omni.repo.man.ExpectedError(f"Unable to find license file for pattern: {src}")

        if omni.repo.man.is_windows():
            # On Windows, the plugInfo LibraryPaths values are correct, but in order to auto-locate them the python modules
            # need to be configured to look in the usd_exchange.libs folder using the PXR_USD_WINDOWS_DLL_PATH environment variable.
            with open(f"{stagingDir}/pxr/__init__.py", "w") as f:
                f.write(
                    inspect.cleandoc(
                        """
                        import os

                        # Set environment variable for USD Windows DLL path
                        dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../usd_exchange.libs"))
                        os.environ["PXR_USD_WINDOWS_DLL_PATH"] = dll_path

                        # OpenUSD's Plug loader resolves lazy plugin dependencies through the process PATH.
                        path_entries = os.environ.get("PATH", "").split(os.pathsep)
                        normalized_entries = [os.path.normcase(os.path.normpath(entry)) for entry in path_entries if entry]
                        if os.path.normcase(os.path.normpath(dll_path)) not in normalized_entries:
                            os.environ["PATH"] = dll_path + os.pathsep + os.environ.get("PATH", "")
                        """
                    )
                )
        elif not omni.repo.man.is_linux():
            raise omni.repo.man.ExpectedError("Unsupported platform")
        # On Linux the plugInfo LibraryPath values are patched after auditwheel (see __patch_usd_pluginfo), once the
        # final hashed library names are known.

        # copy the hatchling build hook (forces a platform/abi-tagged wheel)
        shutil.copyfile(omni.repo.man.resolve_tokens("$root/tools/pyproject/hatch_build.py"), f"{stagingDir}/hatch_build.py")

        if omni.repo.man.is_linux():
            # Strip the staged binaries, so `strip` runs before auditwheel's `patchelf`
            __strip_shared_objects([f"{stagingDir}/**/*.so"])

        # build the wheel with uv, targeting the packman python so the wheel gets the correct interpreter/abi tag
        uv = str(omni.repo.man.get_uv())
        python_exe = omni.repo.man.resolve_tokens("$root/_build/target-deps/python/python${exe_ext}")
        build_args = [uv, "build", "--wheel", f"--python={python_exe}", f"--out-dir={stagingDir}/dist", stagingDir]
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
            # Strip the external libs auditwheel is about to graft so that `strip` runs before auditwheel's `patchelf`
            __strip_shared_objects([f"{source}/lib/*.so*"])
            # repair via auditwheel using an ephemeral env; patchelf is auditwheel's runtime dependency.
            auditwheel_args = [
                uv,
                "tool",
                "run",
                "--from",
                f"auditwheel=={auditwheelVersion}",
                "--with",
                f"patchelf=={patchelfVersion}",
                "auditwheel",
                "repair",
                wheel,
                "--plat",
                platform_target_abi,
                "-w",
                installDir,
            ]
            omni.repo.man.logger.info(" ".join(auditwheel_args))
            omni.repo.man.run_process(auditwheel_args, exit_on_error=True, env=env)

            # auditwheel renames the bundled libs with content hashes, which invalidates the plugInfo LibraryPath values,
            # so we need to patch the plugInfo LibraryPath values to point at the new hashed library names.
            wheel_tag_prefix = os.path.basename(wheel).rsplit("-", 1)[0]
            __patch_usd_pluginfo(uv, f"{installDir}/{wheel_tag_prefix}-{platform_target_abi}.whl", installDir, wheelVersion)

    return run_repo_tool
