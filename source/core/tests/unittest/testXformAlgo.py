# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import usdex.core
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, Vt

IDENTITY_TRANSLATE = Gf.Vec3d(0.0, 0.0, 0.0)
IDENTITY_ROTATE = Gf.Vec3f(0.0, 0.0, 0.0)
IDENTITY_SCALE = Gf.Vec3f(1.0, 1.0, 1.0)
IDENTITY_MATRIX = Gf.Matrix4d().SetIdentity()
IDENTITY_TRANSFORM = Gf.Transform().SetIdentity()
IDENTITY_ORIENTATION = Gf.Quatf.GetIdentity()

IDENTITY_COMPONENTS = tuple(
    [
        IDENTITY_TRANSLATE,
        IDENTITY_TRANSLATE,
        IDENTITY_ROTATE,
        usdex.core.RotationOrder.eXyz,
        IDENTITY_SCALE,
    ],
)

IDENTITY_COMPONENTS_WITH_ORIENTATION_AND_PIVOT = tuple(
    [
        IDENTITY_TRANSLATE,
        IDENTITY_TRANSLATE,
        IDENTITY_ORIENTATION,
        IDENTITY_SCALE,
    ],
)

IDENTITY_COMPONENTS_WITH_ORIENTATION = tuple(
    [
        IDENTITY_TRANSLATE,
        IDENTITY_ORIENTATION,
        IDENTITY_SCALE,
    ],
)

NON_IDENTITY_TRANSLATE = Gf.Vec3d(10.0, 20.0, 30.0)
NON_IDENTITY_ROTATE = Gf.Vec3f(45.0, 0.0, 0.0)
NON_IDENTITY_SCALE = Gf.Vec3f(2.0, 2.0, 2.0)
NON_IDENTITY_ROTATION = Gf.Rotation(Gf.Vec3d.XAxis(), 45.0)
NON_IDENTITY_ORIENTATION = Gf.Quatf(NON_IDENTITY_ROTATION.GetQuat())

NON_IDENTITY_COMPONENTS = tuple(
    [
        NON_IDENTITY_TRANSLATE,
        NON_IDENTITY_TRANSLATE,
        NON_IDENTITY_ROTATE,
        usdex.core.RotationOrder.eXyz,
        NON_IDENTITY_SCALE,
    ],
)

NON_IDENTITY_COMPONENTS_WITH_ORIENTATION_AND_PIVOT = tuple(
    [
        NON_IDENTITY_TRANSLATE,
        NON_IDENTITY_TRANSLATE,
        NON_IDENTITY_ORIENTATION,
        NON_IDENTITY_SCALE,
    ],
)

NON_IDENTITY_COMPONENTS_WITH_ORIENTATION = tuple(
    [
        NON_IDENTITY_TRANSLATE,
        NON_IDENTITY_ORIENTATION,
        NON_IDENTITY_SCALE,
    ],
)

NON_IDENTITY_TRANSFORM = Gf.Transform()
NON_IDENTITY_TRANSFORM.SetTranslation(NON_IDENTITY_TRANSLATE)
NON_IDENTITY_TRANSFORM.SetRotation(NON_IDENTITY_ROTATION)
NON_IDENTITY_TRANSFORM.SetScale(Gf.Vec3d(NON_IDENTITY_SCALE))
NON_IDENTITY_NO_PIVOT_MATRIX = NON_IDENTITY_TRANSFORM.GetMatrix()
NON_IDENTITY_TRANSFORM.SetPivotPosition(NON_IDENTITY_TRANSLATE)

PIVOT_POSITION_TRANSFORM = Gf.Transform()
PIVOT_POSITION_TRANSFORM.SetPivotPosition(NON_IDENTITY_TRANSLATE)

PIVOT_POSITION_AND_ORIENTATION_TRANSFORM = Gf.Transform()
PIVOT_POSITION_AND_ORIENTATION_TRANSFORM.SetPivotPosition(NON_IDENTITY_TRANSLATE)
PIVOT_POSITION_AND_ORIENTATION_TRANSFORM.SetPivotOrientation(NON_IDENTITY_ROTATION)

NON_IDENTITY_MATRIX = NON_IDENTITY_TRANSFORM.GetMatrix()

MATRIX_XFORM_OP_ORDER = Vt.TokenArray(["xformOp:transform"])
COMPONENT_XFORM_OP_ORDER = Vt.TokenArray(
    [
        "xformOp:translate",
        "xformOp:translate:pivot",
        "xformOp:rotateXYZ",
        "xformOp:scale",
        "!invert!xformOp:translate:pivot",
    ]
)
COMPONENT_WITH_ORIENTATION_AND_PIVOT_XFORM_OP_ORDER = Vt.TokenArray(
    [
        "xformOp:translate",
        "xformOp:translate:pivot",
        "xformOp:orient",
        "xformOp:scale",
        "!invert!xformOp:translate:pivot",
    ]
)
COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER = Vt.TokenArray(
    [
        "xformOp:translate",
        "xformOp:orient",
        "xformOp:scale",
    ]
)


class BaseXformTestCase(usdex.test.TestCase):

    def _createTestStage(self):
        """Create an in memory stage holding a range of prims that are useful for testing"""

        # Build a layered stage
        weakerLayer = self.tmpLayer(name="Weaker")
        strongerLayer = self.tmpLayer(name="Stronger")

        rootLayer = Sdf.Layer.CreateAnonymous()
        rootLayer.subLayerPaths.append(strongerLayer.identifier)
        rootLayer.subLayerPaths.append(weakerLayer.identifier)

        stage = Usd.Stage.Open(rootLayer)

        # Define the standard "/Root" prim in the root layer
        stage.SetEditTarget(Usd.EditTarget(rootLayer))
        usdex.core.defineXform(stage, "/Root").GetPrim()
        usdex.core.configureStage(stage, self.defaultPrimName, self.defaultUpAxis, self.defaultLinearUnits, self.defaultAuthoringMetadata)

        # Define test prims in the weaker layer
        stage.SetEditTarget(Usd.EditTarget(weakerLayer))

        # Define an xformable (Xform) and a non-xformable (Scope) prim with no transforms
        usdex.core.defineXform(stage, "/Root/Xform")
        UsdGeom.Scope.Define(stage, "/Root/Scope")

        # Define an xformable (Xform) with a default and time sampled transform matrix
        xform = usdex.core.defineXform(stage, "/Root/Animated_Matrix")
        xformOp = xform.MakeMatrixXform()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))
        xformOp.Set(transform.GetMatrix(), Usd.TimeCode.Default())

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(40.0, 50.0, 60.0))
        xformOp.Set(transform.GetMatrix(), Usd.TimeCode(0.0))

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(70.0, 80.0, 90.0))
        xformOp.Set(transform.GetMatrix(), Usd.TimeCode(10.0))

        # Define an xformable (Xform) with xformOps but an empty xformOpOrder
        xform = usdex.core.defineXform(stage, "/Root/Empty_Xform_Op_Order")
        xformOp = xform.MakeMatrixXform()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))
        xformOp.Set(transform.GetMatrix(), Usd.TimeCode.Default())

        xform.ClearXformOpOrder()

        # Define an xformable (Xform) with a matrix xformOp and matching xformOpOrder
        xform = usdex.core.defineXform(stage, "/Root/Matrix_Xform_Op_Order")
        xformOp = xform.MakeMatrixXform()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))
        xformOp.Set(transform.GetMatrix(), Usd.TimeCode.Default())

        # Define an xformable (Xform) with default and time sampled transform components using the XformCommonAPI
        xform = usdex.core.defineXform(stage, "/Root/Animated_Xform_Common_API")
        xformCommonAPI = UsdGeom.XformCommonAPI(xform.GetPrim())
        xformOps = xformCommonAPI.CreateXformOps(
            UsdGeom.XformCommonAPI.RotationOrderXYZ,
            UsdGeom.XformCommonAPI.OpTranslate,
            UsdGeom.XformCommonAPI.OpRotate,
        )

        # Set time samples on the translate
        translateXformOp = xformOps[0]
        translateXformOp.Set(Gf.Vec3d(10.0, 20.0, 30.0), Usd.TimeCode.Default())
        translateXformOp.Set(Gf.Vec3d(40.0, 50.0, 60.0), Usd.TimeCode(0.0))
        translateXformOp.Set(Gf.Vec3d(70.0, 80.0, 90.0), Usd.TimeCode(10.0))

        # Set time samples on the rotate
        # The rotation is intentionally greater than 360 degrees as this which will cause data loss when using a 4x4 matrix
        rotateXformOp = xformOps[2]
        rotateXformOp.Set(Gf.Vec3f(360.0, 360.0, 0.0), Usd.TimeCode.Default())
        rotateXformOp.Set(Gf.Vec3f(180.0, 0.0, 0.0), Usd.TimeCode(0.0))
        rotateXformOp.Set(Gf.Vec3f(540.0, 0.0, 0.0), Usd.TimeCode(10.0))

        # Create a Prim and then add an instanceable reference to it from within /Root
        # This can be used to create scenarios where a path points to an instance proxy prim.
        stage.CreateClassPrim("/Prototypes")
        usdex.core.defineXform(stage, "/Prototypes/Prototype")
        xformPrim = usdex.core.defineXform(stage, "/Root/Instance").GetPrim()
        xformPrim.GetReferences().AddInternalReference(Sdf.Path("/Prototypes/Prototype"))
        xformPrim.SetInstanceable(True)

        # Set the edit target to the stronger layer
        stage.SetEditTarget(Usd.EditTarget(strongerLayer))

        self.assertIsValidUsd(stage)

        return stage

    def assertTupleWithQuatAlmostEqual(self, tuple1, tuple2, places=6):
        for vector in range(len(tuple1)):
            if isinstance(tuple1[vector], Gf.Quatf):
                self.assertAlmostEqual(abs(Gf.Dot(tuple1[vector], tuple2[vector])), 1.0, places=places)
            else:
                self.assertAlmostEqual(tuple1[vector], tuple2[vector])

    def assertNoExtraneousXformOps(self, prim):
        xformable = UsdGeom.Xformable(prim)
        xformOpOrder = xformable.GetXformOpOrderAttr().Get()
        for prop in prim.GetAuthoredPropertyNames():
            if prop.startswith("xformOp:"):
                self.assertIn(prop, xformOpOrder, f"Found xformOp {prop} not in xformOpOrder")

    @staticmethod
    def _removeXformableProperties(prim):
        """Remove attributes from the UsdGeom.Xformable schema from a prim"""
        # This function will only remove properties from the current edit targets layer
        for name in prim.GetAuthoredPropertyNames():
            # Remove schema explicit properties
            if name == UsdGeom.Tokens.xformOpOrder:
                prim.RemoveProperty(name)
                continue
            # Remove schema namespaced properties
            if name.startswith("xformOp:"):
                prim.RemoveProperty(name)
                continue

    @staticmethod
    def _getOrderedXformOpPrecisions(xformable):
        """Return a list of the precision of each xformOp in the xformOpOrder"""
        return [x.GetPrecision() for x in xformable.GetOrderedXformOps() if not x.IsInverseOp()]


