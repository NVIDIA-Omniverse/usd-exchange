# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import usdex.test
from pxr import Usd


class UsdVersionTest(usdex.test.TestCase):
    def __replaceMinorOrPatch(self, currentVersion: str, newMinorOrPatch: str) -> str:
        parts = currentVersion.split(".")
        if len(parts) >= 3:
            parts[2] = newMinorOrPatch  # Replace patch
        elif len(parts) >= 2:
            parts[1] = newMinorOrPatch  # Replace minor
        return ".".join(parts)

    def testVersion(self):
        # The current version of USD should not be older than Usd.GetVersion()
        # Note that the comments in this test are based on the assumption that
        # the current version of USD is 0.25.05, which is the version at the time
        # of writing this test.
        currentVersion = ".".join([str(x) for x in Usd.GetVersion()])
        self.assertFalse(self.isUsdOlderThan(currentVersion))

        self.assertFalse(self.isUsdOlderThan("0"))  # Only major
        self.assertTrue(self.isUsdOlderThan("99"))  # Only major
        self.assertFalse(self.isUsdOlderThan("0.1"))  # Major and minor
        self.assertTrue(self.isUsdOlderThan("99.0"))  # Major and minor
        self.assertFalse(self.isUsdOlderThan("0.1.0"))
        self.assertFalse(self.isUsdOlderThan("-1.0.0"))

        # Compare against something like 0.25.0
        earlyYearCurrentVersion = self.__replaceMinorOrPatch(currentVersion, "0")
        self.assertFalse(self.isUsdOlderThan(earlyYearCurrentVersion))

        # Compare against something like 0.25.99
        lateYearCurrentVersion = self.__replaceMinorOrPatch(currentVersion, "99")
        self.assertTrue(self.isUsdOlderThan(lateYearCurrentVersion))

        # Make sure that 0.25.05 behaves properly
        patch = currentVersion.split(".")[-1]
        prependedCurrentVersion = self.__replaceMinorOrPatch(currentVersion, "0" + patch)
        self.assertFalse(self.isUsdOlderThan(prependedCurrentVersion))

        # Make sure that 0.25.05-alpha is ignored
        currentVersionAlpha = self.__replaceMinorOrPatch(currentVersion, patch + "-alpha")
        self.assertFalse(self.isUsdOlderThan(currentVersionAlpha))

        # Make sure that 0.25.05+build is ignored
        currentVersionAlpha = self.__replaceMinorOrPatch(currentVersion, patch + "+build")
        self.assertFalse(self.isUsdOlderThan(currentVersionAlpha))

        self.assertTrue(self.isUsdOlderThan("9999.0.0"))
        self.assertTrue(self.isUsdOlderThan("9999.9999.0"))
        self.assertTrue(self.isUsdOlderThan("9999.9999.9999"))

        self.assertFalse(self.isUsdOlderThan(" 0.1.1 "))  # Whitespace
        self.assertTrue(self.isUsdOlderThan(" 99.1.1 "))  # Whitespace
        self.assertFalse(self.isUsdOlderThan("foo.bar.baz"))  # Non-numeric, should handle gracefully
