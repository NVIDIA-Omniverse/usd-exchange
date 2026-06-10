# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import usd_validation_nvidia
import usdex.core
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt
from utils.DefinePointBasedTestCaseMixin import DefinePointBasedTestCaseMixin

POINTS = Vt.Vec3fArray(
    [
        Gf.Vec3f(0.0, 0.0, 0.0),
        Gf.Vec3f(0.0, 0.0, 1.0),
        Gf.Vec3f(1.0, 0.0, 1.0),
        Gf.Vec3f(1.0, 0.0, 0.0),
        Gf.Vec3f(2.0, 0.0, 0.0),
        Gf.Vec3f(2.0, 0.0, 1.0),
    ]
)
IDS = Vt.Int64Array([0, 1, 2, 3, 4, 5])


class DefinePointCloudTestCase(DefinePointBasedTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.definePointCloud
    requiredArgs = tuple([POINTS])
    schema = UsdGeom.Points
    typeName = "Points"
    requiredPropertyNames = set(
        [
            UsdGeom.Tokens.points,
            UsdGeom.Tokens.extent,
        ]
    )
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def assertDefineFunctionSuccess(self, result):
        """Assert the common expectations of a successful call to definePointCloud"""
        super().assertDefineFunctionSuccess(result)

        # Assert that all required topology attributes are authored
        self.assertTrue(result.GetPointsAttr().IsAuthored())

        # Assert that a correct extent has been authored
        extent = UsdGeom.Boundable.ComputeExtentFromPlugins(result, Usd.TimeCode.Default())
        extentAttr = result.GetExtentAttr()
        self.assertTrue(extentAttr.IsAuthored())
        self.assertEqual(extentAttr.Get(), extent)

    def testInvalidTopology(self):
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The point array must not be empty
        points = Vt.Vec3fArray()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid points")]):
            pointCloud = usdex.core.definePointCloud(stage, path, points, IDS)
        self.assertDefineFunctionFailure(pointCloud)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The number of ids must match the number of points
        ids = Vt.Int64Array([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid ids")]):
            pointCloud = usdex.core.definePointCloud(stage, path, POINTS, ids)
        self.assertIsInstance(pointCloud, UsdGeom.Points)
        self.assertFalse(pointCloud)
        self.assertFalse(stage.GetPrimAtPath(path))
        self.assertIsValidUsd(stage)

    def testIds(self):
        # Ids are optional
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/Ids")
        UsdGeom.Scope.Define(stage, parentPath)

        # If ids are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertFalse(result.GetIdsAttr().HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs, ids=None)
        self.assertFalse(result.GetIdsAttr().HasAuthoredValue())

        # If an explicit value is specified a primvar will be authored
        path = parentPath.AppendChild("ExplicitValue")
        values = Vt.Int64Array(range(0, self.primvarSizes[UsdGeom.Tokens.vertex]))
        result = self.defineFunc(stage, path, *self.requiredArgs, ids=values)
        self.assertTrue(result.GetIdsAttr().HasAuthoredValue())
        self.assertEqual(result.GetIdsAttr().Get(), values)

        # If an empty value is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid ids")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, ids=Vt.Int64Array())
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.Int64Array([i for i in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid ids")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, ids=values)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))
        self.assertIsValidUsd(stage)

    def testWidths(self):
        # Widths are optional but if provided will be authored as a constant primvar
        stage = self.createTestStage()
        primvarName = UsdGeom.Tokens.widths
        parentPath = Sdf.Path("/World/Widths")
        UsdGeom.Scope.Define(stage, parentPath)

        # If widths are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=None)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        # If an explicit value is specified a primvar will be authored
        path = parentPath.AppendChild("ExplicitValue")
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([0.5]))
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        primvar: UsdGeom.Primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, widths)
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        # If a value that matches the fallback value is specified a primvar will be authored
        path = parentPath.AppendChild("FallbackValue")
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.0]))
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, widths)
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        # If a value less than 0 is specified a primvar will be authored
        path = parentPath.AppendChild("LessThanOneValue")
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([-0.5]))
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, widths)

        # If a value greater than 1 is specified a primvar will be authored
        path = parentPath.AppendChild("GreaterThanOneValue")
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.5]))
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, widths)

        # If an empty value is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        widths = widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([]))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the number of points a vertex primvar is authored
        path = parentPath.AppendChild("VertexValue")
        values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, widths)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))
        self.validationEngine.disable_rule(usd_validation_nvidia.IndexedPrimvarChecker)
        self.assertIsValidUsd(stage)

    def testIndexedWidths(self):
        # Widths can optional be indexed
        stage = self.createTestStage()
        primvarName = UsdGeom.Tokens.widths
        parentPath = Sdf.Path("/World/IndexedWidths")
        UsdGeom.Scope.Define(stage, parentPath)

        # If widths and widthsIndices are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        # If an empty array is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray(), Vt.IntArray())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the constant size then a constant primvar is authored
        path = parentPath.AppendChild("UniformValue")
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1]), Vt.IntArray([0]))
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, widths)
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        # If the array size matches the number of points a vertex primvar is authored
        path = parentPath.AppendChild("VertexValue")
        values = Vt.FloatArray([1])
        indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, widths)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.FloatArray([1])
        indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but the index values are outside the range of the normals size then no prim is defined
        path = parentPath.AppendChild("IndexValuesGreaterThanRange")
        values = Vt.FloatArray([0.0, 1.0])
        indices = Vt.IntArray([0, 1, 2, 3, 0, 1])
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but there are values less than zero then no prim is defined
        path = parentPath.AppendChild("NegativeIndexValues")
        values = Vt.FloatArray([0.0, 1.0])
        indices = Vt.IntArray([-1, 0, 1, -1, 0, 1])
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=widths)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))
        self.assertIsValidUsd(stage)

    def testSinglePoint(self):
        stage = self.createTestStage()
        path = Sdf.Path("/World/Single")

        point = Vt.Vec3fArray([Gf.Vec3f(0)])
        result = usdex.core.definePointCloud(stage, path, point)
        self.assertDefineFunctionSuccess(result)
        self.assertEqual(result.GetPointsAttr().Get(), point)

        ids = Vt.Int64Array([0])
        result = usdex.core.definePointCloud(stage, path, point, ids=ids)
        self.assertDefineFunctionSuccess(result)
        self.assertEqual(result.GetIdsAttr().Get(), ids)

        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([0.5]))
        result = usdex.core.definePointCloud(stage, path, point, widths=widths)
        self.assertDefineFunctionSuccess(result)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.widths)
        self.assertPrimvar(primvar, widths)

        # vertex interpolation will be respected even though it matches the expected constant interpolation size
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, Vt.FloatArray([0.5]))
        result = usdex.core.definePointCloud(stage, path, point, widths=widths)
        self.assertDefineFunctionSuccess(result)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.widths)
        self.assertPrimvar(primvar, widths)

        indices = Vt.IntArray([0])
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, Vt.FloatArray([0.5]), indices)
        result = usdex.core.definePointCloud(stage, path, point, widths=widths)
        self.assertDefineFunctionSuccess(result)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.widths)
        self.assertPrimvar(primvar, widths)

        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, Vt.Vec3fArray([Gf.Vec3f(0, 1, 0)]))
        result = usdex.core.definePointCloud(stage, path, point, normals=normals)
        self.assertDefineFunctionSuccess(result)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.normals)
        self.assertPrimvar(primvar, normals)

        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, Vt.Vec3fArray([Gf.Vec3f(0, 1, 0)]), indices)
        result = usdex.core.definePointCloud(stage, path, point, normals=normals)
        self.assertDefineFunctionSuccess(result)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.normals)
        self.assertPrimvar(primvar, normals)

        displayColor = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, Vt.Vec3fArray([Gf.Vec3f(0.5, 1, 0.5)]))
        result = usdex.core.definePointCloud(stage, path, point, displayColor=displayColor)
        self.assertDefineFunctionSuccess(result)
        primvar = result.GetDisplayColorPrimvar()
        self.assertPrimvar(primvar, displayColor)

        displayColor = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, Vt.Vec3fArray([Gf.Vec3f(0.5, 1, 0.5)]), indices)
        result = usdex.core.definePointCloud(stage, path, point, displayColor=displayColor)
        self.assertDefineFunctionSuccess(result)
        primvar = result.GetDisplayColorPrimvar()
        self.assertPrimvar(primvar, displayColor)

        displayOpacity = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, Vt.FloatArray([0.5]))
        result = usdex.core.definePointCloud(stage, path, point, displayOpacity=displayOpacity)
        self.assertDefineFunctionSuccess(result)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertPrimvar(primvar, displayOpacity)

        displayOpacity = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, Vt.FloatArray([0.5]), indices)
        result = usdex.core.definePointCloud(stage, path, point, displayOpacity=displayOpacity)
        self.assertDefineFunctionSuccess(result)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertPrimvar(primvar, displayOpacity)
        self.assertIsValidUsd(stage)


