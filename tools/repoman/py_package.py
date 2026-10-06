# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import argparse
import glob
import inspect
import os
import shutil
import subprocess
import tempfile
from typing import Callable, Dict

import licenses
import omni.repo.man
import toml


def __is_elf(path: str) -> bool:
    with open(path, "rb") as binary:
        return binary.read(4) == b"\x7fELF"


def __stage_linux_libraries(patchelf: list, source_lib: str, libs_root: str) -> list:
    """Copy the runtime libraries into ``libs_root`` under their SONAMEs, returning the SONAMEs staged.

    auditwheel only grafts, and renames, the libraries it resolves outside the wheel. Staging them ourselves, as the
    Windows wheel does, keeps the names OpenUSD, oneTBB and MaterialX were built with, which are the names a native
    consumer linked against the same OpenUSD build already depends on. Wheels cannot contain symlinks, so each real
    file is copied once, under the name the loader asks for (``libtbb.so.12``, not ``libtbb.so.12.13``).
    """
    staged = {}
    for lib in sorted(glob.glob(f"{source_lib}/*.so*")):
        if os.path.islink(lib) or not __is_elf(lib):
            continue
        # stdout only: the first `uv tool run` reports installing patchelf on stderr
        soname = subprocess.run([*patchelf, "--print-soname", lib], capture_output=True, text=True, check=True).stdout.strip()
        soname = soname or os.path.basename(lib)
        if not soname.startswith("lib") or ".so" not in soname or "/" in soname:
            raise omni.repo.man.ExpectedError(f"Unexpected SONAME {soname!r} for {lib}")
        if soname in staged:
            raise omni.repo.man.ExpectedError(f"{lib} and {staged[soname]} both provide {soname}")
        staged[soname] = lib
        shutil.copyfile(lib, f"{libs_root}/{soname}")
    return sorted(staged)


def __set_linux_rpaths(patchelf: list, staging_dir: str):
    """Point every staged binary's RPATH at ``usd_exchange.libs``, relative to the binary itself.

    The OpenUSD and usdex binaries carry RPATHs for the install tree they were built into, e.g. ``$ORIGIN/../../..``
    for a ``pxr`` extension module and absolute build-machine paths for the libraries, none of which exist in a wheel.
    ``--force-rpath`` writes ``DT_RPATH``, as auditwheel does, so it also governs the libraries these load in turn.
    """
    libs_root = f"{staging_dir}/usd_exchange.libs"
    for binary in glob.glob(f"{staging_dir}/**/*.so*", recursive=True):
        if os.path.islink(binary) or not __is_elf(binary):
            continue
        relative = os.path.relpath(libs_root, os.path.dirname(binary))
        rpath = "$ORIGIN" if relative == "." else f"$ORIGIN/{relative}"
        omni.repo.man.run_process([*patchelf, "--force-rpath", "--set-rpath", rpath, binary], exit_on_error=True)


def __drop_libpython_dependency(uv: str, patchelf_version: str, unpacked: str):
    """Remove every ``libpython`` ``DT_NEEDED`` entry from the wheel's shared libraries.

    A wheel must resolve the CPython symbols from whichever interpreter imported it, so auditwheel drops these
    entries from the binaries the wheel already contained, but it does not repeat that pass over the libraries
    it grafts in. Those keep the dependency, and an interpreter that ships no ``libpython`` shared library then
    fails the import with "libpython3.x.so.1.0: cannot open shared object file".
    """
    patchelf = [uv, "tool", "run", "--from", f"patchelf=={patchelf_version}", "patchelf"]
    for lib in glob.glob(f"{unpacked}/**/*.so*", recursive=True):
        if os.path.islink(lib) or not os.path.isfile(lib):
            continue
        with open(lib, "rb") as binary:
            if binary.read(4) != b"\x7fELF":
                continue
        _, output = omni.repo.man.run_process_return_output([*patchelf, "--print-needed", lib], exit_on_error=True, print_stdout=False)
        for needed in [line.strip() for line in output if line.strip().startswith("libpython")]:
            omni.repo.man.run_process([*patchelf, "--remove-needed", needed, lib], exit_on_error=True)


def __patch_wheel(uv: str, wheel_path: str, out_dir: str, wheel_version: str, patchelf_version: str):
    """Apply the fixes that can only be made once auditwheel has repaired the wheel.

    ``wheel unpack`` / ``wheel pack`` are used so the wheel's ``RECORD`` is regenerated correctly.
    """
    with tempfile.TemporaryDirectory() as tmp:
        omni.repo.man.run_process(
            [uv, "tool", "run", "--from", f"wheel=={wheel_version}", "wheel", "unpack", wheel_path, "--dest", tmp],
            exit_on_error=True,
        )
        unpacked = glob.glob(f"{tmp}/*/")[0].rstrip("/")

        __drop_libpython_dependency(uv, patchelf_version, unpacked)

        # repack (regenerates dist-info/RECORD), naming the wheel from the tags auditwheel wrote into its `WHEEL`
        omni.repo.man.run_process(
            [uv, "tool", "run", "--from", f"wheel=={wheel_version}", "wheel", "pack", unpacked, "--dest-dir", out_dir],
            exit_on_error=True,
        )


