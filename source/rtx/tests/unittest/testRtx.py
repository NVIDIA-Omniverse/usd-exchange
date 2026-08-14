# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import unittest

import usdex.rtx


class RtxTest(unittest.TestCase):

    def testModuleSymbols(self):
        allowList = [
            "os",  # module necessary to locate bindings on windows
            "_usdex_rtx",  # our binding module
            "deprecated",  # decorator imported from usdex.core
        ]
        allowList.extend([x for x in dir(usdex.rtx) if x.startswith("__")])  # private members

        for attr in dir(usdex.rtx):
            if attr in allowList:
                continue
            self.assertIn(attr, usdex.rtx.__all__)

        for attr in usdex.rtx.__all__:
            self.assertIn(attr, dir(usdex.rtx))
