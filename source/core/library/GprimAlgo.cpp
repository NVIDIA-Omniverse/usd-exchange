// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/GprimAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/base/gf/vec3f.h>
#include <pxr/usd/usdGeom/boundable.h>
#include <pxr/usd/usdGeom/capsule.h>
#include <pxr/usd/usdGeom/cone.h>
#include <pxr/usd/usdGeom/cube.h>
#include <pxr/usd/usdGeom/cylinder.h>
#include <pxr/usd/usdGeom/plane.h>
#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdGeom/sphere.h>

#include <algorithm>
#include <limits>
#include <optional>

using namespace pxr;


UsdGeomPlane usdex::core::definePlane(
    UsdStagePtr stage,
    const SdfPath& path,
    const double width,
    const double length,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string _reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &_reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPlane due to an invalid location: %s", _reason.c_str());
        return UsdGeomPlane();
    }

    UsdGeomPlane plane = UsdGeomPlane::Define(stage, path);
    if (!plane)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPlane at \"%s\"", path.GetAsString().c_str());
        return UsdGeomPlane();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = plane.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    plane.GetAxisAttr().Set(axis);
    plane.GetWidthAttr().Set(width);
    plane.GetLengthAttr().Set(length);

    if (displayColor.has_value())
    {
        plane.GetDisplayColorAttr().Set(VtArray<GfVec3f>{ displayColor.value() });
    }

    if (displayOpacity.has_value())
    {
        plane.GetDisplayOpacityAttr().Set(VtArray<float>{ displayOpacity.value() });
    }

    // Set extent.
    pxr::VtArray<pxr::GfVec3f> extent;
    pxr::UsdGeomBoundable::ComputeExtentFromPlugins(plane, pxr::UsdTimeCode::Default(), &extent);
    plane.GetExtentAttr().Set(extent);

    return plane;
}

UsdGeomPlane usdex::core::definePlane(
    UsdPrim parent,
    const std::string& name,
    const double width,
    const double length,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPlane due to an invalid location: %s", reason.c_str());
        return UsdGeomPlane();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::definePlane(stage, path, width, length, axis, displayColor, displayOpacity);
}

UsdGeomPlane usdex::core::definePlane(
    UsdPrim prim,
    const double width,
    const double length,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPlane on invalid prim");
        return UsdGeomPlane();
    }

    // Warn if original prim is not Plane or Scope or Xform
    const TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Plane && originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform &&
        !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Plane\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    if (originalType == UsdGeomTokens->Plane)
    {
        if (!displayColor.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayColor);
        }
        if (!displayOpacity.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayOpacity);
        }
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPlane due to an invalid location: %s", reason.c_str());
        return UsdGeomPlane();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return usdex::core::definePlane(stage, path, width, length, axis, displayColor, displayOpacity);
}

UsdGeomSphere usdex::core::defineSphere(
    UsdStagePtr stage,
    const SdfPath& path,
    const double radius,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string _reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &_reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomSphere due to an invalid location: %s", _reason.c_str());
        return UsdGeomSphere();
    }

    UsdGeomSphere sphere = UsdGeomSphere::Define(stage, path);
    if (!sphere)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomSphere at \"%s\"", path.GetAsString().c_str());
        return UsdGeomSphere();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = sphere.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    sphere.GetRadiusAttr().Set(radius);

    if (displayColor.has_value())
    {
        sphere.GetDisplayColorAttr().Set(VtArray<GfVec3f>{ displayColor.value() });
    }

    if (displayOpacity.has_value())
    {
        sphere.GetDisplayOpacityAttr().Set(VtArray<float>{ displayOpacity.value() });
    }

    // Set extent.
    pxr::VtArray<pxr::GfVec3f> extent;
    pxr::UsdGeomBoundable::ComputeExtentFromPlugins(sphere, pxr::UsdTimeCode::Default(), &extent);
    sphere.GetExtentAttr().Set(extent);

    return sphere;
}

UsdGeomSphere usdex::core::defineSphere(
    UsdPrim parent,
    const std::string& name,
    const double radius,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomSphere due to an invalid location: %s", reason.c_str());
        return UsdGeomSphere();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineSphere(stage, path, radius, displayColor, displayOpacity);
}