def __strip_shared_objects(lib_globs):
    """Strip symbols (in place) from the shared objects matched by ``lib_globs``.

    This must run *before* any ``patchelf`` edit, so before the staged binaries' RPATHs are set and before
    ``auditwheel repair``. Stripping *after* patchelf -- which is exactly what ``auditwheel repair --strip`` does -- rewrites the
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
        uv = str(omni.repo.man.get_uv())
        patchelf = [uv, "tool", "run", "--from", f"patchelf=={patchelfVersion}", "patchelf"]
        if omni.repo.man.is_windows():
            # DLLs and plugInfo
            shutil.copytree(f"{source}/bin", f"{stagingDir}/usd_exchange.libs", ignore=ignore_callable)
        else:
            # plugInfo, whose LibraryPath values already resolve to the libraries staged beside it
            shutil.copytree(f"{source}/lib/usd", f"{stagingDir}/usd_exchange.libs/usd", ignore=ignore_callable)
            stagedLibs = __stage_linux_libraries(patchelf, f"{source}/lib", f"{stagingDir}/usd_exchange.libs")

        # generate pyproject file
        pyproject_source = omni.repo.man.resolve_tokens("$root/tools/pyproject/pyproject.toml")
        pyproject_target = f"{stagingDir}/pyproject.toml"
        with open(pyproject_source, "r") as f:
            data = toml.load(f)
        data["project"]["version"] = packageVersion
        # inject the specific USD flavor we are building against
        # the validator floor is the version we test against, the major ceiling guards the APIs usdex.test calls at import time
        validatorCeiling = int(validatorVersion.split(".")[0]) + 1
        data["project"]["optional-dependencies"].update(
            {
                usdIdentifier: [],
                "test": [f"usd-validation-nvidia>={validatorVersion},<{validatorCeiling}"],
            }
        )
        with open(pyproject_target, "w") as f:
            toml.dump(data, f)

        # generate the README
        readme_source = omni.repo.man.resolve_tokens("$root/README.md")
        notice_source = omni.repo.man.resolve_tokens("$root/tools/pyproject/pypi-notice.md")
        readme_target = f"{stagingDir}/README.md"
        with open(readme_source, "r") as f:
            data = f.readlines()
        with open(notice_source, "r") as f:
            notice = f.read()
        with open(readme_target, "w") as f:
            f.writelines(data[4:7])
            f.write(f"\n{notice}")

        # gather the license files
        licenses.gather(stagingDir, "release", licenses.WHEEL_NOTICES)

        if omni.repo.man.is_windows():
            # On Windows, the plugInfo LibraryPaths values are correct, but in order to auto-locate them the python modules
            # need to be configured to look in the usd_exchange.libs folder using the PXR_USD_WINDOWS_DLL_PATH environment variable.
            with open(f"{stagingDir}/pxr/__init__.py", "w") as f:
                f.write(inspect.cleandoc("""
                        import os

                        # Prepend the wheel's DLL path while preserving caller-supplied fallback paths.
                        dll_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../usd_exchange.libs"))
                        # OpenUSD searches PATH when PXR_USD_WINDOWS_DLL_PATH is unset, so keep that as the fallback.
                        dll_paths = os.environ.get("PXR_USD_WINDOWS_DLL_PATH", os.environ.get("PATH", "")).split(os.pathsep)
                        normalized_dll_path = os.path.normcase(os.path.normpath(dll_path))
                        dll_paths = [
                            path
                            for path in dll_paths
                            if path and os.path.normcase(os.path.normpath(path)) != normalized_dll_path
                        ]
                        os.environ["PXR_USD_WINDOWS_DLL_PATH"] = os.pathsep.join([dll_path, *dll_paths])

                        # OpenUSD's Plug loader resolves lazy plugin dependencies through the process PATH.
                        path_entries = [
                            entry
                            for entry in os.environ.get("PATH", "").split(os.pathsep)
                            if entry and os.path.normcase(os.path.normpath(entry)) != normalized_dll_path
                        ]
                        os.environ["PATH"] = os.pathsep.join([dll_path, *path_entries])
                        """))
        elif not omni.repo.man.is_linux():
            raise omni.repo.man.ExpectedError("Unsupported platform")

        # copy the hatchling build hook (forces a platform/abi-tagged wheel)
        shutil.copyfile(omni.repo.man.resolve_tokens("$root/tools/pyproject/hatch_build.py"), f"{stagingDir}/hatch_build.py")

        if omni.repo.man.is_linux():
            # Strip the staged binaries, so `strip` runs before any `patchelf` edit
            __strip_shared_objects([f"{stagingDir}/**/*.so*"])
            __set_linux_rpaths(patchelf, stagingDir)

        # build the wheel with uv, targeting the packman python so the wheel gets the correct interpreter/abi tag
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
            with tempfile.TemporaryDirectory() as repairDir:
                # repair via auditwheel using an ephemeral env; patchelf is auditwheel's runtime dependency.
                # `--plat` is left at its `auto` default so the tag follows the symbols the artifacts actually reference.
                # Naming a tag can only over-declare it, as auditwheel stamps anything at or above its floor verbatim.
                # The staged libraries already resolve inside the wheel, so auditwheel grafts none of them. Excluding
                # their SONAMEs as well guarantees a resolution miss can never graft a second, renamed copy; the wheel
                # tests fail on the unresolved dependency instead. Excluded libraries inside the wheel still count
                # towards the platform tag, since auditwheel reads the symbols of every ELF file the wheel contains.
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
                    "-w",
                    repairDir,
                    *[arg for soname in stagedLibs for arg in ("--exclude", soname)],
                ]
                omni.repo.man.logger.info(" ".join(auditwheel_args))
                omni.repo.man.run_process(auditwheel_args, exit_on_error=True)

                repaired = glob.glob(f"{repairDir}/*.whl")[0]
                os.makedirs(installDir, exist_ok=True)
                __patch_wheel(uv, repaired, installDir, wheelVersion, patchelfVersion)
                print(f"Packaged wheel installed to {installDir}/{os.path.basename(repaired)}")

    return run_repo_tool
