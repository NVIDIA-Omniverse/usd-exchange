// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/GprimAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;


namespace usdex::core::bindings
{

void bindGprimAlgo(module& m)
{
    m.def(
        "definePlane",
        overload_cast<UsdStagePtr, const SdfPath&, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(
            &definePlane
        ),
        arg("stage"),
        arg("path"),
        arg("width"),
        arg("length"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"( 
            Defines a plane primitive.

            Defines a plane centered at the origin. The normal vector direction can be specified using ``axis`` as 'X', 'Y', or 'Z'.
            While the ``width`` and ``length`` specify limits for rendering/visualization, it is common to consider the plane as infinite when used as a physics collision in simulation.

            Parameters:
                - **stage** - The stage on which to define the plane
                - **path** - The absolute prim path at which to define the plane
                - **width** - The width of the plane
                - **length** - The length of the plane
                - **axis** - The axis of the plane
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Plane`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePlane",
        overload_cast<UsdPrim, const std::string&, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(
            &definePlane
        ),
        arg("parent"),
        arg("name"),
        arg("width"),
        arg("length"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a plane primitive as a child of the ``parent`` prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the plane
                - **name** - Name of the plane
                - **width** - The width of the plane
                - **length** - The length of the plane
                - **axis** - The axis of the plane
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Plane`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePlane",
        overload_cast<UsdPrim, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(&definePlane),
        arg("prim"),
        arg("width"),
        arg("length"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a plane primitive from an existing prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim below which to define the plane
                - **width** - The width of the plane
                - **length** - The length of the plane
                - **axis** - The axis of the plane
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Plane`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineSphere",
        overload_cast<UsdStagePtr, const SdfPath&, const double, const std::optional<GfVec3f>, const std::optional<float>>(&defineSphere),
        arg("stage"),
        arg("path"),
        arg("radius"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a sphere primitive.

            Defines a sphere of the specified radius at the origin.

            Parameters:
                - **stage** - The stage on which to define the sphere
                - **path** - The absolute prim path at which to define the sphere
                - **radius** - The radius of the sphere
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Sphere`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineSphere",
        overload_cast<UsdPrim, const std::string&, const double, const std::optional<GfVec3f>, const std::optional<float>>(&defineSphere),
        arg("parent"),
        arg("name"),
        arg("radius"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a sphere primitive as a child of the ``parent`` prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the sphere
                - **name** - Name of the sphere
                - **radius** - The radius of the sphere
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Sphere`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineSphere",
        overload_cast<UsdPrim, const double, const std::optional<GfVec3f>, const std::optional<float>>(&defineSphere),
        arg("prim"),
        arg("radius"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a sphere primitive from an existing prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim below which to define the sphere
                - **radius** - The radius of the sphere
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Sphere`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCube",
        overload_cast<UsdStagePtr, const SdfPath&, const double, const std::optional<GfVec3f>, const std::optional<float>>(&defineCube),
        arg("stage"),
        arg("path"),
        arg("size"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cube primitive.

            Defines a cube of the specified size at the origin.

            Note:
                In order to define a rectangular prism, first call ``defineCube`` and then adjust relative scale of each axis using ``usdex.core.setLocalTransform``.

            Parameters:
                - **stage** - The stage on which to define the cube
                - **path** - The absolute prim path at which to define the cube
                - **size** - The size of the cube
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Cube`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCube",
        overload_cast<UsdPrim, const std::string&, const double, const std::optional<GfVec3f>, const std::optional<float>>(&defineCube),
        arg("parent"),
        arg("name"),
        arg("size"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cube primitive from an existing prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the cube
                - **name** - Name of the cube
                - **size** - The size of the cube
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity
        )"
    );

    m.def(
        "defineCube",
        overload_cast<UsdPrim, const double, const std::optional<GfVec3f>, const std::optional<float>>(&defineCube),
        arg("prim"),
        arg("size"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cube primitive from an existing prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim below which to define the cube
                - **size** - The size of the cube
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Cube`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCone",
        overload_cast<UsdStagePtr, const SdfPath&, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(
            &defineCone
        ),
        arg("stage"),
        arg("path"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cone primitive.

            Defines a cone of the specified radius and height at the origin.
            The height direction can be specified using ``axis`` as 'X', 'Y', or 'Z'.

            Parameters:
                - **stage** - The stage on which to define the cone
                - **path** - The absolute prim path at which to define the cone
                - **radius** - The radius of the cone
                - **height** - The height of the cone
                - **axis** - The axis of the cone
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Cone`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCone",
        overload_cast<UsdPrim, const std::string&, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(
            &defineCone
        ),
        arg("parent"),
        arg("name"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cone primitive as a child of the ``parent`` prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the cone
                - **name** - Name of the cone
                - **radius** - The radius of the cone
                - **height** - The height of the cone
                - **axis** - The axis of the cone
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Cone`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCone",
        overload_cast<UsdPrim, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(&defineCone),
        arg("prim"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cone primitive from an existing prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim below which to define the cone
                - **radius** - The radius of the cone
                - **height** - The height of the cone
                - **axis** - The axis of the cone
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Cone`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCylinder",
        overload_cast<UsdStagePtr, const SdfPath&, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(
            &defineCylinder
        ),
        arg("stage"),
        arg("path"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cylinder primitive.

            Defines a cylinder of the specified radius and height at the origin.
            The height direction can be specified using ``axis`` as 'X', 'Y', or 'Z'.

            Parameters:
                - **stage** - The stage on which to define the cylinder
                - **path** - The absolute prim path at which to define the cylinder
                - **radius** - The radius of the cylinder
                - **height** - The height of the cylinder
                - **axis** - The axis of the cylinder
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Cylinder`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCylinder",
        overload_cast<UsdPrim, const std::string&, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(
            &defineCylinder
        ),
        arg("parent"),
        arg("name"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cylinder primitive as a child of the ``parent`` prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the cylinder
                - **name** - Name of the cylinder
                - **radius** - The radius of the cylinder
                - **height** - The height of the cylinder
                - **axis** - The axis of the cylinder
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Cylinder`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCylinder",
        overload_cast<UsdPrim, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(&defineCylinder),
        arg("prim"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a cylinder primitive from an existing prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim below which to define the cylinder
                - **radius** - The radius of the cylinder
                - **height** - The height of the cylinder
                - **axis** - The axis of the cylinder
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Cylinder`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCapsule",
        overload_cast<UsdStagePtr, const SdfPath&, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(
            &defineCapsule
        ),
        arg("stage"),
        arg("path"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a capsule primitive.

            Defines a capsule of the specified radius and height at the origin.
            The height direction can be specified using ``axis`` as 'X', 'Y', or 'Z'.
            The total height of the capsule is ``height`` + ``radius`` + ``radius``.

            Parameters:
                - **stage** - The stage on which to define the capsule
                - **path** - The absolute prim path at which to define the capsule
                - **radius** - The radius of the capsule
                - **height** - The height of the capsule shaft, excluding the end caps
                - **axis** - The axis of the capsule
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Capsule`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCapsule",
        overload_cast<UsdPrim, const std::string&, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(
            &defineCapsule
        ),
        arg("parent"),
        arg("name"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a capsule primitive as a child of the ``parent`` prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the capsule
                - **name** - Name of the capsule
                - **radius** - The radius of the capsule
                - **height** - The height of the capsule shaft, excluding the end caps
                - **axis** - The axis of the capsule
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Capsule`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "defineCapsule",
        overload_cast<UsdPrim, const double, const double, const TfToken, const std::optional<GfVec3f>, const std::optional<float>>(&defineCapsule),
        arg("prim"),
        arg("radius"),
        arg("height"),
        arg("axis"),
        arg("displayColor") = nullptr,
        arg("displayOpacity") = nullptr,
        R"(
            Defines a capsule primitive from an existing prim.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim below which to define the capsule
                - **radius** - The radius of the capsule
                - **height** - The height of the capsule shaft, excluding the end caps
                - **axis** - The axis of the capsule
                - **displayColor** - Values to be authored for the display color
                - **displayOpacity** - Values to be authored for the display opacity

            Returns:
                ``UsdGeom.Capsule`` schema wrapping the defined ``Usd.Prim``.
        )"
    );
}
} // namespace usdex::core::bindings
