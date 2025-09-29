# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import omni.asset_validator
import usdex.core
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdUtils, Vt
from utils.DefinePointBasedTestCaseMixin import DefinePointBasedTestCaseMixin

# Description of a simple mesh with two connected faces
FACE_VERTEX_COUNTS = Vt.IntArray([4, 4])
FACE_VERTEX_INDICES = Vt.IntArray([0, 1, 2, 3, 2, 5, 4, 3])
POINTS = Vt.Vec3fArray(
    [
        Gf.Vec3f(0.0, 0.0, 0.0),
        Gf.Vec3f(0.0, 0.0, 1.0),
        Gf.Vec3f(1.0, 0.0, 1.0),
        Gf.Vec3f(1.0, 0.0, 0.0),
        Gf.Vec3f(2.0, 0.0, 0.0),
        Gf.Vec3f(2.0, 0.0, 1.0),
    ]
)


class DefineMeshTestCase(DefinePointBasedTestCaseMixin, usdex.test.DefineFunctionTestCase):

    # Configure the DefineFunctionTestCase
    defineFunc = usdex.core.definePolyMesh
    requiredArgs = tuple([FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS])
    schema = UsdGeom.Mesh
    typeName = "Mesh"
    requiredPropertyNames = set(
        [
            UsdGeom.Tokens.points,
            UsdGeom.Tokens.faceVertexCounts,
            UsdGeom.Tokens.faceVertexIndices,
            UsdGeom.Tokens.subdivisionScheme,
            UsdGeom.Tokens.orientation,
            UsdGeom.Tokens.extent,
        ]
    )
    primvarSizes = {
        UsdGeom.Tokens.constant: 1,
        UsdGeom.Tokens.uniform: len(FACE_VERTEX_COUNTS),
        UsdGeom.Tokens.vertex: len(POINTS),
        UsdGeom.Tokens.faceVarying: len(FACE_VERTEX_INDICES),
    }

    def setUp(self):
        super().setUp()
        # Disable non-core validator rules
        self.validationEngine.disable_rule(omni.asset_validator.NormalsExistChecker)

    def assertDefineFunctionSuccess(self, result):
        """Assert the common expectations of a successful call to definePolyMesh"""
        super().assertDefineFunctionSuccess(result)

        # Assert that all required topology attributes are authored
        self.assertTrue(result.GetFaceVertexCountsAttr().IsAuthored())
        self.assertTrue(result.GetFaceVertexIndicesAttr().IsAuthored())
        self.assertTrue(result.GetPointsAttr().IsAuthored())

        # Assert that subdivision schema is explicitly authored as None
        attr = result.GetSubdivisionSchemeAttr()
        self.assertTrue(attr.IsAuthored())
        self.assertEqual(attr.Get(), UsdGeom.Tokens.none)

        # Assert that orientation is explicitly authored as Right Handed
        attr = result.GetOrientationAttr()
        self.assertTrue(attr.IsAuthored())
        self.assertEqual(attr.Get(), UsdGeom.Tokens.rightHanded)

        # Assert that a correct extent has been authored
        extent = UsdGeom.Boundable.ComputeExtentFromPlugins(result, Usd.TimeCode.Default())
        extentAttr = result.GetExtentAttr()
        self.assertTrue(extentAttr.IsAuthored())
        self.assertEqual(extentAttr.Get(), extent)

    def testInvalidTopology(self):
        # Invalid topology attribute normals will result in an invalid Mesh schema being returned and no Prim being defined on the Stage
        stage = self.createTestStage()
        path = Sdf.Path("/World/InvalidTopology")

        # The point array must not be empty
        points = Vt.Vec3fArray()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid points")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, points)
        self.assertDefineFunctionFailure(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The sum of the faceVertexCounts must equal the count of the faceVertexIndices otherwise the topology is invalid.
        faceVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            mesh = usdex.core.definePolyMesh(stage, path, faceVertexCounts, FACE_VERTEX_INDICES, POINTS)
        self.assertIsInstance(mesh, UsdGeom.Mesh)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # The faceVertexIndices normals must be within the range of the points otherwise the topology is invalid.
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(0.0, 0.0, 1.0)])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid topology")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, points)
        self.assertIsInstance(mesh, UsdGeom.Mesh)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))
        self.assertIsValidUsd(stage)

    def testUvs(self):
        # Uvs are optional but if provided will be authored as primvar
        stage = self.createTestStage()
        primvarName = UsdUtils.GetPrimaryUVSetName()
        parentPath = Sdf.Path("/World/Uvs")
        UsdGeom.Scope.Define(stage, parentPath)

        # If uvs are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=None)
        primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())

        # If an empty array is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec2fArray())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If an array of size 1 is specified a constant interpolation could be used but this is not valid for texcoords so no prim is defined
        path = parentPath.AppendChild("ConstantValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0)])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.constant, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the number of faces a uniform interpolation could be used but this is not valid for uvs so no prim is defined
        path = parentPath.AppendChild("PerFaceValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0) for _ in range(len(FACE_VERTEX_COUNTS))])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.uniform, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the number of points a vertex primvar is authored
        path = parentPath.AppendChild("PerPointValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0) for _ in range(len(POINTS))])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.vertex, values)
        mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)

        # If the array size matches the number of face vertices a face varying primvar is authored
        path = parentPath.AppendChild("PerFaceVertexValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0) for _ in range(len(FACE_VERTEX_INDICES))])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.faceVarying, values)
        mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0) for _ in range(len(FACE_VERTEX_INDICES) + 1)])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.faceVarying, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        self.validationEngine.disable_rule(omni.asset_validator.IndexedPrimvarChecker)
        self.assertIsValidUsd(stage)

    def testIndexedUvs(self):
        # Uvs can optional be indexed
        stage = self.createTestStage()
        primvarName = UsdUtils.GetPrimaryUVSetName()
        parentPath = Sdf.Path("/World/IndexedUvs")
        UsdGeom.Scope.Define(stage, parentPath)

        # If uvs and uvsIndices are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=None)
        primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())

        # If an empty array is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        values = Vt.Vec2fArray()
        indices = Vt.IntArray()
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If an array of size 1 is specified a constant interpolation could be used but this is not valid for texcoords so no prim is defined
        path = parentPath.AppendChild("ConstantValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0)])
        indices = Vt.IntArray([0])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.constant, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the number of faces a uniform interpolation could be used but this is not valid for uvs so no prim is defined
        path = parentPath.AppendChild("PerFaceValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0)])
        indices = Vt.IntArray([0 for _ in range(len(FACE_VERTEX_COUNTS))])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.uniform, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the number of points a vertex primvar is authored
        path = parentPath.AppendChild("PerPointValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0)])
        indices = Vt.IntArray([0 for _ in range(len(POINTS))])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)

        # If the array size matches the number of face vertices a face varying primvar is authored
        path = parentPath.AppendChild("PerFaceVertexValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0)])
        indices = Vt.IntArray([0 for _ in range(len(FACE_VERTEX_INDICES))])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
        mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        primvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar(primvarName)
        self.assertPrimvar(primvar, data)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0)])
        indices = Vt.IntArray([0 for _ in range(len(FACE_VERTEX_INDICES) + 1)])
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but the index values are outside the range of the uvs size then no prim is defined
        path = parentPath.AppendChild("IndexValuesGreaterThanRange")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0), Gf.Vec2f(0.0, 0.0)])
        indices = Vt.IntArray([0, 1, 2, 3, 0, 1, 2, 3])  # Face varying interpolation
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but there are values less than zero then no prim is defined
        path = parentPath.AppendChild("NegativeIndexValues")
        values = Vt.Vec2fArray([Gf.Vec2f(0.0, 0.0), Gf.Vec2f(0.0, 0.0)])
        indices = Vt.IntArray([-1, 0, 1, -1, 0, 1])  # Vertex interpolation
        data = usdex.core.Vec2fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid uvs")]):
            mesh = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS, uvs=data)
        self.assertFalse(mesh)
        self.assertFalse(stage.GetPrimAtPath(path))
        self.assertIsValidUsd(stage)

    def testDefineMeshFromXform(self):
        stage = self.createTestStage()
        xform = UsdGeom.Xform.Define(stage, Sdf.Path("/World/ExistingXform"))
        mesh = usdex.core.definePolyMesh(xform.GetPrim(), FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertTrue(mesh)
        self.assertEqual(mesh.GetPrim().GetTypeName(), "Mesh")
        self.assertIsValidUsd(stage)

    def testDefineMeshFromScope(self):
        stage = self.createTestStage()
        scope = UsdGeom.Scope.Define(stage, Sdf.Path("/World/ExistingScope"))
        mesh = usdex.core.definePolyMesh(scope.GetPrim(), FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertTrue(mesh)
        self.assertEqual(mesh.GetPrim().GetTypeName(), "Mesh")
        self.assertIsValidUsd(stage)

    def testDefineMeshFromInvalidPrim(self):
        stage = self.createTestStage()
        invalidPrim = stage.GetPrimAtPath("/NonExistent")
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid prim")]):
            mesh = usdex.core.definePolyMesh(invalidPrim, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertFalse(mesh)

    def testDefinePolyMeshFromPrimTypeGuards(self):
        stage = self.createTestStage()

        # Test with non-Scope/Xform prim - should warn
        materialPrim = stage.DefinePrim("/World/MaterialPrim", "Material")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_WARNING_TYPE,
                    '.*Redefining prim.*from type.*Material.*to.*Mesh.*Expected original type to be "" or .*Scope.*or.*Xform',
                )
            ],
        ):
            mesh = usdex.core.definePolyMesh(materialPrim, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertTrue(mesh)
        self.assertEqual(mesh.GetPrim().GetTypeName(), "Mesh")

        # Test with Scope prim - should not warn
        scopePrim = stage.DefinePrim("/World/ScopePrim", "Scope")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            mesh = usdex.core.definePolyMesh(scopePrim, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertTrue(mesh)
        self.assertEqual(mesh.GetPrim().GetTypeName(), "Mesh")

        # Test with Xform prim - should not warn
        xformPrim = stage.DefinePrim("/World/XformPrim", "Xform")
        with usdex.test.ScopedDiagnosticChecker(self, []):
            mesh = usdex.core.definePolyMesh(xformPrim, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertTrue(mesh)
        self.assertEqual(mesh.GetPrim().GetTypeName(), "Mesh")
