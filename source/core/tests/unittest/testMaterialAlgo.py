# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import pathlib
import tempfile
from typing import Any, List, Tuple

import usd_validation_nvidia
import usdex.core
import usdex.test
from pxr import Gf, Plug, Sdf, Sdr, Tf, Usd, UsdGeom, UsdMtlx, UsdShade, UsdUtils, Vt

# USD 25.08 made the MaterialX standard library relocatable. Older runtimes locate it only via this variable, so no MaterialX node
# resolves through `Sdr` and every shader authored below fails `ShaderSdrCompliance`. Point it at the libraries we install with the
# usdMtlx plugin, at import time, as the registry caches these paths the first time it is used.
if Usd.GetVersion()[:2] < (25, 8) and "PXR_MTLX_STDLIB_SEARCH_PATHS" not in os.environ:
    os.environ["PXR_MTLX_STDLIB_SEARCH_PATHS"] = os.path.join(Plug.Registry().GetPluginWithName("usdMtlx").resourcePath, "libraries")


def assertMetadataValueEqual(testCase: usdex.test.TestCase, actual: Any, expected: Any):
    if isinstance(expected, Gf.Vec3f):
        testCase.assertTrue(Gf.IsClose(actual, expected, 1e-6), msg=f"{actual} != {expected}")
    else:
        testCase.assertEqual(actual, expected)


def assertLimitMetadata(
    testCase: usdex.test.TestCase,
    shaderInput: UsdShade.Input,
    expectedSdrMetadata: dict[str, str],
    expectedLimits: dict[str, dict[str, Any]],
):
    testCase.assertTrue(shaderInput.HasSdrMetadata())
    testCase.assertFalse(shaderInput.HasSdrMetadataByKey("default"))
    for key, value in expectedSdrMetadata.items():
        testCase.assertEqual(shaderInput.GetSdrMetadataByKey(key), value)
        testCase.assertNotIn(key, shaderInput.GetAttr().GetCustomData())

    limits = shaderInput.GetAttr().GetMetadata("limits")
    testCase.assertTrue(limits)
    for subDictKey, expectedSubDict in expectedLimits.items():
        testCase.assertIn(subDictKey, limits)
        for key, expectedValue in expectedSubDict.items():
            testCase.assertIn(key, limits[subDictKey])
            assertMetadataValueEqual(testCase, limits[subDictKey][key], expectedValue)


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

    def testBindMaterialSubsets(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        geometry = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild("Geometry")).GetPrim()  # common convention

        material_1 = usdex.core.createMaterial(materials, "Material_1")
        material_2 = usdex.core.createMaterial(materials, "Material_2")
        material_3 = usdex.core.createMaterial(materials, "Material_3")

        # Create a mesh with four faces.
        vertices = [
            Gf.Vec3f(-50.0, 0.0, 50.0),
            Gf.Vec3f(0.0, 0.0, 50.0),
            Gf.Vec3f(50.0, 0.0, 50.0),
            Gf.Vec3f(-50.0, 0.0, 0.0),
            Gf.Vec3f(0.0, 0.0, 0.0),
            Gf.Vec3f(50.0, 0.0, 0.0),
            Gf.Vec3f(-50.0, 0.0, -50.0),
            Gf.Vec3f(0.0, 0.0, -50.0),
            Gf.Vec3f(50.0, 0.0, -50.0),
        ]
        normals = [
            Gf.Vec3f(0.0, 1.0, 0.0),
        ]
        uvs = [
            Gf.Vec2f(0.0, 0.0),
            Gf.Vec2f(0.5, 0.0),
            Gf.Vec2f(0.5, 1.0),
            Gf.Vec2f(0.0, 1.0),
        ]
        normals_indices = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        uvs_indices = [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3]

        points = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray(vertices))
        face_vertex_indices = [0, 1, 4, 3, 1, 2, 5, 4, 3, 4, 7, 6, 4, 5, 8, 7]
        face_vertex_counts = [4, 4, 4, 4]

        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray(normals), indices=Vt.IntArray(normals_indices))
        uvs = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec2fArray(uvs), indices=Vt.IntArray(uvs_indices))

        mesh = usdex.core.definePolyMesh(
            geometry.GetPrim(),
            "mesh",
            faceVertexCounts=Vt.IntArray(face_vertex_counts),
            faceVertexIndices=Vt.IntArray(face_vertex_indices),
            points=points.values(),
            normals=normals,
            uvs=uvs,
        )

        # Create three subsets of the mesh.
        names = ["subset1", "subset2", "subset3"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2]),
            Vt.IntArray([3]),
        ]
        subsets = usdex.core.definePartitionedSubsets(mesh, names, indices)
        self.assertEqual(len(subsets), 3)
        subset1 = mesh.GetPrim().GetChild(names[0])
        self.assertTrue(subset1.IsValid())
        subset2 = mesh.GetPrim().GetChild(names[1])
        self.assertTrue(subset2.IsValid())
        subset3 = mesh.GetPrim().GetChild(names[2])
        self.assertTrue(subset3.IsValid())

        # Bind the materials to the subsets (parallel lists, same order).
        result = usdex.core.bindMaterialSubsets(subsets, [material_1, material_2, material_3])
        self.assertTrue(result)

        # Check that the materials were bound to the subsets.
        self.assertTrue(subset1.HasAPI(UsdShade.MaterialBindingAPI))
        self.assertTrue(subset2.HasAPI(UsdShade.MaterialBindingAPI))
        self.assertTrue(subset3.HasAPI(UsdShade.MaterialBindingAPI))

        self.assertIsValidUsd(stage)

        # Empty materials list.
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, "Unable to bind materials to subsets: The subsets or materials are empty.")]
        ):
            result = usdex.core.bindMaterialSubsets(subsets, [])
        self.assertFalse(result)

        # Mismatched number of subsets and materials.
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    "Unable to bind materials to subsets: The number of subsets does not equal the number of materials.",
                )
            ],
        ):
            result = usdex.core.bindMaterialSubsets(subsets, [material_1, material_2])
        self.assertFalse(result)

        # Invalid UsdGeomSubset schema (default-constructed).
        invalid_subset = UsdGeom.Subset()
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Unable to bind materials to subsets: The subset .* is not valid.*")]
        ):
            result = usdex.core.bindMaterialSubsets([invalid_subset], [material_1])
        self.assertFalse(result)

        # Invalid material. In this case, an error occurs in `bindMaterial`, which is called internally by `bindMaterialSubsets`.
        empty_material = UsdShade.Material()
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Unable to bind materials to subsets: The material .* is not valid.*")]
        ):
            result = usdex.core.bindMaterialSubsets([subsets[0]], [empty_material])
        self.assertFalse(result)

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

    def testComputeEffectiveMtlxSurfaceShader(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # An un-initialized Material will result in an invalid shader
        material = UsdShade.Material()
        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertFalse(shader)

        # An invalid Material will result in an invalid shader
        material = UsdShade.Material(stage.GetPrimAtPath("/Root"))
        self.assertFalse(material)
        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertFalse(shader)

        # A Material with no connected shaders will result in an invalid shader
        material = usdex.core.createMaterial(materials, "MtlxMaterial")
        self.assertTrue(material)
        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertFalse(shader)

        # With only the universal render context connected, that shader will be returned for both render contexts
        universalShader = UsdShade.Shader.Define(stage, material.GetPrim().GetPath().AppendChild("PreviewSurface"))
        self.assertTrue(universalShader)
        material.CreateSurfaceOutput().ConnectToSource(universalShader.CreateOutput("out", Sdf.ValueTypeNames.Token))
        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), universalShader.GetPrim())
        # Confirm the universal function does find it
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), universalShader.GetPrim())

        # A shader connected to the mtlx context IS found
        mtlxShader = UsdShade.Shader.Define(stage, material.GetPrim().GetPath().AppendChild("OpenPBR"))
        self.assertTrue(mtlxShader)
        material.CreateSurfaceOutput("mtlx").ConnectToSource(mtlxShader.CreateOutput("out", Sdf.ValueTypeNames.Token))
        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), mtlxShader.GetPrim())

        # The universal context still returns the universal shader, not the mtlx one
        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), universalShader.GetPrim())
        self.assertNotEqual(shader.GetPrim(), mtlxShader.GetPrim())

        # A material with only an mtlx output does not return a shader for the universal context
        mtlxOnlyMaterial = usdex.core.createMaterial(materials, "MtlxOnlyMaterial")
        mtlxOnlyShader = UsdShade.Shader.Define(stage, mtlxOnlyMaterial.GetPrim().GetPath().AppendChild("OpenPBR"))
        mtlxOnlyMaterial.CreateSurfaceOutput("mtlx").ConnectToSource(mtlxOnlyShader.CreateOutput("out", Sdf.ValueTypeNames.Token))
        shader = usdex.core.computeEffectiveMtlxSurfaceShader(mtlxOnlyMaterial)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim(), mtlxOnlyShader.GetPrim())
        shader = usdex.core.computeEffectivePreviewSurfaceShader(mtlxOnlyMaterial)
        self.assertFalse(shader)

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

        greyLinear = Gf.Vec3f(0.21404113, 0.21404114, 0.21404111)
        darkRedLinear = Gf.Vec3f(0.08898155, 0.010022826, 0.010022825)
        lightGreenLinear = Gf.Vec3f(0.40644825, 0.9331069, 0.40644827)
        purpleLinear = Gf.Vec3f(0.17064494, 0.033104762, 0.3185468)
        blackLinear = Gf.Vec3f(0.0023214042, 0.0023214044, 0.0023214042)

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

        self.assertTrue(Gf.IsClose(convertedGreyLinear, greyLinear, 1e-6))
        self.assertTrue(Gf.IsClose(convertedDarkRedLinear, darkRedLinear, 1e-6))
        self.assertTrue(Gf.IsClose(convertedLightGreenLinear, lightGreenLinear, 1e-6))
        self.assertTrue(Gf.IsClose(convertedPurpleLinear, purpleLinear, 1e-6))
        self.assertTrue(Gf.IsClose(convertedBlackLinear, blackLinear, 1e-6))

        self.assertTrue(Gf.IsClose(convertedGreySrgb, greySrgb, 1e-6))
        self.assertTrue(Gf.IsClose(convertedDarkRedSrgb, darkRedSrgb, 1e-6))
        self.assertTrue(Gf.IsClose(convertedLightGreenSrgb, lightGreenSrgb, 1e-6))
        self.assertTrue(Gf.IsClose(convertedPurpleSrgb, purpleSrgb, 1e-6))
        self.assertTrue(Gf.IsClose(convertedBlackSrgb, blackSrgb, 1e-6))

        self.assertTrue(Gf.IsClose(roundTripGreyLinear, greyLinear, 1e-6))
        self.assertTrue(Gf.IsClose(roundTripRedLinear, darkRedLinear, 1e-6))
        self.assertTrue(Gf.IsClose(roundTripGreenLinear, lightGreenLinear, 1e-6))
        self.assertTrue(Gf.IsClose(roundTripPurpleLinear, purpleLinear, 1e-6))
        self.assertTrue(Gf.IsClose(roundTripBlackLinear, blackLinear, 1e-6))

        self.assertTrue(Gf.IsClose(roundTripGreySrgb, greySrgb, 1e-6))
        self.assertTrue(Gf.IsClose(roundTripRedSrgb, darkRedSrgb, 1e-6))
        self.assertTrue(Gf.IsClose(roundTripGreenSrgb, lightGreenSrgb, 1e-6))
        self.assertTrue(Gf.IsClose(roundTripPurpleSrgb, purpleSrgb, 1e-6))
        self.assertTrue(Gf.IsClose(roundTripBlackSrgb, blackSrgb, 1e-6))

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


class PreviewMaterialHelpersMixin:
    """Mixin providing UPS texture network validation for test classes that verify PreviewSurface shader networks."""

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
        # wrap mode is set to repeat
        self.assertEqual(textureReader.GetInput("wrapS").GetAttr().Get(), "repeat")
        self.assertEqual(textureReader.GetInput("wrapT").GetAttr().Get(), "repeat")

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

    def assertIsSurfaceShader(self, material: UsdShade.Material, shader: UsdShade.Shader):
        surfaceOutput = material.GetSurfaceOutput("mtlx")
        self.assertTrue(surfaceOutput)
        self.assertTrue(surfaceOutput.HasConnectedSource())
        surface = surfaceOutput.GetConnectedSource()[0]
        self.assertEqual(surface.GetOutput("out").GetAttr(), shader.GetOutput("out").GetAttr())

    def assertMaterialXVersion(self, material: UsdShade.Material):
        config = UsdMtlx.MaterialXConfigAPI(material.GetPrim())
        self.assertTrue(config)
        self.assertIn("MaterialXConfigAPI", material.GetPrim().GetAppliedSchemas())
        version = config.GetConfigMtlxVersionAttr()
        self.assertTrue(version.HasAuthoredValue())
        self.assertEqual(version.Get(), "1.39")