UsdGeomSphere usdex::core::defineSphere(
    UsdPrim prim,
    const double radius,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomSphere on invalid prim");
        return UsdGeomSphere();
    }

    // Warn if original prim is not Sphere or Scope or Xform
    const TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Sphere && originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform &&
        !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Sphere\". Expected original type to be \"\" or \"Sphere\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    if (originalType == UsdGeomTokens->Sphere)
    {
        if (!displayColor.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayColor);
        }
        if (!displayOpacity.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayOpacity);
        }
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomSphere due to an invalid location: %s", reason.c_str());
        return UsdGeomSphere();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return usdex::core::defineSphere(stage, path, radius, displayColor, displayOpacity);
}

UsdGeomCube usdex::core::defineCube(
    UsdStagePtr stage,
    const SdfPath& path,
    const double size,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string _reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &_reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCube due to an invalid location: %s", _reason.c_str());
        return UsdGeomCube();
    }

    UsdGeomCube cube = UsdGeomCube::Define(stage, path);
    if (!cube)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCube at \"%s\"", path.GetAsString().c_str());
        return UsdGeomCube();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = cube.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    cube.GetSizeAttr().Set(size);

    if (displayColor.has_value())
    {
        cube.GetDisplayColorAttr().Set(VtArray<GfVec3f>{ displayColor.value() });
    }

    if (displayOpacity.has_value())
    {
        cube.GetDisplayOpacityAttr().Set(VtArray<float>{ displayOpacity.value() });
    }

    // Set extent.
    pxr::VtArray<pxr::GfVec3f> extent;
    pxr::UsdGeomBoundable::ComputeExtentFromPlugins(cube, pxr::UsdTimeCode::Default(), &extent);
    cube.GetExtentAttr().Set(extent);

    return cube;
}

UsdGeomCube usdex::core::defineCube(
    UsdPrim parent,
    const std::string& name,
    const double size,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCube due to an invalid location: %s", reason.c_str());
        return UsdGeomCube();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineCube(stage, path, size, displayColor, displayOpacity);
}

UsdGeomCube usdex::core::defineCube(
    UsdPrim prim,
    const double size,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCube on invalid prim");
        return UsdGeomCube();
    }

    // Warn if original prim is not Cube or Scope or Xform
    const TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Cube && originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform &&
        !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Cube\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    if (originalType == UsdGeomTokens->Cube)
    {
        if (!displayColor.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayColor);
        }
        if (!displayOpacity.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayOpacity);
        }
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCube due to an invalid location: %s", reason.c_str());
        return UsdGeomCube();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return usdex::core::defineCube(stage, path, size, displayColor, displayOpacity);
}

UsdGeomCone usdex::core::defineCone(
    UsdStagePtr stage,
    const SdfPath& path,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string _reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &_reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCone due to an invalid location: %s", _reason.c_str());
        return UsdGeomCone();
    }

    UsdGeomCone cone = UsdGeomCone::Define(stage, path);
    if (!cone)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCone at \"%s\"", path.GetAsString().c_str());
        return UsdGeomCone();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = cone.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    cone.GetAxisAttr().Set(axis);
    cone.GetRadiusAttr().Set(radius);
    cone.GetHeightAttr().Set(height);

    if (displayColor.has_value())
    {
        cone.GetDisplayColorAttr().Set(VtArray<GfVec3f>{ displayColor.value() });
    }

    if (displayOpacity.has_value())
    {
        cone.GetDisplayOpacityAttr().Set(VtArray<float>{ displayOpacity.value() });
    }

    // Set extent.
    pxr::VtArray<pxr::GfVec3f> extent;
    pxr::UsdGeomBoundable::ComputeExtentFromPlugins(cone, pxr::UsdTimeCode::Default(), &extent);
    cone.GetExtentAttr().Set(extent);

    return cone;
}

UsdGeomCone usdex::core::defineCone(
    UsdPrim parent,
    const std::string& name,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCone due to an invalid location: %s", reason.c_str());
        return UsdGeomCone();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineCone(stage, path, radius, height, axis, displayColor, displayOpacity);
}

UsdGeomCone usdex::core::defineCone(
    UsdPrim prim,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCone on invalid prim");
        return UsdGeomCone();
    }

    // Warn if original prim is not Cone or Scope or Xform
    const TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Cone && originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform &&
        !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Cone\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    if (originalType == UsdGeomTokens->Cone)
    {
        if (!displayColor.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayColor);
        }
        if (!displayOpacity.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayOpacity);
        }
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCone due to an invalid location: %s", reason.c_str());
        return UsdGeomCone();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return usdex::core::defineCone(stage, path, radius, height, axis, displayColor, displayOpacity);
}

