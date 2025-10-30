// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/XformAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>


using namespace usdex::core;
using namespace pybind11;

using namespace pxr;

namespace usdex::core::bindings
{

void bindXformAlgo(module& m)
{
    pybind11::enum_<RotationOrder>(m, "RotationOrder", "Enumerates the rotation order of the 3-angle Euler rotation.")
        .value("eXyz", RotationOrder::eXyz)
        .value("eXzy", RotationOrder::eXzy)
        .value("eYxz", RotationOrder::eYxz)
        .value("eYzx", RotationOrder::eYzx)
        .value("eZxy", RotationOrder::eZxy)
        .value("eZyx", RotationOrder::eZyx);

    m.def(
        "setLocalTransform",
        overload_cast<UsdPrim, const GfTransform&, UsdTimeCode>(&setLocalTransform),
        arg("prim"),
        arg("transform"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set the local transform of a prim.

            Parameters:
                - **prim** - The prim to set local transform on.
                - **transform** - The transform value to set.
                - **time** - Time at which to write the value.

            Returns:
                A bool indicating if the local transform was set.

        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "setLocalTransform",
        overload_cast<UsdPrim, const GfMatrix4d&, UsdTimeCode>(&setLocalTransform),
        arg("prim"),
        arg("matrix"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set the local transform of a prim from a 4x4 matrix.

            Parameters:
                - **prim** - The prim to set local transform on.
                - **matrix** - The matrix value to set.
                - **time** - Time at which to write the value.

            Returns:
                A bool indicating if the local transform was set.

        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "setLocalTransform",
        overload_cast<UsdPrim, const GfVec3d&, const GfVec3d&, const GfVec3f&, const RotationOrder, const GfVec3f&, UsdTimeCode>(&setLocalTransform),
        arg("prim"),
        arg("translation"),
        arg("pivot"),
        arg("rotation"),
        arg("rotationOrder"),
        arg("scale"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set the local transform of a prim from common transform components.

            Parameters:
                - **prim** - The prim to set local transform on.
                - **translation** - The translation value to set.
                - **pivot** - The pivot position value to set.
                - **rotation** - The rotation value to set in degrees.
                - **rotationOrder** - The rotation order of the rotation value.
                - **scale** - The scale value to set.
                - **time** - Time at which to write the value.

            Returns:
                A bool indicating if the local transform was set.

        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "setLocalTransform",
        overload_cast<UsdPrim, const GfVec3d&, const GfQuatf&, const GfVec3f&, UsdTimeCode>(&setLocalTransform),
        arg("prim"),
        arg("translation"),
        arg("orientation"),
        arg("scale") = GfVec3f(1.0f),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set the local transform of a prim from common transform components using a quaternion for orientation.

            Parameters:
                - **prim** - The prim to set local transform on.
                - **translation** - The translation value to set.
                - **orientation** - The orientation value to set as a quaternion.
                - **scale** - The scale value to set - defaults to (1.0, 1.0, 1.0).
                - **time** - Time at which to write the value.

            Returns:
                A bool indicating if the local transform was set.

        )",
        call_guard<gil_scoped_acquire>()
    );

    m.def(
        "getLocalTransform",
        overload_cast<const UsdPrim&, UsdTimeCode>(&getLocalTransform),
        arg("prim"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Get the local transform of a prim at a given time.

            Parameters:
                - **prim** - The prim to get local transform from.
                - **time** - Time at which to query the value.

            Returns:
                Transform value as a transform.

        )"
    );

    m.def(
        "getLocalTransformMatrix",
        overload_cast<const UsdPrim&, UsdTimeCode>(&getLocalTransformMatrix),
        arg("prim"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Get the local transform of a prim at a given time in the form of a 4x4 matrix.

            Parameters:
                - **prim** - The prim to get local transform from.
                - **time** - Time at which to query the value.

            Returns:
                Transform value as a 4x4 matrix.

        )"
    );

    m.def(
        "getLocalTransformComponents",
        [](const UsdPrim& prim, UsdTimeCode time)
        {
            GfVec3d translation;
            GfVec3d pivot;
            GfVec3f rotation;
            RotationOrder rotationOrder;
            GfVec3f scale;
            getLocalTransformComponents(prim, translation, pivot, rotation, rotationOrder, scale, time);
            return make_tuple(translation, pivot, rotation, rotationOrder, scale);
        },
        arg("prim"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Get the local transform of a prim at a given time in the form of common transform components.

            Parameters:
                - **prim** - The prim to get local transform from.
                - **time** - Time at which to query the value.

            Returns:
                Transform value as a tuple of translation, pivot, rotation, rotation order, scale.

        )"
    );

    m.def(
        "getLocalTransformComponentsQuat",
        [](const UsdPrim& prim, UsdTimeCode time)
        {
            GfVec3d translation;
            GfVec3d pivot;
            GfQuatf orientation;
            GfVec3f scale;
            getLocalTransformComponentsQuat(prim, translation, pivot, orientation, scale, time);
            return make_tuple(translation, pivot, orientation, scale);
        },
        arg("prim"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Get the local transform of a prim at a given time in the form of common transform components with quaternion orientation.

            Parameters:
                - **prim** - The prim to get local transform from.
                - **time** - Time at which to query the value.

            Returns:
                Transform value as a tuple of translation, pivot, orientation (quaternion), scale.

        )"
    );

    m.def(
        "defineXform",
        overload_cast<UsdStagePtr, const SdfPath&, std::optional<const GfTransform>>(&defineXform),
        arg("stage"),
        arg("path"),
        arg("transform") = nullptr,
        R"(
            Defines an xform on the stage.

            Parameters:
                - **stage** - The stage on which to define the xform
                - **path** - The absolute prim path at which to define the xform
                - **transform** - Optional local transform to set

            Returns:
                UsdGeom.Xform schema wrapping the defined Usd.Prim. Returns an invalid schema on error.
        )"
    );

    m.def(
        "defineXform",
        overload_cast<UsdPrim, const std::string&, std::optional<const GfTransform>>(&defineXform),
        arg("parent"),
        arg("name"),
        arg("transform") = nullptr,
        R"(
            Defines an xform on the stage.

            Parameters:
                - **parent** - Prim below which to define the xform
                - **name** - Name of the xform
                - **transform** - Optional local transform to set

            Returns:
                UsdGeom.Xform schema wrapping the defined Usd.Prim. Returns an invalid schema on error.
        )"
    );

    m.def(
        "defineXform",
        overload_cast<UsdPrim, std::optional<const GfTransform>>(&defineXform),
        arg("prim"),
        arg("transform") = nullptr,
        R"(
            Defines an xform from an existing prim.

            This converts an existing prim to an Xform type, preserving any existing transform data.

            Parameters:
                - **prim** - The existing prim to convert to an xform
                - **transform** - Optional local transform to set

            Returns:
                UsdGeom.Xform schema wrapping the converted Usd.Prim.
        )"
    );

