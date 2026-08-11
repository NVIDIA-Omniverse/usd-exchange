// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/core/PointsAlgo.h
//! @brief Utility functions to create `UsdGeomPoint` Prims.

#include "Api.h"
#include "PrimvarData.h"

#include <pxr/base/gf/vec2f.h>
#include <pxr/base/gf/vec3f.h>
#include <pxr/base/vt/array.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/points.h>
#include <pxr/usd/usdGeom/tokens.h>

#include <optional>

namespace usdex::core
{

//! @defgroup points Point Cloud / Particle Prims
//!
//! Utility functions to create `UsdGeomPoint` prims.
//!
//! [UsdGeomPoints](https://openusd.org/release/api/class_usd_geom_points.html#details) prims are simple point clouds or particle fields.
//! Points generally receive a single shading sample each, which should take normals into account, if present.
//!
//! @{

//! Defines a `UsdGeomPoints` prim on the stage.
//!
//! Attribute values will be validated and in the case of invalid data the Points will not be defined. An invalid `UsdGeomPoints` object will
//! be returned in this case.
//!
//! Values will be authored for all attributes required to completely describe the Points, even if weaker matching opinions already exist.
//!
//! - Point Count
//! - Points
//! - Extent
//!
//! The "extent" of the Points will be computed and authored based on the `points` and `widths` provided.
//!
//! The following common primvars can optionally be authored at the same time using a `PrimvarData` to specify interpolation, data,
//! and optionally indices or elementSize.
//!
//! - Ids
//! - Widths
//! - Normals
//! - Display Color
//! - Display Opacity
//!
//! For both widths and normals, if they are provided, they are authored as `primvars:widths` and `primvars:normals`, so that indexing is possible
//! and to ensure that the value takes precedence in cases where both the non-primvar and primvar attributes are authored.
//!
//! @param stage The stage on which to define the points.
//! @param path The absolute prim path at which to define the points.
//! @param points Vertex positions for the points described in local space.
//! @param ids Values for the id specification for the points.
//! @param widths Values for the width specification for the points.
//! @param normals Values for the normals primvar for the points. Only Vertex normals are considered valid.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomPoints` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomPoints definePointCloud(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::VtVec3fArray& points,
    std::optional<const pxr::VtInt64Array> ids = std::nullopt,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! Defines a `UsdGeomPoints` prim on the stage.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the curves.
//! @param name Name of the curves.
//! @param points Vertex positions for the points described in local space.
//! @param ids Values for the id specification for the points.
//! @param widths Values for the width specification for the points.
//! @param normals Values for the normals primvar for the points. Only Vertex normals are considered valid.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomPoints` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomPoints definePointCloud(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::VtVec3fArray& points,
    std::optional<const pxr::VtInt64Array> ids = std::nullopt,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! Defines a point cloud using the `UsdGeomPoints` schema.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the point cloud on. The prim's type will be set to `UsdGeomPoints`.
//! @param points Positions of the points.
//! @param widths Values for the width specification for the points.
//! @param normals Values for the normals primvar for the points.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomPoints` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomPoints definePointCloud(
    pxr::UsdPrim prim,
    const pxr::VtVec3fArray& points,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! @}

} // namespace usdex::core
