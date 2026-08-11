// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "usdex/core/CurvesAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/usd/usdGeom/basisCurves.h>
#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdGeom/tokens.h>

#include <numeric>

using namespace usdex::core;
using namespace pxr;

namespace
{

// Validate the topology attributes for a basis curves prim.
bool validateTopology(
    const pxr::VtIntArray& curveVertexCounts,
    size_t numPoints,
    const pxr::TfToken& type,
    const pxr::TfToken& basis,
    const pxr::TfToken& wrap,
    std::string* reason
)
{
    // validate tokens compatiblity
    if (type == UsdGeomTokens->linear)
    {
        if (wrap != UsdGeomTokens->nonperiodic && wrap != UsdGeomTokens->periodic)
        {
            *reason = TfStringPrintf(
                "The wrap \"%s\" is invalid for %s curves. It must be \"%s\" or \"%s\".",
                wrap.GetText(),
                type.GetText(),
                UsdGeomTokens->nonperiodic.GetText(),
                UsdGeomTokens->periodic.GetText()
            );
            return false;
        }
    }
    else if (type == UsdGeomTokens->cubic)
    {
        if (basis != UsdGeomTokens->bezier && basis != UsdGeomTokens->bspline && basis != UsdGeomTokens->catmullRom)
        {
            *reason = TfStringPrintf(
                "The basis \"%s\" is invalid for cubic curves. It must be \"%s\", \"%s\", or \"%s\".",
                basis.GetText(),
                UsdGeomTokens->bezier.GetText(),
                UsdGeomTokens->bspline.GetText(),
                UsdGeomTokens->catmullRom.GetText()
            );
            return false;
        }
        else if (wrap != UsdGeomTokens->nonperiodic && wrap != UsdGeomTokens->periodic && wrap != UsdGeomTokens->pinned)
        {
            *reason = TfStringPrintf(
                "The wrap \"%s\" is invalid for %s curves. It must be \"%s\", \"%s\", or \"%s\".",
                wrap.GetText(),
                basis.GetText(),
                UsdGeomTokens->nonperiodic.GetText(),
                UsdGeomTokens->periodic.GetText(),
                UsdGeomTokens->pinned.GetText()
            );
            return false;
        }
    }

    // validate actual topology now that we know the curve specification is valid
    size_t numVertices = 0;
    for (size_t i = 0, numCurves = curveVertexCounts.size(); i < numCurves; ++i)
    {
        const int vertCount = curveVertexCounts[i];
        if (type == UsdGeomTokens->linear)
        {
            if (wrap == UsdGeomTokens->nonperiodic && vertCount < 2)
            {
                *reason = TfStringPrintf(
                    "A minimum of 2 vertices are required to form a valid %s %s curve, but %d vertices were provided for curve %zu.",
                    wrap.GetText(),
                    type.GetText(),
                    vertCount,
                    i
                );
                return false;
            }
            else if (wrap == UsdGeomTokens->periodic && vertCount < 3)
            {
                *reason = TfStringPrintf(
                    "A minimum of 3 vertices are required to form a valid %s %s curve, but %d vertices were provided for curve %zu.",
                    wrap.GetText(),
                    type.GetText(),
                    vertCount,
                    i
                );
                return false;
            }
        }
        else if (type == UsdGeomTokens->cubic)
        {
            if ((wrap == UsdGeomTokens->nonperiodic || basis == UsdGeomTokens->bezier) && vertCount < 4)
            {
                *reason = TfStringPrintf(
                    "A minimum of 4 vertices are required to form a valid %s %s curve, but %d vertices were provided for curve %zu.",
                    wrap.GetText(),
                    basis.GetText(),
                    vertCount,
                    i
                );
                return false;
            }
            else if (wrap == UsdGeomTokens->pinned && (vertCount < 2))
            {
                *reason = TfStringPrintf(
                    "A minimum of 2 vertices are required to form a valid %s %s curve, but %d vertices were provided for curve %zu.",
                    wrap.GetText(),
                    basis.GetText(),
                    vertCount,
                    i
                );
                return false;
            }
            else if (basis == UsdGeomTokens->bezier)
            {
                // these cases can only fail for bezier as vStep == 1 for the others
                static const int s_vStep = 3;
                if (wrap == UsdGeomTokens->nonperiodic && ((vertCount - 4) % s_vStep != 0))
                {
                    static constexpr const char* s_nonperiodicBezierVertCountFormula = "(vertCount - 4) % 3 == 0";
                    *reason = TfStringPrintf(
                        "The number of vertices must match the formula %s to form a valid %s %s curve, but %d vertices were provided for curve %zu.",
                        s_nonperiodicBezierVertCountFormula,
                        wrap.GetText(),
                        basis.GetText(),
                        vertCount,
                        i
                    );
                    return false;
                }
                else if (wrap == UsdGeomTokens->periodic && (vertCount % s_vStep != 0))
                {
                    *reason = TfStringPrintf(
                        "The number of vertices must be divisible by %d to form a valid %s %s curve, but %d vertices were provided for curve %zu.",
                        s_vStep,
                        wrap.GetText(),
                        basis.GetText(),
                        vertCount,
                        i
                    );
                    return false;
                }
            }
            else if (wrap == UsdGeomTokens->periodic && vertCount < 3)
            {
                *reason = TfStringPrintf(
                    "A minimum of 3 vertices are required to form a valid %s %s curve, but %d vertices were provided for curve %zu.",
                    wrap.GetText(),
                    basis.GetText(),
                    vertCount,
                    i
                );
                return false;
            }
        }

        numVertices += vertCount;
    }

    if (numVertices != numPoints)
    {
        *reason = TfStringPrintf("The number of points (%zu) does not match the total curveVertexCounts (%zu).", numPoints, numVertices);
        return false;
    }

    return true;
}

// Determine the list of valid primvar interpolations based on curve type and primvar type
const TfTokenVector& allValidInterpolations(const TfToken& basis, const TfToken& wrap, bool normals)
{
    // All interpolations are valid by default
    static const TfTokenVector s_allValidInterpolations = { UsdGeomTokens->constant,
                                                            UsdGeomTokens->uniform,
                                                            UsdGeomTokens->varying,
                                                            UsdGeomTokens->vertex };

    // There is a reported bug in both UsdGeomBasisCurves and HdBasisCurves with respect to varying primvars on pinned curves (see OpenUSD #2775).
    // As these types of curves are an edge case for clients of OpenUSD Exchange SDK, for now we are considering them invalid to prevent authoring
    // incorrect data. Once the bug is addressed in OpenUSD we will revisit this decision.
    static const TfTokenVector s_validPinnedInterpolations = { UsdGeomTokens->constant, UsdGeomTokens->uniform, UsdGeomTokens->vertex };

    // We consider constant normals to be invalid as well
    static const TfTokenVector s_validNormalsInterpolations = { UsdGeomTokens->uniform, UsdGeomTokens->varying, UsdGeomTokens->vertex };
    static const TfTokenVector s_validPinnedNormalsInterpolations = { UsdGeomTokens->uniform, UsdGeomTokens->vertex };

    if ((basis == UsdGeomTokens->bspline || basis == UsdGeomTokens->catmullRom) && (wrap == UsdGeomTokens->pinned))
    {
        return normals ? s_validPinnedNormalsInterpolations : s_validPinnedInterpolations;
    }

    return normals ? s_validNormalsInterpolations : s_allValidInterpolations;
}

// Compute the required varying primvar size based on the curve topology
size_t varyingPrimvarSize(
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& type,
    const TfToken& basis,
    const TfToken& wrap
)
{
    if (type == UsdGeomTokens->linear)
    {
        return points.size();
    }
    else if (wrap == UsdGeomTokens->periodic)
    {
        int vStep = (basis == UsdGeomTokens->bezier) ? 3 : 1;
        return std::accumulate(
            std::cbegin(curveVertexCounts),
            std::cend(curveVertexCounts),
            0,
            [vStep](int segmentCount, int vertexCount)
            {
                return segmentCount + (vertexCount / vStep);
            }
        );
    }
    else
    {
        int segmentCount = 0;
        if (wrap == UsdGeomTokens->nonperiodic || basis == UsdGeomTokens->bezier)
        {
            int vStep = (basis == UsdGeomTokens->bezier) ? 3 : 1;
            segmentCount = std::accumulate(
                std::cbegin(curveVertexCounts),
                std::cend(curveVertexCounts),
                0,
                [vStep](int segCount, int vertCount)
                {
                    return segCount + ((vertCount - 4) / vStep + 1);
                }
            );
        }
        else if (wrap == UsdGeomTokens->pinned && (basis == UsdGeomTokens->bspline || basis == UsdGeomTokens->catmullRom))
        {
            segmentCount = std::accumulate(
                std::cbegin(curveVertexCounts),
                std::cend(curveVertexCounts),
                0,
                [](int segCount, int vertCount)
                {
                    return segCount + ((vertCount - 2) + 1);
                }
            );
        }

        return segmentCount + curveVertexCounts.size();
    }
}

// Validate the interpolation given the topology information
template <typename T>
bool validatePrimvarInterpolation(
    const PrimvarData<T>& primvar,
    const TfTokenVector& interpolations,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& type,
    const TfToken& basis,
    const TfToken& wrap
)
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

