# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import subprocess
import sys
import unittest


class PxrTest(unittest.TestCase):

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
