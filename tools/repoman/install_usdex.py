# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import argparse
import contextlib
import os
import re
import shutil
from typing import Callable, Dict, List

import omni.repo.man
import packmanapi


class __SemVersion:
    """A minimal semantic version comparator."""

    def __init__(self, version: str):
        # Keep only the numeric parts at the start, stopping at the first non-numeric part in each segment
        self.parts = []
        for part in version.split("."):
            part = part.lstrip()  # Strip whitespace from the front of the part
            num = ""
            for c in part:
                if c.isdigit():
                    num += c
                else:
                    break
            if num:
                self.parts.append(int(num))
            else:
                break
        self.parts = tuple(self.parts)

    def __eq__(self, other):
        return self.parts == other.parts

    def __lt__(self, other):
        # Compare each part, pad with zeros for uneven lengths
        maxlen = max(len(self.parts), len(other.parts))
        a = self.parts + (0,) * (maxlen - len(self.parts))
        b = other.parts + (0,) * (maxlen - len(other.parts))
        return a < b

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        return not self <= other

    def __ge__(self, other):
        return not self < other

    def __repr__(self):
        return f"__SemVersion({'.'.join(map(str, self.parts))})"


def __installPythonModule(prebuild_copy_dict: Dict, sourceRoot: str, moduleNamespace: str, libPrefix: str):
    pythonInstallDir = "${install_dir}/python/" + moduleNamespace
    prebuild_copy_dict.extend(
        [
            [f"{sourceRoot}/{moduleNamespace}/*.py", pythonInstallDir],
            [f"{sourceRoot}/{moduleNamespace}/*.pyi", pythonInstallDir],
            [f"{sourceRoot}/{moduleNamespace}/{libPrefix}*" + "${bindings_ext}", pythonInstallDir],
        ]
    )


def __acquireUSDEX(installDir, useExistingBuild, targetDepsDir, repoVersionFile, usd_flavor, usd_ver, python_ver, buildConfig, version, tokens):
    """Acquire usd-exchange

    This function operates in three different modes:
    - Run from within usdex repo
        - `useExistingBuild` early exit, usdex is already "acquired"
        - otherwise `version` is required, packageName@$version+$platform_target_abi.$buildConfig is fetched from packman and
          linked to `$targetDepsDir/usd-exchange/$buildConfig`
    - Run from within a downstream repo with a configured `target-deps.packman.xml`
        - if using a remote usdex package, package name and version is read and packageName@$packageVersion is fetched from packman
            - this is because packageVersion is hardcoded in the `target-deps` file and doesn't require an appended platform and buildConfig
        - if using a local usdex build, a link is created in `$targetDepsDir/usd-exchange/$buildConfig`
    """
    if useExistingBuild:
        print(f"Using local usd-exchange from {installDir}")
        return installDir

    packageName = None
    packageVersion = None
    if not version:
        info = {}
        # check for a packman dependency
        with contextlib.suppress(packmanapi.PackmanError):
            info = packmanapi.resolve_dependency(
                "usd-exchange",
                "deps/target-deps.packman.xml",
                platform=tokens["platform_target_abi"],
                remotes=["packman:cloudfront"],
                tokens=tokens,
            )
        if "remote_filename" in info:
            # override the package info using details from the remote
            parts = info["remote_filename"].split("@")
            packageName = parts[0]
            packageVersion = os.path.splitext(parts[1])[0]
        elif "local_path" in info:
            # its a local source linked usdex
            linkPath = f"{targetDepsDir}/usd-exchange/{buildConfig}"
            print(f"Link local usd-exchange to {linkPath}")
            packmanapi.link(linkPath, info["local_path"])
            return linkPath

    # No version passed into the function and no packageVersion found in target-deps
    if not version and not packageVersion:
        # Determine the default version for cloned repo when the user "just wants the version associated with this branch"
        if os.path.exists(repoVersionFile):
            package_version = omni.repo.man.build_number.generate_build_number_from_file(repoVersionFile)
            version = package_version.split("+")[0]

        if not version:
            raise omni.repo.man.exceptions.ConfigurationError(
                "No version was specified. Use the `--version` argument or setup a packman dependency for usd-exchange"
            )

    # respect flavor variations if they are provided
    if not packageName or (usd_flavor and usd_ver and python_ver):
        packageName = f"usd-exchange_{usd_flavor}_{usd_ver}_py_{python_ver}"

    linkPath = f"{targetDepsDir}/usd-exchange/{buildConfig}"
    # packageVersion is empty if a version was passed this function
    if not packageVersion:
        packageVersion = f"{version}+{tokens['platform_target_abi']}.{buildConfig}"
    print(f"Download and Link usd-exchange {packageVersion} to {linkPath}")
    try:
        result = packmanapi.install(name=packageName, package_version=packageVersion, remotes=["packman:cloudfront"], link_path=linkPath)
        return list(result.values())[0]
    except packmanapi.PackmanErrorFileNotFound:
        raise omni.repo.man.exceptions.ConfigurationError(f"Unable to download {packageName}, version {packageVersion}")


