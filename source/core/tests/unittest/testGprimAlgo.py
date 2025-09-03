# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from typing import List, Tuple

import omni.asset_validator
import usdex.core
import usdex.test
from pxr import Gf, Usd, UsdGeom


class DefinePlaneTestCase(usdex.test.DefineFunctionTestCase):
    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.definePlane
    requiredArgs = tuple([2.0, 2.0, UsdGeom.Tokens.z])
    typeName = "Plane"
    schema = UsdGeom.Plane
    requiredPropertyNames = set(
        [
            "width",
            "length",
            "axis",
        ]
    )


class DefineSphereTestCase(usdex.test.DefineFunctionTestCase):
    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineSphere
    requiredArgs = tuple([1.0])
    typeName = "Sphere"
    schema = UsdGeom.Sphere
    requiredPropertyNames = set(
        [
            "radius",
        ]
    )


class DefineCubeTestCase(usdex.test.DefineFunctionTestCase):
    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCube
    requiredArgs = tuple([2.0])
    typeName = "Cube"
    schema = UsdGeom.Cube
    requiredPropertyNames = set(
        [
            "size",
        ]
    )


class DefineConeTestCase(usdex.test.DefineFunctionTestCase):
    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCone
    requiredArgs = tuple([1.0, 2.0, UsdGeom.Tokens.z])
    typeName = "Cone"
    schema = UsdGeom.Cone
    requiredPropertyNames = set(
        [
            "radius",
            "height",
            "axis",
        ]
    )


class DefineCylinderTestCase(usdex.test.DefineFunctionTestCase):
    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCylinder
    requiredArgs = tuple([1.0, 2.0, UsdGeom.Tokens.z])
    typeName = "Cylinder"
    schema = UsdGeom.Cylinder
    requiredPropertyNames = set(
        [
            "radius",
            "height",
            "axis",
        ]
    )


class DefineGeomCapsuleTestCase(usdex.test.DefineFunctionTestCase):
    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineCapsule
    requiredArgs = tuple([1.0, 2.0, UsdGeom.Tokens.z])
    typeName = "Capsule"
    schema = UsdGeom.Capsule
    requiredPropertyNames = set(
        [
            "radius",
            "height",
            "axis",
        ]
    )