    // Uniform interpolation requires a value for every curve
    if (primvar.interpolation() == UsdGeomTokens->uniform && size == curveVertexCounts.size())
    {
        return true;
    }

    // Varying interpolation requires a complex computation using curveVertexCounts, type, basis, and wrap
    if (primvar.interpolation() == UsdGeomTokens->varying && size == ::varyingPrimvarSize(curveVertexCounts, points, type, basis, wrap))
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

// Validate a primvar intended for a curves prim.
// Accepts a vector of interpolations and returns the first one where the primvar size matches the topology.
// Validates that a valid interpolation was found and that indices (if provided) fit inside the value range.
// If the primvar is invalid and reason is non-null, an error message describing the validation error will be set.
// Returns the interpolations if the primvar is valid, or an empty token otherwise.
template <typename T>
bool validatePrimvar(
    const PrimvarData<T>& primvar,
    const TfTokenVector& interpolations,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& type,
    const TfToken& basis,
    const TfToken& wrap,
    std::string* reason
)
{
    if (!::validatePrimvarInterpolation<T>(primvar, interpolations, curveVertexCounts, points, type, basis, wrap))
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

UsdGeomBasisCurves defineBasisCurves(
    UsdStagePtr stage,
    const SdfPath& path,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& type,
    const TfToken& basis,
    const TfToken& wrap,
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
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves at \"%s\" due to invalid points: Empty array", path.GetAsString().c_str());
        return UsdGeomBasisCurves();
    }

