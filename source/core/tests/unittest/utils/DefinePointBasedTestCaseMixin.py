# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from abc import ABC, abstractmethod

import omni.asset_validator
import usdex.test
from pxr import Gf, Sdf, Tf, UsdGeom, Vt


class DefinePointBasedTestCaseMixin(ABC):
    """Mixin class to make assertions that should be valid for all OpenUSD Exchange SDK functions that define PointBased prims"""

    @property
    @abstractmethod
    def primvarSizes(self):
        """A dict mapping interpolations to expected value size. Only include the interpolations that are valid for the schema type"""
        raise NotImplementedError()

    def assertPrimvar(self, primvar, data):
        """Assert that a primvar is authored as expected"""
        # The value should be authored and the flattened value equal to the expected values
        self.assertTrue(primvar.HasAuthoredValue())
        self.assertEqual(data.values(), primvar.Get())

        # The interpolation should be authored and equal to the expected value
        self.assertTrue(primvar.HasAuthoredInterpolation())
        self.assertEqual(data.interpolation(), primvar.GetInterpolation())

        # The indexing state should be authored and as expected
        self.assertTrue(primvar.GetIndicesAttr().IsAuthored())
        self.assertEqual(data.hasIndices(), primvar.IsIndexed())

        # The primvar should not be time sampled
        self.assertFalse(primvar.ValueMightBeTimeVarying())

    def testNormals(self):
        # Normals are optional but if provided will be authored as primvar
        stage = self.createTestStage()
        primvarName = UsdGeom.Tokens.normals
        parentPath = Sdf.Path("/World/Normals")
        UsdGeom.Scope.Define(stage, parentPath)

        # If normals are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs, normals=None)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())

        # If an empty array is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, Vt.Vec3fArray())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid normals")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # Constant normals are not valid
        path = parentPath.AppendChild("ConstantValue")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0)])
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid normals")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the uniform size then a uniform primvar is authored
        if UsdGeom.Tokens.uniform in self.primvarSizes:
            path = parentPath.AppendChild("UniformValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.uniform])])
            normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.uniform, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, normals)

        if UsdGeom.Tokens.varying in self.primvarSizes:
            # If the array size matches the number of points a varying primvar is authored
            path = parentPath.AppendChild("VaryingValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.varying])])
            normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.varying, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, normals)

            if self.primvarSizes[UsdGeom.Tokens.varying] != self.primvarSizes[UsdGeom.Tokens.vertex]:
                # If the array size matches the number of points a vertex primvar is authored
                path = parentPath.AppendChild("VertexValue")
                values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
                normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values)
                result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
                primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
                self.assertPrimvar(primvar, normals)
        else:
            # If the array size matches the number of points a vertex primvar is authored
            path = parentPath.AppendChild("VertexValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
            normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, normals)

        if UsdGeom.Tokens.faceVarying in self.primvarSizes:
            # If the array size matches the number of face vertices a face varying primvar is authored
            path = parentPath.AppendChild("FaceVaryingValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.faceVarying])])
            normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, normals)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid normals")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        self.validationEngine.disable_rule(omni.asset_validator.IndexedPrimvarChecker)
        self.assertIsValidUsd(stage)

    def testIndexedNormals(self):
        # Normals can optional be indexed
        stage = self.createTestStage()
        primvarName = UsdGeom.Tokens.normals
        parentPath = Sdf.Path("/World/IndexedNormals")
        UsdGeom.Scope.Define(stage, parentPath)

        # If normals and normalsIndices are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs, normals=None)
        primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
        self.assertFalse(primvar.HasAuthoredValue())

        # If an empty array is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        values = Vt.Vec3fArray()
        indices = Vt.IntArray()
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid normals")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # Constant normals are not valid
        path = parentPath.AppendChild("ConstantValue")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
        indices = Vt.IntArray([0])
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid normals")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the uniform size then a uniform primvar is authored
        if UsdGeom.Tokens.uniform in self.primvarSizes:
            path = parentPath.AppendChild("UniformValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0)])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.uniform])])
            normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.uniform, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.normals)
            self.assertPrimvar(primvar, normals)

        if UsdGeom.Tokens.varying in self.primvarSizes:
            # If the array size matches the varying size a varying primvar is authored
            path = parentPath.AppendChild("VaryingValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.varying])])
            normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.varying, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.normals)
            self.assertPrimvar(primvar, normals)

            if self.primvarSizes[UsdGeom.Tokens.varying] != self.primvarSizes[UsdGeom.Tokens.vertex]:
                # If the array size matches the number of points a vertex primvar is authored
                path = parentPath.AppendChild("VertexValue")
                values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0)])
                indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
                normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
                result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
                primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.normals)
                self.assertPrimvar(primvar, normals)
        else:
            # If the array size matches the number of points a vertex primvar is authored
            path = parentPath.AppendChild("VertexValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0)])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
            normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(UsdGeom.Tokens.normals)
            self.assertPrimvar(primvar, normals)

        # If the array size matches the number of face vertices a face varying primvar is authored
        if UsdGeom.Tokens.faceVarying in self.primvarSizes:
            path = parentPath.AppendChild("FaceVaryingValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0)])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.faceVarying])])
            normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
            primvar = UsdGeom.PrimvarsAPI(result).GetPrimvar(primvarName)
            self.assertPrimvar(primvar, normals)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
        indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        normals = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid normals")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but the index values are outside the range of the normals size then no prim is defined
        path = parentPath.AppendChild("IndexValuesGreaterThanRange")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(0.0, 0.0, 0.0)])
        indices = Vt.IntArray([0, 1, 2, 3, 0, 1, 2, 3])  # Face varying interpolation
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid normals")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but there are values less than zero then no prim is defined
        path = parentPath.AppendChild("NegativeIndexValues")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(0.0, 0.0, 0.0)])
        indices = Vt.IntArray([-1, 0, 1, -1, 0, 1])  # Vertex interpolation
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid normals")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, normals=normals)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        self.assertIsValidUsd(stage)

    def testDisplayColor(self):
        # Display color is optional but if provided will be authored as a constant primvar
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/DisplayColor")
        UsdGeom.Scope.Define(stage, parentPath)

        # If display color is not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        primvar = result.GetDisplayColorPrimvar()
        self.assertFalse(primvar.HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=None)
        primvar = result.GetDisplayColorPrimvar()
        self.assertFalse(primvar.HasAuthoredValue())

        # If an explicit constant value is specified a primvar will be authored
        path = parentPath.AppendChild("ConstantValue")
        values = Vt.Vec3fArray([Gf.Vec3f(0.5, 0.5, 0.5)])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        primvar = result.GetDisplayColorPrimvar()
        self.assertPrimvar(primvar, data)

        # If a value less than 0 is specified a primvar will be authored
        path = parentPath.AppendChild("LessThanOneValue")
        values = Vt.Vec3fArray([Gf.Vec3f(-0.5, -0.5, -0.5)])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        primvar = result.GetDisplayColorPrimvar()
        self.assertPrimvar(primvar, data)

        # If a value greater than 1 is specified a primvar will be authored
        path = parentPath.AppendChild("GreaterThanOneValue")
        values = Vt.Vec3fArray([Gf.Vec3f(1.5, 1.5, 1.5)])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        primvar = result.GetDisplayColorPrimvar()
        self.assertPrimvar(primvar, data)

        # If an invalid interpolation is specified no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        values = Vt.Vec3fArray([Gf.Vec3f(1.5, 1.5, 1.5)])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.rightHanded, values)
        with usdex.test.ScopedDiagnosticChecker(
            self,
            [
                (Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, '.*invalid display color: The interpolation "rightHanded" is not valid for 1 values'),
            ],
        ):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If an empty value is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, Vt.Vec3fArray())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display color")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the uniform size then a uniform primvar is authored
        if UsdGeom.Tokens.uniform in self.primvarSizes:
            path = parentPath.AppendChild("UniformValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.uniform])])
            data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.uniform, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
            primvar = result.GetDisplayColorPrimvar()
            self.assertPrimvar(primvar, data)

        if UsdGeom.Tokens.varying in self.primvarSizes:
            # If the array size matches the number of points a varying primvar is authored
            path = parentPath.AppendChild("VaryingValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.varying])])
            data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.varying, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
            primvar = result.GetDisplayColorPrimvar()
            self.assertPrimvar(primvar, data)

            if self.primvarSizes[UsdGeom.Tokens.varying] != self.primvarSizes[UsdGeom.Tokens.vertex]:
                # If the array size matches the number of points a vertex primvar is authored
                path = parentPath.AppendChild("VertexValue")
                values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
                data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values)
                result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
                primvar = result.GetDisplayColorPrimvar()
                self.assertPrimvar(primvar, data)
        else:
            # If the array size matches the number of points a vertex primvar is authored
            path = parentPath.AppendChild("VertexValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
            data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
            primvar = result.GetDisplayColorPrimvar()
            self.assertPrimvar(primvar, data)

        if UsdGeom.Tokens.faceVarying in self.primvarSizes:
            # If the array size matches the number of face vertices a face varying primvar is authored
            path = parentPath.AppendChild("FaceVaryingValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.faceVarying])])
            data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
            primvar = result.GetDisplayColorPrimvar()
            self.assertPrimvar(primvar, data)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 1.0, 0.0) for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display color")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        self.validationEngine.disable_rule(omni.asset_validator.IndexedPrimvarChecker)
        self.assertIsValidUsd(stage)

    def testIndexedDisplayColor(self):
        # Display color can optional be indexed
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/IndexedDisplayColor")
        UsdGeom.Scope.Define(stage, parentPath)

        # If displayColor and displayColorIndices are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        primvar = result.GetDisplayColorPrimvar()
        self.assertFalse(primvar.HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=None)
        primvar = result.GetDisplayColorPrimvar()
        self.assertFalse(primvar.HasAuthoredValue())

        # If an empty array is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        values = Vt.Vec3fArray()
        indices = Vt.IntArray()
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display color")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the uniform size then a uniform primvar is authored
        if UsdGeom.Tokens.uniform in self.primvarSizes:
            path = parentPath.AppendChild("UniformValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.uniform])])
            data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.uniform, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
            primvar = result.GetDisplayColorPrimvar()
            self.assertPrimvar(primvar, data)

        if UsdGeom.Tokens.varying in self.primvarSizes:
            # If the array size matches the varying size a varying primvar is authored
            path = parentPath.AppendChild("VaryingValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.varying])])
            data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.varying, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
            primvar = result.GetDisplayColorPrimvar()
            self.assertPrimvar(primvar, data)

            if self.primvarSizes[UsdGeom.Tokens.varying] != self.primvarSizes[UsdGeom.Tokens.vertex]:
                # If the array size matches the number of points a vertex primvar is authored
                path = parentPath.AppendChild("VertexValue")
                values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
                indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
                data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
                result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
                primvar = result.GetDisplayColorPrimvar()
                self.assertPrimvar(primvar, data)
        else:
            # If the array size matches the number of points a vertex primvar is authored
            path = parentPath.AppendChild("VertexValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
            data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
            primvar = result.GetDisplayColorPrimvar()
            self.assertPrimvar(primvar, data)

        # If the array size matches the number of face vertices a face varying primvar is authored
        if UsdGeom.Tokens.faceVarying in self.primvarSizes:
            path = parentPath.AppendChild("FaceVaryingValue")
            values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.faceVarying])])
            data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
            primvar = result.GetDisplayColorPrimvar()
            self.assertPrimvar(primvar, data)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0)])
        indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display color")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but the index values are outside the range of the values then no prim is defined
        path = parentPath.AppendChild("IndexValuesGreaterThanRange")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(0.0, 0.0, 0.0)])
        indices = Vt.IntArray([0, 1, 2, 3, 0, 1, 2, 3])  # Face varying interpolation
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display color")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but there are values less than zero then no prim is defined
        path = parentPath.AppendChild("NegativeIndexValues")
        values = Vt.Vec3fArray([Gf.Vec3f(0.0, 0.0, 0.0), Gf.Vec3f(0.0, 0.0, 0.0)])
        indices = Vt.IntArray([-1, 0, 1, -1, 0, 1])  # Vertex interpolation
        data = usdex.core.Vec3fPrimvarData(UsdGeom.Tokens.constant, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display color")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayColor=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        self.assertIsValidUsd(stage)

    def testDisplayOpacity(self):
        # Display opacity is optional but if provided will be authored as a constant primvar
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/DisplayOpacity")
        UsdGeom.Scope.Define(stage, parentPath)

        # If display opacity is not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertFalse(primvar.HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=None)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertFalse(primvar.HasAuthoredValue())

        # If an explicit value is specified a primvar will be authored
        path = parentPath.AppendChild("ExplicitValue")
        values = Vt.FloatArray([0.5])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertPrimvar(primvar, data)

        # If a value that matches the fallback value is specified a primvar will be authored
        path = parentPath.AppendChild("FallbackValue")
        values = Vt.FloatArray([1.0])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertPrimvar(primvar, data)

        # If a value less than 0 is specified a primvar will be authored
        path = parentPath.AppendChild("LessThanOneValue")
        values = Vt.FloatArray([-0.5])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertPrimvar(primvar, data)

        # If a value greater than 1 is specified a primvar will be authored
        path = parentPath.AppendChild("GreaterThanOneValue")
        values = Vt.FloatArray([1.5])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values)
        result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertPrimvar(primvar, data)

        # If an empty value is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, Vt.FloatArray())
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display opacity")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the uniform size then a uniform primvar is authored
        if UsdGeom.Tokens.uniform in self.primvarSizes:
            path = parentPath.AppendChild("UniformValue")
            values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.uniform])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
            primvar = result.GetDisplayOpacityPrimvar()
            self.assertPrimvar(primvar, data)

        if UsdGeom.Tokens.varying in self.primvarSizes:
            # If the array size matches the varying size a varying primvar is authored
            path = parentPath.AppendChild("VaryingValue")
            values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.varying])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.varying, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
            primvar = result.GetDisplayOpacityPrimvar()
            self.assertPrimvar(primvar, data)

            if self.primvarSizes[UsdGeom.Tokens.varying] != self.primvarSizes[UsdGeom.Tokens.vertex]:
                # If the array size matches the number of points a vertex primvar is authored
                path = parentPath.AppendChild("VertexValue")
                values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
                data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
                result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
                primvar = result.GetDisplayOpacityPrimvar()
                self.assertPrimvar(primvar, data)
        else:
            # If the array size matches the number of points a vertex primvar is authored
            path = parentPath.AppendChild("VertexValue")
            values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
            primvar = result.GetDisplayOpacityPrimvar()
            self.assertPrimvar(primvar, data)

        if UsdGeom.Tokens.faceVarying in self.primvarSizes:
            # If the array size matches the number of face vertices a face varying primvar is authored
            path = parentPath.AppendChild("FaceVaryingValue")
            values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.faceVarying])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.faceVarying, values)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
            primvar = result.GetDisplayOpacityPrimvar()
            self.assertPrimvar(primvar, data)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.FloatArray([1.0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display opacity")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        self.validationEngine.disable_rule(omni.asset_validator.IndexedPrimvarChecker)
        self.assertIsValidUsd(stage)

    def testIndexedDisplayOpacity(self):
        # Display color can optional be indexed
        stage = self.createTestStage()
        parentPath = Sdf.Path("/World/IndexedDisplayOpacity")
        UsdGeom.Scope.Define(stage, parentPath)

        # If displayOpacity and displayOpacityIndices are not specified no primvar is authored
        path = parentPath.AppendChild("ImplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertFalse(primvar.HasAuthoredValue())

        # If None is specified no primvar is authored
        path = parentPath.AppendChild("ExplicitDefault")
        result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=None)
        primvar = result.GetDisplayOpacityPrimvar()
        self.assertFalse(primvar.HasAuthoredValue())

        # If an empty array is specified no valid interpolation is found so no prim is defined
        path = parentPath.AppendChild("EmptyValue")
        values = Vt.FloatArray()
        indices = Vt.IntArray()
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.constant, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display opacity")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches the uniform size then a uniform primvar is authored
        if UsdGeom.Tokens.uniform in self.primvarSizes:
            path = parentPath.AppendChild("UniformValue")
            values = Vt.FloatArray([1])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.uniform])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.uniform, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
            primvar = result.GetDisplayOpacityPrimvar()
            self.assertPrimvar(primvar, data)

        if UsdGeom.Tokens.varying in self.primvarSizes:
            # If the array size matches the varying size a varying primvar is authored
            path = parentPath.AppendChild("VaryingValue")
            values = Vt.FloatArray([1])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.varying])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.varying, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
            primvar = result.GetDisplayOpacityPrimvar()
            self.assertPrimvar(primvar, data)

            if self.primvarSizes[UsdGeom.Tokens.varying] != self.primvarSizes[UsdGeom.Tokens.vertex]:
                # If the array size matches the number of points a vertex primvar is authored
                path = parentPath.AppendChild("VertexValue")
                values = Vt.FloatArray([1])
                indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
                data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
                result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
                primvar = result.GetDisplayOpacityPrimvar()
                self.assertPrimvar(primvar, data)
        else:
            # If the array size matches the number of points a vertex primvar is authored
            path = parentPath.AppendChild("VertexValue")
            values = Vt.FloatArray([1])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
            primvar = result.GetDisplayOpacityPrimvar()
            self.assertPrimvar(primvar, data)

        # If the array size matches the number of face vertices a face varying primvar is authored
        if UsdGeom.Tokens.faceVarying in self.primvarSizes:
            path = parentPath.AppendChild("FaceVaryingValue")
            values = Vt.FloatArray([1])
            indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.faceVarying])])
            data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
            primvar = result.GetDisplayOpacityPrimvar()
            self.assertPrimvar(primvar, data)

        # If the array size does not match any valid interpolations then no prim is defined
        path = parentPath.AppendChild("InvalidValue")
        values = Vt.FloatArray([1])
        indices = Vt.IntArray([0 for _ in range(self.primvarSizes[UsdGeom.Tokens.vertex] + 1)])
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display opacity")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but the index values are outside the range of the normals size then no prim is defined
        path = parentPath.AppendChild("IndexValuesGreaterThanRange")
        values = Vt.FloatArray([0.0, 1.0])
        indices = Vt.IntArray([0, 1, 2, 3, 0, 1, 2, 3])  # Face varying interpolation
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.faceVarying, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display opacity")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        # If the array size matches a valid interpolation but there are values less than zero then no prim is defined
        path = parentPath.AppendChild("NegativeIndexValues")
        values = Vt.FloatArray([0.0, 1.0])
        indices = Vt.IntArray([-1, 0, 1, -1, 0, 1])  # Vertex interpolation
        data = usdex.core.FloatPrimvarData(UsdGeom.Tokens.vertex, values, indices)
        with usdex.test.ScopedDiagnosticChecker(self, [(Tf.TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE, ".*invalid display opacity")]):
            result = self.defineFunc(stage, path, *self.requiredArgs, displayOpacity=data)
        self.assertFalse(result)
        self.assertFalse(stage.GetPrimAtPath(path))

        self.assertIsValidUsd(stage)
