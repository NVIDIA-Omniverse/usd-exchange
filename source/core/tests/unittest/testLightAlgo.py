# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import pathlib

import usdex.core
import usdex.test
from pxr import Sdf, Tf, Usd, UsdGeom, UsdLux, UsdShade


class LightAlgoTest(usdex.test.TestCase):
    def _createTestStage(self):
        layer = self.tmpLayer(name="test")
        stage = Usd.Stage.Open(layer)
        self.defaultPrimName = "World"
        UsdGeom.Xform.Define(stage, "/World").GetPrim()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        self.assertIsValidUsd(stage)
        return stage

    def _checkDomeLightAttrs(self, light, intensity, texturePath=None, textureType=None):
        api = UsdLux.LightAPI(light)

        # check intensity
        intensityAttr = api.GetIntensityAttr()
        self.assertTrue(intensityAttr.IsAuthored())
        self.assertAlmostEqual(intensityAttr.Get(), intensity, 5)

        # if texture path was specified it and texture format should be authored
        if texturePath is not None:

            if textureType is None:
                textureType = UsdLux.Tokens.automatic

            texFileAttr = usdex.core.getLightAttr(light.GetTextureFileAttr())
            self.assertTrue(texFileAttr.IsAuthored())
            self.assertEqual(texFileAttr.Get().path, texturePath)

            texFormatAttr = usdex.core.getLightAttr(light.GetTextureFormatAttr())
            self.assertTrue(texFormatAttr.IsAuthored())
            self.assertEqual(texFormatAttr.Get(), textureType)

    def _checkRectLightAttrs(self, light, width, height, intensity, texturePath=None):
        # check width, height & intensity
        widthAttr = light.GetWidthAttr()
        self.assertTrue(widthAttr.IsAuthored())
        self.assertAlmostEqual(widthAttr.Get(), width, 5)

        heightAttr = light.GetHeightAttr()
        self.assertTrue(heightAttr.IsAuthored())
        self.assertAlmostEqual(heightAttr.Get(), height, 5)

        intensityAttr = light.GetIntensityAttr()
        self.assertTrue(intensityAttr.IsAuthored())
        self.assertAlmostEqual(intensityAttr.Get(), intensity, 5)

        # check texture path if supplied
        if texturePath is not None:
            texPathAttr = usdex.core.getLightAttr(light.GetTextureFileAttr())
            self.assertAlmostEqual(texPathAttr.Get().path, texturePath)

    def testDefineDomeLight(self):
        stage = self._createTestStage()
        textureFile = self.tmpFile(name="dome", ext="png")
        relTextureFile = f"./{pathlib.Path(textureFile).name}"

        dome_light_no_texture = usdex.core.defineDomeLight(stage, Sdf.Path("/World/domeLightNoTexture"), 0.77)
        dome_light_auto = usdex.core.defineDomeLight(stage, Sdf.Path("/World/domeLightAuto"), 0.88, relTextureFile)
        dome_light_lat_long = usdex.core.defineDomeLight(stage, Sdf.Path("/World/domeLightLatLong"), 0.99, relTextureFile, UsdLux.Tokens.latlong)

        self._checkDomeLightAttrs(dome_light_no_texture, 0.77)
        self._checkDomeLightAttrs(dome_light_auto, 0.88, relTextureFile)
        self._checkDomeLightAttrs(dome_light_lat_long, 0.99, relTextureFile, UsdLux.Tokens.latlong)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*is not a valid texture format token")]):
            dome_light_invalid_format = usdex.core.defineDomeLight(stage, Sdf.Path("/World/invalid"), 0.11, relTextureFile, UsdLux.Tokens.geometry)
            self.assertFalse(dome_light_invalid_format)

        self.assertIsValidUsd(stage)

    def testDefineRectLight(self):
        stage = self._createTestStage()
        textureFile = self.tmpFile(name="rect", ext="png")
        relTextureFile = f"./{pathlib.Path(textureFile).name}"

        rect_light_no_texture = usdex.core.defineRectLight(stage, Sdf.Path("/World/rectLightNoTexture"), 19, 93, 0.77)
        rect_light_textured = usdex.core.defineRectLight(stage, Sdf.Path("/World/rectLight"), 19.93, 39.91, 0.88, relTextureFile)
        self._checkRectLightAttrs(rect_light_no_texture, 19, 93, 0.77)
        self._checkRectLightAttrs(rect_light_textured, 19.93, 39.91, 0.88, relTextureFile)
        self.assertIsValidUsd(stage)

    def testIsLight(self):
        stage = self._createTestStage()
        cylinderLight = UsdLux.CylinderLight.Define(stage, "/World/cylinderLight")
        diskLight = UsdLux.DiskLight.Define(stage, "/World/diskLight")
        distantLight = UsdLux.DistantLight.Define(stage, "/World/distantLight")
        domeLight = UsdLux.DomeLight.Define(stage, "/World/domeLight")
        sphereLight = UsdLux.SphereLight.Define(stage, "/World/sphereLight")
        rectLight = UsdLux.RectLight.Define(stage, "/World/rectLight")
        xform = UsdGeom.Xform.Define(stage, "/World")
        cube = UsdGeom.Cube.Define(stage, "/World/cube")
        camera = UsdGeom.Camera.Define(stage, "/World/camera")
        material = UsdShade.Material.Define(stage, "/World/material")
        shader = UsdShade.Shader.Define(stage, "/World/shader")

        # ensure that isLight returns true for lights and false for all else
        self.assertTrue(usdex.core.isLight(cylinderLight.GetPrim()))
        self.assertTrue(usdex.core.isLight(diskLight.GetPrim()))
        self.assertTrue(usdex.core.isLight(distantLight.GetPrim()))
        self.assertTrue(usdex.core.isLight(domeLight.GetPrim()))
        self.assertTrue(usdex.core.isLight(sphereLight.GetPrim()))
        self.assertTrue(usdex.core.isLight(rectLight.GetPrim()))
        # geom
        self.assertFalse(usdex.core.isLight(cube.GetPrim()))
        # camera
        self.assertFalse(usdex.core.isLight(camera.GetPrim()))
        # xform
        self.assertFalse(usdex.core.isLight(xform.GetPrim()))
        # shader
        self.assertFalse(usdex.core.isLight(shader.GetPrim()))
        # shadeMaterial
        self.assertFalse(usdex.core.isLight(material.GetPrim()))
        # geom with LightAPI applied
        UsdLux.LightAPI.Apply(cube.GetPrim())
        self.assertTrue(usdex.core.isLight(cube.GetPrim()))

    def testGetLightAttr(self):
        # This test will only work in USD versions after the UsdLuxLights schema added "inputs:" to attribute names
        stage = self._createTestStage()
        distantLight = UsdLux.DistantLight.Define(stage, "/World/distantLight")

        # nothing authored
        self.assertEqual(usdex.core.getLightAttr(distantLight.GetAngleAttr()).Get(), distantLight.GetAngleAttr().Get())

        # old attribute name authored (no inputs:)
        distantLight.GetPrim().CreateAttribute("angle", Sdf.ValueTypeNames.Float, custom=False).Set(0.1)
        self.assertAlmostEqual(usdex.core.getLightAttr(distantLight.GetAngleAttr()).Get(), 0.1)

        # both old and new names authored
        distantLight.CreateAngleAttr().Set(0.5)
        self.assertEqual(usdex.core.getLightAttr(distantLight.GetAngleAttr()).Get(), distantLight.GetAngleAttr().Get())

        # just new name authored
        distantLight.GetPrim().RemoveProperty("angle")
        self.assertEqual(len(distantLight.GetPrim().GetAuthoredAttributes()), 1)
        self.assertEqual(usdex.core.getLightAttr(distantLight.GetAngleAttr()).Get(), distantLight.GetAngleAttr().Get())


