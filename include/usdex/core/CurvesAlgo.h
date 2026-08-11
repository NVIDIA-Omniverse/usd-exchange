// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/core/CurvesAlgo.h
//! @brief Utility functions to create geometric Line and Curve descriptions.

#include "Api.h"
#include "PrimvarData.h"

#include <pxr/base/gf/vec2f.h>
#include <pxr/base/gf/vec3f.h>
#include <pxr/base/vt/array.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/basisCurves.h>
#include <pxr/usd/usdGeom/tokens.h>

#include <optional>

namespace usdex::core
{

//! @defgroup curves Line and Curve Prims
//!
//! Utility functions to create geometric Line and Curve descriptions.
//!
//! [UsdGeomBasisCurves](https://openusd.org/release/api/class_usd_geom_basis_curves.html#details) prims can represent multiple distinct,
//! potentially disconnected curves. All curves within the prim must respect the same basis and wrap values. For example, one prim could contain
//! 1 million non-periodic Bezier curves, but it cannot contain a mix of Bezier & bSpline curves, nor can it contain a mix of periodic, non-periodic,
//! and pinned curves.
//!
//! Linear curves are also represented by `UsdGeomBasisCurves`; in this case the type attribute is "linear" and the basis attribute can be ignored.
//!
//! Normals are another a special case for `UsdGeomBasisCurves`; authoring normals will result in oriented ribbons rather than smooth tubes.
//!
//! @{

//! Defines a batched Linear `UsdGeomBasisCurves` prim on the stage.
//!
//! Attribute values will be validated and in the case of invalid data the Curves will not be defined. An invalid `UsdGeomBasisCurves` object will
//! be returned in this case.
//!
//! Values will be authored for all attributes required to completely describe the Curves, even if weaker matching opinions already exist.
//!
//! - Curve Vertex Counts
//! - Points
//! - Type
//! - Wrap
//! - Extent
//!
//! The "extent" of the Curves will be computed and authored based on the `points` and `widths` provided.
//!
//! The following common primvars can optionally be authored at the same time using a `PrimvarData` to specify interpolation, data,
//! and optionally indices or elementSize.
//!
//! - Widths
//! - Normals
//! - Display Color
//! - Display Opacity
//!
//! For both widths and normals, if they are provided, they are authored as `primvars:widths` and `primvars:normals`, so that indexing is possible
//! and to ensure that the value takes precedence in cases where both the non-primvar and primvar attributes are authored.
//!
//! @param stage The stage on which to define the curves.
//! @param path The absolute prim path at which to define the curves.
//! @param curveVertexCounts The number of vertices in each independent curve. The length of this array determines the number of curves.
//! @param points Vertex/CV positions for the curves described in local space.
//! @param wrap Determines how the start and end points of the curve behave. Accepted values for linear curves are `UsdGeomTokens->nonperiodic` and
//!     `UsdGeomTokens->periodic`.
//! @param widths Values for the width specification for the curves.
//! @param normals Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomBasisCurves` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomBasisCurves defineLinearBasisCurves(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::VtIntArray& curveVertexCounts,
    const pxr::VtVec3fArray& points,
    const pxr::TfToken& wrap = pxr::UsdGeomTokens->nonperiodic,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! Defines a batched Linear `UsdGeomBasisCurves` prim on the stage.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the curves.
//! @param name Name of the curves.
//! @param curveVertexCounts The number of vertices in each independent curve. The length of this array determines the number of curves.
//! @param points Vertex/CV positions for the curves described in local space.
//! @param wrap Determines how the start and end points of the curve behave. Accepted values for linear curves are `UsdGeomTokens->nonperiodic` and
//!     `UsdGeomTokens->periodic`.
//! @param widths Values for the width specification for the curves.
//! @param normals Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomBasisCurves` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomBasisCurves defineLinearBasisCurves(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::VtIntArray& curveVertexCounts,
    const pxr::VtVec3fArray& points,
    const pxr::TfToken& wrap = pxr::UsdGeomTokens->nonperiodic,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! Defines a batched Linear `UsdGeomBasisCurves` prim on the stage.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the curves on. The prim's type will be set to `UsdGeomBasisCurves`.
//! @param curveVertexCounts The number of vertices in each independent curve. The length of this array determines the number of curves.
//! @param points Vertex/CV positions for the curves described in local space.
//! @param wrap Determines how the start and end points of the curve behave. Accepted values for linear curves are `UsdGeomTokens->nonperiodic` and
//!     `UsdGeomTokens->periodic`.
//! @param widths Values for the width specification for the curves.
//! @param normals Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomBasisCurves` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomBasisCurves defineLinearBasisCurves(
    pxr::UsdPrim prim,
    const pxr::VtIntArray& curveVertexCounts,
    const pxr::VtVec3fArray& points,
    const pxr::TfToken& wrap = pxr::UsdGeomTokens->nonperiodic,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! Defines a batched Cubic `UsdGeomBasisCurves` prim on the stage.
//!
//! Attribute values will be validated and in the case of invalid data the Curves will not be defined. An invalid `UsdGeomBasisCurves` object will
//! be returned in this case.
//!
//! Values will be authored for all attributes required to completely describe the Curves, even if weaker matching opinions already exist.
//!
//! - Curve Vertex Counts
//! - Points
//! - Type
//! - Basis
//! - Wrap
//! - Extent
//!
//! The "extent" of the Curves will be computed and authored based on the `points` and `widths` provided.
//!
//! The following common primvars can optionally be authored at the same time using a `PrimvarData` to specify interpolation, data,
//! and optionally indices or elementSize.
//!
//! - Widths
//! - Normals
//! - Display Color
//! - Display Opacity
//!
//! For both widths and normals, if they are provided, they are authored as `primvars:widths` and `primvars:normals`, so that indexing is possible
//! and to ensure that the value takes precedence in cases where both the non-primvar and primvar attributes are authored.
//!
//! @param stage The stage on which to define the curves.
//! @param path The absolute prim path at which to define the curves.
//! @param curveVertexCounts The number of vertices in each independent curve. The length of this array determines the number of curves.
//! @param points Vertex/CV positions for the curves described in local space.
//! @param basis The basis specifies the vstep and matrix used for cubic interpolation. Accepted values for cubic curves are `UsdGeomTokens->bezier`,
//!     `UsdGeomTokens->bspline`, or `UsdGeomTokens->catmullRom`.
//! @param wrap Determines how the start and end points of the curve behave. Accepted values are `UsdGeomTokens->nonperiodic`,
//!     `UsdGeomTokens->periodic`, and `UsdGeomTokens->pinned` (bspline and catmullRom only).
//! @param widths Values for the width specification for the curves.
//! @param normals Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomBasisCurves` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomBasisCurves defineCubicBasisCurves(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::VtIntArray& curveVertexCounts,
    const pxr::VtVec3fArray& points,
    const pxr::TfToken& basis = pxr::UsdGeomTokens->bezier,
    const pxr::TfToken& wrap = pxr::UsdGeomTokens->nonperiodic,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! Defines a batched Cubic `UsdGeomBasisCurves` prim on the stage.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the curves.
//! @param name Name of the curves.
//! @param curveVertexCounts The number of vertices in each independent curve. The length of this array determines the number of curves.
//! @param points Vertex/CV positions for the curves described in local space.
//! @param basis The basis specifies the vstep and matrix used for cubic interpolation. Accepted values for cubic curves are `UsdGeomTokens->bezier`,
//!     `UsdGeomTokens->bspline`, `UsdGeomTokens->catmullRom`.
//! @param wrap Determines how the start and end points of the curve behave. Accepted values are `UsdGeomTokens->nonperiodic`,
//!     `UsdGeomTokens->periodic`, and `UsdGeomTokens->pinned` (bspline and catmullRom only).
//! @param widths Values for the width specification for the curves.
//! @param normals Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomBasisCurves` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomBasisCurves defineCubicBasisCurves(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::VtIntArray& curveVertexCounts,
    const pxr::VtVec3fArray& points,
    const pxr::TfToken& basis = pxr::UsdGeomTokens->bezier,
    const pxr::TfToken& wrap = pxr::UsdGeomTokens->nonperiodic,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! Defines a batched Cubic `UsdGeomBasisCurves` prim on the stage.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the curves on. The prim's type will be set to `UsdGeomBasisCurves`.
//! @param curveVertexCounts The number of vertices in each independent curve. The length of this array determines the number of curves.
//! @param points Vertex/CV positions for the curves described in local space.
//! @param basis The basis specifies the vstep and matrix used for cubic interpolation. Accepted values for cubic curves are `UsdGeomTokens->bezier`,
//!     `UsdGeomTokens->bspline`, `UsdGeomTokens->catmullRom`.
//! @param wrap Determines how the start and end points of the curve behave. Accepted values are `UsdGeomTokens->nonperiodic`,
//!     `UsdGeomTokens->periodic`, and `UsdGeomTokens->pinned` (bspline and catmullRom only).
//! @param widths Values for the width specification for the curves.
//! @param normals Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
//! @param displayColor Values to be authored for the display color primvar.
//! @param displayOpacity Values to be authored for the display opacity primvar.
//! @returns `UsdGeomBasisCurves` schema wrapping the defined `UsdPrim`
USDEX_API pxr::UsdGeomBasisCurves defineCubicBasisCurves(
    pxr::UsdPrim prim,
    const pxr::VtIntArray& curveVertexCounts,
    const pxr::VtVec3fArray& points,
    const pxr::TfToken& basis = pxr::UsdGeomTokens->bezier,
    const pxr::TfToken& wrap = pxr::UsdGeomTokens->nonperiodic,
    std::optional<const FloatPrimvarData> widths = std::nullopt,
    std::optional<const Vec3fPrimvarData> normals = std::nullopt,
    std::optional<const Vec3fPrimvarData> displayColor = std::nullopt,
    std::optional<const FloatPrimvarData> displayOpacity = std::nullopt
);

//! @}

} // namespace usdex::core