class BaseSetLocalTransformTestCase(BaseXformTestCase):
    def assertValuesAuthoredForXformOpsAtTimes(self, xformable, times):
        """Assert that for all the xformOps in the xformOpOrder there are authored values at all the given times"""
        for xformOp in xformable.GetOrderedXformOps():

            # Skip inverse xformOps because they do not have an associated attribute
            if xformOp.IsInverseOp():
                continue

            attr = xformOp.GetAttr()
            for time in times:
                self.assertAttributeHasAuthoredValue(attr, time)

    def assertSuccessfulSetLocalTransform(self, prim):
        """Assert that the local transform was successfully set"""
        layer = prim.GetStage().GetEditTarget().GetLayer()
        xformable = UsdGeom.Xformable(prim)

        # The xform op order attribute should be authored in the current edit target layer
        attr = xformable.GetXformOpOrderAttr()
        attrSpec = layer.GetAttributeAtPath(attr.GetPath())
        self.assertTrue(attr.IsAuthored())
        self.assertTrue(attrSpec)


class SetLocalTransformWithTransformTestCase(BaseSetLocalTransformTestCase):
    def testInvalidPrims(self):
        # An invalid or non-xformable prim will produce a failure return
        stage = self._createTestStage()

        # An invalid prim will produce a failure return
        prim = stage.GetPrimAtPath("/Root/Invalid")
        success = usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertFalse(success)

        # A non-xformable prim will produce a failure return
        prim = stage.GetPrimAtPath("/Root/Scope")
        success = usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertFalse(success)
        self.assertIsValidUsd(stage)

    def testValidPrim(self):
        # A valid xformable prim will produce a success return
        stage = self._createTestStage()

        # An xformable prim with no xformOps will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Xform")
        success = usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)

        # An xformable prim with an empty xformOpOrder will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Empty_Xform_Op_Order")
        success = usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)

        # An xformable prim with an xformOpOrder in a weaker layer will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Matrix_Xform_Op_Order")
        success = usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertIsValidUsd(stage)

    def testTimeArgument(self):
        # The "time" argument is supported but optional
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # In cases where there is no authored xformOpOrder
        # The xformOpOrder attribute should be authored on the prim if the function call is successful
        # All the xformOps in the stack should have values at the "time" that was specified

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test without specifying a time
        # The default time should be used
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode.Default()])

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test default time
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM, Usd.TimeCode.Default())
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode.Default()])

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test a time sample
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM, Usd.TimeCode(5.0))
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0)])

        # Test a second time sample
        # The new and previous time sample should be authored
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM, Usd.TimeCode(10.0))
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0), Usd.TimeCode(10.0)])

        # Test setting the default time when time samples are present
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM, Usd.TimeCode.Default())
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0), Usd.TimeCode(10.0), Usd.TimeCode.Default()])
        self.assertIsValidUsd(stage)

    def testDefaultXformOpOrder(self):
        # Assert the xformOpOrder used when there is no existing opinion
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # An identity transform will be stored as a single transform op and the computed matrix will match that of the
        # transform that was passed in.
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), MATRIX_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_TRANSFORM.GetMatrix())

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # A transform with a pivot position will be stored as components in order to retain the pivot
        usdex.core.setLocalTransform(prim, PIVOT_POSITION_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), PIVOT_POSITION_TRANSFORM.GetMatrix())

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # A transform with a pivot position and a pivot orientation will be stored as matrix because components cannot encode
        # the pivot orientation
        usdex.core.setLocalTransform(prim, PIVOT_POSITION_AND_ORIENTATION_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), MATRIX_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), PIVOT_POSITION_AND_ORIENTATION_TRANSFORM.GetMatrix())

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Setting a value that cannot be encoded will result in a new xformOpOrder even if there are existing ops of the other format.
        # Start with a matrix xformOpOrder
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), MATRIX_XFORM_OP_ORDER)

        # Setting a transform with a pivot position will switch to a component xformOpOrder
        usdex.core.setLocalTransform(prim, PIVOT_POSITION_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)

        # Setting a transform with a pivot position and pivot orientation will switch to a matrix xformOpOrder
        usdex.core.setLocalTransform(prim, PIVOT_POSITION_AND_ORIENTATION_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), MATRIX_XFORM_OP_ORDER)
        self.assertIsValidUsd(stage)

    def testReuseTransformOps(self):
        # If there is a single transform xformOp authored then that should be reused
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Add a transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp()

        # When a transform xformOp is authored it should be reused
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), Vt.TokenArray([xformOp.GetOpName()]))
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Add a transform xformOp that has a custom suffix
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(opSuffix="custom")

        # When a transform xformOp that has an op suffix is authored it should be reused
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), Vt.TokenArray([xformOp.GetOpName()]))
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Add an inverse transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(isInverseOp=True)

        # When an inverse transform xformOp is authored it should not be reused
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), MATRIX_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Clean the prim and add a transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(opSuffix="custom")

        # Setting a transform with a pivot position at this point will not reuse the transform xformOp because this would discard the pivot position.
        # Fidelity of components takes precedence over existing authored xformOpOrders.
        usdex.core.setLocalTransform(prim, PIVOT_POSITION_TRANSFORM)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), PIVOT_POSITION_TRANSFORM.GetMatrix())
        self.assertIsValidUsd(stage)

    def testReuseComponentOps(self):
        # If there are existing xformOps that are considered valid by the XformCommonAPI then these should be reused
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Add all the XformCommonAPI xformOps with an unexpected precisions
        self._removeXformableProperties(prim)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionFloat)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionHalf, opSuffix="pivot")
        xformable.AddRotateXYZOp(precision=UsdGeom.XformOp.PrecisionDouble)
        xformable.AddScaleOp(precision=UsdGeom.XformOp.PrecisionDouble)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionHalf, opSuffix="pivot", isInverseOp=True)

        # Precisions authored originally, these should be unchanged after setting the local transform
        precisions = [
            UsdGeom.XformOp.PrecisionFloat,  # translate
            UsdGeom.XformOp.PrecisionHalf,  # pivot
            UsdGeom.XformOp.PrecisionDouble,  # rotate
            UsdGeom.XformOp.PrecisionDouble,  # scale
        ]

        # When component xform ops already exist but have an unexpected precision they should be reused
        # Coding errors should not be reported
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(self._getOrderedXformOpPrecisions(xformable), precisions)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

        # Add a subset of the XformCommonAPI xformOps with an unexpected precisions
        self._removeXformableProperties(prim)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionFloat)
        xformable.AddRotateXYZOp(precision=UsdGeom.XformOp.PrecisionDouble)

        # Precisions authored originally and the default that will be created, these should be unchanged after setting the local transform
        precisions = [
            UsdGeom.XformOp.PrecisionFloat,  # translate
            UsdGeom.XformOp.PrecisionFloat,  # pivot default
            UsdGeom.XformOp.PrecisionDouble,  # rotate
            UsdGeom.XformOp.PrecisionFloat,  # scale default
        ]

        # When component xform ops already exist but have an unexpected precision they should be reused
        # Un-authored xform ops will be created and use the default precision of the UsdGeomXformCommonAPI
        # Coding errors should not be reported
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(self._getOrderedXformOpPrecisions(xformable), precisions)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)

    def testRoundTrip(self):
        # The computed local transform matrix of a prim should match the transforms matrix after being set on the prim
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # An identity matrix
        usdex.core.setLocalTransform(prim, IDENTITY_TRANSFORM)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_TRANSFORM.GetMatrix())

        # A non-identity matrix
        usdex.core.setLocalTransform(prim, NON_IDENTITY_TRANSFORM)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_TRANSFORM.GetMatrix())
        self.assertIsValidUsd(stage)


