# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib.metadata
import os
import pathlib
import subprocess
import sys
import tempfile
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
                "materialx-LICENSE.txt",
                "onetbb-LICENSE.txt",
                "openusd-LICENSE.txt",
                "pybind11-LICENSE.txt",
                "pyboost11-LICENSE.txt",
                "usd-exchange-LICENSE.md",
            ]
            packageInfoDir = get_package_metadata_directory("usd-exchange")
            self.assertIsNotNone(packageInfoDir, "usd-exchange package is not installed.")
            licenseDir = pathlib.Path(packageInfoDir) / "licenses"
        elif is_running_on_ci():
            # the packages also ship our vendored copy of pybind11-stubgen in dev/tools
            expectedLicenses = [
                "materialx-LICENSE.txt",
                "onetbb-LICENSE.txt",
                "openusd-LICENSE.txt",
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

        foundLicenses = {x.name for x in licenseDir.iterdir() if x.is_file()}
        self.assertEqual(foundLicenses, set(expectedLicenses), f"Notices in {licenseDir.as_posix()} do not match what we redistribute")

    @unittest.skipUnless(in_virtual_environment(), "Not running from an installed wheel; skipping project description test.")
    def testProjectDescription(self):
        # The `pxr` install path collision with `usd-core` cannot be declared in wheel metadata, so the project description must state it.
        metadata = importlib.metadata.metadata("usd-exchange")
        description = metadata.get_payload() or metadata.get("Description", "")
        self.assertIn("usd-core", description)
        self.assertIn("pip install --force-reinstall usd-exchange", description)


class UsdCoreConflictTest(unittest.TestCase):
    """Verify the import time diagnostic for a second OpenUSD installed alongside `usd-exchange`"""

    def importUsdexCore(self, metadataDir: str = None):
        # A fresh process is required because usdex.core is already imported here, and the check only runs at import.
        env = os.environ.copy()
        if metadataDir:
            env["PYTHONPATH"] = os.pathsep.join([metadataDir, env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        return subprocess.run([sys.executable, "-c", "import usdex.core"], capture_output=True, text=True, env=env)

    def writeDistInfo(self, metadataDir: str, name: str, installedUsdModules: bool):
        # Only the distribution metadata is synthesized, so the `pxr` modules of this environment are left intact.
        # It precedes the real metadata on PYTHONPATH, so these tests describe the environment rather than observing it.
        distInfo = pathlib.Path(metadataDir) / f"{name.replace('-', '_')}-25.5.dist-info"
        distInfo.mkdir()
        (distInfo / "METADATA").write_text(f"Metadata-Version: 2.1\nName: {name}\nVersion: 25.5\n")
        if installedUsdModules:
            # a wheel's RECORD lists what it installed; the hash & size columns are unused here
            (distInfo / "RECORD").write_text("pxr/__init__.py,,\npxr/Usd/__init__.py,,\n")

    def testWarnsWhenBothWheelsInstallUsd(self):
        with tempfile.TemporaryDirectory() as tempDir:
            self.writeDistInfo(tempDir, "usd-core", installedUsdModules=True)
            self.writeDistInfo(tempDir, "usd-exchange", installedUsdModules=True)
            result = self.importUsdexCore(tempDir)

        self.assertEqual(result.returncode, 0, result.stderr)
        # assert the detected distribution & the repair advice, rather than the full wording of the warning
        self.assertIn("usd-core 25.5", result.stderr)
        self.assertIn("pip uninstall usd-core", result.stderr)

    def testWarnsWhenTheWheelIsInstalledOverACondaOpenUsd(self):
        # conda's `openusd` reserves the `usd-core` name without installing `pxr`, but the wheel brings its own
        with tempfile.TemporaryDirectory() as tempDir:
            self.writeDistInfo(tempDir, "usd-core", installedUsdModules=False)
            self.writeDistInfo(tempDir, "usd-exchange", installedUsdModules=True)
            result = self.importUsdexCore(tempDir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usd-core 25.5", result.stderr)

    def testSilentWhenNeitherDistributionInstalledUsd(self):
        # the conda arrangement: `openusd` supplies `pxr` & this `usd-exchange` links it
        with tempfile.TemporaryDirectory() as tempDir:
            self.writeDistInfo(tempDir, "usd-core", installedUsdModules=False)
            self.writeDistInfo(tempDir, "usd-exchange", installedUsdModules=False)
            result = self.importUsdexCore(tempDir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("usd-core", result.stderr)

    def testSilentWithoutUsdCore(self):
        result = self.importUsdexCore()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("usd-core", result.stderr)
