# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import argparse
import datetime
import os
from typing import Callable, Dict

import omni.repo.man


def replace_file(filename, new_file_contents):
    try:
        with open(filename, "r+") as f:
            old_file_contents = f.read()
            if old_file_contents != new_file_contents:
                # only write if different otherwise this will force a rebuild every time
                f.seek(0)
                f.write(new_file_contents)
                f.truncate()
    except IOError:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(new_file_contents)


def generate_version_h(macro_namespace, target_file, major, minor, patch, version, package_version, license_preamble, license_text):
    license_preamble = "\n".join([f"// {x}" for x in license_preamble.strip("\n").split("\n")])
    license_text = "\n".join([f"// {x}" for x in license_text.strip("\n").split("\n")])
    new_file_contents = f"""{license_preamble}
//
{license_text}

#pragma once

//! @file {target_file.split("include/")[-1]}
//! @brief Version macros for this library
//! Automatically generated file

//! Major version number. This will not change unless there is a major non-backwards compatible change.
#define {macro_namespace}_VERSION_MAJOR {major}

//! Minor version number. This changes with every release.
#define {macro_namespace}_VERSION_MINOR {minor}

//! Patch number. This will normally be 0, but can change if a fix is back-ported to a previous release.
#define {macro_namespace}_VERSION_PATCH {patch}

//! This is the full version string
#define {macro_namespace}_VERSION_STRING "{version}"

//! This is the full build string
#define {macro_namespace}_BUILD_STRING "{package_version}"
"""
    replace_file(target_file, new_file_contents)


def generate_versioninfo_resource(target_resource_file, target_file, company, product, macro_namespace, license_premble):
    relative_target_resource_file = os.path.join(".", target_resource_file)
    relative_target_file = os.path.join(
        os.path.relpath(
            os.path.realpath(os.path.join(".", os.path.dirname(target_file))),
            os.path.realpath(os.path.dirname(relative_target_resource_file)),
        ),
        os.path.basename(target_file),
    )
    legal_copyright = license_premble.split("\n")[0].partition("SPDX-FileCopyrightText:")[-1].strip()
    new_file_contents = f"""//
#include <winver.h>
#include <ntdef.h>

#include "{relative_target_file}"

#ifdef RC_INVOKED

// ------- version info -------------------------------------------------------

VS_VERSION_INFO VERSIONINFO
FILEVERSION             {macro_namespace}_VERSION_MAJOR,{macro_namespace}_VERSION_MINOR,{macro_namespace}_VERSION_PATCH
PRODUCTVERSION          {macro_namespace}_VERSION_MAJOR,{macro_namespace}_VERSION_MINOR,{macro_namespace}_VERSION_PATCH
BEGIN
    BLOCK "StringFileInfo"
    BEGIN
        BLOCK "040904b0"
        BEGIN
        VALUE "CompanyName",      "{company}"
        VALUE "ProductName",      "{company} {product}"
        VALUE "FileDescription",  "{company} {product}"
        VALUE "FileVersion",      {macro_namespace}_BUILD_STRING
        VALUE "ProductVersion",   {macro_namespace}_BUILD_STRING
        VALUE "LegalCopyright",   "{legal_copyright}"
        END
    END
    BLOCK "VarFileInfo"
    BEGIN
        VALUE "Translation", 0x0409,1200
    END
END
#endif
"""
    replace_file(relative_target_resource_file, new_file_contents)


def setup_repo_tool(parser: argparse.ArgumentParser, config: Dict) -> Callable:
    parser.description = """
        Tool to generate and install Version.h (and optionally version.rc) with automated substitutions based on repo_build_number.
    """
    parser.add_argument(
        "-t",
        "--targetFile",
        dest="target_version_header_file",
        help="Path to generate the target Version.h file",
    )
    parser.add_argument(
        "-rc",
        "--targetResourceFile",
        dest="target_resource_file",
        help="Path to generate the target versioninfo resource file."
        "See https://learn.microsoft.com/en-us/windows/win32/menurc/versioninfo-resource for details",
    )

    tool_config = config.get("repo_version_header", {})
    if not tool_config.get("enabled", True):
        return None

    def run_repo_tool(options: Dict, config: Dict):
        omni.repo.man.logger.warning(
            "repo_version_header is deprecated. The OpenUSD Exchange SDK CMake build now generates Version.h and "
            "version.rc directly (see CMakeLists.txt + cmake/Version.h.in / cmake/version.rc.in); prefer building with "
            "CMake if you can. This tool remains for the docs pipeline and legacy (non-CMake) consumers."
        )
        package_version = omni.repo.man.build_number.generate_build_number_from_file(config["repo"]["folders"]["version_file"])

        target_version_header_file = options.target_version_header_file or config["repo_version_header"]["target_version_header_file"]
        target_resource_file = options.target_resource_file or config["repo_version_header"]["target_resource_file"]
        generate_version_stub_file = config["repo_version_header"]["generate_version_stub_file"]
        company = config["repo_version_header"]["company"]
        product = config["repo_version_header"]["product"]
        macro_namespace = config["repo_version_header"]["macro_namespace"]
        current_year = str(datetime.date.today().year)
        copyright_start = config.get("repo_docs", {}).get("copyright_start", current_year)
        years = current_year if copyright_start == current_year else f"{copyright_start}-{current_year}"
        license_preamble = config["repo_version_header"]["license_preamble"].replace("{years}", years)
        license_text = config["repo_version_header"]["license_text"]

        version = package_version.split("+")[0]
        semantic_version = version.split("-")[0]
        tokens = semantic_version.split(".")
        if len(tokens) == 3:
            (major, minor, patch) = tokens
        elif len(tokens) == 2:
            (major, minor) = tokens
            patch = "0"
        else:
            raise RuntimeError(f"Invalid version specification: {tokens}. repo_version_header requires at major.minor or major.minor.patch syntax")

        if not macro_namespace:
            raise RuntimeError(f"No specified macro namespace. repo_version_header requires a value to ensure defined variables are unique")

        generate_version_h(macro_namespace, target_version_header_file, major, minor, patch, version, package_version, license_preamble, license_text)

        if generate_version_stub_file:
            # this is only necessary because repo_docs doesn't respect repo.folders.version_file
            with open("VERSION", "w") as f:
                f.write(version)

        if target_resource_file:
            generate_versioninfo_resource(
                target_resource_file,
                target_version_header_file,
                company,
                product,
                macro_namespace,
                license_preamble,
            )

    return run_repo_tool