class SetLocalTransformWithMatrixTestCase(BaseSetLocalTransformTestCase):
    def testInvalidPrims(self):
        # An invalid or non-xformable prim will produce a failure return
        stage = self._createTestStage()

        # An invalid prim will produce a failure return
        prim = stage.GetPrimAtPath("/Root/Invalid")
        success = usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertFalse(success)

        # A non-xformable prim will produce a failure return
        prim = stage.GetPrimAtPath("/Root/Scope")
        success = usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertFalse(success)
        self.assertIsValidUsd(stage)

    def testValidPrim(self):
        # A valid xformable prim will produce a success return
        stage = self._createTestStage()

        # An xformable prim with no xformOps will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Xform")
        success = usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)

        # An xformable prim with an empty xformOpOrder will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Empty_Xform_Op_Order")
        success = usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)

        # An xformable prim with an xformOpOrder in a weaker layer will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Matrix_Xform_Op_Order")
        success = usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertIsValidUsd(stage)

    def testTimeArgument(self):
        # The "time" argument is supported but optional
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # In cases where there is no authored xformOpOrder
        # The xformOpOrder attribute should be authored on the prim if the function call is successful
        # All the xformOps in the stack should have values at the "time" that was specified

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test without specifying a time
        # The default time should be used
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode.Default()])

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test default time
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX, Usd.TimeCode.Default())
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode.Default()])

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test a time sample
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX, Usd.TimeCode(5.0))
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0)])

        # Test a second time sample
        # The new and previous time sample should be authored
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX, Usd.TimeCode(10.0))
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0), Usd.TimeCode(10.0)])

        # Test setting the default time when time samples are present
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX, Usd.TimeCode.Default())
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0), Usd.TimeCode(10.0), Usd.TimeCode.Default()])
        self.assertIsValidUsd(stage)

    def testReuseTransformOps(self):
        # If there is a single transform xformOp authored then that should be reused
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Add a transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp()

        # When a transform xformOp is authored it should be reused
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), Vt.TokenArray([xformOp.GetOpName()]))
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Add a transform xformOp that has a custom suffix
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(opSuffix="custom")

        # When a transform xformOp that has an op suffix is authored it should be reused
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), Vt.TokenArray([xformOp.GetOpName()]))
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Add an inverse transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(isInverseOp=True)

        # When an inverse transform xformOp is authored it should not be reused
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), MATRIX_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)

    def testRoundTrip(self):
        # The computed local transform matrix of a prim should match the matrix after being set on the prim
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # An identity matrix
        usdex.core.setLocalTransform(prim, IDENTITY_MATRIX)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # A non-identity matrix
        usdex.core.setLocalTransform(prim, NON_IDENTITY_MATRIX)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)


class SetLocalTransformWithComponentsTestCase(BaseSetLocalTransformTestCase):
    def testInvalidPrims(self):
        # An invalid or non-xformable prim will produce a failure return
        stage = self._createTestStage()

        # An invalid prim will produce a failure return
        prim = stage.GetPrimAtPath("/Root/Invalid")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertFalse(success)

        # A non-xformable prim will produce a failure return
        prim = stage.GetPrimAtPath("/Root/Scope")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertFalse(success)
        self.assertIsValidUsd(stage)

    def testValidPrim(self):
        # A valid xformable prim will produce a success return
        stage = self._createTestStage()

        # An xformable prim with no xformOps will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Xform")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)

        # An xformable prim with an empty xformOpOrder will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Empty_Xform_Op_Order")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)

        # An xformable prim with an xformOpOrder in a weaker layer will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Matrix_Xform_Op_Order")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertIsValidUsd(stage)

    def testTimeArgument(self):
        # The "time" argument is supported but optional
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # In cases where there is no authored xformOpOrder
        # The xformOpOrder attribute should be authored on the prim if the function call is successful
        # All the xformOps in the stack should have values at the "time" that was specified

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test without specifying a time
        # The default time should be used
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode.Default()])

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test default time
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS, Usd.TimeCode.Default())
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode.Default()])

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test a time sample
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS, Usd.TimeCode(5.0))
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0)])

        # Test a second time sample
        # The new and previous time sample should be authored
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS, Usd.TimeCode(10.0))
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0), Usd.TimeCode(10.0)])

        # Test setting the default time when time samples are present
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS, Usd.TimeCode.Default())
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0), Usd.TimeCode(10.0), Usd.TimeCode.Default()])
        self.assertIsValidUsd(stage)

    def testDefaultXformOpOrder(self):
        # Assert the xformOpOrder used when there is no existing opinion
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Identity components will be stored as components
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Non-identity components will be stored as components
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertIsValidUsd(stage)

    def testReuseTransformOps(self):
        # If there is a single transform xformOp authored then that should be reused
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Add a transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp()

        # When a transform xformOp is authored it should be reused
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), Vt.TokenArray([xformOp.GetOpName()]))
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Add a transform xformOp that has a custom suffix
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(opSuffix="custom")

        # When a transform xformOp that has an op suffix is authored it should be reused
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), Vt.TokenArray([xformOp.GetOpName()]))
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Add an inverse transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(isInverseOp=True)

        # When an inverse transform xformOp is authored it should not be reused
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Clean the prim and add a transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(opSuffix="custom")

        # Setting components with a pivot position at this point will not reuse the transform xformOp because this would discard the pivot position.
        # Fidelity of components takes precedence over existing authored xformOpOrders.
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)

    def testReuseComponentOps(self):
        # If there are existing xformOps that are considered valid by the XformCommonAPI then these should be reused
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Add all the XformCommonAPI xformOps with an unexpected precisions
        self._removeXformableProperties(prim)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionFloat)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionHalf, opSuffix="pivot")
        xformable.AddRotateXYZOp(precision=UsdGeom.XformOp.PrecisionDouble)
        xformable.AddScaleOp(precision=UsdGeom.XformOp.PrecisionDouble)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionHalf, opSuffix="pivot", isInverseOp=True)

        # Precisions authored originally, these should be unchanged after setting the local transform
        precisions = [
            UsdGeom.XformOp.PrecisionFloat,  # translate
            UsdGeom.XformOp.PrecisionHalf,  # pivot
            UsdGeom.XformOp.PrecisionDouble,  # rotate
            UsdGeom.XformOp.PrecisionDouble,  # scale
        ]

        # When component xform ops already exist but have an unexpected precision they should be reused
        # Coding errors should not be reported
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(self._getOrderedXformOpPrecisions(xformable), precisions)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

        # Add a subset of the XformCommonAPI xformOps with an unexpected precisions
        self._removeXformableProperties(prim)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionFloat)
        xformable.AddRotateXYZOp(precision=UsdGeom.XformOp.PrecisionDouble)

        # Precisions authored originally and the default that will be created, these should be unchanged after setting the local transform
        precisions = [
            UsdGeom.XformOp.PrecisionFloat,  # translate
            UsdGeom.XformOp.PrecisionFloat,  # pivot default
            UsdGeom.XformOp.PrecisionDouble,  # rotate
            UsdGeom.XformOp.PrecisionFloat,  # scale default
        ]

        # When component xform ops already exist but have an unexpected precision they should be reused
        # Un-authored xform ops will be created and use the default precision of the UsdGeomXformCommonAPI
        # Coding errors should not be reported
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(self._getOrderedXformOpPrecisions(xformable), precisions)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)

    def testRoundTrip(self):
        # The computed local transform matrix of a prim should match the transform components matrix after being set on the prim
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # An identity matrix
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # A non-identity matrix
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)


