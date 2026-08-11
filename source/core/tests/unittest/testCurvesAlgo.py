# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import usdex.core
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt
from utils.DefinePointBasedTestCaseMixin import DefinePointBasedTestCaseMixin

# Description of a simple basis curves prim with one curve
CURVE_VERTEX_COUNTS = Vt.IntArray([7])
POINTS = Vt.Vec3fArray(
    [
        Gf.Vec3f(0.0, 0.0, 0.0),
        Gf.Vec3f(1.0, 1.0, 0.0),
        Gf.Vec3f(1.0, 2.0, 0.0),
        Gf.Vec3f(0.0, 3.0, 0.0),
        Gf.Vec3f(-1.0, 4.0, 0.0),
        Gf.Vec3f(-1.0, 5.0, 0.0),
        Gf.Vec3f(0.0, 6.0, 0.0),
    ]
)

# Description of a simple basis curves prim with batched curves
BATCHED_CURVE_VERTEX_COUNTS = Vt.IntArray([7, 4, 10])
BATCHED_POINTS = Vt.Vec3fArray(
    [
        # curve 0
        Gf.Vec3f(0.0, 0.0, 0.0),
        Gf.Vec3f(1.0, 1.0, 0.0),
        Gf.Vec3f(1.0, 2.0, 0.0),
        Gf.Vec3f(0.0, 3.0, 0.0),
        Gf.Vec3f(-1.0, 4.0, 0.0),
        Gf.Vec3f(-1.0, 5.0, 0.0),
        Gf.Vec3f(0.0, 6.0, 0.0),
        # curve 1
        Gf.Vec3f(0.0, 0.0, 1.0),
        Gf.Vec3f(1.0, 1.0, 1.0),
        Gf.Vec3f(1.0, 2.0, 1.0),
        Gf.Vec3f(0.0, 3.0, 1.0),
        # curve 2
        Gf.Vec3f(0.0, 0.0, 2.0),
        Gf.Vec3f(1.0, 1.0, 2.0),
        Gf.Vec3f(1.0, 2.0, 2.0),
        Gf.Vec3f(0.0, 3.0, 2.0),
        Gf.Vec3f(-1.0, 4.0, 2.0),
        Gf.Vec3f(-1.0, 5.0, 2.0),
        Gf.Vec3f(0.0, 6.0, 2.0),
        Gf.Vec3f(1.0, 7.0, 2.0),
        Gf.Vec3f(1.0, 8.0, 2.0),
        Gf.Vec3f(0.0, 9.0, 2.0),
    ]
)


