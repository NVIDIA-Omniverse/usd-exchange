# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

__all__ = [
    "TestCase",
]

import os
import pathlib
import re
import shutil
import sys
import tempfile
import unittest
from typing import List, Optional

import omni.asset_validator
import pkg_resources
import usdex.core
from pxr import Sdf, Usd, UsdGeom


class TestCase(unittest.TestCase):
    """
    A unittest base class to simplify testing common USD authoring functionality
    """

    maxDiff = None
    "See `unittest.TestCase.maxDiff <https://docs.python.org/3/library/unittest.html#unittest.TestCase.maxDiff>`_ documentation"

    validFileIdentifierRegex = r"[^A-Za-z0-9_-]"

    defaultPrimName = "Root"
    "The default prim name to be used when configuring a ``Usd.Stage``"

    defaultUpAxis = UsdGeom.Tokens.y
    "The default Up Axis to be used when configuring a ``Usd.Stage``"

    defaultLinearUnits = UsdGeom.LinearUnits.meters
    "The default Linear Units to be used when configuring a ``Usd.Stage``"

    defaultAuthoringMetadata = (
        f"usdex_ver: {usdex.core.version()}, usd_ver: {Usd.GetVersion()}, python_ver: {sys.version_info.major}.{sys.version_info.minor}"
    )
    "The default authoring metadata to be used when configuring a ``Usd.Stage``"

    defaultValidationIssuePredicates = []
    "A list of callables to determine if certain USD validation Issues should be ignored for this TestCase"

    @classmethod
    def setUpClass(cls):
        # activate the usdex delegate to affect OpenUSD diagnostic logs
        usdex.core.activateDiagnosticsDelegate()

    def setUp(self):
        super().setUp()

        self.validationEngine = omni.asset_validator.ValidationEngine(init_rules=True)

    def assertIsValidUsd(self, asset: omni.asset_validator.AssetType, issuePredicates: Optional[List] = None, msg: Optional[str] = None):
        """Assert that given asset passes all enabled validation rules

        Args:
            asset: The Asset to validate. Either a Usd.Stage object or a path to a USD Layer.
            issuePredicates: Optional List of additional callables - ``func(issue)`` that are used to check if the issue can be bypassed.
                The default list of IssuePredicates will always be enabled.
            msg: Optional message to report while validation failed.
        """

        ips = []
        if issuePredicates:
            ips = issuePredicates + self.defaultValidationIssuePredicates
        else:
            ips = self.defaultValidationIssuePredicates

        issues = self.__validateUsd(asset=asset, engine=self.validationEngine, issuePredicates=ips)
        if issues:
            if msg is None:
                msg = "\n".join(str(issue) for issue in list(issues))
            self.fail(msg=msg)

    def assertIsInvalidUsd(self, asset: omni.asset_validator.AssetType, issuePredicates: omni.asset_validator.IssuePredicates):
        """Assert that given asset reported with issuePredicates

        Args:
            asset: The Asset to validate. Either a Usd.Stage object or a path to a USD Layer.
            issuePredicates (List): List of omni.asset_validator.IssuePredicates.
        """
        issues = self.__validateUsd(asset=asset, engine=self.validationEngine)

        nonDetectedPredicates = []
        for predicate in issuePredicates:
            if not issues.filter_by(predicate):
                nonDetectedPredicates.append(predicate)

        # Chain all predicates by "or" condition
        predicate = omni.asset_validator.IssuePredicates.Or(*issuePredicates)
        unexpectedIssues = set(issues) - set(issues.filter_by(predicate))

        if not nonDetectedPredicates and not unexpectedIssues:
            return

        msg = ""
        if nonDetectedPredicates:
            msg += "The following IssuePredicates did not occur:\n"
            msg = msg + "\n".join(str(predicate) for predicate in nonDetectedPredicates) + "\n"

        if unexpectedIssues:
            msg += "The following unexpected issues occurred:\n"
            msg = msg + "\n".join(str(issue) for issue in unexpectedIssues) + "\n"

        self.fail(msg=msg)

    def assertUsdLayerEncoding(self, layer: Sdf.Layer, encoding: str):
        """Assert that the given layer uses the given encoding type"""
        self.assertEqual(self.getUsdEncoding(layer), encoding)

    def assertSdfLayerIdentifier(self, layer, identifier):
        """Assert that the given layer has the expected identifier"""
        # Resolve paths to normalize casing and then make them into posix paths, this removes platform specific variations
        expected = pathlib.Path(identifier).resolve().as_posix()
        returned = pathlib.Path(layer.identifier).resolve().as_posix()
        self.assertEqual(expected, returned)

    def assertAttributeHasAuthoredValue(self, attr: Usd.Attribute, time=Usd.TimeCode.Default()):
        """Asserts that a ``Usd.Attribute`` has a value authored at a given time"""
        if time == Usd.TimeCode.Default():
            self.assertIsNotNone(attr.Get(time))
        else:
            self.assertIn(time, attr.GetTimeSamples())

    def assertMatricesAlmostEqual(self, first, second, places=12):
        """Assert that all 16 values of a pair of 4x4 matrices are equal, to a specified number of decimal places"""
        for row in range(4):
            for col in range(4):
                x = first[row][col]
                y = second[row][col]
                self.assertEqual(round(x - y, places), 0)
        self.assertTrue(True)

    def assertVecAlmostEqual(self, first, second, places=12):
        """Assert that all elements of a Vec are equal, to a specified number of decimal places"""
        self.assertEqual(len(first), len(second))
        for idx in range(len(first)):
            self.assertAlmostEqual(first[idx], second[idx], places)

    def tmpLayer(self, name: str = "", ext: str = "usda") -> Sdf.Layer:
        """
        Create a temporary Sdf.Layer on the local filesystem

        Args:
            name: an optional identifier prefix. If not provided the test name will be used
            ext: an optional file extension (excluding ``.``) which must match a registered Sdf.FileFormatPlugin

        Returns:
            The ``Sdf.Layer`` object
        """
        return Sdf.Layer.CreateNew(self.tmpFile(name=name, ext=ext))

    def tmpFile(self, name: str = "", ext: str = "") -> str:
        """
        Create a temporary file on the local filesystem

        Args:
            name: an optional filename prefix. If not provided the test name will be used
            ext: an optional file extension (excluding ``.``)

        Returns:
            The filesystem path
        """
        tempDir = self.tmpBaseDir()
        if not os.path.exists(tempDir):
            os.makedirs(tempDir)

        # Sanitize name string
        name = re.sub(TestCase.validFileIdentifierRegex, "_", name or self._testMethodName)
        (handle, fileName) = tempfile.mkstemp(prefix=f"{os.path.join(tempDir, name)}_", suffix=f".{ext}")
        # closing the os handle immediately. we don't need this now that the file is known to be unique
        # and it interferes with some internal processes.
        os.close(handle)
        return fileName

    @staticmethod
    def isUsdOlderThan(version: str):
        """Determine if the provided versions is older than the current USD runtime"""
        return pkg_resources.parse_version(".".join([str(x) for x in Usd.GetVersion()])) < pkg_resources.parse_version(version)

    @staticmethod
    def tmpBaseDir() -> str:
        """Get the path of the base temp directory. All temp files and directories in the same process will be created under this directory.
        Returns:
            The filesystem path
        """
        # Sanitize Version string
        versionString = re.sub(TestCase.validFileIdentifierRegex, "_", usdex.core.version())

        # Create all subdirs under $TEMP
        pidString = os.environ.get("CI_PIPELINE_IID", os.getpid())
        subdirsPrefix = os.path.join("usdex", f"{versionString}-{pidString}")
        return os.path.join(tempfile.tempdir, subdirsPrefix)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpBaseDir(), ignore_errors=True)

    @staticmethod
    def getUsdEncoding(layer: Sdf.Layer):
        """Get the extension of the encoding type used within an SdfLayer"""
        fileFormat = layer.GetFileFormat()

        # If the encoding is explicit usda return that extension
        usdaFileFormat = Sdf.FileFormat.FindById("usda")
        if fileFormat == usdaFileFormat:
            return "usda"

        # If the encoding is explicit usdc return that extension
        usdcFileFormat = Sdf.FileFormat.FindById("usdc")
        if fileFormat == usdcFileFormat:
            return "usdc"

        # If the encoding is implicit check which of the explicit extensions can read the layer and return that type
        usdFileFormat = Sdf.FileFormat.FindById("usd")
        if fileFormat == usdFileFormat:
            return usdFileFormat.GetUnderlyingFormatForLayer(layer)

        return ""

    @staticmethod
    def __validateUsd(
        asset: omni.asset_validator.AssetType,
        engine: omni.asset_validator.ValidationEngine,
        issuePredicates: Optional[List] = None,
    ) -> omni.asset_validator.IssuesList:
        """Validate asset passes all enabled validation rules

        Args:
            asset: The Asset to validate. Either a Usd.Stage object or a path to a USD Layer.

        Kwargs:
            engine: ValidationEngine for running Rules on a given Asset.
            issuePredicates: Optional List of additional callables - ``func(issue)`` that are used to check if the issue can be bypassed.
                The default list of IssuePredicates will always be enabled.

        Return:
            A list of USD asset Issues.
        """
        result = engine.validate(asset)

        issues = result.issues()
        if issuePredicates:
            allowedIssues = issues.filter_by(omni.asset_validator.IssuePredicates.Or(*issuePredicates))
            if allowedIssues:
                issues = omni.asset_validator.IssuesList(list(set(issues) - set(allowedIssues)))

        return issues
