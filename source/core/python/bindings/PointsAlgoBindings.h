// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/PointsAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

namespace usdex::core::bindings
{

void bindPointsAlgo(module& m)
{
    m.def(
        "definePointCloud",
        overload_cast<
            UsdStagePtr,
            const SdfPath&,
            const VtVec3fArray&,
            std::optional<const VtInt64Array>,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&definePointCloud),
        arg("stage"),
        arg("path"),
        arg("points"),
        arg("ids") = nullptr,
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a ``UsdGeom.Points`` prim on the stage.

            Attribute values will be validated and in the case of invalid data the Points will not be defined. An invalid ``UsdGeom.Points``
            object will be returned in this case.

            Values will be authored for all attributes required to completely describe the Points, even if weaker matching opinions already exist.

                - Point Count
                - Points
                - Extent

            The "extent" of the Points will be computed and authored based on the ``points`` and ``widths`` provided.

            The following common primvars can optionally be authored at the same time using a ``PrimvarData`` to specify interpolation, data,
            and optionally indices or elementSize.

                - Ids
                - Widths
                - Normals
                - Display Color
                - Display Opacity

            For both widths and normals, if they are provided, they are authored as ``primvars:widths`` and ``primvars:normals``, so that indexing is
            possible and to ensure that the value takes precedence in cases where both the non-primvar and primvar attributes are authored.

            Parameters:
                - **stage** The stage on which to define the points.
                - **path** The absolute prim path at which to define the points.
                - **points** Vertex/CV positions for the points described in local space.
                - **ids** Values for the id specification for the points.
                - **widths** Values for the width specification for the points.
                - **normals** Values for the normals primvar for the points. Only Vertex normals are considered valid.
                - **displayColor** Values to be authored for the display color primvar.
                - **displayOpacity** Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.Points`` schema wrapping the defined ``Usd.Prim``
        )"
    );

    m.def(
        "definePointCloud",
        overload_cast<
            UsdPrim,
            const std::string&,
            const VtVec3fArray&,
            std::optional<const VtInt64Array>,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&definePointCloud),
        arg("parent"),
        arg("name"),
        arg("points"),
        arg("ids") = nullptr,
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a ``UsdGeom.Points`` prim on the stage.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** Prim below which to define the points.
                - **name** Name of the points prim.
                - **points** Vertex/CV positions for the points described in local space.
                - **ids** Values for the id specification for the points.
                - **widths** Values for the width specification for the points.
                - **normals** Values for the normals primvar for the points. Only Vertex normals are considered valid.
                - **displayColor** Values to be authored for the display color primvar.
                - **displayOpacity** Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.Points`` schema wrapping the defined ``Usd.Prim``
        )"
    );

    m.def(
        "definePointCloud",
        overload_cast<
            UsdPrim,
            const VtVec3fArray&,
            std::optional<const FloatPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const Vec3fPrimvarData>,
            std::optional<const FloatPrimvarData>>(&definePointCloud),
        arg("prim"),
        arg("points"),
        arg("widths") = nullptr,
        arg("normals") = nullptr,
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a point cloud using the ``UsdGeom.Points`` schema.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the point cloud on. The prim's type will be set to ``UsdGeom.Points``.
                - **points** - Positions of the points.
                - **widths** - Values for the width specification for the points.
                - **normals** - Values for the normals primvar for the points.
                - **displayColor** - Values to be authored for the display color primvar.
                - **displayOpacity** - Values to be authored for the display opacity primvar.

            Returns:
                ``UsdGeom.Points`` schema wrapping the defined ``Usd.Prim``
        )"
    );
}

} // namespace usdex::core::bindings
