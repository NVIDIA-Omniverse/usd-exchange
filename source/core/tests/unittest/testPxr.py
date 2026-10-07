# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import importlib.metadata
import importlib.util
import json
import os
import re
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
        An unset override falls back to ``PATH`` while an empty one excludes it.
        Unset and empty values must not produce empty entries. Reloading ``pxr`` must not add duplicates.
        The existing ``PATH`` prepend must also remain duplicate-free. Both usdex modules must import successfully.
        """
        wheel_dll_root = self._getWheelDllRoot()
        if wheel_dll_root is None:
            self.skipTest("Test requires the installed wheel")

        def normalize_version(version):
            # Accept both SemVer and PEP 440 forms for the SDK version and wheel metadata.
            return re.sub(r"-(a|b|rc)", r"\1", version).replace("-dev", ".dev0")

        package_version = importlib.metadata.version("usd-exchange")
        expected_version = normalize_version(package_version.partition("+")[0])

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
        first, second = r"C:\caller\first", r"D:\caller\second"
        overrides = [r"C:\caller\a", r"D:\caller\b", r"E:\caller\c"]
        # spellings that name the wheel directory: case, separators, trailing separator, and a dot component
        wheel_spellings = [
            wheel_dll_root.upper(),
            wheel_dll_root.replace("\\", "/"),
            wheel_dll_root + "\\",
            os.path.join(os.path.dirname(wheel_dll_root), ".", os.path.basename(wheel_dll_root)),
        ]
        # (name, override, PATH, expected fallbacks, expected PATH entries after the wheel); None leaves a variable unset
        cases = [
            ("unset override falls back to PATH", None, [first, second], [first, second], [first, second]),
            ("empty override excludes PATH", [], [first], [], [first]),
            ("multiple overrides keep their order", overrides, [first], overrides, [first]),
            ("existing wheel entry moves to the front", None, [first, wheel_dll_root, second], [first, second], [first, second]),
            ("equivalent spellings collapse", [*wheel_spellings, overrides[0]], [first, *wheel_spellings, second], [overrides[0]], [first, second]),
            ("unrelated duplicates are kept", None, [first, second, first], [first, second, first], [first, second, first]),
            ("missing PATH", None, None, [], []),
            ("empty PATH", None, [], [], []),
        ]
        for name, override, path, expected_fallbacks, expected_path_entries in cases:
            with self.subTest(name=name):
                env = os.environ.copy()
                for key, value in (("PXR_USD_WINDOWS_DLL_PATH", override), ("PATH", path)):
                    if value is None:
                        env.pop(key, None)
                    else:
                        env[key] = os.pathsep.join(value)
                result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                values = json.loads(result.stdout.splitlines()[-1])
                # exact lists: the wheel directory is first and appears once, and every other entry keeps its order
                self.assertEqual(values["dll_paths"], [values["dll_path"], *expected_fallbacks])
                self.assertEqual(values["path_entries"], [values["dll_path"], *expected_path_entries])
                version = normalize_version(values["version"])
                self.assertEqual(version, expected_version)

    @unittest.skipUnless(sys.platform == "win32", "Windows DLL search test")
    def testPxrDllPathLoadsCallerDll(self):
        """Prove that OpenUSD loads a required DLL found only in a caller-supplied directory.

        The directory is reachable through an explicit override, or through PATH when the override is unset.
        An empty override must exclude PATH, so the same import fails.
        """
        dll_root = self._getWheelDllRoot()
        if dll_root is None:
            self.skipTest("Test requires the installed wheel")
        pxr_root = os.path.abspath(os.path.join(dll_root, "../pxr"))

        with tempfile.TemporaryDirectory(dir=os.path.dirname(dll_root), prefix="_usdex_dll_test_") as staging_root:
            # Create an isolated wheel layout with independent files.
            staged_pxr_root = os.path.join(staging_root, "pxr")
            staged_dll_root = os.path.join(staging_root, "usd_exchange.libs")
            shutil.copytree(pxr_root, staged_pxr_root)
            shutil.copytree(dll_root, staged_dll_root)

            # Remove usd_tf.dll from the wheel directory and expose it only through the caller path.
            fallback_root = os.path.join(staging_root, "fallback")
            os.mkdir(fallback_root)
            staged_dll = os.path.join(staged_dll_root, "usd_tf.dll")
            fallback_dll = os.path.join(fallback_root, os.path.basename(staged_dll))
            self.assertTrue(os.path.isfile(staged_dll), f"Missing wheel DLL: {staged_dll}")
            shutil.move(staged_dll, fallback_dll)

            # Report the file the DLL was loaded from, so another installed copy cannot mask the result.
            script = """
