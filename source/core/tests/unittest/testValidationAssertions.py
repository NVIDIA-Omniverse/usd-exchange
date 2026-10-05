# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import usd_validation_nvidia
import usdex.core
import usdex.test


class ValidationAssertionsTest(usdex.test.TestCase):

    def testIssueLocations(self):
        stage = usdex.core.createStage(
            self.tmpFile("locations", ext="usda"),
            usdex.core.getValidPrimName(self.defaultPrimName),
            self.defaultUpAxis,
            self.defaultLinearUnits,
            self.defaultAuthoringMetadata,
        )
        root = usdex.core.defineXform(stage.GetDefaultPrim()).GetPrim()
        child = usdex.core.defineXform(root, usdex.core.getValidChildName(root, "Child")).GetPrim()

        for locations in (None, root, [root], [root, child], (root,), (root, child)):
            with self.subTest(locations=locations):

                class LocationChecker(usd_validation_nvidia.BaseRuleChecker):
                    def CheckStage(self, stage):
                        self._AddFailedCheck(message="Invalid test locations", at=locations)

                self.validationEngine = usd_validation_nvidia.ValidationEngine(init_rules=False)
                self.validationEngine.enable_rule(LocationChecker)
                issue = self.validationEngine.validate(stage).issues()[0]
                identifiers = issue.at if isinstance(issue.at, (list, tuple)) else [issue.at] if issue.at else []
                expected = "LocationChecker: Invalid test locations"
                if identifiers:
                    expected += " At " + ", ".join(identifier.as_str() for identifier in identifiers)

                with self.assertRaises(AssertionError) as context:
                    self.assertIsValidUsd(stage)
                self.assertEqual(str(context.exception), expected)

    def testIssueFiltering(self):
        stage = usdex.core.createStage(
            self.tmpFile("filtering", ext="usda"),
            usdex.core.getValidPrimName(self.defaultPrimName),
            self.defaultUpAxis,
            self.defaultLinearUnits,
            self.defaultAuthoringMetadata,
        )
        root = usdex.core.defineXform(stage.GetDefaultPrim()).GetPrim()
        child = usdex.core.defineXform(root, usdex.core.getValidChildName(root, "Child")).GetPrim()
        self.assertIsValidUsd(stage)
        expectedPredicate = usd_validation_nvidia.IssuePredicates.ContainsMessage("Expected finding")
        unexpectedPredicate = usd_validation_nvidia.IssuePredicates.ContainsMessage("Unexpected finding")
        missingPredicate = usd_validation_nvidia.IssuePredicates.ContainsMessage("Missing finding")

        for locations in (None, root, [], [root], [root, child], (), (root,), (root, child)):

            class LocationChecker(usd_validation_nvidia.BaseRuleChecker):
                def CheckStage(self, stage):
                    self._AddFailedCheck(message="Expected finding", at=locations)
                    self._AddFailedCheck(message="Unexpected finding", at=locations)

            self.validationEngine = usd_validation_nvidia.ValidationEngine(init_rules=False)
            self.validationEngine.enable_rule(LocationChecker)
            issue = self.validationEngine.validate(stage).issues()[1]
            identifiers = issue.at if isinstance(issue.at, (list, tuple)) else [issue.at] if issue.at else []
            diagnostic = "LocationChecker: Unexpected finding"
            if identifiers:
                diagnostic += " At " + ", ".join(identifier.as_str() for identifier in identifiers)

            with self.subTest(locations=locations, helper="valid-all-allowed"):
                self.assertIsValidUsd(stage, issuePredicates=[expectedPredicate, unexpectedPredicate])
            with self.subTest(locations=locations, helper="invalid-all-expected"):
                self.assertIsInvalidUsd(stage, [expectedPredicate, unexpectedPredicate])
            with self.subTest(locations=locations, helper="valid-unexpected"):
                with self.assertRaises(AssertionError) as context:
                    self.assertIsValidUsd(stage, issuePredicates=[expectedPredicate])
                self.assertEqual(str(context.exception), diagnostic)
            with self.subTest(locations=locations, helper="invalid-unexpected"):
                with self.assertRaises(AssertionError) as context:
                    self.assertIsInvalidUsd(stage, [expectedPredicate])
                self.assertEqual(str(context.exception), f"The following unexpected issues occurred:\n{diagnostic}\n")
            with self.subTest(locations=locations, helper="invalid-missing-and-unexpected"):
                with self.assertRaises(AssertionError) as context:
                    self.assertIsInvalidUsd(stage, [expectedPredicate, missingPredicate])
                self.assertIn("The following IssuePredicates did not occur:", str(context.exception))
                self.assertIn(diagnostic, str(context.exception))
                self.assertNotIn("LocationChecker: Expected finding", str(context.exception))