class DefinePreviewMaterialTest(PreviewMaterialHelpersMixin, usdex.test.DefineFunctionTestCase):

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
            result = usdex.core.addColorTextureToPreviewMaterial(UsdShade.Material(), texture)
        self.assertFalse(result)

        # an invalid surface shader will error gracefully
        badMaterial = UsdShade.Material.Define(parent.GetStage(), parent.GetPath().AppendChild("BadMaterial"))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addColorTextureToPreviewMaterial(badMaterial, texture)
        self.assertFalse(result)

        # a surface shader without an ID will error gracefully
        otherShader = UsdShade.Shader.Define(parent.GetStage(), badMaterial.GetPath().AppendChild("NoShaderId"))
        badMaterial.CreateSurfaceOutput().ConnectToSource(otherShader.CreateOutput(UsdShade.Tokens.surface, Sdf.ValueTypeNames.Token))
        self.assertIsSurfaceShader(badMaterial, otherShader)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addColorTextureToPreviewMaterial(badMaterial, texture)
        self.assertFalse(result)

        # an surface shader that is not a UPS will error gracefully
        otherShader.SetShaderId("UsdUVTexture")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePreviewMaterial")]):
            result = usdex.core.addColorTextureToPreviewMaterial(badMaterial, texture)
        self.assertFalse(result)

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
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), Gf.Vec3f(0.0, 0.5, 1.0), 1e-6))

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
        self.assertFalse(displacementOutput.HasConnectedSource())

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

    def testAddColorTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # a valid preview material will successfully add a color texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.0, 0.5, 1.0))
        result = usdex.core.addColorTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="ColorTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(0.0, 0.5, 1.0),
            connectionInfo=[("diffuseColor", Sdf.ValueTypeNames.Color3f, "rgb")],
        )

        self.assertIsValidUsd(stage)

    def testDeprecatedDiffuseTexture(self):
        texture = self.tmpFile(name="BaseColor", ext="png")

        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.8, 0.1, 0.1))

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Use `addColorTextureToPreviewMaterial` instead")]):
            self.assertTrue(usdex.core.addDiffuseTextureToPreviewMaterial(material, texture))

        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="ColorTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(0.8, 0.1, 0.1),
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
            handle, fileName = tempfile.mkstemp(prefix=f"{os.path.join(tempDir, name)}_", suffix=f".{ext}")
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

    def testAddEmissiveColor(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # a valid preview material will successfully add a emissive color
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.2, 0.2, 0.2))
        result = usdex.core.addEmissiveColorToPreviewMaterial(material, Gf.Vec3f(1.0, 1.0, 0.0))
        self.assertTrue(result)
        surface = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertEqual(surface.GetInput("emissiveColor").GetAttr().Get(), Gf.Vec3f(1.0, 1.0, 0.0))

        self.assertIsValidUsd(stage)

    def testInvalidAddEmissiveColor(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # Invalid emissive color
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.2, 0.2, 0.2))
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Color value .* is invalid: each component must be at least 0 \(no upper bound\).")]
        ):
            result = usdex.core.addEmissiveColorToPreviewMaterial(material, Gf.Vec3f(-1.0, 1.0, 0.0))
        self.assertFalse(result)

        # Specify invalid material
        material = UsdShade.Material()
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Material .* must first be defined using definePreviewMaterial()")]
        ):
            result = usdex.core.addEmissiveColorToPreviewMaterial(material, Gf.Vec3f(1.0, 1.0, 0.0))
        self.assertFalse(result)

        # Materials that do not have UsdPreviewSurface assigned
        material = UsdShade.Material.Define(stage, materials.GetPrim().GetPath().AppendChild("empty_material"))
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Material .* must first be defined using definePreviewMaterial()")]
        ):
            result = usdex.core.addEmissiveColorToPreviewMaterial(material, Gf.Vec3f(1.0, 1.0, 0.0))
        self.assertFalse(result)

        self.assertIsValidUsd(stage)

    def testAddEmissiveTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="emissive", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # a valid preview material will successfully add a emissive texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.2, 0.2, 0.2))
        result = usdex.core.addEmissiveTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="EmissiveTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(0.0, 0.0, 0.0),
            connectionInfo=[("emissiveColor", Sdf.ValueTypeNames.Color3f, "rgb")],
        )

        # the originally defined emissive color value is used in the fallback
        material = usdex.core.definePreviewMaterial(materials, "InitialValues", Gf.Vec3f(0.2, 0.2, 0.2))
        result = usdex.core.addEmissiveColorToPreviewMaterial(material, Gf.Vec3f(1.0, 1.0, 0.2))
        self.assertTrue(result)
        result = usdex.core.addEmissiveTextureToPreviewMaterial(material, texture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            texture,
            textureReaderName="EmissiveTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(1.0, 1.0, 0.2),
            connectionInfo=[("emissiveColor", Sdf.ValueTypeNames.Color3f, "rgb")],
        )

        self.assertIsValidUsd(stage)

    def testInvalidAddEmissiveTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="emissive", ext="png"))

        self.assertInvalidPreviewMaterialForTextureFunctions(parent=materials, texture=texture)

        # Specify invalid material
        material = UsdShade.Material()
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Material .* must first be defined using definePreviewMaterial()")]
        ):
            result = usdex.core.addEmissiveTextureToPreviewMaterial(material, texture)
        self.assertFalse(result)

        # Materials that do not have UsdPreviewSurface assigned
        empty_material = UsdShade.Material.Define(stage, materials.GetPrim().GetPath().AppendChild("empty_material"))
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Material .* must first be defined using definePreviewMaterial()")]
        ):
            result = usdex.core.addEmissiveTextureToPreviewMaterial(empty_material, texture)
        self.assertFalse(result)

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

    def testAddPrimvarShaderWithColorTexture(self):
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

        # Check that a color texture can now be assigned
        colorTexture = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))
        result = usdex.core.addColorTextureToPreviewMaterial(material, colorTexture)
        self.assertTrue(result)
        self.assertValidPreviewMaterialPrimvarNetwork(
            material,
            [("roughness", "perInstanceRoughness", None)],
        )
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            colorTexture,
            textureReaderName="ColorTexture",
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
        colorTexture = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))
        normalTexture = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))

        # a valid preview material will successfully add a color texture
        material = usdex.core.definePreviewMaterial(materials, "Test", Gf.Vec3f(0.0, 0.5, 1.0))
        result = usdex.core.addColorTextureToPreviewMaterial(material, colorTexture)
        self.assertTrue(result)
        result = usdex.core.addNormalTextureToPreviewMaterial(material, normalTexture)
        self.assertTrue(result)

        # both inputs are driven by the expected textures
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            colorTexture,
            textureReaderName="ColorTexture",
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


