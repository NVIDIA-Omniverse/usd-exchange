// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "usdex/core/PointsAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/usd/usdGeom/points.h>
#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdGeom/tokens.h>

#include <numeric>

using namespace usdex::core;
using namespace pxr;

namespace
{

// Validate the interpolation given the topology information
template <typename T>
bool validatePrimvarInterpolation(const PrimvarData<T>& primvar, const TfTokenVector& interpolations, const VtArray<GfVec3f>& points)
{
    if (std::find(interpolations.begin(), interpolations.end(), primvar.interpolation()) == interpolations.end())
    {
        return false;
    }

    size_t size = primvar.effectiveSize();

    // Constant interpolation requires a single value
    if (primvar.interpolation() == UsdGeomTokens->constant && size == 1)
    {
        return true;
    }

    // Vertex interpolation requires a value for every point
    if (primvar.interpolation() == UsdGeomTokens->vertex && size == points.size())
    {
        return true;
    }

    return false;
}

// Validate a primvar intended for a points prim.
// Accepts a vector of allowed interpolations and returns false if the PrimvarData is not within these allowed values.
// Validates that a valid interpolation was found and that indices (if provided) fit inside the value range.
// If the primvar is invalid and reason is non-null, an error message describing the validation error will be set.
template <typename T>
bool validatePrimvar(const PrimvarData<T>& primvar, const TfTokenVector& interpolations, const VtArray<GfVec3f>& points, std::string* reason)
{
    if (!::validatePrimvarInterpolation<T>(primvar, interpolations, points))
    {
        if (reason != nullptr)
        {
            *reason = TfStringPrintf(
                "The interpolation \"%s\" is not valid for %zu %s",
                primvar.interpolation().GetText(),
                primvar.effectiveSize(),
                primvar.hasIndices() ? "indices" : "values"
            );
        }
        return false;
    }

    if (!primvar.isValid())
    {
        if (reason != nullptr)
        {
            *reason = TfStringPrintf("The primvar data is invalid.");
        }
        return false;
    }

    return true;
}

UsdGeomPoints definePointCloudImpl(
    UsdStagePtr stage,
    const SdfPath& path,
    const VtVec3fArray& points,
    std::optional<const VtInt64Array> ids,
    std::optional<const FloatPrimvarData> widths,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    std::string reason;

    // Early out if the points are empty
    if (points.empty())
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPoints at \"%s\" due to invalid points: Empty array", path.GetAsString().c_str());
        return UsdGeomPoints();
    }

    // Early out if the ids are not valid
    if (ids.has_value() && (points.size() != ids.value().size()))
    {
        TF_RUNTIME_ERROR(
            "Unable to define UsdGeomPoints at \"%s\" due to invalid ids: Expected %zu values but found %zu",
            path.GetAsString().c_str(),
            points.size(),
            ids.value().size()
        );
        return UsdGeomPoints();
    }

    static TfTokenVector s_validInterpolations = { UsdGeomTokens->constant, UsdGeomTokens->vertex };

    if (widths.has_value())
    {
        if (!::validatePrimvar(widths.value(), s_validInterpolations, points, &reason))
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomPoints at \"%s\" due to invalid widths: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomPoints();
        }
    }

    // Early out if normals were specified but not valid
    if (normals.has_value())
    {
        static TfTokenVector s_validNormalsInterpolations = { UsdGeomTokens->vertex };
        if (!::validatePrimvar(normals.value(), s_validNormalsInterpolations, points, &reason))
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomPoints at \"%s\" due to invalid normals: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomPoints();
        }
    }

    // Early out if displayColor was specified but not valid
    if (displayColor.has_value())
    {
        if (!::validatePrimvar(displayColor.value(), s_validInterpolations, points, &reason))
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomPoints at \"%s\" due to invalid display color: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomPoints();
        }
    }

    // Early out if displayOpacity was specified but not valid
    if (displayOpacity.has_value())
    {
        if (!::validatePrimvar(displayOpacity.value(), s_validInterpolations, points, &reason))
        {
            TF_RUNTIME_ERROR(
                "Unable to define UsdGeomPoints at \"%s\" due to invalid display opacity: %s",
                path.GetAsString().c_str(),
                reason.c_str()
            );
            return UsdGeomPoints();
        }
    }

    UsdGeomPoints pointCloud = UsdGeomPoints::Define(stage, path);
    if (!pointCloud)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPoints at \"%s\"", path.GetAsString().c_str());
        return UsdGeomPoints();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = pointCloud.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Author opinions on Points topology attributes
    pointCloud.CreatePointsAttr().Set(points);
    if (ids.has_value())
    {
        pointCloud.CreateIdsAttr().Set(ids.value());
    }
    else
    {
        pointCloud.CreateIdsAttr().Block();
    }

    // Optionally author widths
    if (widths.has_value())
    {
        // Define the normals primvar
        const TfToken& name = UsdGeomTokens->widths;
        const SdfValueTypeName& typeName = SdfValueTypeNames->FloatArray;
        UsdGeomPrimvar primvar = UsdGeomPrimvarsAPI(pointCloud.GetPrim()).CreatePrimvar(name, typeName);
        if (!widths.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set widths primvar for UsdGeomPoints at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Optionally author normals
    if (normals.has_value())
    {
        // Define the normals primvar
        const TfToken& name = UsdGeomTokens->normals;
        const SdfValueTypeName& typeName = SdfValueTypeNames->Normal3fArray;
        UsdGeomPrimvar primvar = UsdGeomPrimvarsAPI(pointCloud.GetPrim()).CreatePrimvar(name, typeName);
        if (!normals.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set normals primvar for UsdGeomPoints at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Optionally author display color
    if (displayColor.has_value())
    {
        UsdGeomPrimvar primvar = pointCloud.CreateDisplayColorPrimvar();
        if (!displayColor.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set display color primvar for UsdGeomPoints at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Optionally author display opacity
    if (displayOpacity.has_value())
    {
        UsdGeomPrimvar primvar = pointCloud.CreateDisplayOpacityPrimvar();
        if (!displayOpacity.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set display opacity primvar for UsdGeomPoints at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Compute an extent for the schema so there is a guarantee that the extent will be correct and authored in all cases.
    VtArray<GfVec3f> extent;
    if (!UsdGeomBoundable::ComputeExtentFromPlugins(pointCloud, UsdTimeCode::Default(), &extent))
    {
        // fallback to basic extents
        UsdGeomPointBased::ComputeExtent(points, &extent);
    }
    pointCloud.CreateExtentAttr().Set(extent);

    return pointCloud;
}

} // namespace

UsdGeomPoints usdex::core::definePointCloud(
    UsdStagePtr stage,
    const SdfPath& path,
    const VtVec3fArray& points,
    std::optional<const VtInt64Array> ids,
    std::optional<const FloatPrimvarData> widths,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPoints due to an invalid location: %s", reason.c_str());
        return UsdGeomPoints();
    }

    return ::definePointCloudImpl(stage, path, points, ids, widths, normals, displayColor, displayOpacity);
}

UsdGeomPoints usdex::core::definePointCloud(
    UsdPrim parent,
    const std::string& name,
    const VtVec3fArray& points,
    std::optional<const VtInt64Array> ids,
    std::optional<const FloatPrimvarData> widths,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPoints due to an invalid location: %s", reason.c_str());
        return UsdGeomPoints();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return ::definePointCloudImpl(stage, path, points, ids, widths, normals, displayColor, displayOpacity);
}

UsdGeomPoints usdex::core::definePointCloud(
    UsdPrim prim,
    const VtVec3fArray& points,
    std::optional<const FloatPrimvarData> widths,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    // Early out if the prim is not valid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomPoints on invalid prim");
        return UsdGeomPoints();
    }

    // Warn if original prim is not Scope or Xform
    TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Points\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return ::definePointCloudImpl(stage, path, points, std::nullopt, widths, normals, displayColor, displayOpacity);
}
