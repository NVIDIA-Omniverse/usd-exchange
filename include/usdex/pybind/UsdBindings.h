// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/pybind/UsdBindings.h
//! @brief Provides pybind11 interoperability for OpenUSD's bound python objects.

#include <pxr/base/arch/defines.h>

#if defined(ARCH_OS_LINUX)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wfloat-conversion" // conversion from ‘double’ to ‘float’ may change value
#include "BindingUtils.h"
#pragma GCC diagnostic pop
#else
#include "BindingUtils.h"
#endif

#include <pxr/base/gf/camera.h>
#include <pxr/base/gf/transform.h>
#include <pxr/base/tf/diagnosticBase.h>
#include <pxr/usd/sdf/assetPath.h>
#include <pxr/usd/sdf/layer.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/sdf/primSpec.h>
#include <pxr/usd/sdf/valueTypeName.h>
#include <pxr/usd/usd/attribute.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usdGeom/basisCurves.h>
#include <pxr/usd/usdGeom/camera.h>
#include <pxr/usd/usdGeom/capsule.h>
#include <pxr/usd/usdGeom/capsule_1.h>
#include <pxr/usd/usdGeom/cone.h>
#include <pxr/usd/usdGeom/cube.h>
#include <pxr/usd/usdGeom/cylinder.h>
#include <pxr/usd/usdGeom/cylinder_1.h>
#include <pxr/usd/usdGeom/mesh.h>
#include <pxr/usd/usdGeom/plane.h>
#include <pxr/usd/usdGeom/points.h>
#include <pxr/usd/usdGeom/primvar.h>
#include <pxr/usd/usdGeom/scope.h>
#include <pxr/usd/usdGeom/sphere.h>
#include <pxr/usd/usdGeom/xform.h>
#include <pxr/usd/usdGeom/xformable.h>
#include <pxr/usd/usdLux/distantLight.h>
#include <pxr/usd/usdLux/domeLight.h>
#include <pxr/usd/usdLux/rectLight.h>
#include <pxr/usd/usdLux/shapingAPI.h>
#include <pxr/usd/usdLux/sphereLight.h>
#include <pxr/usd/usdPhysics/fixedJoint.h>
#include <pxr/usd/usdPhysics/joint.h>
#include <pxr/usd/usdPhysics/prismaticJoint.h>
#include <pxr/usd/usdPhysics/revoluteJoint.h>
#include <pxr/usd/usdPhysics/sphericalJoint.h>
#include <pxr/usd/usdShade/material.h>
#include <pxr/usd/usdShade/shader.h>