    // UsdGeomXformable overloads
    m.def(
        "setLocalTransform",
        overload_cast<const UsdGeomXformable&, const GfTransform&, UsdTimeCode>(&setLocalTransform),
        arg("xformable"),
        arg("transform"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set the local transform of an xformable.

            Parameters:
                - **xformable** - The xformable to set local transform on.
                - **transform** - The transform value to set.
                - **time** - Time at which to write the value.

            Returns:
                A bool indicating if the local transform was set.

        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "setLocalTransform",
        overload_cast<const UsdGeomXformable&, const GfMatrix4d&, UsdTimeCode>(&setLocalTransform),
        arg("xformable"),
        arg("matrix"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set the local transform of an xformable from a 4x4 matrix.

            Parameters:
                - **xformable** - The xformable to set local transform on.
                - **matrix** - The matrix value to set.
                - **time** - Time at which to write the value.

            Returns:
                A bool indicating if the local transform was set.

        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "setLocalTransform",
        overload_cast<const UsdGeomXformable&, const GfVec3d&, const GfVec3d&, const GfVec3f&, const RotationOrder, const GfVec3f&, UsdTimeCode>(
            &setLocalTransform
        ),
        arg("xformable"),
        arg("translation"),
        arg("pivot"),
        arg("rotation"),
        arg("rotationOrder"),
        arg("scale"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set the local transform of an xformable from common transform components.

            Parameters:
                - **xformable** - The xformable to set local transform on.
                - **translation** - The translation value to set.
                - **pivot** - The pivot position value to set.
                - **rotation** - The rotation value to set in degrees.
                - **rotationOrder** - The rotation order of the rotation value.
                - **scale** - The scale value to set.
                - **time** - Time at which to write the value.

            Returns:
                A bool indicating if the local transform was set.

        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "setLocalTransform",
        overload_cast<const UsdGeomXformable&, const GfVec3d&, const GfQuatf&, const GfVec3f&, UsdTimeCode>(&setLocalTransform),
        arg("xformable"),
        arg("translation"),
        arg("orientation"),
        arg("scale") = GfVec3f(1.0f),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set the local transform of an xformable from common transform components using a quaternion for orientation.

            Parameters:
                - **xformable** - The xformable to set local transform on.
                - **translation** - The translation value to set.
                - **orientation** - The orientation value to set as a quaternion.
                - **scale** - The scale value to set - defaults to (1.0, 1.0, 1.0).
                - **time** - Time at which to write the value.

            Returns:
                A bool indicating if the local transform was set.

        )",
        call_guard<gil_scoped_acquire>()
    );

    m.def(
        "getLocalTransform",
        overload_cast<const UsdGeomXformable&, UsdTimeCode>(&getLocalTransform),
        arg("xformable"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Get the local transform of an xformable at a given time.

            Parameters:
                - **xformable** - The xformable to get local transform from.
                - **time** - Time at which to query the value.

            Returns:
                Transform value as a transform.

        )"
    );

    m.def(
        "getLocalTransformMatrix",
        overload_cast<const UsdGeomXformable&, UsdTimeCode>(&getLocalTransformMatrix),
        arg("xformable"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Get the local transform of an xformable at a given time in the form of a 4x4 matrix.

            Parameters:
                - **xformable** - The xformable to get local transform from.
                - **time** - Time at which to query the value.

            Returns:
                Transform value as a 4x4 matrix.

        )"
    );

    m.def(
        "getLocalTransformComponents",
        [](const UsdGeomXformable& xformable, UsdTimeCode time)
        {
            GfVec3d translation;
            GfVec3d pivot;
            GfVec3f rotation;
            RotationOrder rotationOrder;
            GfVec3f scale;
            getLocalTransformComponents(xformable, translation, pivot, rotation, rotationOrder, scale, time);
            return make_tuple(translation, pivot, rotation, rotationOrder, scale);
        },
        arg("xformable"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Get the local transform of an xformable at a given time in the form of common transform components.

            Parameters:
                - **xformable** - The xformable to get local transform from.
                - **time** - Time at which to query the value.

            Returns:
                Transform value as a tuple of translation, pivot, rotation, rotation order, scale.

        )"
    );

    m.def(
        "getLocalTransformComponentsQuat",
        [](const UsdGeomXformable& xformable, UsdTimeCode time)
        {
            GfVec3d translation;
            GfVec3d pivot;
            GfQuatf orientation;
            GfVec3f scale;
            getLocalTransformComponentsQuat(xformable, translation, pivot, orientation, scale, time);
            return make_tuple(translation, pivot, orientation, scale);
        },
        arg("xformable"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Get the local transform of an xformable at a given time in the form of common transform components with quaternion orientation.

            Parameters:
                - **xformable** - The xformable to get local transform from.
                - **time** - Time at which to query the value.

            Returns:
                Transform value as a tuple of translation, pivot, orientation (quaternion), scale.

        )"
    );
}

} // namespace usdex::core::bindings
