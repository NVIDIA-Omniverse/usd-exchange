# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import os
import re
from typing import List

import omni.asset_validator
import usdex.core
import usdex.rtx
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade, UsdUtils, Vt

# Description of a simple plane mesh with connected UVs
FACE_VERTEX_COUNTS = Vt.IntArray([4])
FACE_VERTEX_INDICES = Vt.IntArray([0, 1, 2, 3])
POINTS = Vt.Vec3fArray(
    [
        Gf.Vec3f(0.0, 0.0, 0.0),
        Gf.Vec3f(0.0, 0.0, 1.0),
        Gf.Vec3f(1.0, 0.0, 1.0),
        Gf.Vec3f(1.0, 0.0, 0.0),
    ]
)
UVS = usdex.core.Vec2fPrimvarData(
    UsdGeom.Tokens.faceVarying, Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0), Gf.Vec2f(0.0, 1.0), Gf.Vec2f(1.0, 1.0)]), Vt.IntArray([0, 1, 2, 1])
)


def computeEffectiveShaderInputValue(shaderInput):
    """Given a shader input compute the effective value of it accounting for connections"""
    # This is complicated by the differing functions available across OpenUsd versions
    if hasattr(shaderInput, "GetValueProducingAttributes"):
        return shaderInput.GetValueProducingAttributes()[0].Get()
    else:
        return shaderInput.GetValueProducingAttribute()[0].Get()