namespace pybind11::detail
{

//! @defgroup pybind Python Interoperability for pybind11
//!
//! Provides pybind11 interoperability for OpenUSD's bound python objects.
//!
//! Many projects use `pybind11` for python bindings, but OpenUSD 24.08 and older uses `boost::python`, while OpenUSD 24.11 and newer
//! uses a fork of `boost::python` called `pxr_python`.
//!
//! We often need to pass the python objects in and out of c++ between a mix of bound functions.
//! These casters enable pybind11 to consume & to produce OpenUSD bound objects.
//!
//! @note We bind the minimal set of OpenUSD types required by the OpenUSD Exchange SDK public C++ API. Not all types are supported, though more
//! will be added as needed by the public entry points.
//!
//! @{

//! pybind11 interoperability for `GfCamera`
PYBOOST11_TYPE_CASTER(pxr::GfCamera, _("pxr.Gf.Camera"));
//! pybind11 interoperability for `GfQuatd`
PYBOOST11_TYPE_CASTER(pxr::GfQuatd, _("pxr.Gf.Quatd"));
//! pybind11 interoperability for `GfQuatf`
PYBOOST11_TYPE_CASTER(pxr::GfQuatf, _("pxr.Gf.Quatf"));
//! pybind11 interoperability for `GfVec3d`
PYBOOST11_TYPE_CASTER(pxr::GfVec3d, _("pxr.Gf.Vec3d"));
//! pybind11 interoperability for `GfVec3f`
PYBOOST11_TYPE_CASTER(pxr::GfVec3f, _("pxr.Gf.Vec3f"));
//! pybind11 interoperability for `GfVec3i`
PYBOOST11_TYPE_CASTER(pxr::GfVec3i, _("pxr.Gf.Vec3i"));
//! pybind11 interoperability for `GfMatrix4d`
PYBOOST11_TYPE_CASTER(pxr::GfMatrix4d, _("pxr.Gf.Matrix4d"));
//! pybind11 interoperability for `GfTransform`
PYBOOST11_TYPE_CASTER(pxr::GfTransform, _("pxr.Gf.Transform"));
//! pybind11 interoperability for `TfDiagnosticType`
PYBOOST11_TYPE_CASTER(pxr::TfDiagnosticType, _("pxr.Tf.DiagnosticType"));
//! pybind11 interoperability for `SdfAssetPath`
PYBOOST11_TYPE_CASTER(pxr::SdfAssetPath, _("pxr.Sdf.AssetPath"));
//! pybind11 interoperability for `SdfLayerHandle`
PYBOOST11_TYPE_CASTER(pxr::SdfLayerHandle, _("pxr.Sdf.Layer"));
//! pybind11 interoperability for `SdfPath`
PYBOOST11_TYPE_CASTER(pxr::SdfPath, _("pxr.Sdf.Path"));
//! pybind11 interoperability for `SdfValueTypeNames`
PYBOOST11_TYPE_CASTER(pxr::SdfValueTypeName, _("pxr.Sdf.ValueTypeName"));
//! pybind11 interoperability for `SdfPrimSpecHandle`
PYBOOST11_TYPE_CASTER(pxr::SdfPrimSpecHandle, _("pxr.Sdf.PrimSpec"));
//! pybind11 interoperability for `TfToken`
//!
//! Note we want to inform python clients that regular python strings are the expected value type, not `TfToken`
PYBOOST11_TYPE_CASTER(pxr::TfToken, _("str"));
//! pybind11 interoperability for `TfTokenVector`
//!
//! Note we want to inform python clients that regular python a list of strings are the expected value type
PYBOOST11_TYPE_CASTER(pxr::TfTokenVector, _("list(str)"));
//! pybind11 interoperability for `UsdAttribute`
PYBOOST11_TYPE_CASTER(pxr::UsdAttribute, _("pxr.Usd.Attribute"));
//! pybind11 interoperability for `UsdGeomBasisCurves`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomBasisCurves, _("pxr.UsdGeom.BasisCurves"));
//! pybind11 interoperability for `UsdGeomCamera`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomCamera, _("pxr.UsdGeom.Camera"));
//! pybind11 interoperability for `UsdGeomMesh`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomMesh, _("pxr.UsdGeom.Mesh"));
//! pybind11 interoperability for `UsdGeomPoints`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomPoints, _("pxr.UsdGeom.Points"));
//! pybind11 interoperability for `UsdGeomPrimvar`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomPrimvar, _("pxr.UsdGeom.Primvar"));
//! pybind11 interoperability for `UsdGeomScope`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomScope, _("pxr.UsdGeom.Scope"));
//! pybind11 interoperability for `UsdGeomXform`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomXform, _("pxr.UsdGeom.Xform"));
//! pybind11 interoperability for `UsdGeomXformable`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomXformable, _("pxr.UsdGeom.Xformable"));
//! pybind11 interoperability for `UsdLuxDistantLight`
PYBOOST11_TYPE_CASTER(pxr::UsdLuxDistantLight, _("pxr.UsdLux.DistantLight"));
//! pybind11 interoperability for `UsdLuxDomeLight`
PYBOOST11_TYPE_CASTER(pxr::UsdLuxDomeLight, _("pxr.UsdLux.DomeLight"));
#if PXR_VERSION >= 2111
//! pybind11 interoperability for `UsdLuxLightAPI`
PYBOOST11_TYPE_CASTER(pxr::UsdLuxLightAPI, _("pxr.UsdLux.LightAPI"));
#else
//! pybind11 interoperability for `UsdLuxLight`
PYBOOST11_TYPE_CASTER(pxr::UsdLuxLight, _("pxr.UsdLux.Light"));
#endif // PXR_VERSION >= 2111
//! pybind11 interoperability for `UsdLuxRectLight`
PYBOOST11_TYPE_CASTER(pxr::UsdLuxRectLight, _("pxr.UsdLux.RectLight"));
//! pybind11 interoperability for `UsdLuxSphereLight`
PYBOOST11_TYPE_CASTER(pxr::UsdLuxSphereLight, _("pxr.UsdLux.SphereLight"));
//! pybind11 interoperability for `UsdLuxShapingAPI`
PYBOOST11_TYPE_CASTER(pxr::UsdLuxShapingAPI, _("pxr.UsdLux.ShapingAPI"));
//! pybind11 interoperability for `UsdPrim`
PYBOOST11_TYPE_CASTER(pxr::UsdPrim, _("pxr.Usd.Prim"));
//! pybind11 interoperability for `UsdStagePtr`
PYBOOST11_TYPE_CASTER(pxr::UsdStagePtr, _("pxr.Usd.Stage"));
//! pybind11 interoperability for `UsdTimeCode`
PYBOOST11_TYPE_CASTER(pxr::UsdTimeCode, _("pxr.Usd.TimeCode"));
//! pybind11 interoperability for `VtFloatArray`
PYBOOST11_TYPE_CASTER(pxr::VtFloatArray, _("pxr.Vt.FloatArray"));
//! pybind11 interoperability for `VtIntArray`
PYBOOST11_TYPE_CASTER(pxr::VtIntArray, _("pxr.Vt.IntArray"));
//! pybind11 interoperability for `VtInt64Array`
PYBOOST11_TYPE_CASTER(pxr::VtInt64Array, _("pxr.Vt.Int64Array"));
//! pybind11 interoperability for `VtStringArray`
PYBOOST11_TYPE_CASTER(pxr::VtStringArray, _("pxr.Vt.StringArray"));
//! pybind11 interoperability for `VtTokenArray`
PYBOOST11_TYPE_CASTER(pxr::VtTokenArray, _("pxr.Vt.TokenArray"));
//! pybind11 interoperability for `VtVec3fArray`
PYBOOST11_TYPE_CASTER(pxr::VtVec3fArray, _("pxr.Vt.Vec3fArray"));
//! pybind11 interoperability for `VtVec2fArray`
PYBOOST11_TYPE_CASTER(pxr::VtVec2fArray, _("pxr.Vt.Vec2fArray"));
//! pybind11 interoperability for `UsdShadeInput`
PYBOOST11_TYPE_CASTER(pxr::UsdShadeInput, _("pxr.UsdShade.Input"));
//! pybind11 interoperability for `UsdShadeMaterial`
PYBOOST11_TYPE_CASTER(pxr::UsdShadeMaterial, _("pxr.UsdShade.Material"));
//! pybind11 interoperability for `UsdShadeShader`
PYBOOST11_TYPE_CASTER(pxr::UsdShadeShader, _("pxr.UsdShade.Shader"));
//! pybind11 interoperability for `VtValue`
PYBOOST11_TYPE_CASTER(pxr::VtValue, _("pxr.Vt.Value"));
//! pybind11 interoperability for `UsdPhysicsFixedJoint`
PYBOOST11_TYPE_CASTER(pxr::UsdPhysicsFixedJoint, _("pxr.UsdPhysics.FixedJoint"));
//! pybind11 interoperability for `UsdPhysicsRevoluteJoint`
PYBOOST11_TYPE_CASTER(pxr::UsdPhysicsRevoluteJoint, _("pxr.UsdPhysics.RevoluteJoint"));
//! pybind11 interoperability for `UsdPhysicsPrismaticJoint`
PYBOOST11_TYPE_CASTER(pxr::UsdPhysicsPrismaticJoint, _("pxr.UsdPhysics.PrismaticJoint"));
//! pybind11 interoperability for `UsdPhysicsSphericalJoint`
PYBOOST11_TYPE_CASTER(pxr::UsdPhysicsSphericalJoint, _("pxr.UsdPhysics.SphericalJoint"));
//! pybind11 interoperability for `UsdPhysicsJoint`
PYBOOST11_TYPE_CASTER(pxr::UsdPhysicsJoint, _("pxr.UsdPhysics.Joint"));
//! pybind11 interoperability for `UsdGeomSphere`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomSphere, _("pxr.UsdGeom.Sphere"));
//! pybind11 interoperability for `UsdGeomPlane`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomPlane, _("pxr.UsdGeom.Plane"));
//! pybind11 interoperability for `UsdGeomCube`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomCube, _("pxr.UsdGeom.Cube"));
//! pybind11 interoperability for `UsdGeomCone`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomCone, _("pxr.UsdGeom.Cone"));
//! pybind11 interoperability for `UsdGeomCylinder`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomCylinder, _("pxr.UsdGeom.Cylinder"));
//! pybind11 interoperability for `UsdGeomCylinder_1`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomCylinder_1, _("pxr.UsdGeom.Cylinder_1"));
//! pybind11 interoperability for `UsdGeomCapsule`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomCapsule, _("pxr.UsdGeom.Capsule"));
//! pybind11 interoperability for `UsdGeomCapsule_1`
PYBOOST11_TYPE_CASTER(pxr::UsdGeomCapsule_1, _("pxr.UsdGeom.Capsule_1"));
//! @}

} // namespace pybind11::detail
