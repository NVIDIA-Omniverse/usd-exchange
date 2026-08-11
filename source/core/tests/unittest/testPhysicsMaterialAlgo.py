# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from typing import List, Tuple

import usdex.core
import usdex.test
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade


class PhysicsMaterialAlgoTest(usdex.test.DefineFunctionTestCase):
    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.definePhysicsMaterial
    requiredArgs = tuple([0.3])
    typeName = "Material"
    schema = UsdShade.Material
    requiredPropertyNames = set(
        [
            "physics:dynamicFriction",
        ]
    )

    # Check whether the physics material is stored correctly.
    def assertIsPhysicsMaterial(self, material: UsdShade.Material, dynamicFriction: float, staticFriction: float, restitution: float, density: float):
        self.assertTrue(material.GetPrim().HasAPI(UsdPhysics.MaterialAPI))
        materialAPI = UsdPhysics.MaterialAPI(material.GetPrim())

        attr = materialAPI.GetDensityAttr()
        self.assertTrue(attr.IsDefined())
        self.assertTrue(attr.HasAuthoredValue())
        self.assertAlmostEqual(attr.Get(), density, places=6)

        attr = materialAPI.GetDynamicFrictionAttr()
        self.assertTrue(attr.IsDefined())
        self.assertTrue(attr.HasAuthoredValue())
        self.assertAlmostEqual(attr.Get(), dynamicFriction, places=6)

        attr = materialAPI.GetStaticFrictionAttr()
        self.assertTrue(attr.IsDefined())
        self.assertTrue(attr.HasAuthoredValue())
        self.assertAlmostEqual(attr.Get(), staticFriction, places=6)

        attr = materialAPI.GetRestitutionAttr()
        self.assertTrue(attr.IsDefined())
        self.assertTrue(attr.HasAuthoredValue())
        self.assertAlmostEqual(attr.Get(), restitution, places=6)

    # Create a sphere with the given parameters.
    def createSphere(self, stage: Usd.Stage, primPath: str, radius: float, color: Gf.Vec3f, position: Gf.Vec3d):
        sphereGeom = UsdGeom.Sphere.Define(stage, primPath)
        sphereGeom.CreateRadiusAttr(radius)
        sphereGeom.CreateDisplayColorAttr([color])
        prim = sphereGeom.GetPrim()
        usdex.core.setLocalTransform(
            prim, Gf.Vec3d(position), Gf.Vec3d(0, 0, 0), Gf.Vec3f(0, 0, 0), usdex.core.RotationOrder.eXyz, Gf.Vec3f(1.0, 1.0, 1.0)
        )
        return prim

    # Test the physics material define.
    def testPhysicsMaterialDefine(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        defaultPrimPath = stage.GetDefaultPrim().GetPath()
        materialPath = f"{defaultPrimPath}/physics_material"

        # Create a physics material.
        dynamicFriction = 0.5
        staticFriction = 0.1
        restitution = 0.2
        density = 0.3
        material = usdex.core.definePhysicsMaterial(stage, materialPath, dynamicFriction, staticFriction, restitution, density)
        self.assertTrue(material.GetPrim())
        self.assertIsValidUsd(stage)

        # Compare whether the value is stored correctly.
        self.assertIsPhysicsMaterial(material, dynamicFriction, staticFriction, restitution, density)

        # Create a Physics material within the specified xform.
        xformPath = f"{defaultPrimPath}/Physics"
        xform = usdex.core.defineXform(stage, xformPath)

        materialName = "physics_material2"
        dynamicFriction = 0.32
        staticFriction = 0.15
        restitution = 0.25
        density = 0.35
        material = usdex.core.definePhysicsMaterial(xform.GetPrim(), materialName, dynamicFriction, staticFriction, restitution, density)
        self.assertTrue(material.GetPrim())
        self.assertIsValidUsd(stage)

        # Compare whether the value is stored correctly.
        self.assertIsPhysicsMaterial(material, dynamicFriction, staticFriction, restitution, density)

        dynamicFriction = 0.2
        staticFriction = 0.12
        restitution = 0.01
        density = 0.8
        self.assertTrue(usdex.core.addPhysicsToMaterial(material, dynamicFriction, staticFriction, restitution, density))
        self.assertIsValidUsd(stage)

        # Compare whether the value is stored correctly.
        self.assertIsPhysicsMaterial(material, dynamicFriction, staticFriction, restitution, density)

    # Test the physics material bind with an existing material.
    def testPhysicsMaterialDefine_existingMaterial(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        defaultPrimPath = stage.GetDefaultPrim().GetPath()
        materialPath = f"{defaultPrimPath}/material"

        # Create a visual material.
        diffuseColor = Gf.Vec3f(0, 1, 0)
        opacity = 1.0
        roughness = 0.3
        metallic = 1.0
        material = usdex.core.definePreviewMaterial(stage, materialPath, diffuseColor, opacity, roughness, metallic)
        self.assertTrue(material.GetPrim())

        # Assigning physics materials to prims of the same material.
        dynamicFriction = 0.3
        staticFriction = 0.1
        restitution = 0.2
        density = 0.1
        material = usdex.core.definePhysicsMaterial(material.GetPrim(), dynamicFriction, staticFriction, restitution, density)

        self.assertIsValidUsd(stage)

        # Check Visual Material Connection.
        surfaceConnect = material.GetSurfaceOutput().GetValueProducingAttributes()
        self.assertEqual(len(surfaceConnect), 1)
        self.assertEqual(surfaceConnect[0].GetPrim().GetPath(), f"{material.GetPrim().GetPath()}/PreviewSurface")

        # Compare whether the physics material is stored correctly.
        self.assertIsPhysicsMaterial(material, dynamicFriction, staticFriction, restitution, density)

        # Add physics to the material.
        dynamicFriction = 0.1
        self.assertTrue(usdex.core.addPhysicsToMaterial(material, dynamicFriction))
        self.assertIsValidUsd(stage)

        # Compare whether the physics material is stored correctly.
        # Check that dynamicFriction has been updated and that the other parameters remain the same.
        self.assertIsPhysicsMaterial(material, dynamicFriction, staticFriction, restitution, density)

    # Test the physics material bind.
    def testPhysicsMaterialBind(self):
        stage = Usd.Stage.CreateInMemory()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        defaultPrimPath = stage.GetDefaultPrim().GetPath()
        materialPath = f"{defaultPrimPath}/physics_material"

        # ------------------------------------------------------------.
        # Bind physics material to a sphere.
        # ------------------------------------------------------------.
        # Create a physics material.
        dynamicFriction = 0.5
        staticFriction = 0.1
        restitution = 0.2
        density = 0.3
        physics_material = usdex.core.definePhysicsMaterial(stage, materialPath, dynamicFriction, staticFriction, restitution, density)
        self.assertTrue(physics_material.GetPrim())
        self.assertIsValidUsd(stage)

        # Create a sphere.
        spherePath = f"{defaultPrimPath}/sphere"
        position = Gf.Vec3f(0.0, 50.0, 0.0)
        spherePrim = self.createSphere(stage, spherePath, 0.5, Gf.Vec3f(1.0, 0.0, 0.0), position)
        self.assertTrue(spherePrim)

        self.assertTrue(usdex.core.bindPhysicsMaterial(spherePrim, physics_material))
        self.assertIsValidUsd(stage)

        # Get and check material bindings.
        rel = UsdShade.MaterialBindingAPI(spherePrim).GetDirectBindingRel("physics")
        pathList = rel.GetTargets()
        self.assertEqual(len(pathList), 1)
        self.assertEqual(pathList[0], physics_material.GetPrim().GetPath())

        # ------------------------------------------------------------.
        # Bind the visual material first, then the physics material.
        # ------------------------------------------------------------.
        # Create a sphere.
        spherePath = f"{defaultPrimPath}/sphere2"
        position = Gf.Vec3f(2.0, 50.0, 0.0)
        spherePrim = self.createSphere(stage, spherePath, 0.5, Gf.Vec3f(1.0, 0.0, 0.0), position)
        self.assertTrue(spherePrim)

        # Create a visual material.
        materialPath = f"{defaultPrimPath}/visual_material"
        diffuseColor = Gf.Vec3f(0, 1, 0)
        opacity = 1.0
        roughness = 0.3
        metallic = 1.0
        visual_material = usdex.core.definePreviewMaterial(stage, materialPath, diffuseColor, opacity, roughness, metallic)
        self.assertTrue(visual_material.GetPrim())

        # Bind visual material.
        self.assertTrue(usdex.core.bindMaterial(spherePrim, visual_material))

        # Bind physics material.
        self.assertTrue(usdex.core.bindPhysicsMaterial(spherePrim, physics_material))

        # Get and check visual material bindings.
        rel = UsdShade.MaterialBindingAPI(spherePrim).GetDirectBindingRel()
        pathList = rel.GetTargets()
        self.assertEqual(len(pathList), 1)
        self.assertEqual(pathList[0], visual_material.GetPrim().GetPath())

        # Get and check physics material bindings.
        rel = UsdShade.MaterialBindingAPI(spherePrim).GetDirectBindingRel("physics")
        pathList = rel.GetTargets()
        self.assertEqual(len(pathList), 1)
        self.assertEqual(pathList[0], physics_material.GetPrim().GetPath())

        # ------------------------------------------------------------.
        # Bind the physics material first, then the visual material.
        # ------------------------------------------------------------.
        # Create a sphere.
        spherePath = f"{defaultPrimPath}/sphere3"
        position = Gf.Vec3f(4.0, 50.0, 0.0)
        spherePrim = self.createSphere(stage, spherePath, 0.5, Gf.Vec3f(1.0, 0.0, 0.0), position)
        self.assertTrue(spherePrim)

        # Bind physics material.
        self.assertTrue(usdex.core.bindPhysicsMaterial(spherePrim, physics_material))

        # Bind visual material.
        self.assertTrue(usdex.core.bindMaterial(spherePrim, visual_material))

        # Get and check visual material bindings.
        rel = UsdShade.MaterialBindingAPI(spherePrim).GetDirectBindingRel()
        pathList = rel.GetTargets()
        self.assertEqual(len(pathList), 1)
        self.assertEqual(pathList[0], visual_material.GetPrim().GetPath())

        # Get and check physics material bindings.
        rel = UsdShade.MaterialBindingAPI(spherePrim).GetDirectBindingRel("physics")
        pathList = rel.GetTargets()
        self.assertEqual(len(pathList), 1)
        self.assertEqual(pathList[0], physics_material.GetPrim().GetPath())

        # ------------------------------------------------------------.
        # Create and bind a material that has both visual and physics properties.
        # ------------------------------------------------------------.
        # Create a sphere.
        spherePath = f"{defaultPrimPath}/sphere4"
        position = Gf.Vec3f(6.0, 50.0, 0.0)
        spherePrim = self.createSphere(stage, spherePath, 0.5, Gf.Vec3f(1.0, 0.0, 0.0), position)
        self.assertTrue(spherePrim)

        # Create a visual material.
        materialPath = f"{defaultPrimPath}/visual_physics_material"
        diffuseColor = Gf.Vec3f(0, 1, 0)
        opacity = 1.0
        roughness = 0.3
        metallic = 1.0
        visual_physics_material = usdex.core.definePreviewMaterial(stage, materialPath, diffuseColor, opacity, roughness, metallic)
        self.assertTrue(visual_physics_material.GetPrim())

        # add physics material.
        dynamicFriction = 0.5
        staticFriction = 0.1
        restitution = 0.2
        density = 0.3
        usdex.core.addPhysicsToMaterial(visual_physics_material, dynamicFriction, staticFriction, restitution, density)
        self.assertTrue(visual_physics_material.GetPrim())

        # Bind material.
        self.assertTrue(usdex.core.bindMaterial(spherePrim, visual_physics_material))
        self.assertTrue(usdex.core.bindPhysicsMaterial(spherePrim, visual_physics_material))

        # Get and check visual material bindings.
        rel = UsdShade.MaterialBindingAPI(spherePrim).GetDirectBindingRel()
        pathList = rel.GetTargets()
        self.assertEqual(len(pathList), 1)
        self.assertEqual(pathList[0], visual_physics_material.GetPrim().GetPath())

        # Get and check physics material bindings.
        rel = UsdShade.MaterialBindingAPI(spherePrim).GetDirectBindingRel("physics")
        pathList = rel.GetTargets()
        self.assertEqual(len(pathList), 1)
        self.assertEqual(pathList[0], visual_physics_material.GetPrim().GetPath())

        self.assertIsValidUsd(stage)
