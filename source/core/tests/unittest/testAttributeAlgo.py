# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import usdex.core
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdPhysics, UsdShade, Vt


class AttributeAlgoTest(usdex.test.TestCase):
    def _getSchemaFallbackValue(self, prim, attrName):
        """Get the schema fallback value for the given attribute."""
        return prim.GetPrimDefinition().GetAttributeFallbackValue(attrName)

    def _createLayeredSphereStage(self, weakerRadius: float = 2.0):
        """Create a stage with weaker and stronger sublayers and a sphere in the weaker layer."""
        weakerLayer = self.tmpLayer(name="Weaker")
        strongerLayer = self.tmpLayer(name="Stronger")

        rootLayer = Sdf.Layer.CreateAnonymous(tag="Root")
        rootLayer.subLayerPaths.append(strongerLayer.identifier)
        rootLayer.subLayerPaths.append(weakerLayer.identifier)

        stage = Usd.Stage.Open(rootLayer)

        stage.SetEditTarget(Usd.EditTarget(rootLayer))
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        stage.SetEditTarget(Usd.EditTarget(weakerLayer))
        sphere = usdex.core.defineSphere(stage.GetDefaultPrim(), "sphere", weakerRadius)

        # Leave the edit target on the stronger layer for subsequent authoring.
        stage.SetEditTarget(Usd.EditTarget(strongerLayer))
        return stage, weakerLayer, strongerLayer, sphere

    def testSparseAuthoringSkipsFallbackValue(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        # Use UsdGeom.Sphere.Define so we can reference the schema fallback for radius.
        spherePrim = UsdGeom.Sphere.Define(stage, defaultPrim.GetPath().AppendChild("sphere"))

        fallbackValue = self._getSchemaFallbackValue(spherePrim.GetPrim(), "radius")
        result = usdex.core.setEffectiveAttributeValue(spherePrim.GetPrim(), "radius", fallbackValue)
        self.assertTrue(result)
        self.assertFalse(spherePrim.GetRadiusAttr().HasAuthoredValue())
        self.assertEqual(spherePrim.GetRadiusAttr().Get(), fallbackValue)
        self.assertIsValidUsd(stage)

    def testSparseAuthoringSkipsResolvedValueWhenNoSchemaFallback(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        prim = usdex.core.defineXform(defaultPrim, "xform").GetPrim()

        # Create a custom attribute that has no schema fallback value.
        attrName = "customFloat"
        attr = prim.CreateAttribute(attrName, Sdf.ValueTypeNames.Float, custom=True)
        self.assertTrue(attr.IsDefined())
        self.assertFalse(attr.HasAuthoredValue())

        result = usdex.core.setEffectiveAttributeValue(prim, attrName, 0.5)
        self.assertTrue(result)
        self.assertTrue(attr.HasAuthoredValue())
        self.assertEqual(attr.Get(), 0.5)
        self.assertIsValidUsd(stage)

    def testAuthorsNonFallbackValue(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        spherePrim = usdex.core.defineSphere(defaultPrim, "sphere", 1.0)

        result = usdex.core.setEffectiveAttributeValue(spherePrim.GetPrim(), "radius", 2.0)
        self.assertTrue(result)
        self.assertTrue(spherePrim.GetRadiusAttr().HasAuthoredValue())
        self.assertEqual(spherePrim.GetRadiusAttr().Get(), 2.0)
        self.assertIsValidUsd(stage)

    def testFallbackValueClearsAuthoredValue(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        spherePrim = usdex.core.defineSphere(defaultPrim, "sphere", 2.0)

        self.assertTrue(spherePrim.GetRadiusAttr().HasAuthoredValue())
        self.assertEqual(spherePrim.GetRadiusAttr().Get(), 2.0)

        # Setting the value to the fallback value clears the authored opinion in the edit target.
        # In this case, the schema fallback value will be returned.
        fallbackValue = self._getSchemaFallbackValue(spherePrim.GetPrim(), "radius")
        result = usdex.core.setEffectiveAttributeValue(spherePrim.GetPrim(), "radius", fallbackValue)
        self.assertTrue(result)
        self.assertFalse(spherePrim.GetRadiusAttr().HasAuthoredValue())
        self.assertEqual(spherePrim.GetRadiusAttr().Get(), fallbackValue)
        self.assertIsValidUsd(stage)

    def testCoercesIntToDouble(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        spherePrim = usdex.core.defineSphere(defaultPrim, "sphere", 1.0)

        result = usdex.core.setEffectiveAttributeValue(spherePrim.GetPrim(), "radius", 2)
        self.assertTrue(result)
        self.assertEqual(spherePrim.GetRadiusAttr().GetTypeName(), Sdf.ValueTypeNames.Double)
        self.assertTrue(spherePrim.GetRadiusAttr().HasAuthoredValue())
        self.assertEqual(spherePrim.GetRadiusAttr().Get(), 2.0)
        self.assertIsValidUsd(stage)

    def testCoercesIntToFloat(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        # UsdPhysics.MaterialAPI declares physics:density as float (not double).
        material = UsdShade.Material.Define(stage, defaultPrim.GetPath().AppendChild("physicsMaterial"))
        UsdPhysics.MaterialAPI.Apply(material.GetPrim())

        result = usdex.core.setEffectiveAttributeValue(material.GetPrim(), "physics:density", 2)
        self.assertTrue(result)
        densityAttr = UsdPhysics.MaterialAPI(material.GetPrim()).GetDensityAttr()
        self.assertEqual(densityAttr.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertTrue(densityAttr.HasAuthoredValue())
        self.assertEqual(densityAttr.Get(), 2.0)
        self.assertIsValidUsd(stage)

    def testCoercesDoubleToFloat(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        # UsdPhysics.MaterialAPI declares physics:density as float (not double).
        material = UsdShade.Material.Define(stage, defaultPrim.GetPath().AppendChild("physicsMaterial"))
        UsdPhysics.MaterialAPI.Apply(material.GetPrim())

        result = usdex.core.setEffectiveAttributeValue(material.GetPrim(), "physics:density", 2.0)
        self.assertTrue(result)
        densityAttr = UsdPhysics.MaterialAPI(material.GetPrim()).GetDensityAttr()
        self.assertEqual(densityAttr.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertTrue(densityAttr.HasAuthoredValue())
        self.assertEqual(densityAttr.Get(), 2.0)
        self.assertIsValidUsd(stage)

    def testCoercesBoolToNumber(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()

        intAttr = scopePrim.CreateAttribute("intAttr", Sdf.ValueTypeNames.Int)
        floatAttr = scopePrim.CreateAttribute("floatAttr", Sdf.ValueTypeNames.Float)
        doubleAttr = scopePrim.CreateAttribute("doubleAttr", Sdf.ValueTypeNames.Double)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "intAttr", True)
        self.assertTrue(result)
        self.assertEqual(intAttr.GetTypeName(), Sdf.ValueTypeNames.Int)
        self.assertTrue(intAttr.HasAuthoredValue())
        self.assertEqual(intAttr.Get(), 1)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "floatAttr", True)
        self.assertTrue(result)
        self.assertEqual(floatAttr.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertTrue(floatAttr.HasAuthoredValue())
        self.assertEqual(floatAttr.Get(), 1.0)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "doubleAttr", True)
        self.assertTrue(result)
        self.assertEqual(doubleAttr.GetTypeName(), Sdf.ValueTypeNames.Double)
        self.assertTrue(doubleAttr.HasAuthoredValue())
        self.assertEqual(doubleAttr.Get(), 1.0)
        self.assertIsValidUsd(stage)

    def testCoercesNumberToBool(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        boolAttr = scopePrim.CreateAttribute("boolAttr", Sdf.ValueTypeNames.Bool)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "boolAttr", 1)
        self.assertTrue(result)
        self.assertEqual(boolAttr.GetTypeName(), Sdf.ValueTypeNames.Bool)
        self.assertTrue(boolAttr.HasAuthoredValue())
        self.assertEqual(boolAttr.Get(), True)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "boolAttr", 0)
        self.assertTrue(result)
        self.assertEqual(boolAttr.GetTypeName(), Sdf.ValueTypeNames.Bool)
        self.assertTrue(boolAttr.HasAuthoredValue())
        self.assertEqual(boolAttr.Get(), False)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "boolAttr", 1.0)
        self.assertTrue(result)
        self.assertEqual(boolAttr.GetTypeName(), Sdf.ValueTypeNames.Bool)
        self.assertTrue(boolAttr.HasAuthoredValue())
        self.assertEqual(boolAttr.Get(), True)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "boolAttr", 0.0)
        self.assertTrue(result)
        self.assertEqual(boolAttr.GetTypeName(), Sdf.ValueTypeNames.Bool)
        self.assertTrue(boolAttr.HasAuthoredValue())
        self.assertEqual(boolAttr.Get(), False)

    def testCoercesFloat2ToDouble2(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        double2Attr = scopePrim.CreateAttribute("double2Attr", Sdf.ValueTypeNames.Double2)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "double2Attr", Gf.Vec2f(1, 2))
        self.assertTrue(result)
        self.assertEqual(double2Attr.GetTypeName(), Sdf.ValueTypeNames.Double2)
        self.assertTrue(double2Attr.HasAuthoredValue())
        self.assertEqual(double2Attr.Get(), Gf.Vec2d(1, 2))
        self.assertIsValidUsd(stage)

    def testCoercesDouble2ToFloat2(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        float2Attr = scopePrim.CreateAttribute("float2Attr", Sdf.ValueTypeNames.Float2)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "float2Attr", Gf.Vec2d(1, 2))
        self.assertTrue(result)
        self.assertEqual(float2Attr.GetTypeName(), Sdf.ValueTypeNames.Float2)
        self.assertTrue(float2Attr.HasAuthoredValue())
        self.assertEqual(float2Attr.Get(), Gf.Vec2f(1, 2))
        self.assertIsValidUsd(stage)

    def testCoercesFloat3ToDouble3(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        double3Attr = scopePrim.CreateAttribute("double3Attr", Sdf.ValueTypeNames.Double3)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "double3Attr", Gf.Vec3f(1, 2, 3))
        self.assertTrue(result)
        self.assertEqual(double3Attr.GetTypeName(), Sdf.ValueTypeNames.Double3)
        self.assertTrue(double3Attr.HasAuthoredValue())
        self.assertEqual(double3Attr.Get(), Gf.Vec3d(1, 2, 3))
        self.assertIsValidUsd(stage)

    def testCoercesDouble3ToFloat3(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        float3Attr = scopePrim.CreateAttribute("float3Attr", Sdf.ValueTypeNames.Float3)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "float3Attr", Gf.Vec3d(1, 2, 3))
        self.assertTrue(result)
        self.assertEqual(float3Attr.GetTypeName(), Sdf.ValueTypeNames.Float3)
        self.assertTrue(float3Attr.HasAuthoredValue())
        self.assertEqual(float3Attr.Get(), Gf.Vec3f(1, 2, 3))
        self.assertIsValidUsd(stage)

    def testCoercesFloat4ToDouble4(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        double4Attr = scopePrim.CreateAttribute("double4Attr", Sdf.ValueTypeNames.Double4)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "double4Attr", Gf.Vec4f(1, 2, 3, 4))
        self.assertTrue(result)
        self.assertEqual(double4Attr.GetTypeName(), Sdf.ValueTypeNames.Double4)
        self.assertTrue(double4Attr.HasAuthoredValue())
        self.assertEqual(double4Attr.Get(), Gf.Vec4d(1, 2, 3, 4))
        self.assertIsValidUsd(stage)

    def testCoercesDouble4ToFloat4(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        float4Attr = scopePrim.CreateAttribute("float4Attr", Sdf.ValueTypeNames.Float4)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "float4Attr", Gf.Vec4d(1, 2, 3, 4))
        self.assertTrue(result)
        self.assertEqual(float4Attr.GetTypeName(), Sdf.ValueTypeNames.Float4)
        self.assertTrue(float4Attr.HasAuthoredValue())
        self.assertEqual(float4Attr.Get(), Gf.Vec4f(1, 2, 3, 4))
        self.assertIsValidUsd(stage)

    def testCoercesFloat3ToColor3f(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        color3fAttr = scopePrim.CreateAttribute("color3fAttr", Sdf.ValueTypeNames.Color3f)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "color3fAttr", Gf.Vec3f(0.25, 0.5, 0.75))
        self.assertTrue(result)
        self.assertEqual(color3fAttr.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(color3fAttr.HasAuthoredValue())
        self.assertEqual(color3fAttr.Get(), Gf.Vec3f(0.25, 0.5, 0.75))
        self.assertIsValidUsd(stage)

    def testCoercesColor3fToFloat3(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        float3Attr = scopePrim.CreateAttribute("float3Attr", Sdf.ValueTypeNames.Float3)

        result = usdex.core.setEffectiveAttributeValue(scopePrim, "float3Attr", Gf.Vec3f(1, 2, 3))
        self.assertTrue(result)
        self.assertEqual(float3Attr.GetTypeName(), Sdf.ValueTypeNames.Float3)
        self.assertTrue(float3Attr.HasAuthoredValue())
        self.assertEqual(float3Attr.Get(), Gf.Vec3f(1, 2, 3))
        self.assertIsValidUsd(stage)

    def testCoercesQuatfToQuatd(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        quatdAttr = scopePrim.CreateAttribute("quatdAttr", Sdf.ValueTypeNames.Quatd)

        quatf = Gf.Quatf(0.7071068, Gf.Vec3f(0.0, 0.7071068, 0.0))
        result = usdex.core.setEffectiveAttributeValue(scopePrim, "quatdAttr", quatf)
        self.assertTrue(result)
        self.assertEqual(quatdAttr.GetTypeName(), Sdf.ValueTypeNames.Quatd)
        self.assertTrue(quatdAttr.HasAuthoredValue())
        self.assertEqual(quatdAttr.Get(), Gf.Quatd(quatf))
        self.assertIsValidUsd(stage)

    def testCoercesQuatdToQuatf(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        quatfAttr = scopePrim.CreateAttribute("quatfAttr", Sdf.ValueTypeNames.Quatf)

        quatd = Gf.Quatd(0.5, Gf.Vec3d(0.5, 0.5, 0.5))
        result = usdex.core.setEffectiveAttributeValue(scopePrim, "quatfAttr", quatd)
        self.assertTrue(result)
        self.assertEqual(quatfAttr.GetTypeName(), Sdf.ValueTypeNames.Quatf)
        self.assertTrue(quatfAttr.HasAuthoredValue())
        self.assertEqual(quatfAttr.Get(), Gf.Quatf(quatd))
        self.assertIsValidUsd(stage)

    def testAuthorsArrayAttributes(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()

        cases = [
            ("floatArrayAttr", Sdf.ValueTypeNames.FloatArray, Vt.FloatArray([1.0, 2.5, 3.0])),
            ("intArrayAttr", Sdf.ValueTypeNames.IntArray, Vt.IntArray([1, 2, 3])),
            ("doubleArrayAttr", Sdf.ValueTypeNames.DoubleArray, Vt.DoubleArray([1.0, 2.0])),
            ("tokenArrayAttr", Sdf.ValueTypeNames.TokenArray, Vt.TokenArray(["alpha", "beta"])),
            ("float2ArrayAttr", Sdf.ValueTypeNames.Float2Array, Vt.Vec2fArray([Gf.Vec2f(1, 2), Gf.Vec2f(3, 4)])),
            ("float3ArrayAttr", Sdf.ValueTypeNames.Float3Array, Vt.Vec3fArray([Gf.Vec3f(1, 2, 3), Gf.Vec3f(4, 5, 6)])),
            ("float4ArrayAttr", Sdf.ValueTypeNames.Float4Array, Vt.Vec4fArray([Gf.Vec4f(1, 2, 3, 4), Gf.Vec4f(5, 6, 7, 8)])),
            ("double2ArrayAttr", Sdf.ValueTypeNames.Double2Array, Vt.Vec2dArray([Gf.Vec2d(1, 2), Gf.Vec2d(3, 4)])),
            ("double3ArrayAttr", Sdf.ValueTypeNames.Double3Array, Vt.Vec3dArray([Gf.Vec3d(1, 2, 3), Gf.Vec3d(4, 5, 6)])),
            ("double4ArrayAttr", Sdf.ValueTypeNames.Double4Array, Vt.Vec4dArray([Gf.Vec4d(1, 2, 3, 4), Gf.Vec4d(5, 6, 7, 8)])),
            ("color3fArrayAttr", Sdf.ValueTypeNames.Color3fArray, Vt.Vec3fArray([Gf.Vec3f(1, 2, 3), Gf.Vec3f(4, 5, 6)])),
            ("color4fArrayAttr", Sdf.ValueTypeNames.Color4fArray, Vt.Vec4fArray([Gf.Vec4f(1, 2, 3, 4), Gf.Vec4f(5, 6, 7, 8)])),
            ("normal3fArrayAttr", Sdf.ValueTypeNames.Normal3fArray, Vt.Vec3fArray([Gf.Vec3f(1, 2, 3), Gf.Vec3f(4, 5, 6)])),
            ("point3fArrayAttr", Sdf.ValueTypeNames.Point3fArray, Vt.Vec3fArray([Gf.Vec3f(1, 2, 3), Gf.Vec3f(4, 5, 6)])),
        ]
        for attrName, typeName, values in cases:
            attr = scopePrim.CreateAttribute(attrName, typeName)
            result = usdex.core.setEffectiveAttributeValue(scopePrim, attrName, values)
            self.assertTrue(result, attrName)
            self.assertEqual(attr.GetTypeName(), typeName, attrName)
            self.assertTrue(attr.HasAuthoredValue(), attrName)
            self.assertEqual(attr.Get(), values, attrName)

        self.assertIsValidUsd(stage)

    def testCoercesPythonListToArrayAttributes(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()

        cases = [
            ("floatArrayAttr", Sdf.ValueTypeNames.FloatArray, [1.0, 2.5, 3.0], Vt.FloatArray([1.0, 2.5, 3.0])),
            ("intArrayAttr", Sdf.ValueTypeNames.IntArray, [1, 2, 3], Vt.IntArray([1, 2, 3])),
            ("doubleArrayAttr", Sdf.ValueTypeNames.DoubleArray, [1.0, 2.0], Vt.DoubleArray([1.0, 2.0])),
            ("tokenArrayAttr", Sdf.ValueTypeNames.TokenArray, ["alpha", "beta"], Vt.TokenArray(["alpha", "beta"])),
            ("float3ArrayAttr", Sdf.ValueTypeNames.Float3Array, [(1, 2, 3), (4, 5, 6)], Vt.Vec3fArray([Gf.Vec3f(1, 2, 3), Gf.Vec3f(4, 5, 6)])),
            ("double3ArrayAttr", Sdf.ValueTypeNames.Double3Array, [(1, 2, 3), (4, 5, 6)], Vt.Vec3dArray([Gf.Vec3d(1, 2, 3), Gf.Vec3d(4, 5, 6)])),
        ]
        for attrName, typeName, values, expected in cases:
            attr = scopePrim.CreateAttribute(attrName, typeName)
            result = usdex.core.setEffectiveAttributeValue(scopePrim, attrName, values)
            self.assertTrue(result, attrName)
            self.assertTrue(attr.HasAuthoredValue(), attrName)
            self.assertEqual(attr.Get(), expected, attrName)

        self.assertIsValidUsd(stage)

    def testEmptyValueBlocksUnauthoredAttribute(self):
        """An empty value blocks a weaker-layer opinion when the stronger layer is unauthored."""
        stage, weakerLayer, strongerLayer, sphere = self._createLayeredSphereStage(weakerRadius=2.0)
        radiusAttr = sphere.GetRadiusAttr()

        # The weaker-layer opinion is visible before the stronger layer authors anything.
        self.assertEqual(radiusAttr.Get(), 2.0)
        weakerSpec = weakerLayer.GetAttributeAtPath(radiusAttr.GetPath())
        self.assertIsNotNone(weakerSpec)
        self.assertEqual(weakerSpec.default, 2.0)
        self.assertFalse(strongerLayer.GetAttributeAtPath(radiusAttr.GetPath()))

        result = usdex.core.setEffectiveAttributeValue(sphere.GetPrim(), "radius", None)
        self.assertTrue(result)

        self.assertFalse(radiusAttr.HasAuthoredValue())
        self.assertIsNone(radiusAttr.Get())
        strongerSpec = strongerLayer.GetAttributeAtPath(radiusAttr.GetPath())
        self.assertIsNotNone(strongerSpec)
        self.assertEqual(strongerSpec.default, Sdf.ValueBlock())
        self.assertIsValidUsd(stage)

    def testEmptyValueBlocksAuthoredValue(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        spherePrim = usdex.core.defineSphere(defaultPrim, "sphere", 2.0)

        self.assertTrue(spherePrim.GetRadiusAttr().HasAuthoredValue())
        self.assertEqual(spherePrim.GetRadiusAttr().Get(), 2.0)

        # Setting the value to None will block the authored value.
        result = usdex.core.setEffectiveAttributeValue(spherePrim.GetPrim(), "radius", None)
        self.assertTrue(result)
        self.assertFalse(spherePrim.GetRadiusAttr().HasAuthoredValue())
        self.assertIsNone(spherePrim.GetRadiusAttr().Get())
        layer = stage.GetEditTarget().GetLayer()
        attrSpec = layer.GetAttributeAtPath(spherePrim.GetRadiusAttr().GetPath())
        self.assertIsNotNone(attrSpec)
        self.assertEqual(attrSpec.default, Sdf.ValueBlock())
        self.assertIsValidUsd(stage)

        # Entering a new value will unlock the block.
        result = usdex.core.setEffectiveAttributeValue(spherePrim.GetPrim(), "radius", 2.5)
        self.assertTrue(result)
        self.assertTrue(spherePrim.GetRadiusAttr().HasAuthoredValue())
        self.assertEqual(spherePrim.GetRadiusAttr().Get(), 2.5)
        self.assertIsValidUsd(stage)

    def testLayeredFallbackBlocksWeakerLayerOpinion(self):
        stage, _, strongerLayer, sphere = self._createLayeredSphereStage(weakerRadius=2.0)
        radiusAttr = sphere.GetRadiusAttr()

        self.assertEqual(radiusAttr.Get(), 2.0)

        fallbackValue = self._getSchemaFallbackValue(sphere.GetPrim(), "radius")
        result = usdex.core.setEffectiveAttributeValue(sphere.GetPrim(), "radius", fallbackValue)
        self.assertTrue(result)

        self.assertFalse(radiusAttr.HasAuthoredValue())
        self.assertIsNone(radiusAttr.Get())
        strongerSpec = strongerLayer.GetAttributeAtPath(radiusAttr.GetPath())
        self.assertIsNotNone(strongerSpec)
        self.assertEqual(strongerSpec.default, Sdf.ValueBlock())
        self.assertIsValidUsd(stage)

    def testLayeredFallbackClearsStrongerLayerOpinion(self):
        """When only the stronger layer has an opinion, fallback uses Clear() not Block()."""
        strongerLayer = self.tmpLayer(name="StrongerOnly")
        rootLayer = Sdf.Layer.CreateAnonymous(tag="Root")
        rootLayer.subLayerPaths.append(strongerLayer.identifier)

        stage = Usd.Stage.Open(rootLayer)
        stage.SetEditTarget(Usd.EditTarget(rootLayer))
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        stage.SetEditTarget(Usd.EditTarget(strongerLayer))
        sphere = usdex.core.defineSphere(stage.GetDefaultPrim(), "sphere", 3.0)
        radiusAttr = sphere.GetRadiusAttr()

        # Setting the value to the fallback value clears the authored opinion in the edit target.
        fallbackValue = self._getSchemaFallbackValue(sphere.GetPrim(), "radius")
        result = usdex.core.setEffectiveAttributeValue(sphere.GetPrim(), "radius", fallbackValue)
        self.assertTrue(result)

        self.assertFalse(radiusAttr.HasAuthoredValue())
        self.assertEqual(radiusAttr.Get(), fallbackValue)
        strongerSpec = strongerLayer.GetAttributeAtPath(radiusAttr.GetPath())
        self.assertIsNotNone(strongerSpec)
        self.assertIsNone(strongerSpec.default)

        self.assertIsValidUsd(stage)

    def testLayeredClearExposesWeakerLayerOpinion(self):
        """Contrast Block() with Clear(): Clear removes only the stronger-layer opinion."""
        stage, _, strongerLayer, sphere = self._createLayeredSphereStage(weakerRadius=2.0)
        radiusAttr = sphere.GetRadiusAttr()

        result = usdex.core.setEffectiveAttributeValue(sphere.GetPrim(), "radius", 3.0)
        self.assertTrue(result)
        self.assertEqual(radiusAttr.Get(), 3.0)

        radiusAttr.Clear()

        # Without a block, removing the stronger opinion falls back to the weaker layer.
        self.assertEqual(radiusAttr.Get(), 2.0)
        # Clear removes the default value but may leave an empty attribute spec on the layer.
        strongerSpec = strongerLayer.GetAttributeAtPath(radiusAttr.GetPath())
        self.assertIsNotNone(strongerSpec)
        self.assertIsNone(strongerSpec.default)
        layer = stage.GetEditTarget().GetLayer()
        attrSpec = layer.GetAttributeAtPath(radiusAttr.GetPath())
        self.assertIsNotNone(attrSpec)
        self.assertIsNone(attrSpec.default)

        self.assertIsValidUsd(stage)

    def testApiSchemaAttribute(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        cubePrim = usdex.core.defineCube(defaultPrim, "cube", 1.0)

        UsdPhysics.CollisionAPI.Apply(cubePrim.GetPrim())

        result = usdex.core.setEffectiveAttributeValue(cubePrim.GetPrim(), "physics:collisionEnabled", False)
        self.assertTrue(result)
        attr = cubePrim.GetPrim().GetAttribute("physics:collisionEnabled")
        self.assertTrue(attr.HasAuthoredValue())
        self.assertFalse(attr.Get())

        # Setting the value to the fallback value clears the authored opinion in the edit target.
        fallbackValue = self._getSchemaFallbackValue(cubePrim.GetPrim(), "physics:collisionEnabled")
        result = usdex.core.setEffectiveAttributeValue(cubePrim.GetPrim(), "physics:collisionEnabled", fallbackValue)
        self.assertTrue(result)
        self.assertFalse(attr.HasAuthoredValue())
        self.assertEqual(attr.Get(), fallbackValue)
        layer = stage.GetEditTarget().GetLayer()
        attrSpec = layer.GetAttributeAtPath(attr.GetPath())
        self.assertIsNotNone(attrSpec)
        self.assertIsNone(attrSpec.default)

        self.assertIsValidUsd(stage)

    def testInvalidPrimRaisesCodingError(self):
        prim = Usd.Prim()
        self.assertFalse(prim.IsValid())

        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, 'Unable to author attribute "radius".*invalid prim')],
        ):
            result = usdex.core.setEffectiveAttributeValue(prim, "radius", 1.0)
            self.assertFalse(result)

    def testUndefinedAttributeRaisesCodingError(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        spherePrim = usdex.core.defineSphere(defaultPrim, "sphere", 1.0)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, 'Attribute "missing" is not defined')]):
            result = usdex.core.setEffectiveAttributeValue(spherePrim.GetPrim(), "missing", 1.0)
            self.assertFalse(result)
        self.assertIsValidUsd(stage)

    def testTypeMismatchRaisesCodingError(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        spherePrim = usdex.core.defineSphere(defaultPrim, "sphere", 1.0)

        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    'Incompatible value type for attribute "radius".*Value type "string" cannot be converted to attribute type "double"',
                )
            ],
        ):
            result = usdex.core.setEffectiveAttributeValue(spherePrim.GetPrim(), "radius", "not-a-float")
            self.assertFalse(result)
        self.assertIsValidUsd(stage)

    def testTypeMismatchScalarToFloatArrayRaisesCodingError(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        scopePrim.CreateAttribute("floatArrayAttr", Sdf.ValueTypeNames.FloatArray)

        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    'Incompatible value type for attribute "floatArrayAttr".*Value type "double" cannot be converted to attribute type "VtArray<float>"',
                )
            ],
        ):
            result = usdex.core.setEffectiveAttributeValue(scopePrim, "floatArrayAttr", 1.0)
            self.assertFalse(result)
        self.assertIsValidUsd(stage)

    def testTypeMismatchIntArrayToFloatArrayRaisesCodingError(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrim = stage.GetDefaultPrim()
        scopePrim = usdex.core.defineScope(defaultPrim, "scope").GetPrim()
        scopePrim.CreateAttribute("floatArrayAttr", Sdf.ValueTypeNames.FloatArray)

        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    'Incompatible value type for attribute "floatArrayAttr".*Value type "VtArray<int>" cannot be converted to attribute type "VtArray<float>"',
                )
            ],
        ):
            result = usdex.core.setEffectiveAttributeValue(scopePrim, "floatArrayAttr", Vt.IntArray([1, 2]))
            self.assertFalse(result)
        self.assertIsValidUsd(stage)