class DefinePbrMaterialTest(PreviewMaterialHelpersMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase (same pattern as DefinePreviewMaterialTest)
    defineFunc = usdex.core.definePbrMaterial
    requiredArgs = tuple([Gf.Vec3f(1.0, 1.0, 1.0)])
    typeName = "Material"
    schema = UsdShade.Material
    requiredPropertyNames = set()

    def _assertFileColorSpace(self, fileAttr: Usd.Attribute, expectedToken: str):
        # MaterialAlgo.cpp authors the file input color space using UsdAttribute.SetColorSpace(...)
        if hasattr(fileAttr, "GetColorSpace"):
            self.assertEqual(fileAttr.GetColorSpace(), expectedToken)
        else:
            self.assertEqual(fileAttr.GetMetadata("colorSpace"), expectedToken)

    def assertValidPbrTexCoordNetwork(self, material: UsdShade.Material):
        texCoord = UsdShade.Shader(material.GetPrim().GetChild("MtlxPrimvar_st_float2"))
        self.assertTrue(texCoord)
        self.assertEqual(texCoord.GetShaderId(), "ND_geompropvalue_vector2")
        self.assertEqual(texCoord.GetInput("geomprop").GetAttr().Get(), UsdUtils.GetPrimaryUVSetName())
        return texCoord

    def assertValidPbrTiledImageCommon(
        self,
        material: UsdShade.Material,
        texShaderName: str,
        expectedShaderId: str,
        texture: Sdf.AssetPath,
        expectedFileColorSpace: str,
    ) -> UsdShade.Shader:
        texCoord = self.assertValidPbrTexCoordNetwork(material)

        texShader = UsdShade.Shader(material.GetPrim().GetChild(texShaderName))
        self.assertTrue(texShader)
        self.assertEqual(texShader.GetShaderId(), expectedShaderId)

        fileInput = texShader.GetInput("file")
        self.assertTrue(fileInput)
        # Make sure there is a material interface for the "file" inputs
        self.assertTrue(fileInput.HasConnectedSource())
        materialFileInput = fileInput.GetValueProducingAttributes()[0]
        self.assertEqual(materialFileInput.Get().path, texture)
        self._assertFileColorSpace(materialFileInput, expectedFileColorSpace)

        # texcoord is connected to TexCoord.out
        tcInput = texShader.GetInput("texcoord")
        self.assertTrue(tcInput.HasConnectedSource())
        self.assertEqual(tcInput.GetConnectedSource()[0].GetOutputs()[0].GetAttr(), texCoord.GetOutput("out").GetAttr())

        self.assertEqual(texShader.GetInput("uvtiling").GetAttr().Get(), Gf.Vec2f(1.0, 1.0))
        self.assertEqual(texShader.GetInput("uvoffset").GetAttr().Get(), Gf.Vec2f(0.0, 0.0))

        return texShader

    def testInvalidPbrMaterialForTextureFunctions(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))

        # invalid material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addColorTextureToPbrMaterial(UsdShade.Material(), texture)
        self.assertFalse(result)

        # no surface shader wired for mtlx
        badMaterial = UsdShade.Material.Define(materials.GetStage(), materials.GetPath().AppendChild("BadPbrMaterial"))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addColorTextureToPbrMaterial(badMaterial, texture)
        self.assertFalse(result)

        # surface output wired, but shader has no id / wrong id
        otherShader = UsdShade.Shader.Define(materials.GetStage(), badMaterial.GetPath().AppendChild("NoShaderId"))
        badMaterial.CreateSurfaceOutput("mtlx").ConnectToSource(otherShader.CreateOutput(UsdShade.Tokens.surface, Sdf.ValueTypeNames.Token))
        self.assertTrue(badMaterial.GetSurfaceOutput("mtlx").HasConnectedSource())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addColorTextureToPbrMaterial(badMaterial, texture)
        self.assertFalse(result)

        otherShader.SetShaderId("NotOpenPbr")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addColorTextureToPbrMaterial(badMaterial, texture)
        self.assertFalse(result)

    def testPbrMaterialShaders(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.0, 0.5, 1.0), opacity=0.2, roughness=0.3, metallic=0.4)
        self.assertTrue(material)

        assertLimitMetadata(
            self,
            material.GetInput("color"),
            {
                "uimin": "0, 0, 0",
                "uimax": "1, 1, 1",
            },
            {"hard": {"minimum": Gf.Vec3f(0.0, 0.0, 0.0), "maximum": Gf.Vec3f(1.0, 1.0, 1.0)}},
        )
        assertLimitMetadata(
            self,
            material.GetInput("opacity"),
            {"uimin": "0", "uimax": "1"},
            {"hard": {"minimum": 0.0, "maximum": 1.0}},
        )
        assertLimitMetadata(
            self,
            material.GetInput("roughness"),
            {"uimin": "0", "uimax": "1"},
            {"hard": {"minimum": 0.0, "maximum": 1.0}},
        )
        assertLimitMetadata(
            self,
            material.GetInput("metallic"),
            {"uimin": "0", "uimax": "1"},
            {"hard": {"minimum": 0.0, "maximum": 1.0}},
        )

        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertTrue(shader)
        self.assertEqual(shader.GetPrim().GetName(), "OpenPBR")
        self.assertEqual(shader.GetShaderId(), "ND_open_pbr_surface_surfaceshader")
        self.assertIsSurfaceShader(material, shader)
        self.assertMaterialXVersion(material)

        # base_color
        shaderInput = shader.GetInput("base_color")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), Gf.Vec3f(0.0, 0.5, 1.0), 1e-6))

        # geometry_opacity
        shaderInput = shader.GetInput("geometry_opacity")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.2)

        # specular_roughness
        shaderInput = shader.GetInput("specular_roughness")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.3)

        # base_metalness
        shaderInput = shader.GetInput("base_metalness")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.4)
        self.assertIsValidUsd(stage)

    def testPbrSdrMetadata(self):
        def normalizeMetadataValue(value):
            if isinstance(value, str):
                return tuple(float(component.strip()) for component in value.split(","))

            try:
                return tuple(float(component) for component in value)
            except TypeError:
                return (float(value),)

        def assertMetadataValueIsClose(actual, expected):
            actualValues = normalizeMetadataValue(actual)
            expectedValues = normalizeMetadataValue(expected)
            self.assertEqual(len(actualValues), len(expectedValues))
            for actualValue, expectedValue in zip(actualValues, expectedValues):
                self.assertAlmostEqual(actualValue, expectedValue)

        shaderNodeDef = Sdr.Registry().GetShaderNodeByIdentifier("ND_open_pbr_surface_surfaceshader")
        if self.isUsdOlderThan("0.25.08"):
            self.skipTest("Skipping until the MaterialX OpenPBR standard library is available to Sdr")

        self.assertTrue(shaderNodeDef, "Shader node definition not found")

        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        pbrMaterial = usdex.core.definePbrMaterial(materials, "SdrMetadataPbr", Gf.Vec3f(0.2, 0.4, 0.6))
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(pbrMaterial, Gf.Vec3f(1.0, 0.5, 0.25)))
        glassMaterial = usdex.core.defineGlassPbrMaterial(materials, "SdrMetadataGlass", Gf.Vec3f(0.9, 0.95, 1.0))

        elevatedInputs = [
            (pbrMaterial, "color", "base_color"),
            (pbrMaterial, "opacity", "geometry_opacity"),
            (pbrMaterial, "roughness", "specular_roughness"),
            (pbrMaterial, "metallic", "base_metalness"),
            (pbrMaterial, "emissiveColor", "emission_color"),
            (pbrMaterial, "emissiveLuminance", "emission_luminance"),
            (glassMaterial, "color", "transmission_color"),
            (glassMaterial, "ior", "specular_ior"),
            (glassMaterial, "roughness", "specular_roughness"),
        ]

        for material, interfaceInputName, openPbrInputName in elevatedInputs:
            inputProperty = shaderNodeDef.GetShaderInput(openPbrInputName)
            self.assertTrue(inputProperty)
            interfaceInput = material.GetInput(interfaceInputName)
            self.assertTrue(interfaceInput)

            hints = inputProperty.GetHints()
            limits = interfaceInput.GetAttr().GetMetadata("limits")

            self.assertFalse(interfaceInput.HasSdrMetadataByKey("default"))
            for key, expectedValue in hints.items():
                self.assertTrue(interfaceInput.HasSdrMetadataByKey(key), msg=f"Missing {key} on {interfaceInputName}")
                assertMetadataValueIsClose(interfaceInput.GetSdrMetadataByKey(key), expectedValue)
                if key == "uimin":
                    assertMetadataValueIsClose(limits["hard"]["minimum"], expectedValue)
                elif key == "uimax":
                    assertMetadataValueIsClose(limits["hard"]["maximum"], expectedValue)
                elif key == "uisoftmin":
                    assertMetadataValueIsClose(limits["soft"]["minimum"], expectedValue)
                elif key == "uisoftmax":
                    assertMetadataValueIsClose(limits["soft"]["maximum"], expectedValue)

        self.assertIsValidUsd(stage)

    def testPbrMaterialXNodeDefinitions(self):
        if self.isUsdOlderThan("0.25.08"):
            self.skipTest("Skipping until the MaterialX OpenPBR standard library is available to Sdr")

        def getSdfType(shaderProperty):
            typeIndicator = shaderProperty.GetTypeAsSdfType()
            if isinstance(typeIndicator, tuple):
                return typeIndicator[0]
            return typeIndicator.GetSdfType()

        def assertShaderMatchesNodeDefinition(shader):
            shaderId = shader.GetShaderId()
            nodeDefinition = Sdr.Registry().GetShaderNodeByIdentifier(shaderId)
            self.assertTrue(nodeDefinition, msg=f"Missing node definition for {shaderId}")

            for shaderInput in shader.GetInputs():
                inputDefinition = nodeDefinition.GetShaderInput(shaderInput.GetBaseName())
                self.assertTrue(inputDefinition, msg=f"Missing {shaderId} input {shaderInput.GetBaseName()}")
                self.assertEqual(shaderInput.GetTypeName(), getSdfType(inputDefinition))

            for shaderOutput in shader.GetOutputs():
                outputDefinition = nodeDefinition.GetShaderOutput(shaderOutput.GetBaseName())
                self.assertTrue(outputDefinition, msg=f"Missing {shaderId} output {shaderOutput.GetBaseName()}")
                self.assertEqual(shaderOutput.GetTypeName(), getSdfType(outputDefinition))

        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePbrMaterial(materials, "Compatibility", Gf.Vec3f(0.2, 0.4, 0.6))
        self.assertTrue(usdex.core.addColorTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Color", ext="png"))))
        self.assertTrue(usdex.core.addNormalTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Normal", ext="png"))))
        self.assertTrue(usdex.core.addOrmTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="ORM", ext="png"))))
        self.assertTrue(usdex.core.addOpacityTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Opacity", ext="png"))))
        self.assertTrue(usdex.core.addEmissiveTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Emissive", ext="png"))))
        glassMaterial = usdex.core.defineGlassPbrMaterial(materials, "GlassCompatibility", Gf.Vec3f(0.8, 0.9, 1.0))

        for testedMaterial in (material, glassMaterial):
            self.assertMaterialXVersion(testedMaterial)
            for prim in Usd.PrimRange(testedMaterial.GetPrim()):
                shader = UsdShade.Shader(prim)
                if shader and shader.GetShaderId().startswith("ND_"):
                    assertShaderMatchesNodeDefinition(shader)

        self.assertIsValidUsd(stage)

    def testDefinePbrMaterialInvalidInputs(self):
        # mirror testInvalidInputs() for Preview materials
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Opacity value -0.000001 is outside range")]):
            material = usdex.core.definePbrMaterial(materials, "BadOpacity", Gf.Vec3f(1, 0, 0), opacity=-0.000001)
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Opacity value 1.000001 is outside range")]):
            material = usdex.core.definePbrMaterial(materials, "BadOpacity", Gf.Vec3f(1, 0, 0), opacity=1.000001)
        self.assertFalse(material)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Roughness value -0.000001 is outside range")]):
            material = usdex.core.definePbrMaterial(materials, "BadRoughness", Gf.Vec3f(1, 0, 0), roughness=-0.000001)
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Roughness value 1.000001 is outside range")]):
            material = usdex.core.definePbrMaterial(materials, "BadRoughness", Gf.Vec3f(1, 0, 0), roughness=1.000001)
        self.assertFalse(material)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Metallic value -0.000001 is outside range")]):
            material = usdex.core.definePbrMaterial(materials, "BadMetallic", Gf.Vec3f(1, 0, 0), metallic=-0.000001)
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Metallic value 1.000001 is outside range")]):
            material = usdex.core.definePbrMaterial(materials, "BadMetallic", Gf.Vec3f(1, 0, 0), metallic=1.000001)
        self.assertFalse(material)

        material = usdex.core.definePbrMaterial(materials, "LowestValidInputs", Gf.Vec3f(0, 0, 0), opacity=0, roughness=0, metallic=0)
        self.assertTrue(material)
        self.assertIsValidUsd(stage)

        material = usdex.core.definePbrMaterial(materials, "HighestValidInputs", Gf.Vec3f(1, 1, 1), opacity=1, roughness=1, metallic=1)
        self.assertTrue(material)
        self.assertIsValidUsd(stage)

    def testAddColorTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        textures = [Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png")), Sdf.AssetPath(self.tmpFile(name="BaseColor2", ext="png"))]
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.1, 0.2, 0.3))

        for texture in textures:
            result = usdex.core.addColorTextureToPbrMaterial(material, texture)
            self.assertTrue(result)

            # Verify the Mtlx texture network
            texShader = self.assertValidPbrTiledImageCommon(
                material,
                texShaderName="MtlxBaseColorTexture",
                expectedShaderId="ND_tiledimage_color3",
                texture=texture,
                expectedFileColorSpace="srgb_texture",
            )
            self.assertEqual(texShader.GetInput("default").GetAttr().Get(), Gf.Vec3f(0.1, 0.2, 0.3))

            surface = usdex.core.computeEffectiveMtlxSurfaceShader(material)
            self.assertTrue(surface.GetInput("base_color").HasConnectedSource())
            self.assertEqual(surface.GetInput("base_color").GetConnectedSource()[0].GetOutputs()[0].GetAttr(), texShader.GetOutput("out").GetAttr())
            self.assertFalse(surface.GetInput("base_color").GetAttr().HasAuthoredValue())

            # Verify the UPS texture network was also created
            self.assertValidPreviewMaterialTextureNetwork(
                material,
                texture,
                textureReaderName="ColorTexture",
                colorSpace=usdex.core.ColorSpace.eAuto,
                fallbackColor=Gf.Vec3f(0.1, 0.2, 0.3),
                connectionInfo=[("diffuseColor", Sdf.ValueTypeNames.Color3f, "rgb")],
            )
            self.assertIsValidUsd(stage)

    def testAddRoughnessTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        textures = [Sdf.AssetPath(self.tmpFile(name="roughness", ext="png")), Sdf.AssetPath(self.tmpFile(name="roughness2", ext="png"))]
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8), roughness=0.1)

        for texture in textures:
            result = usdex.core.addRoughnessTextureToPbrMaterial(material, texture)
            self.assertTrue(result)

            texShader = self.assertValidPbrTiledImageCommon(
                material,
                texShaderName="MtlxRoughnessTexture",
                expectedShaderId="ND_tiledimage_float",
                texture=texture,
                expectedFileColorSpace=Gf.ColorSpaceNames.Data,
            )
            self.assertAlmostEqual(texShader.GetInput("default").GetAttr().Get(), 0.1)
            surface = usdex.core.computeEffectiveMtlxSurfaceShader(material)
            self.assertTrue(surface.GetInput("specular_roughness").HasConnectedSource())
            self.assertFalse(surface.GetInput("specular_roughness").GetAttr().HasAuthoredValue())

            # Verify the UPS texture network was also created
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
        textures = [Sdf.AssetPath(self.tmpFile(name="metallic", ext="png")), Sdf.AssetPath(self.tmpFile(name="metallic2", ext="png"))]
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8), metallic=0.9)

        for texture in textures:
            result = usdex.core.addMetallicTextureToPbrMaterial(material, texture)
            self.assertTrue(result)

            texShader = self.assertValidPbrTiledImageCommon(
                material,
                texShaderName="MtlxMetallicTexture",
                expectedShaderId="ND_tiledimage_float",
                texture=texture,
                expectedFileColorSpace=Gf.ColorSpaceNames.Data,
            )
            self.assertAlmostEqual(texShader.GetInput("default").GetAttr().Get(), 0.9)
            surface = usdex.core.computeEffectiveMtlxSurfaceShader(material)
            self.assertTrue(surface.GetInput("base_metalness").HasConnectedSource())
            self.assertFalse(surface.GetInput("base_metalness").GetAttr().HasAuthoredValue())

            # Verify the UPS texture network was also created
            self.assertValidPreviewMaterialTextureNetwork(
                material,
                texture,
                textureReaderName="MetallicTexture",
                colorSpace=usdex.core.ColorSpace.eRaw,
                fallbackColor=Gf.Vec3f(0.9, 0.0, 0.0),
                connectionInfo=[("metallic", Sdf.ValueTypeNames.Float, "r")],
            )
            self.assertIsValidUsd(stage)

    def testAddOpacityTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        textures = [Sdf.AssetPath(self.tmpFile(name="opacity", ext="png")), Sdf.AssetPath(self.tmpFile(name="opacity2", ext="png"))]
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8), opacity=0.25)

        for texture in textures:
            result = usdex.core.addOpacityTextureToPbrMaterial(material, texture)
            self.assertTrue(result)

            texShader = self.assertValidPbrTiledImageCommon(
                material,
                texShaderName="MtlxOpacityTexture",
                expectedShaderId="ND_tiledimage_float",
                texture=texture,
                expectedFileColorSpace=Gf.ColorSpaceNames.Data,
            )
            self.assertAlmostEqual(texShader.GetInput("default").GetAttr().Get(), 0.25)
            surface = usdex.core.computeEffectiveMtlxSurfaceShader(material)
            self.assertTrue(surface.GetInput("geometry_opacity").HasConnectedSource())
            self.assertFalse(surface.GetInput("geometry_opacity").GetAttr().HasAuthoredValue())

            # Verify the UPS texture network was also created
            self.assertValidPreviewMaterialTextureNetwork(
                material,
                texture,
                textureReaderName="OpacityTexture",
                colorSpace=usdex.core.ColorSpace.eRaw,
                fallbackColor=Gf.Vec3f(0.25, 0.0, 0.0),
                connectionInfo=[("opacity", Sdf.ValueTypeNames.Float, "r")],
            )
            self.assertIsValidUsd(stage)

    def testAddNormalTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        textures = [Sdf.AssetPath(self.tmpFile(name="N", ext="png")), Sdf.AssetPath(self.tmpFile(name="N2", ext="png"))]
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        for texture in textures:
            result = usdex.core.addNormalTextureToPbrMaterial(material, texture)
            self.assertTrue(result)

            texShader = self.assertValidPbrTiledImageCommon(
                material,
                texShaderName="MtlxNormalTexture",
                expectedShaderId="ND_tiledimage_vector3",
                texture=texture,
                expectedFileColorSpace=Gf.ColorSpaceNames.Data,
            )
            self.assertEqual(texShader.GetInput("default").GetAttr().Get(), Gf.Vec3f(0.5, 0.5, 1.0))

            normalMap = UsdShade.Shader(material.GetPrim().GetChild("MtlxNormalMap"))
            self.assertTrue(normalMap)
            self.assertEqual(normalMap.GetShaderId(), "ND_normalmap_float")
            self.assertTrue(normalMap.GetInput("in").HasConnectedSource())
            self.assertEqual(normalMap.GetInput("in").GetConnectedSource()[0].GetOutputs()[0].GetAttr(), texShader.GetOutput("out").GetAttr())

            surface = usdex.core.computeEffectiveMtlxSurfaceShader(material)
            self.assertTrue(surface.GetInput("geometry_normal").HasConnectedSource())
            self.assertEqual(
                surface.GetInput("geometry_normal").GetConnectedSource()[0].GetOutputs()[0].GetAttr(),
                normalMap.GetOutput("out").GetAttr(),
            )

            # Verify the UPS texture network was also created
            self.assertValidPreviewMaterialTextureNetwork(
                material,
                texture,
                textureReaderName="NormalTexture",
                colorSpace=usdex.core.ColorSpace.eRaw,
                fallbackColor=Gf.Vec3f(0.0, 0.0, 1.0),
                connectionInfo=[("normal", Sdf.ValueTypeNames.Normal3f, "rgb")],
            )
            self.assertIsValidUsd(stage)

    def testAddOrmTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        textures = [Sdf.AssetPath(self.tmpFile(name="ORM", ext="png")), Sdf.AssetPath(self.tmpFile(name="ORM2", ext="png"))]
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8), roughness=0.25, metallic=0.9)

        for texture in textures:
            result = usdex.core.addOrmTextureToPbrMaterial(material, texture)
            self.assertTrue(result)

            texShader = self.assertValidPbrTiledImageCommon(
                material,
                texShaderName="MtlxORMTexture",
                expectedShaderId="ND_tiledimage_vector3",
                texture=texture,
                expectedFileColorSpace=Gf.ColorSpaceNames.Data,
            )
            self.assertEqual(texShader.GetInput("default").GetAttr().Get(), Gf.Vec3f(0.0, 0.25, 0.9))

            sep = UsdShade.Shader(material.GetPrim().GetChild("MtlxSeparateORM"))
            self.assertTrue(sep)
            self.assertEqual(sep.GetShaderId(), "ND_separate3_vector3")
            self.assertTrue(sep.GetInput("in").HasConnectedSource())
            self.assertEqual(sep.GetInput("in").GetConnectedSource()[0].GetOutputs()[0].GetAttr(), texShader.GetOutput("out").GetAttr())

            surface = usdex.core.computeEffectiveMtlxSurfaceShader(material)
            self.assertTrue(surface.GetInput("specular_roughness").HasConnectedSource())
            self.assertEqual(
                surface.GetInput("specular_roughness").GetConnectedSource()[0].GetOutputs()[1].GetAttr(), sep.GetOutput("outy").GetAttr()
            )
            self.assertTrue(surface.GetInput("base_metalness").HasConnectedSource())
            self.assertEqual(surface.GetInput("base_metalness").GetConnectedSource()[0].GetOutputs()[2].GetAttr(), sep.GetOutput("outz").GetAttr())

            # Verify the UPS texture network was also created
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

    def testAddEmissiveColor(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        color = Gf.Vec3f(1.0, 1.0, 0.0)
        luminance = 3000.0
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.2, 0.2, 0.2))
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(material, color, luminance))

        # Verify the material interface inputs were created and have the supplied values
        emissiveColorInput = material.GetInput("emissiveColor")
        self.assertTrue(emissiveColorInput)
        self.assertEqual(emissiveColorInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(Gf.IsClose(emissiveColorInput.Get(), color, 1e-6))
        assertLimitMetadata(
            self,
            emissiveColorInput,
            {
                "uimin": "0, 0, 0",
                "uimax": "1, 1, 1",
            },
            {"hard": {"minimum": Gf.Vec3f(0.0, 0.0, 0.0), "maximum": Gf.Vec3f(1.0, 1.0, 1.0)}},
        )

        emissiveLuminanceInput = material.GetInput("emissiveLuminance")
        self.assertTrue(emissiveLuminanceInput)
        self.assertEqual(emissiveLuminanceInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(emissiveLuminanceInput.Get(), luminance)
        assertLimitMetadata(
            self,
            emissiveLuminanceInput,
            {"uimin": "0", "uisoftmax": "1000"},
            {"hard": {"minimum": 0.0}, "soft": {"maximum": 1000.0}},
        )

        # The OpenPBR shader's emission_color and emission_luminance are connected to the material interface
        mtlxShader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        emissionColor = mtlxShader.GetInput("emission_color")
        self.assertTrue(emissionColor)
        self.assertEqual(emissionColor.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(emissionColor.HasConnectedSource())
        self.assertEqual(emissionColor.GetValueProducingAttributes()[0], emissiveColorInput.GetAttr())
        self.assertFalse(emissionColor.GetAttr().HasAuthoredValue())
        self.assertTrue(Gf.IsClose(emissionColor.GetValueProducingAttributes()[0].Get(), color, 1e-6))

        emissionLuminance = mtlxShader.GetInput("emission_luminance")
        self.assertTrue(emissionLuminance)
        self.assertEqual(emissionLuminance.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertTrue(emissionLuminance.HasConnectedSource())
        self.assertEqual(emissionLuminance.GetValueProducingAttributes()[0], emissiveLuminanceInput.GetAttr())
        self.assertFalse(emissionLuminance.GetAttr().HasAuthoredValue())
        self.assertAlmostEqual(emissionLuminance.GetValueProducingAttributes()[0].Get(), luminance)

        # The UPS shader's emissiveColor is connected to the material interface (no authored direct value)
        previewShader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        previewEmissive = previewShader.GetInput("emissiveColor")
        self.assertTrue(previewEmissive)
        self.assertEqual(previewEmissive.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(previewEmissive.HasConnectedSource())
        self.assertEqual(previewEmissive.GetValueProducingAttributes()[0], emissiveColorInput.GetAttr())
        self.assertFalse(previewEmissive.GetAttr().HasAuthoredValue())
        self.assertTrue(Gf.IsClose(previewEmissive.GetValueProducingAttributes()[0].Get(), color, 1e-6))

        # Calling again with new values updates the material interface (and therefore both shaders)
        newColor = Gf.Vec3f(0.5, 0.0, 0.5)
        newLuminance = 100.0
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(material, newColor, newLuminance))
        self.assertTrue(Gf.IsClose(material.GetInput("emissiveColor").Get(), newColor, 1e-6))
        self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), newLuminance)

        self.assertIsValidUsd(stage)

    def testAddEmissiveColorDefaultLuminance(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # Omitting the luminance argument should fall back to the documented 1000.0 cd/m^2 default
        color = Gf.Vec3f(1.0, 1.0, 0.0)
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.2, 0.2, 0.2))
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(material, color))
        self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), 1000.0)
        self.assertTrue(Gf.IsClose(material.GetInput("emissiveColor").Get(), color, 1e-6))

        self.assertIsValidUsd(stage)

    def testInvalidAddEmissiveColor(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.2, 0.2, 0.2))

        # Invalid emissive color (negative component)
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Color value .* is invalid: each component must be at least 0 \(no upper bound\).")]
        ):
            result = usdex.core.addEmissiveColorToPbrMaterial(material, Gf.Vec3f(-1.0, 1.0, 0.0), 100.0)
        self.assertFalse(result)

        # Invalid emissive color (component above the hard maximum)
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Color value .* is invalid: each component must be at most 1.0.")]
        ):
            result = usdex.core.addEmissiveColorToPbrMaterial(material, Gf.Vec3f(1.1, 1.0, 0.0), 100.0)
        self.assertFalse(result)

        # Invalid luminance (negative)
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Luminance value .* is invalid: must be at least 0.0 \(no upper bound\).")]
        ):
            result = usdex.core.addEmissiveColorToPbrMaterial(material, Gf.Vec3f(1.0, 1.0, 0.0), -1.0)
        self.assertFalse(result)

        # Invalid material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addEmissiveColorToPbrMaterial(UsdShade.Material(), Gf.Vec3f(1.0, 1.0, 0.0), 100.0)
        self.assertFalse(result)

        # Material that is not a definePbrMaterial-style material (no MaterialX OpenPBR surface)
        previewMaterial = usdex.core.definePreviewMaterial(materials, "PreviewOnly", Gf.Vec3f(0.2, 0.2, 0.2))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addEmissiveColorToPbrMaterial(previewMaterial, Gf.Vec3f(1.0, 1.0, 0.0), 100.0)
        self.assertFalse(result)

        # Material with no Preview surface
        previewSurfacePath = usdex.core.computeEffectivePreviewSurfaceShader(material).GetPrim().GetPath()
        stage.RemovePrim(previewSurfacePath)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addEmissiveColorToPbrMaterial(material, Gf.Vec3f(1.0, 1.0, 0.0), 100.0)
        self.assertFalse(result)

        self.assertIsValidUsd(stage)

    def testAddEmissiveTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        textures = [Sdf.AssetPath(self.tmpFile(name="emissive", ext="png")), Sdf.AssetPath(self.tmpFile(name="emissive2", ext="png"))]

        # Without a prior emissive color, the OpenPBR `emission_color` is zero (default), so the Mtlx and UPS fallbacks are zero.
        # The luminance defaults to 1000.0 cd/m^2, creating a new `emissiveLuminance` material interface input.
        material = usdex.core.definePbrMaterial(materials, "NoColor", Gf.Vec3f(0.8, 0.8, 0.8))
        result = usdex.core.addEmissiveTextureToPbrMaterial(material, textures[0])
        self.assertTrue(result)

        # The default luminance was authored on a new material interface input
        self.assertTrue(material.GetInput("emissiveLuminance"))
        self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), 1000.0)
        assertLimitMetadata(
            self,
            material.GetInput("emissiveLuminance"),
            {"uimin": "0", "uisoftmax": "1000"},
            {"hard": {"minimum": 0.0}, "soft": {"maximum": 1000.0}},
        )

        texShader = self.assertValidPbrTiledImageCommon(
            material,
            texShaderName="MtlxEmissiveTexture",
            expectedShaderId="ND_tiledimage_color3",
            texture=textures[0],
            expectedFileColorSpace="srgb_texture",
        )
        self.assertEqual(texShader.GetInput("default").GetAttr().Get(), Gf.Vec3f(0.0, 0.0, 0.0))
        surface = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertTrue(surface.GetInput("emission_color").HasConnectedSource())
        self.assertEqual(surface.GetInput("emission_color").GetConnectedSource()[0].GetOutputs()[0].GetAttr(), texShader.GetOutput("out").GetAttr())
        self.assertFalse(surface.GetInput("emission_color").GetAttr().HasAuthoredValue())

        # OpenPBR emission_luminance is connected to the material interface emissiveLuminance
        emissionLuminance = surface.GetInput("emission_luminance")
        self.assertTrue(emissionLuminance.HasConnectedSource())
        self.assertEqual(emissionLuminance.GetValueProducingAttributes()[0], material.GetInput("emissiveLuminance").GetAttr())

        self.assertValidPreviewMaterialTextureNetwork(
            material,
            textures[0],
            textureReaderName="EmissiveTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(0.0, 0.0, 0.0),
            connectionInfo=[("emissiveColor", Sdf.ValueTypeNames.Color3f, "rgb")],
        )

        # The previously authored emissive color value is used as the texture fallback, and the `emissiveColor` interface input is removed
        # in favor of the `EmissiveTexture` interface input. An explicit luminance argument overrides any value previously set by
        # `addEmissiveColorToPbrMaterial`.
        material = usdex.core.definePbrMaterial(materials, "InitialValues", Gf.Vec3f(0.8, 0.8, 0.8))
        emissiveColor = Gf.Vec3f(1.0, 1.0, 0.2)
        emissiveLuminance = 500.0
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(material, emissiveColor, emissiveLuminance))
        self.assertTrue(material.GetInput("emissiveColor"))
        self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), emissiveLuminance)

        textureLuminance = 250.0
        for texture in textures:
            result = usdex.core.addEmissiveTextureToPbrMaterial(material, texture, textureLuminance)
            self.assertTrue(result)

            # The scalar emissiveColor interface input is removed (replaced by EmissiveTexture); luminance is overwritten with textureLuminance
            self.assertFalse(material.GetInput("emissiveColor"))
            self.assertTrue(material.GetInput("emissiveLuminance"))
            self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), textureLuminance)

            texShader = self.assertValidPbrTiledImageCommon(
                material,
                texShaderName="MtlxEmissiveTexture",
                expectedShaderId="ND_tiledimage_color3",
                texture=texture,
                expectedFileColorSpace="srgb_texture",
            )
            # The fallback default was set to the previously authored emissive color on the first call and persists across subsequent calls.
            self.assertTrue(Gf.IsClose(texShader.GetInput("default").GetAttr().Get(), emissiveColor, 1e-6))

            surface = usdex.core.computeEffectiveMtlxSurfaceShader(material)
            self.assertTrue(surface.GetInput("emission_color").HasConnectedSource())
            self.assertEqual(
                surface.GetInput("emission_color").GetConnectedSource()[0].GetOutputs()[0].GetAttr(), texShader.GetOutput("out").GetAttr()
            )
            self.assertFalse(surface.GetInput("emission_color").GetAttr().HasAuthoredValue())

            # The OpenPBR `emission_luminance` remains connected to the material interface
            emissionLuminance = surface.GetInput("emission_luminance")
            self.assertTrue(emissionLuminance.HasConnectedSource())
            self.assertEqual(emissionLuminance.GetValueProducingAttributes()[0], material.GetInput("emissiveLuminance").GetAttr())

            # The UPS fallback was set to the previously authored emissive color on the first call and persists across subsequent calls.
            self.assertValidPreviewMaterialTextureNetwork(
                material,
                texture,
                textureReaderName="EmissiveTexture",
                colorSpace=usdex.core.ColorSpace.eAuto,
                fallbackColor=emissiveColor,
                connectionInfo=[("emissiveColor", Sdf.ValueTypeNames.Color3f, "rgb")],
            )

        self.assertIsValidUsd(stage)

    def testInvalidAddEmissiveTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        texture = Sdf.AssetPath(self.tmpFile(name="emissive", ext="png"))

        # Invalid material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addEmissiveTextureToPbrMaterial(UsdShade.Material(), texture)
        self.assertFalse(result)

        # Material that is not a definePbrMaterial-style material (no MaterialX OpenPBR surface)
        previewMaterial = usdex.core.definePreviewMaterial(materials, "PreviewOnly", Gf.Vec3f(0.2, 0.2, 0.2))
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addEmissiveTextureToPbrMaterial(previewMaterial, texture)
        self.assertFalse(result)

        # Invalid luminance (negative)
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.2, 0.2, 0.2))
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Luminance value .* is invalid: must be at least 0.0 \(no upper bound\).")]
        ):
            result = usdex.core.addEmissiveTextureToPbrMaterial(material, texture, luminance=-1.0)
        self.assertFalse(result)

        self.assertIsValidUsd(stage)

    def testTexturesShareTexCoordReader(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        baseColorTex = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))
        normalTex = Sdf.AssetPath(self.tmpFile(name="N", ext="png"))

        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.2, 0.3, 0.4))
        self.assertTrue(usdex.core.addColorTextureToPbrMaterial(material, baseColorTex))
        self.assertTrue(usdex.core.addNormalTextureToPbrMaterial(material, normalTex))

        def findTexCoord(stage):
            tex = []
            for prim in stage.Traverse():
                shader = UsdShade.Shader(prim)
                if shader and shader.GetShaderId() == "ND_geompropvalue_vector2":
                    tex.append(shader)
            return tex

        texReaders = findTexCoord(stage)
        self.assertEqual(len(texReaders), 1)
        self.assertEqual(texReaders[0].GetPrim(), material.GetPrim().GetChild("MtlxPrimvar_st_float2"))

    def testDefinePbrMaterialPrimOverload(self):
        # mirror testDefinePreviewMaterialPrimOverload()
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/World/PbrMaterial", "Material")

        color = Gf.Vec3f(0.5, 0.7, 0.9)
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Material.*to.*Material.*Expected original type to be "" or .*Scope.*')],
        ):
            material = usdex.core.definePbrMaterial(prim, color)

        self.assertTrue(material)
        self.assertEqual(material.GetPrim().GetPath(), prim.GetPath())
        self.assertEqual(material.GetPrim().GetTypeName(), "Material")

        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertTrue(shader)
        self.assertEqual(shader.GetShaderId(), "ND_open_pbr_surface_surfaceshader")
        shaderInput = shader.GetInput("base_color")
        self.assertEqual(shaderInput.GetValueProducingAttributes()[0].Get(), color)

    def testDefinePbrMaterialPrimOverloadWithOptionalParams(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/World/PbrMaterialWithParams", "Material")

        color = Gf.Vec3f(0.5, 0.7, 0.9)
        opacity = 0.8
        roughness = 0.3
        metallic = 0.5

        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Material.*to.*Material.*Expected original type to be "" or .*Scope.*')],
        ):
            material = usdex.core.definePbrMaterial(prim, color, opacity=opacity, roughness=roughness, metallic=metallic)

        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        shaderInput = shader.GetInput("base_color")
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), color, 1e-6))
        shaderInput = shader.GetInput("geometry_opacity")
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), opacity, 1e-6))
        shaderInput = shader.GetInput("specular_roughness")
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), roughness, 1e-6))
        shaderInput = shader.GetInput("base_metalness")
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), metallic, 1e-6))

    def testDefinePbrMaterialPrimOverloadMinimalParams(self):
        stage = Usd.Stage.CreateInMemory()
        prim = stage.DefinePrim("/World/PbrMaterialMinimal", "Material")

        color = Gf.Vec3f(1.0, 0.5, 0.2)
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Material.*to.*Material.*Expected original type to be "" or .*Scope.*')],
        ):
            material = usdex.core.definePbrMaterial(prim, color)

        shader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        shaderInput = shader.GetInput("base_color")
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), color, 1e-6))
        shaderInput = shader.GetInput("geometry_opacity")
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), 1.0, 1e-6))
        shaderInput = shader.GetInput("specular_roughness")
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), 0.3, 1e-6))
        shaderInput = shader.GetInput("base_metalness")
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), 0.0, 1e-6))

    def testDefinePbrMaterialPrimOverloadInvalidPrim(self):
        prim = Usd.Prim()
        self.assertFalse(prim.IsValid())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            material = usdex.core.definePbrMaterial(prim, Gf.Vec3f(1.0, 1.0, 1.0))
        self.assertFalse(material)

    def testDefinePbrMaterialPrimOverloadTypeGuards(self):
        stage = Usd.Stage.CreateInMemory()
        color = Gf.Vec3f(0.5, 0.7, 0.9)

        meshPrim = stage.DefinePrim("/World/MeshPrimPbr", "Mesh")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Mesh.*to.*Material.*Expected original type to be "" or .*Scope.*')],
        ):
            material = usdex.core.definePbrMaterial(meshPrim, color)
        self.assertTrue(material)

        scopePrim = stage.DefinePrim("/World/ScopePrimPbr", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            material = usdex.core.definePbrMaterial(scopePrim, color)
        self.assertTrue(material)

        xformPrim = stage.DefinePrim("/World/XformPrimPbr", "Xform")
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Cannot redefine.*from.*Xform.*to.*Material.*because Material is not Xformable")]
        ):
            material = usdex.core.definePbrMaterial(xformPrim, color)
        self.assertFalse(material)

    def testMaterialInterface(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.5, 0.7, 0.9))
        self.assertTrue(material)

        # Verify the material interface (names match UPS / RTX conventions)
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["color", "metallic", "opacity", "roughness"],
        )

        usdex.core.addColorTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png")))
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["ColorTexture", "metallic", "opacity", "roughness"],
        )

        usdex.core.addRoughnessTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Roughness", ext="png")))
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["ColorTexture", "RoughnessTexture", "metallic", "opacity"],
        )

        usdex.core.addNormalTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Normal", ext="png")))
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["ColorTexture", "NormalTexture", "RoughnessTexture", "metallic", "opacity"],
        )

        usdex.core.addOpacityTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Opacity", ext="png")))
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["ColorTexture", "NormalTexture", "OpacityTexture", "RoughnessTexture", "metallic"],
        )

        usdex.core.addMetallicTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Metallic", ext="png")))
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["ColorTexture", "MetallicTexture", "NormalTexture", "OpacityTexture", "RoughnessTexture"],
        )

        # Adding an emissive color creates two new material interface inputs
        usdex.core.addEmissiveColorToPbrMaterial(material, Gf.Vec3f(1.0, 0.5, 0.0), 100.0)
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["ColorTexture", "MetallicTexture", "NormalTexture", "OpacityTexture", "RoughnessTexture", "emissiveColor", "emissiveLuminance"],
        )

        # Adding an emissive texture replaces the scalar emissiveColor with EmissiveTexture (luminance is preserved)
        usdex.core.addEmissiveTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="Emissive", ext="png")))
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["ColorTexture", "EmissiveTexture", "MetallicTexture", "NormalTexture", "OpacityTexture", "RoughnessTexture", "emissiveLuminance"],
        )

        # Try with a new material the ORM texture
        material = usdex.core.definePbrMaterial(materials, "TestORM", Gf.Vec3f(0.5, 0.7, 0.9))
        self.assertTrue(material)

        # Verify the material interface
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["color", "metallic", "opacity", "roughness"],
        )

        usdex.core.addOrmTextureToPbrMaterial(material, Sdf.AssetPath(self.tmpFile(name="ORM", ext="png")))
        self.assertEqual(
            sorted([x.GetBaseName() for x in material.GetInterfaceInputs()]),
            ["ORMTexture", "color", "opacity"],
        )
        self.assertIsValidUsd(stage)

    def testRemoveMaterialInterface(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.5, 0.7, 0.9))
        self.assertTrue(material)

        class TextureInfo:
            def __init__(self, texture, func, shaderName, shaderId, colorSpaceName):
                self.texture = texture
                self.func = func
                self.shaderName = shaderName
                self.shaderId = shaderId
                self.colorSpaceName = colorSpaceName

            def add(self, material):
                return self.func(material, self.texture)

        textureInfos = [
            TextureInfo(
                Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png")),
                usdex.core.addColorTextureToPbrMaterial,
                "MtlxBaseColorTexture",
                "ND_tiledimage_color3",
                "srgb_texture",
            ),
            TextureInfo(
                Sdf.AssetPath(self.tmpFile(name="Normal", ext="png")),
                usdex.core.addNormalTextureToPbrMaterial,
                "MtlxNormalTexture",
                "ND_tiledimage_vector3",
                Gf.ColorSpaceNames.Data,
            ),
            TextureInfo(
                Sdf.AssetPath(self.tmpFile(name="Metallic", ext="png")),
                usdex.core.addMetallicTextureToPbrMaterial,
                "MtlxMetallicTexture",
                "ND_tiledimage_float",
                Gf.ColorSpaceNames.Data,
            ),
            TextureInfo(
                Sdf.AssetPath(self.tmpFile(name="Opacity", ext="png")),
                usdex.core.addOpacityTextureToPbrMaterial,
                "MtlxOpacityTexture",
                "ND_tiledimage_float",
                Gf.ColorSpaceNames.Data,
            ),
            TextureInfo(
                Sdf.AssetPath(self.tmpFile(name="Roughness", ext="png")),
                usdex.core.addRoughnessTextureToPbrMaterial,
                "MtlxRoughnessTexture",
                "ND_tiledimage_float",
                Gf.ColorSpaceNames.Data,
            ),
            TextureInfo(
                Sdf.AssetPath(self.tmpFile(name="Emissive", ext="png")),
                usdex.core.addEmissiveTextureToPbrMaterial,
                "MtlxEmissiveTexture",
                "ND_tiledimage_color3",
                "srgb_texture",
            ),
        ]
        for textureInfo in textureInfos:
            result = textureInfo.add(material)
            self.assertTrue(result)

        result = usdex.core.removeMaterialInterface(material)
        self.assertTrue(result)
        self.assertEqual(material.GetInterfaceInputs(), [])

        # verify that every mtlx input has been disconnected from the material inputs and has the correct value
        for textureInfo in textureInfos:
            texShader = UsdShade.Shader(material.GetPrim().GetChild(textureInfo.shaderName))
            self.assertTrue(texShader)
            self.assertEqual(texShader.GetShaderId(), textureInfo.shaderId)

            fileInput = texShader.GetInput("file")
            self.assertTrue(fileInput)
            self.assertTrue(fileInput.GetAttr().HasAuthoredValue())
            self.assertFalse(fileInput.HasConnectedSource())
            self.assertEqual(fileInput.Get().path, textureInfo.texture)
            self._assertFileColorSpace(fileInput.GetAttr(), textureInfo.colorSpaceName)

        self.assertIsValidUsd(stage)

    def assertValidPbrMaterialPrimvarNetwork(
        self,
        material: UsdShade.Material,
        primvarInfo: List[Tuple[str, str, Any]],  # inputName, primvarName, fallbackValue
    ):
        surfaceShader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertTrue(surfaceShader)
        self.assertEqual(surfaceShader.GetPrim().GetName(), "OpenPBR")
        self.assertEqual(surfaceShader.GetShaderId(), "ND_open_pbr_surface_surfaceshader")

        mtlxTypeMappings = {
            Sdf.ValueTypeNames.Float: "float",
            Sdf.ValueTypeNames.Color3f: "color3",
            Sdf.ValueTypeNames.Float3: "vector3",
        }

        for inputName, primvarName, fallbackValue in primvarInfo:
            input = surfaceShader.GetInput(inputName)
            outputTypeName = input.GetTypeName()

            mtlxTypeId = mtlxTypeMappings.get(
                outputTypeName,
                outputTypeName.GetAsToken().GetString() if hasattr(outputTypeName, "GetAsToken") else str(outputTypeName),
            )

            validPrimvarName = primvarName.replace(":", "_")
            primvarReaderName = usdex.core.getValidPrimName(f"MtlxPrimvar_{validPrimvarName}_{outputTypeName}")
            primvarReader = UsdShade.Shader(material.GetPrim().GetChild(primvarReaderName))
            self.assertTrue(primvarReader, msg=f"Expected primvar reader {primvarReaderName} not found")
            self.assertEqual(primvarReader.GetShaderId(), f"ND_geompropvalue_{mtlxTypeId}")
            self.assertEqual(primvarReader.GetInput("geomprop").GetAttr().Get(), primvarName)

            self.assertTrue(input.HasConnectedSource())
            self.assertEqual(len(input.GetValueProducingAttributes()), 1)
            self.assertEqual(input.GetValueProducingAttributes()[0], primvarReader.GetOutput("out").GetAttr())
            self.assertFalse(input.GetAttr().HasAuthoredValue())

    def testAddPrimvarShaderToInvalidMaterial(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addPrimvarShaderToPbrMaterial(UsdShade.Material(), "base_color", "perInstanceColor")
        self.assertFalse(result)

        material = usdex.core.createMaterial(materials, "NonPbrMaterial")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial")]):
            result = usdex.core.addPrimvarShaderToPbrMaterial(material, "base_color", "perInstanceColor")
        self.assertFalse(result)
        self.assertIsValidUsd(stage)

    def testAddPrimvarShader(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        result = usdex.core.addPrimvarShaderToPbrMaterial(material, "base_color", "perInstanceColor")
        self.assertTrue(result)
        result = usdex.core.addPrimvarShaderToPbrMaterial(material, "specular_roughness", "perInstanceRoughness")
        self.assertTrue(result)

        self.assertValidPbrMaterialPrimvarNetwork(
            material,
            [
                ("base_color", "perInstanceColor", None),
                ("specular_roughness", "perInstanceRoughness", None),
            ],
        )
        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderInvalidInputs(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot add primvar.*on surface shader.*")]):
            result = usdex.core.addPrimvarShaderToPbrMaterial(material, "invalidInput", "perInstanceColor")
            self.assertFalse(result)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot add primvar.*there is no input with that name.*")]):
            result = usdex.core.addPrimvarShaderToPbrMaterial(material, "", "perInstanceColor")
            self.assertFalse(result)

        self.assertIsValidUsd(stage)

    def testAddPrimvarShaderWithColorTexture(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePbrMaterial(materials, "Test", Gf.Vec3f(0.8, 0.8, 0.8))

        result = usdex.core.addPrimvarShaderToPbrMaterial(material, "base_color", "perInstanceColor")
        self.assertTrue(result)
        result = usdex.core.addPrimvarShaderToPbrMaterial(material, "specular_roughness", "perInstanceRoughness")
        self.assertTrue(result)

        self.assertValidPbrMaterialPrimvarNetwork(
            material,
            [
                ("base_color", "perInstanceColor", None),
                ("specular_roughness", "perInstanceRoughness", None),
            ],
        )

        texture = Sdf.AssetPath(self.tmpFile(name="BaseColor", ext="png"))
        result = usdex.core.addColorTextureToPbrMaterial(material, texture)
        self.assertTrue(result)

        # Verify the Mtlx texture network
        texShader = self.assertValidPbrTiledImageCommon(
            material,
            texShaderName="MtlxBaseColorTexture",
            expectedShaderId="ND_tiledimage_color3",
            texture=texture,
            expectedFileColorSpace="srgb_texture",
        )

        # The original default value is lost with primvar connections, so it should be zeroed out
        self.assertEqual(texShader.GetInput("default").GetAttr().Get(), Gf.Vec3f(0.0, 0.0, 0.0))

        # The texture replaced the primvar connection on base_color;
        # specular_roughness primvar should still be intact
        self.assertValidPbrMaterialPrimvarNetwork(
            material,
            [("specular_roughness", "perInstanceRoughness", None)],
        )

        # Re-adding the primvar to base_color should overwrite the texture connection
        result = usdex.core.addPrimvarShaderToPbrMaterial(material, "base_color", "perInstanceColor")
        self.assertTrue(result)
        self.assertValidPbrMaterialPrimvarNetwork(
            material,
            [
                ("base_color", "perInstanceColor", None),
                ("specular_roughness", "perInstanceRoughness", None),
            ],
        )

        self.assertIsValidUsd(stage)

    def testCrossRenderContexts(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.definePreviewMaterial(materials, "PreviewTest", Gf.Vec3f(0.0, 0.5, 1.0))
        self.assertTrue(material)

        funcs = [
            usdex.core.addColorTextureToPbrMaterial,
            usdex.core.addMetallicTextureToPbrMaterial,
            usdex.core.addNormalTextureToPbrMaterial,
            usdex.core.addOpacityTextureToPbrMaterial,
            usdex.core.addOrmTextureToPbrMaterial,
            usdex.core.addRoughnessTextureToPbrMaterial,
            usdex.core.addEmissiveTextureToPbrMaterial,
        ]
        for func in funcs:
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial().*")]):
                result = func(material, Sdf.AssetPath(self.tmpFile(name="TextureFile", ext="png")))
            self.assertFalse(result)

        self.assertIsValidUsd(stage)

        # Check that the texture function fails when there's no Preview material
        material = usdex.core.definePbrMaterial(materials, "JustPbrTest", Gf.Vec3f(0.8, 0.8, 0.8))
        previewSurfacePath = usdex.core.computeEffectivePreviewSurfaceShader(material).GetPrim().GetPath()
        stage.RemovePrim(previewSurfacePath)
        for func in funcs:
            with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*first be defined using definePbrMaterial().*")]):
                result = func(material, Sdf.AssetPath(self.tmpFile(name="TextureFile", ext="png")))
        self.assertFalse(result)

        self.assertIsValidUsd(stage)


# `defineGlassPreviewMaterial` internally calls `definePreviewMaterial`.
# For this reason, the test here focuses solely on the ior and opacity parameters.
class DefineGlassPreviewMaterialTest(PreviewMaterialHelpersMixin, usdex.test.DefineFunctionTestCase):
    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineGlassPreviewMaterial
    requiredArgs = tuple([Gf.Vec3f(1.0, 1.0, 1.0)])
    typeName = "Material"
    schema = UsdShade.Material
    requiredPropertyNames = set()

    def assertIsSurfaceShader(self, material: UsdShade.Material, shader: UsdShade.Shader):
        surfaceOutput = material.GetSurfaceOutput()
        self.assertTrue(surfaceOutput.HasConnectedSource())
        surface = surfaceOutput.GetConnectedSource()[0]
        self.assertEqual(surface.GetOutput(UsdShade.Tokens.surface).GetAttr(), shader.GetOutput(UsdShade.Tokens.surface).GetAttr())

    def testGlassPreviewMaterialShaders(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # the material is created successfully
        material = usdex.core.defineGlassPreviewMaterial(
            materials,
            "Test",
            Gf.Vec3f(0.0, 0.5, 0.9),
            indexOfRefraction=1.48,
            roughness=0.1,
            opacity=0.4,
        )
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
        self.assertTrue(Gf.IsClose(shaderInput.GetValueProducingAttributes()[0].Get(), Gf.Vec3f(0.0, 0.5, 0.9), 1e-6))

        # the shader should include a Float named "opacity" that has the effective specified value
        shaderInput = shader.GetInput("opacity")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.4)

        # the shader should include a Float named "ior" that has the effective specified value
        shaderInput = shader.GetInput("ior")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 1.48)

        # the shader should include a Float named "roughness" that has the effective specified value
        shaderInput = shader.GetInput("roughness")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.1)

        # the shader should include a Float named "metallic" that has the effective specified value
        shaderInput = shader.GetInput("metallic")
        self.assertTrue(shaderInput)
        self.assertEqual(shaderInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(shaderInput.GetValueProducingAttributes()[0].Get(), 0.0)

        # the shader is driving the surface of the material for the universal render context
        self.assertIsSurfaceShader(material, shader)

        # the shader is driving the displacement of the material for the universal render context
        displacementOutput = material.GetDisplacementOutput()
        self.assertFalse(displacementOutput.HasConnectedSource())

        # the volume output was not setup as this is not a volumetric material
        volumeOutput = material.GetVolumeOutput()
        self.assertFalse(volumeOutput.HasConnectedSource())
        self.assertFalse(shader.GetOutput(UsdShade.Tokens.volume))

        # all authored data is valid
        self.assertIsValidUsd(stage)

    def testGlassPreviewMaterialDefaultValues(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        material = usdex.core.defineGlassPreviewMaterial(materials, "Test", Gf.Vec3f(0.0, 0.5, 0.9))
        self.assertTrue(material)

        shader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(shader)
        self.assertAlmostEqual(shader.GetInput("opacity").GetValueProducingAttributes()[0].Get(), 0.2)
        self.assertAlmostEqual(shader.GetInput("ior").GetValueProducingAttributes()[0].Get(), 1.5)
        self.assertAlmostEqual(shader.GetInput("roughness").GetValueProducingAttributes()[0].Get(), 0.02)

        self.assertIsValidUsd(stage)

    def testInvalidInputs(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # An out-of-range color will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Color value .* is outside range")]):
            material = usdex.core.defineGlassPreviewMaterial(materials, "BadColor", Gf.Vec3f(-0.000001, -0.000001, -0.000001))
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Color value .* is outside range")]):
            material = usdex.core.defineGlassPreviewMaterial(materials, "BadColor", Gf.Vec3f(1.000001, 1.000001, 1.000001))
        self.assertFalse(material)

        # An indexOfRefraction below the minimum will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*IOR value -0.000001 is below minimum value 1.0")]):
            material = usdex.core.defineGlassPreviewMaterial(materials, "BadIndexOfRefraction", Gf.Vec3f(1, 0, 0), indexOfRefraction=-0.000001)
        self.assertFalse(material)
        material = usdex.core.defineGlassPreviewMaterial(materials, "HighIndexOfRefraction", Gf.Vec3f(1, 0, 0), indexOfRefraction=4.000001)
        self.assertTrue(material)

        # An out-of-range roughness will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Roughness value -0.000001 is outside range")]):
            material = usdex.core.defineGlassPreviewMaterial(materials, "BadRoughness", Gf.Vec3f(1, 0, 0), indexOfRefraction=1.5, roughness=-0.000001)
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Roughness value 1.000001 is outside range")]):
            material = usdex.core.defineGlassPreviewMaterial(materials, "BadRoughness", Gf.Vec3f(1, 0, 0), indexOfRefraction=1.5, roughness=1.000001)
        self.assertFalse(material)

        # An out-of-range opacity will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Opacity value -0.000001 is outside range")]):
            material = usdex.core.defineGlassPreviewMaterial(materials, "BadOpacity", Gf.Vec3f(1, 0, 0), indexOfRefraction=1.5, opacity=-0.000001)
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Opacity value 1.000001 is outside range")]):
            material = usdex.core.defineGlassPreviewMaterial(materials, "BadOpacity", Gf.Vec3f(1, 0, 0), indexOfRefraction=1.5, opacity=1.000001)
        self.assertFalse(material)

        self.assertIsValidUsd(stage)


class DefineGlassMaterialTest(PreviewMaterialHelpersMixin, usdex.test.DefineFunctionTestCase):
    defineFunc = usdex.core.defineGlassPbrMaterial
    requiredArgs = tuple([Gf.Vec3f(1.0, 1.0, 1.0)])
    typeName = "Material"
    schema = UsdShade.Material
    requiredPropertyNames = set()

    def _assertGlassInterfacePreserved(self, material: UsdShade.Material, color: Gf.Vec3f, ior: float, roughness: float, previewOpacity: float):
        # Verify the glass-specific material interface inputs (color/ior/roughness/opacity) hold the expected values and that
        # both render contexts' glass-relevant shader inputs (transmission/specular/IOR/roughness/opacity/diffuseColor) remain
        # routed through that interface. Used for newly-defined glass materials and to guard against emissive helpers stomping
        # on the glass network.
        colorInput = material.GetInput("color")
        self.assertTrue(colorInput)
        self.assertEqual(colorInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(Gf.IsClose(colorInput.Get(), color, 1e-6))

        iorInput = material.GetInput("ior")
        self.assertTrue(iorInput)
        self.assertEqual(iorInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(iorInput.Get(), ior)

        roughnessInput = material.GetInput("roughness")
        self.assertTrue(roughnessInput)
        self.assertEqual(roughnessInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(roughnessInput.Get(), roughness)

        opacityInput = material.GetInput("opacity")
        self.assertTrue(opacityInput)
        self.assertEqual(opacityInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(opacityInput.Get(), previewOpacity)

        assertLimitMetadata(
            self,
            colorInput,
            {
                "uimin": "0, 0, 0",
                "uimax": "1, 1, 1",
            },
            {"hard": {"minimum": Gf.Vec3f(0.0, 0.0, 0.0), "maximum": Gf.Vec3f(1.0, 1.0, 1.0)}},
        )
        assertLimitMetadata(
            self,
            iorInput,
            {
                "uimin": "0",
                "uisoftmin": "1",
                "uisoftmax": "3",
            },
            {"hard": {"minimum": 0.0}, "soft": {"minimum": 1.0, "maximum": 3.0}},
        )
        assertLimitMetadata(
            self,
            roughnessInput,
            {"uimin": "0", "uimax": "1"},
            {"hard": {"minimum": 0.0, "maximum": 1.0}},
        )
        assertLimitMetadata(
            self,
            opacityInput,
            {"uimin": "0", "uimax": "1"},
            {"hard": {"minimum": 0.0, "maximum": 1.0}},
        )

        # OpenPBR shader: glass connections (transmission_color/specular_ior/specular_roughness) routed through the material interface
        mtlxShader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        transmissionColor = mtlxShader.GetInput("transmission_color")
        self.assertTrue(transmissionColor.HasConnectedSource())
        self.assertEqual(transmissionColor.GetValueProducingAttributes()[0], colorInput.GetAttr())

        specularIor = mtlxShader.GetInput("specular_ior")
        self.assertTrue(specularIor.HasConnectedSource())
        self.assertEqual(specularIor.GetValueProducingAttributes()[0], iorInput.GetAttr())

        specularRoughness = mtlxShader.GetInput("specular_roughness")
        self.assertTrue(specularRoughness.HasConnectedSource())
        self.assertEqual(specularRoughness.GetValueProducingAttributes()[0], roughnessInput.GetAttr())

        # OpenPBR fixed weights remain unchanged
        self.assertAlmostEqual(mtlxShader.GetInput("base_weight").GetAttr().Get(), 0.0)
        self.assertAlmostEqual(mtlxShader.GetInput("specular_weight").GetAttr().Get(), 1.0)
        self.assertAlmostEqual(mtlxShader.GetInput("transmission_weight").GetAttr().Get(), 1.0)

        # UPS shader: glass connections (diffuseColor/ior/opacity/roughness) routed through the material interface
        previewShader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        diffuseColor = previewShader.GetInput("diffuseColor")
        self.assertTrue(diffuseColor.HasConnectedSource())
        self.assertEqual(diffuseColor.GetValueProducingAttributes()[0], colorInput.GetAttr())

        previewIor = previewShader.GetInput("ior")
        self.assertTrue(previewIor.HasConnectedSource())
        self.assertEqual(previewIor.GetValueProducingAttributes()[0], iorInput.GetAttr())

        previewOpacityInput = previewShader.GetInput("opacity")
        self.assertTrue(previewOpacityInput.HasConnectedSource())
        self.assertEqual(previewOpacityInput.GetValueProducingAttributes()[0], opacityInput.GetAttr())

        previewRoughness = previewShader.GetInput("roughness")
        self.assertTrue(previewRoughness.HasConnectedSource())
        self.assertEqual(previewRoughness.GetValueProducingAttributes()[0], roughnessInput.GetAttr())

    def testGlassMaterialShaders(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        color = Gf.Vec3f(0.0, 0.5, 0.9)
        ior = 1.48
        roughness = 0.1
        previewOpacity = 0.4
        material = usdex.core.defineGlassPbrMaterial(
            materials, "Test", color, indexOfRefraction=ior, roughness=roughness, previewOpacity=previewOpacity
        )
        self.assertTrue(material)

        # check the preview surface shader has the expected name + id
        previewShader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        self.assertTrue(previewShader)
        self.assertEqual(previewShader.GetPrim().GetName(), "PreviewSurface")
        self.assertEqual(previewShader.GetShaderId(), "UsdPreviewSurface")

        # check the OpenPBR shader has the expected name + id and is the bound mtlx surface
        mtlxShader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        self.assertTrue(mtlxShader)
        self.assertEqual(mtlxShader.GetPrim().GetName(), "OpenPBR")
        self.assertEqual(mtlxShader.GetShaderId(), "ND_open_pbr_surface_surfaceshader")
        self.assertIsSurfaceShader(material, mtlxShader)
        self.assertMaterialXVersion(material)

        # base_color and geometry_opacity are deliberately omitted on the OpenPBR shader -- glass uses transmission, not diffuse/opacity
        self.assertFalse(mtlxShader.GetInput("base_color"))
        self.assertFalse(mtlxShader.GetInput("geometry_opacity"))

        # All glass-specific interface inputs and shader connections are correctly authored on a freshly defined glass material
        self._assertGlassInterfacePreserved(material, color, ior, roughness, previewOpacity)

        self.assertIsValidUsd(stage)

    def testGlassMaterialDefaultValues(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        color = Gf.Vec3f(0.0, 0.5, 0.9)
        material = usdex.core.defineGlassPbrMaterial(materials, "Test", color)
        self.assertTrue(material)

        self._assertGlassInterfacePreserved(material, color, 1.5, 0.02, 0.2)

        self.assertIsValidUsd(stage)

    def testAddEmissiveColor(self):
        # Mirrors DefinePbrMaterialTest.testAddEmissiveColor, but verifies the glass material's existing interface inputs and
        # shader connections (transmission, IOR, opacity, roughness) are preserved alongside the new emissive ones.
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        glassColor = Gf.Vec3f(0.85, 0.95, 1.0)
        ior = 1.5
        roughness = 0.05
        previewOpacity = 0.4
        emissiveColor = Gf.Vec3f(1.0, 0.9, 0.2)
        emissiveLuminance = 3000.0

        material = usdex.core.defineGlassPbrMaterial(
            materials, "Test", glassColor, indexOfRefraction=ior, roughness=roughness, previewOpacity=previewOpacity
        )
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(material, emissiveColor, emissiveLuminance))

        # New emissive material interface inputs were created with the supplied values
        emissiveColorInput = material.GetInput("emissiveColor")
        self.assertTrue(emissiveColorInput)
        self.assertEqual(emissiveColorInput.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(Gf.IsClose(emissiveColorInput.Get(), emissiveColor, 1e-6))

        emissiveLuminanceInput = material.GetInput("emissiveLuminance")
        self.assertTrue(emissiveLuminanceInput)
        self.assertEqual(emissiveLuminanceInput.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertAlmostEqual(emissiveLuminanceInput.Get(), emissiveLuminance)

        # OpenPBR emission_color / emission_luminance connect to the material interface (no direct authored values on the shader)
        mtlxShader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        emissionColor = mtlxShader.GetInput("emission_color")
        self.assertTrue(emissionColor)
        self.assertEqual(emissionColor.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(emissionColor.HasConnectedSource())
        self.assertEqual(emissionColor.GetValueProducingAttributes()[0], emissiveColorInput.GetAttr())
        self.assertFalse(emissionColor.GetAttr().HasAuthoredValue())
        self.assertTrue(Gf.IsClose(emissionColor.GetValueProducingAttributes()[0].Get(), emissiveColor, 1e-6))

        emissionLuminance = mtlxShader.GetInput("emission_luminance")
        self.assertTrue(emissionLuminance)
        self.assertEqual(emissionLuminance.GetTypeName(), Sdf.ValueTypeNames.Float)
        self.assertTrue(emissionLuminance.HasConnectedSource())
        self.assertEqual(emissionLuminance.GetValueProducingAttributes()[0], emissiveLuminanceInput.GetAttr())
        self.assertFalse(emissionLuminance.GetAttr().HasAuthoredValue())
        self.assertAlmostEqual(emissionLuminance.GetValueProducingAttributes()[0].Get(), emissiveLuminance)

        # UPS emissiveColor connects to the material interface (no direct authored value on the shader)
        previewShader = usdex.core.computeEffectivePreviewSurfaceShader(material)
        previewEmissive = previewShader.GetInput("emissiveColor")
        self.assertTrue(previewEmissive)
        self.assertEqual(previewEmissive.GetTypeName(), Sdf.ValueTypeNames.Color3f)
        self.assertTrue(previewEmissive.HasConnectedSource())
        self.assertEqual(previewEmissive.GetValueProducingAttributes()[0], emissiveColorInput.GetAttr())
        self.assertFalse(previewEmissive.GetAttr().HasAuthoredValue())
        self.assertTrue(Gf.IsClose(previewEmissive.GetValueProducingAttributes()[0].Get(), emissiveColor, 1e-6))

        # The glass-specific interface inputs and shader connections are untouched
        self._assertGlassInterfacePreserved(material, glassColor, ior, roughness, previewOpacity)

        # Calling again with new values updates the material interface (and therefore both shaders), without disturbing glass inputs
        newEmissiveColor = Gf.Vec3f(0.5, 0.0, 0.5)
        newEmissiveLuminance = 100.0
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(material, newEmissiveColor, newEmissiveLuminance))
        self.assertTrue(Gf.IsClose(material.GetInput("emissiveColor").Get(), newEmissiveColor, 1e-6))
        self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), newEmissiveLuminance)
        self._assertGlassInterfacePreserved(material, glassColor, ior, roughness, previewOpacity)

        # Omitting the luminance argument should fall back to the documented 1000.0 cd/m^2 default
        defaultMaterial = usdex.core.defineGlassPbrMaterial(
            materials, "DefaultLuminance", glassColor, indexOfRefraction=ior, roughness=roughness, previewOpacity=previewOpacity
        )
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(defaultMaterial, emissiveColor))
        self.assertAlmostEqual(defaultMaterial.GetInput("emissiveLuminance").Get(), 1000.0)
        self.assertTrue(Gf.IsClose(defaultMaterial.GetInput("emissiveColor").Get(), emissiveColor, 1e-6))

        self.assertIsValidUsd(stage)

    def testAddEmissiveTexture(self):
        # Mirrors DefinePbrMaterialTest.testAddEmissiveTexture, but for glass: the texture must drive emission while the
        # transmission/IOR/opacity glass shader network remains intact in both render contexts.
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()
        textures = [Sdf.AssetPath(self.tmpFile(name="emissive", ext="png")), Sdf.AssetPath(self.tmpFile(name="emissive2", ext="png"))]

        glassColor = Gf.Vec3f(0.85, 0.95, 1.0)
        ior = 1.5
        roughness = 0.05
        previewOpacity = 0.4

        # No prior emissive color: OpenPBR `emission_color` defaults to zero, so the texture fallback / UPS fallback are zero.
        # The luminance defaults to 1000.0 cd/m^2, creating a new `emissiveLuminance` material interface input.
        material = usdex.core.defineGlassPbrMaterial(
            materials, "NoColor", glassColor, indexOfRefraction=ior, roughness=roughness, previewOpacity=previewOpacity
        )
        self.assertTrue(usdex.core.addEmissiveTextureToPbrMaterial(material, textures[0]))

        self.assertTrue(material.GetInput("emissiveLuminance"))
        self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), 1000.0)

        # The OpenPBR emissive texture shader is wired to a material-interface file input and to the shared MtlxPrimvar tex coord reader.
        mtlxTexCoord = UsdShade.Shader(material.GetPrim().GetChild("MtlxPrimvar_st_float2"))
        self.assertTrue(mtlxTexCoord)
        self.assertEqual(mtlxTexCoord.GetShaderId(), "ND_geompropvalue_vector2")
        self.assertEqual(mtlxTexCoord.GetInput("geomprop").GetAttr().Get(), UsdUtils.GetPrimaryUVSetName())

        mtlxTexShader = UsdShade.Shader(material.GetPrim().GetChild("MtlxEmissiveTexture"))
        self.assertTrue(mtlxTexShader)
        self.assertEqual(mtlxTexShader.GetShaderId(), "ND_tiledimage_color3")
        self.assertEqual(mtlxTexShader.GetInput("default").GetAttr().Get(), Gf.Vec3f(0.0, 0.0, 0.0))
        # `file` reads from the material interface input
        fileInput = mtlxTexShader.GetInput("file")
        self.assertTrue(fileInput.HasConnectedSource())
        materialFileAttr = fileInput.GetValueProducingAttributes()[0]
        self.assertEqual(materialFileAttr.Get().path, textures[0])
        # tex coord wiring + standard tile defaults
        self.assertTrue(mtlxTexShader.GetInput("texcoord").HasConnectedSource())
        self.assertEqual(
            mtlxTexShader.GetInput("texcoord").GetConnectedSource()[0].GetOutputs()[0].GetAttr(), mtlxTexCoord.GetOutput("out").GetAttr()
        )
        self.assertEqual(mtlxTexShader.GetInput("uvtiling").GetAttr().Get(), Gf.Vec2f(1.0, 1.0))
        self.assertEqual(mtlxTexShader.GetInput("uvoffset").GetAttr().Get(), Gf.Vec2f(0.0, 0.0))

        mtlxShader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
        # OpenPBR `emission_color` is driven by the texture shader output (no authored direct value)
        self.assertTrue(mtlxShader.GetInput("emission_color").HasConnectedSource())
        self.assertEqual(
            mtlxShader.GetInput("emission_color").GetConnectedSource()[0].GetOutputs()[0].GetAttr(), mtlxTexShader.GetOutput("out").GetAttr()
        )
        self.assertFalse(mtlxShader.GetInput("emission_color").GetAttr().HasAuthoredValue())
        # OpenPBR `emission_luminance` connects to the new material interface input
        emissionLuminance = mtlxShader.GetInput("emission_luminance")
        self.assertTrue(emissionLuminance.HasConnectedSource())
        self.assertEqual(emissionLuminance.GetValueProducingAttributes()[0], material.GetInput("emissiveLuminance").GetAttr())

        # UPS texture network: shared UV reader + texture reader fed into the PreviewSurface emissiveColor input
        self.assertValidPreviewMaterialTextureNetwork(
            material,
            textures[0],
            textureReaderName="EmissiveTexture",
            colorSpace=usdex.core.ColorSpace.eAuto,
            fallbackColor=Gf.Vec3f(0.0, 0.0, 0.0),
            connectionInfo=[("emissiveColor", Sdf.ValueTypeNames.Color3f, "rgb")],
        )

        # Glass-specific connections survived the texture authoring
        self._assertGlassInterfacePreserved(material, glassColor, ior, roughness, previewOpacity)

        # When an emissive color was authored beforehand, it becomes the texture fallback (Mtlx `default` and UPS `fallback`),
        # the scalar `emissiveColor` interface input is replaced by the `EmissiveTexture` interface input,
        # and the explicit luminance argument overwrites any value previously set by addEmissiveColorToPbrMaterial.
        material = usdex.core.defineGlassPbrMaterial(
            materials, "InitialValues", glassColor, indexOfRefraction=ior, roughness=roughness, previewOpacity=previewOpacity
        )
        emissiveColor = Gf.Vec3f(1.0, 1.0, 0.2)
        emissiveLuminance = 500.0
        self.assertTrue(usdex.core.addEmissiveColorToPbrMaterial(material, emissiveColor, emissiveLuminance))
        self.assertTrue(material.GetInput("emissiveColor"))
        self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), emissiveLuminance)
        self._assertGlassInterfacePreserved(material, glassColor, ior, roughness, previewOpacity)

        textureLuminance = 250.0
        for texture in textures:
            self.assertTrue(usdex.core.addEmissiveTextureToPbrMaterial(material, texture, textureLuminance))

            # Scalar emissiveColor interface input is removed (replaced by EmissiveTexture); luminance is overwritten
            self.assertFalse(material.GetInput("emissiveColor"))
            self.assertTrue(material.GetInput("emissiveLuminance"))
            self.assertAlmostEqual(material.GetInput("emissiveLuminance").Get(), textureLuminance)

            mtlxTexShader = UsdShade.Shader(material.GetPrim().GetChild("MtlxEmissiveTexture"))
            self.assertTrue(mtlxTexShader)
            self.assertEqual(mtlxTexShader.GetShaderId(), "ND_tiledimage_color3")
            # `file` updates across calls; the previously authored emissive color persists as the fallback `default`.
            self.assertEqual(mtlxTexShader.GetInput("file").GetValueProducingAttributes()[0].Get().path, texture)
            self.assertTrue(Gf.IsClose(mtlxTexShader.GetInput("default").GetAttr().Get(), emissiveColor, 1e-6))

            mtlxShader = usdex.core.computeEffectiveMtlxSurfaceShader(material)
            self.assertTrue(mtlxShader.GetInput("emission_color").HasConnectedSource())
            self.assertEqual(
                mtlxShader.GetInput("emission_color").GetConnectedSource()[0].GetOutputs()[0].GetAttr(),
                mtlxTexShader.GetOutput("out").GetAttr(),
            )
            self.assertFalse(mtlxShader.GetInput("emission_color").GetAttr().HasAuthoredValue())

            # The OpenPBR emission_luminance remains connected to the material interface
            emissionLuminance = mtlxShader.GetInput("emission_luminance")
            self.assertTrue(emissionLuminance.HasConnectedSource())
            self.assertEqual(emissionLuminance.GetValueProducingAttributes()[0], material.GetInput("emissiveLuminance").GetAttr())

            # UPS fallback was set to the previously authored emissive color and persists across subsequent calls.
            self.assertValidPreviewMaterialTextureNetwork(
                material,
                texture,
                textureReaderName="EmissiveTexture",
                colorSpace=usdex.core.ColorSpace.eAuto,
                fallbackColor=emissiveColor,
                connectionInfo=[("emissiveColor", Sdf.ValueTypeNames.Color3f, "rgb")],
            )

            # Glass-specific connections still intact across repeated texture authoring
            self._assertGlassInterfacePreserved(material, glassColor, ior, roughness, previewOpacity)

        self.assertIsValidUsd(stage)

    def testInvalidInputs(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)
        materials = UsdGeom.Scope.Define(stage, stage.GetDefaultPrim().GetPath().AppendChild(UsdUtils.GetMaterialsScopeName())).GetPrim()

        # An out-of-range color will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Color value .* is outside range")]):
            material = usdex.core.defineGlassPbrMaterial(
                materials, "BadColor", Gf.Vec3f(-0.000001, -0.000001, -0.000001), indexOfRefraction=1.5, roughness=0.1, previewOpacity=0.4
            )
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Color value .* is outside range")]):
            material = usdex.core.defineGlassPbrMaterial(
                materials, "BadColor", Gf.Vec3f(1.000001, 1.000001, 1.000001), indexOfRefraction=1.5, roughness=0.1, previewOpacity=0.4
            )
        self.assertFalse(material)

        # An indexOfRefraction below the minimum will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*IOR value -0.000001 is below minimum value 1.0")]):
            material = usdex.core.defineGlassPbrMaterial(
                materials, "BadIndexOfRefraction", Gf.Vec3f(1, 0, 0), indexOfRefraction=-0.000001, roughness=0.1, previewOpacity=0.4
            )
        self.assertFalse(material)
        material = usdex.core.defineGlassPbrMaterial(
            materials, "HighIndexOfRefraction", Gf.Vec3f(1, 0, 0), indexOfRefraction=4.000001, roughness=0.1, previewOpacity=0.4
        )
        self.assertTrue(material)

        # An out-of-range roughness will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Roughness value -0.000001 is outside range")]):
            material = usdex.core.defineGlassPbrMaterial(
                materials, "BadRoughness", Gf.Vec3f(1, 0, 0), indexOfRefraction=1.5, roughness=-0.000001, previewOpacity=0.4
            )
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Roughness value 1.000001 is outside range")]):
            material = usdex.core.defineGlassPbrMaterial(
                materials, "BadRoughness", Gf.Vec3f(1, 0, 0), indexOfRefraction=1.5, roughness=1.000001, previewOpacity=0.4
            )
        self.assertFalse(material)

        # An out-of-range previewOpacity will prevent authoring a material
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Opacity value -0.000001 is outside range")]):
            material = usdex.core.defineGlassPbrMaterial(
                materials, "BadOpacity", Gf.Vec3f(1, 0, 0), indexOfRefraction=1.5, roughness=0.1, previewOpacity=-0.000001
            )
        self.assertFalse(material)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Opacity value 1.000001 is outside range")]):
            material = usdex.core.defineGlassPbrMaterial(
                materials, "BadOpacity", Gf.Vec3f(1, 0, 0), indexOfRefraction=1.5, roughness=0.1, previewOpacity=1.000001
            )
        self.assertFalse(material)

        self.assertIsValidUsd(stage)


class ConnectPreviewSurfacePrimvarShaderTest(usdex.test.TestCase):

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

        # Define the material and the surface shader to ensure we have a Preview Surface surface shader, but specifically
        # don't use definePbrMaterial() to show that it's not a prerequisite
        self.material = UsdShade.Material.Define(self.stage, self.materials.GetPath().AppendChild("TestMaterial"))
        surfaceShader = UsdShade.Shader.Define(self.stage, self.material.GetPath().AppendChild("TestSurfaceShader"))
        surfaceShader.SetShaderId("UsdPreviewSurface")
        self.material.CreateSurfaceOutput().ConnectToSource(surfaceShader.CreateOutput("surface", Sdf.ValueTypeNames.Token))

        # this shader id is invented so the tests can declare arbitrary input names and types without depending on a real Sdr node,
        # so `Sdr` cannot resolve it, but the generated primvar reader shaders must still validate
        self.shader = UsdShade.Shader.Define(self.stage, self.material.GetPath().AppendChild("TestShader"))
        self.shader.SetShaderId("UsdTestShader")
        shaderPath = self.shader.GetPath()
        self.defaultValidationIssuePredicates = [
            usd_validation_nvidia.IssuePredicates.And(
                usd_validation_nvidia.IssuePredicates.IsRule("ShaderSdrCompliance"),
                lambda issue: getattr(issue.at, "prim_id", None) is not None and issue.at.prim_id.path == shaderPath,
            )
        ]

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
            inputProperty = shaderNodeDef.GetShaderInput("fallback")
            self.assertTrue(inputProperty)
            outputProperty = shaderNodeDef.GetShaderOutput("result")
            self.assertTrue(outputProperty)

            # In USD 24.11, SdfTypeIndicator was converted from a std::pair to a full class
            if isinstance(inputProperty.GetTypeAsSdfType(), tuple):
                inputPropertySdfType = inputProperty.GetTypeAsSdfType()[0]
                outputPropertySdfType = outputProperty.GetTypeAsSdfType()[0]
            else:
                inputPropertySdfType = inputProperty.GetTypeAsSdfType().GetSdfType()
                outputPropertySdfType = outputProperty.GetTypeAsSdfType().GetSdfType()

            self.assertEqual(fallback.GetTypeName(), inputPropertySdfType)
            self.assertEqual(result.GetTypeName(), outputPropertySdfType)

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


class ConnectMtlxPrimvarShaderTest(usdex.test.TestCase):

    # MaterialX primvar readers use the type name directly (no role distinction).
    # input sdfTypeName: (output SdfTypeName, mtlxTypeId, fallbackValue)
    typeMappings = {
        Sdf.ValueTypeNames.Int: (Sdf.ValueTypeNames.Int, "integer", 1),
        Sdf.ValueTypeNames.Bool: (Sdf.ValueTypeNames.Bool, "boolean", True),
        Sdf.ValueTypeNames.Float: (Sdf.ValueTypeNames.Float, "float", 0.8),
        Sdf.ValueTypeNames.Color3f: (Sdf.ValueTypeNames.Color3f, "color3", Gf.Vec3f(0.1, 0.2, 0.3)),
        Sdf.ValueTypeNames.Color4f: (Sdf.ValueTypeNames.Color4f, "color4", Gf.Vec4f(0.4, 0.5, 0.6, 0.7)),
        Sdf.ValueTypeNames.Float2: (Sdf.ValueTypeNames.Float2, "vector2", Gf.Vec2f(0.1, 0.2)),
        Sdf.ValueTypeNames.Float3: (Sdf.ValueTypeNames.Float3, "vector3", Gf.Vec3f(0.3, 0.4, 0.5)),
        Sdf.ValueTypeNames.Float4: (Sdf.ValueTypeNames.Float4, "vector4", Gf.Vec4f(0.6, 0.7, 0.8, 0.9)),
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

        # Define the material and the surface shader to ensure we have a MaterialX surface shader, but specifically
        # don't use definePbrMaterial() to show that it's not a prerequisite
        self.material = UsdShade.Material.Define(self.stage, self.materials.GetPath().AppendChild("TestMaterial"))
        surfaceShader = UsdShade.Shader.Define(self.stage, self.material.GetPath().AppendChild("TestSurfaceShader"))
        surfaceShader.SetShaderId("ND_surface_unlit")
        self.material.CreateSurfaceOutput("mtlx").ConnectToSource(surfaceShader.CreateOutput("out", Sdf.ValueTypeNames.Token))

        # this shader id is invented so `isMtlxNetworkShader` selects the MaterialX branch for arbitrary input names and types, without
        # depending on a real Sdr node, so `Sdr` cannot resolve it, but the generated primvar reader shaders must still validate
        self.shader = UsdShade.Shader.Define(self.stage, self.material.GetPath().AppendChild("TestShader"))
        self.shader.SetShaderId("ND_test_shader")
        shaderPath = self.shader.GetPath()
        self.defaultValidationIssuePredicates = [
            usd_validation_nvidia.IssuePredicates.And(
                usd_validation_nvidia.IssuePredicates.IsRule("ShaderSdrCompliance"),
                lambda issue: getattr(issue.at, "prim_id", None) is not None and issue.at.prim_id.path == shaderPath,
            )
        ]

    def assertValidMtlxShaderPrimvarNetwork(
        self,
        shader: UsdShade.Shader,
        primvarInfo: List[Tuple[str, str, Any]],  # inputName, primvarName, fallbackValue
    ):
        self.assertTrue(shader)

        for inputName, primvarName, fallbackValue in primvarInfo:
            input = shader.GetInput(inputName)
            outputName = "out"

            if input.GetTypeName() in self.typeMappings:
                outputTypeName, mtlxTypeId, _setFallbackValue = self.typeMappings[input.GetTypeName()]
            else:
                outputTypeName = input.GetTypeName()
                mtlxTypeId = input.GetTypeName().GetAsToken().GetString()

            validPrimvarName = primvarName.replace(":", "_")
            primvarReaderName = usdex.core.getValidPrimName(f"MtlxPrimvar_{validPrimvarName}_{outputTypeName}")
            primvarReader = UsdShade.Shader(shader.GetPrim().GetParent().GetChild(primvarReaderName))
            self.assertTrue(primvarReader, msg=f"Expected primvar reader {primvarReaderName} not found")
            self.assertEqual(primvarReader.GetShaderId(), f"ND_geompropvalue_{mtlxTypeId}")
            self.assertEqual(str(primvarReader.GetOutput(outputName).GetTypeName()), str(outputTypeName))
            self.assertEqual(primvarReader.GetInput("geomprop").GetAttr().Get(), primvarName)
            if fallbackValue is not None:
                self.assertEqual(primvarReader.GetInput("default").GetTypeName(), outputTypeName)
                self.assertAlmostEqual(primvarReader.GetInput("default").GetAttr().Get(), fallbackValue)
            else:
                self.assertFalse(primvarReader.GetInput("default"))

            self.assertTrue(input.HasConnectedSource())
            source, sourceAttr, sourceType = input.GetConnectedSource()
            self.assertEqual(sourceType, UsdShade.AttributeType.Output)
            self.assertEqual(
                source.GetOutput(sourceAttr).GetAttr(),
                primvarReader.GetOutput(outputName).GetAttr(),
                msg=f"Incorrect connection for {inputName} ({input.GetTypeName()}) -> {outputName}",
            )
            self.assertFalse(input.GetAttr().HasAuthoredValue())
            self.assertEqual(len(input.GetValueProducingAttributes()), 1)
            self.assertEqual(input.GetValueProducingAttributes()[0], primvarReader.GetOutput(outputName).GetAttr())

    def testConnect(self):
        shaderInput = self.shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f)
        result = usdex.core.connectPrimvarShader(shaderInput, "paintColor", Gf.Vec3f(0.1, 0.2, 0.3))
        self.assertTrue(result)
        self.assertValidMtlxShaderPrimvarNetwork(
            self.shader,
            [("base_color", "paintColor", Gf.Vec3f(0.1, 0.2, 0.3))],
        )

        shaderInput = self.shader.CreateInput("specular_roughness", Sdf.ValueTypeNames.Float)
        result = usdex.core.connectPrimvarShader(shaderInput, "paint:Roughness")
        self.assertTrue(result)
        self.assertValidMtlxShaderPrimvarNetwork(
            self.shader,
            [
                ("base_color", "paintColor", Gf.Vec3f(0.1, 0.2, 0.3)),
                ("specular_roughness", "paint:Roughness", None),
            ],
        )
        self.assertIsValidUsd(self.stage)

    def testInvalidInput(self):
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*UsdShadeInput is not valid.*")]):
            result = usdex.core.connectPrimvarShader(UsdShade.Input(), "paintColor")
            self.assertFalse(result)
        self.assertIsValidUsd(self.stage)

    def testInvalidNames(self):
        shaderInput = self.shader.CreateInput("base_color", Sdf.ValueTypeNames.Color3f)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*the primvar name is invalid.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "")
            self.assertFalse(result)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*the primvar name is invalid.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "inv@lidName")
            self.assertFalse(result)
        self.assertIsValidUsd(self.stage)

    def testAllInputTypes(self):
        connectionData = []
        for inputType in self.typeMappings.keys():
            connectionType, mtlxTypeId, fallbackValue = self.typeMappings[inputType]
            shaderInput = self.shader.CreateInput(f"shaderInput_{mtlxTypeId}", inputType)
            result = usdex.core.connectPrimvarShader(shaderInput, f"pv_{mtlxTypeId}", fallbackValue)
            self.assertTrue(result, msg=f"Failed to connect primvar for type {inputType}")
            connectionData.append((f"shaderInput_{mtlxTypeId}", f"pv_{mtlxTypeId}", fallbackValue))

        self.assertValidMtlxShaderPrimvarNetwork(
            self.shader,
            connectionData,
        )
        self.assertIsValidUsd(self.stage)

    def testAllInputTypesWithSdrRegistry(self):
        #  Run the test that creates all of the currently supported USD Preview Surface input types
        self.testAllInputTypes()

        shaderIdNames = self.getAllShaderNames()
        for prim in self.material.GetPrim().GetChildren():
            shader = UsdShade.Shader(prim)
            if "ND_geompropvalue_" not in shader.GetShaderId():
                continue

            self.assertIn(shader.GetShaderId(), shaderIdNames)

            # Check that "fallback" and "result" are the correct types
            fallback = shader.GetInput("default")
            result = shader.GetOutput("out")

            shaderNodeDef = Sdr.Registry().GetShaderNodeByIdentifier(shader.GetShaderId())
            inputProperty = shaderNodeDef.GetShaderInput("default")
            self.assertTrue(inputProperty)
            outputProperty = shaderNodeDef.GetShaderOutput("out")
            self.assertTrue(outputProperty)

            # In USD 24.11, SdfTypeIndicator was converted from a std::pair to a full class
            if isinstance(inputProperty.GetTypeAsSdfType(), tuple):
                inputPropertySdfType = inputProperty.GetTypeAsSdfType()[0]
                outputPropertySdfType = outputProperty.GetTypeAsSdfType()[0]
            else:
                inputPropertySdfType = inputProperty.GetTypeAsSdfType().GetSdfType()
                outputPropertySdfType = outputProperty.GetTypeAsSdfType().GetSdfType()

            self.assertEqual(fallback.GetTypeName(), inputPropertySdfType)
            self.assertEqual(result.GetTypeName(), outputPropertySdfType)

    def testOverwriteOutputType(self):
        shaderInput = self.shader.CreateInput("specular_roughness", Sdf.ValueTypeNames.Float)
        shaderPath = self.shader.GetPrim().GetParent().GetPath().AppendChild("MtlxPrimvar_paintRoughness_float")
        primvarShader = UsdShade.Shader.Define(self.stage, shaderPath)

        primvarShader.CreateOutput("out", Sdf.ValueTypeNames.String)

        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*existing shader.*does not match the input type.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "paintRoughness")
            self.assertFalse(result)

    def testUnsupportedMtlxInputType(self):
        shaderInput = self.shader.CreateInput("unsupportedNormal", Sdf.ValueTypeNames.Normal3f)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*<normal3f> is not supported.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "paintNormal")
            self.assertFalse(result)

        shaderInput = self.shader.CreateInput("unsupportedString", Sdf.ValueTypeNames.String)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*<string> is not supported.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "paintString")
            self.assertFalse(result)

        shaderInput = self.shader.CreateInput("unsupportedMatrix", Sdf.ValueTypeNames.Matrix4d)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*<matrix4d> is not supported.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "paintMatrix")
            self.assertFalse(result)

        shaderInput = self.shader.CreateInput("unsupportedDouble", Sdf.ValueTypeNames.Double)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot connect primvar.*<double> is not supported.*")]):
            result = usdex.core.connectPrimvarShader(shaderInput, "paintDouble")
            self.assertFalse(result)
