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

    def testMissingUsdConvertersDuringImport(self):
        # Load the native module in a fresh interpreter without importing pxr.Gf.
        # This exercises the same missing converter as a foreign USD runtime,
        # without requiring a second, unsupported USD installation in the test.
        script = """
import importlib.util
import os
import sys

# Python 3.8+ needs explicit DLL directories on Windows, including wheel libs.
dll_dirs = []
if hasattr(os, "add_dll_directory"):
    for path in sys.argv[2:]:
        if os.path.isdir(path):
            dll_dirs.append(os.add_dll_directory(path))
spec = importlib.util.spec_from_file_location("_usdex_core", sys.argv[1])
try:
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
except ImportError as error:
    assert isinstance(error.__cause__, TypeError), repr(error)
    assert "No to_python" in str(error.__cause__), repr(error.__cause__)
    assert "GfVec3f" in str(error.__cause__), repr(error.__cause__)
else:
    raise AssertionError("Import unexpectedly succeeded without USD converters")
# The interpreter must remain usable after the failed extension initialization.
assert sum(range(10)) == 45
"""
        modulePath = pathlib.Path(usdex.core._usdex_core.__file__).resolve()
        pythonRoot = modulePath.parents[2]
        dllDirs = [pythonRoot.parent / "bin", pythonRoot / "usd_exchange.libs"]
        dllDirs.extend(pathlib.Path(p) for p in os.environ.get("PATH", "").split(os.pathsep) if p)
        result = subprocess.run([sys.executable, "-c", script, str(modulePath), *map(str, dllDirs)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
        # usd-exchange is what the environment should keep, so it must not be the one named for removal
        self.assertNotIn("pip uninstall usd-exchange", result.stderr)

    def testWarnsWhenTheWheelIsInstalledOverAnExistingOpenUsd(self):
        # a package manager that supplies `pxr` reserves the `usd-core` name without installing it (conda's `openusd`
        # does this), so the wheel that brought its own modules is what has to be removed
        with tempfile.TemporaryDirectory() as tempDir:
            self.writeDistInfo(tempDir, "usd-core", installedUsdModules=False)
            self.writeDistInfo(tempDir, "usd-exchange", installedUsdModules=True)
            result = self.importUsdexCore(tempDir)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usd-core 25.5", result.stderr)
        self.assertIn("pip uninstall usd-exchange", result.stderr)
        # uninstalling the reservation would remove no modules & leave the conflict in place
        self.assertNotIn("pip uninstall usd-core", result.stderr)

    def testSilentWhenNeitherDistributionInstalledUsd(self):
        # `pxr` comes from another package manager & this `usd-exchange` links it rather than bundling one
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
