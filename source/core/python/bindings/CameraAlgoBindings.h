// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "usdex/core/CameraAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

namespace usdex::core::bindings
{

void bindCameraAlgo(module& m)
{
    m.def(
        "defineCamera",
        overload_cast<UsdStagePtr, const SdfPath&, const GfCamera&>(&defineCamera),
        arg("stage"),
        arg("path"),
        arg("cameraData"),
        R"(
            Defines a basic 3d camera on the stage.

            Note that ``Gf.Camera`` is a simplified form of 3d camera data that does not account for time-sampled data, shutter window,
            stereo role, or exposure. If you need to author those properties, do so after defining the ``UsdGeom.Camera``.

            An invalid UsdGeomCamera will be returned if camera attributes could not be authored successfully.

            Parameters:
                - **stage** - The stage on which to define the camera
                - **path** - The absolute prim path at which to define the camera
                - **cameraData** - The camera data to set, including the world space transform matrix

            Returns:
                A ``UsdGeom.Camera`` schema wrapping the defined ``Usd.Prim``.

        )"
    );

    m.def(
        "defineCamera",
        overload_cast<UsdPrim, const std::string&, const GfCamera&>(&defineCamera),
        arg("parent"),
        arg("name"),
        arg("cameraData"),
        R"(
            Defines a basic 3d camera on the stage.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the camera
                - **name** - Name of the camera
                - **cameraData** - The camera data to set, including the world space transform matrix

            Returns:
                A ``UsdGeom.Camera`` schema wrapping the defined ``Usd.Prim``.

        )"
    );

    m.def(
        "defineCamera",
        overload_cast<UsdPrim, const GfCamera&>(&defineCamera),
        arg("prim"),
        arg("cameraData"),
        R"(
            Defines a basic 3d camera from an existing prim.

            This converts an existing prim to a Camera type, preserving any existing transform data.

            Parameters:
                - **prim** - The existing prim to convert to a camera
                - **cameraData** - The camera data to set, including the world space transform matrix

            Returns:
                A ``UsdGeom.Camera`` schema wrapping the converted ``Usd.Prim``.

        )"
    );
}

} // namespace usdex::core::bindings
