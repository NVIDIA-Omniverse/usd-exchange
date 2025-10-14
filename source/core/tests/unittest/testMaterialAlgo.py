# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
import pathlib
import tempfile
import unittest
from typing import Any, List, Tuple

import usdex.core
import usdex.test
from pxr import Gf, Sdf, Sdr, Tf, Usd, UsdGeom, UsdShade, UsdUtils


class MaterialAlgoTest(usdex.test.TestCase):

    def testCreateMaterial(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.createMaterial(parent=materials, name="foo")
        self.assertTrue(material.GetPrim())
        self.assertIsValidUsd(stage)

        # An invalid parent will result in an invalid Material schema being returned
        invalid_parent = stage.GetPrimAtPath("/Root/InvalidPath")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid location")]):
            material = usdex.core.createMaterial(invalid_parent, "InvalidMaterial")
        self.assertFalse(material)

        # An invalid name will result in an invalid Material schema being returned
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid location")]):
            material = usdex.core.createMaterial(materials, "")
        self.assertFalse(material)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid location")]):
            material = usdex.core.createMaterial(materials, "1_Material")
        self.assertFalse(material)

    def testBindMaterial(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        geometry = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild("Geometry")).GetPrim()  # common convention
        cube = UsdGeom.Cube.Define(stage, geometry.GetPath().AppendChild("Cube")).GetPrim()
        cube2 = UsdGeom.Cube.Define(stage, geometry.GetPath().AppendChild("Cube2")).GetPrim()
        cubeXform = UsdGeom.Xform.Define(stage, geometry.GetPath().AppendChild("CubeXform")).GetPrim()
        nestedCube = UsdGeom.Cube.Define(stage, cubeXform.GetPath().AppendChild("Cube")).GetPrim()
        UsdGeom.Cube.Define(stage, cubeXform.GetPath().AppendChild("NoMaterialCube")).GetPrim()
        nestedMaterials = UsdGeom.Scope.Define(stage, cubeXform.GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        instancedCubeXform = UsdGeom.Xform.Define(stage, geometry.GetPath().AppendChild("InstancedCubeXform")).GetPrim()
        instancedCubeXform.GetReferences().AddInternalReference(cubeXform.GetPath())
        instancedCubeXform.SetInstanceable(True)

        material = usdex.core.createMaterial(materials, "Material")
        self.assertTrue(material)

        result = usdex.core.bindMaterial(cube, material)
        self.assertTrue(result)
        self.assertTrue(cube.HasAPI(UsdShade.MaterialBindingAPI))
        self.assertIsValidUsd(stage)

        # An invalid material will fail to bind
        invalidMaterial = UsdShade.Material(materials.GetChild("InvalidPath"))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, "UsdShadeMaterial.*is not valid, cannot bind material")]):
            result = usdex.core.bindMaterial(cube2, invalidMaterial)
        self.assertFalse(result)
        self.assertFalse(cube2.HasAPI(UsdShade.MaterialBindingAPI))

        # An invalid target prim will fail to be bound
        invalidTarget = UsdGeom.Cube(geometry.GetChild("InvalidPath")).GetPrim()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, "UsdPrim.*is not valid, cannot bind material")]):
            result = usdex.core.bindMaterial(invalidTarget, material)
        self.assertFalse(result)

        # If both are invalid it cannot bind either
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*are not valid, cannot bind material")]):
            result = usdex.core.bindMaterial(invalidTarget, invalidMaterial)
        self.assertFalse(result)

        # Check that bindMaterial() prevents binding across an Instance boundary
        # First create and bind a material to the referenced xform/cube (this should work properly)
        nestedMaterial = usdex.core.createMaterial(nestedMaterials, "Material")
        self.assertTrue(nestedMaterial)
        result = usdex.core.bindMaterial(nestedCube, nestedMaterial)
        self.assertTrue(result)
        self.assertTrue(nestedCube.HasAPI(UsdShade.MaterialBindingAPI))
        self.assertIsValidUsd(stage)
        # Now, attempt to bind the material to the instanced cube
        instancedCube = instancedCubeXform.GetPrim().GetChild("Cube")
        self.assertTrue(instancedCube)
        self.assertTrue(instancedCube.HasAPI(UsdShade.MaterialBindingAPI))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, "Cannot bind material due to an invalid location")]):
            result = usdex.core.bindMaterial(instancedCube, material)
        self.assertFalse(result)
        self.assertTrue(instancedCube.HasAPI(UsdShade.MaterialBindingAPI))
        # Last, check that the bind behavior is the same on a prim with no material assigned
        instancedCube = instancedCubeXform.GetPrim().GetChild("NoMaterialCube")
        self.assertTrue(instancedCube)
        self.assertFalse(instancedCube.HasAPI(UsdShade.MaterialBindingAPI))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, "Cannot bind material due to an invalid location")]):
            result = usdex.core.bindMaterial(instancedCube, material)
        self.assertFalse(result)
        self.assertFalse(instancedCube.HasAPI(UsdShade.MaterialBindingAPI))
        self.assertIsValidUsd(stage)

    def testComputeEffectiveSurfaceShader(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # An un-initialized Material will result in an invalid shader schema being returned
        material = UsdShade.Material()
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertFalse(shader)

        # An invalid UsdShade.Material will result in an invalid shader schema being returned
        material = UsdShade.Material(stage.GetPrimAtPath("/Root"))
        self.assertFalse(material)
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertFalse(shader)

        # A Material with no connected shaders will result in an invalid shader schema being returned
        material = usdex.core.createMaterial(materials, "Material")
        self.assertTrue(material)
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertFalse(shader)

        # A connected surface shader will be returned
        previewShader = UsdShade.Shader.Define(stage, material.GetPrim().GetPath().AppendChild("PreviewSurface"))
        self.assertTrue(previewShader)
        output = previewShader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput().ConnectToSource(output)
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), previewShader.GetPrim())

        # Even with another render context connected, the shader for the universal context is returned
        otherShader = UsdShade.Shader.Define(stage, material.GetPrim().GetPath().AppendChild("foo"))
        self.assertTrue(otherShader)
        output = otherShader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("fancy").ConnectToSource(output)
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)
        self.assertNotEqual(shader.GetPrim(), otherShader.GetPrim())
        self.assertEqual(shader.GetPrim(), previewShader.GetPrim())

    def testColorSpaceToken(self):
        self.assertEqual(usdex.core.getColorSpaceToken(usdex.core.ColorSpace.eAuto), "auto")
        self.assertEqual(usdex.core.getColorSpaceToken(usdex.core.ColorSpace.eRaw), "raw")
        self.assertEqual(usdex.core.getColorSpaceToken(usdex.core.ColorSpace.eSrgb), "sRGB")

    def testColorSpaceConversions(self):
        greySrgb = Gf.Vec3f(0.5, 0.5, 0.5)
        darkRedSrgb = Gf.Vec3f(0.33, 0.1, 0.1)
        lightGreenSrgb = Gf.Vec3f(0.67, 0.97, 0.67)
        purpleSrgb = Gf.Vec3f(0.45, 0.2, 0.6)
        blackSrgb = Gf.Vec3f(0.03, 0.03, 0.03)

        greyLinear = Gf.Vec3f(0.21404114, 0.21404114, 0.21404114)
        darkRedLinear = Gf.Vec3f(0.0889815256, 0.01002282, 0.01002282)
        lightGreenLinear = Gf.Vec3f(0.406448301, 0.93310684, 0.406448301)
        purpleLinear = Gf.Vec3f(0.17064493, 0.033104767, 0.3185467781)
        blackLinear = Gf.Vec3f(0.0023219814, 0.0023219814, 0.0023219814)

        convertedGreyLinear = usdex.core.sRgbToLinear(greySrgb)
        convertedDarkRedLinear = usdex.core.sRgbToLinear(darkRedSrgb)
        convertedLightGreenLinear = usdex.core.sRgbToLinear(lightGreenSrgb)
        convertedPurpleLinear = usdex.core.sRgbToLinear(purpleSrgb)
        convertedBlackLinear = usdex.core.sRgbToLinear(blackSrgb)

        convertedGreySrgb = usdex.core.linearToSrgb(greyLinear)
        convertedDarkRedSrgb = usdex.core.linearToSrgb(darkRedLinear)
        convertedLightGreenSrgb = usdex.core.linearToSrgb(lightGreenLinear)
        convertedPurpleSrgb = usdex.core.linearToSrgb(purpleLinear)
        convertedBlackSrgb = usdex.core.linearToSrgb(blackLinear)

        roundTripGreySrgb = usdex.core.linearToSrgb(convertedGreyLinear)
        roundTripRedSrgb = usdex.core.linearToSrgb(convertedDarkRedLinear)
        roundTripGreenSrgb = usdex.core.linearToSrgb(convertedLightGreenLinear)
        roundTripPurpleSrgb = usdex.core.linearToSrgb(convertedPurpleLinear)
        roundTripBlackSrgb = usdex.core.linearToSrgb(convertedBlackLinear)

        roundTripGreyLinear = usdex.core.sRgbToLinear(convertedGreySrgb)
        roundTripRedLinear = usdex.core.sRgbToLinear(convertedDarkRedSrgb)
        roundTripGreenLinear = usdex.core.sRgbToLinear(convertedLightGreenSrgb)
        roundTripPurpleLinear = usdex.core.sRgbToLinear(convertedPurpleSrgb)
        roundTripBlackLinear = usdex.core.sRgbToLinear(convertedBlackSrgb)

        self.assertVecAlmostEqual(convertedGreyLinear, greyLinear, places=6)
        self.assertVecAlmostEqual(convertedDarkRedLinear, darkRedLinear, places=6)
        self.assertVecAlmostEqual(convertedLightGreenLinear, lightGreenLinear, places=6)
        self.assertVecAlmostEqual(convertedPurpleLinear, purpleLinear, places=6)
        self.assertVecAlmostEqual(convertedBlackLinear, blackLinear, places=6)

        self.assertVecAlmostEqual(convertedGreySrgb, greySrgb, places=6)
        self.assertVecAlmostEqual(convertedDarkRedSrgb, darkRedSrgb, places=6)
        self.assertVecAlmostEqual(convertedLightGreenSrgb, lightGreenSrgb, places=6)
        self.assertVecAlmostEqual(convertedPurpleSrgb, purpleSrgb, places=6)
        self.assertVecAlmostEqual(convertedBlackSrgb, blackSrgb, places=6)

        self.assertVecAlmostEqual(roundTripGreyLinear, greyLinear, places=6)
        self.assertVecAlmostEqual(roundTripRedLinear, darkRedLinear, places=6)
        self.assertVecAlmostEqual(roundTripGreenLinear, lightGreenLinear, places=6)
        self.assertVecAlmostEqual(roundTripPurpleLinear, purpleLinear, places=6)
        self.assertVecAlmostEqual(roundTripBlackLinear, blackLinear, places=6)

        self.assertVecAlmostEqual(roundTripGreySrgb, greySrgb, places=6)
        self.assertVecAlmostEqual(roundTripRedSrgb, darkRedSrgb, places=6)
        self.assertVecAlmostEqual(roundTripGreenSrgb, lightGreenSrgb, places=6)
        self.assertVecAlmostEqual(roundTripPurpleSrgb, purpleSrgb, places=6)
        self.assertVecAlmostEqual(roundTripBlackSrgb, blackSrgb, places=6)

    def testAddPreviewMaterialInterface(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        normalTexture = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))
        ormTexture = Sdf.AssetPath(self.tmpFile(name="ORM", ext="png"))
        opacityTexture = Sdf.AssetPath(self.tmpFile(name="Opacity", ext="png"))
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.25, 0.5, 0.25))
        usdex.core.addNormalTextureToPreviewMaterial(material, normalTexture)
        usdex.core.addOrmTextureToPreviewMaterial(material, ormTexture)
        usdex.core.addOpacityTextureToPreviewMaterial(material, opacityTexture)

        # the material starts with no inputs
        self.assertEqual(material.GetInputs(), [])

        # the material will gain 6 inputs based on the authored surface inputs
        result = usdex.core.addPreviewMaterialInterface(material)
        self.assertTrue(result)
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["NormalTexture", "ORMTexture", "OpacityTexture", "diffuseColor", "ior", "opacityThreshold"],
        )

        # the values are now exposed on the material inputs
        self.assertEqual(material.GetInput("diffuseColor").GetAttr().Get(), Gf.Vec3f(0.25, 0.5, 0.25))
        self.assertEqual(material.GetInput("ior").GetAttr().Get(), 1.0)
        # rather than try to assert the exact epsilon between c++ and python we
        # assert that the threshold is a very small non-zero number
        self.assertGreater(material.GetInput("opacityThreshold").GetAttr().Get(), 0)
        self.assertLess(material.GetInput("opacityThreshold").GetAttr().Get(), 1e-6)
        self.assertEqual(material.GetInput("NormalTexture").GetAttr().Get().path, normalTexture)
        self.assertEqual(material.GetInput("ORMTexture").GetAttr().Get().path, ormTexture)
        self.assertEqual(material.GetInput("OpacityTexture").GetAttr().Get().path, opacityTexture)

        # the material inputs are driving the shader inputs
        consumers = material.ComputeInterfaceInputConsumersMap()
        self.assertEqual(
            sorted([x for x in consumers.keys()], key=lambda x: x.GetFullName()),
            sorted([x for x in material.GetInterfaceInputs()], key=lambda x: x.GetFullName()),
        )
        for materialInput, destinations in consumers.items():
            for dest in destinations:
                # the destination has no opinion of its own
                self.assertFalse(dest.GetAttr().HasAuthoredValue())
                # the destination is properly connected to the source
                source, sourceAttr, sourceType = dest.GetConnectedSource()
                self.assertEqual(sourceType, UsdShade.AttributeType.Input)
                self.assertEqual(source.GetInput(sourceAttr).GetAttr(), materialInput.GetAttr())
                self.assertEqual(UsdShade.Utils.GetValueProducingAttributes(dest), [materialInput.GetAttr()])

        # all authored data is valid
        self.assertIsValidUsd(stage)

    def testAddPreviewMaterialInterfaceFailures(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # an invalid material will error gracefully
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, "UsdShadeMaterial.*is not valid.")]):
            result = usdex.core.addPreviewMaterialInterface(UsdShade.Material())
        self.assertFalse(result)

        # non-UPS render contexts will error gracefully
        otherMaterial = UsdShade.Material.Define(stage, materials.GetPath().AppendChild("NonUniversal"))
        otherShader = UsdShade.Shader.Define(stage, otherMaterial.GetPath().AppendChild("NonUniversalShader"))
        otherMaterial.CreateSurfaceOutput("foo").ConnectToSource(otherShader.CreateOutput("out", Sdf.ValueTypeNames.Token))
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*does not have a valid surface shader for the universal render context."),
            ],
        ):
            result = usdex.core.addPreviewMaterialInterface(otherMaterial)
        self.assertFalse(result)

        # a material with no surface outputs will error gracefully
        badMaterial = usdex.core.definePreviewMaterial(materials, "NoSurface", Gf.Vec3f(0.25, 0.5, 0.25))
        badMaterial.GetSurfaceOutput().ClearSources()
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*does not have a valid surface shader for the universal render context."),
            ],
        ):
            result = usdex.core.addPreviewMaterialInterface(badMaterial)
        self.assertFalse(result)

        # multiple render contexts will error gracefully
        multiContextMaterial = usdex.core.definePreviewMaterial(materials, "MultiContext", Gf.Vec3f(0.25, 0.5, 0.25))
        otherShader = UsdShade.Shader.Define(stage, multiContextMaterial.GetPath().AppendChild("NonUniversalShader"))
        multiContextMaterial.CreateSurfaceOutput("foo").ConnectToSource(otherShader.CreateOutput("out", Sdf.ValueTypeNames.Token))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*has 2 effective surface outputs.")]):
            result = usdex.core.addPreviewMaterialInterface(multiContextMaterial)
        self.assertFalse(result)

    def testAddPreviewMaterialInterfaceFromStrongerLayer(self):
        # build a layered stage
        weakerSubLayer = self.tmpLayer(name="Weaker")
        strongerSubLayer = self.tmpLayer(name="Stronger")
        rootLayer = Sdf.Layer.CreateAnonymous(tag="Root")
        rootLayer.subLayerPaths.append(strongerSubLayer.identifier)
        rootLayer.subLayerPaths.append(weakerSubLayer.identifier)
        stage = Usd.Stage.Open(rootLayer)

        # define the top level structure in the root layer
        stage.SetEditTarget(Usd.EditTarget(rootLayer))
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # define the material in the weaker layer
        stage.SetEditTarget(Usd.EditTarget(weakerSubLayer))
        normalTexture = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))
        ormTexture = Sdf.AssetPath(self.tmpFile(name="ORM", ext="png"))
        opacityTexture = Sdf.AssetPath(self.tmpFile(name="Opacity", ext="png"))
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.25, 0.5, 0.25))
        usdex.core.addNormalTextureToPreviewMaterial(material, normalTexture)
        usdex.core.addOrmTextureToPreviewMaterial(material, ormTexture)
        usdex.core.addOpacityTextureToPreviewMaterial(material, opacityTexture)

        # the material starts with no inputs
        self.assertEqual(material.GetInterfaceInputs(), [])

        # add the interface from the stronger layer
        stage.SetEditTarget(Usd.EditTarget(strongerSubLayer))
        result = usdex.core.addPreviewMaterialInterface(material)
        self.assertTrue(result)

        # the material will gain 6 inputs based on the authored surface inputs
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["NormalTexture", "ORMTexture", "OpacityTexture", "diffuseColor", "ior", "opacityThreshold"],
        )

        # the values are now exposed on the material inputs
        self.assertEqual(material.GetInput("diffuseColor").GetAttr().Get(), Gf.Vec3f(0.25, 0.5, 0.25))
        self.assertEqual(material.GetInput("ior").GetAttr().Get(), 1.0)
        # rather than try to assert the exact epsilon between c++ and python we
        # assert that the threshold is a very small non-zero number
        self.assertGreater(material.GetInput("opacityThreshold").GetAttr().Get(), 0)
        self.assertLess(material.GetInput("opacityThreshold").GetAttr().Get(), 1e-6)
        self.assertEqual(material.GetInput("NormalTexture").GetAttr().Get().path, normalTexture)
        self.assertEqual(material.GetInput("ORMTexture").GetAttr().Get().path, ormTexture)
        self.assertEqual(material.GetInput("OpacityTexture").GetAttr().Get().path, opacityTexture)

        # the material inputs are driving the shader inputs
        consumers = material.ComputeInterfaceInputConsumersMap()
        self.assertEqual(
            sorted([x for x in consumers.keys()], key=lambda x: x.GetFullName()),
            sorted([x for x in material.GetInterfaceInputs()], key=lambda x: x.GetFullName()),
        )
        for materialInput, destinations in consumers.items():
            for dest in destinations:
                # the destination still has its original opinion coming from the weaker layer
                self.assertTrue(dest.GetAttr().HasAuthoredValue())
                # since the destination is properly connected to the source, the interface input is still the value-providing attribute
                source, sourceAttr, sourceType = dest.GetConnectedSource()
                self.assertEqual(sourceType, UsdShade.AttributeType.Input)
                self.assertEqual(source.GetInput(sourceAttr).GetAttr(), materialInput.GetAttr())
                self.assertEqual(UsdShade.Utils.GetValueProducingAttributes(dest), [materialInput.GetAttr()])

        # all authored data is valid
        self.assertIsValidUsd(stage)

    def testRemoveMaterialInterfaceAndBakeValues(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        normalTexture = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))
        ormTexture = Sdf.AssetPath(self.tmpFile(name="ORM", ext="png"))
        opacityTexture = Sdf.AssetPath(self.tmpFile(name="Opacity", ext="png"))
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.25, 0.5, 0.25))
        usdex.core.addNormalTextureToPreviewMaterial(material, normalTexture)
        usdex.core.addOrmTextureToPreviewMaterial(material, ormTexture)
        usdex.core.addOpacityTextureToPreviewMaterial(material, opacityTexture)
        usdex.core.addPreviewMaterialInterface(material)

        # the material starts with 6 inputs
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["NormalTexture", "ORMTexture", "OpacityTexture", "diffuseColor", "ior", "opacityThreshold"],
        )

        # removing the interface leaves no inputs on the material
        result = usdex.core.removeMaterialInterface(material)
        self.assertTrue(result)
        self.assertEqual(material.GetInterfaceInputs(), [])

        # the previously exposed values have been baked down onto the shaders
        diffuseInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("diffuseColor")
        self.assertEqual(diffuseInput.GetConnectedSources(), ([], []))
        self.assertTrue(diffuseInput.GetAttr().HasAuthoredValue())
        self.assertEqual(diffuseInput.GetAttr().Get(), Gf.Vec3f(0.25, 0.5, 0.25))
        iorInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("ior")
        self.assertEqual(iorInput.GetConnectedSources(), ([], []))
        self.assertTrue(iorInput.GetAttr().HasAuthoredValue())
        self.assertEqual(iorInput.GetAttr().Get(), 1.0)
        opacityThresholdInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("opacityThreshold")
        self.assertEqual(opacityThresholdInput.GetConnectedSources(), ([], []))
        self.assertTrue(opacityThresholdInput.GetAttr().HasAuthoredValue())
        # rather than try to assert the exact epsilon between c++ and python we
        # assert that the threshold is a very small non-zero number
        self.assertGreater(opacityThresholdInput.GetAttr().Get(), 0)
        self.assertLess(opacityThresholdInput.GetAttr().Get(), 1e-6)
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("NormalTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertTrue(fileInput.GetAttr().HasAuthoredValue())
        self.assertEqual(fileInput.GetAttr().Get().path, normalTexture)
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("ORMTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertTrue(fileInput.GetAttr().HasAuthoredValue())
        self.assertEqual(fileInput.GetAttr().Get().path, ormTexture)
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("OpacityTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertTrue(fileInput.GetAttr().HasAuthoredValue())
        self.assertEqual(fileInput.GetAttr().Get().path, opacityTexture)

        # all authored data remains valid
        self.assertIsValidUsd(stage)

        # an invalid material will error gracefully
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, "UsdShadeMaterial.*is not valid.")]):
            result = usdex.core.removeMaterialInterface(UsdShade.Material())
        self.assertFalse(result)

    def testRemoveMaterialInterfaceAndDiscardValues(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        normalTexture = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))
        ormTexture = Sdf.AssetPath(self.tmpFile(name="ORM", ext="png"))
        opacityTexture = Sdf.AssetPath(self.tmpFile(name="Opacity", ext="png"))
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.25, 0.5, 0.25))
        usdex.core.addNormalTextureToPreviewMaterial(material, normalTexture)
        usdex.core.addOrmTextureToPreviewMaterial(material, ormTexture)
        usdex.core.addOpacityTextureToPreviewMaterial(material, opacityTexture)
        usdex.core.addPreviewMaterialInterface(material)

        # the material starts with 6 inputs
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["NormalTexture", "ORMTexture", "OpacityTexture", "diffuseColor", "ior", "opacityThreshold"],
        )

        # removing the interface leaves no inputs on the material
        result = usdex.core.removeMaterialInterface(material, bakeValues=False)
        self.assertTrue(result)
        self.assertEqual(material.GetInterfaceInputs(), [])

        # the previously exposed values have been discarded
        diffuseInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("diffuseColor")
        self.assertEqual(diffuseInput.GetConnectedSources(), ([], []))
        self.assertFalse(diffuseInput.GetAttr().HasAuthoredValue())
        iorInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("ior")
        self.assertEqual(iorInput.GetConnectedSources(), ([], []))
        self.assertFalse(iorInput.GetAttr().HasAuthoredValue())
        opacityThresholdInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("opacityThreshold")
        self.assertEqual(opacityThresholdInput.GetConnectedSources(), ([], []))
        self.assertFalse(opacityThresholdInput.GetAttr().HasAuthoredValue())
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("NormalTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertFalse(fileInput.GetAttr().HasAuthoredValue())
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("ORMTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertFalse(fileInput.GetAttr().HasAuthoredValue())
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("OpacityTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertFalse(fileInput.GetAttr().HasAuthoredValue())

        # all authored data remains valid
        self.assertIsValidUsd(
            stage,
        )

    def testRemoveMaterialInterfaceFromStrongerLayer(self):
        # build a layered stage
        weakerSubLayer = self.tmpLayer(name="Weaker")
        strongerSubLayer = self.tmpLayer(name="Stronger")
        rootLayer = Sdf.Layer.CreateAnonymous(tag="Root")
        rootLayer.subLayerPaths.append(strongerSubLayer.identifier)
        rootLayer.subLayerPaths.append(weakerSubLayer.identifier)
        stage = Usd.Stage.Open(rootLayer)

        # define the top level structure in the root layer
        stage.SetEditTarget(Usd.EditTarget(rootLayer))
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # define the material in the weaker layer
        stage.SetEditTarget(Usd.EditTarget(weakerSubLayer))
        normalTexture = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))
        ormTexture = Sdf.AssetPath(self.tmpFile(name="ORM", ext="png"))
        opacityTexture = Sdf.AssetPath(self.tmpFile(name="Opacity", ext="png"))
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.25, 0.5, 0.25))
        usdex.core.addNormalTextureToPreviewMaterial(material, normalTexture)
        usdex.core.addOrmTextureToPreviewMaterial(material, ormTexture)
        usdex.core.addOpacityTextureToPreviewMaterial(material, opacityTexture)
        usdex.core.addPreviewMaterialInterface(material)

        # the material starts with 6 inputs
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["NormalTexture", "ORMTexture", "OpacityTexture", "diffuseColor", "ior", "opacityThreshold"],
        )

        # remove the interface from the stronger layer
        stage.SetEditTarget(Usd.EditTarget(strongerSubLayer))
        result = usdex.core.removeMaterialInterface(material)
        self.assertTrue(result)

        # the material inputs remain, as they cannot be removed via the current edit target, but their values are blocked
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["NormalTexture", "ORMTexture", "OpacityTexture", "diffuseColor", "ior", "opacityThreshold"],
        )
        for source in material.GetInterfaceInputs():
            self.assertFalse(source.GetAttr().HasAuthoredValue())

        # the previously exposed values have been baked down onto the shaders
        diffuseInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("diffuseColor")
        self.assertEqual(diffuseInput.GetConnectedSources(), ([], []))
        self.assertTrue(diffuseInput.GetAttr().HasAuthoredValue())
        self.assertEqual(diffuseInput.GetAttr().Get(), Gf.Vec3f(0.25, 0.5, 0.25))
        iorInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("ior")
        self.assertEqual(iorInput.GetConnectedSources(), ([], []))
        self.assertTrue(iorInput.GetAttr().HasAuthoredValue())
        self.assertEqual(iorInput.GetAttr().Get(), 1.0)
        opacityThresholdInput = UsdShade.Shader(material.GetPrim().GetChild("PreviewSurface")).GetInput("opacityThreshold")
        self.assertEqual(opacityThresholdInput.GetConnectedSources(), ([], []))
        self.assertTrue(opacityThresholdInput.GetAttr().HasAuthoredValue())
        # rather than try to assert the exact epsilon between c++ and python we
        # assert that the threshold is a very small non-zero number
        self.assertGreater(opacityThresholdInput.GetAttr().Get(), 0)
        self.assertLess(opacityThresholdInput.GetAttr().Get(), 1e-6)
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("NormalTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertTrue(fileInput.GetAttr().HasAuthoredValue())
        self.assertEqual(fileInput.GetAttr().Get().path, normalTexture)
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("ORMTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertTrue(fileInput.GetAttr().HasAuthoredValue())
        self.assertEqual(fileInput.GetAttr().Get().path, ormTexture)
        fileInput = UsdShade.Shader(material.GetPrim().GetChild("OpacityTexture")).GetInput("file")
        self.assertEqual(fileInput.GetConnectedSources(), ([], []))
        self.assertTrue(fileInput.GetAttr().HasAuthoredValue())
        self.assertEqual(fileInput.GetAttr().Get().path, opacityTexture)

        # all authored data remains valid
        self.assertIsValidUsd(stage)


class DefinePreviewMaterialTest(usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.definePreviewMaterial
    requiredArgs = tuple([Gf.Vec3f(1.0, 1.0, 1.0)])
    typeName = "Material"
    schema = UsdShade.Material
    requiredPropertyNames = set()

    def assertIsSurfaceShader(self, material: UsdShade.Material, shader: UsdShade.Shader):
        surfaceOutput = material.GetSurfaceOutput()
        self.assertTrue(surfaceOutput.HasConnectedSource())
        surface = surfaceOutput.GetConnectedSource()[0]
        self.assertEqual(surface.GetOutput(UsdShade.Tokens.surface).GetAttr(), shader.GetOutput(UsdShade.Tokens.surface).GetAttr())

    def assertInvalidPreviewMaterialForTextureFunctions(self, parent: Usd.Prim, texture: Sdf.AssetPath):
        # an invalid material will error gracefully
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addDiffuseTextureToPreviewMaterial(UsdShade.Material(), texture)
        self.assertFalse(result)

        # an invalid surface shader will error gracefully
        badMaterial = UsdShade.Material.Define(parent.GetStage(), parent.GetPath().AppendChild("BadMaterial"))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addDiffuseTextureToPreviewMaterial(badMaterial, texture)
        self.assertFalse(result)

        # a surface shader without an ID will error gracefully
        otherShader = UsdShade.Shader.Define(parent.GetStage(), badMaterial.GetPath().AppendChild("NoShaderId"))
        badMaterial.CreateSurfaceOutput().ConnectToSource(otherShader.CreateOutput(UsdShade.Tokens.surface, Sdf.ValueTypeNames.Token))
        self.assertIsSurfaceShader(badMaterial, otherShader)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addDiffuseTextureToPreviewMaterial(badMaterial, texture)
        self.assertFalse(result)

        # an surface shader that is not a UPS will error gracefully
        otherShader.SetShaderId("UsdUvTexture")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addDiffuseTextureToPreviewMaterial(badMaterial, texture)
        self.assertFalse(result)

    def assertValidPreviewMaterialTextureNetwork(
        self,
        material: UsdShade.Material,
        texture: Sdf.AssetPath,
        textureReaderName: str,
        colorSpace: usdex.core.ColorSpace,
        fallbackColor: Gf.Vec3f,
        connectionInfo: List[Tuple[str, Sdf.ValueTypeName, str]],
    ):
        uvReader = UsdShade.Shader(material.GetPrim().GetChild("Primvar_st_float2"))
        self.assertTrue(uvReader)
        self.assertEqual(uvReader.GetShaderId(), "UsdPrimvarReader_float2")
        self.assertEqual(uvReader.GetInput("varname").GetAttr().Get(), UsdUtils.GetPrimaryUVSetName())

        textureReader = UsdShade.Shader(material.GetPrim().GetChild(textureReaderName))
        self.assertTrue(textureReader)
        self.assertEqual(textureReader.GetShaderId(), "UsdUVTexture")
        self.assertEqual(textureReader.GetInput("file").GetAttr().Get().path, texture)
        self.assertEqual(textureReader.GetInput("sourceColorSpace").GetAttr().Get(), usdex.core.getColorSpaceToken(colorSpace))
        # fallback is a float4 with a solid alpha channel
        self.assertEqual(textureReader.GetInput("fallback").GetAttr().Get(), Gf.Vec4f(fallbackColor[0], fallbackColor[1], fallbackColor[2], 1.0))
        # tex coord input is driven by the tex coord reader
        self.assertTrue(textureReader.GetInput("st").HasConnectedSource())
        self.assertEqual(textureReader.GetInput("st").GetConnectedSource()[0].GetOutputs()[0].GetAttr(), uvReader.GetOutput("result").GetAttr())

        surface = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(surface)
        self.assertEqual(surface.GetPrim().GetName(), "PreviewSurface")
        self.assertEqual(surface.GetShaderId(), "UsdPreviewSurface")

        # verify the connectionInfo
        for inputName, inputTypeName, outputName in connectionInfo:
            self.assertTrue(surface.GetInput(inputName).HasConnectedSource())
            self.assertEqual(surface.GetInput(inputName).GetTypeName(), inputTypeName)
            source, sourceAttr, sourceType = surface.GetInput(inputName).GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Output)
            self.assertEqual(
                source.GetOutput(sourceAttr).GetAttr(),
                textureReader.GetOutput(outputName).GetAttr(),
                msg=f"Incorrect connection for {inputName} ({inputTypeName}) -> {outputName}",
            )
            # the only opinion is from the connection
            self.assertFalse(surface.GetInput(inputName).GetAttr().HasAuthoredValue())
            self.assertEqual(len(surface.GetInput(inputName).GetValueProducingAttributes()), 1)
            self.assertEqual(surface.GetInput(inputName).GetValueProducingAttributes()[0], textureReader.GetOutput(outputName).GetAttr())

    def assertValidPreviewMaterialPrimvarNetwork(
        self,
        material: UsdShade.Material,
        primvarInfo: List[Tuple[str, str, Any]],  # inputName, primvarName, fallbackValue
    ):
        surfaceShader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(surfaceShader)
        self.assertEqual(surfaceShader.GetPrim().GetName(), "PreviewSurface")
        self.assertEqual(surfaceShader.GetShaderId(), "UsdPreviewSurface")

        # verify the primvarInfo
        for inputName, primvarName, fallbackValue in primvarInfo:
            input = surfaceShader.GetInput(inputName)
            outputName = "result"
            outputTypeName = input.GetTypeName()
            if outputTypeName == Sdf.ValueTypeNames.Color3f:
                outputTypeName = Sdf.ValueTypeNames.Float3

            # Make the primvar name valid for the shader prim by first replacing any ':' with '_'
            validPrimvarName = primvarName.replace(":", "_")
            primvarReaderName = usdex.core.getValidPrimName(f"Primvar_{validPrimvarName}_{outputTypeName}")
            primvarReader = UsdShade.Shader(material.GetPrim().GetChild(primvarReaderName))
            self.assertTrue(primvarReader)
            self.assertEqual(primvarReader.GetShaderId(), f"UsdPrimvarReader_{outputTypeName}")
            self.assertEqual(str(primvarReader.GetOutput(outputName).GetTypeName()), str(outputTypeName))
            self.assertEqual(primvarReader.GetInput("varname").GetAttr().Get(), primvarName)
            if fallbackValue:
                self.assertEqual(primvarReader.GetInput("fallback").GetTypeName(), outputTypeName)
                self.assertAlmostEqual(primvarReader.GetInput("fallback").GetAttr().Get(), fallbackValue)
            else:
                self.assertFalse(primvarReader.GetInput("fallback"))

            self.assertTrue(input.HasConnectedSource())
            source, sourceAttr, sourceType = input.GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Output)
            self.assertEqual(
                source.GetOutput(sourceAttr).GetAttr(),
                primvarReader.GetOutput(outputName).GetAttr(),
                msg=f"Incorrect connection for {inputName} ({input.GetTypeName()}) -> {outputName}",
            )
            # the only opinion is from the connection
            self.assertFalse(input.GetAttr().HasAuthoredValue())
            self.assertEqual(len(input.GetValueProducingAttributes()), 1)
            self.assertEqual(input.GetValueProducingAttributes()[0], primvarReader.GetOutput(outputName).GetAttr())

    def testPreviewMaterialShaders(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # the material is created successfully
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.0, 0.5, 1.0), opacity=0.2, roughness=0.3, metallic=0.4)
        self.assertTrue(material)

        # the shader is now in place
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim().GetName(), "PreviewSurface")
        self.assertEqual(shader.GetShaderId(), "UsdPreviewSurface")

        # the shader should include a Color named "diffuseColor" that has the effective specified value
        shaderInput = shader.GetInput("diffuseColor")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertVecAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), Gf.Vec3f(0.0, 0.5, 1.0))

        # the shader should include a Float named "opacity" that has the effective specified value
        shaderInput = shader.GetInput("opacity")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.2)

        # the shader should include a Float named "roughness" that has the effective specified value
        shaderInput = shader.GetInput("roughness")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.3)

        # the shader should include a Float named "metallic" that has the effective specified value
        shaderInput = shader.GetInput("metallic")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.4)

        # the shader is driving the surface of the material for the universal render context
        self.assertIsSurfaceShader(material, shader)

        # the shader is driving the surface of the material for the universal render context
        displacementOutput = material.GetDisplacementOutput()
        self.assertTrue(displacementOutput.HasConnectedSource())
        displacement = displacementOutput.GetConnectedSource()[0]
        self.assertEqual(displacement.GetOutput(UsdShade.Tokens.displacement).GetAttr(), shader.GetOutput(UsdShade.Tokens.displacement).GetAttr())

        # the volume output was not setup as this is not a volumetric material
        volumeOutput = material.GetVolumeOutput()
        self.assertFalse(volumeOutput.HasConnectedSource())
        self.assertFalse(shader.GetOutput(UsdShade.Tokens.volume))

        # all authored data is valid
        self.assertIsValidUsd(stage)

    def testInvalidInputs(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # An out-of-range opacity will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Opacity value -0.000001 is outside range")]):
            material = usdex.core.definePreviewMaterial(materials, "BadOpacity", Gf.Vec3f(1, 0, 0), opacity=-0.000001)
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Opacity value 1.000001 is outside range")]):
            material = usdex.core.definePreviewMaterial(materials, "BadOpacity", Gf.Vec3f(1, 0, 0), opacity=1.000001)
        self.assertFalse(material)

        # An out-of-range roughness will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Roughness value -0.000001 is outside range")]):
            material = usdex.core.definePreviewMaterial(materials, "BadRoughness", Gf.Vec3f(1, 0, 0), roughness=-0.000001)
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Roughness value 1.000001 is outside range")]):
            material = usdex.core.definePreviewMaterial(materials, "BadRoughness", Gf.Vec3f(1, 0, 0), roughness=1.000001)
        self.assertFalse(material)

        # An out-of-range metallic will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Metallic value -0.000001 is outside range")]):
            material = usdex.core.definePreviewMaterial(materials, "BadMetallic", Gf.Vec3f(1, 0, 0), metallic=-0.000001)
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Metallic value 1.000001 is outside range")]):
            material = usdex.core.definePreviewMaterial(materials, "BadMetallic", Gf.Vec3f(1, 0, 0), metallic=1.000001)
        self.assertFalse(material)

        material = usdex.core.definePreviewMaterial(materials, "LowestValidInputs", Gf.Vec3f(0, 0, 0), opacity=0, roughness=0, metallic=0)
        self.assertTrue(material)
        self.assertIsValidUsd(stage)

        material = usdex.core.definePreviewMaterial(materials, "HighestValidInputs", Gf.Vec3f(1, 1, 1), opacity=1, roughness=1, metallic=1)
        self.assertTrue(material)
        self.assertIsValidUsd(stage)

    def testAddDiffuseTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # a valid preview material will successfully add a diffuse texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.0, 0.5, 1.0))
        result = usdex.core.addDiffuseTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="DiffuseTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(0.0, 0.5, 1.0),
            connectionInfo=[("diffuseColor", Sdf.ValueTypeNames.Color3f, "rgb")],
        )

        self.assertIsValidUsd(stage)

    def testAddNormalTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # a valid preview material will successfully add a normals texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))
        result = usdex.core.addNormalTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="NormalTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(0.0, 0.0, 1.0),
            connectionInfo=[("normal", Sdf.ValueTypeNames.Normal3f, "rgb")],
        )
        textureReader = UsdShade.Shader(material.GetPrim().GetChild("NormalTexture"))
        self.assertEqual(textureReader.GetInput("scale").GetAttr().Get(), Gf.Vec4f(2, 2, 2, 1))
        self.assertEqual(textureReader.GetInput("bias").GetAttr().Get(), Gf.Vec4f(-1, -1, -1, 0))

        # a non 8-bit texture will successfully add a normals texture, but will not adjust scale & bias
        texture = Sdf.AssetPath(self.tmpFile(name="N", ext="exr"))
        material = usdex.core.definePreviewMaterial(materials, "GoodFormat", Gf.Vec3f(0.8, 0.8, 0.8))
        result = usdex.core.addNormalTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="NormalTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(0.0, 0.0, 1.0),
            connectionInfo=[("normal", Sdf.ValueTypeNames.Normal3f, "rgb")],
        )
        textureReader = UsdShade.Shader(material.GetPrim().GetChild("NormalTexture"))
        self.assertFalse(textureReader.GetInput("scale").GetAttr())
        self.assertFalse(textureReader.GetInput("bias").GetAttr())

        self.assertIsValidUsd(stage)

    def testAddRelativeNormalTexture(self):
        # Test relative normal texture paths in root layer, session layer, and subLayers resident in subdirectories
        identifier = self.tmpFile("test", "usda")
        stage = usdex.core.createStage(identifier, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        def subDirTmpFile(subdir: str = "", name: str = "", ext: str = "") -> str:
            # Helper function to create a temp file under the temp base dir within a subdir
            tempDir = pathlib.Path(self.tmpBaseDir()) / subdir
            tempDir.mkdir(parents=True, exist_ok=True)
            (handle, fileName) = tempfile.mkstemp(prefix=f"{os.path.join(tempDir, name)}_", suffix=f".{ext}")
            os.close(handle)
            return fileName

        identifierParent = pathlib.Path(identifier).parent
        sameDirTextureFile = self.tmpFile(name="N", ext="png")
        subDirTextureFile = subDirTmpFile(subdir="textures", name="N", ext="png")

        # ./N.png - same relative
        # N.png - same "search relative"
        # ./textures/N.png - subdir relative
        # textures/N.png - subdir "search relative"
        textureAssetPaths = [
            f"./{pathlib.Path(sameDirTextureFile).name}",
            f"{pathlib.Path(sameDirTextureFile).name}",
            f"./{pathlib.Path(subDirTextureFile).relative_to(identifierParent).as_posix()}",
            f"{pathlib.Path(subDirTextureFile).relative_to(identifierParent).as_posix()}",
        ]

        def assertRelativeNormalTex(texture: Sdf.AssetPath, materialName: str):
            # An 8-bit texture with a relative path needs a scale & bias
            material = usdex.core.definePreviewMaterial(materials, materialName, Gf.Vec3f(0.8, 0.8, 0.8))
            result = usdex.core.addNormalTextureToPreviewMaterial(material, texture)
            self.assertTrue(result)
            self.assertValidPreviewMaterialTextureNetwork(
                material,
                texture,
                textureReaderName="NormalTexture",
                colorSpace=usdex.core.ColorSpace.eRaw,
                fallbackColor=Gf.Vec3f(0.0, 0.0, 1.0),
                connectionInfo=[("normal", Sdf.ValueTypeNames.Normal3f, "rgb")],
            )
            textureReader = UsdShade.Shader(material.GetPrim().GetChild("NormalTexture"))
            self.assertEqual(textureReader.GetInput("scale").GetAttr().Get(), Gf.Vec4f(2, 2, 2, 1))
            self.assertEqual(textureReader.GetInput("bias").GetAttr().Get(), Gf.Vec4f(-1, -1, -1, 0))

        # Define materials in the root layer
        for i, texturePath in enumerate(textureAssetPaths):
            assertRelativeNormalTex(Sdf.AssetPath(texturePath), f"RelativeNormal_{i}")

        # Define materials in the session layer
        stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))
        for i, texturePath in enumerate(textureAssetPaths):
            assertRelativeNormalTex(Sdf.AssetPath(texturePath), f"RelativeNormal_Session_{i}")

        # Define materials in a sublayer in subdirectory
        subDirIdentifier = subDirTmpFile(subdir="sublayers", name="materials", ext="usda")
        layer = Sdf.Layer.CreateAnonymous()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_STATUS_TYPE, "Exporting")]):
            success = usdex.core.exportLayer(layer, subDirIdentifier, self.defaultAuthoringMetadata)
        self.assertTrue(success)
        subLayer = Sdf.Layer.FindOrOpen(subDirIdentifier)
        stage.GetRootLayer().subLayerPaths.append(subDirIdentifier)
        stage.SetEditTarget(Usd.EditTarget(subLayer))

        # ../N.png - parent dir relative
        # ../textures/N.png - subdir of parent dir relative
        textureAssetPaths = [
            f"../{pathlib.Path(sameDirTextureFile).name}",
            f"../{pathlib.Path(subDirTextureFile).relative_to(identifierParent).as_posix()}",
        ]
        for i, texturePath in enumerate(textureAssetPaths):
            assertRelativeNormalTex(Sdf.AssetPath(texturePath), f"RelativeNormal_Sublayer_{i}")

        self.assertIsValidUsd(stage)

    def testAddOrmTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="ORM", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # a valid preview material will successfully add a ORM texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))
        result = usdex.core.addOrmTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="ORMTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(1.0, 0.5, 0.0),
            connectionInfo=[
                ("occlusion", Sdf.ValueTypeNames.Float, "r"),
                ("roughness", Sdf.ValueTypeNames.Float, "g"),
                ("metallic", Sdf.ValueTypeNames.Float, "b"),
            ],
        )

        # the originally defined roughness and metallic values are used in the fallback (opacity is not relevant)
        material = usdex.core.definePreviewMaterial(materials, "InitialValues", Gf.Vec3f(0.8, 0.8, 0.8), opacity=0.8, roughness=0.25, metallic=0.9)
        result = usdex.core.addOrmTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="ORMTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(1.0, 0.25, 0.9),
            connectionInfo=[
                ("occlusion", Sdf.ValueTypeNames.Float, "r"),
                ("roughness", Sdf.ValueTypeNames.Float, "g"),
                ("metallic", Sdf.ValueTypeNames.Float, "b"),
            ],
        )

        self.assertIsValidUsd(stage)

    def testAddRoughnessTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="roughness", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # a valid preview material will successfully add a ORM texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))
        result = usdex.core.addRoughnessTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="RoughnessTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(0.5, 0.0, 0.0),
            connectionInfo=[("roughness", Sdf.ValueTypeNames.Float, "r")],
        )

        # the originally defined roughness value is used in the fallback
        material = usdex.core.definePreviewMaterial(materials, "InitialValues", Gf.Vec3f(0.8, 0.8, 0.8), roughness=0.1)
        result = usdex.core.addRoughnessTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="RoughnessTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(0.1, 0.0, 0.0),
            connectionInfo=[("roughness", Sdf.ValueTypeNames.Float, "r")],
        )

        self.assertIsValidUsd(stage)

    def testAddMetallicTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="metallic", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # a valid preview material will successfully add a ORM texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))
        result = usdex.core.addMetallicTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="MetallicTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(0.0, 0.0, 0.0),
            connectionInfo=[("metallic", Sdf.ValueTypeNames.Float, "r")],
        )

        # the originally defined metallic value is used in the fallback
        material = usdex.core.definePreviewMaterial(materials, "InitialValues", Gf.Vec3f(0.8, 0.8, 0.8), metallic=0.1)
        result = usdex.core.addMetallicTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="MetallicTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(0.1, 0.0, 0.0),
            connectionInfo=[("metallic", Sdf.ValueTypeNames.Float, "r")],
        )

        self.assertIsValidUsd(stage)

    def testAddOpacityTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="opacity", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # a valid preview material will successfully add a ORM texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))
        result = usdex.core.addOpacityTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="OpacityTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(1.0, 0.0, 0.0),
            connectionInfo=[("opacity", Sdf.ValueTypeNames.Float, "r")],
        )
        surface = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertEqual(surface.GetInput("ior").GetAttr().Get(), 1.0)
        # rather than try to assert the exact epsilon between c++ and python we
        # assert that the threshold is a very small non-zero number
        self.assertGreater(surface.GetInput("opacityThreshold").GetAttr().Get(), 0)
        self.assertLess(surface.GetInput("opacityThreshold").GetAttr().Get(), 1e-6)

        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderToInvalidMaterial(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # check invalid material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(UsdShade.Material(), "diffuseColor", "perInstanceColor")
        self.assertFalse(result)

        # check with a non-preview material
        material = usdex.core.createMaterial(materials, "NonPreviewMaterial")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "diffuseColor", "perInstanceColor")
        self.assertFalse(result)
        self.assertIsValidUsd(stage)

    def testAddPrimvarShader(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "diffuseColor", "perInstanceColor")
        self.assertTrue(result)

        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", "perInstanceColor", None),
            ],
        )

        result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "roughness", "perInstanceRoughness")
        self.assertTrue(result)

        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", "perInstanceColor", None),
                ("roughness", "perInstanceRoughness", None),
            ],
        )
        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderWithDiffuseTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "diffuseColor", "perInstanceColor")
        self.assertTrue(result)
        result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "roughness", "perInstanceRoughness")
        self.assertTrue(result)

        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", "perInstanceColor", None),
                ("roughness", "perInstanceRoughness", None),
            ],
        )

        # Check that a diffuse texture can now be assigned
        diffuseTexture = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))
        result = usdex.core.addDiffuseTextureToPreviewMaterial(material, diffuseTexture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [("roughness", "perInstanceRoughness", None)],
        )
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            diffuseTexture,
            textureReaderName="DiffuseTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(0.0, 0.0, 0.0),  # default fallback
            connectionInfo=[("diffuseColor", Sdf.ValueTypeNames.Color3f, "rgb")],
        )

        result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "diffuseColor", "perInstanceColor")
        self.assertTrue(result)
        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", "perInstanceColor", None),
                ("roughness", "perInstanceRoughness", None),
            ],
        )

        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderChangingOutputType(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "diffuseColor", "randomPrimvar")
        self.assertTrue(result)

        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", "randomPrimvar", None),
            ],
        )

        result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "roughness", "randomPrimvar")
        self.assertTrue(result)

        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", "randomPrimvar", None),
                ("roughness", "randomPrimvar", None),
            ],
        )
        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderWithFallbackValue(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        fallbackColors = [None, Gf.Vec3f(0.1, 0.1, 0.1), Gf.Vec3f(0.4, 0.5, 0.6)]
        fallbackRoughnesses = [None, 0.88, 0.3]

        for fallbackColor, fallbackRoughness in zip(fallbackColors, fallbackRoughnesses):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "diffuseColor", "perInstanceColor", fallbackColor)
            self.assertTrue(result)
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "roughness", "perInstanceRoughness", fallbackRoughness)
            self.assertTrue(result)

            self.assertValidPreviewMaterialPrimvarNetwork(
                material,
                [
                    ("diffuseColor", "perInstanceColor", fallbackColor),
                    ("roughness", "perInstanceRoughness", fallbackRoughness),
                ],
            )

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot set fallback.*does not match input type.*")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "diffuseColor", "perInstanceColor", fallbackRoughnesses[-1])
            self.assertTrue(result)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot set fallback.*does not match input type.*")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "roughness", "perInstanceRoughness", fallbackColors[-1])
            self.assertTrue(result)

        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", "perInstanceColor", fallbackColors[-1]),
                ("roughness", "perInstanceRoughness", fallbackRoughnesses[-1]),
            ],
        )
        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderInvalidInputs(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot add primvar.*on surface shader.*")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "invalidInput", "perInstanceColor")
            self.assertFalse(result)

        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        shaderInput = shader.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Int)
        shaderInput.Set(0)
        shaderInput.SetConnectability(UsdShade.Tokens.interfaceOnly)

        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*connectability is interfaceOnly.*")]
        ):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "useSpecularWorkflow", "perInstanceSpec")
            self.assertFalse(result)

        # verify that the connectivity check didn't create the primvar reader
        self.assertFalse(material.GetPrim().GetChild("Primvar_perInstanceSpec_int"))

        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderInvalidNames(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        primvarName = "primvars:invalid:prim:name"
        result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "diffuseColor", primvarName)
        self.assertTrue(result)
        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", primvarName, None),
            ],
        )

        # Get the number of shaders in the material
        numShaders = len(material.GetPrim().GetChildren())

        invalidPrimvarName = "primvars:invalid:prim:n@me"
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*the primvar name is invalid.*")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "metallic", invalidPrimvarName)
            self.assertFalse(result)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*the primvar name is invalid.*")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "metallic", "")
            self.assertFalse(result)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot add primvar.*there is no input with that name.*")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "", primvarName)
            self.assertFalse(result)

        # Verify that the number of shaders in the material is the same
        self.assertEqual(len(material.GetPrim().GetChildren()), numShaders)

        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [
                ("diffuseColor", primvarName, None),
            ],
        )
        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderUnsupportedUsdPreviewSurfaceInputType(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        shaderInput = shader.CreateInput("highPrecisionDouble", Sdf.ValueTypeNames.Double)
        self.assertTrue(shaderInput)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*<double> is not supported.*")]):
            result = usdex.core.addPrimvarShaderToPreviewMaterial(material, "highPrecisionDouble", "paintHighPrecisionDouble")
            self.assertFalse(result)

    def testTexturesShareTexCoordReader(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        diffuseTexture = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))
        normalTexture = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))

        # a valid preview material will successfully add a diffuse texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.0, 0.5, 1.0))
        result = usdex.core.addDiffuseTextureToPreviewMaterial(material, diffuseTexture)
        self.assertTrue(result)
        result = usdex.core.addNormalTextureToPreviewMaterial(material, normalTexture)
        self.assertTrue(result)

        # both inputs are driven by the expected textures
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            diffuseTexture,
            textureReaderName="DiffuseTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(0.0, 0.5, 1.0),
            connectionInfo=[("diffuseColor", Sdf.ValueTypeNames.Color3f, "rgb")],
        )
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            normalTexture,
            textureReaderName="NormalTexture",
            colorSpace=usdex.core.ColorSpace.eRaw,
            fallbackColor=Gf.Vec3f(0.0, 0.0, 1.0),
            connectionInfo=[("normal", Sdf.ValueTypeNames.Normal3f, "rgb")],
        )

        # the primvar reader for tex coords is shared
        def findTextureReaders(stage):
            textureReaders = []
            for prim in stage.Traverse():
                shader = UsdShade.Shader(prim)
                if shader and shader.GetShaderId() == "UsdPrimvarReader_float2":
                    textureReaders.append(shader)
            return textureReaders

        textureReaders = findTextureReaders(stage)
        self.assertEqual(len(textureReaders), 1)
        # assertValidPreviewMaterialTextureNetwork will have already ensured both textures are driven by TexCoordReader
        self.assertEqual(textureReaders[0].GetPrim(), material.GetPrim().GetChild("Primvar_st_float2"))

    def testDefinePreviewMaterialPrimOverload(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/World/PreviewMaterial", "Material")

        # Define the material using the prim overload
        color = Gf.Vec3f(0.5, 0.7, 0.9)
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Material.*to.*Material.*Expected original type to be "" or .*Scope.*')],
        ):
            material = usdex.core.definePreviewMaterial(prim, color)

        # Verify the prim was created correctly
        self.assertTrue(material)
        self.assertEqual(material.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(material.GetPrim().GetTypeName(), "Material")

        # Verify the material has the expected shader network
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)

        # Verify the diffuse color was set
        diffuseColorInput = shader.GetInput("diffuseColor")
        self.assertTrue(diffuseColorInput.GetAttr().HasAuthoredValue())
        self.assertEqual(diffuseColorInput.GetAttr().Get(), color)

    def testDefinePreviewMaterialPrimOverloadWithOptionalParams(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/World/PreviewMaterialWithParams", "Material")

        # Define the material with optional parameters
        color = Gf.Vec3f(0.5, 0.7, 0.9)
        opacity = 0.8
        roughness = 0.3
        metallic = 0.5

        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Material.*to.*Material.*Expected original type to be "" or .*Scope.*')],
        ):
            material = usdex.core.definePreviewMaterial(prim, color, opacity=opacity, roughness=roughness, metallic=metallic)

        # Verify the prim was created correctly
        self.assertTrue(material)
        self.assertEqual(material.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(material.GetPrim().GetTypeName(), "Material")

        # Verify the material has the expected shader network
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)

        # Verify the parameters were set
        diffuseColorInput = shader.GetInput("diffuseColor")
        self.assertTrue(diffuseColorInput.GetAttr().HasAuthoredValue())
        self.assertEqual(diffuseColorInput.GetAttr().Get(), color)

        opacityInput = shader.GetInput("opacity")
        self.assertTrue(opacityInput.GetAttr().HasAuthoredValue())
        self.assertAlmostEqual(opacityInput.GetAttr().Get(), opacity, places=6)

        roughnessInput = shader.GetInput("roughness")
        self.assertTrue(roughnessInput.GetAttr().HasAuthoredValue())
        self.assertAlmostEqual(roughnessInput.GetAttr().Get(), roughness, places=6)

        metallicInput = shader.GetInput("metallic")
        self.assertTrue(metallicInput.GetAttr().HasAuthoredValue())
        self.assertAlmostEqual(metallicInput.GetAttr().Get(), metallic, places=6)

    def testDefinePreviewMaterialPrimOverloadMinimalParams(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/World/PreviewMaterialMinimal", "Material")

        # Define the material with just the required color parameter
        color = Gf.Vec3f(1.0, 0.5, 0.2)
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Material.*to.*Material.*Expected original type to be "" or .*Scope.*')],
        ):
            material = usdex.core.definePreviewMaterial(prim, color)

        # Verify the prim was created correctly
        self.assertTrue(material)
        self.assertEqual(material.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(material.GetPrim().GetTypeName(), "Material")

        # Verify the material has the expected shader network
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)

        # Verify the diffuse color was set
        diffuseColorInput = shader.GetInput("diffuseColor")
        self.assertTrue(diffuseColorInput.GetAttr().HasAuthoredValue())
        self.assertEqual(diffuseColorInput.GetAttr().Get(), color)

        # Verify default values for optional parameters
        opacityInput = shader.GetInput("opacity")
        self.assertTrue(opacityInput.GetAttr().HasAuthoredValue())
        self.assertAlmostEqual(opacityInput.GetAttr().Get(), 1.0, places=6)  # Default opacity

        roughnessInput = shader.GetInput("roughness")
        self.assertTrue(roughnessInput.GetAttr().HasAuthoredValue())
        self.assertAlmostEqual(roughnessInput.GetAttr().Get(), 0.5, places=6)  # Default roughness

        metallicInput = shader.GetInput("metallic")
        self.assertTrue(metallicInput.GetAttr().HasAuthoredValue())
        self.assertAlmostEqual(metallicInput.GetAttr().Get(), 0.0, places=6)  # Default metallic

    def testDefinePreviewMaterialPrimOverloadInvalidPrim(self):
        # Test with invalid prim
        prim = Usd.Prim()
        self.assertFalse(prim.IsValid())

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            material = usdex.core.definePreviewMaterial(prim, Gf.Vec3f(1.0, 1.0, 1.0))
        self.assertFalse(material)

    def testDefinePreviewMaterialPrimOverloadTypeGuards(self):
        stage = Usd.Stage.CreateInMemory()
        color = Gf.Vec3f(0.5, 0.7, 0.9)

        # Test with non-Scope/Xform prim - should warn
        meshPrim = stage.DefinePrim("/World/MeshPrim", "Mesh")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Mesh.*to.*Material.*Expected original type to be "" or .*Scope.*')],
        ):
            material = usdex.core.definePreviewMaterial(meshPrim, color)
        self.assertTrue(material)
        self.assertEqual(material.GetPrim().GetTypeName(), "Material")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            material = usdex.core.definePreviewMaterial(scopePrim, color)
        self.assertTrue(material)
        self.assertEqual(material.GetPrim().GetTypeName(), "Material")

        # Test with Xform prim - should error because Material is not Xformable
        xformPrim = stage.DefinePrim("/World/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Cannot redefine.*from.*Xform.*to.*Material.*because Material is not Xformable")]
        ):
            material = usdex.core.definePreviewMaterial(xformPrim, color)
        self.assertFalse(material)