class DefineBasisCurvesTestCaseMixin(DefinePointBasedTestCaseMixin):

    # Partially configure the DefineFunctionTestCase
    schema = UsdGeom.BasisCurves
    typeName = "BasisCurves"
    requiredPropertyNames = set(
        [
            UsdGeom.Tokens.curveVertexCounts,
            UsdGeom.Tokens.points,
            UsdGeom.Tokens.type,
            UsdGeom.Tokens.wrap,
            UsdGeom.Tokens.extent,
        ]
    )

    def assertDefineFunctionSuccess(self, result):
        """Assert the common expectations of a successful call to defineBasisCurves"""
        super().assertDefineFunctionSuccess(result)

        # Assert that all required topology attributes are authored
        self.assertTrue(result.GetCurveVertexCountsAttr().IsAuthored())
        self.assertTrue(result.GetPointsAttr().IsAuthored())
        self.assertTrue(result.GetTypeAttr().IsAuthored())
        if result.GetTypeAttr().Get() == UsdGeom.Tokens.cubic:
            self.assertTrue(result.GetBasisAttr().IsAuthored())
        else:  # linear
            self.assertFalse(result.GetBasisAttr().IsAuthored())
        self.assertTrue(result.GetWrapAttr().IsAuthored())

        # Assert that a correct extent has been authored
        extent = UsdGeom.Boundable.ComputeExtentFromPlugins(result, Usd.TimeCode.Default())
        extentAttr = result.GetExtentAttr()
        self.assertTrue(extentAttr.IsAuthored())
        self.assertEqual(extentAttr.Get(), extent)

    def testWidths(self):
        # Widths are optional but if provided will be authored as a constant primvar
        stage = self.createTestStage()
        primvarName = UsdGeom.Tokens.widths
        parentPath = Sdf.Path("/World/Widths")

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
        values = Vt.FloatArray([0.5])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        primvar: UsdGeom.Primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        # If a value that matches the fallback value is specified a primvar will be authored
        path = parentPath.AppendChild("FallbackValue")
        values = Vt.FloatArray([1.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        # If a value less than 0 is specified a primvar will be authored
        path = parentPath.AppendChild("LessThanOneValue")
        values = Vt.FloatArray([-0.5])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)

        # If a value greater than 1 is specified a primvar will be authored
        path = parentPath.AppendChild("GreaterThanOneValue")
        values = Vt.FloatArray([1.5])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)

        # If an empty value is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the uniform size then a uniform primvar is authored
        path = parentPath.AppendChild("UniformValue")
        values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.uniform])])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)

        if UsdGeom.Tokens.varying in self.primvarSizes:
            # If the array size matches the varying size a varying primvar is authored
            path = parentPath.AppendChild("VaryingValue")
            values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.varying])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.varying, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, data)

            if self.primvarSizes[UsdGeom.Tokens.varying] != self.primvarSizes[UsdGeom.Tokens.vertex]:
                # If the array size matches the number of points a vertex primvar is authored
                path = parentPath.AppendChild("VertexValue")
                values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
                data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
                result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
                primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
                self.assertPrimvar(primvar, data)
        else:
            # If the array size matches the number of points a vertex primvar is authored
            path = parentPath.AppendChild("VertexValue")
            values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, data)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testIndexedWidths(self):
        # Display color can optional be indexed
        stage = self.createTestStage()
        primvarName = UsdGeom.Tokens.widths
        parentPath = Sdf.Path("/World/IndexedWidths")

        # If widths and widthsIndices are not specified no primvar is authored
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

        # If an empty array is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        values = Vt.FloatArray()
        indices = Vt.IntArray()
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the uniform size then a uniform primvar is authored
        path = parentPath.AppendChild("UniformValue")
        values = Vt.FloatArray([1])
        indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.uniform])])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, values, indices)
        result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)
        # native widths are never authored
        self.assertFalse(result.GetWidthsAttr().HasAuthoredValue())

        if UsdGeom.Tokens.varying in self.primvarSizes:
            # If the array size matches the varying size a varying primvar is authored
            path = parentPath.AppendChild("VaryingValue")
            values = Vt.FloatArray([1])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.varying])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.varying, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, data)

            if self.primvarSizes[UsdGeom.Tokens.varying] != self.primvarSizes[UsdGeom.Tokens.vertex]:
                # If the array size matches the number of points a vertex primvar is authored
                path = parentPath.AppendChild("VertexValue")
                values = Vt.FloatArray([1])
                indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
                data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
                result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
                primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
                self.assertPrimvar(primvar, data)
        else:
            # If the array size matches the number of points a vertex primvar is authored
            path = parentPath.AppendChild("VertexValue")
            values = Vt.FloatArray([1])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, data)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.FloatArray([1])
        indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but the index values are outside the range of the normals size then no prim is defined
        path = parentPath.AppendChild("IndexValuesGreaterThanRange")
        values = Vt.FloatArray([0.0, 1.0])
        indices = Vt.IntArray([0, 1, 2, 3, 0, 1, 2, 3])  # Face varying interpolation
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but there are values less than zero then no prim is defined
        path = parentPath.AppendChild("NegativeIndexValues")
        values = Vt.FloatArray([0.0, 1.0])
        indices = Vt.IntArray([-1, 0, 1, -1, 0, 1])  # Vertex interpolation
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid widths")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, widths=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))


class LinearBasisCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineBasisCurvesTestCaseMixin
    defineFunc = usdex.core.defineLinearBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: len(POINTS),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The point array must not be empty
        points = Vt.Vec3fArray()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid points")]):
            curves = usdex.core.defineLinearBasisCurves(stage, path, CURVE_VERTEX_COUNTS, points)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The wrap must be periodic or nonperiodic for linear curves
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineLinearBasisCurves(stage, path, CURVE_VERTEX_COUNTS, POINTS, wrap=UsdGeom.Tokens.pinned)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # There must be at least 2 verts per nonperiodic linear curve
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
        curveVertexCount = Vt.IntArray([1])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineLinearBasisCurves(stage, path, curveVertexCount, points)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # There must be at least 3 verts per periodic linear curve
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 0.0, 0.0)])
        curveVertexCount = Vt.IntArray([1])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineLinearBasisCurves(stage, path, curveVertexCount, points, wrap=UsdGeom.Tokens.periodic)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineLinearBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineLinear(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/Linear")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("ImplicitDefault")
        curves = usdex.core.defineLinearBasisCurves(stage, path, CURVE_VERTEX_COUNTS, POINTS)
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.linear)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)

        path = parentPath.AppendChild("Nonperiodic")
        curves = usdex.core.defineLinearBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            wrap=UsdGeom.Tokens.nonperiodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.linear)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)

        path = parentPath.AppendChild("Periodic")
        curves = usdex.core.defineLinearBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.linear)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedLinearBasisCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineLinearBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: len(BATCHED_POINTS),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # There must be at least 2 verts per nonperiodic linear curve
        points = BATCHED_POINTS[:-8]
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineLinearBasisCurves(stage, path, BATCHED_CURVE_VERTEX_COUNTS, points)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # There must be at least 3 verts per periodic linear curve
        points = BATCHED_POINTS[:-7]
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineLinearBasisCurves(stage, path, BATCHED_CURVE_VERTEX_COUNTS, points, wrap=UsdGeom.Tokens.periodic)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineLinearBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedLinear(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedLinear")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Nonperiodic")
        curves = usdex.core.defineLinearBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            wrap=UsdGeom.Tokens.nonperiodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.linear)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)

        path = parentPath.AppendChild("Periodic")
        curves = usdex.core.defineLinearBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.linear)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)


class NonperiodicBezierCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bezier])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int((CURVE_VERTEX_COUNTS[0] - 4) / 3 + 1 + 1),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The basis must be one of bezier, bspline, catmulRom for cubic curves
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                CURVE_VERTEX_COUNTS,
                POINTS,
                basis=UsdGeom.Tokens.hermite,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The wrap must be one of periodic, nonperiodic, or pinned for bezier curves
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                CURVE_VERTEX_COUNTS,
                POINTS,
                basis=UsdGeom.Tokens.bezier,
                wrap=UsdGeom.Tokens.hermite,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # There must be at least 4 verts per nonperiodic cubic curve
        points = POINTS[0:3]
        curveVertexCount = Vt.IntArray([3])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                curveVertexCount,
                points,
                basis=UsdGeom.Tokens.bezier,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # There must be (vertCount - 4) % 3 verts per nonperiodic bezier curve
        points = POINTS[:-1]
        curveVertexCount = Vt.IntArray([6])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCount, points, basis=UsdGeom.Tokens.bezier)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineNonperiodicBezier(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/Bezier")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Nonperiodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            basis=UsdGeom.Tokens.bezier,
            wrap=UsdGeom.Tokens.nonperiodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bezier)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedNonperiodicBezierCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS, UsdGeom.Tokens.bezier])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int(sum([x - 4 for x in BATCHED_CURVE_VERTEX_COUNTS]) / 3 + (2 * len(BATCHED_CURVE_VERTEX_COUNTS))),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedNonperiodicBezier(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedBezier")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Nonperiodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            basis=UsdGeom.Tokens.bezier,
            wrap=UsdGeom.Tokens.nonperiodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bezier)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)

        path = parentPath.AppendChild("Periodic")
        curveVertexCounts = Vt.IntArray([6, 9])
        points = Vt.Vec3fArray(list(BATCHED_POINTS[:6]) + list(BATCHED_POINTS[11:-1]))
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            curveVertexCounts,
            points,
            basis=UsdGeom.Tokens.bezier,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bezier)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), curveVertexCounts)
        self.assertEqual(curves.GetPointsAttr().Get(), points)


class PeriodicBezierCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    curveVertexCounts = Vt.IntArray([6])
    points = POINTS[:-1]

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([curveVertexCounts, points, UsdGeom.Tokens.bezier, UsdGeom.Tokens.periodic])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(curveVertexCounts),
        UsdGeom.Tokens.varying: int((curveVertexCounts[0]) / 3),
        UsdGeom.Tokens.vertex: len(points),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The number of vertices must be divisible by 3 per periodic bezier curve
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                CURVE_VERTEX_COUNTS,
                POINTS,
                basis=UsdGeom.Tokens.bezier,
                wrap=UsdGeom.Tokens.periodic,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefinePeriodicBezier(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/Bezier")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Periodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            self.curveVertexCounts,
            self.points,
            basis=UsdGeom.Tokens.bezier,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bezier)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), self.curveVertexCounts)
        self.assertEqual(curves.GetPointsAttr().Get(), self.points)


class BatchedPeriodicBezierCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    curveVertexCounts = Vt.IntArray([6, 9])
    points = Vt.Vec3fArray(list(BATCHED_POINTS[:6]) + list(BATCHED_POINTS[11:-1]))

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([curveVertexCounts, points, UsdGeom.Tokens.bezier, UsdGeom.Tokens.periodic])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(curveVertexCounts),
        UsdGeom.Tokens.varying: int(sum(curveVertexCounts) / 3),
        UsdGeom.Tokens.vertex: len(points),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedPeriodicBezier(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedBezier")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Periodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            self.curveVertexCounts,
            self.points,
            basis=UsdGeom.Tokens.bezier,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bezier)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), self.curveVertexCounts)
        self.assertEqual(curves.GetPointsAttr().Get(), self.points)


class PinnedBezierCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bezier, UsdGeom.Tokens.pinned])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int((CURVE_VERTEX_COUNTS[0] - 4) / 3 + 1 + 1),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # There must be at least 4 verts per pinned bezier curve
        points = POINTS[:3]
        curveVertexCount = Vt.IntArray([3])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                curveVertexCount,
                points,
                basis=UsdGeom.Tokens.bezier,
                wrap=UsdGeom.Tokens.pinned,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefinePinnedBezier(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/Bezier")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Pinned")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            basis=UsdGeom.Tokens.bezier,
            wrap=UsdGeom.Tokens.pinned,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bezier)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.pinned)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedPinnedBezierCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS, UsdGeom.Tokens.bezier, UsdGeom.Tokens.pinned])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int(sum([x - 4 for x in BATCHED_CURVE_VERTEX_COUNTS]) / 3 + (2 * len(BATCHED_CURVE_VERTEX_COUNTS))),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedPinnedBezier(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedBezier")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Pinned")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            basis=UsdGeom.Tokens.bezier,
            wrap=UsdGeom.Tokens.pinned,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bezier)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.pinned)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)


class NonperiodicBsplineCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bspline])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int((CURVE_VERTEX_COUNTS[0] - 4) / 1 + 1 + 1),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # There must be at least 4 verts per nonperiodic cubic curve
        points = POINTS[0:3]
        curveVertexCount = Vt.IntArray([3])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                curveVertexCount,
                points,
                basis=UsdGeom.Tokens.bezier,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineNonperiodicBSpline(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/Bspline")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Nonperiodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            basis=UsdGeom.Tokens.bspline,
            wrap=UsdGeom.Tokens.nonperiodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bspline)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedNonperiodicBsplineCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS, UsdGeom.Tokens.bspline])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int(sum([x - 4 for x in BATCHED_CURVE_VERTEX_COUNTS]) / 1 + (2 * len(BATCHED_CURVE_VERTEX_COUNTS))),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedNonperiodicBSpline(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedBspline")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Nonperiodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            basis=UsdGeom.Tokens.bspline,
            wrap=UsdGeom.Tokens.nonperiodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bspline)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)


class PeriodicBsplineCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bspline, UsdGeom.Tokens.periodic])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int((CURVE_VERTEX_COUNTS[0]) / 1),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # There must be at least 2 verts per periodic bspline / catmullRom curve
        points = POINTS[0:1]
        curveVertexCount = Vt.IntArray([1])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                curveVertexCount,
                points,
                basis=UsdGeom.Tokens.catmullRom,
                wrap=UsdGeom.Tokens.periodic,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefinePeriodicBSpline(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/Bspline")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Periodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            basis=UsdGeom.Tokens.bspline,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bspline)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedPeriodicBsplineCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS, UsdGeom.Tokens.bspline, UsdGeom.Tokens.periodic])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int(sum(BATCHED_CURVE_VERTEX_COUNTS) / 1),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedPeriodicBSpline(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedBspline")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Periodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            basis=UsdGeom.Tokens.bspline,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bspline)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)


class PinnedBsplineCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bspline, UsdGeom.Tokens.pinned])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # There must be at least 2 verts per pinned bspline or catmullRom curve
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
        curveVertexCount = Vt.IntArray([1])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                curveVertexCount,
                points,
                basis=UsdGeom.Tokens.bspline,
                wrap=UsdGeom.Tokens.pinned,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefinePinnedBSpline(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/Bspline")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Pinned")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            basis=UsdGeom.Tokens.bspline,
            wrap=UsdGeom.Tokens.pinned,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bspline)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.pinned)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedPinnedBsplineCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS, UsdGeom.Tokens.bspline, UsdGeom.Tokens.pinned])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedPinnedBSpline(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedBspline")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Pinned")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            basis=UsdGeom.Tokens.bspline,
            wrap=UsdGeom.Tokens.pinned,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bspline)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.pinned)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)


class NonperiodicCatmullRomCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.catmullRom])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int((CURVE_VERTEX_COUNTS[0] - 4) / 1 + 1 + 1),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # There must be at least 4 verts per nonperiodic cubic curve
        points = POINTS[0:3]
        curveVertexCount = Vt.IntArray([3])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                curveVertexCount,
                points,
                basis=UsdGeom.Tokens.bezier,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineNonperiodicCatmullRom(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/CatmullRom")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Nonperiodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            basis=UsdGeom.Tokens.catmullRom,
            wrap=UsdGeom.Tokens.nonperiodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.catmullRom)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedNonperiodicCatmullRomCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS, UsdGeom.Tokens.catmullRom])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int(sum([x - 4 for x in BATCHED_CURVE_VERTEX_COUNTS]) / 1 + (2 * len(BATCHED_CURVE_VERTEX_COUNTS))),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedNonperiodicCatmullRom(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedCatmullRom")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Nonperiodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            basis=UsdGeom.Tokens.catmullRom,
            wrap=UsdGeom.Tokens.nonperiodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.catmullRom)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)


class PeriodicCatmullRomCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.catmullRom, UsdGeom.Tokens.periodic])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int((CURVE_VERTEX_COUNTS[0]) / 1),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # There must be at least 2 verts per periodic bspline / catmullRom curve
        points = POINTS[0:1]
        curveVertexCount = Vt.IntArray([1])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                curveVertexCount,
                points,
                basis=UsdGeom.Tokens.catmullRom,
                wrap=UsdGeom.Tokens.periodic,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefinePeriodicCatmullRom(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/CatmullRom")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Periodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            basis=UsdGeom.Tokens.catmullRom,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.catmullRom)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedPeriodicCatmullRomCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS, UsdGeom.Tokens.catmullRom, UsdGeom.Tokens.periodic])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.varying: int(sum(BATCHED_CURVE_VERTEX_COUNTS) / 1),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedPeriodicCatmullRom(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedCatmullRom")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Periodic")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            basis=UsdGeom.Tokens.catmullRom,
            wrap=UsdGeom.Tokens.periodic,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.catmullRom)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)


class PinnedCatmullRomCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.catmullRom, UsdGeom.Tokens.pinned])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.vertex: len(POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # There must be at least 2 verts per pinned bspline or catmullRom curve
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
        curveVertexCount = Vt.IntArray([1])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(
                stage,
                path,
                curveVertexCount,
                points,
                basis=UsdGeom.Tokens.bspline,
                wrap=UsdGeom.Tokens.pinned,
            )
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefinePinnedCatmullRom(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/CatmullRom")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Pinned")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            CURVE_VERTEX_COUNTS,
            POINTS,
            basis=UsdGeom.Tokens.catmullRom,
            wrap=UsdGeom.Tokens.pinned,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.catmullRom)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.pinned)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)