class SetLocalTransformWithOrientationTestCase(BaseSetLocalTransformTestCase):
    def testInvalidPrims(self):
        # An invalid or non-xformable prim will produce a failure return
        stage = self._createTestStage()

        # An invalid prim will produce a failure return
        prim = stage.GetPrimAtPath("/Root/Invalid")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertFalse(success)

        # A non-xformable prim will produce a failure return
        prim = stage.GetPrimAtPath("/Root/Scope")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertFalse(success)
        self.assertIsValidUsd(stage)

    def testValidPrim(self):
        # A valid xformable prim will produce a success return
        stage = self._createTestStage()

        # An xformable prim with no xformOps will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Xform")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)

        # An xformable prim with an empty xformOpOrder will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Empty_Xform_Op_Order")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)

        # An xformable prim with an xformOpOrder in a weaker layer will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Matrix_Xform_Op_Order")
        success = usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertIsValidUsd(stage)

    def testDefaultScale(self):
        # The default scale should be used if no scale is authored
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)
        self._removeXformableProperties(prim)
        success = usdex.core.setLocalTransform(prim, translation=NON_IDENTITY_TRANSLATE, orientation=NON_IDENTITY_ORIENTATION)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetScaleOp().Get(), IDENTITY_SCALE)

        # Author a non-identity scale, then check that default scale still works
        xformable.GetScaleOp().Set(NON_IDENTITY_SCALE)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_NO_PIVOT_MATRIX, 1e-6))

        success = usdex.core.setLocalTransform(prim, translation=NON_IDENTITY_TRANSLATE, orientation=NON_IDENTITY_ORIENTATION)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetScaleOp().Get(), IDENTITY_SCALE)

    def testTimeArgument(self):
        # The "time" argument is supported but optional
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # In cases where there is no authored xformOpOrder
        # The xformOpOrder attribute should be authored on the prim if the function call is successful
        # All the xformOps in the stack should have values at the "time" that was specified

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test without specifying a time
        # The default time should be used
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode.Default()])

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test default time
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION, Usd.TimeCode.Default())
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode.Default()])

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Test a time sample
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION, Usd.TimeCode(5.0))
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0)])

        # Test a second time sample
        # The new and previous time sample should be authored
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION, Usd.TimeCode(10.0))
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0), Usd.TimeCode(10.0)])

        # Test setting the default time when time samples are present
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION, Usd.TimeCode.Default())
        self.assertTrue(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertValuesAuthoredForXformOpsAtTimes(xformable, [Usd.TimeCode(5.0), Usd.TimeCode(10.0), Usd.TimeCode.Default()])
        self.assertIsValidUsd(stage)

    def testDefaultXformOpOrder(self):
        # Assert the xformOpOrder used when there is no existing opinion
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Identity components with orientation will be stored as components
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)

        # Clean the prim and assert that it is not transformed
        self._removeXformableProperties(prim)
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())

        # Non-identity components with orientation will be stored as components
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertIsValidUsd(stage)

    def testReuseTransformOps(self):
        # If there is a single transform xformOp authored then that should not be reused
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Add a transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp()

        # When a transform xformOp is authored it should not be reused
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Add a transform xformOp that has a custom suffix
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(opSuffix="custom")

        # When a transform xformOp that has an op suffix is authored it should not be reused
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Add an inverse transform xformOp
        self._removeXformableProperties(prim)
        xformOp = xformable.AddTransformOp(isInverseOp=True)

        # When an inverse transform xformOp is authored it should not be reused
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # Clean the prim and add a transform xformOp
        self._removeXformableProperties(prim)
        xformable.AddTransformOp(opSuffix="custom")

        # Setting components with orientation at this point will not reuse the transform xformOp because this would discard the orientation.
        # Fidelity of components takes precedence over existing authored xformOpOrders.
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_NO_PIVOT_MATRIX, 1e-6))
        self.assertIsValidUsd(stage)

    def testReuseComponentOps(self):
        # If there are existing xformOps that are considered valid by the XformCommonAPI then these should be reused
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Add all the XformCommonAPI xformOps with an unexpected precisions
        self._removeXformableProperties(prim)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionFloat)
        xformable.AddOrientOp(precision=UsdGeom.XformOp.PrecisionDouble)
        xformable.AddScaleOp(precision=UsdGeom.XformOp.PrecisionDouble)

        # Precisions authored originally, these should be unchanged after setting the local transform
        precisions = [
            UsdGeom.XformOp.PrecisionFloat,  # translate
            UsdGeom.XformOp.PrecisionDouble,  # orient
            UsdGeom.XformOp.PrecisionDouble,  # scale
        ]

        # When component xform ops already exist but have an unexpected precision they should be reused
        # Coding errors should not be reported
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(self._getOrderedXformOpPrecisions(xformable), precisions)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_NO_PIVOT_MATRIX, 1e-6))

        # Add a subset of the standard xformOps with an unexpected precisions
        self._removeXformableProperties(prim)
        xformable.AddTranslateOp(precision=UsdGeom.XformOp.PrecisionFloat)
        xformable.AddOrientOp(precision=UsdGeom.XformOp.PrecisionDouble)

        # Precisions authored originally and the default that will be created, these should be unchanged after setting the local transform
        precisions = [
            UsdGeom.XformOp.PrecisionFloat,  # translate
            UsdGeom.XformOp.PrecisionDouble,  # orient
            UsdGeom.XformOp.PrecisionFloat,  # scale default
        ]

        # When component xform ops already exist but have an unexpected precision they should be reused
        # Un-authored xform ops will be created and use the default precision of the UsdGeomXformCommonAPI
        # Coding errors should not be reported
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(self._getOrderedXformOpPrecisions(xformable), precisions)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_NO_PIVOT_MATRIX, 1e-6))
        self.assertIsValidUsd(stage)

    def testRoundTrip(self):
        # The computed local transform matrix of a prim should match the transform components matrix after being set on the prim
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # An identity matrix
        usdex.core.setLocalTransform(prim, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # A non-identity matrix (adjusted for no pivot)
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_NO_PIVOT_MATRIX, 1e-6))
        self.assertIsValidUsd(stage)

    def testRotationOrientationRoundTrip(self):
        """Test that we can successfully switch between rotation and orientation based transforms"""
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # First set using rotation components
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX, 1e-6))

        # Verify no extraneous xformOps
        self.assertNoExtraneousXformOps(prim)

        # Then set using orientation components
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_WITH_ORIENTATION_XFORM_OP_ORDER)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_NO_PIVOT_MATRIX, 1e-6))

        # Verify no extraneous xformOps
        self.assertNoExtraneousXformOps(prim)

        # Then set back to rotation components
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetXformOpOrderAttr().Get(), COMPONENT_XFORM_OP_ORDER)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX, 1e-6))

        # Verify no extraneous xformOps
        self.assertNoExtraneousXformOps(prim)

        # Verify we can still get the components correctly
        components = usdex.core.getLocalTransformComponents(prim)
        self.assertTupleEqual(components, NON_IDENTITY_COMPONENTS)

        components_with_orientation = usdex.core.getLocalTransformComponentsQuat(prim)
        self.assertTupleWithQuatAlmostEqual(components_with_orientation, NON_IDENTITY_COMPONENTS_WITH_ORIENTATION_AND_PIVOT)
        self.assertIsValidUsd(stage)


