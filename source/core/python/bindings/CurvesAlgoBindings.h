// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/CurvesAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

namespace usdex::core::bindings
{

void bindCurvesAlgo(module& m)
{
    m.def(
        "defineLinearBasisCurves",
        overload_cast<
            UsdStagePtr,
            const SdfPath&,
            const VtIntArray&,
            const VtVec3fArray&,
            const TfToken&,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&defineLinearBasisCurves),
        arg("stage"),
        arg("path"),
        arg("curveVertexCounts"),
        arg("points"),
        arg("wrap") = UsdGeomTokens->nonperiodic.GetString(),
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a batched Linear ``UsdGeom.BasisCurves`` prim on the stage.

            Attribute values will be validated and in the case of invalid data the Curves will not be defined. An invalid ``UsdGeom.BasisCurves``
            object will be returned in this case.

            Values will be authored for all attributes required to completely describe the Curves, even if weaker matching opinions already exist.

                - Curve Vertex Counts
                - Points
                - Type
                - Wrap
                - Extent

            The "extent" of the Curves will be computed and authored based on the ``points`` and ``widths`` provided.

            The following common primvars can optionally be authored at the same time using a ``PrimvarData`` to specify interpolation, data,
            and optionally indices or elementSize.

                - Widths
                - Normals
                - Display Color
                - Display Opacity

            For both widths and normals, if they are provided, they are authored as ``primvars:widths`` and ``primvars:normals``, so that indexing is
            possible and to ensure that the value takes precedence in cases where both the non-primvar and primvar attributes are authored.

            Parameters:
                - **stage** The stage on which to define the curves.
                - **path** The absolute prim path at which to define the curves.
                - **curveVertexCounts** The number of vertices in each independent curve. The length of this array determines the number of curves.
                - **points** Vertex/CV positions for the curves described in local space.
                - **wrap** Determines how the start and end points of the curve behave. Accepted values for linear curves are
                    ``UsdGeom.Tokens.nonperiodic`` and ``UsdGeom.Tokens.periodic``.
                - **widths** Values for the width specification for the curves.
                - **normals** Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
                - **displayColor** Values to be authored for the display color primvar.
                - **displayOpacity** Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.BasisCurves`` schema wrapping the defined ``Usd.Prim``
        )"
    );

    m.def(
        "defineLinearBasisCurves",
        overload_cast<
            UsdPrim,
            const std::string&,
            const VtIntArray&,
            const VtVec3fArray&,
            const TfToken&,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&defineLinearBasisCurves),
        arg("parent"),
        arg("name"),
        arg("curveVertexCounts"),
        arg("points"),
        arg("wrap") = UsdGeomTokens->nonperiodic.GetString(),
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a batched Linear ``UsdGeom.BasisCurves`` prim on the stage.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** Prim below which to define the curves
                - **name** Name of the curves
                - **curveVertexCounts** The number of vertices in each independent curve. The length of this array determines the number of curves.
                - **points** Vertex/CV positions for the curves described in local space.
                - **wrap** Determines how the start and end points of the curve behave. Accepted values for linear curves are
                    ``UsdGeom.Tokens.nonperiodic`` and ``UsdGeom.Tokens.periodic``.
                - **widths** Values for the width specification for the curves.
                - **normals** Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
                - **displayColor** Values to be authored for the display color primvar.
                - **displayOpacity** Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.BasisCurves`` schema wrapping the defined ``Usd.Prim``
        )"
    );

    m.def(
        "defineLinearBasisCurves",
        overload_cast<
            UsdPrim,
            const VtIntArray&,
            const VtVec3fArray&,
            const TfToken&,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&defineLinearBasisCurves),
        arg("prim"),
        arg("curveVertexCounts"),
        arg("points"),
        arg("wrap") = UsdGeomTokens->nonperiodic.GetString(),
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a batched Linear ``UsdGeom.BasisCurves`` prim on the stage.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** The stage on which to define the curves.
                - **name** The absolute prim path at which to define the curves.
                - **curveVertexCounts** The number of vertices in each independent curve. The length of this array determines the number of curves.
                - **points** Vertex/CV positions for the curves described in local space.
                - **wrap** Determines how the start and end points of the curve behave. Accepted values for linear curves are
                    ``UsdGeom.Tokens.nonperiodic`` and ``UsdGeom.Tokens.periodic``.
                - **widths** Values for the width specification for the curves.
                - **normals** Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
                - **displayColor** Values to be authored for the display color primvar.
                - **displayOpacity** Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.BasisCurves`` schema wrapping the defined ``Usd.Prim``
        )"
    );

    m.def(
        "defineCubicBasisCurves",
        overload_cast<
            UsdStagePtr,
            const SdfPath&,
            const VtIntArray&,
            const VtVec3fArray&,
            const TfToken&,
            const TfToken&,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&defineCubicBasisCurves),
        arg("stage"),
        arg("path"),
        arg("curveVertexCounts"),
        arg("points"),
        arg("basis") = UsdGeomTokens->bezier.GetString(),
        arg("wrap") = UsdGeomTokens->nonperiodic.GetString(),
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a batched Cubic ``UsdGeom.BasisCurves`` prim on the stage.

            Attribute values will be validated and in the case of invalid data the Curves will not be defined. An invalid ``UsdGeom.BasisCurves``
            object will be returned in this case.

            Values will be authored for all attributes required to completely describe the Curves, even if weaker matching opinions already exist.

                - Curve Vertex Counts
                - Points
                - Type
                - Basis
                - Wrap
                - Extent

            The "extent" of the Curves will be computed and authored based on the ``points`` and ``widths`` provided.

            The following common primvars can optionally be authored at the same time using a ``PrimvarData`` to specify interpolation, data,
            and optionally indices or elementSize.

                - Widths
                - Normals
                - Display Color
                - Display Opacity

            For both widths and normals, if they are provided, they are authored as ``primvars:widths`` and ``primvars:normals``, so that indexing is
            possible and to ensure that the value takes precedence in cases where both the non-primvar and primvar attributes are authored.

            Parameters:
                - **stage** The stage on which to define the curves.
                - **path** The absolute prim path at which to define the curves.
                - **curveVertexCounts** The number of vertices in each independent curve. The length of this array determines the number of curves.
                - **points** Vertex/CV positions for the curves described in local space.
                - **basis** The basis specifies the vstep and matrix used for cubic interpolation. Accepted values for cubic curves are
                    ``UsdGeom.Tokens.bezier``, ``UsdGeom.Tokens.bspline``, or ``UsdGeom.Tokens.catmullRom``.
                - **wrap** Determines how the start and end points of the curve behave. Accepted values are ``UsdGeom.Tokens.nonperiodic``,
                    ``UsdGeom.Tokens.periodic``, and ``UsdGeom.Tokens.pinned`` (bspline and catmullRom only).
                - **widths** Values for the width specification for the curves.
                - **normals** Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
                - **displayColor** Values to be authored for the display color primvar.
                - **displayOpacity** Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.BasisCurves`` schema wrapping the defined ``Usd.Prim``
        )"
    );

    m.def(
        "defineCubicBasisCurves",
        overload_cast<
            UsdPrim,
            const std::string&,
            const VtIntArray&,
            const VtVec3fArray&,
            const TfToken&,
            const TfToken&,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&defineCubicBasisCurves),
        arg("parent"),
        arg("name"),
        arg("curveVertexCounts"),
        arg("points"),
        arg("basis") = UsdGeomTokens->bezier.GetString(),
        arg("wrap") = UsdGeomTokens->nonperiodic.GetString(),
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a batched Cubic ``UsdGeom.BasisCurves`` prim on the stage.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** Prim below which to define the curves
                - **name** Name of the curves
                - **curveVertexCounts** The number of vertices in each independent curve. The length of this array determines the number of curves.
                - **points** Vertex/CV positions for the curves described in local space.
                - **basis** The basis specifies the vstep and matrix used for cubic interpolation. Accepted values for cubic curves are
                    ``UsdGeom.Tokens.bezier``, ``UsdGeom.Tokens.bspline``, ``UsdGeom.Tokens.catmullRom``.
                - **wrap** Determines how the start and end points of the curve behave. Accepted values are ``UsdGeom.Tokens.nonperiodic``,
                    ``UsdGeom.Tokens.periodic``, and ``UsdGeom.Tokens.pinned`` (bspline and catmullRom only).
                - **widths** Values for the width specification for the curves.
                - **normals** Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
                - **displayColor** Values to be authored for the display color primvar.
                - **displayOpacity** Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.BasisCurves`` schema wrapping the defined ``Usd.Prim``
        )"
    );

    m.def(
        "defineCubicBasisCurves",
        overload_cast<
            UsdPrim,
            const VtIntArray&,
            const VtVec3fArray&,
            const TfToken&,
            const TfToken&,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&defineCubicBasisCurves),
        arg("prim"),
        arg("curveVertexCounts"),
        arg("points"),
        arg("basis") = UsdGeomTokens->bezier.GetString(),
        arg("wrap") = UsdGeomTokens->nonperiodic.GetString(),
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a batched Cubic ``UsdGeom.BasisCurves`` prim on the stage.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** The stage on which to define the curves.
                - **name** The absolute prim path at which to define the curves.
                - **curveVertexCounts** The number of vertices in each independent curve. The length of this array determines the number of curves.
                - **points** Vertex/CV positions for the curves described in local space.
                - **basis** The basis specifies the vstep and matrix used for cubic interpolation. Accepted values for cubic curves are
                    ``UsdGeom.Tokens.bezier``, ``UsdGeom.Tokens.bspline``, or ``UsdGeom.Tokens.catmullRom``.
                - **wrap** Determines how the start and end points of the curve behave. Accepted values are ``UsdGeom.Tokens.nonperiodic``,
                    ``UsdGeom.Tokens.periodic``, and ``UsdGeom.Tokens.pinned`` (bspline and catmullRom only).
                - **widths** Values for the width specification for the curves.
                - **normals** Values for the normals primvar for the curves. If authored, the curves are considered oriented ribbons rather than tubes.
                - **displayColor** Values to be authored for the display color primvar.
                - **displayOpacity** Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.BasisCurves`` schema wrapping the defined ``Usd.Prim``
        )"
    );
}

} // namespace usdex::core::bindings