def __computeUsdMidfix(usd_root: str):
    # try to find out what the USD prefix is by looking for a known non-monolithic USD library name with a longer name
    usd_libraries = [f for f in os.listdir(os.path.join(usd_root, "lib")) if re.match(r".*usdGeom.*", f)]
    if usd_libraries:
        # sort the results by length and use the first one
        usd_libraries.sort(key=len)
        usd_library = os.path.splitext(os.path.basename(usd_libraries[0]))[0]
        usd_lib_prefix = usd_library[:-7]
        if os.name != "nt":  # equivalent to os.host() ~= "windows"
            # we also picked up the lib part, which we don't want
            return usd_lib_prefix[3:], False
        else:
            return usd_lib_prefix, False
    else:
        # couldn't find a prefixed or un-prefixed usdGeom library could be monolithic - we do this last because *usd_ms is a
        # very short name to match and likely would be matched by several libraries
        library_name = None
        library_prefix = ""

        # first try looking for the release build
        monolithic_libraries = [f for f in os.listdir(os.path.join(usd_root, "lib")) if re.match(r".*usd_ms.*", f)]
        if monolithic_libraries:
            # sort the results by length and use the first one
            monolithic_libraries.sort(key=len)
            library_name = os.path.splitext(os.path.basename(monolithic_libraries[0]))[0]

        if os.name != "nt" and library_name is not None:
            # We picked up the library prefix from the file name (i.e libusd_ms.so)
            library_name = library_name[3:]

        if library_name is not None:
            start_index = library_name.rfind("usd_ms")
            if start_index > 0:
                library_prefix = library_name[:start_index]

        return library_prefix, True