class GetLocalTransformTest(BaseXformTestCase):
    def testInvalidPrims(self):
        # An invalid or non-xformable prim will produce an identity return
        stage = self._createTestStage()

        # An invalid prim will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Invalid")
        transform = usdex.core.getLocalTransform(prim)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, IDENTITY_TRANSFORM)

        # A non-xformable prim will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Scope")
        transform = usdex.core.getLocalTransform(prim)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, IDENTITY_TRANSFORM)
        self.assertIsValidUsd(stage)

    def testValidPrim(self):
        # A valid xformable prim with no xform will produce an identity return
        stage = self._createTestStage()

        # An xformable prim with no xformOps will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Xform")
        transform = usdex.core.getLocalTransform(prim)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, IDENTITY_TRANSFORM)

        # An xformable prim with an empty xformOpOrder will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Empty_Xform_Op_Order")
        transform = usdex.core.getLocalTransform(prim)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, IDENTITY_TRANSFORM)
        self.assertIsValidUsd(stage)

    def testTimeArgument(self):
        # The "time" argument is supported but optional
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Animated_Matrix")

        # Declare the expected values at different times
        transformDefault = Gf.Transform()
        transformDefault.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))

        transformTime0 = Gf.Transform()
        transformTime0.SetTranslation(Gf.Vec3d(40.0, 50.0, 60.0))

        transformTime5 = Gf.Transform()
        transformTime5.SetTranslation(Gf.Vec3d(55.0, 65.0, 75.0))

        transformTime10 = Gf.Transform()
        transformTime10.SetTranslation(Gf.Vec3d(70.0, 80.0, 90.0))

        # When "time" is not specified the "default" time is used
        transform = usdex.core.getLocalTransform(prim)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, transformDefault)

        # The "default" time value is respected
        time = Usd.TimeCode.Default()
        transform = usdex.core.getLocalTransform(prim, time)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, transformDefault)

        # The "earliest" time value is respected
        time = Usd.TimeCode.EarliestTime()
        transform = usdex.core.getLocalTransform(prim, time)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, transformTime0)

        # When a time value that matches a time sample is specified it is respected
        time = Usd.TimeCode(0.0)
        transform = usdex.core.getLocalTransform(prim, time)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, transformTime0)

        time = Usd.TimeCode(10.0)
        transform = usdex.core.getLocalTransform(prim, time)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, transformTime10)

        # When a time value that falls between a time sample is specified it is interpolated
        time = Usd.TimeCode(5.0)
        transform = usdex.core.getLocalTransform(prim, time)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, transformTime5)
        self.assertIsValidUsd(stage)

    def testXformCommonAPIXformOps(self):
        # When authored xformOps are from UsdGeomXformCommonAPI retain as much fidelity as possible
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Animated_Xform_Common_API")

        # Declare the expected values at different times
        expectedDefault = Gf.Transform()
        # There is no rotation in the result because the presence of two rotations causes in a new rotation to be computed in a lossy manner
        expectedDefault.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))

        expectedTime0 = Gf.Transform()
        expectedTime0.SetTranslation(Gf.Vec3d(40.0, 50.0, 60.0))
        expectedTime0.SetRotation(Gf.Rotation(Gf.Vec3d.XAxis(), 180.0))

        expectedTime5 = Gf.Transform()
        expectedTime5.SetTranslation(Gf.Vec3d(55.0, 65.0, 75.0))
        expectedTime5.SetRotation(Gf.Rotation(Gf.Vec3d.XAxis(), 360.0))

        expectedTime10 = Gf.Transform()
        expectedTime10.SetTranslation(Gf.Vec3d(70.0, 80.0, 90.0))
        expectedTime10.SetRotation(Gf.Rotation(Gf.Vec3d.XAxis(), 540.0))

        # Assert the expected values at different times
        returned = usdex.core.getLocalTransform(prim, Usd.TimeCode.Default())
        self.assertEqual(returned.GetRotation(), expectedDefault.GetRotation())
        self.assertEqual(returned, expectedDefault)

        returned = usdex.core.getLocalTransform(prim, Usd.TimeCode(0.0))
        self.assertEqual(returned.GetRotation(), expectedTime0.GetRotation())
        self.assertEqual(returned, expectedTime0)

        returned = usdex.core.getLocalTransform(prim, Usd.TimeCode(5.0))
        self.assertEqual(returned.GetRotation(), expectedTime5.GetRotation())
        self.assertEqual(returned, expectedTime5)

        returned = usdex.core.getLocalTransform(prim, Usd.TimeCode(10.0))
        self.assertEqual(returned.GetRotation(), expectedTime10.GetRotation())
        self.assertEqual(returned, expectedTime10)
        self.assertIsValidUsd(stage)


class GetLocalTransformMatrixTest(BaseXformTestCase):
    def testInvalidPrims(self):
        # An invalid or non-xformable prim will produce an identity return
        stage = self._createTestStage()

        # An invalid prim will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Invalid")
        matrix = usdex.core.getLocalTransformMatrix(prim)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, IDENTITY_MATRIX)

        # A non-xformable prim will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Scope")
        matrix = usdex.core.getLocalTransformMatrix(prim)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)

    def testValidPrim(self):
        # A valid xformable prim with no xform ops will produce an identity return
        stage = self._createTestStage()

        # An xformable prim with no xformOps will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Xform")
        matrix = usdex.core.getLocalTransformMatrix(prim)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, IDENTITY_MATRIX)

        # An xformable prim with an empty xformOpOrder will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Empty_Xform_Op_Order")
        matrix = usdex.core.getLocalTransformMatrix(prim)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)

    def testTimeArgument(self):
        # The "time" argument is supported but optional
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Animated_Matrix")

        # Declare the expected values at different times
        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))
        matrixDefault = transform.GetMatrix()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(40.0, 50.0, 60.0))
        matrixTime0 = transform.GetMatrix()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(55.0, 65.0, 75.0))
        matrixTime5 = transform.GetMatrix()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(70.0, 80.0, 90.0))
        matrixTime10 = transform.GetMatrix()

        # When "time" is not specified the "default" time is used
        matrix = usdex.core.getLocalTransformMatrix(prim)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, matrixDefault)

        # The "default" time value is respected
        time = Usd.TimeCode.Default()
        matrix = usdex.core.getLocalTransformMatrix(prim, time)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, matrixDefault)

        # The "earliest" time value is respected
        time = Usd.TimeCode.EarliestTime()
        matrix = usdex.core.getLocalTransformMatrix(prim, time)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, matrixTime0)

        # When a time value that matches a time sample is specified it is respected
        time = Usd.TimeCode(0.0)
        matrix = usdex.core.getLocalTransformMatrix(prim, time)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, matrixTime0)

        time = Usd.TimeCode(10.0)
        matrix = usdex.core.getLocalTransformMatrix(prim, time)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, matrixTime10)

        # When a time value that falls between a time sample is specified it is interpolated
        time = Usd.TimeCode(5.0)
        matrix = usdex.core.getLocalTransformMatrix(prim, time)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, matrixTime5)
        self.assertIsValidUsd(stage)

    def testXformCommonAPIXformOps(self):
        # When authored xformOps are from UsdGeomXformCommonAPI retain as much fidelity as possible
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Animated_Xform_Common_API")

        # Declare the expected values at different times
        transform = Gf.Transform()
        # There is no rotation in the result because the 4x4 matrix treats 360 degrees as 0
        transform.SetTranslation(Gf.Vec3d(10.0, 20.0, 30.0))
        matrixDefault = transform.GetMatrix()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(40.0, 50.0, 60.0))
        transform.SetRotation(Gf.Rotation(Gf.Vec3d.XAxis(), 180.0))
        matrixTime0 = transform.GetMatrix()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(55.0, 65.0, 75.0))
        # There is no rotation in the result because the 4x4 matrix treats 360 degrees as 0
        matrixTime5 = transform.GetMatrix()

        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(70.0, 80.0, 90.0))
        # There is a rotation of 180 degrees in the result because the 4x4 matrix treats 540 degrees as 180 degrees
        transform.SetRotation(Gf.Rotation(Gf.Vec3d.XAxis(), 180.0))
        matrixTime10 = transform.GetMatrix()

        # Assert the expected values at different times
        # We assert that the matrices are almost equal to account for float to double precision errors
        returned = usdex.core.getLocalTransformMatrix(prim, Usd.TimeCode.Default())
        self.assertTrue(Gf.IsClose(returned, matrixDefault, 1e-6))

        returned = usdex.core.getLocalTransformMatrix(prim, Usd.TimeCode(0.0))
        self.assertTrue(Gf.IsClose(returned, matrixTime0, 1e-6))

        returned = usdex.core.getLocalTransformMatrix(prim, Usd.TimeCode(5.0))
        self.assertTrue(Gf.IsClose(returned, matrixTime5, 1e-6))

        returned = usdex.core.getLocalTransformMatrix(prim, Usd.TimeCode(10.0))
        self.assertTrue(Gf.IsClose(returned, matrixTime10, 1e-6))
        self.assertIsValidUsd(stage)


