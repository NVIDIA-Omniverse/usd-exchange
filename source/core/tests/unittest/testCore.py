# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import importlib.metadata
import os
import pathlib
import sys
import unittest

import usdex.core


def get_changelog_version_string():
    """Get the version string from the CHANGELOG.md"""
    changes = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "CHANGELOG.md")
    with open(changes, "r") as f:
        version = f.readline().strip("# \n")
    return version


def get_package_metadata_directory(package_name: str):
    try:
        package_files = importlib.metadata.files(package_name)
        if package_files is None:
            return None
        for file in package_files:
            if file.name == "METADATA":
                metadata_file_path = file.locate()
                return metadata_file_path.parent
    except importlib.metadata.PackageNotFoundError:
        return None


def is_running_on_ci():
    return os.environ.get("GITLAB_CI") is not None


def in_virtual_environment():
    return hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix


class CoreTest(unittest.TestCase):

    def testVersion(self):
        version = get_changelog_version_string()
        self.assertEqual(usdex.core.version(), version)

    def testBuildVersion(self):
        version = get_changelog_version_string()
        self.assertEqual(usdex.core.buildVersion().split("+")[0], version)

    def testModuleSymbols(self):
        allowList = [
            "os",  # module necessary to locate bindings on windows
            "_usdex_core",  # our binding module
            "_AssetStructureBindings",  # hand rolled binding
            "_StageAlgoBindings",  # hand rolled binding
        ]
        allowList.extend([x for x in dir(usdex.core) if x.startswith("__")])  # private members

        for attr in dir(usdex.core):
            if attr in allowList:
                continue
            self.assertIn(attr, usdex.core.__all__)

        for attr in usdex.core.__all__:
            self.assertIn(attr, dir(usdex.core))

    @unittest.skipUnless(in_virtual_environment() or is_running_on_ci(), "Not running in CI or virtual environment; skipping license test.")
    def testRedistLicenses(self):
        if in_virtual_environment():
            expectedLicenses = [
                "usd-exchange-LICENSE.md",
                "boost-LICENSE*.txt",
                "pybind11-LICENSE.txt",
                "pyboost11-LICENSE.txt",
                "usd-license.txt",
                "*tbb-LICENSE*",
                "zlib-LICENSE",
            ]
            packageInfoDir = get_package_metadata_directory("usd-exchange")
            self.assertIsNotNone(packageInfoDir, "usd-exchange package is not installed.")
            licenseDir = pathlib.Path(packageInfoDir) / "licenses"
        elif is_running_on_ci():
            expectedLicenses = [
                "cortex-LICENSE.txt",
                "cxxopts-LICENSE.txt",
                "doctest-LICENSE.txt",
                "gaffer-LICENSE.txt",
                "pybind11-LICENSE.txt",
                "pybind11-stubgen-LICENSE.txt",
                "pyboost11-LICENSE.txt",
                "usd-exchange-LICENSE.md",
            ]
            import omni.repo.man

            test_root = omni.repo.man.resolve_tokens("$test_root")
            licenseDir = pathlib.Path(test_root) / "PACKAGE-LICENSES"
        else:
            self.skipTest("Not running in CI or virtual environment; skipping license test.")

        self.assertTrue(licenseDir.exists(), f"Licenses directory does not exist at {licenseDir.as_posix()}")

        for licensePattern in expectedLicenses:
            matchingFiles = list(licenseDir.glob(licensePattern))
            self.assertEqual(len(matchingFiles), 1, f"License file matching pattern '{licensePattern}' not found in {licenseDir.as_posix()}")
