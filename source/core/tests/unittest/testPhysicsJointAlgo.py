# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import List, Tuple

import omni.asset_validator
import usdex.core
import usdex.test
from pxr import Gf, Tf, Usd, UsdGeom, UsdPhysics


class PhysicsJointAlgoTest(usdex.test.TestCase):
    # Create a cube with the given parameters.
    def createCube(self, stage: Usd.Stage, primPath: str, size: float, color: Gf.Vec3f, position: Gf.Vec3d, rotation: Gf.Vec3f, scale: Gf.Vec3f):
        cubeGeom = UsdGeom.Cube.Define(stage, primPath)
        cubeGeom.CreateSizeAttr(size)
        cubeGeom.CreateDisplayColorAttr([color])
        prim = cubeGeom.GetPrim()
        usdex.core.setLocalTransform(prim, Gf.Vec3d(position), Gf.Vec3d(0, 0, 0), rotation, usdex.core.RotationOrder.eXyz, scale)
        return prim

    # Create a capsule with the given parameters.
    def createCapsule(
        self, stage: Usd.Stage, primPath: str, radius: float, height: float, axis: str, color: Gf.Vec3f, position: Gf.Vec3d, rotation: Gf.Vec3f
    ):
        capsuleGeom = UsdGeom.Capsule.Define(stage, primPath)
        capsuleGeom.CreateRadiusAttr(radius)
        capsuleGeom.CreateHeightAttr(height)
        capsuleGeom.CreateAxisAttr(axis)
        capsuleGeom.CreateDisplayColorAttr([color])
        prim = capsuleGeom.GetPrim()
        usdex.core.setLocalTransform(prim, Gf.Vec3d(position), Gf.Vec3d(0, 0, 0), rotation, usdex.core.RotationOrder.eXyz, Gf.Vec3f(1.0, 1.0, 1.0))
        return prim

    # Create a cylinder with the given parameters.
    def createCylinder(
        self, stage: Usd.Stage, primPath: str, radius: float, height: float, axis: str, color: Gf.Vec3f, position: Gf.Vec3d, rotation: Gf.Vec3f
    ):
        cylinderGeom = UsdGeom.Cylinder.Define(stage, primPath)
        cylinderGeom.CreateRadiusAttr(radius)
        cylinderGeom.CreateHeightAttr(height)
        cylinderGeom.CreateAxisAttr(axis)
        cylinderGeom.CreateDisplayColorAttr([color])
        prim = cylinderGeom.GetPrim()
        usdex.core.setLocalTransform(prim, Gf.Vec3d(position), Gf.Vec3d(0, 0, 0), rotation, usdex.core.RotationOrder.eXyz, Gf.Vec3f(1.0, 1.0, 1.0))
        return prim

    # Create a xform with the given parameters.
    def createXform(self, stage: Usd.Stage, primPath: str, position: Gf.Vec3d, rotation: Gf.Vec3f, scale: Gf.Vec3f):
        xform = usdex.core.defineXform(stage, primPath)
        prim = xform.GetPrim()
        usdex.core.setLocalTransform(prim, Gf.Vec3d(position), Gf.Vec3d(0, 0, 0), rotation, usdex.core.RotationOrder.eXyz, scale)
        return prim

    # Override createTestStage for testing purposes for PhysicsJoint.
    def overrideCreateTestStage(self, stage: Usd.Stage) -> Tuple[Usd.Prim, Usd.Prim, usdex.core.JointFrame]:
        defaultPrim = stage.GetDefaultPrim()
        xform_path = f"{defaultPrim.GetPath()}/xform"
        self.createXform(stage, xform_path, Gf.Vec3d(0, 0, 0), Gf.Vec3f(0, 0, 0), Gf.Vec3f(1, 1, 1))

        # Create body0 and body1 to be used for testing.
        cube0_path = f"{xform_path}/cube0"
        translation = Gf.Vec3d(0.0, 30.0, 0.0)
        rotationXYZ = Gf.Vec3f(0, 0, 0)
        scale = Gf.Vec3f(2.0, 0.5, 0.5)
        body0 = self.createCube(stage, cube0_path, 10.0, Gf.Vec3f(0.0, 1.0, 0.0), translation, rotationXYZ, scale)

        cube1_path = f"{xform_path}/cube1"
        translation = Gf.Vec3d(21.0, 30.0, 0.0)
        rotationXYZ = Gf.Vec3f(0, 0, 0)
        scale = Gf.Vec3f(2.0, 0.5, 0.5)
        body1 = self.createCube(stage, cube1_path, 10.0, Gf.Vec3f(0.0, 0.0, 1.0), translation, rotationXYZ, scale)

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(body0)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(body0)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(body1)
        UsdPhysics.RigidBodyAPI.Apply(body1)

        # Calculate the midpoint of body0 and body1 in world coordinates.
        xform_cache = UsdGeom.XformCache()
        cube0_worldTransform = xform_cache.GetLocalToWorldTransform(body0)
        cube1_worldTransform = xform_cache.GetLocalToWorldTransform(body1)
        cube0_worldPosition = cube0_worldTransform.ExtractTranslation()
        cube1_worldPosition = cube1_worldTransform.ExtractTranslation()
        joint_position = (cube0_worldPosition + cube1_worldPosition) / 2.0
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.World, joint_position, Gf.Quatd.GetIdentity())

        return [body0, body1, jointFrame]

    # Check the physics joint parameters.
    def assertIsPhysicsJoint(
        self,
        joint: UsdPhysics.Joint,
        localPos0: Gf.Vec3f,
        localRot0: Gf.Quatf,
        localPos1: Gf.Vec3f,
        localRot1: Gf.Quatf,
        axis: str = None,
        lower_limit: float = None,
        upper_limit: float = None,
        coneAngle0Limit: float = None,
        coneAngle1Limit: float = None,
    ):
        self.assertTrue(joint.GetLocalPos0Attr().HasAuthoredValue())
        self.assertTrue(joint.GetLocalRot0Attr().HasAuthoredValue())
        self.assertTrue(joint.GetLocalPos1Attr().HasAuthoredValue())
        self.assertTrue(joint.GetLocalRot1Attr().HasAuthoredValue())

        _localPos0: Gf.Vec3f = joint.GetLocalPos0Attr().Get()
        _localRot0: Gf.Quatf = joint.GetLocalRot0Attr().Get()
        _localPos1: Gf.Vec3f = joint.GetLocalPos1Attr().Get()
        _localRot1: Gf.Quatf = joint.GetLocalRot1Attr().Get()

        self.assertTrue(Gf.IsClose(_localPos0, localPos0, 1e-6))
        self.assertTrue(Gf.IsClose(_localPos1, localPos1, 1e-6))
        self.assertAlmostEqual(_localRot0.GetReal(), localRot0.GetReal(), places=6)
        self.assertTrue(Gf.IsClose(_localRot0.GetImaginary(), localRot0.GetImaginary(), 1e-6))
        self.assertAlmostEqual(_localRot1.GetReal(), localRot1.GetReal(), places=6)
        self.assertTrue(Gf.IsClose(_localRot1.GetImaginary(), localRot1.GetImaginary(), 1e-6))

        prim = joint.GetPrim()
        if prim.IsA(UsdPhysics.RevoluteJoint) or prim.IsA(UsdPhysics.PrismaticJoint) or prim.IsA(UsdPhysics.SphericalJoint):
            if axis is not None:
                self.assertTrue(joint.GetAxisAttr().HasAuthoredValue())
                self.assertEqual(joint.GetAxisAttr().Get(), axis)
            else:
                self.assertFalse(joint.GetAxisAttr().HasAuthoredValue())

        if prim.IsA(UsdPhysics.RevoluteJoint) or prim.IsA(UsdPhysics.PrismaticJoint):
            if lower_limit is not None:
                self.assertTrue(joint.GetLowerLimitAttr().HasAuthoredValue())
                self.assertAlmostEqual(joint.GetLowerLimitAttr().Get(), lower_limit, places=4)
            else:
                self.assertFalse(joint.GetLowerLimitAttr().HasAuthoredValue())

            if upper_limit is not None:
                self.assertTrue(joint.GetUpperLimitAttr().HasAuthoredValue())
                self.assertAlmostEqual(joint.GetUpperLimitAttr().Get(), upper_limit, places=4)
            else:
                self.assertFalse(joint.GetUpperLimitAttr().HasAuthoredValue())

        if prim.IsA(UsdPhysics.SphericalJoint):
            if coneAngle0Limit is not None:
                self.assertTrue(joint.GetConeAngle0LimitAttr().HasAuthoredValue())
                self.assertAlmostEqual(joint.GetConeAngle0LimitAttr().Get(), coneAngle0Limit, places=4)
            else:
                self.assertFalse(joint.GetConeAngle0LimitAttr().HasAuthoredValue())

            if coneAngle1Limit is not None:
                self.assertTrue(joint.GetConeAngle1LimitAttr().HasAuthoredValue())
                self.assertAlmostEqual(joint.GetConeAngle1LimitAttr().Get(), coneAngle1Limit, places=4)
            else:
                self.assertFalse(joint.GetConeAngle1LimitAttr().HasAuthoredValue())