class GetLocalTransformComponentsTest(BaseXformTestCase):
    def testInvalidPrims(self):
        # An invalid or non-xformable prim will produce an identity return
        stage = self._createTestStage()

        # An invalid prim will produce an identity result
        prim = stage.GetPrimAtPath("/Root/Invalid")
        returned = usdex.core.getLocalTransformComponents(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS)

        # A non-xformable prim will produce an identity result
        prim = stage.GetPrimAtPath("/Root/Scope")
        returned = usdex.core.getLocalTransformComponents(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS)
        self.assertIsValidUsd(stage)

    def testValidPrim(self):
        # A valid xformable prim with no xform ops will produce an identity return
        stage = self._createTestStage()

        # An xformable prim with no xformOps will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Xform")
        returned = usdex.core.getLocalTransformComponents(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS)

        # An xformable prim with an empty xformOpOrder will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Empty_Xform_Op_Order")
        returned = usdex.core.getLocalTransformComponents(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS)
        self.assertIsValidUsd(stage)

    def testTimeArgument(self):
        # The "time" argument is supported but optional
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Animated_Matrix")

        # Declare the expected values at different times
        translation = Gf.Vec3d(10.0, 20.0, 30.0)
        componentsDefault = tuple([translation, IDENTITY_TRANSLATE, IDENTITY_ROTATE, usdex.core.RotationOrder.eXyz, IDENTITY_SCALE])

        translation = Gf.Vec3d(40.0, 50.0, 60.0)
        componentsTime0 = tuple([translation, IDENTITY_TRANSLATE, IDENTITY_ROTATE, usdex.core.RotationOrder.eXyz, IDENTITY_SCALE])

        translation = Gf.Vec3d(55.0, 65.0, 75.0)
        componentsTime5 = tuple([translation, IDENTITY_TRANSLATE, IDENTITY_ROTATE, usdex.core.RotationOrder.eXyz, IDENTITY_SCALE])

        translation = Gf.Vec3d(70.0, 80.0, 90.0)
        componentsTime10 = tuple([translation, IDENTITY_TRANSLATE, IDENTITY_ROTATE, usdex.core.RotationOrder.eXyz, IDENTITY_SCALE])

        # When "time" is not specified the "default" time is used
        returned = usdex.core.getLocalTransformComponents(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsDefault)

        # The "default" time value is respected
        time = Usd.TimeCode.Default()
        returned = usdex.core.getLocalTransformComponents(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsDefault)

        # The "earliest" time value is respected
        time = Usd.TimeCode.EarliestTime()
        returned = usdex.core.getLocalTransformComponents(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsTime0)

        # When a time value that matches a time sample is specified it is respected
        time = Usd.TimeCode(0.0)
        returned = usdex.core.getLocalTransformComponents(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsTime0)

        time = Usd.TimeCode(10.0)
        returned = usdex.core.getLocalTransformComponents(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsTime10)

        # When a time value that falls between a time sample is specified it is interpolated
        time = Usd.TimeCode(5.0)
        returned = usdex.core.getLocalTransformComponents(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsTime5)
        self.assertIsValidUsd(stage)

    def testXformCommonAPIXformOps(self):
        # When authored xformOps are from UsdGeomXformCommonAPI retain as much fidelity as possible
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Animated_Xform_Common_API")

        # Declare the expected values at different times
        translation = Gf.Vec3d(10.0, 20.0, 30.0)
        rotation = Gf.Vec3f(360.0, 360.0, 0.0)
        expectedDefault = tuple([translation, IDENTITY_TRANSLATE, rotation, usdex.core.RotationOrder.eXyz, IDENTITY_SCALE])

        translation = Gf.Vec3d(40.0, 50.0, 60.0)
        rotation = Gf.Vec3f(180.0, 0.0, 0.0)
        expectedTime0 = tuple([translation, IDENTITY_TRANSLATE, rotation, usdex.core.RotationOrder.eXyz, IDENTITY_SCALE])

        translation = Gf.Vec3d(55.0, 65.0, 75.0)
        rotation = Gf.Vec3f(360.0, 0.0, 0.0)
        expectedTime5 = tuple([translation, IDENTITY_TRANSLATE, rotation, usdex.core.RotationOrder.eXyz, IDENTITY_SCALE])

        translation = Gf.Vec3d(70.0, 80.0, 90.0)
        rotation = Gf.Vec3f(540.0, 0.0, 0.0)
        expectedTime10 = tuple([translation, IDENTITY_TRANSLATE, rotation, usdex.core.RotationOrder.eXyz, IDENTITY_SCALE])

        # Assert the expected values at different times
        returned = usdex.core.getLocalTransformComponents(prim, Usd.TimeCode.Default())
        self.assertTupleEqual(returned, expectedDefault)

        returned = usdex.core.getLocalTransformComponents(prim, Usd.TimeCode(0.0))
        self.assertTupleEqual(returned, expectedTime0)

        returned = usdex.core.getLocalTransformComponents(prim, Usd.TimeCode(5.0))
        self.assertTupleEqual(returned, expectedTime5)

        returned = usdex.core.getLocalTransformComponents(prim, Usd.TimeCode(10.0))
        self.assertTupleEqual(returned, expectedTime10)
        self.assertIsValidUsd(stage)


class GetLocalTransformWithOrientationTest(BaseXformTestCase):
    def testInvalidPrims(self):
        # An invalid or non-xformable prim will produce an identity return
        stage = self._createTestStage()

        # An invalid prim will produce an identity result
        prim = stage.GetPrimAtPath("/Root/Invalid")
        returned = usdex.core.getLocalTransformComponentsQuat(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS_WITH_ORIENTATION_AND_PIVOT)

        # A non-xformable prim will produce an identity result
        prim = stage.GetPrimAtPath("/Root/Scope")
        returned = usdex.core.getLocalTransformComponentsQuat(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS_WITH_ORIENTATION_AND_PIVOT)
        self.assertIsValidUsd(stage)

    def testValidPrim(self):
        # A valid xformable prim with no xform ops will produce an identity return
        stage = self._createTestStage()

        # An xformable prim with no xformOps will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Xform")
        returned = usdex.core.getLocalTransformComponentsQuat(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS_WITH_ORIENTATION_AND_PIVOT)

        # An xformable prim with an empty xformOpOrder will produce an identity matrix
        prim = stage.GetPrimAtPath("/Root/Empty_Xform_Op_Order")
        returned = usdex.core.getLocalTransformComponentsQuat(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS_WITH_ORIENTATION_AND_PIVOT)
        self.assertIsValidUsd(stage)

    def testTimeArgument(self):
        # The "time" argument is supported but optional
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Animated_Matrix")

        # Declare the expected values at different times
        translation = Gf.Vec3d(10.0, 20.0, 30.0)
        componentsDefault = tuple([translation, IDENTITY_TRANSLATE, IDENTITY_ORIENTATION, IDENTITY_SCALE])

        translation = Gf.Vec3d(40.0, 50.0, 60.0)
        componentsTime0 = tuple([translation, IDENTITY_TRANSLATE, IDENTITY_ORIENTATION, IDENTITY_SCALE])

        translation = Gf.Vec3d(55.0, 65.0, 75.0)
        componentsTime5 = tuple([translation, IDENTITY_TRANSLATE, IDENTITY_ORIENTATION, IDENTITY_SCALE])

        translation = Gf.Vec3d(70.0, 80.0, 90.0)
        componentsTime10 = tuple([translation, IDENTITY_TRANSLATE, IDENTITY_ORIENTATION, IDENTITY_SCALE])

        # When "time" is not specified the "default" time is used
        returned = usdex.core.getLocalTransformComponentsQuat(prim)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsDefault)

        # The "default" time value is respected
        time = Usd.TimeCode.Default()
        returned = usdex.core.getLocalTransformComponentsQuat(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsDefault)

        # The "earliest" time value is respected
        time = Usd.TimeCode.EarliestTime()
        returned = usdex.core.getLocalTransformComponentsQuat(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsTime0)

        # When a time value that matches a time sample is specified it is respected
        time = Usd.TimeCode(0.0)
        returned = usdex.core.getLocalTransformComponentsQuat(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsTime0)

        time = Usd.TimeCode(10.0)
        returned = usdex.core.getLocalTransformComponentsQuat(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsTime10)

        # When a time value that falls between a time sample is specified it is interpolated
        time = Usd.TimeCode(5.0)
        returned = usdex.core.getLocalTransformComponentsQuat(prim, time)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, componentsTime5)
        self.assertIsValidUsd(stage)

    def testXformCommonAPIXformOps(self):
        # When authored xformOps are from UsdGeomXformCommonAPI retain as much fidelity as possible
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Animated_Xform_Common_API")

        # Declare the expected values at different times
        translation = Gf.Vec3d(10.0, 20.0, 30.0)
        orientation = Gf.Quatf.GetIdentity()
        expectedDefault = tuple([translation, IDENTITY_TRANSLATE, orientation, IDENTITY_SCALE])

        translation = Gf.Vec3d(40.0, 50.0, 60.0)
        orientation = Gf.Quatf(0.0, 1.0, 0.0, 0.0)  # 180 degrees around X
        expectedTime0 = tuple([translation, IDENTITY_TRANSLATE, orientation, IDENTITY_SCALE])

        translation = Gf.Vec3d(55.0, 65.0, 75.0)
        orientation = Gf.Quatf.GetIdentity()  # 360 degrees around X
        expectedTime5 = tuple([translation, IDENTITY_TRANSLATE, orientation, IDENTITY_SCALE])

        translation = Gf.Vec3d(70.0, 80.0, 90.0)
        orientation = Gf.Quatf(0.0, 1.0, 0.0, 0.0)  # 180 degrees around X (540 degrees)
        expectedTime10 = tuple([translation, IDENTITY_TRANSLATE, orientation, IDENTITY_SCALE])

        # Assert the expected values at different times
        returned = usdex.core.getLocalTransformComponentsQuat(prim, Usd.TimeCode.Default())
        self.assertTupleEqual(returned, expectedDefault)

        returned = usdex.core.getLocalTransformComponentsQuat(prim, Usd.TimeCode(0.0))
        self.assertTupleWithQuatAlmostEqual(returned, expectedTime0)

        returned = usdex.core.getLocalTransformComponentsQuat(prim, Usd.TimeCode(5.0))
        self.assertTupleWithQuatAlmostEqual(returned, expectedTime5)

        returned = usdex.core.getLocalTransformComponentsQuat(prim, Usd.TimeCode(10.0))
        self.assertTupleWithQuatAlmostEqual(returned, expectedTime10)
        self.assertIsValidUsd(stage)