class DefineDomeLightTestCase(usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineDomeLight
    requiredArgs = tuple([1.0])
    typeName = "DomeLight"
    schema = UsdLux.DomeLight
    requiredPropertyNames = set(
        [
            "inputs:intensity",
        ]
    )


class DefineRectLightTestCase(usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineRectLight
    requiredArgs = tuple([1.0, 2.0, 3.0])
    typeName = "RectLight"
    schema = UsdLux.RectLight
    requiredPropertyNames = set(
        [
            "inputs:height",
            "inputs:intensity",
            "inputs:width",
            UsdGeom.Tokens.extent,
        ]
    )


class LightAlgoPrimOverloadTest(usdex.test.TestCase):
    """Test prim overloads for light define functions."""

    def createTestStage(self):
        stage = Usd.Stage.CreateInMemory()
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.centimeters)
        return stage

    def testDefineDomeLightPrimOverload(self):
        stage = self.createTestStage()

        # Create a prim first
        path = Sdf.Path("/World/DomeLight")
        prim = stage.DefinePrim(path)
        self.assertTrue(prim.IsValid())

        # Test the prim overload
        light = usdex.core.defineDomeLight(prim, 1.5)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim(), prim)
        self.assertEqual(light.GetPrim().GetTypeName(), "DomeLight")

        # Check intensity
        intensityAttr = light.GetIntensityAttr()
        self.assertTrue(intensityAttr.IsAuthored())
        self.assertAlmostEqual(intensityAttr.Get(), 1.5, 5)

    def testDefineDomeLightPrimOverloadWithTexture(self):
        stage = self.createTestStage()

        # Create a prim first
        path = Sdf.Path("/World/DomeLightTextured")
        prim = stage.DefinePrim(path)
        self.assertTrue(prim.IsValid())

        # Test the prim overload with texture
        textureFile = "./test.png"
        light = usdex.core.defineDomeLight(prim, 2.0, textureFile, UsdLux.Tokens.latlong)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim(), prim)
        self.assertEqual(light.GetPrim().GetTypeName(), "DomeLight")

        # Check intensity
        intensityAttr = light.GetIntensityAttr()
        self.assertTrue(intensityAttr.IsAuthored())
        self.assertAlmostEqual(intensityAttr.Get(), 2.0, 5)

        # Check texture
        texFileAttr = usdex.core.getLightAttr(light.GetTextureFileAttr())
        self.assertTrue(texFileAttr.IsAuthored())
        self.assertEqual(texFileAttr.Get().path, textureFile)

        texFormatAttr = usdex.core.getLightAttr(light.GetTextureFormatAttr())
        self.assertTrue(texFormatAttr.IsAuthored())
        self.assertEqual(texFormatAttr.Get(), UsdLux.Tokens.latlong)

    def testDefineDomeLightPrimOverloadInvalidPrim(self):
        # Test with invalid prim
        prim = Usd.Prim()
        self.assertFalse(prim.IsValid())

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            light = usdex.core.defineDomeLight(prim, 1.0)
        self.assertFalse(light)

    def testDefineRectLightPrimOverload(self):
        stage = self.createTestStage()

        # Create a prim first
        path = Sdf.Path("/World/RectLight")
        prim = stage.DefinePrim(path)
        self.assertTrue(prim.IsValid())

        # Test the prim overload
        light = usdex.core.defineRectLight(prim, 5.0, 10.0, 2.5)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim(), prim)
        self.assertEqual(light.GetPrim().GetTypeName(), "RectLight")

        # Check width, height, and intensity
        widthAttr = light.GetWidthAttr()
        self.assertTrue(widthAttr.IsAuthored())
        self.assertAlmostEqual(widthAttr.Get(), 5.0, 5)

        heightAttr = light.GetHeightAttr()
        self.assertTrue(heightAttr.IsAuthored())
        self.assertAlmostEqual(heightAttr.Get(), 10.0, 5)

        intensityAttr = light.GetIntensityAttr()
        self.assertTrue(intensityAttr.IsAuthored())
        self.assertAlmostEqual(intensityAttr.Get(), 2.5, 5)

    def testDefineRectLightPrimOverloadWithTexture(self):
        stage = self.createTestStage()

        # Create a prim first
        path = Sdf.Path("/World/RectLightTextured")
        prim = stage.DefinePrim(path)
        self.assertTrue(prim.IsValid())

        # Test the prim overload with texture
        textureFile = "./rect_texture.png"
        light = usdex.core.defineRectLight(prim, 8.0, 12.0, 3.0, textureFile)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim(), prim)
        self.assertEqual(light.GetPrim().GetTypeName(), "RectLight")

        # Check width, height, and intensity
        widthAttr = light.GetWidthAttr()
        self.assertTrue(widthAttr.IsAuthored())
        self.assertAlmostEqual(widthAttr.Get(), 8.0, 5)

        heightAttr = light.GetHeightAttr()
        self.assertTrue(heightAttr.IsAuthored())
        self.assertAlmostEqual(heightAttr.Get(), 12.0, 5)

        intensityAttr = light.GetIntensityAttr()
        self.assertTrue(intensityAttr.IsAuthored())
        self.assertAlmostEqual(intensityAttr.Get(), 3.0, 5)

        # Check texture
        texPathAttr = usdex.core.getLightAttr(light.GetTextureFileAttr())
        self.assertTrue(texPathAttr.IsAuthored())
        self.assertEqual(texPathAttr.Get().path, textureFile)

    def testDefineRectLightPrimOverloadInvalidPrim(self):
        # Test with invalid prim
        prim = Usd.Prim()
        self.assertFalse(prim.IsValid())

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            light = usdex.core.defineRectLight(prim, 1.0, 2.0, 3.0)
        self.assertFalse(light)

    def testDefineDomeLightPrimOverloadTypeGuards(self):
        stage = self.createTestStage()

        # Test with non-Scope/Xform prim - should warn
        meshPrim = stage.DefinePrim("/World/MeshPrim", "Mesh")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Mesh.*to.*DomeLight.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            light = usdex.core.defineDomeLight(meshPrim, 1.0)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim().GetTypeName(), "DomeLight")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            light = usdex.core.defineDomeLight(scopePrim, 1.0)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim().GetTypeName(), "DomeLight")

        # Test with Xform prim - should not warn
        xformPrim = stage.DefinePrim("/World/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            light = usdex.core.defineDomeLight(xformPrim, 1.0)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim().GetTypeName(), "DomeLight")

    def testDefineRectLightPrimOverloadTypeGuards(self):
        stage = self.createTestStage()

        # Test with non-Scope/Xform prim - should warn
        meshPrim = stage.DefinePrim("/World/MeshPrim", "Mesh")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Mesh.*to.*RectLight.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            light = usdex.core.defineRectLight(meshPrim, 1.0, 2.0, 3.0)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim().GetTypeName(), "RectLight")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            light = usdex.core.defineRectLight(scopePrim, 1.0, 2.0, 3.0)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim().GetTypeName(), "RectLight")

        # Test with Xform prim - should not warn
        xformPrim = stage.DefinePrim("/World/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            light = usdex.core.defineRectLight(xformPrim, 1.0, 2.0, 3.0)
        self.assertTrue(light)
        self.assertEqual(light.GetPrim().GetTypeName(), "RectLight")
