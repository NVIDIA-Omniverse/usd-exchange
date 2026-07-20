# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import Tuple

import usdex.core
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt

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


class PrimvarDataTestCase(usdex.test.TestCase):
    @staticmethod
    def interpolations() -> Tuple[str]:
        return (UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying, UsdGeom.Tokens.faceVarying, UsdGeom.Tokens.uniform, UsdGeom.Tokens.constant)

    def assertPrimvarData(self, cls, interpolation, values, elementSize=-1):
        data = cls(interpolation, values, elementSize=elementSize)
        self.assertEqual(data.interpolation(), interpolation)
        self.assertEqual(data.values(), values)
        self.assertEqual(data.elementSize(), elementSize)
        if elementSize > 0:
            self.assertEqual(data.effectiveSize(), len(values) / elementSize)
        else:
            self.assertEqual(data.effectiveSize(), len(values))
        self.assertFalse(data.hasIndices())
        self.assertTrue(data.isValid())

    def assertIndexedPrimvarData(self, cls, interpolation, values, indices: Vt.IntArray, elementSize=-1):
        data = cls(interpolation, values, indices, elementSize=elementSize)
        self.assertEqual(data.interpolation(), interpolation)
        self.assertEqual(data.values(), values)
        self.assertEqual(data.elementSize(), elementSize)
        self.assertTrue(data.hasIndices())
        self.assertEqual(data.indices(), indices)
        if elementSize > 0:
            self.assertEqual(data.effectiveSize(), len(indices) / elementSize)
        else:
            self.assertEqual(data.effectiveSize(), len(indices))
        self.assertTrue(data.isValid())

    def testValues(self):
        for interpolation in self.interpolations():
            floats = Vt.FloatArray([-1.0, -0.5, 1.5])
            self.assertPrimvarData(usdex.core.FloatPrimvarData, interpolation, floats)

            ints = Vt.IntArray([-1, 0, 1])
            self.assertPrimvarData(usdex.core.IntPrimvarData, interpolation, ints)

            longs = Vt.Int64Array([-1, 0, 1])
            self.assertPrimvarData(usdex.core.Int64PrimvarData, interpolation, longs)

            vectors = Vt.Vec3fArray([Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 1, 0), Gf.Vec3f(0, 1, 1)])
            self.assertPrimvarData(usdex.core.Vec3fPrimvarData, interpolation, vectors)

            coords = Vt.Vec2fArray([Gf.Vec2f(0, 0), Gf.Vec2f(0, 1), Gf.Vec2f(1, 1)])
            self.assertPrimvarData(usdex.core.Vec2fPrimvarData, interpolation, coords)

            strings = Vt.StringArray(["a", "foo"])
            self.assertPrimvarData(usdex.core.StringPrimvarData, interpolation, strings)

            tokens = Vt.TokenArray([UsdGeom.Tokens.vertex, UsdGeom.Tokens.none])
            self.assertPrimvarData(usdex.core.TokenPrimvarData, interpolation, tokens)

        # no interpolation
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        data = usdex.core.FloatPrimvarData("", values)
        self.assertFalse(data.isValid())

        # bad interpolation
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.cubic, values)
        self.assertFalse(data.isValid())

        # mismatched data types
        self.assertRaises(TypeError, usdex.core.IntPrimvarData, UsdGeom.Tokens.vertex, values)

    def testIndices(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        for interpolation in self.interpolations():
            self.assertIndexedPrimvarData(usdex.core.FloatPrimvarData, interpolation, values, indices)

        # out of range
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, Vt.IntArray([0, 1, 3]))
        self.assertFalse(data.isValid())
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, Vt.IntArray([0, -1, 2]))
        self.assertFalse(data.isValid())

    def testElementSize(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])

        for interpolation in self.interpolations():
            # just one element
            self.assertPrimvarData(usdex.core.FloatPrimvarData, interpolation, values, elementSize=3)
            self.assertIndexedPrimvarData(usdex.core.FloatPrimvarData, interpolation, values, indices, elementSize=3)

            # no elements
            self.assertPrimvarData(usdex.core.FloatPrimvarData, interpolation, values, elementSize=0)
            self.assertIndexedPrimvarData(usdex.core.FloatPrimvarData, interpolation, values, indices, elementSize=0)
            self.assertPrimvarData(usdex.core.FloatPrimvarData, interpolation, values, elementSize=-2)
            self.assertIndexedPrimvarData(usdex.core.FloatPrimvarData, interpolation, values, indices, elementSize=-2)

        notEnoughValues = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, elementSize=4)
        self.assertFalse(notEnoughValues.isValid())

        notEnoughIndices = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices, elementSize=2)
        self.assertFalse(notEnoughIndices.isValid())

        wrongNumberOfValues = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, elementSize=2)
        self.assertFalse(wrongNumberOfValues.isValid())

        wrongNumberOfIndices = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices, elementSize=2)
        self.assertFalse(wrongNumberOfIndices.isValid())

    def testIsIdentical(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        a = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        b = a
        self.assertTrue(a.isIdentical(b))
        self.assertTrue(b.isIdentical(a))

        sameValues = Vt.FloatArray([-1.0, -0.5, 1.5])
        c = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, sameValues, indices)
        self.assertFalse(a.isIdentical(c))
        self.assertFalse(c.isIdentical(a))

        sameIndices = Vt.IntArray([0, 1, 2])
        d = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, sameIndices)
        self.assertFalse(a.isIdentical(d))
        self.assertFalse(d.isIdentical(a))

    def testEquality(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        a = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        b = a
        self.assertEqual(a, b)

        sameValues = Vt.FloatArray([-1.0, -0.5, 1.5])
        c = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, sameValues, indices)
        self.assertEqual(a, c)

        sameIndices = Vt.IntArray([0, 1, 2])
        d = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, sameIndices)
        self.assertEqual(a, d)

    def testInequality(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        original = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        differentInterpolation = usdex.core.FloatPrimvarData(UsdGeom.Tokens.varying, values, indices)
        self.assertNotEqual(original, differentInterpolation)
        noIndices = usdex.core.FloatPrimvarData(UsdGeom.Tokens.varying, values)
        self.assertNotEqual(original, noIndices)
        differentData = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, Vt.FloatArray([-1.0, -0.5, 1.5, 2.0]), indices)
        self.assertNotEqual(original, differentData)
        differentIndices = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, Vt.IntArray([2, 1, 0]))
        self.assertNotEqual(original, differentIndices)
        differentElementSize = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices, elementSize=3)
        self.assertNotEqual(original, differentElementSize)

    def testGetPrimvarData(self):
        stage = Usd.Stage.CreateInMemory()
        path = Sdf.Path("/Prim")
        scope = UsdGeom.Scope.Define(stage, path)
        primvarsApi = UsdGeom.PrimvarsAPI(scope.GetPrim())
        self.assertTrue(primvarsApi)
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        primvar = primvarsApi.CreateIndexedPrimvar("test", Sdf.ValueTypeNames.FloatArray, values, indices, UsdGeom.Tokens.vertex, 3)
        data = usdex.core.FloatPrimvarData.getPrimvarData(primvar)
        self.assertEqual(data.interpolation(), UsdGeom.Tokens.vertex)
        self.assertEqual(data.values(), values)
        self.assertEqual(data.indices(), indices)
        self.assertEqual(data.elementSize(), 3)
        self.assertTrue(data.isValid())

        usdex.core.configureStage(stage, "Prim", self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        self.assertIsValidUsd(stage)

    def testSetPrimvar(self):
        stage = Usd.Stage.CreateInMemory()
        path = Sdf.Path("/Prim")
        scope = UsdGeom.Scope.Define(stage, path)
        primvarsApi = UsdGeom.PrimvarsAPI(scope.GetPrim())
        self.assertTrue(primvarsApi)
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        primvar = primvarsApi.CreatePrimvar("test", Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.vertex)
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, values, indices, elementSize=3)
        self.assertTrue(data.setPrimvar(primvar))
        self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.uniform)
        self.assertEqual(primvar.Get(), values)
        self.assertEqual(primvar.GetIndices(), indices)
        self.assertEqual(primvar.GetElementSize(), 3)

        usdex.core.configureStage(stage, "Prim", self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        self.assertIsValidUsd(stage)

    def testTimeSamples(self):
        stage = Usd.Stage.CreateInMemory()
        path = Sdf.Path("/Prim")
        scope = UsdGeom.Scope.Define(stage, path)
        primvarsApi = UsdGeom.PrimvarsAPI(scope.GetPrim())
        self.assertTrue(primvarsApi)
        indices = Vt.IntArray([0, 1, 2])
        primvar = primvarsApi.CreatePrimvar("test", Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.vertex)

        for time in (Usd.TimeCode.EarliestTime(), 0, 0.25, 1, 10.5):
            values = Vt.FloatArray([-1.0, -0.5, 1.5])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, values, indices)
            self.assertTrue(data.setPrimvar(primvar, time))
            self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.uniform)
            self.assertEqual(primvar.Get(time), values)
            self.assertEqual(primvar.GetIndices(time), indices)
            self.assertFalse(primvar.HasAuthoredElementSize())

        for time in (Usd.TimeCode.EarliestTime(), 0, 0.25, 1, 10.5):
            data = usdex.core.FloatPrimvarData.getPrimvarData(primvar, time)
            self.assertEqual(data.interpolation(), UsdGeom.Tokens.uniform)
            self.assertEqual(data.values(), primvar.Get(time))
            self.assertEqual(data.indices(), primvar.GetIndices(time))
            self.assertEqual(data.elementSize(), -1)
            self.assertTrue(data.isValid())

        usdex.core.configureStage(stage, "Prim", self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        self.assertIsValidUsd(stage)

    def testStr(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices, elementSize=3)
        self.assertEqual(str(data), 'usdex.core.FloatPrimvarData(interpolation="vertex", values=[-1, -0.5, 1.5], indices=[0, 1, 2], elementSize=3)')

    def testIndex(self):
        # Non-indexed primvar data can be indexed
        values = Vt.FloatArray([0.0, 0.0, 1.0, 1.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
        self.assertTrue(data.index())

        self.assertTrue(data.hasIndices())
        self.assertEqual(data.values(), Vt.FloatArray([0.0, 1.0]))
        self.assertEqual(data.indices(), Vt.IntArray([0, 0, 1, 1]))

        # The pxr.Gf types are supported
        values = Vt.Vec3fArray([Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 1, 0), Gf.Vec3f(0, 0, 0)])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values)
        self.assertTrue(data.index())

        self.assertTrue(data.hasIndices())
        self.assertEqual(data.values(), Vt.Vec3fArray([Gf.Vec3f(0, 0, 0), Gf.Vec3f(0, 1, 0)]))
        self.assertEqual(data.indices(), Vt.IntArray([0, 1, 0]))

        # The std types are supported
        values = Vt.StringArray(["red", "green", "blue", "red", "green", "blue"])
        data = usdex.core.StringPrimvarData(UsdGeom.Tokens.vertex, values)
        self.assertTrue(data.index())

        self.assertTrue(data.hasIndices())
        self.assertEqual(data.values(), Vt.StringArray(["red", "green", "blue"]))
        self.assertEqual(data.indices(), Vt.IntArray([0, 1, 2, 0, 1, 2]))

        # Primvar data that has an element size will not be indexed as the correct strategy for this is unclear
        values = Vt.FloatArray([0.0, 1.0, 0.0, 1.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, elementSize=2)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*due to element size")]):
            self.assertFalse(data.index())

        # Non-optimal indexed primvar data can be indexed and will become optimal
        values = Vt.FloatArray([0.0, 1.0, 0.0])
        indices = Vt.IntArray([0, 0, 1, 1, 2, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        self.assertTrue(data.index())

        self.assertTrue(data.hasIndices())
        self.assertEqual(data.values(), Vt.FloatArray([0.0, 1.0]))
        self.assertEqual(data.indices(), Vt.IntArray([0, 0, 1, 1, 0, 0]))

        # Data that is already indexed efficiently will not be changed
        values = Vt.FloatArray([0.0, 1.0])
        indices = Vt.IntArray([0, 0, 1, 1, 0, 0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        self.assertFalse(data.index())

        self.assertTrue(data.hasIndices())
        self.assertEqual(data.values(), Vt.FloatArray([0.0, 1.0]))
        self.assertEqual(data.indices(), Vt.IntArray([0, 0, 1, 1, 0, 0]))

        # We do not reorder indices and values as part of indexing, even if it does not match the indexing we would compute
        values = Vt.FloatArray([1.0, 0.0])
        indices = Vt.IntArray([1, 1, 0, 0, 1, 1])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        self.assertFalse(data.index())

        self.assertTrue(data.hasIndices())
        self.assertEqual(data.values(), Vt.FloatArray([1.0, 0.0]))
        self.assertEqual(data.indices(), Vt.IntArray([1, 1, 0, 0, 1, 1]))

        # Non-indexed primvar data will not be indexed if there are no duplicate values
        values = Vt.FloatArray([0.0, 1.0, 2.0, 3.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
        self.assertFalse(data.index())

        self.assertFalse(data.hasIndices())

        # Primvar data with invalid indices cannot be indexed because the flattened values cannot be computed
        # However the invalid indices will not be changed
        values = Vt.FloatArray([0.0, 1.0])
        indices = Vt.IntArray([0, 0, 1, 1, 2, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*existing indices outside the range of existing values"),
            ],
        ):
            self.assertFalse(data.index())

        self.assertTrue(data.hasIndices())
        self.assertEqual(data.values(), Vt.FloatArray([0.0, 1.0]))
        self.assertEqual(data.indices(), Vt.IntArray([0, 0, 1, 1, 2, 2]))

    def testHasUnindexedValues(self):
        # Non-indexed primvar data
        values = Vt.FloatArray([0.0, 1.0, 2.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
        self.assertFalse(data.hasUnindexedValues())

        # Indexed primvar data
        values = Vt.FloatArray([0.0, 1.0, 2.0])
        indices = Vt.IntArray([0, 1, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        self.assertFalse(data.hasUnindexedValues())

        # Indexed primvar data with unused values
        values = Vt.FloatArray([0.0, 1.0, 2.0])
        indices = Vt.IntArray([0, 1, 1])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        self.assertTrue(data.hasUnindexedValues())

        # Non-indexed primvar data (Gf.Vec3f)
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 1.0, 1.0), Gf.Vec3f(2.0, 2.0, 2.0)])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values)
        self.assertFalse(data.hasUnindexedValues())

        # Indexed primvar data (Gf.Vec3f)
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 1.0, 1.0), Gf.Vec3f(2.0, 2.0, 2.0)])
        indices = Vt.IntArray([0, 1, 2])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        self.assertFalse(data.hasUnindexedValues())

        # Indexed primvar data with unused values (Gf.Vec3f)
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 1.0, 1.0), Gf.Vec3f(2.0, 2.0, 2.0)])
        indices = Vt.IntArray([0, 2, 2])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        self.assertTrue(data.hasUnindexedValues())


class PrimvarDataCreateTestCase(usdex.test.TestCase):
    def setUp(self):
        super().setUp()
        self.stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(self.stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = self.stage.GetDefaultPrim()
        self.scope = usdex.core.defineScope(defaultPrim, "foo")
        self.prim = self.scope.GetPrim()

    def assertPrimvarIndicesBlocked(self, primvar):
        """Assert that a non-indexed primvar has blocked indices via ``setPrimvar()``."""
        self.assertFalse(primvar.IsIndexed())
        indicesAttr = primvar.GetIndicesAttr()
        self.assertTrue(indicesAttr.IsAuthored())
        self.assertFalse(indicesAttr.HasAuthoredValue())

    def testConstantScalar(self):
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, Vt.Vec3fArray([Gf.Vec3f(0, 1, 2)]))
        self.assertTrue(data.createPrimvar(self.prim, "foo"))
        self.assertIsInstance(data, usdex.core.Vec3fPrimvarData)
        self.assertEqual(data.interpolation(), UsdGeom.Tokens.constant)
        self.assertEqual(data.values(), Vt.Vec3fArray([Gf.Vec3f(0, 1, 2)]))
        self.assertTrue(data.isValid())

        primvar = UsdGeom.PrimvarsAPI(self.prim).GetPrimvar("foo")
        self.assertTrue(primvar)
        self.assertEqual(primvar.GetTypeName(), Sdf.ValueTypeNames.Float3Array)
        self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.constant)
        self.assertEqual(primvar.Get(), data.values())

        self.assertIsValidUsd(self.stage)

    def testConstantSingleElementArray(self):
        values = Vt.FloatArray([0.5])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        self.assertTrue(data.createPrimvar(self.prim, "opacity"))
        self.assertTrue(data.isValid())
        self.assertIsInstance(data, usdex.core.FloatPrimvarData)
        self.assertEqual(data.interpolation(), UsdGeom.Tokens.constant)
        self.assertEqual(data.values(), values)

        self.assertIsValidUsd(self.stage)

    def testExplicitInterpolation(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
        self.assertTrue(data.createPrimvar(self.prim, "widths"))
        self.assertTrue(data.isValid())
        self.assertIsInstance(data, usdex.core.FloatPrimvarData)
        self.assertEqual(data.interpolation(), UsdGeom.Tokens.vertex)
        self.assertEqual(data.values(), values)

        primvar = UsdGeom.PrimvarsAPI(self.prim).GetPrimvar("widths")
        self.assertEqual(primvar.Get(), values)

        self.assertIsValidUsd(self.stage)

    def testIndexedPrimvar(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        self.assertTrue(data.createPrimvar(self.prim, "indexed"))
        self.assertTrue(data.isValid())
        self.assertIsInstance(data, usdex.core.FloatPrimvarData)
        self.assertTrue(data.hasIndices())
        self.assertEqual(data.indices(), indices)

        primvar = UsdGeom.PrimvarsAPI(self.prim).GetPrimvar("indexed")
        self.assertTrue(primvar.IsIndexed())
        self.assertEqual(primvar.GetIndices(), indices)

        self.assertIsValidUsd(self.stage)

    def testSupportedScalarTypes(self):
        cases = (
            (Vt.FloatArray([1.5]), usdex.core.FloatPrimvarData, None),
            (Vt.IntArray([2]), usdex.core.IntPrimvarData, None),
            (Vt.Int64Array([2**40]), usdex.core.Int64PrimvarData, None),
            (Vt.StringArray(["label"]), usdex.core.StringPrimvarData, None),
            (Vt.Vec2fArray([Gf.Vec2f(0, 1)]), usdex.core.Vec2fPrimvarData, None),
            (Vt.Vec3fArray([Gf.Vec3f(0, 1, 2)]), usdex.core.Vec3fPrimvarData, None),
            (Vt.Vec3fArray([Gf.Vec3f(0.1, 0.2, 0.3)]), usdex.core.Vec3fPrimvarData, Sdf.ValueTypeNames.Color3fArray),
            (Vt.Vec3fArray([Gf.Vec3f(0, 1, 0)]), usdex.core.Vec3fPrimvarData, Sdf.ValueTypeNames.Normal3fArray),
            (Vt.Vec3fArray([Gf.Vec3f(1, 2, 3)]), usdex.core.Vec3fPrimvarData, Sdf.ValueTypeNames.Point3fArray),
            (Vt.Vec3fArray([Gf.Vec3f(0.2, 0.3, 0.4)]), usdex.core.Vec3fPrimvarData, Sdf.ValueTypeNames.Color3f),
            (Vt.Vec3fArray([Gf.Vec3f(0, 0, 1)]), usdex.core.Vec3fPrimvarData, Sdf.ValueTypeNames.Normal3f),
            (Vt.Vec3fArray([Gf.Vec3f(4, 5, 6)]), usdex.core.Vec3fPrimvarData, Sdf.ValueTypeNames.Point3f),
        )
        scalarToArrayTypeNames = {
            Sdf.ValueTypeNames.Color3f: Sdf.ValueTypeNames.Color3fArray,
            Sdf.ValueTypeNames.Normal3f: Sdf.ValueTypeNames.Normal3fArray,
            Sdf.ValueTypeNames.Point3f: Sdf.ValueTypeNames.Point3fArray,
        }
        for index, (expectedValues, cls, valueTypeName) in enumerate(cases):
            data = cls(UsdGeom.Tokens.constant, expectedValues)
            if valueTypeName is None:
                self.assertTrue(data.createPrimvar(self.prim, f"attr{index}"))
            else:
                self.assertTrue(data.createPrimvar(self.prim, f"attr{index}", valueTypeName))
            self.assertTrue(data.isValid())
            self.assertIsInstance(data, cls)
            self.assertEqual(data.interpolation(), UsdGeom.Tokens.constant)
            self.assertEqual(data.values(), expectedValues)

            if valueTypeName is not None:
                primvar = UsdGeom.PrimvarsAPI(self.prim).GetPrimvar(f"attr{index}")
                expectedTypeName = scalarToArrayTypeNames.get(valueTypeName, valueTypeName)
                self.assertEqual(primvar.GetTypeName(), expectedTypeName)
                self.assertEqual(primvar.Get(), expectedValues)

        self.assertIsValidUsd(self.stage)

    def testSupportedArrayTypes(self):
        cases = (
            (Vt.FloatArray([1.0, 2.0, 3.0]), usdex.core.FloatPrimvarData, None),
            (Vt.IntArray([1, 2, 3]), usdex.core.IntPrimvarData, None),
            (Vt.Int64Array([1, 2, 3]), usdex.core.Int64PrimvarData, None),
            (Vt.StringArray(["item1", "item2"]), usdex.core.StringPrimvarData, None),
            (Vt.TokenArray(["item1", "item2"]), usdex.core.TokenPrimvarData, None),
            (Vt.Vec2fArray([Gf.Vec2f(0, 1), Gf.Vec2f(2, 3)]), usdex.core.Vec2fPrimvarData, None),
            (Vt.Vec3fArray([Gf.Vec3f(0, 1, 2), Gf.Vec3f(3, 4, 5)]), usdex.core.Vec3fPrimvarData, None),
            (
                Vt.Vec3fArray([Gf.Vec3f(0.1, 0.2, 0.3), Gf.Vec3f(0.4, 0.5, 0.6)]),
                usdex.core.Vec3fPrimvarData,
                Sdf.ValueTypeNames.Color3fArray,
            ),
            (
                Vt.Vec3fArray([Gf.Vec3f(0, 1, 0), Gf.Vec3f(1, 0, 0)]),
                usdex.core.Vec3fPrimvarData,
                Sdf.ValueTypeNames.Normal3fArray,
            ),
            (
                Vt.Vec3fArray([Gf.Vec3f(1, 2, 3), Gf.Vec3f(4, 5, 6)]),
                usdex.core.Vec3fPrimvarData,
                Sdf.ValueTypeNames.Point3fArray,
            ),
            (
                Vt.Vec3fArray([Gf.Vec3f(0.2, 0.3, 0.4), Gf.Vec3f(0.5, 0.6, 0.7)]),
                usdex.core.Vec3fPrimvarData,
                Sdf.ValueTypeNames.Color3f,
            ),
            (
                Vt.Vec3fArray([Gf.Vec3f(0, 0, 1), Gf.Vec3f(1, 0, 0)]),
                usdex.core.Vec3fPrimvarData,
                Sdf.ValueTypeNames.Normal3f,
            ),
            (
                Vt.Vec3fArray([Gf.Vec3f(7, 8, 9), Gf.Vec3f(10, 11, 12)]),
                usdex.core.Vec3fPrimvarData,
                Sdf.ValueTypeNames.Point3f,
            ),
        )
        scalarToArrayTypeNames = {
            Sdf.ValueTypeNames.Color3f: Sdf.ValueTypeNames.Color3fArray,
            Sdf.ValueTypeNames.Normal3f: Sdf.ValueTypeNames.Normal3fArray,
            Sdf.ValueTypeNames.Point3f: Sdf.ValueTypeNames.Point3fArray,
        }
        for index, (values, cls, valueTypeName) in enumerate(cases):
            data = cls(UsdGeom.Tokens.vertex, values)
            if valueTypeName is None:
                self.assertTrue(data.createPrimvar(self.prim, f"attr{index}"))
            else:
                self.assertTrue(data.createPrimvar(self.prim, f"attr{index}", valueTypeName))
            self.assertTrue(data.isValid())
            self.assertIsInstance(data, cls)
            self.assertEqual(data.interpolation(), UsdGeom.Tokens.vertex)
            self.assertEqual(data.values(), values)

            if valueTypeName is not None:
                primvar = UsdGeom.PrimvarsAPI(self.prim).GetPrimvar(f"attr{index}")
                expectedTypeName = scalarToArrayTypeNames.get(valueTypeName, valueTypeName)
                self.assertEqual(primvar.GetTypeName(), expectedTypeName)
                self.assertEqual(primvar.Get(), values)

        self.assertIsValidUsd(self.stage)

    def testIncompatibleValueTypeName(self):
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.0]))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*value type is incompatible.*")]):
            self.assertFalse(data.createPrimvar(self.prim, "color", Sdf.ValueTypeNames.Color3fArray))

        self.assertIsValidUsd(self.stage)

    def testTimeSample(self):
        values = Vt.FloatArray([1.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        self.assertTrue(data.createPrimvar(self.prim, "sampled"))
        self.assertTrue(data.isValid())

        primvar = UsdGeom.PrimvarsAPI(self.prim).GetPrimvar("sampled")
        self.assertTrue(data.setPrimvar(primvar, 10.5))
        self.assertEqual(primvar.Get(10.5), values)
        self.assertPrimvarIndicesBlocked(primvar)

        self.assertIsValidUsd(self.stage)

    def testEmptyArray(self):
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([]))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*primvar data is invalid.*")]):
            self.assertFalse(data.createPrimvar(self.prim, "empty"))
        self.assertFalse(data.isValid())

    def testInvalidPrimData(self):
        # If the index is out of range
        indices = Vt.IntArray([0, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.0]), indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*primvar data is invalid.*")]):
            self.assertFalse(data.createPrimvar(self.prim, "invalid"))
        self.assertFalse(data.isValid())

        # If the element size is invalid
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.0]), elementSize=2)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*primvar data is invalid.*")]):
            self.assertFalse(data.createPrimvar(self.prim, "invalid"))
        self.assertFalse(data.isValid())

    def testCreatePrimvarInvalidIndicesElementSize(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices, elementSize=2)
        self.assertFalse(data.isValid())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*primvar data is invalid.*")]):
            self.assertFalse(data.createPrimvar(self.prim, "invalid"))
        self.assertFalse(data.isValid())

        self.assertIsValidUsd(self.stage)

    def testNonIndexedPrimvarBlocksIndices(self):
        values = Vt.FloatArray([1.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        self.assertTrue(data.createPrimvar(self.prim, "sampled"))
        self.assertTrue(data.isValid())
        self.assertFalse(data.hasIndices())

        primvar = UsdGeom.PrimvarsAPI(self.prim).GetPrimvar("sampled")
        self.assertPrimvarIndicesBlocked(primvar)
        self.assertEqual(primvar.Get(), values)

        self.assertIsValidUsd(self.stage)

    def testReplacingIndexedPrimvarBlocksIndices(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        primvarsApi = UsdGeom.PrimvarsAPI(self.prim)
        primvar = primvarsApi.CreateIndexedPrimvar(
            "sampled",
            Sdf.ValueTypeNames.FloatArray,
            values,
            indices,
            UsdGeom.Tokens.vertex,
        )
        self.assertTrue(primvar.IsIndexed())

        replacement = Vt.FloatArray([1.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, replacement)
        self.assertTrue(data.createPrimvar(self.prim, "sampled"))
        self.assertTrue(data.isValid())
        self.assertFalse(data.hasIndices())

        primvar = primvarsApi.GetPrimvar("sampled")
        self.assertPrimvarIndicesBlocked(primvar)
        self.assertEqual(primvar.Get(), replacement)

        self.assertIsValidUsd(self.stage)

    def testCreatePrimvarWithElementSize(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, values, indices, elementSize=3)
        self.assertTrue(data.createPrimvar(self.prim, "withElementSize"))
        self.assertTrue(data.isValid())
        self.assertEqual(data.elementSize(), 3)

        primvar = UsdGeom.PrimvarsAPI(self.prim).GetPrimvar("withElementSize")
        self.assertTrue(primvar.IsIndexed())
        self.assertEqual(primvar.Get(), values)
        self.assertEqual(primvar.GetIndices(), indices)
        self.assertTrue(primvar.HasAuthoredElementSize())
        self.assertEqual(primvar.GetElementSize(), 3)

        self.assertIsValidUsd(self.stage)

    def testCreatePrimvarResetsElementSize(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        indices = Vt.IntArray([0, 1, 2])
        primvarsApi = UsdGeom.PrimvarsAPI(self.prim)

        indexedData = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, values, indices, elementSize=3)
        self.assertTrue(indexedData.createPrimvar(self.prim, "sampled"))

        primvar = primvarsApi.GetPrimvar("sampled")
        self.assertTrue(primvar.HasAuthoredElementSize())
        self.assertEqual(primvar.GetElementSize(), 3)

        replacement = Vt.FloatArray([-1.0, 0.5, 1.5])
        flatData = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, replacement)
        self.assertTrue(flatData.createPrimvar(self.prim, "sampled"))
        self.assertTrue(flatData.isValid())
        self.assertFalse(flatData.hasIndices())

        primvar = primvarsApi.GetPrimvar("sampled")
        self.assertFalse(primvar.IsIndexed())
        self.assertPrimvarIndicesBlocked(primvar)
        self.assertEqual(primvar.Get(), replacement)
        # elementSize cannot be blocked but should be reset to 1
        self.assertTrue(primvar.HasAuthoredElementSize())
        self.assertEqual(primvar.GetElementSize(), 1)
        self.assertNotEqual(primvar.GetElementSize(), flatData.elementSize())

        self.assertIsValidUsd(self.stage)

    def testInvalidPrim(self):
        invalidPrim = self.stage.GetPrimAtPath("/Missing")
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, Vt.Vec3fArray([Gf.Vec3f(0, 1, 2)]))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*prim is invalid.*")]):
            self.assertFalse(data.createPrimvar(invalidPrim, "foo"))
        self.assertIsInstance(data, usdex.core.Vec3fPrimvarData)
        self.assertTrue(data.isValid())

        self.assertIsValidUsd(self.stage)

    def testInvalidName(self):
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, Vt.Vec3fArray([Gf.Vec3f(0, 1, 2)]))
        # An empty name.
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*name is invalid.*")]):
            self.assertFalse(data.createPrimvar(self.prim, ""))

        # A name that does not conform to USD naming conventions.
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*name is invalid.*")]):
            self.assertFalse(data.createPrimvar(self.prim, "1_InvalidName"))

        self.assertIsValidUsd(self.stage)

    def testCreatePrimvarFailed(self):
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray([1.0]))
        # USD reserves the ":indices" suffix for indexed primvars; CreatePrimvar rejects it.
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_CODING_ERROR_TYPE, '.*reserved name "indices".*'),
                (Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*CreatePrimvar failed.*"),
            ],
        ):
            self.assertFalse(data.createPrimvar(self.prim, "widths:indices"))

        self.assertIsValidUsd(self.stage)

    def testCreatePrimvarFailureWarnsForAllValueTypes(self):
        """
        Each ``PrimvarData`` type emits ``Cannot create primvar`` on failure.
        """
        scalarCases = (
            (Vt.FloatArray([1.0]), usdex.core.FloatPrimvarData),
            (Vt.IntArray([2]), usdex.core.IntPrimvarData),
            (Vt.Int64Array([2**40]), usdex.core.Int64PrimvarData),
            (Vt.StringArray(["label"]), usdex.core.StringPrimvarData),
            (Vt.Vec2fArray([Gf.Vec2f(0, 1)]), usdex.core.Vec2fPrimvarData),
            (Vt.Vec3fArray([Gf.Vec3f(0, 1, 2)]), usdex.core.Vec3fPrimvarData),
        )
        for values, cls in scalarCases:
            data = cls(UsdGeom.Tokens.constant, values)
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*name is invalid.*")]):
                self.assertFalse(data.createPrimvar(self.prim, ""))
            self.assertTrue(data.isValid())
            self.assertIsInstance(data, cls)

        arrayCases = (
            (Vt.FloatArray(), usdex.core.FloatPrimvarData),
            (Vt.IntArray(), usdex.core.IntPrimvarData),
            (Vt.Int64Array(), usdex.core.Int64PrimvarData),
            (Vt.StringArray(), usdex.core.StringPrimvarData),
            (Vt.TokenArray(), usdex.core.TokenPrimvarData),
            (Vt.Vec2fArray(), usdex.core.Vec2fPrimvarData),
            (Vt.Vec3fArray(), usdex.core.Vec3fPrimvarData),
        )
        for values, cls in arrayCases:
            data = cls(UsdGeom.Tokens.constant, values)
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*primvar data is invalid.*")]):
                self.assertFalse(data.createPrimvar(self.prim, "empty"))
            self.assertFalse(data.isValid())
            self.assertIsInstance(data, cls)

        self.assertIsValidUsd(self.stage)

    def testAuthorPrimvarDataFailed(self):
        primvarsApi = UsdGeom.PrimvarsAPI(self.prim)
        primvar = primvarsApi.CreatePrimvar("data", Sdf.ValueTypeNames.FloatArray, UsdGeom.Tokens.vertex)
        self.assertTrue(primvar)

        # Author a non-int :indices attribute so setPrimvar() cannot call SetIndices().
        self.prim.CreateAttribute("primvars:data:indices", Sdf.ValueTypeNames.FloatArray)

        values = Vt.FloatArray([1.0, 2.0, 3.0])
        indices = Vt.IntArray([0, 1, 2])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_CODING_ERROR_TYPE, ".*expected 'VtArray<float>', got 'VtArray<int>'.*"),
                (Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*failed to author primvar data.*"),
            ],
        ):
            self.assertFalse(data.createPrimvar(self.prim, "data"))

        self.assertIsValidUsd(self.stage)

    def testInvalidInterpolation(self):
        values = Vt.FloatArray([-1.0, -0.5, 1.5])
        data = usdex.core.FloatPrimvarData("notAnInterpolation", values)
        self.assertFalse(data.isValid())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*primvar data is invalid.*")]):
            self.assertFalse(data.createPrimvar(self.prim, "needsInterpolation"))

        self.assertIsValidUsd(self.stage)


