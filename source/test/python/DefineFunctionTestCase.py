# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

__all__ = [
    "DefineFunctionTestCase",
]

import unittest
from abc import abstractmethod

from pxr import Sdf, Tf, Usd, UsdGeom

from .ScopedDiagnosticChecker import ScopedDiagnosticChecker
from .TestCase import TestCase


class DefineFunctionTestCase(TestCase):
    """
    Class to make assertions that should be valid for all usdex functions that define typed prims

    This class inherits from `usdex.test.TestCase` and adds several abstract properties that must be overridden by derived classes
    in order to configure the expected results of a default "define" operation.

    It also adds 2 useful assertions: `assertDefineFunctionSuccess` and `assertDefineFunctionFailure` and adds several concrete
    test method implementations to cover scenarios that all "define" functions must adhere to.
    """

    @property
    @abstractmethod
    def defineFunc(self):
        """The function used to define the prim"""
        raise NotImplementedError()

    @property
    @abstractmethod
    def requiredArgs(self):
        """A tuple of valid values for the required arguments"""
        raise NotImplementedError()

    @property
    @abstractmethod
    def schema(self):
        """The class that the return value should be an instance of"""
        raise NotImplementedError()

    @property
    @abstractmethod
    def typeName(self):
        """The type name that the defined prim should have"""
        raise NotImplementedError()

    @property
    @abstractmethod
    def requiredPropertyNames(self):
        """A set of property names that the defined prim should have"""
        raise NotImplementedError()

    def createTestStage(self):
        """Create an in memory stage holding a range of prims that are useful for testing"""
        # Create the stage and define the standard "/World" prim at the root

        # Build a layered stage
        self.weakerSubLayer = self.tmpLayer(name="Weaker")
        self.strongerSubLayer = self.tmpLayer(name="Stronger")
        self.rootLayer = self.tmpLayer(name="Root")
        self.rootLayer.subLayerPaths.append(self.strongerSubLayer.identifier)
        self.rootLayer.subLayerPaths.append(self.weakerSubLayer.identifier)

        stage = Usd.Stage.Open(self.rootLayer)

        # Define the standard "/World" prim in the root layer
        stage.SetEditTarget(Usd.EditTarget(self.rootLayer))
        prim = UsdGeom.Xform.Define(stage, "/World").GetPrim()
        stage.SetDefaultPrim(prim)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.centimeters)

        # Define test prims in the weaker layer
        stage.SetEditTarget(Usd.EditTarget(self.weakerSubLayer))

        # Create a prototype prim and then add an instanceable reference to it from within /World
        # This can be used to create scenarios where a path points to an instance proxy prim
        # Typeless prims will fail the TypeChecker asset validation checks
        stage.CreateClassPrim("/Prototypes")
        UsdGeom.Xform.Define(stage, "/Prototypes/Prototype")
        xformPrim = UsdGeom.Xform.Define(stage, "/World/Instance")
        xformPrim.GetPrim().GetReferences().AddInternalReference(Sdf.Path("/Prototypes/Prototype"))
        xformPrim.GetPrim().SetInstanceable(True)

        # Set the edit target to the stronger layer
        stage.SetEditTarget(Usd.EditTarget(self.strongerSubLayer))

        return stage

    def assertDefineFunctionSuccess(self, result):
        """Assert that the result returned represents success"""
        # The result should be a valid instance of the schema associated with the typed prim being defined
        self.assertIsInstance(result, self.schema)
        self.assertTrue(result)

        # Get the stages current edit target layer to assert that opinions have been authored explicitly
        layer = result.GetPrim().GetStage().GetEditTarget().GetLayer()

        # The prim should have a "def" specifier and type name authored in the current layer
        primPath = result.GetPath()
        primSpec = layer.GetPrimAtPath(primPath)
        self.assertTrue(primSpec, f'No prim defined at "{primPath}" in layer "{layer.identifier}"')
        self.assertEqual(primSpec.typeName, self.typeName)
        self.assertEqual(primSpec.specifier, Sdf.SpecifierDef)

        # All of the required properties should have default values authored in the current layer
        for propertyName in self.requiredPropertyNames:
            propertyPath = primPath.AppendProperty(propertyName)
            propertySpec = layer.GetPropertyAtPath(propertyPath)
            self.assertTrue(propertySpec, f'No property defined at "{propertyPath}" in layer "{layer.identifier}"')
            self.assertTrue(propertySpec.HasDefaultValue())

    def assertDefineFunctionFailure(self, result):
        """Assert that the result returned represents a failure"""
        # The result should be an invalid instance of the schema associated with the typed prim being defined
        self.assertIsInstance(result, self.schema)
        self.assertFalse(result)

    def testStagePathSuccess(self):
        # A valid stage and path will result in success
        stage = self.createTestStage()

        # A prim can be defined in the root layer
        path = Sdf.Path("/World/NewPrim")
        stage.SetEditTarget(Usd.EditTarget(self.rootLayer))
        result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)
        self.assertIsValidUsd(stage)

    def testWeakerStronger(self):
        # A prim can be defined in a weaker sub layer and then re-defined in a stronger one.
        stage = self.createTestStage()

        path = Sdf.Path("/World/WeakerFirst")
        stage.SetEditTarget(Usd.EditTarget(self.weakerSubLayer))
        result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)

        stage.SetEditTarget(Usd.EditTarget(self.strongerSubLayer))
        result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)
        self.assertIsValidUsd(stage)

    def testStrongerWeaker(self):
        # A prim can be defined in a stronger sub layer and then re-defined in a weaker one.
        stage = self.createTestStage()

        path = Sdf.Path("/World/StrongerFirst")
        stage.SetEditTarget(Usd.EditTarget(self.strongerSubLayer))
        result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)

        stage.SetEditTarget(Usd.EditTarget(self.weakerSubLayer))
        result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)
        self.assertIsValidUsd(stage)

    def testParentNameSuccess(self):
        # A valid parent and name will result in success
        stage = self.createTestStage()

        # A location where no prim currently exists will result in success
        parent = stage.GetPrimAtPath("/World")
        name = "NewPrim"
        result = self.defineFunc(parent, name, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)
        self.assertIsValidUsd(stage)

    def testRedefinePrim(self):
        # A prim can be converted from one type to another
        stage = self.createTestStage()

        # Create a Scope prim first
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        self.assertEqual(scopePrim.GetTypeName(), "Scope")

        # Convert it to the target type
        result = self.defineFunc(scopePrim, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)
        self.assertEqual(result.GetPrim(), scopePrim)
        self.assertEqual(result.GetPrim().GetTypeName(), self.typeName)

        # Create an untyped prim first
        untyped_prim = stage.DefinePrim("/World/UntypedPrim", "")
        self.assertEqual(untyped_prim.GetTypeName(), "")

        # Convert it to the target type
        result = self.defineFunc(untyped_prim, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)
        self.assertEqual(result.GetPrim(), untyped_prim)
        self.assertEqual(result.GetPrim().GetTypeName(), self.typeName)

    def testInvalidStage(self):
        # An invalid stage will result in a failure
        path = Sdf.Path("/World/InvalidStage")

        # A null object will be accepted but the function will return a failure
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Invalid UsdStage")]):
            result = self.defineFunc(None, path, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

    def testInvalidPath(self):
        # A invalid path will result in a failure
        stage = self.createTestStage()

        # The absolute root is an invalid
        path = Sdf.Path("/")
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # A relative path is invalid
        path = Sdf.Path("Foo/Bar")
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # An uninitialized path is invalid
        path = Sdf.Path()
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # The path for an instance proxy is invalid
        path = Sdf.Path("/World/Instance/Instanced")
        with ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    ".*invalid location.*/World/Instance/Instanced.*descendant of instance.*authoring is not allowed",
                ),
            ],
        ):
            result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # A path where a parent is an instance proxy is invalid
        path = Sdf.Path("/World/Instance/Instanced/Prim")
        with ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    ".*invalid location.*/World/Instance/Instanced/Prim.*descendant of instance.*authoring is not allowed",
                ),
            ],
        ):
            result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)
        self.assertIsValidUsd(stage)

    def testInvalidParent(self):
        # A invalid parent will result in a failure
        stage = self.createTestStage()
        name = "Prim"

        # An un-initialized prim is invalid
        parent = Usd.Prim()
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            result = self.defineFunc(parent, name, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # An invalid prim is invalid
        parent = stage.GetPrimAtPath("/World/InvalidParent")
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            result = self.defineFunc(parent, name, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # An instance proxy is invalid
        parent = stage.GetPrimAtPath("/World/Instance/Instanced")
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            result = self.defineFunc(parent, name, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)
        self.assertIsValidUsd(stage)

    def testInvalidName(self):
        # A invalid name will result in a failure
        stage = self.createTestStage()
        parent = stage.GetPrimAtPath("/World")

        # An empty string is invalid
        name = ""
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*not a valid prim name")]):
            result = self.defineFunc(parent, name, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # A string containing illegal characters is invalid
        name = "Foo Bar"
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*not a valid prim name")]):
            result = self.defineFunc(parent, name, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # A string starting with a numeric is invalid
        name = "1_Prim"
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*not a valid prim name")]):
            result = self.defineFunc(parent, name, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

        # The name of an instance proxy is invalid
        parent = stage.GetPrimAtPath("/World/Instance")
        name = "Instanced"
        with ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location.*/World/Instance.*an instance, authoring is not allowed"),
            ],
        ):
            result = self.defineFunc(parent, name, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)
        self.assertIsValidUsd(stage)

    def testDefineFromInvalidPrim(self):
        stage = self.createTestStage()
        invalidPrim = stage.GetPrimAtPath("/NonExistent")
        with ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            result = self.defineFunc(invalidPrim, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)
