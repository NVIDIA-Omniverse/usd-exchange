# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import subprocess
import sys
import unittest


class PxrTest(unittest.TestCase):

    def testPxrImport(self):
        # clear the PATH to avoid test suite bootstrapping the USD install
        env = os.environ.copy()
        if env.get("PXR_USD_WINDOWS_DLL_PATH"):
            del env["PATH"]
        # Run in subprocess to avoid usdex.core already being imported
        code = "from pxr import Tf; assert hasattr(Tf, 'Status')"
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, f"Failed to import pxr.Tf: {result.stderr.decode()}")

        code = """
from pxr import Usd
major, minor, patch = Usd.GetVersion()
if major >= 24 and minor >= 11:
    from pxr import UsdSemantics
    assert hasattr(UsdSemantics, 'LabelsAPI'), "UsdSemantics.LabelsAPI not available"
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, f"Failed to import pxr.UsdSemantics: {result.stderr.decode()}")