class BatchedPinnedCatmullRomCurvesTestCase(DefineBasisCurvesTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCubicBasisCurves
    requiredArgs = tuple([BATCHED_CURVE_VERTEX_COUNTS, BATCHED_POINTS, UsdGeom.Tokens.catmullRom, UsdGeom.Tokens.pinned])
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(BATCHED_CURVE_VERTEX_COUNTS),
        UsdGeom.Tokens.vertex: len(BATCHED_POINTS),
    }

    def testInvalidTopology(self):
        # Invalid topology will result in an invalid schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The sum of the curveVertexCounts must equal the count of the points
        curveVertexCounts = Vt.IntArray([7, 4, 11])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            curves = usdex.core.defineCubicBasisCurves(stage, path, curveVertexCounts, BATCHED_POINTS)
        self.assertDefineFunctionFailure(curves)
        self.assertFalse(stage.GetPrimAtPath(path))

    def testDefineBatchedCatmullRom(self):
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/BatchedCatmullRom")
        UsdGeom.Xform.Define(stage, parentPath)

        path = parentPath.AppendChild("Pinned")
        curves = usdex.core.defineCubicBasisCurves(
            stage,
            path,
            BATCHED_CURVE_VERTEX_COUNTS,
            BATCHED_POINTS,
            basis=UsdGeom.Tokens.catmullRom,
            wrap=UsdGeom.Tokens.pinned,
        )
        self.assertDefineFunctionSuccess(curves)
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.catmullRom)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.pinned)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), BATCHED_CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), BATCHED_POINTS)