class CreateConstantPrimvarTestCase(usdex.test.TestCase):
    def setUp(self):
        super().setUp()
        self.stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(self.stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = self.stage.GetDefaultPrim()
        self.scope = usdex.core.defineScope(defaultPrim, "foo")
        self.prim = self.scope.GetPrim()

    def testScalarTypesWithValueTypeName(self):
        cases = (
            (1.5, Vt.FloatArray, Sdf.ValueTypeNames.FloatArray),
            (2, Vt.IntArray, Sdf.ValueTypeNames.IntArray),
            (2**40, Vt.Int64Array, Sdf.ValueTypeNames.Int64Array),
            ("descriptor", Vt.StringArray, Sdf.ValueTypeNames.StringArray),
            (Gf.Vec2f(0.1, 0.2), Vt.Vec2fArray, Sdf.ValueTypeNames.TexCoord2fArray),
        )
        for index, (value, arrayType, valueTypeName) in enumerate(cases):
            primvar = usdex.core.createConstantPrimvar(self.prim, f"attr{index}", value, valueTypeName)
            self.assertTrue(primvar, msg=f"{valueTypeName} at index {index}")
            self.assertIsInstance(primvar, UsdGeom.Primvar)
            self.assertEqual(primvar.GetTypeName(), valueTypeName)
            self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.constant)
            self.assertEqual(primvar.Get(), arrayType([value]))

        self.assertIsValidUsd(self.stage)

    def testVec3fWithValueTypeName(self):
        value = Gf.Vec3f(0.5, 0.7, 0.9)
        cases = (
            ("displayColor", Sdf.ValueTypeNames.Color3fArray, Sdf.ValueTypeNames.Color3fArray),
            ("normal", Sdf.ValueTypeNames.Normal3fArray, Sdf.ValueTypeNames.Normal3fArray),
            ("point", Sdf.ValueTypeNames.Point3fArray, Sdf.ValueTypeNames.Point3fArray),
            ("displayColorScalar", Sdf.ValueTypeNames.Color3f, Sdf.ValueTypeNames.Color3fArray),
            ("normalScalar", Sdf.ValueTypeNames.Normal3f, Sdf.ValueTypeNames.Normal3fArray),
            ("pointScalar", Sdf.ValueTypeNames.Point3f, Sdf.ValueTypeNames.Point3fArray),
        )
        for name, valueTypeName, expectedTypeName in cases:
            primvar = usdex.core.createConstantPrimvar(self.prim, name, value, valueTypeName)
            self.assertTrue(primvar, msg=f"{valueTypeName} at {name}")
            self.assertIsInstance(primvar, UsdGeom.Primvar)
            self.assertEqual(primvar.GetTypeName(), expectedTypeName)
            self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.constant)
            self.assertEqual(primvar.Get(), Vt.Vec3fArray([value]))

        self.assertIsValidUsd(self.stage)

    def testTokenWithValueTypeName(self):
        # In Python, str values author StringArray primvars by default. To author a TokenArray primvar, pass
        # Sdf.ValueTypeNames.TokenArray as valueTypeName.
        value = "item1"
        primvar = usdex.core.createConstantPrimvar(self.prim, "tokenAttr", value, Sdf.ValueTypeNames.TokenArray)
        self.assertTrue(primvar)
        self.assertIsInstance(primvar, UsdGeom.Primvar)
        self.assertEqual(primvar.GetTypeName(), Sdf.ValueTypeNames.TokenArray)
        self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.constant)
        self.assertEqual(primvar.Get(), Vt.TokenArray([value]))

        self.assertIsValidUsd(self.stage)

    def testSupportedScalarTypes(self):
        cases = (
            (1.5, Vt.FloatArray, Sdf.ValueTypeNames.FloatArray),
            (2, Vt.IntArray, Sdf.ValueTypeNames.IntArray),
            (2**40, Vt.Int64Array, Sdf.ValueTypeNames.Int64Array),
            ("descriptor", Vt.StringArray, Sdf.ValueTypeNames.StringArray),
            (Gf.Vec2f(0.1, 0.2), Vt.Vec2fArray, Sdf.ValueTypeNames.TexCoord2fArray),
            (Gf.Vec3f(0.0, 1.0, 2.0), Vt.Vec3fArray, Sdf.ValueTypeNames.Float3Array),
        )
        for index, (value, arrayType, valueTypeName) in enumerate(cases):
            primvar = usdex.core.createConstantPrimvar(self.prim, f"attr{index}", value)
            self.assertTrue(primvar, msg=f"{valueTypeName} at index {index}")
            self.assertIsInstance(primvar, UsdGeom.Primvar)
            self.assertEqual(primvar.GetTypeName(), valueTypeName)
            self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.constant)
            self.assertEqual(primvar.Get(), arrayType([value]))

        self.assertIsValidUsd(self.stage)

    def testFailureReturnsInvalidPrimvar(self):
        invalidPrim = self.stage.GetPrimAtPath("/Missing")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*prim is invalid.*")]):
            primvar = usdex.core.createConstantPrimvar(invalidPrim, "foo", 2)
        self.assertFalse(primvar)
        self.assertIsInstance(primvar, UsdGeom.Primvar)

    def testFailureInvalidName(self):
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*name is invalid.*")]):
            primvar = usdex.core.createConstantPrimvar(self.prim, "", 1.5)
        self.assertFalse(primvar)
        self.assertIsInstance(primvar, UsdGeom.Primvar)

        self.assertIsValidUsd(self.stage)

    def testFailureCreatePrimvarFailed(self):
        # USD reserves the ":indices" suffix for indexed primvars; CreatePrimvar rejects it.
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_CODING_ERROR_TYPE, '.*reserved name "indices".*'),
                (Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*CreatePrimvar failed.*"),
            ],
        ):
            primvar = usdex.core.createConstantPrimvar(self.prim, "widths:indices", 1.0)
        self.assertFalse(primvar)
        self.assertIsInstance(primvar, UsdGeom.Primvar)

        self.assertIsValidUsd(self.stage)

    def testIncompatibleValueTypeName(self):
        cases = (
            (1.5, Sdf.ValueTypeNames.IntArray),
            (2, Sdf.ValueTypeNames.FloatArray),
            (2**40, Sdf.ValueTypeNames.IntArray),
            ("descriptor", Sdf.ValueTypeNames.FloatArray),
            (Gf.Vec2f(0.1, 0.2), Sdf.ValueTypeNames.Float3Array),
            (Gf.Vec3f(1.0, 0.0, 0.0), Sdf.ValueTypeNames.FloatArray),
        )
        for index, (value, valueTypeName) in enumerate(cases):
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*value type is incompatible.*")]):
                primvar = usdex.core.createConstantPrimvar(self.prim, f"attr{index}", value, valueTypeName)
            self.assertFalse(primvar, msg=f"index {index}")
            self.assertIsInstance(primvar, UsdGeom.Primvar)

        self.assertIsValidUsd(self.stage)