UsdGeomCylinder usdex::core::defineCylinder(
    UsdStagePtr stage,
    const SdfPath& path,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string _reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &_reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCylinder due to an invalid location: %s", _reason.c_str());
        return UsdGeomCylinder();
    }

    UsdGeomCylinder cylinder = UsdGeomCylinder::Define(stage, path);
    if (!cylinder)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCylinder at \"%s\"", path.GetAsString().c_str());
        return UsdGeomCylinder();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = cylinder.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    cylinder.GetAxisAttr().Set(axis);
    cylinder.GetRadiusAttr().Set(radius);
    cylinder.GetHeightAttr().Set(height);

    if (displayColor.has_value())
    {
        cylinder.GetDisplayColorAttr().Set(VtArray<GfVec3f>{ displayColor.value() });
    }

    if (displayOpacity.has_value())
    {
        cylinder.GetDisplayOpacityAttr().Set(VtArray<float>{ displayOpacity.value() });
    }

    // Set extent.
    pxr::VtArray<pxr::GfVec3f> extent;
    pxr::UsdGeomBoundable::ComputeExtentFromPlugins(cylinder, pxr::UsdTimeCode::Default(), &extent);
    cylinder.GetExtentAttr().Set(extent);

    return cylinder;
}

UsdGeomCylinder usdex::core::defineCylinder(
    UsdPrim parent,
    const std::string& name,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCylinder due to an invalid location: %s", reason.c_str());
        return UsdGeomCylinder();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineCylinder(stage, path, radius, height, axis, displayColor, displayOpacity);
}

UsdGeomCylinder usdex::core::defineCylinder(
    UsdPrim prim,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCylinder on invalid prim");
        return UsdGeomCylinder();
    }

    // Warn if original prim is not Cylinder or Scope or Xform
    const TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Cylinder && originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform &&
        !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Cylinder\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    if (originalType == UsdGeomTokens->Cylinder)
    {
        if (!displayColor.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayColor);
        }
        if (!displayOpacity.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayOpacity);
        }
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCylinder due to an invalid location: %s", reason.c_str());
        return UsdGeomCylinder();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return usdex::core::defineCylinder(stage, path, radius, height, axis, displayColor, displayOpacity);
}

UsdGeomCapsule usdex::core::defineCapsule(
    UsdStagePtr stage,
    const SdfPath& path,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string _reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &_reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCapsule due to an invalid location: %s", _reason.c_str());
        return UsdGeomCapsule();
    }

    UsdGeomCapsule capsule = UsdGeomCapsule::Define(stage, path);
    if (!capsule)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCapsule at \"%s\"", path.GetAsString().c_str());
        return UsdGeomCapsule();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = capsule.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    capsule.GetAxisAttr().Set(axis);
    capsule.GetRadiusAttr().Set(radius);
    capsule.GetHeightAttr().Set(height);

    if (displayColor.has_value())
    {
        capsule.GetDisplayColorAttr().Set(VtArray<GfVec3f>{ displayColor.value() });
    }

    if (displayOpacity.has_value())
    {
        capsule.GetDisplayOpacityAttr().Set(VtArray<float>{ displayOpacity.value() });
    }

    // Set extent.
    pxr::VtArray<pxr::GfVec3f> extent;
    pxr::UsdGeomBoundable::ComputeExtentFromPlugins(capsule, pxr::UsdTimeCode::Default(), &extent);
    capsule.GetExtentAttr().Set(extent);

    return capsule;
}

UsdGeomCapsule usdex::core::defineCapsule(
    UsdPrim parent,
    const std::string& name,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCapsule due to an invalid location: %s", reason.c_str());
        return UsdGeomCapsule();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineCapsule(stage, path, radius, height, axis, displayColor, displayOpacity);
}

UsdGeomCapsule usdex::core::defineCapsule(
    UsdPrim prim,
    const double radius,
    const double height,
    const TfToken axis,
    const std::optional<GfVec3f> displayColor,
    const std::optional<float> displayOpacity
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCapsule on invalid prim");
        return UsdGeomCapsule();
    }

    // Warn if original prim is not Capsule or Scope or Xform
    const TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Capsule && originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform &&
        !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Capsule\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    if (originalType == UsdGeomTokens->Capsule)
    {
        if (!displayColor.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayColor);
        }
        if (!displayOpacity.has_value())
        {
            UsdGeomPrimvarsAPI(prim).BlockPrimvar(UsdGeomTokens->primvarsDisplayOpacity);
        }
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomCapsule due to an invalid location: %s", reason.c_str());
        return UsdGeomCapsule();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return usdex::core::defineCapsule(stage, path, radius, height, axis, displayColor, displayOpacity);
}
