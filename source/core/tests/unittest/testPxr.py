# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib.metadata
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


class PxrTest(unittest.TestCase):

    def _getWheelDllRoot(self):
        pxr_spec = importlib.util.find_spec("pxr")
        if pxr_spec is None or pxr_spec.origin is None:
            return None
        dll_root = os.path.abspath(os.path.join(os.path.dirname(pxr_spec.origin), "../usd_exchange.libs"))
        return dll_root if os.path.isdir(dll_root) else None

    def _removePathEntry(self, path_value, excluded_path):
        excluded_path = os.path.normcase(os.path.realpath(excluded_path))
        filtered_paths = []
        for path in path_value.split(os.pathsep):
            if os.path.normcase(os.path.realpath(path)) != excluded_path:
                filtered_paths.append(path)
        return os.pathsep.join(filtered_paths)

    @unittest.skipUnless(sys.platform == "win32", "Windows DLL search test")
    def testPxrDllPathPreservesFallbacks(self):
        """Verify the complete environment-variable contract for the generated wheel initializer.

        The wheel path must appear first and exactly once. Caller paths must retain their order.
        Unset and empty values must not produce empty entries. Reloading ``pxr`` must not add duplicates.
        The existing ``PATH`` prepend must also remain duplicate-free. Both usdex modules must import successfully.
        """
        wheel_dll_root = self._getWheelDllRoot()
        if wheel_dll_root is None:
            self.skipTest("Test requires the installed wheel")

        package_version = importlib.metadata.version("usd-exchange")
        expected_version = package_version.partition("+")[0]

        script = """
import importlib
import json
import os
import pxr
import usdex.core
import usdex.rtx

# Exercise the generated initializer twice to verify that both environment variables remain duplicate-free.
importlib.reload(pxr)
dll_path = os.path.abspath(os.path.join(os.path.dirname(pxr.__file__), "../usd_exchange.libs"))
print(json.dumps({
    "dll_path": dll_path,
    "dll_paths": os.environ["PXR_USD_WINDOWS_DLL_PATH"].split(os.pathsep),
    "path_entries": os.environ["PATH"].split(os.pathsep),
    "version": usdex.core.version(),
}))
"""
        cases = {
            "unset": None,
            "empty": [],
            "multiple": [r"C:\caller\first", r"D:\caller\second", r"E:\caller\third"],
        }
        for name, fallback_paths in cases.items():
            with self.subTest(name=name):
                env = os.environ.copy()
                if fallback_paths is None:
                    env.pop("PXR_USD_WINDOWS_DLL_PATH", None)
                    expected_fallbacks = []
                else:
                    env["PXR_USD_WINDOWS_DLL_PATH"] = os.pathsep.join(fallback_paths)
                    expected_fallbacks = fallback_paths
                # Remove the wheel path so the first import must prepend it to PATH.
                env["PATH"] = self._removePathEntry(env.get("PATH", ""), wheel_dll_root)
                result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                values = json.loads(result.stdout.splitlines()[-1])
                self.assertEqual(values["dll_paths"], [values["dll_path"], *expected_fallbacks])
                self.assertEqual(values["dll_paths"].count(values["dll_path"]), 1)
                normalized_dll_path = os.path.normcase(os.path.realpath(values["dll_path"]))
                normalized_path_entries = []
                for path in values["path_entries"]:
                    normalized_path_entries.append(os.path.normcase(os.path.realpath(path)))
                self.assertEqual(normalized_path_entries[0], normalized_dll_path)
                self.assertEqual(normalized_path_entries.count(normalized_dll_path), 1)
                self.assertEqual(values["version"], expected_version)

    @unittest.skipUnless(sys.platform == "win32", "Windows DLL search test")
    def testPxrDllPathLoadsCallerDll(self):
        """Prove that OpenUSD loads a required DLL found only in a caller-supplied directory."""
        dll_root = self._getWheelDllRoot()
        if dll_root is None:
            self.skipTest("Test requires the installed wheel")
        pxr_root = os.path.abspath(os.path.join(dll_root, "../pxr"))

        with tempfile.TemporaryDirectory(dir=os.path.dirname(dll_root), prefix="_usdex_dll_test_") as staging_root:
            # Hard links create an isolated wheel layout without copying every large binary.
            staged_pxr_root = os.path.join(staging_root, "pxr")
            staged_dll_root = os.path.join(staging_root, "usd_exchange.libs")
            shutil.copytree(pxr_root, staged_pxr_root, copy_function=os.link)
            shutil.copytree(dll_root, staged_dll_root, copy_function=os.link)

            # Remove usd_tf.dll from the wheel directory and expose it only through the caller path.
            fallback_root = os.path.join(staging_root, "fallback")
            os.mkdir(fallback_root)
            staged_dll = os.path.join(staged_dll_root, "usd_tf.dll")
            fallback_dll = os.path.join(fallback_root, os.path.basename(staged_dll))
            self.assertTrue(os.path.isfile(staged_dll), f"Missing wheel DLL: {staged_dll}")
            shutil.move(staged_dll, fallback_dll)

            env = os.environ.copy()
            env["PXR_USD_WINDOWS_DLL_PATH"] = fallback_root
            env["PYTHONPATH"] = staging_root
            env["PATH"] = self._removePathEntry(env.get("PATH", ""), dll_root)
            result = subprocess.run(
                [sys.executable, "-c", "from pxr import Tf; assert hasattr(Tf, 'Status')"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def testPxrImport(self):
        # Guardrail: OpenUSD must import in a fresh process where usdex has not bootstrapped it. Run in a subprocess
        # (so usdex.core is not already imported) with a cleared PATH so we do not lean on a discoverable USD install.
        env = os.environ.copy()
        if env.get("PXR_USD_WINDOWS_DLL_PATH"):
            del env["PATH"]
        result = subprocess.run([sys.executable, "-c", "from pxr import Tf; assert hasattr(Tf, 'Status')"], capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, f"Failed to import pxr standalone: {result.stderr.decode()}")

    def testShippedSchemas(self):
        # the shipped schemas must be importable
        from pxr import Usd, UsdMedia, UsdMtlx, UsdProc, UsdRender, UsdSemantics, UsdSkel, UsdVol

        self.assertTrue(hasattr(UsdSemantics, "LabelsAPI"))
        self.assertTrue(hasattr(UsdVol, "Volume"))
        self.assertTrue(hasattr(UsdSkel, "Skeleton"))
        self.assertTrue(hasattr(UsdMedia, "SpatialAudio"))
        self.assertTrue(hasattr(UsdProc, "GenerativeProcedural"))
        self.assertTrue(hasattr(UsdRender, "Settings"))
        self.assertTrue(hasattr(UsdMtlx, "MaterialXConfigAPI"))

        if Usd.GetVersion()[:2] >= (26, 8):
            from pxr import UsdLod, UsdProfiles

            self.assertTrue(hasattr(UsdLod, "LevelOfDetail"))
            self.assertTrue(hasattr(UsdProfiles, "Profile"))

    def testValidatorPluginsImplemented(self):
        try:
            import usd_validation_nvidia
            from pxr import UsdValidation
        except ImportError:
            self.skipTest("usd_validation_nvidia / pxr.UsdValidation not available")
        self.assertTrue(hasattr(UsdValidation, "ValidationRegistry"))
        engine = usd_validation_nvidia.ValidationEngine(init_rules=True)
        adapters = [r for r in engine.rules if issubclass(r, usd_validation_nvidia.UsdValidatorAdapter)]
        self.assertTrue(adapters, "no UsdValidatorAdapter rules registered")
        self.assertTrue(all(r.is_implemented() for r in adapters))

    def testNativeValidatorsAdapted(self):
        try:
            import usd_validation_nvidia
            import usdex.test  # noqa: F401 imported for the rules it registers
            from pxr import Usd
            from usdex.test.ValidationRules import _nativeValidators
        except ImportError:
            self.skipTest("usd_validation_nvidia / pxr.UsdValidation not available")
        expected = {name for names in _nativeValidators.values() for name in names}
        if Usd.GetVersion()[:2] < (26, 8):
            # OpenUSD 26.08 added these two, the other six exist in every supported flavor
            expected -= {"usdShadeValidators:EncapsulationMaterialValidator", "usdValidation:AttributeTypeMismatch"}
        engine = usd_validation_nvidia.ValidationEngine(init_rules=True)
        registered = {r.validator_name() for r in engine.rules if issubclass(r, usd_validation_nvidia.UsdValidatorAdapter)}
        # an unregistered rule means its validator plugin was not loadable, which silently disables the checks
        self.assertFalse(expected - registered)
