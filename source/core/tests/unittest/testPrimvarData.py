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
