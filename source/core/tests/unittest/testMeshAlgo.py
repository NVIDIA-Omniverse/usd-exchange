# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

import omni.asset_validator
import usdex.core
import usdex.test
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade, UsdUtils, Vt
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

    # Error message prefix for each subset-definition function (must match MeshAlgo.cpp).
    _SUBSET_ERROR_PREFIX = {
        usdex.core.definePartitionedSubsets: "partitioned subsets",
        usdex.core.defineNonOverlappingSubsets: "non-overlapping subsets",
        usdex.core.defineUnrestrictedSubsets: "unrestricted subsets",
    }

    def defineQuadMesh(self, stage: Usd.Stage, name: str) -> UsdGeom.Mesh:
        # Create a mesh with four faces for subset verification.
        default_prim = stage.GetDefaultPrim()
        vertices = [
            Gf.Vec3f(-50.0, 0.0, 50.0),
            Gf.Vec3f(0.0, 0.0, 50.0),
            Gf.Vec3f(50.0, 0.0, 50.0),
            Gf.Vec3f(-50.0, 0.0, 0.0),
        ]
        face_vertex_indices = [0, 1, 2, 3]
        face_vertex_counts = [4]
        normals = [
            Gf.Vec3f(0.0, 1.0, 0.0),
        ]
        normals_indices = [0] * 4
        points = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray(vertices))
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray(normals), indices=Vt.IntArray(normals_indices))
        mesh = usdex.core.definePolyMesh(
            default_prim,
            name,
            faceVertexCounts=Vt.IntArray(face_vertex_counts),
            faceVertexIndices=Vt.IntArray(face_vertex_indices),
            points=points.values(),
            normals=normals,
        )
        return mesh

    def define4faceMesh(self, stage: Usd.Stage, name: str) -> UsdGeom.Mesh:
        # Create a mesh with four faces for subset verification.
        default_prim = stage.GetDefaultPrim()
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
        face_vertex_indices = [0, 1, 4, 3, 1, 2, 5, 4, 3, 4, 7, 6, 4, 5, 8, 7]
        face_vertex_counts = [4, 4, 4, 4]
        normals = [
            Gf.Vec3f(0.0, 1.0, 0.0),
        ]
        normals_indices = [0] * 16

        points = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray(vertices))
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, Vt.Vec3fArray(normals), indices=Vt.IntArray(normals_indices))
        mesh = usdex.core.definePolyMesh(
            default_prim,
            name,
            faceVertexCounts=Vt.IntArray(face_vertex_counts),
            faceVertexIndices=Vt.IntArray(face_vertex_indices),
            points=points.values(),
            normals=normals,
        )
        return mesh

    def checkErrorDefineGeomSubsets(
        self,
        stage: Usd.Stage,
        define_subset_func=usdex.core.definePartitionedSubsets,
    ):
        prefix = self._SUBSET_ERROR_PREFIX[define_subset_func]

        # define mesh.
        plane_mesh = self.define4faceMesh(stage, "error_check_mesh")

        # When the names and indices are empty.
        names = []
        indices = []
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: Unable to define subsets due to invalid names or indices.*",
                )
            ],
        ):
            subsets = define_subset_func(plane_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = plane_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # When an empty subset name is specified.
        names = ["subset", ""]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([2, 3])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: There is an empty subset name.*",
                )
            ],
        ):
            subsets = define_subset_func(plane_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = plane_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # When an invalid subset name is specified.
        names = ["subset", "01234=test"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([2, 3])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: Unable to define subsets due to invalid subset name: .* is not a valid USD identifier.*",
                )
            ],
        ):
            subsets = define_subset_func(plane_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = plane_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # If the same subset name is specified.
        names = ["subset", "subset"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([2, 3])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: Unable to define subsets due to duplicate subset name: 'subset'.*",
                )
            ],
        ):
            subsets = define_subset_func(plane_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = plane_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # When the number of elements in 'names' and 'faceCounts' are different.
        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: Length of names must equal length of indices.*",
                )
            ],
        ):
            subsets = define_subset_func(plane_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = plane_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # When a subset is created that contains no faces.
        names = ["subset1", "subset2", "subset3", "subset4"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([]), Vt.IntArray([2]), Vt.IntArray([3])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: Unable to define subsets due to empty subset indices*",
                )
            ],
        ):
            subsets = define_subset_func(plane_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = plane_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

    def checkDefineGeomSubsets_familyName(self, stage: Usd.Stage, define_subset_func=usdex.core.definePartitionedSubsets):
        prefix = self._SUBSET_ERROR_PREFIX[define_subset_func]

        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([2, 3])]

        # When the family name is valid.
        family_name = "foo"
        family_name_mesh = self.define4faceMesh(stage, "family_name_mesh")
        subsets = define_subset_func(family_name_mesh, names, indices, familyName=family_name)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetFamilyNameAttr().IsAuthored())
            self.assertEqual(subsets[i].GetFamilyNameAttr().Get(), family_name)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{family_name}:familyType"
        prop = family_name_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # When the family name is empty.
        # Empty family names are permitted.
        family_name = ""
        empty_family_name_mesh = self.define4faceMesh(stage, "empty_family_name_mesh")
        subsets = define_subset_func(empty_family_name_mesh, names, indices, familyName=family_name)
        self.assertEqual(len(subsets), 2)

        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetFamilyNameAttr().IsAuthored())
            self.assertEqual(subsets[i].GetFamilyNameAttr().Get(), family_name)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:familyType"
        prop = empty_family_name_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # When the family name is invalid.
        family_name = "01234=test"
        invalid_family_name_mesh = self.define4faceMesh(stage, "invalid_family_name_mesh")
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: Unable to define subsets due to invalid family name: .* is not a valid USD identifier.*",
                )
            ],
        ):
            subsets = define_subset_func(invalid_family_name_mesh, names, indices, familyName=family_name)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{family_name}:familyType"
        prop = invalid_family_name_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

    def checkDefineGeomSubsets_elementType_invalid(self, stage: Usd.Stage, define_subset_func=usdex.core.definePartitionedSubsets):
        prefix = self._SUBSET_ERROR_PREFIX[define_subset_func]
        default_prim = stage.GetDefaultPrim()

        # When the element type is invalid.
        element_type = "invalid"
        invalid_element_type_mesh = self.define4faceMesh(stage, "invalid_element_type_mesh")
        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([2, 3])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: Unable to define subsets due to invalid element type for Mesh subsets: {element_type}.*",
                )
            ],
        ):
            subsets = define_subset_func(invalid_element_type_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = invalid_element_type_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

    def checkDefineGeomSubsets_elementType_valid_all(self, stage: Usd.Stage, define_subset_func=usdex.core.definePartitionedSubsets):
        # Verification of combinations that function correctly.
        default_prim = stage.GetDefaultPrim()
        looks_prim = UsdGeom.Scope.Define(stage, default_prim.GetPath().AppendChild("Looks"))
        self.assertTrue(looks_prim.GetPrim().IsValid())

        # Define material.
        material = usdex.core.definePreviewMaterial(looks_prim.GetPrim(), "material", Gf.Vec3f(0.8, 0.8, 0.8))
        self.assertTrue(material.GetPrim().IsValid())

        # elementType: face.
        # indices specify face indices.
        # Bind the material.
        element_type = UsdGeom.Tokens.face
        face_mesh = self.define4faceMesh(stage, "face_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2, 3]),
        ]
        subsets = define_subset_func(face_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)
            self.assertTrue(usdex.core.bindMaterial(subsets[i].GetPrim(), material))

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = face_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # elementType: edge.
        # indices specify (pointIndex, pointIndex) pairs that define each edge.
        element_type = UsdGeom.Tokens.edge
        edge_mesh = self.defineQuadMesh(stage, "edge_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1, 1, 2]),
            Vt.IntArray([2, 3, 3, 0]),
        ]
        subsets = define_subset_func(edge_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = edge_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # elementType: point.
        # indices specify point indices.
        element_type = UsdGeom.Tokens.point
        point_mesh = self.defineQuadMesh(stage, "point_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2, 3]),
        ]
        subsets = define_subset_func(point_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = point_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

    def checkDefineGeomSubsets_existingSubsets(self, stage: Usd.Stage, define_subset_func=usdex.core.definePartitionedSubsets):
        prefix = self._SUBSET_ERROR_PREFIX[define_subset_func]

        # Storing the first subsets
        check_existing_subsets_mesh = self.define4faceMesh(stage, "check_existing_subsets_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2, 3]),
        ]
        subsets = define_subset_func(check_existing_subsets_mesh, names, indices)
        self.assertEqual(len(subsets), 2)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = check_existing_subsets_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # When the subsets already exist within the given prim.
        # This case will result in an error.
        names = ["subset1", "subset2", "subset3"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2]),
            Vt.IntArray([3]),
        ]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define {prefix}.*: Unable to define subsets due to existing subsets with the same family name: materialBind",
                )
            ],
        ):
            subsets = define_subset_func(check_existing_subsets_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Since there is already a familyName with the same value, this returns True.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = check_existing_subsets_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # If a different family name is specified.
        other_family_name = "foo"
        subsets = define_subset_func(check_existing_subsets_mesh, names, indices, familyName=other_family_name)
        self.assertEqual(len(subsets), 3)
        for i in range(3):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), UsdGeom.Tokens.face)
            self.assertTrue(subsets[i].GetFamilyNameAttr().IsAuthored())
            self.assertEqual(subsets[i].GetFamilyNameAttr().Get(), other_family_name)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{other_family_name}:familyType"
        prop = check_existing_subsets_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

    def testDefinePartitionedSubsets(self):
        stage = self.createTestStage()

        # Check error cases.
        self.checkErrorDefineGeomSubsets(stage, usdex.core.definePartitionedSubsets)

        # Check family name cases.
        self.checkDefineGeomSubsets_familyName(stage, usdex.core.definePartitionedSubsets)

        # Check element type invalid cases.
        self.checkDefineGeomSubsets_elementType_invalid(stage, usdex.core.definePartitionedSubsets)

        # Check element type valid all cases.
        self.checkDefineGeomSubsets_elementType_valid_all(stage, usdex.core.definePartitionedSubsets)

        # Check existing subsets cases.
        self.checkDefineGeomSubsets_existingSubsets(stage, usdex.core.definePartitionedSubsets)

        self.assertIsValidUsd(stage)

    def testDefinePartitionedSubsets_elementType_face(self):
        stage = self.createTestStage()

        # When the face index appears in multiple subsets.
        index_check_mesh = self.define4faceMesh(stage, "index_check_mesh")
        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([1, 2])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define partitioned subsets.*: Found duplicate index 1 in GeomSubset.*",
                )
            ],
        ):
            subsets = usdex.core.definePartitionedSubsets(index_check_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = index_check_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # There is an index for an unassigned face.
        unassigned_face_mesh = self.define4faceMesh(stage, "unassigned_face_mesh")
        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([2])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define partitioned subsets.*: Number of unique indices at time DEFAULT does not match the element count 4.*",
                )
            ],
        ):
            subsets = usdex.core.definePartitionedSubsets(unassigned_face_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = unassigned_face_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        self.assertIsValidUsd(stage)

    def testDefinePartitionedSubsets_elementType_edge(self):
        stage = self.createTestStage()

        # elementType: edge.
        # When the edge indices is missing.
        element_type = UsdGeom.Tokens.edge
        error_edge_mesh = self.defineQuadMesh(stage, "error_edge_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1, 1, 2]),
            Vt.IntArray([2, 3]),  # The edge [3, 0] is missing.
        ]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define partitioned subsets.*: Number of unique indices at time DEFAULT does not match the element count 4.*",
                )
            ],
        ):
            subsets = usdex.core.definePartitionedSubsets(error_edge_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_edge_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # elementType: edge.
        # When there are duplicate pairs of edge indices.
        element_type = UsdGeom.Tokens.edge
        error_duplicate_edge_mesh = self.defineQuadMesh(stage, "error_duplicate_edge_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1, 1, 2]),
            Vt.IntArray([2, 3, 2, 1]),
        ]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define partitioned subsets.*: Found duplicate edge.*\(1, 2\) in GeomSubset at path .* at time DEFAULT.*",
                )
            ],
        ):
            subsets = usdex.core.definePartitionedSubsets(error_edge_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_edge_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        self.assertIsValidUsd(stage)

    def testDefinePartitionedSubsets_elementType_point(self):
        stage = self.createTestStage()

        # elementType: point.
        # When the point indices is missing.
        element_type = UsdGeom.Tokens.point
        error_point_mesh = self.defineQuadMesh(stage, "error_point_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2]),  # The point [3] is missing.
        ]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define partitioned subsets.*: Number of unique indices at time DEFAULT does not match the element count 4.*",
                )
            ],
        ):
            subsets = usdex.core.definePartitionedSubsets(error_point_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_point_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # elementType: point.
        # When there are duplicate of point indices.
        element_type = UsdGeom.Tokens.point
        error_duplicate_point_mesh = self.defineQuadMesh(stage, "error_duplicate_point_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2, 3, 2]),
        ]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define partitioned subsets.*: Found duplicate index 2 in GeomSubset at path .* at time DEFAULT.*",
                )
            ],
        ):
            subsets = usdex.core.definePartitionedSubsets(error_duplicate_point_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_duplicate_point_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        self.assertIsValidUsd(stage)

    def testDefineNonOverlappingSubsets(self):
        stage = self.createTestStage()

        # Check error cases.
        self.checkErrorDefineGeomSubsets(stage, usdex.core.defineNonOverlappingSubsets)

        # Check family name cases.
        self.checkDefineGeomSubsets_familyName(stage, usdex.core.defineNonOverlappingSubsets)

        # Check element type invalid cases.
        self.checkDefineGeomSubsets_elementType_invalid(stage, usdex.core.defineNonOverlappingSubsets)

        # Check element type valid all cases.
        self.checkDefineGeomSubsets_elementType_valid_all(stage, usdex.core.defineNonOverlappingSubsets)

        # Check existing subsets cases.
        self.checkDefineGeomSubsets_existingSubsets(stage, usdex.core.defineNonOverlappingSubsets)

        self.assertIsValidUsd(stage)

    def testDefineNonOverlappingSubsets_elementType_face(self):
        stage = self.createTestStage()

        # When the face index appears in multiple subsets.
        index_check_mesh = self.define4faceMesh(stage, "index_check_mesh")
        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([1, 2])]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define non-overlapping subsets.*: Found duplicate index 1 in GeomSubset.*",
                )
            ],
        ):
            subsets = usdex.core.defineNonOverlappingSubsets(index_check_mesh, names, indices)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = index_check_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        # There is an index for an unassigned face.
        # However, in the case of NonOverlapping, this is permitted.
        unassigned_face_mesh = self.define4faceMesh(stage, "unassigned_face_mesh")
        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([2])]
        subsets = usdex.core.defineNonOverlappingSubsets(unassigned_face_mesh, names, indices)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), UsdGeom.Tokens.face)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = unassigned_face_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        self.assertIsValidUsd(stage)

    def testDefineNonOverlappingSubsets_elementType_edge(self):
        stage = self.createTestStage()

        # elementType: edge.
        # When the edge indices is missing.
        # However, in the case of NonOverlapping, this is permitted.
        element_type = UsdGeom.Tokens.edge
        error_edge_mesh = self.defineQuadMesh(stage, "error_edge_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1, 1, 2]),
            Vt.IntArray([2, 3]),  # The edge [3, 0] is missing.
        ]
        subsets = usdex.core.defineNonOverlappingSubsets(error_edge_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_edge_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # elementType: edge.
        # When there are duplicate pairs of edge indices.
        element_type = UsdGeom.Tokens.edge
        error_duplicate_edge_mesh = self.defineQuadMesh(stage, "error_duplicate_edge_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1, 1, 2]),
            Vt.IntArray([2, 3, 2, 1]),
        ]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define non-overlapping subsets.*: Found duplicate edge.*\(1, 2\) in GeomSubset at path .* at time DEFAULT.*",
                )
            ],
        ):
            subsets = usdex.core.defineNonOverlappingSubsets(error_duplicate_edge_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_duplicate_edge_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        self.assertIsValidUsd(stage)

    def testDefineNonOverlappingSubsets_elementType_point(self):
        stage = self.createTestStage()

        # elementType: point.
        # When the point indices is missing.
        # However, in the case of NonOverlapping, this is permitted.
        element_type = UsdGeom.Tokens.point
        error_point_mesh = self.defineQuadMesh(stage, "error_point_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2]),  # The point [3] is missing.
        ]
        subsets = usdex.core.defineNonOverlappingSubsets(error_point_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_point_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # elementType: point.
        # When there are duplicate of point indices.
        element_type = UsdGeom.Tokens.point
        error_duplicate_point_mesh = self.defineQuadMesh(stage, "error_duplicate_point_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2, 3, 2]),
        ]
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (
                    Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    f".*Failed to define non-overlapping subsets.*: Found duplicate index 2 in GeomSubset at path .* at time DEFAULT.*",
                )
            ],
        ):
            subsets = usdex.core.defineNonOverlappingSubsets(error_duplicate_point_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 0)

        # Check if the parent prim's subset attribute has been removed in case of failure.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_duplicate_point_mesh.GetPrim().GetProperty(propName)
        self.assertFalse(prop.IsValid())

        self.assertIsValidUsd(stage)

    def testDefineUnrestrictedSubsets(self):
        stage = self.createTestStage()

        # Check error cases.
        self.checkErrorDefineGeomSubsets(stage, usdex.core.defineUnrestrictedSubsets)

        # Check family name cases.
        self.checkDefineGeomSubsets_familyName(stage, usdex.core.defineUnrestrictedSubsets)

        # Check element type invalid cases.
        self.checkDefineGeomSubsets_elementType_invalid(stage, usdex.core.defineUnrestrictedSubsets)

        # Check element type valid all cases.
        self.checkDefineGeomSubsets_elementType_valid_all(stage, usdex.core.defineUnrestrictedSubsets)

        # Check existing subsets cases.
        self.checkDefineGeomSubsets_existingSubsets(stage, usdex.core.defineUnrestrictedSubsets)

        self.assertIsValidUsd(stage)

    def testDefineUnrestrictedSubsets_elementType_face(self):
        stage = self.createTestStage()

        # When the face index appears in multiple subsets.
        # However, in the case of Unrestricted, this is permitted.
        index_check_mesh = self.define4faceMesh(stage, "index_check_mesh")
        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([1, 2])]
        subsets = usdex.core.defineUnrestrictedSubsets(index_check_mesh, names, indices)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), UsdGeom.Tokens.face)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = index_check_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # There is an index for an unassigned face.
        # However, in the case of Unrestricted, this is permitted.
        unassigned_face_mesh = self.define4faceMesh(stage, "unassigned_face_mesh")
        names = ["subset1", "subset2"]
        indices = [Vt.IntArray([0, 1]), Vt.IntArray([2])]
        subsets = usdex.core.defineUnrestrictedSubsets(unassigned_face_mesh, names, indices)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), UsdGeom.Tokens.face)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = unassigned_face_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        self.assertIsValidUsd(stage)

    def testDefineUnrestrictedSubsets_elementType_edge(self):
        stage = self.createTestStage()

        # elementType: edge.
        # When the edge indices is missing.
        # However, in the case of Unrestricted, this is permitted.
        element_type = UsdGeom.Tokens.edge
        error_edge_mesh = self.defineQuadMesh(stage, "error_edge_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1, 1, 2]),
            Vt.IntArray([2, 3]),  # The edge [3, 0] is missing.
        ]
        subsets = usdex.core.defineUnrestrictedSubsets(error_edge_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_edge_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # elementType: edge.
        # When there are duplicate pairs of edge indices.
        # However, in the case of Unrestricted, this is permitted.
        element_type = UsdGeom.Tokens.edge
        error_duplicate_edge_mesh = self.defineQuadMesh(stage, "error_duplicate_edge_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1, 1, 2]),
            Vt.IntArray([2, 3, 2, 1]),
        ]
        subsets = usdex.core.defineUnrestrictedSubsets(error_duplicate_edge_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_duplicate_edge_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        self.assertIsValidUsd(stage)

    def testDefineUnrestrictedSubsets_elementType_point(self):
        stage = self.createTestStage()

        # elementType: point.
        # When the point indices is missing.
        # However, in the case of Unrestricted, this is permitted.
        element_type = UsdGeom.Tokens.point
        error_point_mesh = self.defineQuadMesh(stage, "error_point_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2]),  # The point [3] is missing.
        ]
        subsets = usdex.core.defineUnrestrictedSubsets(error_point_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_point_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        # elementType: point.
        # When there are duplicate of point indices.
        # However, in the case of Unrestricted, this is permitted.
        element_type = UsdGeom.Tokens.point
        error_duplicate_point_mesh = self.defineQuadMesh(stage, "error_duplicate_point_mesh")
        names = ["subset1", "subset2"]
        indices = [
            Vt.IntArray([0, 1]),
            Vt.IntArray([2, 3, 2]),
        ]
        subsets = usdex.core.defineUnrestrictedSubsets(error_duplicate_point_mesh, names, indices, elementType=element_type)
        self.assertEqual(len(subsets), 2)
        for i in range(2):
            self.assertTrue(subsets[i].GetPrim().IsValid())
            self.assertEqual(subsets[i].GetPrim().GetName(), names[i])
            self.assertTrue(subsets[i].GetElementTypeAttr().IsAuthored())
            self.assertEqual(subsets[i].GetElementTypeAttr().Get(), element_type)

        # Check if the parent prim's subset attribute is authored.
        propName = f"subsetFamily:{UsdShade.Tokens.materialBind}:familyType"
        prop = error_duplicate_point_mesh.GetPrim().GetProperty(propName)
        self.assertTrue(prop.IsValid())

        self.assertIsValidUsd(stage)
