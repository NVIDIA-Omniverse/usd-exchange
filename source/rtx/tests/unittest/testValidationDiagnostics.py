# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os

import usd_validation_nvidia
import usdex.core
import usdex.rtx
import usdex.test
from pxr import Gf, Sdf, Tf, UsdShade


class ValidationDiagnosticsTest(usdex.test.TestCase):

    def testUnresolvedMdlLocations(self):
        # Use an absent absolute path so MDL search paths cannot satisfy this dependency.
        missingMdl = os.path.join(self.tmpDir(), "missing.mdl")
        for count in (1, 2):
            with self.subTest(materialCount=count):
                stage = usdex.core.createStage(
                    self.tmpFile(f"materials_{count}", ext="usda"),
                    usdex.core.getValidPrimName(self.defaultPrimName),
                    self.defaultUpAxis,
                    self.defaultLinearUnits,
                    self.defaultAuthoringMetadata,
                )
                root = usdex.core.defineXform(stage.GetDefaultPrim()).GetPrim()
                attributes = []
                for index in range(count):
                    material = usdex.rtx.definePbrMaterial(root, usdex.core.getValidChildName(root, f"Material_{index}"), Gf.Vec3f(0.5))
                    shader = UsdShade.Shader(material.ComputeSurfaceSource("mdl")[0])
                    shader.SetSourceAsset(Sdf.AssetPath(missingMdl), "mdl")
                    attributes.append(shader.GetPrim().GetAttribute("info:mdl:sourceAsset"))

                self.validationEngine = usd_validation_nvidia.ValidationEngine(init_rules=False)
                self.validationEngine.enable_rule(usd_validation_nvidia.MaterialPathChecker)
                # USD 26.08+ de-duplicates warnings for attributes sharing the same missing asset.
                warningCount = count if self.isUsdOlderThan("0.26.08") else 1
                expected = [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, r".*Failed to resolve reference @.*missing\.mdl@")] * warningCount
                with usdex.test.ScopedDiagnosticChecker(self, expected):
                    issues = self.validationEngine.validate(stage).issues()
                self.assertEqual(len(issues), 1)
                issue = issues[0]
                self.assertIsInstance(issue.at, tuple)
                self.assertEqual(len(issue.at), count)

                # Leave the missing-MDL finding unfiltered: it must be an informative assertion failure.
                with usdex.test.ScopedDiagnosticChecker(self, expected), self.assertRaises(AssertionError) as context:
                    self.assertIsValidUsd(stage)
                diagnostic = str(context.exception)
                self.assertIn("MaterialPathChecker:", diagnostic)
                self.assertIn(issue.message, diagnostic)
                self.assertIn(missingMdl, diagnostic)
                for attribute in attributes:
                    self.assertIn(str(attribute.GetPrim().GetPath()), diagnostic)
                    self.assertIn(attribute.GetName(), diagnostic)

                # Unexpected findings must also be readable through assertIsInvalidUsd.
                with usdex.test.ScopedDiagnosticChecker(self, expected), self.assertRaises(AssertionError) as context:
                    self.assertIsInvalidUsd(stage, [usd_validation_nvidia.IssuePredicates.ContainsMessage("Different finding")])
                self.assertIn(diagnostic, str(context.exception))
