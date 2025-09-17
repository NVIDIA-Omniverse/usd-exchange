# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import usdex.core
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt


class DefineCameraTestCase(usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCamera
    requiredArgs = tuple([Gf.Camera()])
    schema = UsdGeom.Camera
    typeName = "Camera"
    requiredPropertyNames = set(
        [
            UsdGeom.Tokens.projection,
            UsdGeom.Tokens.horizontalAperture,
            UsdGeom.Tokens.verticalAperture,
            UsdGeom.Tokens.horizontalApertureOffset,
            UsdGeom.Tokens.verticalApertureOffset,
            UsdGeom.Tokens.focalLength,
            UsdGeom.Tokens.clippingRange,
            UsdGeom.Tokens.clippingPlanes,
            UsdGeom.Tokens.fStop,
            UsdGeom.Tokens.focusDistance,
            # FUTURE: account for shutter, stereo, exposure
        ]
    )

    def assertCamerasEqual(self, camera: UsdGeom.Camera, cameraData: Gf.Camera):
        self.assertEqual(camera.GetLocalTransformation(), cameraData.transform)
        self.assertEqual(usdex.core.getLocalTransformMatrix(camera.GetPrim()), cameraData.transform)

        projection = camera.GetProjectionAttr().Get()
        if projection == "perspective":
            self.assertEqual(cameraData.projection, Gf.Camera.Perspective)
        elif projection == "orthographic":
            self.assertEqual(cameraData.projection, Gf.Camera.Orthographic)
        else:
            self.assertFalse(True, f"Camera has an invalid projection attr '{projection}'")

        self.assertEqual(camera.GetHorizontalApertureAttr().Get(), cameraData.horizontalAperture)
        self.assertEqual(camera.GetVerticalApertureAttr().Get(), cameraData.verticalAperture)
        self.assertEqual(camera.GetHorizontalApertureOffsetAttr().Get(), cameraData.horizontalApertureOffset)
        self.assertEqual(camera.GetVerticalApertureOffsetAttr().Get(), cameraData.verticalApertureOffset)
        self.assertEqual(camera.GetFocalLengthAttr().Get(), cameraData.focalLength)
        self.assertEqual(camera.GetClippingRangeAttr().Get(), Gf.Vec2f(cameraData.clippingRange.min, cameraData.clippingRange.max))

        self.assertEqual(camera.GetClippingPlanesAttr().Get(), Vt.Vec4fArray(cameraData.clippingPlanes))

        self.assertEqual(camera.GetFStopAttr().Get(), cameraData.fStop)
        self.assertEqual(camera.GetFocusDistanceAttr().Get(), cameraData.focusDistance)

    def testStrongerWeaker(self):
        # This differs from the implementation in DefineFunctionTestCase
        # A prim can be defined in a stronger sub layer but will fail to re-define in a weaker one.
        stage = self.createTestStage()

        path = Sdf.Path("/World/StrongerFirst")
        stage.SetEditTarget(Usd.EditTarget(self.strongerSubLayer))
        result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionSuccess(result)
        self.assertIsValidUsd(result.GetPrim().GetStage())

        stage.SetEditTarget(Usd.EditTarget(self.weakerSubLayer))
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*opinions in the composed layer stack are stronger"),
                (Tf.TF_DIAGNOSTIC_WARNING_TYPE, "Could not clear xformOpOrder"),
            ],
        ):
            result = self.defineFunc(stage, path, *self.requiredArgs)
        self.assertDefineFunctionFailure(result)

    def testDefineDefaultCamera(self):
        stage = self.createTestStage()
        path = Sdf.Path("/World/Camera")
        cameraData = Gf.Camera()
        camera = usdex.core.defineCamera(stage, path, cameraData)
        self.assertDefineFunctionSuccess(camera)
        self.assertCamerasEqual(camera, cameraData)
        self.assertIsValidUsd(stage)

    def testDefineOrthoCamera(self):
        stage = self.createTestStage()
        path = Sdf.Path("/World/Camera")
        cameraData = Gf.Camera(projection=Gf.Camera.Orthographic)
        camera = usdex.core.defineCamera(stage, path, cameraData)
        self.assertDefineFunctionSuccess(camera)
        self.assertCamerasEqual(camera, cameraData)
        self.assertIsValidUsd(stage)

    def testDefineTransformedCamera(self):
        stage = self.createTestStage()
        path = Sdf.Path("/World/Camera")
        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))
        transform.SetPivotPosition(Gf.Vec3d(10.0, 20.0, 30.0))
        transform.SetRotation(Gf.Rotation(Gf.Vec3d.XAxis(), 45.0))
        transform.SetScale(Gf.Vec3d(2.0, 2.0, 2.0))
        cameraData = Gf.Camera(transform=transform.GetMatrix())
        camera = usdex.core.defineCamera(stage, path, cameraData)
        self.assertDefineFunctionSuccess(camera)
        self.assertCamerasEqual(camera, cameraData)
        self.assertIsValidUsd(stage)

    def testDefineCameraFromXform(self):
        stage = self.createTestStage()
        xform = UsdGeom.Xform.Define(stage, Sdf.Path("/World/ExistingXform"))
        cameraData = Gf.Camera()
        camera = usdex.core.defineCamera(xform.GetPrim(), cameraData)
        self.assertTrue(camera)
        self.assertEqual(camera.GetPrim().GetTypeName(), "Camera")
        self.assertIsValidUsd(stage)

    def testDefineCameraFromPrimWithTransform(self):
        stage = self.createTestStage()
        xform = UsdGeom.Xform.Define(stage, Sdf.Path("/World/TransformedXform"))
        # Set an initial transform on the xform
        usdex.core.setLocalTransform(xform.GetPrim(), Gf.Transform(Gf.Matrix4d().SetTranslate(Gf.Vec3d(1, 2, 3))))

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))
        cameraData = Gf.Camera(transform=transform.GetMatrix())
        camera = usdex.core.defineCamera(xform.GetPrim(), cameraData)
        self.assertTrue(camera)
        self.assertEqual(camera.GetPrim().GetTypeName(), "Camera")
        self.assertIsValidUsd(stage)
        self.assertEqual(camera.GetLocalTransformation(), transform.GetMatrix())

    def testDefineCameraFromPrimTypeGuards(self):
        stage = self.createTestStage()
        cameraData = Gf.Camera()

        # Test with non-Scope/Xform prim - should warn
        meshPrim = stage.DefinePrim("/World/MeshPrim", "Mesh")
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Redefining prim.*from type.*Mesh.*to.*Camera.*Expected original type to be.*Scope.*or.*Xform")]
        ):
            camera = usdex.core.defineCamera(meshPrim, cameraData)
        self.assertTrue(camera)
        self.assertEqual(camera.GetPrim().GetTypeName(), "Camera")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            camera = usdex.core.defineCamera(scopePrim, cameraData)
        self.assertTrue(camera)
        self.assertEqual(camera.GetPrim().GetTypeName(), "Camera")

        # Test with Xform prim - should not warn
        xformPrim = stage.DefinePrim("/World/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            camera = usdex.core.defineCamera(xformPrim, cameraData)
        self.assertTrue(camera)
        self.assertEqual(camera.GetPrim().GetTypeName(), "Camera")

    def testAuthoringOneFilmbackAttributeAuthorsAllOnNonCentimeterStage(self):
        # Authoring a single lens/filmback attribute should result in all related
        # attributes being explicitly authored when the stage units are not centimeters.
        stage = self.createTestStage()
        stage.SetEditTarget(Usd.EditTarget(self.rootLayer))

        # Switch the stage to meters so tenths-of-scene-unit no longer equals millimeters
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.meters)

        path = Sdf.Path("/World/CameraUnits")

        # Only author a single property on the GfCamera; SetFromCamera should still
        # author all lens/filmback properties on the prim.
        cameraData = Gf.Camera()
        cameraData.verticalAperture = 0.1

        camera = usdex.core.defineCamera(stage, path, cameraData)
        self.assertDefineFunctionSuccess(camera)

        # Verify that all lens/filmback properties have authored default values
        # in the current edit target layer (no reliance on fallbacks).
        layer = stage.GetEditTarget().GetLayer()
        primPath = camera.GetPath()
        for propertyName in [
            UsdGeom.Tokens.horizontalAperture,
            UsdGeom.Tokens.verticalAperture,
            UsdGeom.Tokens.horizontalApertureOffset,
            UsdGeom.Tokens.verticalApertureOffset,
            UsdGeom.Tokens.focalLength,
            UsdGeom.Tokens.focusDistance,
            UsdGeom.Tokens.clippingRange,
        ]:
            propertySpec = layer.GetAttributeAtPath(primPath.AppendProperty(propertyName))
            attr = camera.GetPrim().GetAttribute(propertyName)
            self.assertTrue(
                propertySpec and propertySpec.HasDefaultValue() and attr.HasAuthoredValue(),
                f'Property "{propertyName}" not explicitly authored on non-centimeter stage',
            )