class DefineXformTestCase(usdex.test.DefineFunctionTestCase, BaseXformTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.defineXform
    requiredArgs = tuple()
    typeName = "Xform"
    schema = UsdGeom.Xform
    requiredPropertyNames = set()

    def testOptionalTransform(self):
        # A transform can optionally be supplied and will be used to set the local transform of the Xform
        stage = self._createTestStage()

        UsdGeom.Scope.Define(stage, "/Root/StagePath")
        UsdGeom.Scope.Define(stage, "/Root/ParentName")
        parent = stage.GetPrimAtPath("/Root/ParentName")

        # If None is passed then the local transform is not set
        # stage, path
        path = Sdf.Path("/Root/StagePath/None")
        mesh = usdex.core.defineXform(stage, path, transform=None)
        self.assertTrue(mesh)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # parent, name
        name = "None"
        mesh = usdex.core.defineXform(parent, name, transform=None)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # prim
        mesh = usdex.core.defineXform(mesh.GetPrim(), transform=None)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # If a valid transform is passed in the prim will have that as it's local transform
        # stage, path
        path = Sdf.Path("/Root/StagePath/NonIdentityTransform")
        mesh = usdex.core.defineXform(stage, path, transform=NON_IDENTITY_TRANSFORM)
        self.assertTrue(mesh)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

        # parent, name
        name = "NonIdentityTransform"
        mesh = usdex.core.defineXform(parent, name, transform=NON_IDENTITY_TRANSFORM)
        self.assertTrue(mesh)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

        # prim
        mesh = usdex.core.defineXform(mesh.GetPrim(), transform=NON_IDENTITY_TRANSFORM)
        self.assertTrue(mesh)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

        self.assertIsValidUsd(stage)

    def testOptionalMatrix(self):
        # A matrix can optionally be supplied and will be used to set the local transform of the Xform
        stage = self._createTestStage()

        UsdGeom.Scope.Define(stage, "/Root/StagePath")
        UsdGeom.Scope.Define(stage, "/Root/ParentName")
        parent = stage.GetPrimAtPath("/Root/ParentName")

        # If None is passed then the local matrix is not set
        # stage, path
        path = Sdf.Path("/Root/StagePath/None")
        mesh = usdex.core.defineXform(stage, path)
        self.assertTrue(mesh)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # parent, name
        name = "None"
        mesh = usdex.core.defineXform(parent, name)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # prim
        mesh = usdex.core.defineXform(mesh.GetPrim())
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertFalse(xformable.GetXformOpOrderAttr().IsAuthored())
        self.assertEqual(xformable.GetLocalTransformation(), IDENTITY_MATRIX)

        # If a valid matrix is passed in the prim will have that as it's local transform
        # stage, path
        path = Sdf.Path("/Root/StagePath/NonIdentityMatrix")
        mesh = usdex.core.defineXform(stage, path, matrix=NON_IDENTITY_MATRIX)
        self.assertTrue(mesh)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

        # parent, name
        name = "NonIdentityMatrix"
        mesh = usdex.core.defineXform(parent, name, matrix=NON_IDENTITY_MATRIX)
        self.assertTrue(mesh)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

        # prim
        mesh = usdex.core.defineXform(mesh.GetPrim(), matrix=NON_IDENTITY_MATRIX)
        self.assertTrue(mesh)
        xformable = UsdGeom.Xformable(mesh.GetPrim())
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

        self.assertIsValidUsd(stage)


# Smoke tests for UsdGeomXformable overloads
class SetLocalTransformWithTransformXformableTestCase(BaseSetLocalTransformTestCase):
    def testInvalidXformable(self):
        # An invalid xformable will produce a failure return and emit a runtime error
        xformable = UsdGeom.Xformable()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*UsdGeomXformable.*is not valid")]):
            success = usdex.core.setLocalTransform(xformable, IDENTITY_TRANSFORM)
        self.assertFalse(success)

    def testValidXformable(self):
        # A valid xformable will produce a success return and same results as prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        success = usdex.core.setLocalTransform(xformable, NON_IDENTITY_TRANSFORM)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

    def testRoundTrip(self):
        # The xformable overload should produce the same results as the prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        usdex.core.setLocalTransform(xformable, NON_IDENTITY_TRANSFORM)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_TRANSFORM.GetMatrix())
        self.assertIsValidUsd(stage)


class SetLocalTransformWithMatrixXformableTestCase(BaseSetLocalTransformTestCase):
    def testInvalidXformable(self):
        # An invalid xformable will produce a failure return and emit a runtime error
        xformable = UsdGeom.Xformable()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*UsdGeomXformable.*is not valid")]):
            success = usdex.core.setLocalTransform(xformable, IDENTITY_MATRIX)
        self.assertFalse(success)

    def testValidXformable(self):
        # A valid xformable will produce a success return and same results as prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        success = usdex.core.setLocalTransform(xformable, NON_IDENTITY_MATRIX)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

    def testRoundTrip(self):
        # The xformable overload should produce the same results as the prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        usdex.core.setLocalTransform(xformable, NON_IDENTITY_MATRIX)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)


class SetLocalTransformWithComponentsXformableTestCase(BaseSetLocalTransformTestCase):
    def testInvalidXformable(self):
        # An invalid xformable will produce a failure return and emit a runtime error
        xformable = UsdGeom.Xformable()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*UsdGeomXformable.*is not valid")]):
            success = usdex.core.setLocalTransform(xformable, *IDENTITY_COMPONENTS)
        self.assertFalse(success)

    def testValidXformable(self):
        # A valid xformable will produce a success return and same results as prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        success = usdex.core.setLocalTransform(xformable, *NON_IDENTITY_COMPONENTS)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)

    def testRoundTrip(self):
        # The xformable overload should produce the same results as the prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        usdex.core.setLocalTransform(xformable, *NON_IDENTITY_COMPONENTS)
        self.assertEqual(xformable.GetLocalTransformation(), NON_IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)


class SetLocalTransformWithOrientationXformableTestCase(BaseSetLocalTransformTestCase):
    def testInvalidXformable(self):
        # An invalid xformable will produce a failure return and emit a runtime error
        xformable = UsdGeom.Xformable()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*UsdGeomXformable.*is not valid")]):
            success = usdex.core.setLocalTransform(xformable, *IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertFalse(success)

    def testValidXformable(self):
        # A valid xformable will produce a success return and same results as prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        success = usdex.core.setLocalTransform(xformable, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertTrue(success)
        self.assertSuccessfulSetLocalTransform(prim)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_NO_PIVOT_MATRIX, 1e-6))

    def testRoundTrip(self):
        # The xformable overload should produce the same results as the prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        usdex.core.setLocalTransform(xformable, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)
        self.assertTrue(Gf.IsClose(xformable.GetLocalTransformation(), NON_IDENTITY_NO_PIVOT_MATRIX, 1e-6))
        self.assertIsValidUsd(stage)


