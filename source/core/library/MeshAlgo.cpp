// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/MeshAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/usd/usdGeom/mesh.h>
#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdGeom/tokens.h>
#include <pxr/usd/usdUtils/pipeline.h>


using namespace usdex::core;
using namespace pxr;

namespace
{

// Validate the interpolation given the topology information
template <typename T>
bool validatePrimvarInterpolation(
    const PrimvarData<T>& primvar,
    const TfTokenVector& interpolations,
    const VtArray<int>& faceVertexCounts,
    const VtArray<int>& faceVertexIndices,
    const VtArray<GfVec3f>& points
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

    // Uniform interpolation requires a value for every face on the mesh
    if (primvar.interpolation() == UsdGeomTokens->uniform && size == faceVertexCounts.size())
    {
        return true;
    }

    // Vertex interpolation requires a value for every point in the mesh
    if (primvar.interpolation() == UsdGeomTokens->vertex && size == points.size())
    {
        return true;
    }

    // Face varying interpolation requires a value for every face vertex in the mesh
    if (primvar.interpolation() == UsdGeomTokens->faceVarying && size == faceVertexIndices.size())
    {
        return true;
    }

    return false;
}

// Validate a primvar intended for a mesh.
// Accepts a vector of allowed interpolations and returns false if the PrimvarData is not within these allowed values.
// Validates that a valid interpolation was found and that indices (if provided) fit inside the value range.
// If the primvar is invalid and reason is non-null, an error message describing the validation error will be set.
template <typename T>
bool validatePrimvar(
    const PrimvarData<T>& primvar,
    const TfTokenVector& interpolations,
    const VtArray<int>& faceVertexCounts,
    const VtArray<int>& faceVertexIndices,
    const VtArray<GfVec3f>& points,
    std::string* reason
)
{
    if (!::validatePrimvarInterpolation<T>(primvar, interpolations, faceVertexCounts, faceVertexIndices, points))
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

// Compute face normals using vector-area approach
std::vector<pxr::GfVec3f> computeFaceNormals(
    const VtIntArray& faceVertexCounts,
    const VtIntArray& faceVertexIndices,
    const VtVec3fArray& points,
    const pxr::GfVec3f& defaultNormal,
    std::string* reason
)
{

    std::vector<pxr::GfVec3f> faceNormals;
    faceNormals.reserve(faceVertexCounts.size());

    GfVec3d vectorArea;
    bool hasDegenerateFaces = false;
    size_t vertexIndex = 0;
    for (size_t faceIndex = 0; faceIndex < faceVertexCounts.size(); ++faceIndex)
    {
        const int vertexCount = faceVertexCounts[faceIndex];
        if (vertexCount < 3)
        {
            hasDegenerateFaces = true;
            // Fallback to a default normal if the face has less than 3 vertices
            faceNormals.push_back(defaultNormal);
            vertexIndex += vertexCount;
            continue;
        }

        vectorArea = GfVec3d(0.0, 0.0, 0.0);

        // Get the first vertex
        const GfVec3f& v0 = points[faceVertexIndices[vertexIndex]];

        // Sum cross products of consecutive edges
        for (int i = 1; i < vertexCount - 1; ++i)
        {
            const GfVec3f& v1 = points[faceVertexIndices[vertexIndex + i]];
            const GfVec3f& v2 = points[faceVertexIndices[vertexIndex + i + 1]];

            // Cross product of (v1-v0) and (v2-v0)
            const GfVec3d edge1 = GfVec3d(v1) - GfVec3d(v0);
            const GfVec3d edge2 = GfVec3d(v2) - GfVec3d(v0);
            const GfVec3d cross = GfCross(edge1, edge2);
            vectorArea += cross;
        }

        // Normalize the vector area to get the face normal
        const double length = vectorArea.GetLength();
        if (length > 1e-14)
        {
            faceNormals.push_back(GfVec3f(vectorArea / length));
        }
        else
        {
            hasDegenerateFaces = true;
            // Fallback to a default normal if the face is degenerate
            faceNormals.push_back(defaultNormal);
        }

        vertexIndex += vertexCount;
    }

    if (hasDegenerateFaces && reason != nullptr)
    {
        *reason = TfStringPrintf("Some faces are degenerate and have been assigned fallback normals");
    }

    return faceNormals;
}

// Compute vertex normals by averaging face normals
std::vector<pxr::GfVec3f> computeVertexNormals(
    const VtIntArray& faceVertexCounts,
    const VtIntArray& faceVertexIndices,
    const VtVec3fArray& points,
    const pxr::GfVec3f& defaultNormal,
    std::string* reason
)
{
    // First compute face normals
    auto faceNormals = computeFaceNormals(faceVertexCounts, faceVertexIndices, points, defaultNormal, reason);
    if (faceNormals.empty())
    {
        return {};
    }

    // Initialize vertex normals to zero
    std::vector<pxr::GfVec3f> vertexNormals(points.size(), GfVec3f(0.0f, 0.0f, 0.0f));

    // Sum face normals for each vertex
    size_t vertexIndex = 0;
    for (size_t faceIndex = 0; faceIndex < faceVertexCounts.size(); ++faceIndex)
    {
        const int vertexCount = faceVertexCounts[faceIndex];
        const GfVec3f& faceNormal = faceNormals[faceIndex];

        for (int i = 0; i < vertexCount; ++i)
        {
            int vertexIdx = faceVertexIndices[vertexIndex + i];
            if (vertexIdx >= 0 && vertexIdx < static_cast<int>(points.size()))
            {
                vertexNormals[vertexIdx] += faceNormal;
            }
        }

        vertexIndex += vertexCount;
    }

    // Normalize vertex normals
    bool hasVerticesWithoutFaces = false;
    for (GfVec3f& normal : vertexNormals)
    {
        float length = normal.GetLength();
        if (length > 1e-6f)
        {
            normal /= length;
        }
        else
        {
            // Fallback to a default normal if the vertex has no contributing faces
            hasVerticesWithoutFaces = true;
            normal = defaultNormal;
        }
    }

    if (hasVerticesWithoutFaces)
    {
        *reason = TfStringPrintf("Some vertices have no contributing faces and have been assigned fallback normals");
    }

    return vertexNormals;
}

// Compute face-varying normals (corner normals)
// This is a simplified implementation that uses the face normal for each corner
std::vector<pxr::GfVec3f> computeFaceVaryingNormals(
    const VtIntArray& faceVertexCounts,
    const VtIntArray& faceVertexIndices,
    const VtVec3fArray& points,
    const pxr::GfVec3f& defaultNormal,
    std::string* reason
)
{
    auto faceNormals = computeFaceNormals(faceVertexCounts, faceVertexIndices, points, defaultNormal, reason);
    if (faceNormals.empty())
    {
        return {};
    }

    // Create face-varying normals by repeating face normals for each corner
    std::vector<pxr::GfVec3f> cornerNormals;
    cornerNormals.reserve(faceVertexIndices.size());

    size_t vertexIndex = 0;
    for (size_t faceIndex = 0; faceIndex < faceVertexCounts.size(); ++faceIndex)
    {
        const int vertexCount = faceVertexCounts[faceIndex];
        const GfVec3f& faceNormal = faceNormals[faceIndex];

        // Assign the same face normal to all corners of this face
        for (int i = 0; i < vertexCount; ++i)
        {
            cornerNormals.push_back(faceNormal);
        }

        vertexIndex += vertexCount;
    }

    return cornerNormals;
}

// Create an indexed Vec3fPrimvarData from a vector of values
Vec3fPrimvarData getIndexedPrimvar(const std::vector<pxr::GfVec3f>& values, const pxr::TfToken& interpolation)
{
    const VtVec3fArray valuesArray(values.begin(), values.end());
    Vec3fPrimvarData primvarData(interpolation, valuesArray);
    primvarData.index();
    return primvarData;
}

Vec3fPrimvarData getInvalidPrimvar()
{
    // Return an invalid primvar to indicate failure
    return Vec3fPrimvarData(UsdGeomTokens->constant, VtVec3fArray());
}

} // namespace

UsdGeomMesh usdex::core::definePolyMesh(
    UsdStagePtr stage,
    const SdfPath& path,
    const VtIntArray& faceVertexCounts,
    const VtIntArray& faceVertexIndices,
    const VtVec3fArray& points,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec2fPrimvarData> uvs,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomMesh due to an invalid location: %s", reason.c_str());
        return UsdGeomMesh();
    }