class SetConstantPrimvarTestCase(usdex.test.TestCase):
    def setUp(self):
        super().setUp()
        self.stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(self.stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = self.stage.GetDefaultPrim()
        self.scope = usdex.core.defineScope(defaultPrim, "foo")
        self.prim = self.scope.GetPrim()

    def testSupportedScalarTypes(self):
        cases = (
            (1.5, 9.9, Vt.FloatArray, Sdf.ValueTypeNames.FloatArray),
            (2, 99, Vt.IntArray, Sdf.ValueTypeNames.IntArray),
            (2**40, 2**41, Vt.Int64Array, Sdf.ValueTypeNames.Int64Array),
            ("descriptor", "updated", Vt.StringArray, Sdf.ValueTypeNames.StringArray),
            (Gf.Vec2f(0.1, 0.2), Gf.Vec2f(0.9, 0.8), Vt.Vec2fArray, Sdf.ValueTypeNames.TexCoord2fArray),
            (Gf.Vec3f(0.0, 1.0, 2.0), Gf.Vec3f(3.0, 4.0, 5.0), Vt.Vec3fArray, Sdf.ValueTypeNames.Float3Array),
        )
        for index, (initialValue, updatedValue, arrayType, valueTypeName) in enumerate(cases):
            # First create the primvar with createConstantPrimvar, then update its value with setConstantPrimvar
            primvar = usdex.core.createConstantPrimvar(self.prim, f"attr{index}", initialValue)
            self.assertTrue(primvar)
            self.assertEqual(primvar.Get(), arrayType([initialValue]))

            self.assertTrue(usdex.core.setConstantPrimvar(self.prim, f"attr{index}", updatedValue))

            self.assertEqual(primvar.GetTypeName(), valueTypeName)
            self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.constant)
            self.assertEqual(primvar.Get(), arrayType([updatedValue]))

        self.assertIsValidUsd(self.stage)

    def testVec3fRoleArrayTypes(self):
        initialValue = Gf.Vec3f(0.0, 1.0, 2.0)
        updatedValue = Gf.Vec3f(3.0, 4.0, 5.0)
        cases = (
            ("colorAttr", Sdf.ValueTypeNames.Color3fArray),
            ("normalAttr", Sdf.ValueTypeNames.Normal3fArray),
            ("pointAttr", Sdf.ValueTypeNames.Point3fArray),
        )
        for name, valueTypeName in cases:
            primvar = usdex.core.createConstantPrimvar(self.prim, name, initialValue, valueTypeName)
            self.assertTrue(primvar)
            self.assertEqual(primvar.GetTypeName(), valueTypeName)
            self.assertEqual(primvar.Get(), Vt.Vec3fArray([initialValue]))

            self.assertTrue(usdex.core.setConstantPrimvar(self.prim, name, updatedValue))

            self.assertEqual(primvar.GetTypeName(), valueTypeName)
            self.assertEqual(primvar.GetInterpolation(), UsdGeom.Tokens.constant)
            self.assertEqual(primvar.Get(), Vt.Vec3fArray([updatedValue]))

        self.assertIsValidUsd(self.stage)

    def testTokenWithStringValue(self):
        # A Python str passed to a TokenArray primvar is automatically treated as a TfToken
        value = "item1"
        primvar = usdex.core.createConstantPrimvar(self.prim, "tokenAttr", value, Sdf.ValueTypeNames.TokenArray)
        self.assertTrue(primvar)

        newValue = "item2"
        self.assertTrue(usdex.core.setConstantPrimvar(self.prim, "tokenAttr", newValue))
        self.assertEqual(primvar.GetTypeName(), Sdf.ValueTypeNames.TokenArray)
        self.assertEqual(primvar.Get(), Vt.TokenArray([newValue]))

        self.assertIsValidUsd(self.stage)

    def testTimeSample(self):
        primvar = usdex.core.createConstantPrimvar(self.prim, "sampled", 1.0)
        self.assertTrue(primvar)

        self.assertTrue(usdex.core.setConstantPrimvar(self.prim, "sampled", 2.0, 10.0))
        self.assertEqual(primvar.Get(10.0), Vt.FloatArray([2.0]))

        self.assertIsValidUsd(self.stage)

    def testFailureInvalidPrim(self):
        invalidPrim = self.stage.GetPrimAtPath("/Missing")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot set primvar.*prim is invalid.*")]):
            self.assertFalse(usdex.core.setConstantPrimvar(invalidPrim, "foo", 1.0))

    def testFailurePrimvarDoesNotExist(self):
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot set primvar.*primvar does not exist.*")]):
            self.assertFalse(usdex.core.setConstantPrimvar(self.prim, "nonExistent", 1.0))

        self.assertIsValidUsd(self.stage)

    def testFailureIncompatibleValueType(self):
        # Create a FloatArray primvar, then attempt to set a Vec3f value on it.
        # USD emits a coding error for the type mismatch, followed by the setConstantPrimvar warning.
        primvar = usdex.core.createConstantPrimvar(self.prim, "floatAttr", 1.0)
        self.assertTrue(primvar)

        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_CODING_ERROR_TYPE, ".*Type mismatch.*primvars:floatAttr.*"),
                (Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot set primvar.*failed to set primvar data.*"),
            ],
        ):
            self.assertFalse(usdex.core.setConstantPrimvar(self.prim, "floatAttr", Gf.Vec3f(1.0, 0.0, 0.0)))

        self.assertIsValidUsd(self.stage)
