// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/MeshAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;


namespace usdex::core::bindings
{

void bindMeshAlgo(module& m)
{
    m.def(
        "definePolyMesh",
        overload_cast<
            UsdStagePtr,
            const SdfPath&,
            const VtIntArray&,
            const VtIntArray&,
            const VtVec3fArray&,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec2fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&definePolyMesh),
        arg("stage"),
        arg("path"),
        arg("faceVertexCounts"),
        arg("faceVertexIndices"),
        arg("points"),
        arg("normals") = nullptr,
        arg("uvs") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a basic polygon mesh on the stage.

            All interrelated attribute values will be authored, even if weaker matching opinions already exist.

            The following common primvars can optionally be authored at the same time.

                - Normals
                - Primary UV Set
                - Display Color
                - Display Opacity

            Parameters:
                - **stage** - The stage on which to define the mesh
                - **path** - The absolute prim path at which to define the mesh
                - **faceVertexCounts** - The number of vertices in each face of the mesh
                - **faceVertexIndices** - Indices of the positions from the ``points`` to use for each face vertex
                - **points** - Vertex positions for the mesh described points in local space
                - **normals** - Values to be authored for the normals primvar
                - **uvs** - Values to be authored for the uv primvar
                - **displayColor** - Value to be authored for the display color primvar
                - **displayOpacity** - Value to be authored for the display opacity primvar

            Returns:
                ``UsdGeom.Mesh`` schema wrapping the defined ``Usd.Prim``.

        )"
    );

    m.def(
        "definePolyMesh",
        overload_cast<
            UsdPrim,
            const std::string&,
            const VtIntArray&,
            const VtIntArray&,
            const VtVec3fArray&,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec2fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&definePolyMesh),
        arg("parent"),
        arg("name"),
        arg("faceVertexCounts"),
        arg("faceVertexIndices"),
        arg("points"),
        arg("normals") = nullptr,
        arg("uvs") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a basic polygon mesh on the stage.

            All interrelated attribute values will be authored, even if weaker matching opinions already exist.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the mesh
                - **name** - Name of the mesh
                - **faceVertexCounts** - The number of vertices in each face of the mesh
                - **faceVertexIndices** - Indices of the positions from the ``points`` to use for each face vertex
                - **points** - Vertex positions for the mesh described points in local space
                - **normals** - Values to be authored for the normals primvar
                - **uvs** - Values to be authored for the uv primvar
                - **displayColor** - Value to be authored for the display color primvar
                - **displayOpacity** - Value to be authored for the display opacity primvar

            Returns:
                ``UsdGeom.Mesh`` schema wrapping the defined ``Usd.Prim``.

        )"
    );

    m.def(
        "definePolyMesh",
        overload_cast<
            UsdPrim,
            const VtIntArray&,
            const VtIntArray&,
            const VtVec3fArray&,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec2fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&definePolyMesh),
        arg("prim"),
        arg("faceVertexCounts"),
        arg("faceVertexIndices"),
        arg("points"),
        arg("normals") = nullptr,
        arg("uvs") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a basic polygon mesh on the stage.

            All interrelated attribute values will be authored, even if weaker matching opinions already exist.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Existing prim to convert to a mesh
                - **faceVertexCounts** - The number of vertices in each face of the mesh
                - **faceVertexIndices** - Indices of the positions from the ``points`` to use for each face vertex
                - **points** - Vertex positions for the mesh described points in local space
                - **normals** - Values to be authored for the normals primvar
                - **uvs** - Values to be authored for the uv primvar
                - **displayColor** - Value to be authored for the display color primvar
                - **displayOpacity** - Value to be authored for the display opacity primvar

            Returns:
                ``UsdGeom.Mesh`` schema wrapping the defined ``Usd.Prim``.

        )"
    );

    m.def(
        "computeMeshNormals",
        overload_cast<const VtIntArray&, const VtIntArray&, const VtVec3fArray&, const TfToken&, const GfVec3f&>(&computeMeshNormals),
        arg("faceVertexCounts"),
        arg("faceVertexIndices"),
        arg("points"),
        arg("interpolation") = UsdGeomTokens->uniform,
        arg("fallback") = GfVec3f(0.0f, 0.0f, 1.0f),
        R"(
            Computes mesh normals for a given mesh topology.

            This function computes normals for mesh geometry using vector-area approach for face normals
            and area-weighted averaging for vertex normals. The computation supports uniform, vertex, and
            faceVarying interpolations to match USD's primvar interpolation types. FaceVarying normals are a simplified
            approach that assigns the same face normal to all corners of each face.

            Normal computation assumes right-handed mesh orientation. The winding order of the data should be reversed in advance if that is not the case.

            Degenerate faces (with zero area) and vertices with no contributing faces are assigned the fallback normal.

            Note:
                This function is designed primarily to resolve USD validation issues for meshes
                that lack normals data. For production-quality rendering with sharp edges or complex
                shading requirements, consider using specialized mesh processing libraries that provide
                full edge connectivity analysis and advanced normal computation algorithms.

            Args:
                - **faceVertexCounts** - The number of vertices in each face of the mesh
                - **faceVertexIndices** - Indices of the positions from the ``points`` to use for each face vertex
                - **points** - Vertex positions for the mesh described in local space
                - **interpolation** - The desired interpolation type for the computed normals
                - **fallback** - The fallback normal to use for degenerate faces and vertices with no contributing faces

            Returns:
                Vec3fPrimvarData containing the computed normals, or an invalid one if computation fails.

        )"
    );

    m.def(
        "computeMeshNormals",
        overload_cast<UsdGeomMesh, const TfToken&, const GfVec3f&>(&computeMeshNormals),
        arg("mesh"),
        arg("interpolation") = UsdGeomTokens->uniform,
        arg("fallback") = GfVec3f(0.0f, 0.0f, 1.0f),
        R"(
            Computes mesh normals and updates the mesh with the computed normals.

            This is an overloaded member function, provided for convenience.

            Parameters:
                - **mesh** - Mesh prim to compute the normals for.
                - **interpolation** - The desired interpolation type for the computed normals
                - **fallback** - The fallback normal to use for degenerate faces and vertices with no contributing faces

            Returns:
                Vec3fPrimvarData containing the computed normals, or an invalid one if computation fails.
        )"
    );

    m.def(
        "definePartitionedSubsets",
        &definePartitionedSubsets,
        arg("prim"),
        arg("names"),
        arg("indices"),
        arg("elementType") = UsdGeomTokens->face,
        arg("familyName") = UsdShadeTokens->materialBind,
        R"(
            Fully partitions a geometry prim into multiple disjoint subsets.

            Every element of the geometry must appear in exactly one subset in this family,
            with no element appearing in more than one subset, and no element left unassigned.

            The prim must be a geometry that supports subsets (e.g. ``UsdGeom.Mesh`` from ``usdex.core.definePolyMesh``).
            Use ``usdex.core.bindMaterial`` to bind materials to each subset.

            Args:
                mesh: The mesh prim to add the subsets to
                names: The names of the subsets (length must equal len(indices))
                indices: Per-subset element indices; list of index arrays. len(indices) is the number of subsets,
                    indices[i] is the index list for subset i.
                elementType: The element type of the subsets. Valid values are ``UsdGeom.Tokens.Face``, ``UsdGeom.Tokens.Edge``, and ``UsdGeom.Tokens.Point`` (default: ``UsdGeom.Tokens.Face``)
                familyName: The family name of the subsets (default: ``UsdShade.Tokens.MaterialBind``)

            Returns:
                The list of subsets created. Empty list on failure.
        )"
    );

    m.def(
        "defineNonOverlappingSubsets",
        &defineNonOverlappingSubsets,
        arg("prim"),
        arg("names"),
        arg("indices"),
        arg("elementType") = UsdGeomTokens->face,
        arg("familyName") = UsdShadeTokens->materialBind,
        R"(
            Partially partitions a geometry prim into multiple disjoint subsets.

            An element may appear in at most one subset in this family, and at most once within that subset.
            The union of all subsets need not cover the whole geometry (some elements may be unassigned).
            Use when subsets must not overlap but need not cover the entire geometry.

            The prim must be a geometry that supports subsets (e.g. ``UsdGeom.Mesh`` from ``usdex.core.definePolyMesh``).
            Use ``usdex.core.bindMaterial`` to bind materials to each subset.

            Args:
                mesh: The mesh prim to add the subsets to
                names: The names of the subsets (length must equal len(indices))
                indices: Per-subset element indices; list of index arrays. len(indices) is the number of subsets,
                    indices[i] is the index list for subset i.
                elementType: The element type of the subsets. Valid values are ``UsdGeom.Tokens.Face``, ``UsdGeom.Tokens.Edge``, and ``UsdGeom.Tokens.Point`` (default: ``UsdGeom.Tokens.Face``)
                familyName: The family name of the subsets (default: ``UsdShade.Tokens.MaterialBind``)

            Returns:
                The list of subsets created. Empty list on failure.
        )"
    );

    m.def(
        "defineUnrestrictedSubsets",
        &defineUnrestrictedSubsets,
        arg("prim"),
        arg("names"),
        arg("indices"),
        arg("elementType") = UsdGeomTokens->face,
        arg("familyName") = UsdShadeTokens->materialBind,
        R"(
            Partially partitions a geometry prim into multiple, possibly overlapping, subsets.

            No restrictions: elements may appear in multiple subsets, and the union of all subsets
            need not represent the whole geometry. Use when overlapping or partial subsets are needed.

            The prim must be a geometry that supports subsets (e.g. ``UsdGeom.Mesh`` from ``usdex.core.definePolyMesh``).
            Use ``usdex.core.bindMaterial`` to bind materials to each subset.

            Args:
                mesh: The mesh prim to add the subsets to
                names: The names of the subsets (length must equal len(indices))
                indices: Per-subset element indices; list of index arrays. len(indices) is the number of subsets,
                    indices[i] is the index list for subset i.
                elementType: The element type of the subsets. Valid values are ``UsdGeom.Tokens.Face``, ``UsdGeom.Tokens.Edge``, and ``UsdGeom.Tokens.Point`` (default: ``UsdGeom.Tokens.Face``)
                familyName: The family name of the subsets (default: ``UsdShade.Tokens.MaterialBind``)

            Returns:
                The list of subsets created. Empty list on failure.
        )"
    );
}

} // namespace usdex::core::bindings
