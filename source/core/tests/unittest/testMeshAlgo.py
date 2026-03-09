# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

    def testComputeMeshNormals(self):
        self.validationEngine.enable_rule(omni.asset_validator.NormalsExistChecker)
        stage = self.createTestStage()

        faceVertexCounts = Vt.IntArray([3])
        faceVertexIndices = Vt.IntArray([0, 1, 2])
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 0.0, 0.0), Gf.Vec3f(0.0, 1.0, 0.0)])

        # Test uniform normals
        uniformNormals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.uniform)
        self.assertTrue(uniformNormals.isValid())
        self.assertEqual(uniformNormals.interpolation(), UsdGeom.Tokens.uniform)
        self.assertEqual(uniformNormals.effectiveSize(), 1)
        uniformNormals.index()
        scope = UsdGeom.Scope.Define(stage, Sdf.Path("/World/TestUniformNormals"))
        mesh = usdex.core.definePolyMesh(scope.GetPrim(), faceVertexCounts, faceVertexIndices, points, normals=uniformNormals)
        self.assertTrue(mesh)
        self.assertIsValidUsd(stage)

        # Test vertex normals
        vertexNormals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.vertex)
        self.assertTrue(vertexNormals.isValid())
        self.assertEqual(vertexNormals.interpolation(), UsdGeom.Tokens.vertex)
        self.assertEqual(vertexNormals.effectiveSize(), 3)
        vertexNormals.index()
        scope = UsdGeom.Scope.Define(stage, Sdf.Path("/World/TestVertexNormals"))
        mesh = usdex.core.definePolyMesh(scope.GetPrim(), faceVertexCounts, faceVertexIndices, points, normals=vertexNormals)
        self.assertTrue(mesh)
        self.assertIsValidUsd(stage)

        # Test face-varying normals
        faceVaryingNormals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.faceVarying)
        self.assertTrue(faceVaryingNormals.isValid())
        self.assertEqual(faceVaryingNormals.interpolation(), UsdGeom.Tokens.faceVarying)
        self.assertEqual(faceVaryingNormals.effectiveSize(), 3)
        faceVaryingNormals.index()
        scope = UsdGeom.Scope.Define(stage, Sdf.Path("/World/TestFaceVaryingNormals"))
        mesh = usdex.core.definePolyMesh(scope.GetPrim(), faceVertexCounts, faceVertexIndices, points, normals=faceVaryingNormals)
        self.assertTrue(mesh)
        self.assertIsValidUsd(stage)

        # Test that vertices used across multiple faces with differing normals are correctly averaged
        faceVertexCounts = Vt.IntArray([3, 3])
        faceVertexIndices = Vt.IntArray([0, 1, 2, 0, 3, 4])
        points = Vt.Vec3fArray(
            [
                Gf.Vec3f(0.0, 0.0, 0.0),
                Gf.Vec3f(1.0, 0.0, 0.0),
                Gf.Vec3f(0.0, 1.0, 0.0),
                Gf.Vec3f(0.0, 0.0, 1.0),
                Gf.Vec3f(1.0, 0.0, 1.0),
            ]
        )

        vertexNormals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.vertex)
        self.assertTrue(vertexNormals.isValid())
        self.assertEqual(vertexNormals.interpolation(), UsdGeom.Tokens.vertex)
        self.assertEqual(vertexNormals.effectiveSize(), 5)

        normalsArray = []
        for i in range(5):
            normalsArray.append(vertexNormals.values()[vertexNormals.indices()[i]] if vertexNormals.hasIndices() else vertexNormals.values()[i])

        # Verify all normals are normalized
        for i in range(5):
            normalLength = normalsArray[i].GetLength()
            self.assertAlmostEqual(normalLength, 1.0, places=5, msg=f"Normal at vertex {i} is not normalized")

        sharedVertexNormal = normalsArray[0]
        self.assertGreater(abs(sharedVertexNormal[1]), 0.1, "Shared vertex normal should have Y component from triangle 2")
        self.assertGreater(abs(sharedVertexNormal[2]), 0.1, "Shared vertex normal should have Z component from triangle 1")

        vertex1Normal = normalsArray[1]
        self.assertGreater(abs(vertex1Normal[2]), 0.5, "Vertex 1 normal should be primarily in Z direction")
        vertex2Normal = normalsArray[2]
        self.assertGreater(abs(vertex2Normal[2]), 0.5, "Vertex 2 normal should be primarily in Z direction")
        vertex3Normal = normalsArray[3]
        self.assertGreater(abs(vertex3Normal[1]), 0.5, "Vertex 3 normal should be primarily in Y direction")
        vertex4Normal = normalsArray[4]
        self.assertGreater(abs(vertex4Normal[1]), 0.5, "Vertex 4 normal should be primarily in Y direction")

    def testComputeMeshNormalsInvalidTopology(self):
        # The point array must not be empty
        points = Vt.Vec3fArray()
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Unable to compute normals due to invalid points: Empty array")]
        ):
            normals = usdex.core.computeMeshNormals(FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, points, UsdGeom.Tokens.vertex)
        self.assertFalse(normals.isValid())

        # The sum of the faceVertexCounts must equal the count of the faceVertexIndices otherwise the topology is invalid.
        faceVertexCounts = Vt.IntArray([2])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Unable to compute normals due to invalid topology")]):
            normals = usdex.core.computeMeshNormals(faceVertexCounts, FACE_VERTEX_INDICES, POINTS, UsdGeom.Tokens.vertex)
        self.assertFalse(normals.isValid())

        # The faceVertexIndices must be within the range of the points otherwise the topology is invalid.
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(0.0, 0.0, 1.0)])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Unable to compute normals due to invalid topology")]):
            normals = usdex.core.computeMeshNormals(FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, points, UsdGeom.Tokens.vertex)
        self.assertFalse(normals.isValid())

        # Test empty face vertex counts
        emptyFaceVertexCounts = Vt.IntArray()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Unable to compute normals due to invalid topology")]):
            normals = usdex.core.computeMeshNormals(emptyFaceVertexCounts, FACE_VERTEX_INDICES, POINTS, UsdGeom.Tokens.vertex)
        self.assertFalse(normals.isValid())

        # Test empty face vertex indices
        emptyFaceVertexIndices = Vt.IntArray()
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Unable to compute normals due to invalid topology")]):
            normals = usdex.core.computeMeshNormals(FACE_VERTEX_COUNTS, emptyFaceVertexIndices, POINTS, UsdGeom.Tokens.vertex)
        self.assertFalse(normals.isValid())

        # Invalid topology scenario that is not caught by prior checks
        # Test with negative face vertex indices
        faceVertexCounts = Vt.IntArray([3])
        faceVertexIndices = Vt.IntArray([-1, 0, 1])
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 0.0, 0.0), Gf.Vec3f(0.0, 1.0, 0.0)])
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*Unable to compute normals due to invalid topology")]):
            normals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.vertex)
        self.assertFalse(normals.isValid())

    def testComputeMeshNormalsInvalidInterpolation(self):
        # Invalid interpolation value. Include varying and one other clearly invalid value.
        faceVertexCounts = Vt.IntArray([3])
        faceVertexIndices = Vt.IntArray([0, 1, 2])
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 0.0, 0.0), Gf.Vec3f(0.0, 1.0, 0.0)])

        # Test with "varying" interpolation
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Unable to compute normals due to unsupported interpolation.*varying.*")]
        ):
            normals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, "varying")
        self.assertFalse(normals.isValid())

        # Test with another clearly invalid interpolation value
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Unable to compute normals due to unsupported interpolation.*invalid.*")]
        ):
            normals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, "invalid")
        self.assertFalse(normals.isValid())

    def testComputeMeshNormalsFallback(self):
        # Topology data where one or more faces have less than 3 vertices
        faceVertexCounts = Vt.IntArray([2, 3])
        faceVertexIndices = Vt.IntArray([0, 1, 0, 1, 2])
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 0.0, 0.0), Gf.Vec3f(0.0, 1.0, 0.0)])
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Some faces are degenerate and have been assigned fallback normals.*")]
        ):
            normals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.uniform)
        self.assertTrue(normals.isValid())
        self.assertEqual(normals.interpolation(), UsdGeom.Tokens.uniform)
        self.assertEqual(normals.effectiveSize(), 2)

        # Topology data where one or more faces are degenerate and the default normal has been assigned
        faceVertexCounts = Vt.IntArray([3])
        faceVertexIndices = Vt.IntArray([0, 1, 2])
        points = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(1.0, 0.0, 0.0), Gf.Vec3f(2.0, 0.0, 0.0)])
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Some faces are degenerate and have been assigned fallback normals.*")]
        ):
            normals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.uniform)
        self.assertTrue(normals.isValid())
        self.assertEqual(normals.interpolation(), UsdGeom.Tokens.uniform)

        # Topology data where an unused vertex is assigned the default normal
        faceVertexCounts = Vt.IntArray([3])
        faceVertexIndices = Vt.IntArray([0, 1, 2])
        points = Vt.Vec3fArray(
            [
                Gf.Vec3f(0.0, 0.0, 0.0),
                Gf.Vec3f(1.0, 0.0, 0.0),
                Gf.Vec3f(0.0, 1.0, 0.0),
                Gf.Vec3f(2.0, 2.0, 2.0),
            ]
        )
        with usdex.test.ScopedDiagnosticChecker(
            self, [(Tf.TF_DIAGNOSTIC_WARNING_TYPE, ".*Some vertices have no contributing faces and have been assigned fallback normals.*")]
        ):
            normals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.vertex)
        self.assertTrue(normals.isValid())
        self.assertEqual(normals.interpolation(), UsdGeom.Tokens.vertex)
        self.assertEqual(normals.effectiveSize(), 4)

    def testComputeMeshNormalsSmallVertices(self):
        faceVertexCounts = Vt.IntArray([4])
        faceVertexIndices = Vt.IntArray([0, 1, 2, 3])

        # Testing on a rectangle with normal (0, 1, 0).
        _vertices = [
            Gf.Vec3f(0.0, 0.0, 0.0),
            Gf.Vec3f(0.5, 0.0, 0.0),
            Gf.Vec3f(0.5, 0.0, -0.5),
            Gf.Vec3f(0, 0.0, -0.5),
        ]
        n = Gf.Vec3f(0.0, 1.0, 0.0)

        scale = 1.0
        for i in range(6):
            vertices = [v * scale for v in _vertices]
            points = Vt.Vec3fArray(vertices)
            normals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.uniform)
            self.assertTrue(normals.isValid())
            self.assertEqual(normals.interpolation(), UsdGeom.Tokens.uniform)
            self.assertEqual(normals.effectiveSize(), 1)
            n_dot = Gf.Dot(normals.values()[0], n)
            self.assertAlmostEqual(n_dot, 1.0, places=6)
            scale *= 0.1

        # Testing normals for free-orientation rectangles.
        # These are vertices on the same plane.
        _vertices = [
            Gf.Vec3f(0.996, 2.591, -0.828),
            Gf.Vec3f(10.579, 5.449, -0.828),
            Gf.Vec3f(9.003, 10.733, -9.171),
            Gf.Vec3f(-0.579, 7.875, -9.171),
        ]

        # Calculate the normal for the rectangle.
        e1 = _vertices[1] - _vertices[0]
        e2 = _vertices[2] - _vertices[1]
        n = Gf.Cross(e1, e2).GetNormalized()

        scale = 1.0
        for i in range(6):
            vertices = [v * scale for v in _vertices]
            points = Vt.Vec3fArray(vertices)
            normals = usdex.core.computeMeshNormals(faceVertexCounts, faceVertexIndices, points, UsdGeom.Tokens.uniform)
            self.assertTrue(normals.isValid())
            self.assertEqual(normals.interpolation(), UsdGeom.Tokens.uniform)
            self.assertEqual(normals.effectiveSize(), 1)
            n_dot = Gf.Dot(normals.values()[0], n)
            self.assertAlmostEqual(n_dot, 1.0, places=6)
            scale *= 0.1

    def testComputeMeshNormalsWithExistingMesh(self):
        stage = self.createTestStage()

        # Create a mesh with no normal vectors.
        path = Sdf.Path("/World/TestMesh_normals_uniform")
        mesh_normals_uniform = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertTrue(mesh_normals_uniform.GetPrim().IsValid())

        path = Sdf.Path("/World/TestMesh_normals_vertex")
        mesh_normals_vertex = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertTrue(mesh_normals_vertex.GetPrim().IsValid())

        path = Sdf.Path("/World/TestMesh_normals_faceVarying")
        mesh_normals_faceVarying = usdex.core.definePolyMesh(stage, path, FACE_VERTEX_COUNTS, FACE_VERTEX_INDICES, POINTS)
        self.assertTrue(mesh_normals_faceVarying.GetPrim().IsValid())

        # Verify that the mesh has no normals.
        self.assertFalse(mesh_normals_uniform.GetNormalsAttr().IsAuthored())
        self.assertFalse(mesh_normals_vertex.GetNormalsAttr().IsAuthored())
        self.assertFalse(mesh_normals_faceVarying.GetNormalsAttr().IsAuthored())
        primvarsAPI = UsdGeom.PrimvarsAPI(mesh_normals_uniform.GetPrim())
        primvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.normals)
        self.assertFalse(primvar.HasAuthoredValue())
        primvarsAPI = UsdGeom.PrimvarsAPI(mesh_normals_vertex.GetPrim())
        primvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.normals)
        self.assertFalse(primvar.HasAuthoredValue())
        primvarsAPI = UsdGeom.PrimvarsAPI(mesh_normals_faceVarying.GetPrim())
        primvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.normals)
        self.assertFalse(primvar.HasAuthoredValue())

        # Compute mesh normals (uniform).
        normals = usdex.core.computeMeshNormals(mesh_normals_uniform, UsdGeom.Tokens.uniform)
        self.assertTrue(normals.isValid())
        self.assertEqual(normals.interpolation(), UsdGeom.Tokens.uniform)
        self.assertEqual(normals.effectiveSize(), 2)

        # Verify that the normals are stored in the mesh.
        primvarsAPI = UsdGeom.PrimvarsAPI(mesh_normals_uniform.GetPrim())
        primvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.normals)
        self.assertTrue(primvar.IsDefined())
        self.assertTrue(primvar.HasAuthoredValue())
        self.assertTrue(primvar.GetInterpolation() == UsdGeom.Tokens.uniform)
        self.assertTrue(len(primvar.Get()) > 0)
        self.assertEqual(len(primvar.GetIndices()), 2)

        # Compute mesh normals (vertex).
        normals = usdex.core.computeMeshNormals(mesh_normals_vertex, UsdGeom.Tokens.vertex)
        self.assertTrue(normals.isValid())
        self.assertEqual(normals.interpolation(), UsdGeom.Tokens.vertex)
        self.assertEqual(normals.effectiveSize(), 6)

        # Verify that the normals are stored in the mesh.
        primvarsAPI = UsdGeom.PrimvarsAPI(mesh_normals_vertex.GetPrim())
        primvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.normals)
        self.assertTrue(primvar.IsDefined())
        self.assertTrue(primvar.HasAuthoredValue())
        self.assertTrue(primvar.GetInterpolation() == UsdGeom.Tokens.vertex)
        self.assertTrue(len(primvar.Get()) > 0)
        self.assertEqual(len(primvar.GetIndices()), 6)

        # Compute mesh normals (faceVarying).
        normals = usdex.core.computeMeshNormals(mesh_normals_faceVarying, UsdGeom.Tokens.faceVarying)
        self.assertTrue(normals.isValid())
        self.assertEqual(normals.interpolation(), UsdGeom.Tokens.faceVarying)
        self.assertEqual(normals.effectiveSize(), 8)

        # Verify that the normals are stored in the mesh.
        primvarsAPI = UsdGeom.PrimvarsAPI(mesh_normals_faceVarying.GetPrim())
        primvar = primvarsAPI.GetPrimvar(UsdGeom.Tokens.normals)
        self.assertTrue(primvar.IsDefined())
        self.assertTrue(primvar.HasAuthoredValue())
        self.assertTrue(primvar.GetInterpolation() == UsdGeom.Tokens.faceVarying)
        self.assertTrue(len(primvar.Get()) > 0)
        self.assertEqual(len(primvar.GetIndices()), 8)