    // Early out if the topology is not valid
    if (!::validateTopology(curveVertexCounts, points.size(), type, basis, wrap, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves at \"%s\" due to invalid topology: %s", path.GetAsString().c_str(), reason.c_str());
        return UsdGeomBasisCurves();
    }

    const TfTokenVector& validInterpolations = ::allValidInterpolations(basis, wrap, /* normals */ false);

    if (widths.has_value())
    {
        if (!::validatePrimvar(widths.value(), validInterpolations, curveVertexCounts, points, type, basis, wrap, &reason))
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves at \"%s\" due to invalid widths: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomBasisCurves();
        }
    }

    // Early out if normals were specified but not valid
    if (normals.has_value())
    {
        bool validNormals = ::validatePrimvar(
            normals.value(),
            ::allValidInterpolations(basis, wrap, /* normals */ true),
            curveVertexCounts,
            points,
            type,
            basis,
            wrap,
            &reason
        );
        if (!validNormals)
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves at \"%s\" due to invalid normals: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomBasisCurves();
        }
    }

    // Early out if displayColor was specified but not valid
    if (displayColor.has_value())
    {
        if (!::validatePrimvar(displayColor.value(), validInterpolations, curveVertexCounts, points, type, basis, wrap, &reason))
        {
            TF_RUNTIME_ERROR(
                "Unable to define UsdGeomBasisCurves at \"%s\" due to invalid display color: %s",
                path.GetAsString().c_str(),
                reason.c_str()
            );
            return UsdGeomBasisCurves();
        }
    }

    // Early out if displayOpacity was specified but not valid
    if (displayOpacity.has_value())
    {
        if (!::validatePrimvar(displayOpacity.value(), validInterpolations, curveVertexCounts, points, type, basis, wrap, &reason))
        {
            TF_RUNTIME_ERROR(
                "Unable to define UsdGeomBasisCurves at \"%s\" due to invalid display opacity: %s",
                path.GetAsString().c_str(),
                reason.c_str()
            );
            return UsdGeomBasisCurves();
        }
    }

    UsdGeomBasisCurves curves = UsdGeomBasisCurves::Define(stage, path);
    if (!curves)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves at \"%s\"", path.GetAsString().c_str());
        return UsdGeomBasisCurves();
    }

    // Author opinions on BasisCurves topology attributes
    curves.CreateTypeAttr().Set(type);
    curves.CreateCurveVertexCountsAttr().Set(curveVertexCounts);
    curves.CreatePointsAttr().Set(points);
    if (type == UsdGeomTokens->cubic)
    {
        curves.CreateBasisAttr().Set(basis);
    }
    curves.CreateWrapAttr().Set(wrap);

    // Explicitly author the specifier and type name
    UsdPrim prim = curves.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Optionally author widths
    if (widths.has_value())
    {
        // Define the normals primvar
        const TfToken& name = UsdGeomTokens->widths;
        const SdfValueTypeName& typeName = SdfValueTypeNames->FloatArray;
        UsdGeomPrimvar primvar = UsdGeomPrimvarsAPI(curves.GetPrim()).CreatePrimvar(name, typeName);
        if (!widths.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set widths primvar for UsdGeomBasisCurves at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Optionally author normals
    if (normals.has_value())
    {
        // Define the normals primvar
        const TfToken& name = UsdGeomTokens->normals;
        const SdfValueTypeName& typeName = SdfValueTypeNames->Normal3fArray;
        UsdGeomPrimvar primvar = UsdGeomPrimvarsAPI(curves.GetPrim()).CreatePrimvar(name, typeName);
        if (!normals.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set normals primvar for UsdGeomBasisCurves at \"%s\"", path.GetAsString().c_str());
        }
        else
        {
            // unclear if this affects curve rendering, but it is a property of UsdGeomPointBased, so we might as well set it explicitly.
            curves.CreateOrientationAttr().Set(UsdGeomTokens->rightHanded);
        }
    }

    // Optionally author display color
    if (displayColor.has_value())
    {
        UsdGeomPrimvar primvar = curves.CreateDisplayColorPrimvar();
        if (!displayColor.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set display color primvar for UsdGeomBasisCurves at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Optionally author display opacity
    if (displayOpacity.has_value())
    {
        UsdGeomPrimvar primvar = curves.CreateDisplayOpacityPrimvar();
        if (!displayOpacity.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set display opacity primvar for UsdGeomBasisCurves at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Compute an extent for the schema so there is a guarantee that the extent will be correct and authored in all cases.
    VtArray<GfVec3f> extent;
    if (!UsdGeomBoundable::ComputeExtentFromPlugins(curves, UsdTimeCode::Default(), &extent))
    {
        // fallback to basic extents
        UsdGeomPointBased::ComputeExtent(points, &extent);
    }
    curves.CreateExtentAttr().Set(extent);

    return curves;
}

} // namespace

UsdGeomBasisCurves usdex::core::defineLinearBasisCurves(
    UsdStagePtr stage,
    const SdfPath& path,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& wrap,
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
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves due to an invalid location: %s", reason.c_str());
        return UsdGeomBasisCurves();
    }

    return ::defineBasisCurves(stage, path, curveVertexCounts, points, UsdGeomTokens->linear, {}, wrap, widths, normals, displayColor, displayOpacity);
}

UsdGeomBasisCurves usdex::core::defineLinearBasisCurves(
    UsdPrim parent,
    const std::string& name,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& wrap,
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
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves due to an invalid location: %s", reason.c_str());
        return UsdGeomBasisCurves();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return ::defineBasisCurves(stage, path, curveVertexCounts, points, UsdGeomTokens->linear, {}, wrap, widths, normals, displayColor, displayOpacity);
}

UsdGeomBasisCurves usdex::core::defineLinearBasisCurves(
    UsdPrim prim,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& wrap,
    std::optional<const FloatPrimvarData> widths,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    // Early out if the prim is not valid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves on invalid prim");
        return UsdGeomBasisCurves();
    }

    // Warn if original prim is not Scope or Xform
    TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"BasisCurves\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return ::defineBasisCurves(stage, path, curveVertexCounts, points, UsdGeomTokens->linear, {}, wrap, widths, normals, displayColor, displayOpacity);
}

UsdGeomBasisCurves usdex::core::defineCubicBasisCurves(
    UsdStagePtr stage,
    const SdfPath& path,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& basis,
    const TfToken& wrap,
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
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves due to an invalid location: %s", reason.c_str());
        return UsdGeomBasisCurves();
    }

    return ::defineBasisCurves(
        stage,
        path,
        curveVertexCounts,
        points,
        UsdGeomTokens->cubic,
        basis,
        wrap,
        widths,
        normals,
        displayColor,
        displayOpacity
    );
}

UsdGeomBasisCurves usdex::core::defineCubicBasisCurves(
    UsdPrim parent,
    const std::string& name,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& basis,
    const TfToken& wrap,
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
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves due to an invalid location: %s", reason.c_str());
        return UsdGeomBasisCurves();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return ::defineBasisCurves(
        stage,
        path,
        curveVertexCounts,
        points,
        UsdGeomTokens->cubic,
        basis,
        wrap,
        widths,
        normals,
        displayColor,
        displayOpacity
    );
}

UsdGeomBasisCurves usdex::core::defineCubicBasisCurves(
    UsdPrim prim,
    const VtIntArray& curveVertexCounts,
    const VtVec3fArray& points,
    const TfToken& basis,
    const TfToken& wrap,
    std::optional<const FloatPrimvarData> widths,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    // Early out if the prim is not valid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomBasisCurves on invalid prim");
        return UsdGeomBasisCurves();
    }

    // Warn if original prim is not Scope or Xform
    TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"BasisCurves\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return ::defineBasisCurves(
        stage,
        path,
        curveVertexCounts,
        points,
        UsdGeomTokens->cubic,
        basis,
        wrap,
        widths,
        normals,
        displayColor,
        displayOpacity
    );
}