class PhysicsJointAlgoTest_FixedJoint(PhysicsJointAlgoTest, usdex.test.DefineFunctionTestCase):
    defineFunc = usdex.core.definePhysicsFixedJoint
    requiredArgs = tuple([Usd.Prim(), Usd.Prim(), usdex.core.JointFrame()])
    typeName = "PhysicsFixedJoint"
    schema = UsdPhysics.FixedJoint
    requiredPropertyNames = []

    # Override createTestStage for testing purposes for PhysicsJoint.
    def createTestStage(self):
        stage = super().createTestStage()
        body0, body1, jointFrame = self.overrideCreateTestStage(stage)

        # Replaces requiredArgs.
        self.requiredArgs = tuple([body0, body1, jointFrame])

        return stage

    # Test the physics fixed joint simple.
    def testPhysicsFixedJoint_simple(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create cube0.
        cube0_path = f"/{self.defaultPrimName}/cube0"
        translation = Gf.Vec3d(0.0, 30.0, 0.0)
        rotationXYZ = Gf.Vec3f(0, 0, 0)
        scale = Gf.Vec3f(2.0, 0.5, 0.5)
        self.createCube(stage, cube0_path, 10.0, Gf.Vec3f(0.0, 1.0, 0.0), translation, rotationXYZ, scale)

        # Create cube1.
        cube1_path = f"/{self.defaultPrimName}/cube1"
        translation = Gf.Vec3d(21.0, 30.0, 0.0)
        rotationXYZ = Gf.Vec3f(0, 0, 0)
        scale = Gf.Vec3f(2.0, 0.5, 0.5)
        self.createCube(stage, cube1_path, 10.0, Gf.Vec3f(0.0, 0.0, 1.0), translation, rotationXYZ, scale)

        # cube0 : rigid body + collider (kinematic)
        cube0_prim = stage.GetPrimAtPath(cube0_path)
        UsdPhysics.CollisionAPI.Apply(cube0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(cube0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        # cube1 : rigid body + collider
        cube1_prim = stage.GetPrimAtPath(cube1_path)
        UsdPhysics.CollisionAPI.Apply(cube1_prim)
        UsdPhysics.RigidBodyAPI.Apply(cube1_prim)

        # Calculate the midpoint of cube0 and cube1 in world coordinates.
        xform_cache = UsdGeom.XformCache()
        cube0_worldTransform = xform_cache.GetLocalToWorldTransform(cube0_prim)
        cube1_worldTransform = xform_cache.GetLocalToWorldTransform(cube1_prim)
        cube0_worldPosition = cube0_worldTransform.ExtractTranslation()
        cube1_worldPosition = cube1_worldTransform.ExtractTranslation()
        joint_position = (cube0_worldPosition + cube1_worldPosition) / 2.0

        # Create a fixed joint.
        # Here, the position and rotation in world coordinates are specified as the center of the joint.
        joint_path = f"/{self.defaultPrimName}/fixed_joint"
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.World, joint_position, Gf.Quatd.GetIdentity())
        joint = usdex.core.definePhysicsFixedJoint(stage, joint_path, cube0_prim, cube1_prim, jointFrame)
        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(5.25, 0.0, 0.0)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(-5.25, 0.0, 0.0)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1)

    # Test the physics fixed joint with xform.
    # Place an Xform with position and rotation, and place Physics joint body0 and body1 inside it.
    def testPhysicsFixedJoint_with_xform(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xform_path = f"/{self.defaultPrimName}/xform"
        xform_position = Gf.Vec3d(0.0, 80.0, 0.0)
        xform_rotation = Gf.Vec3f(0.0, 40.0, 0.0)
        xform_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        xformPrim = self.createXform(stage, xform_path, xform_position, xform_rotation, xform_scale)

        # Create cube0.
        cube0_path = f"{xform_path}/cube0"
        translation = Gf.Vec3d(0.0, 30.0, 0.0)
        rotationXYZ = Gf.Vec3f(0, 0, 0)
        scale = Gf.Vec3f(2.0, 0.5, 0.5)
        self.createCube(stage, cube0_path, 10.0, Gf.Vec3f(0.0, 1.0, 0.0), translation, rotationXYZ, scale)

        # Create cube1.
        cube1_path = f"{xform_path}/cube1"
        translation = Gf.Vec3d(21.0, 30.0, 0.0)
        rotationXYZ = Gf.Vec3f(0, 0, 0)
        scale = Gf.Vec3f(2.0, 0.5, 0.5)
        self.createCube(stage, cube1_path, 10.0, Gf.Vec3f(0.0, 0.0, 1.0), translation, rotationXYZ, scale)

        # cube0 : rigid body + collider (kinematic)
        cube0_prim = stage.GetPrimAtPath(cube0_path)
        UsdPhysics.CollisionAPI.Apply(cube0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(cube0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        # cube1 : rigid body + collider
        cube1_prim = stage.GetPrimAtPath(cube1_path)
        UsdPhysics.CollisionAPI.Apply(cube1_prim)
        UsdPhysics.RigidBodyAPI.Apply(cube1_prim)

        # Calculate the midpoint of cube0 and cube1 in world coordinates.
        xform_cache = UsdGeom.XformCache()
        cube0_worldTransform = xform_cache.GetLocalToWorldTransform(cube0_prim)
        cube1_worldTransform = xform_cache.GetLocalToWorldTransform(cube1_prim)
        cube0_worldPosition = cube0_worldTransform.ExtractTranslation()
        cube1_worldPosition = cube1_worldTransform.ExtractTranslation()
        joint_position = (cube0_worldPosition + cube1_worldPosition) / 2.0

        xformMatrix = usdex.core.getLocalTransformMatrix(xformPrim)

        joint_orientation = xformMatrix.RemoveScaleShear().ExtractRotation().GetQuat()
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.World, joint_position, joint_orientation)

        # Create a fixed joint under the root.
        # Here, the position and rotation in world coordinates are specified as the center of the joint.
        joint_name = "fixed_joint"
        rootPrim = stage.GetPrimAtPath(f"/{self.defaultPrimName}")
        joint = usdex.core.definePhysicsFixedJoint(rootPrim, joint_name, cube0_prim, cube1_prim, jointFrame)
        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(5.25, 0.0, 0.0)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(-5.25, 0.0, 0.0)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1)

    # Test the physics fixed joint with xform.
    # Creating a joint when the hierarchical structure contains body0 and body1.
    # In addition, rotation and scaling of Xform are specified,
    # which causes an 'ScaleOrientation is not supported for rigid bodies.' error.
    def testPhysicsFixedJoint_with_xform_complexHierarchy_scaleOrientation(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xform_path = f"/{self.defaultPrimName}/Xform"
        xform_position = Gf.Vec3d(0.0, 80.0, 0.0)
        xform_rotation = Gf.Vec3f(10.0, 20.0, 0.0)
        xform_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        xform_prim = self.createXform(stage, xform_path, xform_position, xform_rotation, xform_scale)

        xform1_path = f"/{self.defaultPrimName}/Xform1"
        xform1_position = Gf.Vec3d(-69.67, 43.42, 0.0)
        xform1_rotation = Gf.Vec3f(30.0, 0.0, 0.0)
        xform1_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        self.createXform(stage, xform1_path, xform1_position, xform1_rotation, xform1_scale)

        xform1_2_path = f"{xform1_path}/Xform1_2"
        xform1_2_position = Gf.Vec3d(0.0, 7.38, -34.35)
        xform1_2_rotation = Gf.Vec3f(0.0, -50.0, 0.0)
        xform1_2_scale = Gf.Vec3f(0.5, 0.5, 0.5)
        self.createXform(stage, xform1_2_path, xform1_2_position, xform1_2_rotation, xform1_2_scale)

        # Create cube0.
        cube0_path = f"{xform1_path}/cube0"
        translation = Gf.Vec3d(164.79, 53.42, 12.91)
        rotationXYZ = Gf.Vec3f(-37.0, 33.82, -22.76)
        scale = Gf.Vec3f(2.0, 0.5, 0.5)
        self.createCube(stage, cube0_path, 10.0, Gf.Vec3f(0.0, 1.0, 0.0), translation, rotationXYZ, scale)

        # Create cube1.
        cube1_path = f"{xform1_2_path}/cube1"
        translation = Gf.Vec3d(287.05, 78.59, -231.38)
        rotationXYZ = Gf.Vec3f(-101.6, 70.84, -78.4)
        scale = Gf.Vec3f(4.0, 1.0, 1.0)
        self.createCube(stage, cube1_path, 10.0, Gf.Vec3f(0.0, 0.0, 1.0), translation, rotationXYZ, scale)

        # cube0 : rigid body + collider (kinematic)
        cube0_prim = stage.GetPrimAtPath(cube0_path)
        UsdPhysics.CollisionAPI.Apply(cube0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(cube0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        # cube1 : rigid body + collider
        cube1_prim = stage.GetPrimAtPath(cube1_path)
        UsdPhysics.CollisionAPI.Apply(cube1_prim)
        UsdPhysics.RigidBodyAPI.Apply(cube1_prim)

        # Calculate the midpoint of cube0 and cube1 in world coordinates.
        xform_cache = UsdGeom.XformCache()
        cube0_worldTransform = xform_cache.GetLocalToWorldTransform(cube0_prim)
        cube1_worldTransform = xform_cache.GetLocalToWorldTransform(cube1_prim)
        cube0_worldPosition = cube0_worldTransform.ExtractTranslation()
        cube1_worldPosition = cube1_worldTransform.ExtractTranslation()
        joint_position = (cube0_worldPosition + cube1_worldPosition) / 2.0

        # Get the local position of the joint in the cube0's coordinate system.
        cube0_worldTransform = UsdGeom.XformCache().GetLocalToWorldTransform(cube0_prim)
        lPos = cube0_worldTransform.GetInverse().Transform(joint_position)

        joint_local_position = lPos
        joint_local_orientation = Gf.Quatd.GetIdentity()
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body0, joint_local_position, joint_local_orientation)

        # Create a fixed joint under the "xform".
        joint_name = "fixed_joint"
        joint = usdex.core.definePhysicsFixedJoint(xform_prim, joint_name, cube0_prim, cube1_prim, jointFrame)
        self.assertTrue(joint)

        # cube0, cube1:'ScaleOrientation is not supported for rigid bodies.'
        # This warning will be skipped during USD validation.
        self.assertIsValidUsd(
            stage,
            issuePredicates=[
                omni.asset_validator.IssuePredicates.ContainsMessage("ScaleOrientation is not supported for rigid bodies."),
            ],
        )

        # Check the joint parameters.
        # The error is a bit larger because of the scale and shear factors.
        # Here we compare the actual values after calculation.
        localPos0 = Gf.Vec3f(5.2484603, -0.0013820197, 0.009961868)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(-5.2484603, 0.00008684622, -0.0122021055)
        localRot1 = Gf.Quatf(1, 0.000045843633, -0.000053343734, 0.000030884887)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1)


class PhysicsJointAlgoTest_RevoluteJoint(PhysicsJointAlgoTest, usdex.test.DefineFunctionTestCase):
    defineFunc = usdex.core.definePhysicsRevoluteJoint
    requiredArgs = tuple([Usd.Prim(), Usd.Prim(), usdex.core.JointFrame(), Gf.Vec3f(1.0, 0.0, 0.0)])
    typeName = "PhysicsRevoluteJoint"
    schema = UsdPhysics.RevoluteJoint
    requiredPropertyNames = []

    # Override createTestStage for testing purposes for PhysicsJoint.
    def createTestStage(self):
        stage = super().createTestStage()
        body0, body1, jointFrame = self.overrideCreateTestStage(stage)

        # Replaces requiredArgs.
        axis = Gf.Vec3f(1.0, 0.0, 0.0)
        self.requiredArgs = tuple([body0, body1, jointFrame, axis])

        return stage

    # Test the physics revolute joint simple.
    def testPhysicsRevoluteJoint_simple(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create capsules.
        # The capsules are aligned along the Z axis.
        capsule0_path = f"/{self.defaultPrimName}/capsule0"
        capsule1_path = f"/{self.defaultPrimName}/capsule1"
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z
        capsule_margin = 1.0

        pz = 0.0
        capsule_translation = Gf.Vec3d(0.0, 0.0, pz)
        capsule_rotationXYZ = Gf.Vec3f(0, 0, 0)
        capsule0_prim = self.createCapsule(
            stage, capsule0_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        pz += capsule_height + capsule_radius * 2.0 + capsule_margin
        capsule_translation = Gf.Vec3d(0.0, 0.0, pz)
        capsule1_prim = self.createCapsule(
            stage, capsule1_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(capsule0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(capsule0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(capsule1_prim)
        UsdPhysics.RigidBodyAPI.Apply(capsule1_prim)

        # Create a revolute joint.
        axis = Gf.Vec3f(1.0, 0.0, 0.0)
        lower_limit = -20.0
        upper_limit = 35.0

        xform_cache = UsdGeom.XformCache()
        capsule0_worldTransform = xform_cache.GetLocalToWorldTransform(capsule0_prim)
        capsule1_worldTransform = xform_cache.GetLocalToWorldTransform(capsule1_prim)
        capsule0_worldPosition = capsule0_worldTransform.ExtractTranslation()
        capsule1_worldPosition = capsule1_worldTransform.ExtractTranslation()
        joint_position = (capsule0_worldPosition + capsule1_worldPosition) / 2.0
        joint_orientation = Gf.Quatd.GetIdentity()
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.World, joint_position, joint_orientation)

        joint_path = f"/{self.defaultPrimName}/revolute_joint"
        joint = usdex.core.definePhysicsRevoluteJoint(stage, joint_path, capsule0_prim, capsule1_prim, jointFrame, axis, lower_limit, upper_limit)

        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(0, 0, 5.5)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0, 0, -5.5)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, lower_limit, upper_limit)

        # Change parameters.
        axis = Gf.Vec3f(-1.0, 0.0, 0.0)
        lower_limit = -40.0
        upper_limit = 15.0
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, Gf.Vec3d(0, 0, -5.75), joint_orientation)
        usdex.core.alignPhysicsJoint(joint, jointFrame, axis)
        joint.GetLowerLimitAttr().Set(lower_limit)
        joint.GetUpperLimitAttr().Set(upper_limit)
        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(0, 0, 5.25)
        localRot0 = Gf.Quatf(0, 0, -1, 0)
        localPos1 = Gf.Vec3f(0, 0, -5.75)
        localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, lower_limit, upper_limit)

    # Test the physics revolute joint with xform.
    def testPhysicsRevoluteJoint_with_xform(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xform_path = f"/{self.defaultPrimName}/xform"
        xform_position = Gf.Vec3d(0.0, 20.0, 0.0)
        xform_rotation = Gf.Vec3f(0.0, 40.0, 0.0)
        xform_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        self.createXform(stage, xform_path, xform_position, xform_rotation, xform_scale)

        # Create capsules.
        # The capsules are aligned along the Z axis.
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z
        capsule_margin = 1.0
        pz = 0.0
        capsule_count = 4
        for i in range(capsule_count):
            capsule_path = f"{xform_path}/capsule{i}"
            capsule_translation = Gf.Vec3d(0.0, 30.0, pz)
            capsule_rotationXYZ = Gf.Vec3f(0, 0, 0)
            capsulePrim = self.createCapsule(
                stage, capsule_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
            )
            pz += capsule_height + capsule_radius * 2.0 + capsule_margin

            # Apply collision and rigidbody.
            UsdPhysics.CollisionAPI.Apply(capsulePrim)
            rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(capsulePrim)
            if i == 0:
                rigidbodyAPI.CreateKinematicEnabledAttr(True)

        # Create Xform.
        xform_joints_path = f"/{self.defaultPrimName}/joints"
        xform_position = Gf.Vec3d(-20.0, 30.0, 0.0)
        xform_rotation = Gf.Vec3f(0.0, 0.0, 0.0)
        xform_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        xform_joints_prim = self.createXform(stage, xform_joints_path, xform_position, xform_rotation, xform_scale)

        # Create revolute joints.
        xform_cache = UsdGeom.XformCache()
        for i in range(capsule_count - 1):
            # Get the world position of the joint.
            capsule0_path = f"{xform_path}/capsule{i}"
            capsule1_path = f"{xform_path}/capsule{i+1}"
            capsule0_prim = stage.GetPrimAtPath(capsule0_path)
            capsule1_prim = stage.GetPrimAtPath(capsule1_path)
            capsule0_worldTransform = xform_cache.GetLocalToWorldTransform(capsule0_prim)
            capsule1_worldTransform = xform_cache.GetLocalToWorldTransform(capsule1_prim)
            capsule0_worldPosition = capsule0_worldTransform.ExtractTranslation()
            capsule1_worldPosition = capsule1_worldTransform.ExtractTranslation()
            joint_position = (capsule0_worldPosition + capsule1_worldPosition) / 2.0

            # Get the local position of the joint in the capsule0_prim's coordinate system.
            lPos = capsule0_worldTransform.GetInverse().Transform(joint_position)
            jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body0, lPos, Gf.Quatd.GetIdentity())

            axis = Gf.Vec3f(1.0, 0.0, 0.0)
            lower_limit = -20.0
            upper_limit = 35.0

            # Create a revolute joint.
            joint_name = f"revolute_joint_{i}"
            joint = usdex.core.definePhysicsRevoluteJoint(
                xform_joints_prim, joint_name, capsule0_prim, capsule1_prim, jointFrame, axis, lower_limit, upper_limit
            )
            self.assertTrue(joint)

            # Check the joint parameters.
            localPos0 = Gf.Vec3f(0, 0, 5.5)
            localRot0 = Gf.Quatf.GetIdentity()
            localPos1 = Gf.Vec3f(0, 0, -5.5)
            localRot1 = Gf.Quatf.GetIdentity()
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, lower_limit, upper_limit)

        self.assertIsValidUsd(stage)

    # Test the physics revolute joint with car wheels.
    # This is a test of the four revolute joints, which can rotate without any angle restrictions.
    def testPhysicsRevoluteJoint_car_wheels(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Tilted board
        cube0_path = f"/{self.defaultPrimName}/board"
        translation = Gf.Vec3d(0.0, 5.0, 0.0)
        rotationXYZ = Gf.Vec3f(0, 0, -15)
        scale = Gf.Vec3f(1.5, 0.08, 1.0)
        board = self.createCube(stage, cube0_path, 10.0, Gf.Vec3f(0.8, 0.8, 0.8), translation, rotationXYZ, scale)
        UsdPhysics.CollisionAPI.Apply(board)

        xform_car_path = f"/{self.defaultPrimName}/car"
        xform_position = Gf.Vec3d(0.0, 0.0, 0.0)
        xform_rotation = Gf.Vec3f(0, 0, 0)
        xform_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        self.createXform(stage, xform_car_path, xform_position, xform_rotation, xform_scale)

        xform_joints_path = f"{xform_car_path}/joints"
        xform_joints_prim = self.createXform(stage, xform_joints_path, xform_position, xform_rotation, xform_scale)

        # Car body
        cube1_path = f"{xform_car_path}/body"
        translation = Gf.Vec3d(-4.0, 12.0, 0.0)
        rotationXYZ = Gf.Vec3f(0, 0, 0)
        scale = Gf.Vec3f(0.4, 0.2, 0.3)
        car_body_prim = self.createCube(stage, cube1_path, 10.0, Gf.Vec3f(0.0, 1.0, 0.0), translation, rotationXYZ, scale)
        UsdPhysics.CollisionAPI.Apply(car_body_prim)
        UsdPhysics.RigidBodyAPI.Apply(car_body_prim)

        # Car wheels
        rotationXYZ = Gf.Vec3f(0, 0, 0)
        scale = Gf.Vec3f(1, 1, 1)
        cylinder_radius = 1.0
        cylinder_height = 0.5
        cylinder_axis = UsdGeom.Tokens.z

        wheel0_path = f"{xform_car_path}/wheel_back_right"
        wheel0_translation = Gf.Vec3d(-5.3, 11.3, 1.92)
        wheel0_prim = self.createCylinder(
            stage, wheel0_path, cylinder_radius, cylinder_height, cylinder_axis, Gf.Vec3f(0.0, 0.0, 1.0), wheel0_translation, rotationXYZ
        )
        UsdPhysics.CollisionAPI.Apply(wheel0_prim)
        UsdPhysics.RigidBodyAPI.Apply(wheel0_prim)

        wheel1_path = f"{xform_car_path}/wheel_back_left"
        wheel1_translation = Gf.Vec3d(-5.3, 11.3, -1.92)
        wheel1_prim = self.createCylinder(
            stage, wheel1_path, cylinder_radius, cylinder_height, cylinder_axis, Gf.Vec3f(0.0, 0.0, 1.0), wheel1_translation, rotationXYZ
        )
        UsdPhysics.CollisionAPI.Apply(wheel1_prim)
        UsdPhysics.RigidBodyAPI.Apply(wheel1_prim)

        wheel2_path = f"{xform_car_path}/wheel_front_right"
        wheel2_translation = Gf.Vec3d(-2.64, 11.3, 1.92)
        wheel2_prim = self.createCylinder(
            stage, wheel2_path, cylinder_radius, cylinder_height, cylinder_axis, Gf.Vec3f(0.0, 0.0, 1.0), wheel2_translation, rotationXYZ
        )
        UsdPhysics.CollisionAPI.Apply(wheel2_prim)
        UsdPhysics.RigidBodyAPI.Apply(wheel2_prim)

        wheel3_path = f"{xform_car_path}/wheel_front_left"
        wheel3_translation = Gf.Vec3d(-2.64, 11.3, -1.92)
        wheel3_prim = self.createCylinder(
            stage, wheel3_path, cylinder_radius, cylinder_height, cylinder_axis, Gf.Vec3f(0.0, 0.0, 1.0), wheel3_translation, rotationXYZ
        )
        UsdPhysics.CollisionAPI.Apply(wheel3_prim)
        UsdPhysics.RigidBodyAPI.Apply(wheel3_prim)

        # Revolute joint for car wheels.
        # This does not impose any angle restrictions.
        axis = Gf.Vec3f(0.0, 0.0, 1.0)

        joint_position = Gf.Vec3d(0.0, 0.0, -cylinder_height * 0.5)
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, joint_position, Gf.Quatd.GetIdentity())
        joint_name = "revolute_joint_0"
        joint = usdex.core.definePhysicsRevoluteJoint(xform_joints_prim, joint_name, car_body_prim, wheel0_prim, jointFrame, axis)
        self.assertTrue(joint)

        localPos0 = Gf.Vec3f(-3.25, -3.5, 5.566666)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0.0, 0.0, -0.25)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z)

        joint_position = Gf.Vec3d(0.0, 0.0, cylinder_height * 0.5)
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, joint_position, Gf.Quatd.GetIdentity())
        joint_name = "revolute_joint_1"
        joint = usdex.core.definePhysicsRevoluteJoint(xform_joints_prim, joint_name, car_body_prim, wheel1_prim, jointFrame, axis)
        self.assertTrue(joint)

        localPos0 = Gf.Vec3f(-3.25, -3.5, -5.566666)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0.0, 0.0, 0.25)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z)

        joint_position = Gf.Vec3d(0.0, 0.0, -cylinder_height * 0.5)
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, joint_position, Gf.Quatd.GetIdentity())
        joint_name = "revolute_joint_2"
        joint = usdex.core.definePhysicsRevoluteJoint(xform_joints_prim, joint_name, car_body_prim, wheel2_prim, jointFrame, axis)
        self.assertTrue(joint)

        localPos0 = Gf.Vec3f(3.4, -3.5, 5.566666)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0.0, 0.0, -0.25)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z)

        joint_position = Gf.Vec3d(0.0, 0.0, cylinder_height * 0.5)
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, joint_position, Gf.Quatd.GetIdentity())
        joint_name = "revolute_joint_3"
        joint = usdex.core.definePhysicsRevoluteJoint(xform_joints_prim, joint_name, car_body_prim, wheel3_prim, jointFrame, axis)
        self.assertTrue(joint)

        localPos0 = Gf.Vec3f(3.4, -3.5, -5.566666)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0.0, 0.0, 0.25)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z)

        self.assertIsValidUsd(stage)

    # Create two capsules.
    # The two capsules are placed inside the Xform.
    def _create_two_capsules(self, stage: Usd.Stage, xform_path: str, xform_position: Gf.Vec3d, xform_rotation: Gf.Vec3f) -> List[Usd.Prim]:
        # Create Xform.
        xform_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        self.createXform(stage, xform_path, xform_position, xform_rotation, xform_scale)

        capsule0_path = f"{xform_path}/capsule0"
        capsule1_path = f"{xform_path}/capsule1"
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z

        capsule_translation = Gf.Vec3d(0.0, 8.0, 0.0)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule0_prim = self.createCapsule(
            stage, capsule0_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        capsule_translation = Gf.Vec3d(0.0, 5.24, 10.65)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule1_prim = self.createCapsule(
            stage, capsule1_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 0.0, 1.0), capsule_translation, capsule_rotationXYZ
        )

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(capsule0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(capsule0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(capsule1_prim)
        UsdPhysics.RigidBodyAPI.Apply(capsule1_prim)

        return [capsule0_prim, capsule1_prim]

    # Create two capsules and a RevoluteJoint by specifying the axis.
    def create_revolute_joint_with_capsules(
        self,
        stage: Usd.Stage,
        parent_prim_path: str,
        name: str,
        position: Gf.Vec3f,
        joint_position: Gf.Vec3d,
        joint_orientation: Gf.Quatd,
        joint_axis: Gf.Vec3f,
        joint_lower_limit: float,
        joint_upper_limit: float,
    ):
        xform_path = f"{parent_prim_path}/{name}"
        capsules = self._create_two_capsules(stage, xform_path, position, Gf.Vec3f(0.0, 0.0, 0.0))
        xform_prim = stage.GetPrimAtPath(xform_path)
        self.assertTrue(xform_prim)
        self.assertTrue(capsules[0])
        self.assertTrue(capsules[1])

        joint_name = "revolute_joint"
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body0, joint_position, joint_orientation)
        joint = usdex.core.definePhysicsRevoluteJoint(
            xform_prim, joint_name, capsules[0], capsules[1], jointFrame, joint_axis, joint_lower_limit, joint_upper_limit
        )
        self.assertTrue(joint)
        return joint

    # Testing joint rotation axis -X, -Y, -Z
    # Comparison of axis +X, +Y, +Z and -X, -Y, -Z.
    def testPhysicsRevolutelJoint_positive_and_negative_axis(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        positive_axis_xform_path = f"/{self.defaultPrimName}/positive_axis"
        self.createXform(stage, positive_axis_xform_path, Gf.Vec3d(0.0, 0.0, 0.0), Gf.Vec3f(0.0, 20.0, 5.0), Gf.Vec3f(1.0, 1.0, 1.0))

        negative_axis_xform_path = f"/{self.defaultPrimName}/negative_axis"
        self.createXform(stage, negative_axis_xform_path, Gf.Vec3d(0.0, 0.0, 25.0), Gf.Vec3f(0.0, 20.0, 5.0), Gf.Vec3f(1.0, 1.0, 1.0))

        # ------------------------------------------------------------.
        # Test positive axis.
        # ------------------------------------------------------------.
        # The joint connecting the two capsules has an axis of (1, 0, 0).
        # joint_lower_limit -20.0, joint_upper_limit 40.0.
        name = "xform_angle_positive_axis_x_limit"
        position = Gf.Vec3d(0.0, 30.0, 0.0)
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)
        joint_orientation = Gf.Quatd.GetIdentity()
        joint_axis = Gf.Vec3f(1.0, 0.0, 0.0)
        joint_lower_limit = -20.0
        joint_upper_limit = 40.0
        joint = self.create_revolute_joint_with_capsules(
            stage, positive_axis_xform_path, name, position, joint_position, joint_orientation, joint_axis, joint_lower_limit, joint_upper_limit
        )

        localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
        localRot0 = Gf.Quatf(1, 0, 0, 0)
        localPos1 = Gf.Vec3f(0.0, 0.0055400045, -5.501821)
        localRot1 = Gf.Quatf(1, 0, 0, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, joint_lower_limit, joint_upper_limit)

        # The joint connecting the two capsules has an axis of (0, 1, 0).
        # joint_lower_limit -20.0, joint_upper_limit 40.0.
        name = "xform_angle_positive_axis_y_limit"
        position = Gf.Vec3d(10.0, 30.0, 0.0)
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)
        joint_orientation = Gf.Quatd.GetIdentity()
        joint_axis = Gf.Vec3f(0.0, 1.0, 0.0)
        joint = self.create_revolute_joint_with_capsules(
            stage, positive_axis_xform_path, name, position, joint_position, joint_orientation, joint_axis, joint_lower_limit, joint_upper_limit
        )

        localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
        localRot0 = Gf.Quatf(1, 0, 0, 0)
        localPos1 = Gf.Vec3f(0.0, 0.0055400045, -5.501821)
        localRot1 = Gf.Quatf(1, 0, 0, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.y, joint_lower_limit, joint_upper_limit)

        # The joint connecting the two capsules has an axis of (0, 0, 1).
        # joint_lower_limit -20.0, joint_upper_limit 40.0.
        name = "xform_angle_positive_axis_z_limit"
        position = Gf.Vec3d(20.0, 30.0, 0.0)
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)

        # In the case of this capsule, the local axis direction is Z. So we rotate it so that the X axis is the axial direction.
        joint_orientation = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), Gf.Vec3d(1.0, 0.0, 0.0)).GetQuat()

        joint_axis = Gf.Vec3f(0.0, 0.0, 1.0)
        joint = self.create_revolute_joint_with_capsules(
            stage, positive_axis_xform_path, name, position, joint_position, joint_orientation, joint_axis, joint_lower_limit, joint_upper_limit
        )

        localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
        localRot0 = Gf.Quatf(0.70710677, 0, 0.70710677, 0)
        localPos1 = Gf.Vec3f(0.0, 0.0055400045, -5.501821)
        localRot1 = Gf.Quatf(0.70710677, 0, 0.70710677, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z, joint_lower_limit, joint_upper_limit)

        # ------------------------------------------------------------.
        # Test negative axis.
        # ------------------------------------------------------------.
        # The joint connecting the two capsules has an axis of (-1, 0, 0).
        # joint_lower_limit -20.0, joint_upper_limit 40.0.
        name = "xform_angle_negative_axis_x_limit"
        position = Gf.Vec3d(0.0, 30.0, 0.0)
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)
        joint_orientation = Gf.Quatd.GetIdentity()
        joint_axis = Gf.Vec3f(-1.0, 0.0, 0.0)
        joint_lower_limit = -20.0
        joint_upper_limit = 40.0
        joint = self.create_revolute_joint_with_capsules(
            stage, negative_axis_xform_path, name, position, joint_position, joint_orientation, joint_axis, joint_lower_limit, joint_upper_limit
        )

        localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
        localRot0 = Gf.Quatf(0, 0, -1, 0)
        localPos1 = Gf.Vec3f(0.0, 0.0055400045, -5.501821)
        localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, joint_lower_limit, joint_upper_limit)

        # The joint connecting the two capsules has an axis of (0, -1, 0).
        # joint_lower_limit -20.0, joint_upper_limit 40.0.
        name = "xform_angle_negative_axis_y_limit"
        position = Gf.Vec3d(10.0, 30.0, 0.0)
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)
        joint_orientation = Gf.Quatd.GetIdentity()
        joint_axis = Gf.Vec3f(0.0, -1.0, 0.0)
        joint = self.create_revolute_joint_with_capsules(
            stage, negative_axis_xform_path, name, position, joint_position, joint_orientation, joint_axis, joint_lower_limit, joint_upper_limit
        )

        localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
        localRot0 = Gf.Quatf(0, -1, 0, 0)
        localPos1 = Gf.Vec3f(0.0, 0.0055400045, -5.501821)
        localRot1 = Gf.Quatf(0, -1, 0, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.y, joint_lower_limit, joint_upper_limit)

        # The joint connecting the two capsules has an axis of (0, 0, -1).
        # joint_lower_limit -20.0, joint_upper_limit 40.0.
        name = "xform_angle_negative_axis_z_limit"
        position = Gf.Vec3d(20.0, 30.0, 0.0)
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)

        # In the case of this capsule, the local axis direction is Z. So we rotate it so that the X axis is the axial direction.
        joint_orientation = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), Gf.Vec3d(1.0, 0.0, 0.0)).GetQuat()

        joint_axis = Gf.Vec3f(0.0, 0.0, -1.0)
        joint = self.create_revolute_joint_with_capsules(
            stage, negative_axis_xform_path, name, position, joint_position, joint_orientation, joint_axis, joint_lower_limit, joint_upper_limit
        )

        localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
        localRot0 = Gf.Quatf(0, -0.70710677, 0, 0.70710677)
        localPos1 = Gf.Vec3f(0.0, 0.0055400045, -5.501821)
        localRot1 = Gf.Quatf(0, -0.70710677, 0, 0.70710677)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z, joint_lower_limit, joint_upper_limit)

        # ------------------------------------------------------------.
        # axis +X, -X: Rotate localRot around the Y axis.
        # ------------------------------------------------------------.
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)
        joint_orientation = Gf.Quatd.GetIdentity()
        joint_lower_limit = -30.0
        joint_upper_limit = 60.0

        negative_axis_x_tilt_xform_path = f"/{self.defaultPrimName}/negative_axis_x_tilt"
        self.createXform(stage, negative_axis_x_tilt_xform_path, Gf.Vec3d(0.0, 0.0, 50.0), Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 1.0, 1.0))

        # joint_axis = (1, 0, 0)
        joint_axis = Gf.Vec3f(1.0, 0.0, 0.0)
        for i in range(4):
            angle = i * 10.0
            name = f"tilt_y_{i * 10}"
            position = Gf.Vec3f(i * 10.0, 30.0, 0.0)
            joint_orientation = Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), angle).GetQuat()
            joint = self.create_revolute_joint_with_capsules(
                stage,
                negative_axis_x_tilt_xform_path,
                name,
                position,
                joint_position,
                joint_orientation,
                joint_axis,
                joint_lower_limit,
                joint_upper_limit,
            )

            localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
            localRot0 = Gf.Quatf(joint_orientation)
            localPos1 = Gf.Vec3f(0.0, 0.005540, -5.501821)
            localRot1 = Gf.Quatf(joint_orientation)
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, joint_lower_limit, joint_upper_limit)

        # joint_axis = (-1, 0, 0)
        joint_axis = Gf.Vec3f(-1.0, 0.0, 0.0)
        for i in range(4):
            angle = i * 10.0
            name = f"tilt_y_negative_{i * 10}"
            position = Gf.Vec3f(i * 10.0, 30.0, 20.0)
            joint_orientation = Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), angle).GetQuat()
            joint = self.create_revolute_joint_with_capsules(
                stage,
                negative_axis_x_tilt_xform_path,
                name,
                position,
                joint_position,
                joint_orientation,
                joint_axis,
                joint_lower_limit,
                joint_upper_limit,
            )

            match i:
                case 0:
                    localRot0 = Gf.Quatf(0, 0, -1, 0)
                case 1:
                    localRot0 = Gf.Quatf(0.087155744, 0, -0.9961947, 0)
                case 2:
                    localRot0 = Gf.Quatf(0.17364818, 0, -0.9848077, 0)
                case 3:
                    localRot0 = Gf.Quatf(0.25881904, 0, -0.9659258, 0)

            localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
            localRot1 = localRot0
            localPos1 = Gf.Vec3f(0.0, 0.005540, -5.501821)
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, joint_lower_limit, joint_upper_limit)

        # ------------------------------------------------------------.
        # axis +Y, -Y: Rotate localRot around the Z axis.
        # ------------------------------------------------------------.
        negative_axis_y_tilt_xform_path = f"/{self.defaultPrimName}/negative_axis_y_tilt"
        self.createXform(stage, negative_axis_y_tilt_xform_path, Gf.Vec3d(40.0, 0.0, 50.0), Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 1.0, 1.0))

        # joint_axis = (0, 1, 0)
        joint_axis = Gf.Vec3f(0.0, 1.0, 0.0)
        for i in range(4):
            angle = i * 10.0
            name = f"tilt_z_{i * 10}"
            position = Gf.Vec3f(i * 10.0, 30.0, 0.0)
            joint_orientation = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), angle).GetQuat()
            joint = self.create_revolute_joint_with_capsules(
                stage,
                negative_axis_y_tilt_xform_path,
                name,
                position,
                joint_position,
                joint_orientation,
                joint_axis,
                joint_lower_limit,
                joint_upper_limit,
            )

            localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
            localRot0 = Gf.Quatf(joint_orientation)
            localPos1 = Gf.Vec3f(0.0, 0.005540, -5.501821)
            localRot1 = Gf.Quatf(joint_orientation)
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.y, joint_lower_limit, joint_upper_limit)

        # joint_axis = (0, -1, 0)
        joint_axis = Gf.Vec3f(0.0, -1.0, 0.0)
        for i in range(4):
            angle = i * 10.0
            name = f"tilt_z_negative_{i * 10}"
            position = Gf.Vec3f(i * 10.0, 30.0, 20.0)
            joint_orientation = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), angle).GetQuat()
            joint = self.create_revolute_joint_with_capsules(
                stage,
                negative_axis_y_tilt_xform_path,
                name,
                position,
                joint_position,
                joint_orientation,
                joint_axis,
                joint_lower_limit,
                joint_upper_limit,
            )

            match i:
                case 0:
                    localRot0 = Gf.Quatf(0, -1, 0, 0)
                case 1:
                    localRot0 = Gf.Quatf(0, -0.9961947, -0.087155744, 0)
                case 2:
                    localRot0 = Gf.Quatf(0, -0.9848077, -0.17364818, 0)
                case 3:
                    localRot0 = Gf.Quatf(0, -0.9659258, -0.25881904, 0)

            localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
            localRot1 = localRot0
            localPos1 = Gf.Vec3f(0.0, 0.005540, -5.501821)
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.y, joint_lower_limit, joint_upper_limit)

        # ------------------------------------------------------------.
        # axis +Z, -Z: Rotate localRot around the Y axis.
        # ------------------------------------------------------------.
        negative_axis_z_tilt_xform_path = f"/{self.defaultPrimName}/negative_axis_z_tilt"
        self.createXform(stage, negative_axis_z_tilt_xform_path, Gf.Vec3d(80.0, 0.0, 50.0), Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 1.0, 1.0))

        # joint_axis = (0, 0, 1)
        zToX_Rot = Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), Gf.Vec3d(1.0, 0.0, 0.0)).GetQuat()
        joint_axis = Gf.Vec3f(0.0, 0.0, 1.0)
        for i in range(4):
            angle = i * 10.0
            name = f"tilt_y_{i * 10}"
            position = Gf.Vec3f(i * 10.0, 30.0, 0.0)
            joint_orientation = Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), angle).GetQuat() * zToX_Rot
            joint = self.create_revolute_joint_with_capsules(
                stage,
                negative_axis_z_tilt_xform_path,
                name,
                position,
                joint_position,
                joint_orientation,
                joint_axis,
                joint_lower_limit,
                joint_upper_limit,
            )

            match i:
                case 0:
                    localRot0 = Gf.Quatf(0.70710677, 0, 0.70710677, 0)
                case 1:
                    localRot0 = Gf.Quatf(0.64278764, 0, 0.76604444, 0)
                case 2:
                    localRot0 = Gf.Quatf(0.5735764, 0, 0.819152, 0)
                case 3:
                    localRot0 = Gf.Quatf(0.49999997, 0, 0.8660253, 0)

            localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
            localPos1 = Gf.Vec3f(0.0, 0.005540, -5.501821)
            localRot1 = localRot0
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z, joint_lower_limit, joint_upper_limit)

        # joint_axis = (0, 0, -1)
        joint_axis = Gf.Vec3f(0.0, 0.0, -1.0)
        for i in range(4):
            angle = i * 10.0
            name = f"tilt_y_negative_{i * 10}"
            position = Gf.Vec3f(i * 10.0, 30.0, 20.0)
            joint_orientation = Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), angle).GetQuat() * zToX_Rot
            joint = self.create_revolute_joint_with_capsules(
                stage,
                negative_axis_z_tilt_xform_path,
                name,
                position,
                joint_position,
                joint_orientation,
                joint_axis,
                joint_lower_limit,
                joint_upper_limit,
            )

            match i:
                case 0:
                    localRot0 = Gf.Quatf(0, -0.70710677, 0, 0.70710677)
                case 1:
                    localRot0 = Gf.Quatf(0, -0.64278764, 0, 0.76604444)
                case 2:
                    localRot0 = Gf.Quatf(0, -0.57357645, 0, 0.819152)
                case 3:
                    localRot0 = Gf.Quatf(0, -0.49999997, 0, 0.8660253)

            localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
            localPos1 = Gf.Vec3f(0.0, 0.005540, -5.501821)
            localRot1 = localRot0
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z, joint_lower_limit, joint_upper_limit)

        self.assertIsValidUsd(stage)

    # Tests for joint axis other than +X, +Y, +Z, -X, -Y, -Z.
    def testPhysicsRevolutelJoint_any_axis(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        any_axis_xform_path = f"/{self.defaultPrimName}/any_axis"
        self.createXform(stage, any_axis_xform_path, Gf.Vec3d(0.0, 0.0, 0.0), Gf.Vec3f(0.0, 20.0, 5.0), Gf.Vec3f(1.0, 1.0, 1.0))

        # Rotate the axis around the Z axis.
        # The base joint_orientation(rocalRot) has no rotation.
        # joint_lower_limit -30.0, joint_upper_limit 60.0.
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)
        joint_orientation = Gf.Quatd.GetIdentity()
        joint_lower_limit = -30.0
        joint_upper_limit = 60.0

        for i in range(6):
            name = f"xform_axis_xy_{i * 10}"
            angle = i * 10.0
            joint_axis = Gf.Vec3f(Gf.Rotation(Gf.Vec3d(0.0, 0.0, 1.0), angle).TransformDir(Gf.Vec3d(1, 0, 0)))
            position = Gf.Vec3f(i * 10.0, 30.0, 0.0)

            joint = self.create_revolute_joint_with_capsules(
                stage, any_axis_xform_path, name, position, joint_position, joint_orientation, joint_axis, joint_lower_limit, joint_upper_limit
            )

            match i:
                case 0:
                    # Equivalent to RotateXYZ(0, 0, 0)
                    localRot0 = Gf.Quatf(1, 0, 0, 0)
                case 1:
                    # Equivalent to RotateXYZ(0, 0, 10)
                    localRot0 = Gf.Quatf(0.9961947, 0, 0, 0.08715564)
                case 2:
                    # Equivalent to RotateXYZ(0, 0, 20)
                    localRot0 = Gf.Quatf(0.9848077, 0, 0, 0.17364818)
                case 3:
                    # Equivalent to RotateXYZ(0, 0, 30)
                    localRot0 = Gf.Quatf(0.9659258, 0, 0, 0.25881907)
                case 4:
                    # Equivalent to RotateXYZ(0, 0, 40)
                    localRot0 = Gf.Quatf(0.9396926, 0, 0, 0.34202012)
                case 5:
                    # Equivalent to RotateXYZ(0, 0, 50)
                    localRot0 = Gf.Quatf(0.9063077, 0, 0, 0.42261826)

            localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
            localPos1 = Gf.Vec3f(0.0, 0.005540444, -5.501821)
            localRot1 = localRot0
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, joint_lower_limit, joint_upper_limit)

        # Rotate the axis around the Y axis.
        # Specify rotation with the base joint_orientation(localRot).
        # joint_lower_limit -30.0, joint_upper_limit 60.0.
        joint_position = Gf.Vec3d(0.0, 0.0, 5.5)
        joint_orientation = Gf.Rotation(Gf.Vec3d(1.0, 0.0, 0.0), -25.0).GetQuat()
        joint_lower_limit = -30.0
        joint_upper_limit = 60.0

        for i in range(6):
            name = f"xform_axis_xz_{i * 10}"
            angle = i * 10.0
            joint_axis = Gf.Vec3f(Gf.Rotation(Gf.Vec3d(0.0, 1.0, 0.0), angle).TransformDir(Gf.Vec3d(1, 0, 0)))
            position = Gf.Vec3f(i * 10.0, 30.0, 30.0)

            joint = self.create_revolute_joint_with_capsules(
                stage, any_axis_xform_path, name, position, joint_position, joint_orientation, joint_axis, joint_lower_limit, joint_upper_limit
            )

            match i:
                case 0:
                    # Equivalent to RotateXYZ(-25, 0, 0)
                    localRot0 = Gf.Quatf(0.976296, -0.21643962, -0, -0)
                case 1:
                    # Equivalent to RotateXYZ(-25, 10, 0)
                    localRot0 = Gf.Quatf(0.9725809, -0.215616, 0.085089706, -0.018863933)
                case 2:
                    # Equivalent to RotateXYZ(-25, 20, 0)
                    localRot0 = Gf.Quatf(0.96146387, -0.21315141, 0.16953203, -0.037584346)
                case 3:
                    # Equivalent to RotateXYZ(-25, 30, 0)
                    localRot0 = Gf.Quatf(0.9430295, -0.20906462, 0.25268403, -0.056018703)
                case 4:
                    # Equivalent to RotateXYZ(-25, 40, 0)
                    localRot0 = Gf.Quatf(0.9174181, -0.20338671, 0.3339129, -0.07402671)
                case 5:
                    # Equivalent to RotateXYZ(-25, 50, 0)
                    localRot0 = Gf.Quatf(0.8848247, -0.19616091, 0.4126005, -0.09147133)

            localPos0 = Gf.Vec3f(0.0, 0.0, 5.5)
            localPos1 = Gf.Vec3f(0.0, 0.005540444, -5.501821)
            localRot1 = localRot0
            self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, joint_lower_limit, joint_upper_limit)

        self.assertIsValidUsd(stage)

    # A test of using rigid bodies in a hierarchical structure.
    # Also, here we assign a rigid body to the Xform.
    # Note that placing a hierarchical rigid body will result in an error, but this will be skipped in this test.
    def testPhysicsRevoluteJoint_RigidBodyHierarchy(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        body1_path = f"/{self.defaultPrimName}/body1"
        body1_position = Gf.Vec3d(0.0, 0.0, 1.0)
        body1_rotation = Gf.Vec3f(-45.0, 0.0, 0.0)
        body1_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        body1_prim = self.createXform(stage, body1_path, body1_position, body1_rotation, body1_scale)

        body2_path = f"{body1_path}/body2"
        body2_position = Gf.Vec3d(0.0, 0.5, 0.0)
        body2_rotation = Gf.Vec3f(0.0, 0.0, 0.0)
        body2_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        body2_prim = self.createXform(stage, body2_path, body2_position, body2_rotation, body2_scale)

        box1_path = f"{body1_path}/box1"
        box1_size = 2.0
        box1_position = Gf.Vec3d(0.0, 0.0, 0.0)
        box1_rotation = Gf.Vec3f(0.0, 0.0, 0.0)
        box1_scale = Gf.Vec3f(0.1, 0.5, 0.1)
        box1_prim = self.createCube(stage, box1_path, box1_size, Gf.Vec3f(0.0, 1.0, 0.0), box1_position, box1_rotation, box1_scale)

        box2_path = f"{body2_path}/box2"
        box2_size = 2.0
        box2_position = Gf.Vec3d(0.0, 0.6, 0.0)
        box2_rotation = Gf.Vec3f(0.0, 0.0, 0.0)
        box2_scale = Gf.Vec3f(0.05, 0.5, 0.05)
        box2_prim = self.createCube(stage, box2_path, box2_size, Gf.Vec3f(0.0, 0.0, 1.0), box2_position, box2_rotation, box2_scale)

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(box1_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(body1_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(box2_prim)
        UsdPhysics.RigidBodyAPI.Apply(body2_prim)

        joint_name = "revolute_joint"
        joint_position = Gf.Vec3d(0.0, 0.1, 0.0)
        joint_orientation = Gf.Quatd.GetIdentity()
        joint_axis = Gf.Vec3f(1.0, 0.0, 0.0)
        joint_lower_limit = -30.0
        joint_upper_limit = 60.0
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, joint_position, joint_orientation)
        joint = usdex.core.definePhysicsRevoluteJoint(
            body2_prim, joint_name, body1_prim, body2_prim, jointFrame, joint_axis, joint_lower_limit, joint_upper_limit
        )
        self.assertTrue(joint)

        localPos0 = Gf.Vec3f(0.0, 0.6, 0.0)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0.0, 0.1, 0.0)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, joint_lower_limit, joint_upper_limit)

        # 'Simulation of multiple rigid bodies in a hierarchy will cause unpredicted results. Please fix the hierarchy or use XformStack reset'
        # This warning will be skipped during USD validation.
        self.assertIsValidUsd(
            stage,
            issuePredicates=[
                omni.asset_validator.IssuePredicates.ContainsMessage(
                    "Simulation of multiple rigid bodies in a hierarchy will cause unpredicted results. Please fix the hierarchy or use XformStack reset"
                ),
            ],
        )