class ConnectPrimvarShaderTest(usdex.test.TestCase):

    # input sdfTypeName: (fallback/result SdfTypeName, primvarReaderRoleName, fallbackValue)
    typeMappings = {
        Sdf.ValueTypeNames.Float: (Sdf.ValueTypeNames.Float, "float", 0.8),
        Sdf.ValueTypeNames.Float2: (Sdf.ValueTypeNames.Float2, "float2", Gf.Vec2f(0.1, 0.2)),
        Sdf.ValueTypeNames.Float3: (Sdf.ValueTypeNames.Float3, "float3", Gf.Vec3f(0.3, 0.4, 0.5)),
        Sdf.ValueTypeNames.Float4: (Sdf.ValueTypeNames.Float4, "float4", Gf.Vec4f(0.6, 0.7, 0.8, 0.9)),
        Sdf.ValueTypeNames.Int: (Sdf.ValueTypeNames.Int, "int", 1),
        Sdf.ValueTypeNames.String: (Sdf.ValueTypeNames.String, "string", "test"),
        Sdf.ValueTypeNames.Normal3f: (Sdf.ValueTypeNames.Normal3f, "normal", Gf.Vec3f(0.1, 0.2, 0.3)),
        Sdf.ValueTypeNames.Point3f: (Sdf.ValueTypeNames.Point3f, "point", Gf.Vec3f(0.4, 0.5, 0.6)),
        Sdf.ValueTypeNames.Vector3f: (Sdf.ValueTypeNames.Vector3f, "vector", Gf.Vec3f(0.7, 0.8, 0.9)),
        Sdf.ValueTypeNames.Matrix4d: (
            Sdf.ValueTypeNames.Matrix4d,
            "matrix",
            Gf.Matrix4d(1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0),
        ),
        Sdf.ValueTypeNames.Color3f: (Sdf.ValueTypeNames.Float3, "float3", Gf.Vec3f(0.1, 0.2, 0.3)),
        Sdf.ValueTypeNames.Color4f: (Sdf.ValueTypeNames.Float4, "float4", Gf.Vec4f(0.4, 0.5, 0.6, 0.7)),
    }

    def getAllShaderNames(self):
        if hasattr(Sdr.Registry(), "GetShaderNodeNames"):
            return Sdr.Registry().GetShaderNodeNames()
        else:
            return Sdr.Registry().GetNodeNames()

    def setUp(self):
        super().setUp()
        self.stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(self.stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        self.materials = UsdGeom.Scope.Define(
            self.stage, self.stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())
        ).GetPrim()
        self.material = UsdShade.Material.Define(self.stage, self.materials.GetPath().AppendChild("TestMaterial"))
        self.shader = UsdShade.Shader.Define(self.stage, self.material.GetPath().AppendChild("TestShader"))
        self.shader.SetShaderId("TestShader")

    def assertValidShaderPrimvarNetwork(
        self,
        shader: UsdShade.Shader,
        primvarInfo: List[Tuple[str, str, Any]],  # inputName, primvarName, fallbackValue
    ):
        self.assertTrue(shader)

        # verify the primvarInfo
        for inputName, primvarName, fallbackValue in primvarInfo:
            input = shader.GetInput(inputName)
            outputName = "result"

            # check if the input type is in the typeMappings
            if input.GetTypeName() in self.typeMappings:
                outputTypeName, primvarRoleName, setFallbackValue = self.typeMappings[input.GetTypeName()]
            else:
                outputTypeName = input.GetTypeName()
                primvarRoleName = input.GetTypeName()

            # Make the primvar name valid for the shader prim by first replacing any ':' with '_'
            validPrimvarName = primvarName.replace(":", "_")
            primvarReaderName = usdex.core.getValidPrimName(f"Primvar_{validPrimvarName}_{primvarRoleName}")
            primvarReader = UsdShade.Shader(shader.GetPrim().GetParent().GetChild(primvarReaderName))
            self.assertTrue(primvarReader)
            self.assertEqual(primvarReader.GetShaderId(), f"UsdPrimvarReader_{primvarRoleName}")
            self.assertEqual(str(primvarReader.GetOutput(outputName).GetTypeName()), str(outputTypeName))
            self.assertEqual(primvarReader.GetInput("varname").GetAttr().Get(), primvarName)
            if fallbackValue is not None:
                self.assertEqual(primvarReader.GetInput("fallback").GetTypeName(), outputTypeName)
                self.assertAlmostEqual(primvarReader.GetInput("fallback").GetAttr().Get(), fallbackValue)
            else:
                self.assertFalse(primvarReader.GetInput("fallback"))

            self.assertTrue(input.HasConnectedSource())
            source, sourceAttr, sourceType = input.GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Output)
            self.assertEqual(
                source.GetOutput(sourceAttr).GetAttr(),
                primvarReader.GetOutput(outputName).GetAttr(),
                msg=f"Incorrect connection for {inputName} ({input.GetTypeName()}) -> {outputName}",
            )
            # the only opinion is from the connection
            self.assertFalse(input.GetAttr().HasAuthoredValue())
            self.assertEqual(len(input.GetValueProducingAttributes()), 1)
            self.assertEqual(input.GetValueProducingAttributes()[0], primvarReader.GetOutput(outputName).GetAttr())

    def testConnect(self):
        shaderInput = self.shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
        result = usdex.core.connectPrimvarShader(shaderInput, "paintColor", Gf.Vec3f(0.1, 0.2, 0.3))
        self.assertTrue(result)
        self.assertValidShaderPrimvarNetwork(
            self.shader,
            [("diffuseColor", "paintColor", Gf.Vec3f(0.1, 0.2, 0.3))],
        )

        # Check with a primvar name that is invalid for a prim name (contains a `:`)
        shaderInput = self.shader.CreateInput("roughness", Sdf.ValueTypeNames.Float)
        result = usdex.core.connectPrimvarShader(shaderInput, "paint:Roughness")
        self.assertTrue(result)
        self.assertValidShaderPrimvarNetwork(
            self.shader,
            [
                ("diffuseColor", "paintColor", Gf.Vec3f(0.1, 0.2, 0.3)),
                ("roughness", "paint:Roughness", None),
            ],
        )
        self.assertIsValidUsd(self.stage)

    def testInvalidInput(self):
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*UsdShadeInput is not valid.*")]):
            result = usdex.core.connectPrimvarShader(UsdShade.Input(), "paintColor")
            self.assertFalse(result)
        self.assertIsValidUsd(self.stage)

    def testInvalidNames(self):
        shaderInput = self.shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*the primvar name is invalid.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "")
            self.assertFalse(result)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*the primvar name is invalid.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "inv@lidName")
            self.assertFalse(result)
        self.assertIsValidUsd(self.stage)

    def testAllInputTypes(self):
        # Test with all input types mentioned in the USD Preview Surface spec: https://openusd.org/release/spec_usdpreviewsurface.html#primvar-reader
        connectionData = []
        for inputType in self.typeMappings.keys():
            connectionType, primvarRoleName, fallbackValue = self.typeMappings[inputType]
            shaderInput = self.shader.CreateInput(f"shaderInput_{inputType}", inputType)
            result = usdex.core.connectPrimvarShader(shaderInput, f"pv_{inputType}", fallbackValue)
            self.assertTrue(result)
            connectionData.append((f"shaderInput_{inputType}", f"pv_{inputType}", fallbackValue))

        self.assertValidShaderPrimvarNetwork(
            self.shader,
            connectionData,
        )
        self.assertIsValidUsd(self.stage)

    def testAllInputTypesWithSdrRegistry(self):
        # To enable this test, add the UsdShaders plugin using this repo.toml repo_test.env_vars setting:
        # [ "PXR_PLUGINPATH_NAME", "${root}/_build/target-deps/usd/release/plugin/usd/usdShaders/resources" ],

        if "UsdPreviewSurface" not in self.getAllShaderNames():
            self.skipTest("Skipping until the UsdShaders plugin is available")

        #  Run the test that creates all of the currently supported USD Preview Surface input types
        self.testAllInputTypes()

        shaderIdNames = self.getAllShaderNames()
        for prim in self.material.GetPrim().GetChildren():
            shader = UsdShade.Shader(prim)
            if "PrimvarReader_" not in shader.GetShaderId():
                continue

            self.assertIn(shader.GetShaderId(), shaderIdNames)

            # Check that "fallback" and "result" are the correct types
            fallback = shader.GetInput("fallback")
            result = shader.GetOutput("result")

            shaderNodeDef = Sdr.Registry().GetShaderNodeByIdentifier(shader.GetShaderId())
            inputProperty = shaderNodeDef.GetInput("fallback")
            self.assertTrue(inputProperty)
            outputProperty = shaderNodeDef.GetOutput("result")
            self.assertTrue(outputProperty)

            self.assertEqual(fallback.GetTypeName(), inputProperty.GetTypeAsSdfType().GetSdfType())
            self.assertEqual(result.GetTypeName(), outputProperty.GetTypeAsSdfType().GetSdfType())

    def testOverwriteOutputType(self):
        shaderInput = self.shader.CreateInput("roughness", Sdf.ValueTypeNames.Float)
        shaderPath = self.shader.GetPrim().GetParent().GetPath().AppendChild("Primvar_paintRoughness_float")
        primvarShader = UsdShade.Shader.Define(self.stage, shaderPath)

        # Set the output type to a different type to verify it is overwritten
        primvarShader.CreateOutput("result", Sdf.ValueTypeNames.String)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*existing shader.*does not match the input type.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "paintRoughness")
            self.assertFalse(result)

    def testUnsupportedUsdPreviewSurfaceInputType(self):
        shaderInput = self.shader.CreateInput("highPrecisionDouble", Sdf.ValueTypeNames.Double)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*<double> is not supported.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "paintHighPrecisionDouble")
            self.assertFalse(result)