def __install(
    installDir: str,
    useExistingBuild: bool,
    stagingDir: str,
    usd_flavor: str,
    usd_ver: str,
    python_ver: str,
    usd_validation_version: str,
    uv_extra_index_url: str,
    repoVersionFile: str,
    buildConfig: str,
    clean: bool,
    version: str,
    installPythonLibs: bool,
    installRtxModules: bool,
    installTestModules: bool,
    extraPlugins: List[str],
):
    tokens = omni.repo.man.get_tokens()
    tokens["config"] = buildConfig
    platform = tokens["platform"]
    tokens["platform_host"] = platform
    tokens["platform_target_abi"] = omni.repo.man.get_abi_platform_translation(platform, tokens.get("abi", "2.35"))
    installDir = omni.repo.man.resolve_tokens(installDir, extra_tokens=tokens)
    targetDepsDir = omni.repo.man.resolve_tokens(f"{stagingDir}/target-deps", extra_tokens=tokens)

    if clean:
        print(f"Cleaning install dir {installDir}")
        shutil.rmtree(installDir, ignore_errors=True)
        print(f"Cleaning staging dir {stagingDir}")
        shutil.rmtree(stagingDir, ignore_errors=True)
        return

    usd_exchange_path = __acquireUSDEX(
        installDir,
        useExistingBuild,
        targetDepsDir,
        repoVersionFile,
        usd_flavor,
        usd_ver,
        python_ver,
        buildConfig,
        version,
        tokens,
    )

    runtimeDeps = [f"usd-{buildConfig}", f"tbb-{buildConfig}", f"materialx-{buildConfig}"]
    if python_ver != "0":
        runtimeDeps.append("python")

    print("Download usd-exchange dependencies...")
    depsFile = f"{usd_exchange_path}/dev/deps/all-deps.packman.xml"
    result = packmanapi.pull(depsFile, platform=platform, tokens=tokens, return_extra_info=True)
    for dep, info in result.items():
        if dep in runtimeDeps:
            if dep == f"usd-{buildConfig}":
                linkPath = f"{targetDepsDir}/usd/{buildConfig}"
            elif dep == f"tbb-{buildConfig}":
                linkPath = f"{targetDepsDir}/tbb/{buildConfig}"
            elif dep == f"materialx-{buildConfig}":
                linkPath = f"{targetDepsDir}/materialx/{buildConfig}"
            elif "package_name" in info and buildConfig in info["package_name"]:  # dep uses omniflow v2 naming with separate release/debug packages
                linkPath = f"{targetDepsDir}/{dep}/{buildConfig}"
            elif "local_path" in info and buildConfig in info["local_path"]:  # dep is source linked locally
                linkPath = f"{targetDepsDir}/{dep}/{buildConfig}"
            else:
                linkPath = f"{targetDepsDir}/{dep}"
            print(f"Link {dep} to {linkPath}")
            packmanapi.link(linkPath, info["local_path"])

    print(f"Install usd-exchange to {installDir}")
    mapping = omni.repo.man.get_platform_file_mapping(platform)
    mapping["config"] = buildConfig
    mapping["root"] = tokens["root"]
    mapping["install_dir"] = installDir
    os_name, arch = omni.repo.man.get_platform_os_and_arch(platform)
    filters = [platform, buildConfig, os_name, arch]

    python_path = f"{targetDepsDir}/python"
    usd_path = f"{targetDepsDir}/usd/{buildConfig}"
    tbb_path = f"{targetDepsDir}/tbb/{buildConfig}"
    materialx_path = f"{targetDepsDir}/materialx/{buildConfig}"

    # Acquire the asset validator from PyPI. It is a pure-python wheel, so a single install into the staging dir
    # provides the module that is assembled into the install tree below (covers both in-repo and standalone installs).
    validator_path = f"{targetDepsDir}/usd-validation-nvidia"
    if installTestModules and python_ver != "0":
        # the packman python package exposes the canonical `python${exe_ext}` entry point
        pythonExecutable = os.path.join(python_path, "python" + mapping["exe_ext"])
        # a non-empty (and resolved) token means the package may come from that index rather than PyPI
        extraIndex = uv_extra_index_url if (uv_extra_index_url and not uv_extra_index_url.startswith("${")) else None
        source = f"PyPI or {extraIndex}" if extraIndex else "PyPI"
        print(f"Install usd-validation-nvidia=={usd_validation_version} from {source} to {validator_path}")
        # `uv pip install` is uv's own native installer (it does not shell out to pip); resolve the vendored uv
        # binary via get_uv() exactly as repo_man does internally (see omni.repo.man.deps._uv_requirements_load).
        # `--no-deps` keeps OpenUSD (which we already bundle) out of the validator's staging directory.
        uvInstall = [
            str(omni.repo.man.get_uv()),
            "pip",
            "install",
            "--no-config",
            "--no-deps",
            f"--python={pythonExecutable}",
            f"--target={validator_path}",
        ]
        if extraIndex:
            uvInstall += ["--extra-index-url", extraIndex]
        uvInstall.append(f"usd-validation-nvidia=={usd_validation_version}")
        omni.repo.man.run_process(uvInstall, exit_on_error=True)

    runtimeInstallDir = "${install_dir}/bin" if os.name == "nt" else "${install_dir}/lib"
    libInstallDir = runtimeInstallDir
    usdNativePluginSourceDir = f"{usd_path}/lib/usd"
    usdPluginSourceDir = f"{usd_path}/plugin/usd"
    usdPluginInstallDir = f"{runtimeInstallDir}/usd"
    usdexLibSourceDir = f"{usd_exchange_path}/bin" if os.name == "nt" else f"{usd_exchange_path}/lib"

    prebuild_dict = {
        "copy": [
            [usdexLibSourceDir + "/${lib_prefix}usdex_core${lib_ext}", libInstallDir],
        ],
    }

    if installRtxModules:
        prebuild_dict["copy"].append([usdexLibSourceDir + "/${lib_prefix}usdex_rtx${lib_ext}", libInstallDir])

    # usd
    usdLibMidfix, monolithic = __computeUsdMidfix(usd_path)
    # plugins usdex links against; identical for monolithic & modular, only the backing libraries differ (usd_ms vs per-module)
    usdPlugins = [
        "ar",
        "sdf",
        "sdr",
        "usd",
        "usdGeom",
        "usdLux",
        "usdPhysics",
        "usdShade",
        "usdShaders",
        "usdUI",
    ]
    if monolithic:
        usdLibs = ["usd_ms"]
        usdPluginLibs = []
    else:
        usdLibs = [
            "ar",
            "arch",
            "gf",
            "js",
            "kind",
            "pcp",
            "plug",
            "sdf",
            "sdr",
            "tf",
            "trace",
            "ts",
            "usd",
            "usdGeom",
            "usdLux",
            "usdPhysics",
            "usdShade",
            "usdUtils",
            "usdUI",
            "vt",
            "work",
        ]
        usdPluginLibs = [
            "usdShaders",
        ]

    if __SemVersion(usd_ver) < __SemVersion("25.08"):
        usdPlugins.append("ndr")
        if not monolithic:
            usdLibs.append("ndr")

    # schemas we ship for downstream authoring but do not link ourselves
    shippedSchemas = [
        "usdMedia",
        "usdMtlx",
        "usdProc",
        "usdRender",
        "usdSemantics",
        "usdSkel",
        "usdVol",
    ]
    if __SemVersion(usd_ver) >= __SemVersion("26.08"):
        shippedSchemas += ["usdLod", "usdProfiles"]
    usdPlugins += shippedSchemas
    if not monolithic:
        usdLibs += shippedSchemas

    # native OpenUSD validators loaded by usd_validation_nvidia's adapters
    validators = []
    if installTestModules and python_ver != "0":
        validators = [
            "usdValidation",
            "usdGeomValidators",
            "usdPhysicsValidators",
            "usdShadeValidators",
            "usdSkelValidators",
            "usdUtilsValidators",
        ]
        if __SemVersion(usd_ver) >= __SemVersion("26.08"):
            validators.append("usdLuxValidators")
        usdPlugins += validators
        if not monolithic:
            usdLibs += validators

    # allow for extra user supplied plugins
    for extra in extraPlugins:
        extraLibExists = os.path.exists(omni.repo.man.resolve_tokens(usd_path + "/lib/${lib_prefix}" + usdLibMidfix + extra + "${lib_ext}"))
        extraPluginExists = os.path.exists(f"{usdNativePluginSourceDir}/{extra}")
        if not extraLibExists and not extraPluginExists:
            print(f"Warning: Skipping {extra} as neither the plugInfo nor the library exist in this USD flavor")
            continue
        if extraLibExists and extra not in usdLibs:
            usdLibs.append(extra)
        if extraPluginExists and extra not in usdPlugins:
            usdPlugins.append(extra)

    for lib in usdLibs:
        prebuild_dict["copy"].append([usd_path + "/lib/${lib_prefix}" + usdLibMidfix + lib + "${lib_ext}", libInstallDir])
    prebuild_dict["copy"].append([f"{usdNativePluginSourceDir}/plugInfo.json", f"{usdPluginInstallDir}/plugInfo.json"])
    for plugin in usdPlugins:
        if os.path.exists(f"{usdNativePluginSourceDir}/{plugin}"):
            prebuild_dict["copy"].append([f"{usdNativePluginSourceDir}/{plugin}", f"{usdPluginInstallDir}/{plugin}"])
        elif os.path.exists(f"{usdPluginSourceDir}/{plugin}"):
            prebuild_dict["copy"].append([f"{usdPluginSourceDir}/{plugin}", f"{usdPluginInstallDir}/{plugin}"])
        else:
            raise omni.repo.man.exceptions.ConfigurationError(f"Plugin {plugin} not found in {usdNativePluginSourceDir} or {usdPluginSourceDir}")
    for lib in usdPluginLibs:
        prebuild_dict["copy"].append([f"{usdPluginSourceDir}/{lib}" + "${lib_ext}", usdPluginInstallDir])

    # tbb comes from the standalone oneTBB package on every supported flavor; the lib name differs only by config
    # (debug suffix) and platform (linux libtbb.so*, windows tbb12.dll)
    if buildConfig == "debug":
        prebuild_dict["copy"].extend(
            [
                [tbb_path + "/lib/${lib_prefix}" + "tbb_debug" + "${lib_ext}*", libInstallDir],
                [tbb_path + "/bin/${lib_prefix}" + "tbb12_debug" + "${lib_ext}*", libInstallDir],  # windows
            ]
        )
    else:
        prebuild_dict["copy"].extend(
            [
                [tbb_path + "/lib/${lib_prefix}" + "tbb" + "${lib_ext}*", libInstallDir],
                [tbb_path + "/bin/${lib_prefix}" + "tbb12" + "${lib_ext}*", libInstallDir],  # windows
            ]
        )

    # usdMtlx is a mandatory shipped schema, so its MaterialX libraries from the standalone MaterialX package always ship too
    mtlxLibraryDir = f"{libInstallDir}/usd/usdMtlx/resources/libraries"
    prebuild_dict["copy"].extend(
        [
            [materialx_path + "/lib/${lib_prefix}MaterialXFormat*${lib_ext}*", libInstallDir],
            [materialx_path + "/lib/${lib_prefix}MaterialXCore*${lib_ext}*", libInstallDir],
            [materialx_path + "/bin/${lib_prefix}MaterialXFormat*${lib_ext}*", libInstallDir],  # windows
            [materialx_path + "/bin/${lib_prefix}MaterialXCore*${lib_ext}*", libInstallDir],  # windows
            [f"{materialx_path}/libraries/bxdf/*open_pbr_surface.mtlx", f"{mtlxLibraryDir}/bxdf/"],
            [f"{materialx_path}/libraries/stdlib/stdlib_defs.mtlx", f"{mtlxLibraryDir}/stdlib/stdlib_defs.mtlx"],
            [f"{materialx_path}/libraries/stdlib/stdlib_ng.mtlx", f"{mtlxLibraryDir}/stdlib/stdlib_ng.mtlx"],
        ]
    )

    if python_ver != "0":
        # usdex core only
        __installPythonModule(prebuild_dict["copy"], f"{usd_exchange_path}/python", "usdex/core", "_usdex_core")
        if installRtxModules:
            __installPythonModule(prebuild_dict["copy"], f"{usd_exchange_path}/python", "usdex/rtx", "_usdex_rtx")
        # usd dependencies
        if monolithic:
            pass  # monolithic builds with python support already have the python bindings embedded
        else:
            prebuild_dict["copy"].append([usd_path + "/lib/${lib_prefix}" + usdLibMidfix + "python${lib_ext}", libInstallDir])
        if installPythonLibs:
            prebuild_dict["copy"].extend(
                [
                    [python_path + "/lib/${lib_prefix}*python*${lib_ext}*", libInstallDir],
                    [python_path + "/${lib_prefix}*python*${lib_ext}*", libInstallDir],  # windows
                ]
            )
        # minimal selection of usd modules
        usdModules = [
            ("pxr/Ar", "_ar"),
            ("pxr/Gf", "_gf"),
            ("pxr/Kind", "_kind"),
            ("pxr/Ndr", "_ndr"),
            ("pxr/Pcp", "_pcp"),
            ("pxr/Plug", "_plug"),
            ("pxr/Sdf", "_sdf"),
            ("pxr/Sdr", "_sdr"),
            ("pxr/Tf", "_tf"),
            ("pxr/Trace", "_trace"),
            ("pxr/Ts", "_ts"),
            ("pxr/Usd", "_usd"),
            ("pxr/UsdGeom", "_usdGeom"),
            ("pxr/UsdLux", "_usdLux"),
            ("pxr/UsdPhysics", "_usdPhysics"),
            ("pxr/UsdShade", "_usdShade"),
            ("pxr/UsdUI", "_usdUI"),
            ("pxr/UsdUtils", "_usdUtils"),
            ("pxr/Vt", "_vt"),
            ("pxr/Work", "_work"),
        ]
        # python modules for the shipped schemas
        shippedSchemaModules = [
            ("pxr/UsdMedia", "_usdMedia"),
            ("pxr/UsdMtlx", "_usdMtlx"),
            ("pxr/UsdProc", "_usdProc"),
            ("pxr/UsdRender", "_usdRender"),
            ("pxr/UsdSemantics", "_usdSemantics"),
            ("pxr/UsdSkel", "_usdSkel"),
            ("pxr/UsdVol", "_usdVol"),
        ]
        if __SemVersion(usd_ver) >= __SemVersion("26.08"):
            shippedSchemaModules += [
                ("pxr/UsdLod", "_usdLod"),
                ("pxr/UsdProfiles", "_usdProfiles"),
            ]
        usdModules += shippedSchemaModules

        # usdex.test
        if installTestModules:
            __installPythonModule(prebuild_dict["copy"], f"{usd_exchange_path}/python", "usdex/test", None)
            # usd_validation_nvidia is pip-installed above; copy the whole package (the capabilities submodule comes along)
            prebuild_dict["copy"].append([f"{validator_path}/usd_validation_nvidia", "${install_dir}/python/usd_validation_nvidia"])
            # pxr.UsdValidation is the native framework usd_validation_nvidia's adapters load
            usdModules.append(("pxr/UsdValidation", "_usdValidation"))

        # allow for extra user supplied plugins
        for extra in extraPlugins:
            if not any([f"_{extra}" == x[1] for x in usdModules]):
                extraPascalCase = f"{extra[0].upper()}{extra[1:]}"
                if os.path.exists(f"{usd_path}/lib/python/pxr/{extraPascalCase}"):
                    usdModules.append((f"pxr/{extraPascalCase}", f"_{extra}"))

        for moduleNamespace, libPrefix in usdModules:
            __installPythonModule(prebuild_dict["copy"], f"{usd_path}/lib/python", moduleNamespace, libPrefix)

    omni.repo.man.fileutils.ERROR_IF_NOT_EXIST = True
    omni.repo.man.fileutils.copy_and_link_using_dict(prebuild_dict, filters, mapping)


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    toolConfig = config.get("repo_install_usdex", {})
    if not toolConfig.get("enabled", True):
        return None

    installDir = toolConfig["install_dir"]
    stagingDir = toolConfig["staging_dir"]
    usd_flavor = toolConfig["usd_flavor"]
    usd_ver = toolConfig["usd_ver"]
    python_ver = toolConfig["python_ver"]
    usd_validation_version = toolConfig["usd_validation_version"]
    repoVersionFile = config["repo"]["folders"]["version_file"]

    parser.description = "Tool to download and install precompiled OpenUSD Exchange binaries and all of its runtime dependencies."
    parser.add_argument(
        "--version",
        dest="version",
        help="The exact version of OpenUSD Exchange to install. Overrides any specified packman dependency. "
        "If this arg is not specified, and no packman dependency exists, then repo_build_number will be used to determine the current version. "
        "Note this last fallback assumes source code and git history are available. If they are not, the install will fail.",
    )
    parser.add_argument(
        "-s",
        "--staging-dir",
        dest="staging_dir",
        help=f"Required compile, link, and runtime dependencies will be downloaded & linked this folder. Defaults to `{stagingDir}`",
    )
    parser.add_argument(
        "-i",
        "--install-dir",
        dest="install_dir",
        help=f"Required runtime files will be assembled into this folder. Defaults to `{installDir}`",
    )
    parser.add_argument(
        "--use-existing-build",
        action="store_true",
        dest="use_existing_build",
        help="Enable this to use an existing build of OpenUSD Exchange rather than download a package. "
        "The OpenUSD Exchange distro must already exist in the --install-dir or the process will fail.",
        default=False,
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        dest="clean",
        help="Clean the install directory and staging directory and exit.",
        default=False,
    )
    omni.repo.man.add_config_arg(parser)
    parser.add_argument(
        "--usd-flavor",
        dest="usd_flavor",
        choices=["usd", "usd-minimal"],  # public flavors only
        help=f"""
        The OpenUSD flavor to install. 'usd' means stock pxr builds, while 'usd-minimal' excludes many plugins, excludes python bindings, and
        is a monolithic build with just one usd_ms library. Defaults to `{usd_flavor}`
        """,
    )
    parser.add_argument(
        "--usd-version",
        dest="usd_ver",
        default=usd_ver,
        choices=["26.08", "25.11", "25.05"],  # public versions only
        help=f"The OpenUSD version to install. Defaults to `{usd_ver}`",
    )
    parser.add_argument(
        "--python-version",
        dest="python_ver",
        choices=["3.13", "3.12", "3.11", "3.10", "0"],
        help=f"The Python flavor to install. Use `0` to disable Python features. Defaults to `{python_ver}`",
    )
    parser.add_argument(
        "--install-python-libs",
        action="store_true",
        dest="install_python_libs",
        default=False,
        help="""
        Enable to install libpython3.so / python3.dll.
        This should not be used if you are providing your own python runtime.
        This has no effect if --python-version=0
        """,
    )
    parser.add_argument(
        "--install-rtx",
        action="store_true",
        dest="install_rtx_modules",
        default=False,
        help="""
        Enable to install `usdex.rtx` shared library and python module.
        """,
    )
    parser.add_argument(
        "--install-test",
        action="store_true",
        dest="install_test_modules",
        default=False,
        help="""
        Enable to install `usdex.test` python unittest module and its dependencies.
        This has no effect if --python-version=0
        """,
    )
    parser.add_argument(
        "--usd-validation-version",
        dest="usd_validation_version",
        help=f"The version of the usd-validation-nvidia PyPI package to install with --install-test. Defaults to `{usd_validation_version}`",
    )
    parser.add_argument(
        "--install-extra-plugins",
        dest="install_extra_plugins",
        nargs="+",
        type=str,
        default=[],
        help="""
        List additional OpenUSD plugins by name (e.g. 'usdMedia') to install the necessary plugInfo.json and associated schema,
        libraries, and python modules.
        If unspecified, only the strictly required OpenUSD plugins will be installed.
        Python modules will be skipped if --python-version=0
        """,
    )

    def run_repo_tool(options: Dict, config: Dict):
        toolConfig = config["repo_install_usdex"]
        stagingDir = options.staging_dir or toolConfig["staging_dir"]
        installDir = options.install_dir or toolConfig["install_dir"]
        useExistingBuild = options.use_existing_build or toolConfig["use_existing_build"]
        usd_flavor = options.usd_flavor or toolConfig["usd_flavor"]
        usd_ver = options.usd_ver or toolConfig["usd_ver"]
        python_ver = options.python_ver or toolConfig["python_ver"]
        usd_validation_version = options.usd_validation_version or toolConfig["usd_validation_version"]
        # optional index for wheel dependencies; empty by default means PyPI only
        uv_extra_index_url = omni.repo.man.resolve_tokens("${uv_extra_index_url}")

        if usd_flavor == "usd-minimal":
            if python_ver != "0":
                print(f"usd-minimal flavors explicitly exclude python. Overriding '{python_ver}' to '0'")
            python_ver = "0"

        __install(
            installDir,
            useExistingBuild,
            stagingDir,
            usd_flavor,
            usd_ver,
            python_ver,
            usd_validation_version,
            uv_extra_index_url,
            repoVersionFile,
            options.config,
            options.clean,
            options.version,
            options.install_python_libs,
            options.install_rtx_modules,
            options.install_test_modules,
            options.install_extra_plugins,
        )

    return run_repo_tool