class GetLocalTransformXformableTest(BaseXformTestCase):
    def testInvalidXformable(self):
        # An invalid xformable will produce an identity return and emit a runtime error
        xformable = UsdGeom.Xformable()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*UsdGeomXformable.*is not valid")]):
            transform = usdex.core.getLocalTransform(xformable)
        self.assertIsInstance(transform, Gf.Transform)
        self.assertEqual(transform, IDENTITY_TRANSFORM)

    def testValidXformable(self):
        # A valid xformable will produce the same results as prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Set a transform first
        usdex.core.setLocalTransform(prim, NON_IDENTITY_TRANSFORM)

        # Test that xformable overload returns same result as prim version
        transformFromPrim = usdex.core.getLocalTransform(prim)
        transformFromXformable = usdex.core.getLocalTransform(xformable)
        self.assertEqual(transformFromPrim, transformFromXformable)
        self.assertEqual(transformFromXformable, NON_IDENTITY_TRANSFORM)
        self.assertIsValidUsd(stage)


class GetLocalTransformMatrixXformableTest(BaseXformTestCase):
    def testInvalidXformable(self):
        # An invalid xformable will produce an identity return and emit a runtime error
        xformable = UsdGeom.Xformable()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*UsdGeomXformable.*is not valid")]):
            matrix = usdex.core.getLocalTransformMatrix(xformable)
        self.assertIsInstance(matrix, Gf.Matrix4d)
        self.assertEqual(matrix, IDENTITY_MATRIX)

    def testValidXformable(self):
        # A valid xformable will produce the same results as prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Set a transform first
        usdex.core.setLocalTransform(prim, NON_IDENTITY_MATRIX)

        # Test that xformable overload returns same result as prim version
        matrixFromPrim = usdex.core.getLocalTransformMatrix(prim)
        matrixFromXformable = usdex.core.getLocalTransformMatrix(xformable)
        self.assertEqual(matrixFromPrim, matrixFromXformable)
        self.assertEqual(matrixFromXformable, NON_IDENTITY_MATRIX)
        self.assertIsValidUsd(stage)


class GetLocalTransformComponentsXformableTest(BaseXformTestCase):
    def testInvalidXformable(self):
        # An invalid xformable will produce an identity return and emit a runtime error
        xformable = UsdGeom.Xformable()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*UsdGeomXformable.*is not valid")]):
            returned = usdex.core.getLocalTransformComponents(xformable)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS)

    def testValidXformable(self):
        # A valid xformable will produce the same results as prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Set components first
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS)

        # Test that xformable overload returns same result as prim version
        componentsFromPrim = usdex.core.getLocalTransformComponents(prim)
        componentsFromXformable = usdex.core.getLocalTransformComponents(xformable)
        self.assertTupleEqual(componentsFromPrim, componentsFromXformable)
        self.assertTupleEqual(componentsFromXformable, NON_IDENTITY_COMPONENTS)
        self.assertIsValidUsd(stage)


class GetLocalTransformComponentsQuatXformableTest(BaseXformTestCase):
    def testInvalidXformable(self):
        # An invalid xformable will produce an identity return and emit a runtime error
        xformable = UsdGeom.Xformable()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*UsdGeomXformable.*is not valid")]):
            returned = usdex.core.getLocalTransformComponentsQuat(xformable)
        self.assertIsInstance(returned, tuple)
        self.assertTupleEqual(returned, IDENTITY_COMPONENTS_WITH_ORIENTATION_AND_PIVOT)

    def testValidXformable(self):
        # A valid xformable will produce the same results as prim version
        stage = self._createTestStage()
        prim = stage.GetPrimAtPath("/Root/Xform")
        xformable = UsdGeom.Xformable(prim)

        # Set components with orientation first
        usdex.core.setLocalTransform(prim, *NON_IDENTITY_COMPONENTS_WITH_ORIENTATION)

        # Test that xformable overload returns same result as prim version
        componentsFromPrim = usdex.core.getLocalTransformComponentsQuat(prim)
        componentsFromXformable = usdex.core.getLocalTransformComponentsQuat(xformable)
        self.assertTupleWithQuatAlmostEqual(componentsFromPrim, componentsFromXformable)

        # The expected result should have identity pivot since NON_IDENTITY_COMPONENTS_WITH_ORIENTATION has no pivot
        expectedComponents = tuple(
            [
                NON_IDENTITY_TRANSLATE,
                IDENTITY_TRANSLATE,  # pivot position should be identity
                NON_IDENTITY_ORIENTATION,
                NON_IDENTITY_SCALE,
            ]
        )
        self.assertTupleWithQuatAlmostEqual(componentsFromXformable, expectedComponents)
        self.assertIsValidUsd(stage)


class DefineXformFromPrimTestCase(BaseXformTestCase):
    def testDefineXformFromXform(self):
        stage = self._createTestStage()
        xform = UsdGeom.Xform.Define(stage, Sdf.Path("/Root/ExistingXform"))
        result = usdex.core.defineXform(xform.GetPrim())
        self.assertTrue(result)
        self.assertEqual(result.GetPrim().GetTypeName(), "Xform")
        self.assertEqual(result.GetPrim().GetPath(), xform.GetPrim().GetPath())
        self.assertIsValidUsd(stage)

    def testDefineXformFromScope(self):
        stage = self._createTestStage()
        scope = UsdGeom.Scope.Define(stage, Sdf.Path("/Root/ExistingScope"))
        result = usdex.core.defineXform(scope.GetPrim())
        self.assertTrue(result)
        self.assertEqual(result.GetPrim().GetTypeName(), "Xform")
        self.assertEqual(result.GetPrim().GetPath(), scope.GetPrim().GetPath())
        self.assertIsValidUsd(stage)

    def testDefineXformFromPrimWithTransform(self):
        stage = self._createTestStage()
        scope = UsdGeom.Scope.Define(stage, Sdf.Path("/Root/TransformedScope"))
        transform = Gf.Transform()
        transform.SetTranslation(Gf.Vec3d(1, 2, 3))
        result = usdex.core.defineXform(scope.GetPrim(), transform)
        self.assertTrue(result)
        self.assertEqual(result.GetPrim().GetTypeName(), "Xform")
        self.assertEqual(usdex.core.getLocalTransform(result.GetPrim()), transform)
        self.assertIsValidUsd(stage)

    def testDefineXformFromInvalidPrim(self):
        stage = self._createTestStage()
        invalidPrim = stage.GetPrimAtPath("/NonExistent")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            result = usdex.core.defineXform(invalidPrim)
        self.assertFalse(result)

    def testDefineXformFromPrimPreservesExistingTransform(self):
        stage = self._createTestStage()
        xform = UsdGeom.Xform.Define(stage, Sdf.Path("/Root/ExistingXform"))
        # Set an initial transform
        initialTransform = Gf.Transform()
        initialTransform.SetTranslation(Gf.Vec3d(5, 6, 7))
        usdex.core.setLocalTransform(xform.GetPrim(), initialTransform)

        # Convert without specifying new transform - should preserve existing
        result = usdex.core.defineXform(xform.GetPrim())
        self.assertTrue(result)
        self.assertEqual(result.GetPrim().GetTypeName(), "Xform")
        self.assertEqual(usdex.core.getLocalTransform(result.GetPrim()), initialTransform)
        self.assertIsValidUsd(stage)

    def testDefineXformFromPrimTypeGuards(self):
        """Test type guards for defineXform prim overload."""
        stage = self._createTestStage()

        # Test with non-Scope/Xform prim - should warn
        meshPrim = stage.DefinePrim("/Root/MeshPrim", "Mesh")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, '.*Redefining prim.*from type.*Mesh.*to.*Xform.*Expected original type to be "" or .*Scope.*or.*Xform')],
        ):
            result = usdex.core.defineXform(meshPrim)
        self.assertTrue(result)
        self.assertEqual(result.GetPrim().GetTypeName(), "Xform")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/Root/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            result = usdex.core.defineXform(scopePrim)
        self.assertTrue(result)
        self.assertEqual(result.GetPrim().GetTypeName(), "Xform")

        # Test with Xform prim - should not warn
        xformPrim = stage.DefinePrim("/Root/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            result = usdex.core.defineXform(xformPrim)
        self.assertTrue(result)
        self.assertEqual(result.GetPrim().GetTypeName(), "Xform")