class PhysicsJointAlgoTest_PrismaticJoint(PhysicsJointAlgoTest, usdex.test.DefineFunctionTestCase):
    defineFunc = usdex.core.definePhysicsPrismaticJoint
    requiredArgs = tuple([Usd.Prim(), Usd.Prim(), usdex.core.JointFrame(), Gf.Vec3f(0.0, 0.0, 1.0)])
    typeName = "PhysicsPrismaticJoint"
    schema = UsdPhysics.PrismaticJoint
    requiredPropertyNames = []

    # Override createTestStage for testing purposes for PhysicsJoint.
    def createTestStage(self):
        stage = super().createTestStage()
        body0, body1, jointFrame = self.overrideCreateTestStage(stage)

        # Replaces requiredArgs.
        axis = Gf.Vec3f(0.0, 0.0, 1.0)
        self.requiredArgs = tuple([body0, body1, jointFrame, axis])

        return stage

    # Test the physics prismatic joint simple.
    def testPhysicsPrismaticJoint_simple(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create capsules.
        # The capsules are aligned along the Z axis.
        # These are tilted about the X axis so that they can be moved by gravity.
        capsule0_path = f"/{self.defaultPrimName}/capsule0"
        capsule1_path = f"/{self.defaultPrimName}/capsule1"
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z

        capsule_translation = Gf.Vec3d(0.0, 8.0, 0.0)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule0_prim = self.createCapsule(
            stage, capsule0_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        capsule_translation = Gf.Vec3d(0.0, 5.24, 10.65)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule1_prim = self.createCapsule(
            stage, capsule1_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(capsule0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(capsule0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(capsule1_prim)
        UsdPhysics.RigidBodyAPI.Apply(capsule1_prim)

        # Create a prismatic joint.
        axis = Gf.Vec3f(0.0, 0.0, 1.0)
        lower_limit = -0.5
        upper_limit = 15.0

        xform_cache = UsdGeom.XformCache()
        capsule0_worldTransform = xform_cache.GetLocalToWorldTransform(capsule0_prim)
        capsule1_worldTransform = xform_cache.GetLocalToWorldTransform(capsule1_prim)
        capsule0_worldPosition = capsule0_worldTransform.ExtractTranslation()
        capsule1_worldPosition = capsule1_worldTransform.ExtractTranslation()
        joint_position = (capsule0_worldPosition + capsule1_worldPosition) / 2.0
        joint_orientation = Gf.Rotation(Gf.Vec3d(1, 0, 0), 14.5).GetQuat()
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.World, joint_position, joint_orientation)

        joint_path = f"/{self.defaultPrimName}/prismatic_joint"
        joint = usdex.core.definePhysicsPrismaticJoint(stage, joint_path, capsule0_prim, capsule1_prim, jointFrame, axis, lower_limit, upper_limit)
        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(0, -0.0027703806, 5.5009103)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0, 0.0027700635, -5.5009108)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z, lower_limit, upper_limit)

    # Test the physics prismatic joint with xform.
    def testPhysicsPrismaticJoint_with_xform(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xform_path = f"/{self.defaultPrimName}/xform"
        xform_position = Gf.Vec3d(-20.0, 30.0, 0.0)
        xform_rotation = Gf.Vec3f(0.0, 30.0, 0.0)
        xform_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        self.createXform(stage, xform_path, xform_position, xform_rotation, xform_scale)

        # Create capsules.
        # The capsules are aligned along the Z axis.
        # These are tilted about the X axis so that they can be moved by gravity.
        capsule0_path = f"{xform_path}/capsule0"
        capsule1_path = f"{xform_path}/capsule1"
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z

        capsule_translation = Gf.Vec3d(0.0, 8.0, 0.0)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule0_prim = self.createCapsule(
            stage, capsule0_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        capsule_translation = Gf.Vec3d(0.0, 5.24, 10.65)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule1_prim = self.createCapsule(
            stage, capsule1_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(capsule0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(capsule0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(capsule1_prim)
        UsdPhysics.RigidBodyAPI.Apply(capsule1_prim)

        # Create Xform.
        xform_joints_path = f"/{self.defaultPrimName}/joints"
        xform_joints_position = Gf.Vec3d(20.0, 10.0, 0.0)
        xform_joints_rotation = Gf.Vec3f(10.0, 35.0, -2.0)
        xform_joints_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        xform_joints_prim = self.createXform(stage, xform_joints_path, xform_joints_position, xform_joints_rotation, xform_joints_scale)

        # Create a prismatic joint.
        axis = Gf.Vec3f(0.0, 0.0, 1.0)
        lower_limit = -0.5
        upper_limit = 15.0

        xform_cache = UsdGeom.XformCache()
        capsule0_worldTransform = xform_cache.GetLocalToWorldTransform(capsule0_prim)
        capsule1_worldTransform = xform_cache.GetLocalToWorldTransform(capsule1_prim)
        capsule0_worldPosition = capsule0_worldTransform.ExtractTranslation()
        capsule1_worldPosition = capsule1_worldTransform.ExtractTranslation()
        joint_position = (capsule0_worldPosition + capsule1_worldPosition) / 2.0

        # Get the local position of the joint in the capsule0_prim's coordinate system.
        lPos = capsule0_worldTransform.GetInverse().Transform(joint_position)
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body0, lPos, Gf.Quatd.GetIdentity())

        joint_name = "prismatic_joint"
        joint = usdex.core.definePhysicsPrismaticJoint(
            xform_joints_prim, joint_name, capsule0_prim, capsule1_prim, jointFrame, axis, lower_limit, upper_limit
        )
        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(0, -0.002770222, 5.5009108)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0, 0.002770222, -5.5009108)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z, lower_limit, upper_limit)


class PhysicsJointAlgoTest_SphericalJoint(PhysicsJointAlgoTest, usdex.test.DefineFunctionTestCase):
    defineFunc = usdex.core.definePhysicsSphericalJoint
    requiredArgs = tuple([Usd.Prim(), Usd.Prim(), usdex.core.JointFrame(), Gf.Vec3f(1.0, 0.0, 0.0)])
    typeName = "PhysicsSphericalJoint"
    schema = UsdPhysics.SphericalJoint
    requiredPropertyNames = []

    # Override createTestStage for testing purposes for PhysicsJoint.
    def createTestStage(self):
        stage = super().createTestStage()
        body0, body1, jointFrame = self.overrideCreateTestStage(stage)

        # Replaces requiredArgs.
        axis = Gf.Vec3f(0.0, 0.0, 1.0)
        self.requiredArgs = tuple([body0, body1, jointFrame, axis])

        return stage

    # Test the physics spherical joint simple.
    def testPhysicsSphericalJoint_simple(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create capsules.
        # The capsules are aligned along the Z axis.
        # These are tilted about the X axis so that they can be moved by gravity.
        capsule0_path = f"/{self.defaultPrimName}/capsule0"
        capsule1_path = f"/{self.defaultPrimName}/capsule1"
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z

        capsule_translation = Gf.Vec3d(0.0, 8.0, 0.0)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule0_prim = self.createCapsule(
            stage, capsule0_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        capsule_translation = Gf.Vec3d(0.0, 5.24, 10.65)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule1_prim = self.createCapsule(
            stage, capsule1_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 0.0, 1.0), capsule_translation, capsule_rotationXYZ
        )

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(capsule0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(capsule0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(capsule1_prim)
        UsdPhysics.RigidBodyAPI.Apply(capsule1_prim)

        # Create a prismatic joint.
        axis = Gf.Vec3f(0.0, 0.0, 1.0)
        coneAngle0Limit = 20.0
        coneAngle1Limit = 40.0

        xform_cache = UsdGeom.XformCache()
        capsule0_worldTransform = xform_cache.GetLocalToWorldTransform(capsule0_prim)
        capsule1_worldTransform = xform_cache.GetLocalToWorldTransform(capsule1_prim)
        capsule0_worldPosition = capsule0_worldTransform.ExtractTranslation()
        capsule1_worldPosition = capsule1_worldTransform.ExtractTranslation()
        joint_position = (capsule0_worldPosition + capsule1_worldPosition) / 2.0
        joint_orientation = Gf.Rotation(Gf.Vec3d(1, 0, 0), 14.5).GetQuat()
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.World, joint_position, joint_orientation)

        joint_path = f"/{self.defaultPrimName}/spherical_joint"
        joint = usdex.core.definePhysicsSphericalJoint(
            stage, joint_path, capsule0_prim, capsule1_prim, jointFrame, axis, coneAngle0Limit, coneAngle1Limit
        )
        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(0, -0.0027703806, 5.5009103)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0, 0.0027700635, -5.5009108)
        localRot1 = Gf.Quatf.GetIdentity()
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z, None, None, coneAngle0Limit, coneAngle1Limit)

    # Test the physics spherical joint with xform.
    def testPhysicsSphericalJoint_with_xform(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xform_path = f"/{self.defaultPrimName}/xform"
        xform_position = Gf.Vec3d(-20.0, 30.0, 0.0)
        xform_rotation = Gf.Vec3f(20.0, 30.0, 0.0)
        xform_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        self.createXform(stage, xform_path, xform_position, xform_rotation, xform_scale)

        xform2_path = f"{xform_path}/xform2"
        xform2_position = Gf.Vec3d(20.0, 10.0, 5.0)
        xform2_rotation = Gf.Vec3f(-20.0, 10.0, 0.0)
        xform2_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        self.createXform(stage, xform2_path, xform2_position, xform2_rotation, xform2_scale)

        # Create capsules.
        # The capsules are aligned along the Z axis.
        # These are tilted about the X axis so that they can be moved by gravity.
        capsule0_path = f"{xform_path}/capsule0"
        capsule1_path = f"{xform2_path}/capsule1"
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z

        capsule_translation = Gf.Vec3d(0.0, 8.0, 0.0)
        capsule_rotationXYZ = Gf.Vec3f(14.5, 0, 0)
        capsule0_prim = self.createCapsule(
            stage, capsule0_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        capsule_translation = Gf.Vec3d(-20.677, -5.188, 0.337)
        capsule_rotationXYZ = Gf.Vec3f(34.78, -9.39, -3.45)
        capsule1_prim = self.createCapsule(
            stage, capsule1_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 0.0, 1.0), capsule_translation, capsule_rotationXYZ
        )

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(capsule0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(capsule0_prim)
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(capsule1_prim)
        UsdPhysics.RigidBodyAPI.Apply(capsule1_prim)

        # Create a prismatic joint.
        axis = Gf.Vec3f(0.0, 0.0, 1.0)
        coneAngle0Limit = 20.0
        coneAngle1Limit = 40.0

        xform_cache = UsdGeom.XformCache()
        capsule0_worldTransform = xform_cache.GetLocalToWorldTransform(capsule0_prim)
        capsule1_worldTransform = xform_cache.GetLocalToWorldTransform(capsule1_prim)
        capsule0_worldPosition = capsule0_worldTransform.ExtractTranslation()
        capsule1_worldPosition = capsule1_worldTransform.ExtractTranslation()
        joint_position = (capsule0_worldPosition + capsule1_worldPosition) / 2.0
        lPos = capsule0_worldTransform.GetInverse().Transform(joint_position)
        joint_orientation = Gf.Quatd.GetIdentity()
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body0, lPos, joint_orientation)

        xform_joints_path = f"/{self.defaultPrimName}/joints"
        xform_joints_position = Gf.Vec3d(10.0, 30.0, 2.0)
        xform_joints_rotation = Gf.Vec3f(10.0, 0.0, 0.0)
        xform_joints_scale = Gf.Vec3f(1.0, 1.0, 1.0)
        xform_joints_prim = self.createXform(stage, xform_joints_path, xform_joints_position, xform_joints_rotation, xform_joints_scale)

        joint_name = "spherical_joint"
        joint = usdex.core.definePhysicsSphericalJoint(
            xform_joints_prim, joint_name, capsule0_prim, capsule1_prim, jointFrame, axis, coneAngle0Limit, coneAngle1Limit
        )
        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(0.00012089346, -0.0027256596, 5.5008125)
        localRot0 = Gf.Quatf.GetIdentity()
        localPos1 = Gf.Vec3f(0.000044151413, 0.0030490516, -5.500812)
        localRot1 = Gf.Quatf(1.0, Gf.Vec3f(0.000029394923, -0.000015000849, -0.0000019334022))
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.z, None, None, coneAngle0Limit, coneAngle1Limit)

    # Test to swap referenced bodies.
    def testSwapReferencedBodies(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create capsules.
        # The capsules are aligned along the Z axis.
        capsule0_path = f"/{self.defaultPrimName}/capsule0"
        capsule1_path = f"/{self.defaultPrimName}/capsule1"
        capsule2_path = f"/{self.defaultPrimName}/capsule2"
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z
        capsule_margin = 1.0

        pz = 0.0
        capsule_translation = Gf.Vec3d(0.0, 0.0, pz)
        capsule_rotationXYZ = Gf.Vec3f(0, 0, 0)
        capsule0_prim = self.createCapsule(
            stage, capsule0_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        pz += capsule_height + capsule_radius * 2.0 + capsule_margin
        capsule_translation = Gf.Vec3d(0.0, 0.0, pz)
        capsule1_prim = self.createCapsule(
            stage, capsule1_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        # For testing replacement.
        capsule2_prim = self.createCapsule(
            stage, capsule2_path, capsule_radius, capsule_height, capsule_axis, Gf.Vec3f(0.0, 1.0, 0.0), capsule_translation, capsule_rotationXYZ
        )

        # Apply collision and rigidbody.
        UsdPhysics.CollisionAPI.Apply(capsule0_prim)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(capsule0_prim)

        # Specify kinematics to prevent the root rigid body from free-falling during playback.
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        UsdPhysics.CollisionAPI.Apply(capsule1_prim)
        UsdPhysics.RigidBodyAPI.Apply(capsule1_prim)

        UsdPhysics.RigidBodyAPI.Apply(capsule2_prim)

        # Create a revolute joint.
        axis = Gf.Vec3f(1.0, 0.0, 0.0)
        lower_limit = -20.0
        upper_limit = 35.0

        xform_cache = UsdGeom.XformCache()
        capsule0_worldTransform = xform_cache.GetLocalToWorldTransform(capsule0_prim)
        capsule1_worldTransform = xform_cache.GetLocalToWorldTransform(capsule1_prim)
        capsule0_worldPosition = capsule0_worldTransform.ExtractTranslation()
        capsule1_worldPosition = capsule1_worldTransform.ExtractTranslation()
        joint_position = (capsule0_worldPosition + capsule1_worldPosition) / 2.0
        joint_orientation = Gf.Quatd.GetIdentity()
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.World, joint_position, joint_orientation)

        joint_path = f"/{self.defaultPrimName}/revolute_joint"
        joint = usdex.core.definePhysicsRevoluteJoint(stage, joint_path, capsule0_prim, capsule1_prim, jointFrame, axis, lower_limit, upper_limit)

        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        axis = Gf.Vec3f(-1.0, 0.0, 0.0)
        new_lower_limit = -40.0
        new_upper_limit = 15.0
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, Gf.Vec3d(0, 0, -5.75), joint_orientation)

        # Change parameters.
        # Replace capsule1_prim with capsule2_prim in body1.
        usdex.core.connectPhysicsJoint(joint, capsule0_prim, capsule2_prim, jointFrame, axis)
        joint.GetLowerLimitAttr().Set(new_lower_limit)
        joint.GetUpperLimitAttr().Set(new_upper_limit)
        self.assertTrue(joint)
        self.assertIsValidUsd(stage)

        body0_targets = joint.GetBody0Rel().GetTargets()
        body1_targets = joint.GetBody1Rel().GetTargets()
        self.assertEqual(len(body0_targets), 1)
        self.assertEqual(len(body1_targets), 1)
        self.assertEqual(body0_targets[0], capsule0_prim.GetPath())
        self.assertEqual(body1_targets[0], capsule2_prim.GetPath())

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(0, 0, 5.25)
        localRot0 = Gf.Quatf(0, 0, -1, 0)
        localPos1 = Gf.Vec3f(0, 0, -5.75)
        localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, new_lower_limit, new_upper_limit)

        # Specify an empty prim for body0.
        usdex.core.connectPhysicsJoint(joint, Usd.Prim(), capsule1_prim, jointFrame, axis)
        self.assertEqual(len(joint.GetBody0Rel().GetTargets()), 0)

        localPos0 = Gf.Vec3f(0, 0, 5.25)
        localRot0 = Gf.Quatf(0, 0, -1, 0)
        localPos1 = Gf.Vec3f(0, 0, -5.75)
        localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, new_lower_limit, new_upper_limit)

        # Specify an empty prim for body1.
        jointFrame.space = usdex.core.JointFrame.Space.Body0
        usdex.core.connectPhysicsJoint(joint, capsule0_prim, Usd.Prim(), jointFrame, axis)
        self.assertEqual(len(joint.GetBody1Rel().GetTargets()), 0)

        localPos0 = Gf.Vec3f(0, 0, -5.75)
        localRot0 = Gf.Quatf(0, 0, -1, 0)
        localPos1 = Gf.Vec3f(0, 0, -5.75)
        localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, new_lower_limit, new_upper_limit)

        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Body0 and Body1 are not specified for PhysicsJoint at")]
        ):
            jointFrame.space = usdex.core.JointFrame.Space.World
            usdex.core.connectPhysicsJoint(joint, Usd.Prim(), Usd.Prim(), jointFrame, axis)

    def testSwapReferencedBodiesWithMultiLayers(self):
        output_dir = self.tmpDir()

        stage = Usd.Stage.CreateNew(f"{output_dir}/physics_joint_multi_layer_test.usda")
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Geometry and physics prims stored separately in separate layers.
        class Tokens:
            Asset = usdex.core.getAssetToken()
            Contents = usdex.core.getContentsToken()
            Geometry = usdex.core.getGeometryToken()
            Physics = usdex.core.getPhysicsToken()

        content: dict[Tokens, Usd.Stage] = {}

        content[Tokens.Asset] = stage
        root: Usd.Prim = usdex.core.defineXform(stage, stage.GetDefaultPrim().GetPath()).GetPrim()

        # setup the root layer of the payload
        content[Tokens.Contents] = usdex.core.createAssetPayload(stage)

        # setup a content layer for referenced meshes
        content[Tokens.Geometry] = usdex.core.addAssetContent(content[Tokens.Contents], Tokens.Geometry, format="usda")

        # setup a content layer for physics
        content[Tokens.Physics] = usdex.core.addAssetContent(content[Tokens.Contents], Tokens.Physics, format="usda")

        geo_scope = content[Tokens.Geometry].GetDefaultPrim().GetChild(Tokens.Geometry).GetPrim()
        physics_scope = content[Tokens.Physics].GetDefaultPrim().GetChild(Tokens.Physics).GetPrim()

        # Geometry layer: Create capsules.
        # The capsules are aligned along the Z axis.
        capsule0_path = geo_scope.GetPath().AppendChild("capsule0")
        capsule1_path = geo_scope.GetPath().AppendChild("capsule1")
        capsule2_path = geo_scope.GetPath().AppendChild("capsule2")
        capsule_radius = 1.0
        capsule_height = 8.0
        capsule_axis = UsdGeom.Tokens.z
        capsule_margin = 1.0

        pz = 0.0
        capsule_translation = Gf.Vec3d(0.0, 0.0, pz)
        capsule_rotationXYZ = Gf.Vec3f(0, 0, 0)
        capsule0_prim = self.createCapsule(
            geo_scope.GetStage(),
            capsule0_path,
            capsule_radius,
            capsule_height,
            capsule_axis,
            Gf.Vec3f(0.0, 1.0, 0.0),
            capsule_translation,
            capsule_rotationXYZ,
        )

        pz += capsule_height + capsule_radius * 2.0 + capsule_margin
        capsule_translation = Gf.Vec3d(0.0, 0.0, pz)
        capsule1_prim = self.createCapsule(
            geo_scope.GetStage(),
            capsule1_path,
            capsule_radius,
            capsule_height,
            capsule_axis,
            Gf.Vec3f(0.0, 1.0, 0.0),
            capsule_translation,
            capsule_rotationXYZ,
        )

        # For testing replacement.
        capsule2_prim = self.createCapsule(
            geo_scope.GetStage(),
            capsule2_path,
            capsule_radius,
            capsule_height,
            capsule_axis,
            Gf.Vec3f(0.0, 1.0, 0.0),
            capsule_translation,
            capsule_rotationXYZ,
        )

        # Physics layer: Apply collision and rigidbody.
        prim_over = content[Tokens.Physics].OverridePrim(capsule0_prim.GetPath())
        UsdPhysics.CollisionAPI.Apply(prim_over)
        rigidbodyAPI = UsdPhysics.RigidBodyAPI.Apply(prim_over)

        # Specify kinematics to prevent the root rigid body from free-falling during playback.
        rigidbodyAPI.CreateKinematicEnabledAttr(True)

        prim_over = content[Tokens.Physics].OverridePrim(capsule1_prim.GetPath())
        UsdPhysics.CollisionAPI.Apply(prim_over)
        UsdPhysics.RigidBodyAPI.Apply(prim_over)

        prim_over = content[Tokens.Physics].OverridePrim(capsule2_prim.GetPath())
        UsdPhysics.RigidBodyAPI.Apply(prim_over)

        # Create a revolute joint.
        axis = Gf.Vec3f(1.0, 0.0, 0.0)
        lower_limit = -20.0
        upper_limit = 35.0

        xform_cache = UsdGeom.XformCache()
        capsule0_worldTransform = xform_cache.GetLocalToWorldTransform(capsule0_prim)
        capsule1_worldTransform = xform_cache.GetLocalToWorldTransform(capsule1_prim)
        capsule0_worldPosition = capsule0_worldTransform.ExtractTranslation()
        capsule1_worldPosition = capsule1_worldTransform.ExtractTranslation()
        joint_position = (capsule0_worldPosition + capsule1_worldPosition) / 2.0
        joint_orientation = Gf.Quatd.GetIdentity()
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.World, joint_position, joint_orientation)

        joint_path = physics_scope.GetPath().AppendChild("revolute_joint")
        joint = usdex.core.definePhysicsRevoluteJoint(
            physics_scope.GetStage(), joint_path, capsule0_prim, capsule1_prim, jointFrame, axis, lower_limit, upper_limit
        )
        self.assertTrue(joint)
        self.assertIsValidUsd(content[Tokens.Asset])

        # Check that the joint is not in the geometry layer.
        self.assertNotEqual(capsule0_prim.GetStage(), joint.GetPrim().GetStage())
        self.assertNotEqual(capsule1_prim.GetStage(), joint.GetPrim().GetStage())
        self.assertNotEqual(capsule2_prim.GetStage(), joint.GetPrim().GetStage())

        axis = Gf.Vec3f(-1.0, 0.0, 0.0)
        new_lower_limit = -40.0
        new_upper_limit = 15.0
        jointFrame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, Gf.Vec3d(0, 0, -5.75), joint_orientation)

        # Change parameters.
        # When using alignPhysicsJoint, body0/body1 refer to the Physics layer on the joint's stage,
        # and position and orientation will be jointFrame.position and jointFrame.orientation * axis (fail).
        usdex.core.alignPhysicsJoint(joint, jointFrame, axis)
        self.assertIsValidUsd(content[Tokens.Asset])
        localPos0 = localPos1 = Gf.Vec3f(jointFrame.position)
        localRot0 = localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, lower_limit, upper_limit)

        # Change parameters.
        # Replace capsule1_prim with capsule2_prim in body1.
        # The joint belongs to the Physics layer, and body0 and body1 belong to the Geometry layer.
        usdex.core.connectPhysicsJoint(joint, capsule0_prim, capsule2_prim, jointFrame, axis)
        joint.GetLowerLimitAttr().Set(new_lower_limit)
        joint.GetUpperLimitAttr().Set(new_upper_limit)
        self.assertTrue(joint)
        self.assertIsValidUsd(content[Tokens.Asset])

        body0_targets = joint.GetBody0Rel().GetTargets()
        body1_targets = joint.GetBody1Rel().GetTargets()
        self.assertEqual(len(body0_targets), 1)
        self.assertEqual(len(body1_targets), 1)
        self.assertEqual(body0_targets[0], capsule0_prim.GetPath())
        self.assertEqual(body1_targets[0], capsule2_prim.GetPath())

        # Check the joint parameters.
        localPos0 = Gf.Vec3f(0, 0, 5.25)
        localRot0 = Gf.Quatf(0, 0, -1, 0)
        localPos1 = Gf.Vec3f(0, 0, -5.75)
        localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, new_lower_limit, new_upper_limit)

        # Specify an empty prim for body0.
        usdex.core.connectPhysicsJoint(joint, Usd.Prim(), capsule1_prim, jointFrame, axis)
        self.assertEqual(len(joint.GetBody0Rel().GetTargets()), 0)

        localPos0 = Gf.Vec3f(0, 0, 5.25)
        localRot0 = Gf.Quatf(0, 0, -1, 0)
        localPos1 = Gf.Vec3f(0, 0, -5.75)
        localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, new_lower_limit, new_upper_limit)

        # Specify an empty prim for body1.
        jointFrame.space = usdex.core.JointFrame.Space.Body0
        usdex.core.connectPhysicsJoint(joint, capsule0_prim, Usd.Prim(), jointFrame, axis)
        self.assertEqual(len(joint.GetBody1Rel().GetTargets()), 0)

        localPos0 = Gf.Vec3f(0, 0, -5.75)
        localRot0 = Gf.Quatf(0, 0, -1, 0)
        localPos1 = Gf.Vec3f(0, 0, -5.75)
        localRot1 = Gf.Quatf(0, 0, -1, 0)
        self.assertIsPhysicsJoint(joint, localPos0, localRot0, localPos1, localRot1, UsdGeom.Tokens.x, new_lower_limit, new_upper_limit)

        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Body0 and Body1 are not specified for PhysicsJoint at")]
        ):
            jointFrame.space = usdex.core.JointFrame.Space.World
            usdex.core.connectPhysicsJoint(joint, Usd.Prim(), Usd.Prim(), jointFrame, axis)