class PointsAlgoPrimOverloadTest(usdex.test.TestCase):
    """Test prim overloads for points define functions."""

    def createTestStage(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.centimeters)
        return stage

    def testDefinePointCloudPrimOverload(self):
        stage = self.createTestStage()
        prim = stage.DefinePrim("/World/PointCloud", "Points")

        # Define the point cloud using the prim overload
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Points.*to.*Points.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            points = usdex.core.definePointCloud(prim, POINTS)

        # Verify the prim was created correctly
        self.assertTrue(points)
        self.assertEqual(points.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(points.GetPrim().GetTypeName(), "Points")

        # Verify the points attribute was set
        self.assertEqual(points.GetPointsAttr().Get(), POINTS)

    def testDefinePointCloudPrimOverloadWithWidths(self):
        stage = self.createTestStage()
        prim = stage.DefinePrim("/World/PointCloudWithWidths", "Points")

        # Create test widths
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.5]))

        # Define the point cloud using the prim overload
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Points.*to.*Points.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            points = usdex.core.definePointCloud(prim, POINTS, widths=widths)

        # Verify the prim was created correctly
        self.assertTrue(points)
        self.assertEqual(points.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(points.GetPrim().GetTypeName(), "Points")

        # Verify the widths attribute was set
        primvar = UsdGeom.PrimvarsAPI(points).GetPrimvar(UsdGeom.Tokens.widths)
        self.assertTrue(primvar.HasAuthoredValue())
        self.assertEqual(primvar.Get(), widths.values())

    def testDefinePointCloudPrimOverloadWithOptionalArgs(self):
        stage = self.createTestStage()
        prim = stage.DefinePrim("/World/PointCloudWithOptionalArgs", "Points")

        # Create test data for optional arguments
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.5]))
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, Vt.Vec3fArray([Gf.Vec3f(0, 1, 0)] * len(POINTS)))
        displayColor = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, Vt.Vec3fArray([Gf.Vec3f(0.5, 0.7, 0.9)]))
        displayOpacity = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([0.8]))

        # Define the point cloud using the prim overload
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Points.*to.*Points.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            points = usdex.core.definePointCloud(
                prim, POINTS, widths=widths, normals=normals, displayColor=displayColor, displayOpacity=displayOpacity
            )

        # Verify the prim was created correctly
        self.assertTrue(points)
        self.assertEqual(points.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(points.GetPrim().GetTypeName(), "Points")

        # Verify the points attribute was set
        self.assertEqual(points.GetPointsAttr().Get(), POINTS)

        # Verify the optional arguments were set
        primvarsAPI = UsdGeom.PrimvarsAPI(points)

        widthsPrimvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.widths)
        self.assertTrue(widthsPrimvar.HasAuthoredValue())
        self.assertEqual(widthsPrimvar.Get(), widths.values())

        normalsPrimvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.normals)
        self.assertTrue(normalsPrimvar.HasAuthoredValue())
        self.assertEqual(normalsPrimvar.Get(), normals.values())

        displayColorPrimvar = points.GetDisplayColorPrimvar()
        self.assertTrue(displayColorPrimvar.HasAuthoredValue())
        self.assertEqual(displayColorPrimvar.Get(), displayColor.values())

        displayOpacityPrimvar = points.GetDisplayOpacityPrimvar()
        self.assertTrue(displayOpacityPrimvar.HasAuthoredValue())
        self.assertEqual(displayOpacityPrimvar.Get(), displayOpacity.values())

    def testDefinePointCloudPrimOverloadInvalidPrim(self):
        """Test the prim overload for definePointCloud with invalid prim."""
        # Test with invalid prim
        prim = Usd.Prim()
        self.assertFalse(prim.IsValid())

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            points = usdex.core.definePointCloud(prim, POINTS)
        self.assertFalse(points)

    def testDefinePointCloudPrimOverloadSinglePoint(self):
        stage = self.createTestStage()
        prim = stage.DefinePrim("/World/SinglePoint", "Points")

        # Create a single point
        singlePoint = Vt.Vec3fArray([Gf.Vec3f(1.0, 2.0, 3.0)])

        # Define the point cloud using the prim overload
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Points.*to.*Points.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            points = usdex.core.definePointCloud(prim, singlePoint)

        # Verify the prim was created correctly
        self.assertTrue(points)
        self.assertEqual(points.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(points.GetPrim().GetTypeName(), "Points")

        # Verify the points attribute was set
        self.assertEqual(points.GetPointsAttr().Get(), singlePoint)

    def testDefinePointCloudFromPrimTypeGuards(self):
        stage = self.createTestStage()

        # Test with non-Scope/Xform prim - should warn
        materialPrim = stage.DefinePrim("/World/MaterialPrim", "Material")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Material.*to.*Points.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            points = usdex.core.definePointCloud(materialPrim, POINTS)
        self.assertTrue(points)
        self.assertEqual(points.GetPrim().GetTypeName(), "Points")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            points = usdex.core.definePointCloud(scopePrim, POINTS)
        self.assertTrue(points)
        self.assertEqual(points.GetPrim().GetTypeName(), "Points")

        # Test with Xform prim - should not warn
        xformPrim = stage.DefinePrim("/World/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            points = usdex.core.definePointCloud(xformPrim, POINTS)
        self.assertTrue(points)
        self.assertEqual(points.GetPrim().GetTypeName(), "Points")