    // Early out if the points are empty
    if (points.empty())
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomMesh at \"%s\" due to invalid points: Empty array", path.GetAsString().c_str());
        return UsdGeomMesh();
    }

    // Early out if the topology is not valid
    if (!UsdGeomMesh::ValidateTopology(faceVertexIndices, faceVertexCounts, points.size(), &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomMesh at \"%s\" due to invalid topology: %s", path.GetAsString().c_str(), reason.c_str());
        return UsdGeomMesh();
    }

    // Early out if normals were specified but not valid
    if (normals.has_value())
    {
        static const TfTokenVector validInterpolations = { UsdGeomTokens->uniform, UsdGeomTokens->vertex, UsdGeomTokens->faceVarying };
        if (!validatePrimvar(normals.value(), validInterpolations, faceVertexCounts, faceVertexIndices, points, &reason))
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomMesh at \"%s\" due to invalid normals: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomMesh();
        }
    }

    // Early out if uvs were specified but not valid
    if (uvs.has_value())
    {
        static const TfTokenVector validInterpolations = { UsdGeomTokens->vertex, UsdGeomTokens->faceVarying };
        if (!validatePrimvar(uvs.value(), validInterpolations, faceVertexCounts, faceVertexIndices, points, &reason))
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomMesh at \"%s\" due to invalid uvs: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomMesh();
        }
    }

    // All interpolations are valid by default
    static const TfTokenVector s_allValidInterpolations = { UsdGeomTokens->constant,
                                                            UsdGeomTokens->uniform,
                                                            UsdGeomTokens->varying,
                                                            UsdGeomTokens->vertex,
                                                            UsdGeomTokens->faceVarying };

    // Early out if displayColor was specified but not valid
    if (displayColor.has_value())
    {
        if (!::validatePrimvar(displayColor.value(), s_allValidInterpolations, faceVertexCounts, faceVertexIndices, points, &reason))
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomMesh at \"%s\" due to invalid display color: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomMesh();
        }
    }

    // Early out if displayOpacity was specified but not valid
    if (displayOpacity.has_value())
    {
        if (!::validatePrimvar(displayOpacity.value(), s_allValidInterpolations, faceVertexCounts, faceVertexIndices, points, &reason))
        {
            TF_RUNTIME_ERROR("Unable to define UsdGeomMesh at \"%s\" due to invalid display opacity: %s", path.GetAsString().c_str(), reason.c_str());
            return UsdGeomMesh();
        }
    }

    // Define the Mesh and check that this was successful
    UsdGeomMesh mesh = UsdGeomMesh::Define(stage, path);
    if (!mesh)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomMesh at \"%s\"", path.GetAsString().c_str());
        return UsdGeomMesh();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = mesh.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Author opinions on Mesh attributes
    mesh.CreateOrientationAttr().Set(UsdGeomTokens->rightHanded);
    mesh.CreateSubdivisionSchemeAttr().Set(UsdGeomTokens->none);

    // Create and set required topology attributes
    mesh.CreateFaceVertexCountsAttr().Set(faceVertexCounts);
    mesh.CreateFaceVertexIndicesAttr().Set(faceVertexIndices);
    mesh.CreatePointsAttr().Set(points);

    // Compute an extent from the points so there is a guarantee that the extent will be correct and authored in all cases.
    VtArray<GfVec3f> extent;
    UsdGeomPointBased::ComputeExtent(points, &extent);
    mesh.CreateExtentAttr().Set(extent);

    // Optionally author normals
    if (normals.has_value())
    {
        // Define the normals primvar
        const TfToken& name = UsdGeomTokens->normals;
        const SdfValueTypeName& typeName = SdfValueTypeNames->Normal3fArray;
        UsdGeomPrimvar primvar = UsdGeomPrimvarsAPI(mesh.GetPrim()).CreatePrimvar(name, typeName);
        if (!normals.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set normals primvar for UsdGeomMesh at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Optionally author the primary UV set
    if (uvs.has_value())
    {
        const TfToken& name = UsdUtilsGetPrimaryUVSetName();
        const SdfValueTypeName& typeName = SdfValueTypeNames->TexCoord2fArray;
        UsdGeomPrimvar primvar = UsdGeomPrimvarsAPI(mesh.GetPrim()).CreatePrimvar(name, typeName);
        if (!uvs.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set uvs primvar for UsdGeomMesh at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Optionally author display color
    if (displayColor.has_value())
    {
        UsdGeomPrimvar primvar = mesh.CreateDisplayColorPrimvar();
        if (!displayColor.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set display color primvar for UsdGeomMesh at \"%s\"", path.GetAsString().c_str());
        }
    }

    // Optionally author display opacity
    if (displayOpacity.has_value())
    {
        UsdGeomPrimvar primvar = mesh.CreateDisplayOpacityPrimvar();
        if (!displayOpacity.value().setPrimvar(primvar))
        {
            TF_WARN("Failed to set display opacity primvar for UsdGeomMesh at \"%s\"", path.GetAsString().c_str());
        }
    }

    return mesh;
}

UsdGeomMesh usdex::core::definePolyMesh(
    UsdPrim parent,
    const std::string& name,
    const VtIntArray& faceVertexCounts,
    const VtIntArray& faceVertexIndices,
    const VtVec3fArray& points,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec2fPrimvarData> uvs,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomMesh due to an invalid location: %s", reason.c_str());
        return UsdGeomMesh();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::definePolyMesh(stage, path, faceVertexCounts, faceVertexIndices, points, normals, uvs, displayColor, displayOpacity);
}

UsdGeomMesh usdex::core::definePolyMesh(
    UsdPrim prim,
    const VtIntArray& faceVertexCounts,
    const VtIntArray& faceVertexIndices,
    const VtVec3fArray& points,
    std::optional<const Vec3fPrimvarData> normals,
    std::optional<const Vec2fPrimvarData> uvs,
    std::optional<const Vec3fPrimvarData> displayColor,
    std::optional<const FloatPrimvarData> displayOpacity
)
{
    // Early out if the prim is invalid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomMesh due to an invalid prim");
        return UsdGeomMesh();
    }

    // Warn if original prim is not Scope or Xform
    TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Mesh\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::definePolyMesh(stage, path, faceVertexCounts, faceVertexIndices, points, normals, uvs, displayColor, displayOpacity);
}

Vec3fPrimvarData usdex::core::computeMeshNormals(
    const VtIntArray& faceVertexCounts,
    const VtIntArray& faceVertexIndices,
    const VtVec3fArray& points,
    const TfToken& interpolation,
    const GfVec3f& fallback
)
{
    // Validate interpolation
    if (interpolation != UsdGeomTokens->uniform && interpolation != UsdGeomTokens->vertex && interpolation != UsdGeomTokens->faceVarying)
    {
        TF_WARN(
            "Unable to compute normals due to unsupported interpolation '%s'. Only 'uniform', 'vertex', and 'faceVarying' are supported.",
            interpolation.GetText()
        );
        return getInvalidPrimvar();
    }

    // Early out if the points are empty
    if (points.empty())
    {
        TF_RUNTIME_ERROR("Unable to compute normals due to invalid points: Empty array");
        return getInvalidPrimvar();
    }

    // Early out if the topology is not valid
    std::string reason;
    if (!UsdGeomMesh::ValidateTopology(faceVertexIndices, faceVertexCounts, points.size(), &reason))
    {
        TF_RUNTIME_ERROR("Unable to compute normals due to invalid topology: %s", reason.c_str());
        return getInvalidPrimvar();
    }

    // Normalize the fallback vector to ensure it's a valid normal
    GfVec3f defaultNormal = fallback.GetNormalized();

    if (interpolation == UsdGeomTokens->uniform)
    {
        auto faceNormals = computeFaceNormals(faceVertexCounts, faceVertexIndices, points, defaultNormal, &reason);
        if (!reason.empty())
        {
            TF_WARN("%s", reason.c_str());
        }
        if (faceNormals.empty())
        {
            return getInvalidPrimvar();
        }
        return getIndexedPrimvar(faceNormals, UsdGeomTokens->uniform);
    }
    else if (interpolation == UsdGeomTokens->vertex)
    {
        auto vertexNormals = computeVertexNormals(faceVertexCounts, faceVertexIndices, points, defaultNormal, &reason);
        if (!reason.empty())
        {
            TF_WARN("%s", reason.c_str());
        }
        if (vertexNormals.empty())
        {
            return getInvalidPrimvar();
        }
        return getIndexedPrimvar(vertexNormals, UsdGeomTokens->vertex);
    }
    else if (interpolation == UsdGeomTokens->faceVarying)
    {
        auto cornerNormals = computeFaceVaryingNormals(faceVertexCounts, faceVertexIndices, points, defaultNormal, &reason);
        if (!reason.empty())
        {
            TF_WARN("%s", reason.c_str());
        }
        if (cornerNormals.empty())
        {
            return getInvalidPrimvar();
        }
        return getIndexedPrimvar(cornerNormals, UsdGeomTokens->faceVarying);
    }

    return getInvalidPrimvar();
}

Vec3fPrimvarData usdex::core::computeMeshNormals(UsdGeomMesh mesh, const TfToken& interpolation, const GfVec3f& fallback)
{
    // Early out if the mesh is invalid
    if (!mesh)
    {
        TF_RUNTIME_ERROR("Unable to compute normals due to invalid mesh");
        return getInvalidPrimvar();
    }

    VtIntArray faceVertexCounts;
    VtIntArray faceVertexIndices;
    VtVec3fArray points;
    mesh.GetFaceVertexCountsAttr().Get(&faceVertexCounts);
    mesh.GetFaceVertexIndicesAttr().Get(&faceVertexIndices);
    mesh.GetPointsAttr().Get(&points);

    Vec3fPrimvarData normals = computeMeshNormals(faceVertexCounts, faceVertexIndices, points, interpolation, fallback);

    // Define the normals primvar
    UsdGeomPrimvar primvar = UsdGeomPrimvarsAPI(mesh.GetPrim()).CreatePrimvar(UsdGeomTokens->normals, SdfValueTypeNames->Normal3fArray);
    if (!normals.setPrimvar(primvar))
    {
        TF_WARN("Failed to set normals primvar for UsdGeomMesh at \"%s\"", mesh.GetPrim().GetPath().GetAsString().c_str());
    }

    return normals;
}