class MaterialAlgoTest(usdex.test.TestCase):

    def setUp(self):
        super().setUp()

        self.validationEngine.disable_rule(omni.asset_validator.NormalsExistChecker)

    @staticmethod
    def allowedIssuePredicates() -> List[omni.asset_validator.IssuePredicates]:
        """Return a list of callables that determine if an issue can be bypassed by tests"""

        def checkUnresolvableDependenciesIssue(issue):
            # special case for MDL material libraries
            if re.match("Found unresolvable external dependency '.*\.(mdl)'\.", issue.message):
                return True

        # Allows any issue reporting `The path "Omni*.mdl" does not exist.` to be bypassed.
        omniMdlPredicate = omni.asset_validator.IssuePredicates.And(
            omni.asset_validator.IssuePredicates.ContainsMessage("The path Omni"),
            omni.asset_validator.IssuePredicates.ContainsMessage(".mdl does not exist."),
        )

        return [omniMdlPredicate, checkUnresolvableDependenciesIssue]

    @staticmethod
    def getExpectedResolveDiagMsgs(failCount, mdlName):
        expected = []
        msg = f".*Failed to resolve reference @{mdlName}@"
        for i in range(failCount):
            expected.append((Tf.TF_DIAGNOSTIC_WARNING_TYPE, msg))
        return expected

    def _createTestStage(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        defaultPrimPath = stage.GetDefaultPrim().GetPath()
        UsdGeom.Xform.Define(stage, defaultPrimPath)

        # Define two non-xformable (Geometry and Looks) prims with no transforms
        materialsScopeName = UsdUtils.GetMaterialsScopeName()
        geometryScopeName = "Geometry"
        geometryScopePath = defaultPrimPath.AppendChild(geometryScopeName)

        UsdGeom.Scope.Define(stage, geometryScopePath)
        UsdGeom.Scope.Define(stage, defaultPrimPath.AppendChild(materialsScopeName))

        # Define xformable (Xform) prim with a UsdGeomCylinder (Cylinder) as a child
        xformPath = geometryScopePath.AppendChild("Xform")
        cylinderPath = xformPath.AppendChild("Cylinder")
        UsdGeom.Xform.Define(stage, xformPath)
        UsdGeom.Cylinder.Define(stage, cylinderPath)

        # Add a GeomMesh (Plane) as another child of Xform
        path = xformPath.AppendChild("Plane")
        plane = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=UVS)
        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(0.0, 0.0, 5.0))
        transform.SetScale(Gf.Vec3d(5.0, 1.0, 5.0))
        usdex.core.setLocalTransform(plane.GetPrim(), transform)

        self.assertIsValidUsd(stage)
        return stage

    def assertFractionalOpacityEnabled(self, stage):
        """Validate that the fractionalCutoutOpacity render setting has been explicitly authored and is enabled"""
        # We check the root layer because only custom data stored there is respected, but in reality we should have authored this into the current
        # edit target for the stage. The current logic is sufficient for testing.
        layer = stage.GetRootLayer()

        # Custom layer data should exist and contain "renderSettings"
        self.assertTrue(layer.HasCustomLayerData)
        self.assertIn("renderSettings", layer.customLayerData)
        renderSettings = layer.customLayerData["renderSettings"]

        # The render settings should contain "rtx:raytracing:fractionalCutoutOpacity" and the value should be True
        self.assertIn("rtx:raytracing:fractionalCutoutOpacity", renderSettings)
        self.assertTrue(renderSettings["rtx:raytracing:fractionalCutoutOpacity"])

    def _validateOmniPBRMaterial(self, stage, material, mdlShader, previewShader, color, opacity, roughness, metallic):
        """Validate that the OmniPbr Material is setup as expected"""

        # The Material Interface should include a Color3f named "Color" that holds the specified value
        shaderInput = material.GetInput("diffuseColor")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertVecAlmostEqual(shaderInput.Get(), color)

        # The Material Interface should include a Float named "Opacity" that holds the specified value
        shaderInput = material.GetInput("opacity")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.Get(), opacity)

        # The Material Interface should include a Float named "Roughness" that holds the specified value
        shaderInput = material.GetInput("roughness")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.Get(), roughness)

        # The Material Interface should include a Float named "Roughness" that holds the specified value
        shaderInput = material.GetInput("metallic")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.Get(), metallic)

        # Validate the MDL Shader
        shader = mdlShader

        # The MDL Shader should include a Color3f named "diffuse_color_constant" that has the effective specified value
        shaderInput = shader.GetInput("diffuse_color_constant")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertVecAlmostEqual(computeEffectiveShaderInputValue(shaderInput), color)

        # The MDL Shader should include a Float named "opacity_constant" that has the effective specified value
        shaderInput = shader.GetInput("opacity_constant")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), opacity)

        # The MDL Shader should include a Float named "reflection_roughness_constant" that has the effective specified value
        shaderInput = shader.GetInput("reflection_roughness_constant")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), roughness)

        # The MDL Shader should include a Float named "metallic_constant" that has the effective specified value
        shaderInput = shader.GetInput("metallic_constant")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), metallic)

        # When opacity is not 1.0 the MDL Shader should include a Bool named "enable_opacity" that is True.
        # The Fractional Opacity render setting will also be enabled.
        if opacity < 1.0:

            shaderInput = shader.GetInput("enable_opacity")
            self.assertTrue(shaderInput)
            self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Bool)
            self.assertTrue(shaderInput.Get())

            self.assertFractionalOpacityEnabled(stage)

        # Validate the default Shader
        shader = previewShader

        # The Shader should include a Color3f named "diffuseColor" that has the effective specified value
        shaderInput = shader.GetInput("diffuseColor")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertVecAlmostEqual(computeEffectiveShaderInputValue(shaderInput), color)

        # The Shader should include a Float named "opacity" that has the effective specified value
        shaderInput = shader.GetInput("opacity")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), opacity)

        # The Shader should include a Float named "roughness" that has the effective specified value
        shaderInput = shader.GetInput("roughness")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), roughness)

        # The Shader should include a Float named "metallic" that has the effective specified value
        shaderInput = shader.GetInput("metallic")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), metallic)

    def _validateOmniGlassMaterial(self, material, mdlShader, previewShader, color, ior):

        # The Material Interface should include a Color3f named "Color" that holds the specified value
        shaderInput = material.GetInput("diffuseColor")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertVecAlmostEqual(shaderInput.Get(), color)

        # The Material Interface should include a Float named "IOR" that holds the specified value
        shaderInput = material.GetInput("ior")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.Get(), ior, places=5)

        # Validate the MDL Shader
        shader = mdlShader

        # The MDL Shader should include a Color3f named "glass_color" that has the effective specified value
        shaderInput = shader.GetInput("glass_color")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertVecAlmostEqual(computeEffectiveShaderInputValue(shaderInput), color)

        # The MDL Shader should include a Float named "glass_ior" that has the effective specified value
        shaderInput = shader.GetInput("glass_ior")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), ior, places=5)

        # Validate the default Shader
        shader = previewShader

        # The Shader should include a Color3f named "diffuseColor" that has the effective specified value
        shaderInput = shader.GetInput("diffuseColor")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertVecAlmostEqual(computeEffectiveShaderInputValue(shaderInput), color)

        # The Shader should include a Float named "ior" that has the effective specified value
        shaderInput = shader.GetInput("ior")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), ior, places=5)

        # The Shader should include a Float named "opacity" that has a value of 0.0
        shaderInput = shader.GetInput("opacity")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.Get(), 0.0)

    def _validateMaterial(self, material):
        self.assertTrue(material.GetPrim())
        self.assertTrue(isinstance(material, UsdShade.Material))

    def _validateShader(self, shader, shaderType):
        if shaderType == "OmniPBR":
            self.assertTrue(shader.GetPrim())
            self.assertTrue(isinstance(shader, UsdShade.Shader))
            asset = shader.GetSourceAsset("mdl")
            self.assertEqual(asset, Sdf.AssetPath("OmniPBR.mdl"))
            subAsset = shader.GetSourceAssetSubIdentifier("mdl")
            self.assertEqual(subAsset, "OmniPBR")
        elif shaderType == "OmniGlass":
            self.assertTrue(shader.GetPrim())
            self.assertTrue(isinstance(shader, UsdShade.Shader))
            asset = shader.GetSourceAsset("mdl")
            self.assertEqual(asset, Sdf.AssetPath("OmniGlass.mdl"))
            subAsset = shader.GetSourceAssetSubIdentifier("mdl")
            self.assertEqual(subAsset, "OmniGlass")
        elif shaderType == "UsdPreviewSurface":
            self.assertTrue(shader.GetPrim())
            self.assertTrue(isinstance(shader, UsdShade.Shader))
            shaderId = shader.GetShaderId()
            self.assertEqual(shaderId, "UsdPreviewSurface")
        else:
            self.assertTrue(False, msg=f"Shader validation is not supported for {shaderType}")

    def _validateMdlConnection(self, material, shader, connected=True):
        if connected:
            mdlShaderOutput = shader.GetOutput("out")
            self.assertTrue(mdlShaderOutput.GetAttr().IsDefined())

            surfaceOutput = material.GetSurfaceOutput("mdl")
            self.assertTrue(surfaceOutput.HasConnectedSource())
            surface = surfaceOutput.GetConnectedSource()[0]
            self.assertEqual(surface.GetOutput("out").GetAttr(), mdlShaderOutput.GetAttr())

            displacementOutput = material.GetDisplacementOutput("mdl")
            self.assertTrue(displacementOutput.HasConnectedSource())
            displacement = displacementOutput.GetConnectedSource()[0]
            self.assertEqual(displacement.GetOutput("out").GetAttr(), mdlShaderOutput.GetAttr())

            volumeOutput = material.GetVolumeOutput("mdl")
            self.assertTrue(volumeOutput.HasConnectedSource())
            volume = volumeOutput.GetConnectedSource()[0]
            self.assertEqual(volume.GetOutput("out").GetAttr(), mdlShaderOutput.GetAttr())
        else:
            surface = material.GetSurfaceOutput("mdl")
            self.assertFalse(surface.GetAttr())

            displacement = material.GetDisplacementOutput("mdl")
            self.assertFalse(displacement.GetAttr())

            volume = material.GetVolumeOutput("mdl")
            self.assertFalse(volume.GetAttr())

    def _validatePreviewShaderConnection(self, material, shader):
        surfaceOutput = material.GetSurfaceOutput()
        self.assertTrue(surfaceOutput.HasConnectedSource())
        surface = surfaceOutput.GetConnectedSource()[0]
        self.assertEqual(surface.GetOutput(UsdShade.Tokens.surface).GetAttr(), shader.GetOutput(UsdShade.Tokens.surface).GetAttr())

        displacementOutput = material.GetDisplacementOutput()
        self.assertTrue(displacementOutput.HasConnectedSource())
        displacement = displacementOutput.GetConnectedSource()[0]
        self.assertEqual(displacement.GetOutput(UsdShade.Tokens.displacement).GetAttr(), shader.GetOutput(UsdShade.Tokens.displacement).GetAttr())

        volumeOutput = material.GetVolumeOutput()
        self.assertFalse(volumeOutput.HasConnectedSource())
        self.assertFalse(shader.GetOutput(UsdShade.Tokens.volume))

    def testMdlMaterialCreation(self):
        stage = self._createTestStage()
        materialScopePath = stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())
        materialScope = stage.GetPrimAtPath(materialScopePath)
        cylinder = stage.GetPrimAtPath("/Root/Geometry/Xform/Cylinder")

        material = usdex.core.createMaterial(materialScope, "TestMaterial")
        self._validateMaterial(material)
        shader = usdex.rtx.createMdlShader(material, "TestShader", Sdf.AssetPath("OmniPBR.mdl"), "OmniPBR")
        self._validateShader(shader, "OmniPBR")
        self._validateMdlConnection(material, shader)

        # test creating a new shader on a previously connected connected material
        shader2 = usdex.rtx.createMdlShader(material, "TestShader2", Sdf.AssetPath("OmniPBR.mdl"), "OmniPBR")
        self._validateShader(shader2, "OmniPBR")
        self._validateMdlConnection(material, shader2)

        # test connectMaterialOutputs = False
        material2 = usdex.core.createMaterial(materialScope, "TestMaterial2")
        self._validateMaterial(material2)

        unconnectedShader = usdex.rtx.createMdlShader(material2, "unconnectedShader", Sdf.AssetPath("OmniGlass.mdl"), "OmniGlass", False)
        self._validateShader(unconnectedShader, "OmniGlass")
        self._validateMdlConnection(material2, unconnectedShader, connected=False)

        usdex.core.bindMaterial(cylinder, material)
        self.assertTrue(cylinder.HasAPI(UsdShade.MaterialBindingAPI))

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid location")]):
            testShader = usdex.rtx.createMdlShader(UsdShade.Material(), "badShader", Sdf.AssetPath("OmniPBR.mdl"), "OmniPBR", False)
        self.assertFalse(testShader.GetPrim())

        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(1, "OmniGlass.mdl")
        expected += MaterialAlgoTest.getExpectedResolveDiagMsgs(2, "OmniPBR.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            self.assertIsValidUsd(stage, issuePredicates=self.allowedIssuePredicates())

    def testInvalidMdlShaderCreation(self):
        stage = self._createTestStage()
        path = stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())
        parent = stage.GetPrimAtPath(path)
        name = "Material"

        # Construct valid default arguments
        material = usdex.core.createMaterial(parent, name)
        mdlPath = Sdf.AssetPath("OmniPBR.mdl")
        module = "OmniPBR"

        # An invalid parent will result in an invalid Shader schema being returned
        invalid_parent = UsdShade.Material(stage.GetPrimAtPath("/Root/InvalidPath"))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid location")]):
            shader = usdex.rtx.createMdlShader(invalid_parent, name, mdlPath, module)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)

        # An invalid name will result in an invalid Shader schema being returned
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid location")]):
            shader = usdex.rtx.createMdlShader(material, "", mdlPath, module)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid location")]):
            shader = usdex.rtx.createMdlShader(material, "1_Material", mdlPath, module)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid location")]):
            shader = usdex.rtx.createMdlShader(material, "Glass.mdl", mdlPath, module)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)
        self.assertIsValidUsd(stage)

    def testComputeEffectiveSurfaceShader(self):
        stage = self._createTestStage()

        # An un-initialized Material will result in an invalid shader schema being returned
        material = UsdShade.Material()
        shader = usdex.rtx.computeEffectiveMdlSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)

        # An invalid UsdShade.Material will result in an invalid shader schema being returned
        material = UsdShade.Material(stage.GetPrimAtPath("/Root"))
        shader = usdex.rtx.computeEffectiveMdlSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)

        # A Material with no connected shaders will result in an invalid shader schema being returned
        path = stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())
        parent = stage.GetPrimAtPath(path)
        name = "Material"
        material = usdex.core.createMaterial(parent, name)
        shader = usdex.rtx.computeEffectiveMdlSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)

        # With only the MDL render context connected, that shader will be returned for MDL, but an invalid shader schema being returned for preview
        path = material.GetPrim().GetPath().AppendChild("MdlShader")
        mdlShader = UsdShade.Shader.Define(stage, path)
        output = mdlShader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput("mdl").ConnectToSource(output)
        shader = usdex.rtx.computeEffectiveMdlSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), mdlShader.GetPrim())
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertFalse(shader)

        # With both render contexts connected, that associated shader will be returned for each context
        path = material.GetPrim().GetPath().AppendChild("PreviewSurface")
        previewShader = UsdShade.Shader.Define(stage, path)
        output = previewShader.CreateOutput("out", Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput().ConnectToSource(output)
        shader = usdex.rtx.computeEffectiveMdlSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), mdlShader.GetPrim())
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), previewShader.GetPrim())

        # With only the universal render context connected, that shader will be returned for both render contexts
        material.GetSurfaceOutput("mdl").GetAttr().ClearConnections()
        shader = usdex.rtx.computeEffectiveMdlSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), previewShader.GetPrim())
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertIsInstance(shader, UsdShade.Shader)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), previewShader.GetPrim())

    def testMaterialDefinition(self):
        stage = self._createTestStage()
        materialScopePath = stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())
        materialScope = stage.GetPrimAtPath(materialScopePath)
        mdlShaderName = "MDLShader"
        usdShaderName = "PreviewSurface"

        badStage = None
        badPrim = Usd.Prim()

        red = usdex.core.sRgbToLinear(Gf.Vec3f(0.8, 0.1, 0.1))
        green = usdex.core.sRgbToLinear(Gf.Vec3f(0.1, 0.8, 0.1))
        blue = usdex.core.sRgbToLinear(Gf.Vec3f(0.1, 0.1, 0.8))

        # OmniPBR test stage overload
        materialPath = materialScopePath.AppendChild("TestMaterial")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        material = usdex.rtx.definePbrMaterial(stage, materialPath, red)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self._validateMaterial(material)
        self._validateShader(mdlShader, "OmniPBR")
        self._validateShader(previewShader, "UsdPreviewSurface")
        self._validateMdlConnection(material, mdlShader)
        self._validatePreviewShaderConnection(material, previewShader)
        self._validateOmniPBRMaterial(stage, material, mdlShader, previewShader, red, 1.0, 0.5, 0.0)

        # OmniPBR test prim overload
        materialPath = materialScopePath.AppendChild("TestMaterial2")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        material = usdex.rtx.definePbrMaterial(materialScope, "TestMaterial2", blue, 0.2, 0.2, 0.8)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self._validateMaterial(material)
        self._validateShader(mdlShader, "OmniPBR")
        self._validateShader(previewShader, "UsdPreviewSurface")
        self._validateMdlConnection(material, mdlShader)
        self._validatePreviewShaderConnection(material, previewShader)
        self._validateOmniPBRMaterial(stage, material, mdlShader, previewShader, blue, 0.2, 0.2, 0.8)

        # OmniGlass test stage overload
        materialPath = materialScopePath.AppendChild("TestGlassMaterial")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        material = usdex.rtx.defineGlassMaterial(stage, materialPath, green)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self._validateMaterial(material)
        self._validateShader(mdlShader, "OmniGlass")
        self._validateShader(previewShader, "UsdPreviewSurface")
        self._validateMdlConnection(material, mdlShader)
        self._validatePreviewShaderConnection(material, previewShader)
        self._validateOmniGlassMaterial(material, mdlShader, previewShader, green, 1.491)

        # OmniGlass test prim overload
        materialPath = materialScopePath.AppendChild("TestGlassMaterial2")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        material = usdex.rtx.defineGlassMaterial(materialScope, "TestGlassMaterial2", blue, 2.2)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self._validateMaterial(material)
        self._validateShader(mdlShader, "OmniGlass")
        self._validateShader(previewShader, "UsdPreviewSurface")
        self._validateMdlConnection(material, mdlShader)
        self._validatePreviewShaderConnection(material, previewShader)
        self._validateOmniGlassMaterial(material, mdlShader, previewShader, blue, 2.2)

        # test bad stage
        materialPath = materialScopePath.AppendChild("badMaterial")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            material = usdex.rtx.definePbrMaterial(badStage, materialPath, red)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self.assertFalse(material)
        self.assertFalse(mdlShader)
        self.assertFalse(previewShader)

        materialPath = materialScopePath.AppendChild("badGlassMaterial")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            material = usdex.rtx.defineGlassMaterial(badStage, materialPath, green)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self.assertFalse(material)
        self.assertFalse(mdlShader)
        self.assertFalse(previewShader)

        # test bad prim
        materialPath = materialScopePath.AppendChild("badMaterial3")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            material = usdex.rtx.definePbrMaterial(badPrim, "badMaterial3", red)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self.assertFalse(material)
        self.assertFalse(mdlShader)
        self.assertFalse(previewShader)

        materialPath = materialScopePath.AppendChild("badGlassMaterial2")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid location")]):
            material = usdex.rtx.defineGlassMaterial(badPrim, "badGlassMaterial2", green)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self.assertFalse(material)
        self.assertFalse(mdlShader)
        self.assertFalse(previewShader)

        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(2, "OmniGlass.mdl")
        expected += MaterialAlgoTest.getExpectedResolveDiagMsgs(2, "OmniPBR.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            self.assertIsValidUsd(stage, issuePredicates=self.allowedIssuePredicates())

    def testTexturedMaterialDefinition(self):
        stage = self._createTestStage()
        materialScopePath = stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())
        cylinder = stage.GetPrimAtPath("/Root/Geometry/Xform/Cylinder")
        plane = stage.GetPrimAtPath("/Root/Geometry/Xform/Plane")
        mdlShaderName = "MDLShader"
        usdShaderName = "PreviewSurface"
        diffuseTexture = self.tmpFile(name="BaseColor", ext="png")
        diffuseTexture2 = self.tmpFile(name="BaseColor", ext="png")
        normalTexture = self.tmpFile(name="N", ext="png")
        normalTexture2 = self.tmpFile(name="N", ext="png")
        opacityTexture = self.tmpFile(name="Opacity", ext="png")
        opacityTexture2 = "invalid"
        ormTexture = self.tmpFile(name="OMR", ext="png")
        ormTexture2 = self.tmpFile(name="OMR", ext="png")
        roughnessTexture = self.tmpFile(name="R", ext="png")
        roughnessTexture2 = self.tmpFile(name="R", ext="png")
        metallicTexture = self.tmpFile(name="M", ext="png")
        metallicTexture2 = self.tmpFile(name="M", ext="png")

        red = usdex.core.sRgbToLinear(Gf.Vec3f(0.8, 0.1, 0.1))

        # OmniPBR test stage overload
        materialPath = materialScopePath.AppendChild("ORM_Material")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        opacity = 1.0
        roughness = 0.77
        metallic = 0.33
        material = usdex.rtx.definePbrMaterial(stage, materialPath, color=red, roughness=roughness, metallic=metallic)
        usdex.core.bindMaterial(cylinder, material)
        usdex.core.bindMaterial(plane, material)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))
        self._validateMaterial(material)
        self._validateShader(mdlShader, "OmniPBR")
        self._validateShader(previewShader, "UsdPreviewSurface")
        self._validateMdlConnection(material, mdlShader)
        self._validatePreviewShaderConnection(material, previewShader)
        self._validateOmniPBRMaterial(stage, material, mdlShader, previewShader, red, 1.0, roughness, metallic)

        # Diffuse
        def checkDiffuseTexture(matPrim, tex, color, fallback=None, diffLayer=False):
            self.assertTrue(usdex.rtx.addDiffuseTextureToPbrMaterial(matPrim, tex))
            # Check that "Color" was removed if the texture was applied with the same edit target
            if diffLayer:
                self.assertTrue(matPrim.GetInput("diffuseColor"))
            else:
                self.assertFalse(matPrim.GetInput("diffuseColor"))
            # Check that many other inputs were modified and set
            primStShader = UsdShade.Shader(stage.GetPrimAtPath(materialPath.AppendChild("TexCoordReader")))
            self.assertTrue(isinstance(primStShader, UsdShade.Shader))
            diffuseTexShader = UsdShade.Shader(stage.GetPrimAtPath(materialPath.AppendChild("DiffuseTexture")))
            self.assertTrue(isinstance(diffuseTexShader, UsdShade.Shader))
            self.assertEqual(computeEffectiveShaderInputValue(matPrim.GetInput("DiffuseTexture")).path, tex)
            self.assertEqual(matPrim.GetInput("DiffuseTexture").GetAttr().GetColorSpace(), "auto")
            self.assertEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("diffuse_color_constant")), color)
            self.assertEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("diffuse_texture")).path, tex)
            self.assertTrue(mdlShader.GetInput("diffuse_texture").HasConnectedSource())
            fallback = color if fallback is None else fallback
            self.assertEqual(
                computeEffectiveShaderInputValue(diffuseTexShader.GetInput("fallback")), Gf.Vec4f(fallback[0], fallback[1], fallback[2], 1.0)
            )
            self.assertTrue(diffuseTexShader.GetInput("file").HasConnectedSource())
            source, sourceName, sourceType = diffuseTexShader.GetInput("file").GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Input)
            self.assertEqual(source.GetInput(sourceName), matPrim.GetInput("DiffuseTexture"))
            self.assertEqual(computeEffectiveShaderInputValue(diffuseTexShader.GetInput("sourceColorSpace")), "auto")
            self.assertTrue(previewShader.GetInput("diffuseColor").HasConnectedSource())

        checkDiffuseTexture(material, diffuseTexture2, red)
        # The second time there'll be no fallback color to read from the material input
        checkDiffuseTexture(material, diffuseTexture, red, fallback=Gf.Vec3f(0))

        # Normal
        def checkNormalTexture(matPrim, tex):
            self.assertTrue(usdex.rtx.addNormalTextureToPbrMaterial(matPrim, tex))
            normalTexShader = UsdShade.Shader(stage.GetPrimAtPath(materialPath.AppendChild("NormalTexture")))
            self.assertTrue(isinstance(normalTexShader, UsdShade.Shader))
            self.assertEqual(computeEffectiveShaderInputValue(matPrim.GetInput("NormalTexture")).path, tex)
            self.assertEqual(matPrim.GetInput("NormalTexture").GetAttr().GetColorSpace(), "raw")
            self.assertEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("normalmap_texture")).path, tex)
            self.assertTrue(mdlShader.GetInput("normalmap_texture").HasConnectedSource())
            self.assertEqual(computeEffectiveShaderInputValue(normalTexShader.GetInput("fallback")), Gf.Vec4f(0.0, 0.0, 1.0, 1.0))
            self.assertTrue(normalTexShader.GetInput("file").HasConnectedSource())
            source, sourceName, sourceType = normalTexShader.GetInput("file").GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Input)
            self.assertEqual(source.GetInput(sourceName), matPrim.GetInput("NormalTexture"))
            self.assertEqual(computeEffectiveShaderInputValue(normalTexShader.GetInput("sourceColorSpace")), "raw")
            self.assertTrue(previewShader.GetInput("normal").HasConnectedSource())

        checkNormalTexture(material, normalTexture2)
        checkNormalTexture(material, normalTexture)

        # ORM
        def checkOrmTexture(matPrim, tex, r, m, fallback=None, diffLayer=False):
            self.assertTrue(usdex.rtx.addOrmTextureToPbrMaterial(matPrim, tex))
            if diffLayer:
                self.assertTrue(matPrim.GetInput("roughness"))
                self.assertTrue(matPrim.GetInput("metallic"))
            else:
                self.assertFalse(matPrim.GetInput("roughness"))
                self.assertFalse(matPrim.GetInput("metallic"))
            ormTexShader = UsdShade.Shader(stage.GetPrimAtPath(materialPath.AppendChild("ORMTexture")))
            self.assertTrue(isinstance(ormTexShader, UsdShade.Shader))
            self.assertEqual(computeEffectiveShaderInputValue(matPrim.GetInput("ORMTexture")).path, tex)
            self.assertEqual(matPrim.GetInput("ORMTexture").GetAttr().GetColorSpace(), "raw")
            self.assertEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("ORM_texture")).path, tex)
            self.assertTrue(mdlShader.GetInput("ORM_texture").HasConnectedSource())
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("reflection_roughness_texture_influence")), 1.0)
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("metallic_texture_influence")), 1.0)
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("reflection_roughness_constant")), r)
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("metallic_constant")), m)
            fallback = Gf.Vec4f(1, r, m, 1) if fallback is None else fallback
            self.assertEqual(computeEffectiveShaderInputValue(ormTexShader.GetInput("fallback")), fallback)
            self.assertTrue(ormTexShader.GetInput("file").HasConnectedSource())
            source, sourceName, sourceType = ormTexShader.GetInput("file").GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Input)
            self.assertEqual(source.GetInput(sourceName), matPrim.GetInput("ORMTexture"))
            self.assertEqual(computeEffectiveShaderInputValue(ormTexShader.GetInput("sourceColorSpace")), "raw")
            self.assertTrue(previewShader.GetInput("roughness").HasConnectedSource())
            self.assertTrue(previewShader.GetInput("metallic").HasConnectedSource())

        checkOrmTexture(material, ormTexture2, roughness, metallic)
        # The second time there'll be no fallback color to read from the material input
        checkOrmTexture(material, ormTexture, roughness, metallic, fallback=Gf.Vec4f(1, 0.5, 0, 1))

        # Make a new material to test R & M separately
        materialPath = materialScopePath.AppendChild("RM_Material")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        material = usdex.rtx.definePbrMaterial(stage, materialPath, color=red, roughness=roughness, metallic=metallic)
        usdex.core.bindMaterial(cylinder, material)
        usdex.core.bindMaterial(plane, material)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))

        # Diffuse & Normal
        checkDiffuseTexture(material, diffuseTexture, red)
        checkNormalTexture(material, normalTexture)

        # Add and check roughness
        def checkRoughnessTexture(matPrim, tex, r, fallback=None, diffLayer=False):
            self.assertTrue(usdex.rtx.addRoughnessTextureToPbrMaterial(matPrim, tex))
            if diffLayer:
                self.assertTrue(matPrim.GetInput("roughness"))
            else:
                self.assertFalse(matPrim.GetInput("roughness"))
            roughnessTexShader = UsdShade.Shader(stage.GetPrimAtPath(materialPath.AppendChild("RoughnessTexture")))
            self.assertTrue(isinstance(roughnessTexShader, UsdShade.Shader))
            self.assertEqual(computeEffectiveShaderInputValue(matPrim.GetInput("RoughnessTexture")).path, tex)
            self.assertEqual(matPrim.GetInput("RoughnessTexture").GetAttr().GetColorSpace(), "raw")
            self.assertEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("reflectionroughness_texture")).path, tex)
            self.assertTrue(mdlShader.GetInput("reflectionroughness_texture").HasConnectedSource())
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("reflection_roughness_texture_influence")), 1.0)
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("reflection_roughness_constant")), r)
            fallback = r if fallback is None else fallback
            self.assertAlmostEqual(computeEffectiveShaderInputValue(roughnessTexShader.GetInput("fallback"))[0], fallback)
            self.assertTrue(roughnessTexShader.GetInput("file").HasConnectedSource())
            source, sourceName, sourceType = roughnessTexShader.GetInput("file").GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Input)
            self.assertEqual(source.GetInput(sourceName), matPrim.GetInput("RoughnessTexture"))
            self.assertEqual(computeEffectiveShaderInputValue(roughnessTexShader.GetInput("sourceColorSpace")), "raw")
            self.assertTrue(previewShader.GetInput("roughness").HasConnectedSource())

        checkRoughnessTexture(material, roughnessTexture2, roughness)
        # The second time there'll be no fallback color to read from the material input
        checkRoughnessTexture(material, roughnessTexture, roughness, fallback=0.5)

        # Add and check metallic
        def checkMetallicTexture(matPrim, tex, m, fallback=None, diffLayer=False):
            self.assertTrue(usdex.rtx.addMetallicTextureToPbrMaterial(matPrim, tex))
            # Check that "Metallic" was removed if the texture was applied with the same edit target
            if diffLayer:
                self.assertTrue(matPrim.GetInput("metallic"))
            else:
                self.assertFalse(matPrim.GetInput("metallic"))
            metallicTexShader = UsdShade.Shader(stage.GetPrimAtPath(materialPath.AppendChild("MetallicTexture")))
            self.assertTrue(isinstance(metallicTexShader, UsdShade.Shader))
            self.assertEqual(computeEffectiveShaderInputValue(matPrim.GetInput("MetallicTexture")).path, tex)
            self.assertEqual(matPrim.GetInput("MetallicTexture").GetAttr().GetColorSpace(), "raw")
            self.assertEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("metallic_texture")).path, tex)
            self.assertTrue(mdlShader.GetInput("metallic_texture").HasConnectedSource())
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("metallic_texture_influence")), 1.0)
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("metallic_constant")), m)
            fallback = m if fallback is None else fallback
            self.assertAlmostEqual(computeEffectiveShaderInputValue(metallicTexShader.GetInput("fallback"))[0], fallback)
            self.assertTrue(metallicTexShader.GetInput("file").HasConnectedSource())
            source, sourceName, sourceType = metallicTexShader.GetInput("file").GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Input)
            self.assertEqual(source.GetInput(sourceName), matPrim.GetInput("MetallicTexture"))
            self.assertEqual(computeEffectiveShaderInputValue(metallicTexShader.GetInput("sourceColorSpace")), "raw")
            self.assertTrue(previewShader.GetInput("metallic").HasConnectedSource())

        checkMetallicTexture(material, metallicTexture2, metallic)
        # The second time there'll be no fallback color to read from the material input
        checkMetallicTexture(material, metallicTexture, metallic, fallback=0.0)

        # Add and check opacity
        def checkOpacityTexture(matPrim, tex, o, fallback=None, diffLayer=False):
            self.assertTrue(usdex.rtx.addOpacityTextureToPbrMaterial(matPrim, tex))
            if diffLayer:
                self.assertTrue(matPrim.GetInput("opacity"))
            else:
                self.assertFalse(matPrim.GetInput("opacity"))
            opacityTexShader = UsdShade.Shader(stage.GetPrimAtPath(materialPath.AppendChild("OpacityTexture")))
            self.assertTrue(isinstance(opacityTexShader, UsdShade.Shader))
            self.assertEqual(computeEffectiveShaderInputValue(matPrim.GetInput("OpacityTexture")).path, tex)
            self.assertEqual(matPrim.GetInput("OpacityTexture").GetAttr().GetColorSpace(), "raw")
            self.assertEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("opacity_texture")).path, tex)
            self.assertTrue(mdlShader.GetInput("opacity_texture").HasConnectedSource())

            # Opacity threshold on a PBR greater than 0 (float epsilon) otherwise cutout textures don't work properly
            shaderInput = mdlShader.GetInput("opacity_threshold")
            self.assertTrue(shaderInput)
            self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
            self.assertGreater(computeEffectiveShaderInputValue(shaderInput), 0)

            self.assertEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("enable_opacity_texture")), True)
            self.assertAlmostEqual(computeEffectiveShaderInputValue(mdlShader.GetInput("opacity_constant")), o)
            fallback = o if fallback is None else fallback
            self.assertAlmostEqual(computeEffectiveShaderInputValue(opacityTexShader.GetInput("fallback"))[0], fallback)
            self.assertTrue(opacityTexShader.GetInput("file").HasConnectedSource())
            source, sourceName, sourceType = opacityTexShader.GetInput("file").GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Input)
            self.assertEqual(source.GetInput(sourceName), matPrim.GetInput("OpacityTexture"))
            self.assertEqual(computeEffectiveShaderInputValue(opacityTexShader.GetInput("sourceColorSpace")), "raw")
            self.assertTrue(previewShader.GetInput("opacity").HasConnectedSource())

            # IOR on a PBR should be 1.0 otherwise there's excess color rather than transparency
            shaderInput = previewShader.GetInput("ior")
            self.assertTrue(shaderInput)
            self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
            self.assertAlmostEqual(computeEffectiveShaderInputValue(shaderInput), 1.0)

            # Opacity threshold on a PBR greater than 0 (float epsilon) otherwise cutout textures don't work properly
            shaderInput = previewShader.GetInput("opacityThreshold")
            self.assertTrue(shaderInput)
            self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
            self.assertGreater(computeEffectiveShaderInputValue(shaderInput), 0)

        checkOpacityTexture(material, opacityTexture2, opacity)
        # The second time there'll be no fallback color to read from the material input
        checkOpacityTexture(material, opacityTexture, opacity, fallback=1.0)

        # Make a new material to mess with from the session layer (not unlike a .live layer)
        materialPath = materialScopePath.AppendChild("RootLayer_Material")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)
        material = usdex.rtx.definePbrMaterial(stage, materialPath, color=red, roughness=roughness, metallic=metallic)
        usdex.core.bindMaterial(cylinder, material)
        usdex.core.bindMaterial(plane, material)
        mdlShader = UsdShade.Shader(stage.GetPrimAtPath(mdlShaderPath))
        previewShader = UsdShade.Shader(stage.GetPrimAtPath(previewShaderPath))

        stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*doesn't exist in the current edit target layer")] * 6):
            checkDiffuseTexture(material, diffuseTexture, red, diffLayer=True)
            checkNormalTexture(material, normalTexture)
            checkOrmTexture(material, ormTexture, roughness, metallic, diffLayer=True)
            # roughness and metallic need default fallbacks because ORM will have already cleared the original value
            checkRoughnessTexture(material, roughnessTexture, roughness, fallback=0.5, diffLayer=True)
            checkMetallicTexture(material, metallicTexture, metallic, fallback=0.0, diffLayer=True)
            checkOpacityTexture(material, opacityTexture, opacity, diffLayer=True)

        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(3, "OmniPBR.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            self.assertIsValidUsd(stage, issuePredicates=self.allowedIssuePredicates())

    def testInvalidTexturedMaterialDefinition(self):
        stage = self._createTestStage()
        materialScopePath = stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())
        mdlShaderName = "MDLShader"
        usdShaderName = "PreviewSurface"
        red = usdex.core.sRgbToLinear(Gf.Vec3f(0.8, 0.1, 0.1))

        # OmniPBR test stage overload
        materialPath = materialScopePath.AppendChild("TestMaterial")
        mdlShaderPath = materialPath.AppendChild(mdlShaderName)
        previewShaderPath = materialPath.AppendChild(usdShaderName)

        def checkNoTextureAdds(material):
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot add texture")] * 6):
                self.assertFalse(usdex.rtx.addDiffuseTextureToPbrMaterial(material, "my_diffuse_texture_path"))
                self.assertFalse(usdex.rtx.addNormalTextureToPbrMaterial(material, "my_normal_texture_path"))
                self.assertFalse(usdex.rtx.addOrmTextureToPbrMaterial(material, "my_orm_texture_path"))
                self.assertFalse(usdex.rtx.addRoughnessTextureToPbrMaterial(material, "my_roughness_texture_path"))
                self.assertFalse(usdex.rtx.addMetallicTextureToPbrMaterial(material, "my_metallic_texture_path"))
                self.assertFalse(usdex.rtx.addOpacityTextureToPbrMaterial(material, "my_opacity_texture_path"))

        # different MDL
        # "Cannot add texture <%s>, the MDL UsdShadShader <%s> does not have the correct source asset <OmniPBR.mdl>. It is using <OmniGlass.mdl>"
        material = usdex.rtx.defineGlassMaterial(stage, materialPath, color=Gf.Vec3f(0.2))
        checkNoTextureAdds(material)
        self.assertTrue(stage.RemovePrim(materialPath))

        # Missing MDL shader
        # "Cannot add texture <%s>, UsdShadeMaterial <%s> does not have a valid MDL Shader"
        material = usdex.rtx.definePbrMaterial(stage, materialPath, color=red)
        self.assertTrue(stage.RemovePrim(mdlShaderPath))
        checkNoTextureAdds(material)
        self.assertTrue(stage.RemovePrim(materialPath))

        # Missing USD Preview Surface shader
        # "Cannot add texture <%s>, UsdShadeMaterial <%s> does not have a valid USD Preview Surface Shader"
        material = usdex.rtx.definePbrMaterial(stage, materialPath, color=red)
        self.assertTrue(stage.RemovePrim(previewShaderPath))
        checkNoTextureAdds(material)
        self.assertTrue(stage.RemovePrim(materialPath))

        # Invalid material
        # "Cannot add texture <%s>, UsdShadeMaterial <%s> is not a valid material"
        checkNoTextureAdds(UsdShade.Material())

        self.assertIsValidUsd(stage)

    def testCreateMdlShaderInput(self):
        stage = self._createTestStage()
        materialScopePath = stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())
        cylinder = stage.GetPrimAtPath("/Root/Geometry/Xform/Cylinder")
        plane = stage.GetPrimAtPath("/Root/Geometry/Xform/Plane")
        diffuseTexture = self.tmpFile(name="BaseColor", ext="png")
        normalTexture = self.tmpFile(name="N", ext="png")
        color = usdex.core.sRgbToLinear(Gf.Vec3f(0.0, 0.5, 0.5))

        materialPath = materialScopePath.AppendChild("Diffuse_Material")

        # Invalid material
        invalidMaterial = UsdShade.Material()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*cannot create MDL shader input")]):
            shaderInput = usdex.rtx.createMdlShaderInput(invalidMaterial, "invalid_material_input", "invalid_value", Sdf.ValueTypeNames.Asset)
        self.assertIsInstance(shaderInput, UsdShade.Input)
        self.assertFalse(shaderInput)

        # Invalid MDL shader
        noShaderMaterial = usdex.core.createMaterial(stage.GetDefaultPrim(), "NoShaderMaterial")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create MDL shader input")]):
            shaderInput = usdex.rtx.createMdlShaderInput(noShaderMaterial, "invalid_mdl_shader_input", "invalid_value", Sdf.ValueTypeNames.Asset)
        self.assertIsInstance(shaderInput, UsdShade.Input)
        self.assertFalse(shaderInput)

        # OmniPBR test stage overload
        material = usdex.rtx.definePbrMaterial(stage, materialPath, color=color)
        self.assertTrue(usdex.rtx.addDiffuseTextureToPbrMaterial(material, diffuseTexture))
        usdex.core.bindMaterial(cylinder, material)
        usdex.core.bindMaterial(plane, material)

        def checkMdlShaderInput(matPrim, name, value, typeName, colorSpace=None):
            shaderInput = usdex.rtx.createMdlShaderInput(matPrim, name, value, typeName, colorSpace)
            self.assertIsInstance(shaderInput, UsdShade.Input)
            self.assertTrue(shaderInput)
            attr = shaderInput.GetAttr()
            if typeName == Sdf.ValueTypeNames.Asset:
                self.assertEqual(computeEffectiveShaderInputValue(shaderInput).path, value)
            else:
                self.assertEqual(computeEffectiveShaderInputValue(shaderInput), value)
            self.assertEqual(shaderInput.GetBaseName(), name)
            self.assertEqual(shaderInput.GetTypeName(), typeName)
            self.assertEqual(attr.GetColorSpace(), "" if colorSpace is None else usdex.core.getColorSpaceToken(colorSpace))

        checkMdlShaderInput(material, "project_uvw", True, Sdf.ValueTypeNames.Bool)
        checkMdlShaderInput(material, "diffuse_texture", normalTexture, Sdf.ValueTypeNames.Asset, usdex.core.ColorSpace.eSrgb)
        checkMdlShaderInput(material, "diffuse_texture", normalTexture, Sdf.ValueTypeNames.Asset, usdex.core.ColorSpace.eRaw)
        checkMdlShaderInput(material, "diffuse_texture", diffuseTexture, Sdf.ValueTypeNames.Asset, usdex.core.ColorSpace.eAuto)
        checkMdlShaderInput(material, "normalmap_texture", normalTexture, Sdf.ValueTypeNames.Asset, usdex.core.ColorSpace.eRaw)
        checkMdlShaderInput(material, "opacity_mode", 1, Sdf.ValueTypeNames.Int)
        checkMdlShaderInput(material, "bump_factor", 2.0, Sdf.ValueTypeNames.Float)
        checkMdlShaderInput(material, "texture_translate", Gf.Vec2f(1.0, 1.0), Sdf.ValueTypeNames.Float2)
        checkMdlShaderInput(material, "diffuse_tint", Gf.Vec3f(1.0, 1.0, 0.0), Sdf.ValueTypeNames.Color3f)
        checkMdlShaderInput(material, "example_token", "token_string", Sdf.ValueTypeNames.Token)

        # Attempt to change the type (it should work in this edit target)
        checkMdlShaderInput(material, "opacity_mode", "mono_alpha", Sdf.ValueTypeNames.Token)

        # Change the edit target to the session layer and attempt to write an input with a different type
        stage.SetEditTarget(Usd.EditTarget(stage.GetSessionLayer()))

        # Attempt to change the type (it should NOT work in this edit target)
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*input already exists as type <token>"),
                (Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*doesn't exist in the current edit target layer"),
            ],
        ):
            shaderInput = usdex.rtx.createMdlShaderInput(material, "opacity_mode", 1, Sdf.ValueTypeNames.Int)
        self.assertIsInstance(shaderInput, UsdShade.Input)
        self.assertFalse(shaderInput)

        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(1, "OmniPBR.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            self.assertIsValidUsd(stage, issuePredicates=self.allowedIssuePredicates())

    def testCannotAddPreviewMaterialInterface(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        material = usdex.core.definePreviewMaterial(materials, "Test", color=Gf.Vec3f(0.25, 0.5, 0.25), roughness=0.77, metallic=0.33, opacity=0.8)

        # creating a MDL surface shader will prevent the Preview Material interface from succeeding
        usdex.rtx.createMdlShader(material, "TestMDL", mdlPath=Sdf.AssetPath("OmniPBR.mdl"), module="OmniPBR")

        # the material starts with no inputs
        self.assertEqual(material.GetInputs(), [])

        # multiple render contexts will error gracefully
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*has 2 effective surface outputs.")]):
            result = usdex.core.addPreviewMaterialInterface(material)
        self.assertFalse(result)
        self.assertEqual(material.GetInputs(), [])

        # disconnecting the MDL surface will allow the Preview Material Interface to be authored
        material.GetSurfaceOutput("mdl").ClearSources()
        result = usdex.core.addPreviewMaterialInterface(material)
        self.assertTrue(result)
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["diffuseColor", "metallic", "opacity", "roughness"],
        )


class definePbrMaterialTestCase(usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCaseMixin
    defineFunc = usdex.rtx.definePbrMaterial
    requiredArgs = tuple([Gf.Vec3f(1.0, 1.0, 1.0)])
    typeName = "Material"
    schema = UsdShade.Material
    requiredPropertyNames = set()
    defaultValidationIssuePredicates = MaterialAlgoTest.allowedIssuePredicates()

    def testStagePathSuccess(self):
        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(1, "OmniPBR.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            super().testStagePathSuccess()

    def testWeakerStronger(self):
        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(2, "OmniPBR.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            super().testWeakerStronger()

    def testStrongerWeaker(self):
        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(2, "OmniPBR.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            super().testStrongerWeaker()

    def testParentNameSuccess(self):
        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(1, "OmniPBR.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            super().testParentNameSuccess()


class defineGlassMaterialTestCase(usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCaseMixin
    defineFunc = usdex.rtx.defineGlassMaterial
    requiredArgs = tuple([Gf.Vec3f(1.0, 1.0, 1.0)])
    typeName = "Material"
    schema = UsdShade.Material
    requiredPropertyNames = set()
    defaultValidationIssuePredicates = MaterialAlgoTest.allowedIssuePredicates()

    def testStagePathSuccess(self):
        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(1, "OmniGlass.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            super().testStagePathSuccess()

    def testWeakerStronger(self):
        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(2, "OmniGlass.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            super().testWeakerStronger()

    def testStrongerWeaker(self):
        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(2, "OmniGlass.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            super().testStrongerWeaker()

    def testParentNameSuccess(self):
        expected = MaterialAlgoTest.getExpectedResolveDiagMsgs(1, "OmniGlass.mdl")
        with usdex.test.ScopedDiagnosticChecker(self, expected):
            super().testParentNameSuccess()