class CurvesAlgoPrimOverloadTest(usdex.test.TestCase):
    """Test prim overloads for curves define functions."""

    def createTestStage(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.centimeters)
        return stage

    def testDefineLinearBasisCurvesPrimOverload(self):
        stage = self.createTestStage()

        # Create a prim first
        path = Sdf.Path("/World/LinearCurves")
        prim = stage.DefinePrim(path)
        self.assertTrue(prim.IsValid())

        # Test the prim overload
        curves = usdex.core.defineLinearBasisCurves(prim, CURVE_VERTEX_COUNTS, POINTS)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim(), prim)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.linear)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)

    def testDefineLinearBasisCurvesPrimOverloadWithWrap(self):
        stage = self.createTestStage()

        # Create a prim first
        path = Sdf.Path("/World/LinearCurvesPeriodic")
        prim = stage.DefinePrim(path)
        self.assertTrue(prim.IsValid())

        # Test the prim overload with wrap parameter
        curves = usdex.core.defineLinearBasisCurves(prim, CURVE_VERTEX_COUNTS, POINTS, wrap=UsdGeom.Tokens.periodic)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim(), prim)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.linear)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)

    def testDefineLinearBasisCurvesPrimOverloadInvalidPrim(self):
        # Test with invalid prim
        prim = Usd.Prim()
        self.assertFalse(prim.IsValid())

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            curves = usdex.core.defineLinearBasisCurves(prim, CURVE_VERTEX_COUNTS, POINTS)
        self.assertFalse(curves)

    def testDefineCubicBasisCurvesPrimOverload(self):
        stage = self.createTestStage()

        # Create a prim first
        path = Sdf.Path("/World/CubicCurves")
        prim = stage.DefinePrim(path)
        self.assertTrue(prim.IsValid())

        # Test the prim overload
        curves = usdex.core.defineCubicBasisCurves(prim, CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bezier)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim(), prim)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bezier)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.nonperiodic)
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)

    def testDefineCubicBasisCurvesPrimOverloadWithWrap(self):
        stage = self.createTestStage()

        # Create a prim first
        path = Sdf.Path("/World/CubicCurvesPinned")
        prim = stage.DefinePrim(path)
        self.assertTrue(prim.IsValid())

        # Test the prim overload with wrap parameter
        curves = usdex.core.defineCubicBasisCurves(prim, CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bspline, UsdGeom.Tokens.pinned)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim(), prim)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")
        self.assertEqual(curves.GetTypeAttr().Get(), UsdGeom.Tokens.cubic)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.bspline)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.pinned)

    def testDefineCubicBasisCurvesPrimOverloadInvalidPrim(self):
        # Test with invalid prim
        prim = Usd.Prim()
        self.assertFalse(prim.IsValid())

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            curves = usdex.core.defineCubicBasisCurves(prim, CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bezier)
        self.assertFalse(curves)

    def testDefineCubicBasisCurvesPrimOverloadWithOptionalArgs(self):
        stage = self.createTestStage()
        prim = stage.DefinePrim("/World/CubicCurvesWithOptionalArgs", "BasisCurves")

        # Create test data for optional arguments
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, Vt.Vec3fArray([Gf.Vec3f(0, 1, 0)] * len(POINTS)))
        displayColor = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, Vt.Vec3fArray([Gf.Vec3f(0.5, 0.7, 0.9)]))
        widths = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.5]))

        # Define the cubic curves with optional arguments
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*BasisCurves.*to.*BasisCurves.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            curves = usdex.core.defineCubicBasisCurves(
                prim,
                CURVE_VERTEX_COUNTS,
                POINTS,
                UsdGeom.Tokens.catmullRom,
                UsdGeom.Tokens.periodic,
                widths=widths,
                normals=normals,
                displayColor=displayColor,
            )

        # Verify the prim was created correctly
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")

        # Verify the curve attributes were set
        self.assertEqual(curves.GetCurveVertexCountsAttr().Get(), CURVE_VERTEX_COUNTS)
        self.assertEqual(curves.GetPointsAttr().Get(), POINTS)
        self.assertEqual(curves.GetBasisAttr().Get(), UsdGeom.Tokens.catmullRom)
        self.assertEqual(curves.GetWrapAttr().Get(), UsdGeom.Tokens.periodic)

        # Verify the optional arguments were set
        primvarsAPI = UsdGeom.PrimvarsAPI(curves)

        widthsPrimvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.widths)
        self.assertTrue(widthsPrimvar.HasAuthoredValue())
        self.assertEqual(widthsPrimvar.Get(), widths.values())

        normalsPrimvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.normals)
        self.assertTrue(normalsPrimvar.HasAuthoredValue())
        self.assertEqual(normalsPrimvar.Get(), normals.values())

        displayColorPrimvar = curves.GetDisplayColorPrimvar()
        self.assertTrue(displayColorPrimvar.HasAuthoredValue())
        self.assertEqual(displayColorPrimvar.Get(), displayColor.values())

    def testDefineLinearBasisCurvesPrimOverloadTypeGuards(self):
        stage = self.createTestStage()

        # Test with non-Scope/Xform prim - should warn
        materialPrim = stage.DefinePrim("/World/MaterialPrim", "Material")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Material.*to.*BasisCurves.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            curves = usdex.core.defineLinearBasisCurves(materialPrim, CURVE_VERTEX_COUNTS, POINTS)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            curves = usdex.core.defineLinearBasisCurves(scopePrim, CURVE_VERTEX_COUNTS, POINTS)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")

        # Test with Xform prim - should not warn
        xformPrim = stage.DefinePrim("/World/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            curves = usdex.core.defineLinearBasisCurves(xformPrim, CURVE_VERTEX_COUNTS, POINTS)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")

    def testDefineCubicBasisCurvesPrimOverloadTypeGuards(self):
        stage = self.createTestStage()

        # Test with non-Scope/Xform prim - should warn
        materialPrim = stage.DefinePrim("/World/MaterialPrim", "Material")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Material.*to.*BasisCurves.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            curves = usdex.core.defineCubicBasisCurves(materialPrim, CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bezier)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            curves = usdex.core.defineCubicBasisCurves(scopePrim, CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bezier)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")

        # Test with Xform prim - should not warn
        xformPrim = stage.DefinePrim("/World/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            curves = usdex.core.defineCubicBasisCurves(xformPrim, CURVE_VERTEX_COUNTS, POINTS, UsdGeom.Tokens.bezier)
        self.assertTrue(curves)
        self.assertEqual(curves.GetPrim().GetTypeName(), "BasisCurves")