import ctypes
from ctypes import wintypes
from pxr import Tf
assert hasattr(Tf, "Status")
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
buffer = ctypes.create_unicode_buffer(32768)
kernel32.GetModuleFileNameW(kernel32.GetModuleHandleW("usd_tf.dll"), buffer, len(buffer))
print(buffer.value)
"""
            path = self._removePathEntry(os.environ.get("PATH", ""), dll_root)
            # (name, override, PATH, whether usd_tf.dll must load); None leaves the override unset
            cases = [
                ("explicit override", fallback_root, path, True),
                ("unset override falls back to PATH", None, os.pathsep.join([fallback_root, path]), True),
                ("empty override excludes PATH", "", os.pathsep.join([fallback_root, path]), False),
            ]
            for name, override, path_value, loads in cases:
                with self.subTest(name=name):
                    env = os.environ.copy()
                    env["PYTHONPATH"] = staging_root
                    env["PATH"] = path_value
                    if override is None:
                        env.pop("PXR_USD_WINDOWS_DLL_PATH", None)
                    else:
                        env["PXR_USD_WINDOWS_DLL_PATH"] = override
                    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env)
                    if loads:
                        self.assertEqual(result.returncode, 0, result.stderr)
                        loaded_dll = result.stdout.splitlines()[-1]
                        self.assertEqual(os.path.normcase(os.path.realpath(loaded_dll)), os.path.normcase(os.path.realpath(fallback_dll)))
                    else:
                        self.assertNotEqual(result.returncode, 0, result.stdout)
                        self.assertIn("DLL load failed", result.stderr)

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

        if Usd.GetVersion() >= (0, 26, 8):
            from pxr import UsdLod, UsdProfiles

            self.assertTrue(hasattr(UsdLod, "RootAPI"))
            self.assertTrue(hasattr(UsdProfiles, "ClaimsAPI"))
            self.assertTrue(hasattr(UsdProfiles, "ProfileRegistry"))

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

    def testNativeValidatorsProvidedByUvn(self):
        try:
            import usd_validation_nvidia
            import usdex.test  # noqa: F401 imported for the rules it registers
        except ImportError:
            self.skipTest("usd_validation_nvidia / pxr.UsdValidation not available")
        requiredAdapters = (
            usd_validation_nvidia.UsdShadeEncapsulationMaterialValidator,
            usd_validation_nvidia.UsdShadeMaterialBindingCollectionValidator,
            usd_validation_nvidia.UsdShadeMaterialBindingRelationships,
            usd_validation_nvidia.UsdShadeShaderSdrCompliance,
            usd_validation_nvidia.UsdShadeSubsetsMaterialBindFamilyChecker,
            usd_validation_nvidia.UsdUtilsFileExtensionValidator,
            usd_validation_nvidia.UsdUtilsPackageEncapsulationValidator,
            usd_validation_nvidia.UsdValidationAttributeTypeMismatchChecker,
        )
        expected = {rule for rule in requiredAdapters if rule.is_implemented()}
        engine = usd_validation_nvidia.ValidationEngine(init_rules=True)
        adapters = [r for r in engine.rules if issubclass(r, usd_validation_nvidia.UsdValidatorAdapter)]
        expectedNames = {rule.validator_name() for rule in expected}
        registered = [rule for rule in adapters if rule.validator_name() in expectedNames]
        self.assertCountEqual(registered, expected)