class GprimAlgoTest(usdex.test.TestCase):
    # Set the local position of the prim.
    def setLocalPosition(self, prim: Usd.Prim, position: Gf.Vec3d):
        pivot = Gf.Vec3d(0)
        rotation = Gf.Vec3f(0)
        scale = Gf.Vec3f(1)
        usdex.core.setLocalTransform(prim, position, pivot, rotation, usdex.core.RotationOrder.eXyz, scale)

    # Geometric primitives are placed by specifying the prim path.
    def testGprimAlgo(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xformPath = f"/{self.defaultPrimName}/xform"
        xformPrim = usdex.core.defineXform(stage, xformPath)

        # Create plane.
        planePath = f"{xformPath}/plane"
        planeAxis = UsdGeom.Tokens.y
        planeWidth = 50.0
        planeLength = 20.0
        planeDisplayColor = Gf.Vec3f(0.5, 0.5, 0.5)
        plane = usdex.core.definePlane(stage, planePath, planeWidth, planeLength, planeAxis, planeDisplayColor)
        self.assertTrue(plane)
        self.assertEqual(plane.GetWidthAttr().Get(), planeWidth)
        self.assertEqual(plane.GetLengthAttr().Get(), planeLength)
        self.assertEqual(plane.GetAxisAttr().Get(), planeAxis)
        self.assertEqual(len(plane.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(plane.GetDisplayColorAttr().Get()[0], planeDisplayColor)

        # Create sphere.
        spherePath = f"{xformPath}/sphere"
        radius = 5.0
        sphereDisplayColor = Gf.Vec3f(0, 1, 0)
        sphere = usdex.core.defineSphere(stage, spherePath, radius, sphereDisplayColor)
        self.assertTrue(sphere)
        self.assertEqual(sphere.GetRadiusAttr().Get(), radius)
        self.assertEqual(len(sphere.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(sphere.GetDisplayColorAttr().Get()[0], sphereDisplayColor)
        self.setLocalPosition(sphere, Gf.Vec3d(-20.0, 5.0, 0.0))

        # Create cube.
        cubePath = f"{xformPath}/cube"
        cubeSize = 8.0
        cubeDisplayColor = Gf.Vec3f(0, 0, 1)
        cube = usdex.core.defineCube(stage, cubePath, cubeSize, cubeDisplayColor)
        self.assertTrue(cube)
        self.assertEqual(cube.GetSizeAttr().Get(), cubeSize)
        self.assertEqual(len(cube.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(cube.GetDisplayColorAttr().Get()[0], cubeDisplayColor)
        self.setLocalPosition(cube, Gf.Vec3d(-10.0, 4.0, 0.0))

        # Create cone.
        conePath = f"{xformPath}/cone"
        coneAxis = UsdGeom.Tokens.y
        coneRadius = 4.0
        coneHeight = 10.0
        coneDisplayColor = Gf.Vec3f(0.5, 0, 0)
        cone = usdex.core.defineCone(stage, conePath, coneRadius, coneHeight, coneAxis, coneDisplayColor)
        self.assertTrue(cone)
        self.assertEqual(cone.GetRadiusAttr().Get(), coneRadius)
        self.assertEqual(cone.GetHeightAttr().Get(), coneHeight)
        self.assertEqual(cone.GetAxisAttr().Get(), coneAxis)
        self.assertEqual(len(cone.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(cone.GetDisplayColorAttr().Get()[0], coneDisplayColor)
        self.setLocalPosition(cone, Gf.Vec3d(0.0, 5.0, 0.0))

        # Create cylinder.
        cylinderPath = f"{xformPath}/cylinder"
        cylinderAxis = UsdGeom.Tokens.y
        cylinderRadius = 2.0
        cylinderHeight = 10.0
        cylinderDisplayColor = Gf.Vec3f(0, 0.5, 0)
        cylinder = usdex.core.defineCylinder(stage, cylinderPath, cylinderRadius, cylinderHeight, cylinderAxis, cylinderDisplayColor)
        self.assertTrue(cylinder)
        self.assertEqual(cylinder.GetRadiusAttr().Get(), cylinderRadius)
        self.assertEqual(cylinder.GetHeightAttr().Get(), cylinderHeight)
        self.assertEqual(cylinder.GetAxisAttr().Get(), cylinderAxis)
        self.assertEqual(len(cylinder.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(cylinder.GetDisplayColorAttr().Get()[0], cylinderDisplayColor)
        self.setLocalPosition(cylinder, Gf.Vec3d(10.0, 5.0, 0.0))

        # Create capsule.
        capsulePath = f"{xformPath}/capsule"
        capsuleAxis = UsdGeom.Tokens.y
        capsuleRadius = 2.0
        capsuleHeight = 10.0
        capsuleDisplayColor = Gf.Vec3f(0, 0, 0.5)
        capsule = usdex.core.defineCapsule(stage, capsulePath, capsuleRadius, capsuleHeight, capsuleAxis, capsuleDisplayColor)
        self.assertTrue(capsule)
        self.assertEqual(capsule.GetRadiusAttr().Get(), capsuleRadius)
        self.assertEqual(capsule.GetHeightAttr().Get(), capsuleHeight)
        self.assertEqual(capsule.GetAxisAttr().Get(), capsuleAxis)
        self.assertEqual(len(capsule.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(capsule.GetDisplayColorAttr().Get()[0], capsuleDisplayColor)
        self.setLocalPosition(capsule, Gf.Vec3d(20.0, 7.0, 0.0))

        self.assertIsValidUsd(stage)

    # Test the definePlane function.
    def testGprimPlane(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xformPath = f"/{self.defaultPrimName}/xform"
        xformPrim = usdex.core.defineXform(stage, xformPath)

        # Creates a plane as a child of the specified prim.
        planeAxis = UsdGeom.Tokens.y
        planeWidth = 10.0
        planeLength = 8.0
        plane = usdex.core.definePlane(xformPrim.GetPrim(), "plane", planeWidth, planeLength, planeAxis)
        self.assertTrue(plane)
        self.assertEqual(plane.GetWidthAttr().Get(), planeWidth)
        self.assertEqual(plane.GetLengthAttr().Get(), planeLength)
        self.assertEqual(plane.GetAxisAttr().Get(), planeAxis)

        # Update Axis.
        newPlaneAxis = UsdGeom.Tokens.x
        newPlaneWidth = 15.0
        newPlaneLength = 12.0
        usdex.core.definePlane(plane.GetPrim(), newPlaneWidth, newPlaneLength, newPlaneAxis)
        self.assertEqual(plane.GetWidthAttr().Get(), newPlaneWidth)
        self.assertEqual(plane.GetLengthAttr().Get(), newPlaneLength)
        self.assertEqual(plane.GetAxisAttr().Get(), newPlaneAxis)

        # Update Display Color and Opacity.
        newDisplayColor = Gf.Vec3f(0, 1, 0)
        newDisplayOpacity = 0.5
        usdex.core.definePlane(plane.GetPrim(), newPlaneWidth, newPlaneLength, newPlaneAxis, newDisplayColor, newDisplayOpacity)
        self.assertEqual(len(plane.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(plane.GetDisplayColorAttr().Get()[0], newDisplayColor)
        self.assertEqual(len(plane.GetDisplayOpacityAttr().Get()), 1)
        self.assertEqual(plane.GetDisplayOpacityAttr().Get()[0], newDisplayOpacity)

        # Since the width is 15 and the length is 12, the extent is 0 x 12 x 15.
        extentAttr = plane.GetExtentAttr()
        self.assertTrue(extentAttr)
        extent = extentAttr.Get()
        extentX = extent[1][0] - extent[0][0]
        extentY = extent[1][1] - extent[0][1]
        extentZ = extent[1][2] - extent[0][2]
        self.assertEqual(extentX, 0.0)
        self.assertEqual(extentY, newPlaneLength)
        self.assertEqual(extentZ, newPlaneWidth)

        # If displayColor and displayOpacity are not specified, verify that they are cleared.
        usdex.core.definePlane(plane.GetPrim(), newPlaneWidth, newPlaneLength, newPlaneAxis)
        self.assertFalse(plane.GetDisplayColorAttr().Get())
        self.assertFalse(plane.GetDisplayOpacityAttr().Get())

        self.assertIsValidUsd(stage)

    # Test the defineSphere function.
    def testGprimSphere(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xformPath = f"/{self.defaultPrimName}/xform"
        xformPrim = usdex.core.defineXform(stage, xformPath)

        # Creates a sphere as a child of the specified prim.
        radius = 5.0
        sphere = usdex.core.defineSphere(xformPrim.GetPrim(), "sphere", radius)
        self.assertTrue(sphere)
        self.assertEqual(sphere.GetRadiusAttr().Get(), radius)

        # Update Radius.
        newRadius = 10.0
        usdex.core.defineSphere(sphere.GetPrim(), newRadius)
        self.assertEqual(sphere.GetRadiusAttr().Get(), newRadius)

        # Update Display Color and Opacity.
        newDisplayColor = Gf.Vec3f(0, 1, 0)
        newDisplayOpacity = 0.5
        usdex.core.defineSphere(sphere.GetPrim(), newRadius, newDisplayColor, newDisplayOpacity)
        self.assertEqual(len(sphere.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(sphere.GetDisplayColorAttr().Get()[0], newDisplayColor)
        self.assertEqual(len(sphere.GetDisplayOpacityAttr().Get()), 1)
        self.assertEqual(sphere.GetDisplayOpacityAttr().Get()[0], newDisplayOpacity)

        # Since the radius is 10, the extent is 20 x 20 x 20.
        extentAttr = sphere.GetExtentAttr()
        self.assertTrue(extentAttr)
        extent = extentAttr.Get()
        extentX = extent[1][0] - extent[0][0]
        extentY = extent[1][1] - extent[0][1]
        extentZ = extent[1][2] - extent[0][2]
        self.assertEqual(extentX, newRadius * 2.0)
        self.assertEqual(extentY, newRadius * 2.0)
        self.assertEqual(extentZ, newRadius * 2.0)

        # If displayColor and displayOpacity are not specified, verify that they are cleared.
        usdex.core.defineSphere(sphere.GetPrim(), newRadius)
        self.assertFalse(sphere.GetDisplayColorAttr().Get())
        self.assertFalse(sphere.GetDisplayOpacityAttr().Get())

        self.assertIsValidUsd(stage)

    # Test the defineCube function.
    def testGprimCube(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xformPath = f"/{self.defaultPrimName}/xform"
        xformPrim = usdex.core.defineXform(stage, xformPath)

        # Creates a cube as a child of the specified prim.
        cubeSize = 10.0
        cube = usdex.core.defineCube(xformPrim.GetPrim(), "cube", cubeSize)
        self.assertTrue(cube)
        self.assertEqual(cube.GetSizeAttr().Get(), cubeSize)

        # Update Size.
        newCubeSize = 15.0
        usdex.core.defineCube(cube.GetPrim(), newCubeSize)
        self.assertEqual(cube.GetSizeAttr().Get(), newCubeSize)

        # Update Display Color and Opacity.
        newDisplayColor = Gf.Vec3f(0, 1, 0)
        newDisplayOpacity = 0.5
        usdex.core.defineCube(cube.GetPrim(), newCubeSize, newDisplayColor, newDisplayOpacity)
        self.assertEqual(len(cube.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(cube.GetDisplayColorAttr().Get()[0], newDisplayColor)
        self.assertEqual(len(cube.GetDisplayOpacityAttr().Get()), 1)
        self.assertEqual(cube.GetDisplayOpacityAttr().Get()[0], newDisplayOpacity)

        # Since the size is 15, the extent is 15 x 15 x 15.
        extentAttr = cube.GetExtentAttr()
        self.assertTrue(extentAttr)
        extent = extentAttr.Get()
        extentX = extent[1][0] - extent[0][0]
        extentY = extent[1][1] - extent[0][1]
        extentZ = extent[1][2] - extent[0][2]
        self.assertEqual(extentX, newCubeSize)
        self.assertEqual(extentY, newCubeSize)
        self.assertEqual(extentZ, newCubeSize)

        # If displayColor and displayOpacity are not specified, verify that they are cleared.
        usdex.core.defineCube(cube.GetPrim(), newCubeSize)
        self.assertFalse(cube.GetDisplayColorAttr().Get())
        self.assertFalse(cube.GetDisplayOpacityAttr().Get())

        self.assertIsValidUsd(stage)

    # Test the defineCone function.
    def testGprimCone(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xformPath = f"/{self.defaultPrimName}/xform"
        xformPrim = usdex.core.defineXform(stage, xformPath)

        # Creates cones as a child of the specified prim.
        coneRadius = 4.0
        coneHeight = 10.0
        coneX = usdex.core.defineCone(xformPrim.GetPrim(), "coneX", coneRadius, coneHeight, UsdGeom.Tokens.x)
        self.assertTrue(coneX)
        self.assertEqual(coneX.GetRadiusAttr().Get(), coneRadius)
        self.assertEqual(coneX.GetHeightAttr().Get(), coneHeight)
        self.assertEqual(coneX.GetAxisAttr().Get(), UsdGeom.Tokens.x)
        self.setLocalPosition(coneX, Gf.Vec3d(0.0, 5.0, 0.0))

        coneY = usdex.core.defineCone(xformPrim.GetPrim(), "coneY", coneRadius, coneHeight, UsdGeom.Tokens.y)
        self.assertTrue(coneY)
        self.assertEqual(coneY.GetRadiusAttr().Get(), coneRadius)
        self.assertEqual(coneY.GetHeightAttr().Get(), coneHeight)
        self.assertEqual(coneY.GetAxisAttr().Get(), UsdGeom.Tokens.y)
        self.setLocalPosition(coneY, Gf.Vec3d(10.0, 5.0, 0.0))

        coneZ = usdex.core.defineCone(xformPrim.GetPrim(), "coneZ", coneRadius, coneHeight, UsdGeom.Tokens.z)
        self.assertTrue(coneZ)
        self.assertEqual(coneZ.GetRadiusAttr().Get(), coneRadius)
        self.assertEqual(coneZ.GetHeightAttr().Get(), coneHeight)
        self.assertEqual(coneZ.GetAxisAttr().Get(), UsdGeom.Tokens.z)
        self.setLocalPosition(coneZ, Gf.Vec3d(20.0, 5.0, 0.0))

        # Update Size.
        newConeRadius = 3.0
        newConeHeight = 8.0
        usdex.core.defineCone(coneY.GetPrim(), newConeRadius, newConeHeight, UsdGeom.Tokens.y)
        self.assertEqual(coneY.GetRadiusAttr().Get(), newConeRadius)
        self.assertEqual(coneY.GetHeightAttr().Get(), newConeHeight)
        self.assertEqual(coneY.GetAxisAttr().Get(), UsdGeom.Tokens.y)

        # Update Display Color and Opacity.
        newDisplayColor = Gf.Vec3f(0, 1, 0)
        newDisplayOpacity = 0.5
        usdex.core.defineCone(coneY.GetPrim(), newConeRadius, newConeHeight, UsdGeom.Tokens.y, newDisplayColor, newDisplayOpacity)
        self.assertEqual(len(coneY.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(coneY.GetDisplayColorAttr().Get()[0], newDisplayColor)
        self.assertEqual(len(coneY.GetDisplayOpacityAttr().Get()), 1)
        self.assertEqual(coneY.GetDisplayOpacityAttr().Get()[0], newDisplayOpacity)

        # Since the radius is 3 and the height is 8, the extent is 6 x 8 x 6.
        extentAttr = coneY.GetExtentAttr()
        self.assertTrue(extentAttr)
        extent = extentAttr.Get()
        extentX = extent[1][0] - extent[0][0]
        extentY = extent[1][1] - extent[0][1]
        extentZ = extent[1][2] - extent[0][2]
        self.assertEqual(extentX, newConeRadius * 2.0)
        self.assertEqual(extentY, newConeHeight)
        self.assertEqual(extentZ, newConeRadius * 2.0)

        # If displayColor and displayOpacity are not specified, verify that they are cleared.
        usdex.core.defineCone(coneY.GetPrim(), newConeRadius, newConeHeight, UsdGeom.Tokens.y)
        self.assertFalse(coneY.GetDisplayColorAttr().Get())
        self.assertFalse(coneY.GetDisplayOpacityAttr().Get())

        self.assertIsValidUsd(stage)

    # Test the defineCylinder function.
    def testGprimCylinder(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xformPath = f"/{self.defaultPrimName}/xform"
        xformPrim = usdex.core.defineXform(stage, xformPath)

        # Creates cylinders as a child of the specified prim.
        cylinderRadius = 4.0
        cylinderHeight = 10.0
        cylinderX = usdex.core.defineCylinder(xformPrim.GetPrim(), "cylinderX", cylinderRadius, cylinderHeight, UsdGeom.Tokens.x)
        self.assertTrue(cylinderX)
        self.assertEqual(cylinderX.GetRadiusAttr().Get(), cylinderRadius)
        self.assertEqual(cylinderX.GetHeightAttr().Get(), cylinderHeight)
        self.assertEqual(cylinderX.GetAxisAttr().Get(), UsdGeom.Tokens.x)
        self.setLocalPosition(cylinderX, Gf.Vec3d(0.0, 5.0, 0.0))

        cylinderY = usdex.core.defineCylinder(xformPrim.GetPrim(), "cylinderY", cylinderRadius, cylinderHeight, UsdGeom.Tokens.y)
        self.assertTrue(cylinderY)
        self.assertEqual(cylinderY.GetRadiusAttr().Get(), cylinderRadius)
        self.assertEqual(cylinderY.GetHeightAttr().Get(), cylinderHeight)
        self.assertEqual(cylinderY.GetAxisAttr().Get(), UsdGeom.Tokens.y)
        self.setLocalPosition(cylinderY, Gf.Vec3d(10.0, 5.0, 0.0))

        cylinderZ = usdex.core.defineCylinder(xformPrim.GetPrim(), "cylinderZ", cylinderRadius, cylinderHeight, UsdGeom.Tokens.z)
        self.assertTrue(cylinderZ)
        self.assertEqual(cylinderZ.GetRadiusAttr().Get(), cylinderRadius)
        self.assertEqual(cylinderZ.GetHeightAttr().Get(), cylinderHeight)
        self.assertEqual(cylinderZ.GetAxisAttr().Get(), UsdGeom.Tokens.z)
        self.setLocalPosition(cylinderZ, Gf.Vec3d(20.0, 5.0, 0.0))

        # Update Size.
        newCylinderRadius = 3.0
        newCylinderHeight = 8.0
        usdex.core.defineCylinder(cylinderY.GetPrim(), newCylinderRadius, newCylinderHeight, UsdGeom.Tokens.y)
        self.assertEqual(cylinderY.GetRadiusAttr().Get(), newCylinderRadius)
        self.assertEqual(cylinderY.GetHeightAttr().Get(), newCylinderHeight)
        self.assertEqual(cylinderY.GetAxisAttr().Get(), UsdGeom.Tokens.y)

        # Update Display Color and Opacity.
        newDisplayColor = Gf.Vec3f(0, 1, 0)
        newDisplayOpacity = 0.5
        usdex.core.defineCylinder(cylinderY.GetPrim(), newCylinderRadius, newCylinderHeight, UsdGeom.Tokens.y, newDisplayColor, newDisplayOpacity)
        self.assertEqual(len(cylinderY.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(cylinderY.GetDisplayColorAttr().Get()[0], newDisplayColor)
        self.assertEqual(len(cylinderY.GetDisplayOpacityAttr().Get()), 1)
        self.assertEqual(cylinderY.GetDisplayOpacityAttr().Get()[0], newDisplayOpacity)

        # Since the radius is 3 and the height is 8, the extent is 6 x 8 x 6.
        extentAttr = cylinderY.GetExtentAttr()
        self.assertTrue(extentAttr)
        extent = extentAttr.Get()
        extentX = extent[1][0] - extent[0][0]
        extentY = extent[1][1] - extent[0][1]
        extentZ = extent[1][2] - extent[0][2]
        self.assertEqual(extentX, newCylinderRadius * 2.0)
        self.assertEqual(extentY, newCylinderHeight)
        self.assertEqual(extentZ, newCylinderRadius * 2.0)

        # If displayColor and displayOpacity are not specified, verify that they are cleared.
        usdex.core.defineCylinder(cylinderY.GetPrim(), newCylinderRadius, newCylinderHeight, UsdGeom.Tokens.y)
        self.assertFalse(cylinderY.GetDisplayColorAttr().Get())
        self.assertFalse(cylinderY.GetDisplayOpacityAttr().Get())

        self.assertIsValidUsd(stage)

    # Test the defineCapsule function.
    def testGprimCapsule(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Create Xform.
        xformPath = f"/{self.defaultPrimName}/xform"
        xformPrim = usdex.core.defineXform(stage, xformPath)

        # Creates capsules as a child of the specified prim.
        capsuleRadius = 4.0
        capsuleHeight = 10.0
        capsuleX = usdex.core.defineCapsule(xformPrim.GetPrim(), "capsuleX", capsuleRadius, capsuleHeight, UsdGeom.Tokens.x)
        self.assertTrue(capsuleX)
        self.assertEqual(capsuleX.GetRadiusAttr().Get(), capsuleRadius)
        self.assertEqual(capsuleX.GetHeightAttr().Get(), capsuleHeight)
        self.assertEqual(capsuleX.GetAxisAttr().Get(), UsdGeom.Tokens.x)
        self.setLocalPosition(capsuleX, Gf.Vec3d(0.0, 5.0, 0.0))

        capsuleY = usdex.core.defineCapsule(xformPrim.GetPrim(), "capsuleY", capsuleRadius, capsuleHeight, UsdGeom.Tokens.y)
        self.assertTrue(capsuleY)
        self.assertEqual(capsuleY.GetRadiusAttr().Get(), capsuleRadius)
        self.assertEqual(capsuleY.GetHeightAttr().Get(), capsuleHeight)
        self.assertEqual(capsuleY.GetAxisAttr().Get(), UsdGeom.Tokens.y)
        self.setLocalPosition(capsuleY, Gf.Vec3d(15.0, 5.0, 0.0))

        capsuleZ = usdex.core.defineCapsule(xformPrim.GetPrim(), "capsuleZ", capsuleRadius, capsuleHeight, UsdGeom.Tokens.z)
        self.assertTrue(capsuleZ)
        self.assertEqual(capsuleZ.GetRadiusAttr().Get(), capsuleRadius)
        self.assertEqual(capsuleZ.GetHeightAttr().Get(), capsuleHeight)
        self.assertEqual(capsuleZ.GetAxisAttr().Get(), UsdGeom.Tokens.z)
        self.setLocalPosition(capsuleZ, Gf.Vec3d(30.0, 5.0, 0.0))

        # Update Size.
        newCapsuleRadius = 3.0
        newCapsuleHeight = 8.0
        usdex.core.defineCapsule(capsuleY.GetPrim(), newCapsuleRadius, newCapsuleHeight, UsdGeom.Tokens.y)
        self.assertEqual(capsuleY.GetRadiusAttr().Get(), newCapsuleRadius)
        self.assertEqual(capsuleY.GetHeightAttr().Get(), newCapsuleHeight)
        self.assertEqual(capsuleY.GetAxisAttr().Get(), UsdGeom.Tokens.y)

        # Update Display Color and Opacity.
        newDisplayColor = Gf.Vec3f(0, 1, 0)
        newDisplayOpacity = 0.5
        usdex.core.defineCapsule(capsuleY.GetPrim(), newCapsuleRadius, newCapsuleHeight, UsdGeom.Tokens.y, newDisplayColor, newDisplayOpacity)
        self.assertEqual(len(capsuleY.GetDisplayColorAttr().Get()), 1)
        self.assertEqual(capsuleY.GetDisplayColorAttr().Get()[0], newDisplayColor)
        self.assertEqual(len(capsuleY.GetDisplayOpacityAttr().Get()), 1)
        self.assertEqual(capsuleY.GetDisplayOpacityAttr().Get()[0], newDisplayOpacity)

        # Since the radius is 3 and the height is 8, the extent is 6 x (8 + 3 * 2) x 6.
        extentAttr = capsuleY.GetExtentAttr()
        self.assertTrue(extentAttr)
        extent = extentAttr.Get()
        extentX = extent[1][0] - extent[0][0]
        extentY = extent[1][1] - extent[0][1]
        extentZ = extent[1][2] - extent[0][2]
        self.assertEqual(extentX, newCapsuleRadius * 2.0)
        self.assertEqual(extentY, newCapsuleHeight + newCapsuleRadius * 2.0)
        self.assertEqual(extentZ, newCapsuleRadius * 2.0)

        # If displayColor and displayOpacity are not specified, verify that they are cleared.
        usdex.core.defineCapsule(capsuleY.GetPrim(), newCapsuleRadius, newCapsuleHeight, UsdGeom.Tokens.y)
        self.assertFalse(capsuleY.GetDisplayColorAttr().Get())
        self.assertFalse(capsuleY.GetDisplayOpacityAttr().Get())

        self.assertIsValidUsd(stage)
