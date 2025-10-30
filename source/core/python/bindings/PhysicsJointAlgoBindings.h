// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/PhysicsJointAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

namespace usdex::core::bindings
{

void bindPhysicsJointAlgo(module& m)
{
    pybind11::class_<JointFrame>(
        m,
        "JointFrame",
        R"(
            Specifies a position and rotation in the coordinate system specified by ``space``

            Note:
                The ``position`` and ``orientation`` are stored as doubles to avoid precision loss when aligning the joint to each body.
                This differs from the ``UsdPhysics.Joint`` schema, which stores them as floats. The final authored values on the
                ``PhysicsJoint`` prim will be cast down to floats to align with the schema.
        )"
    )
        .def(pybind11::init<>())
        .def(pybind11::init<JointFrame::Space, const GfVec3d&, const GfQuatd&>(), arg("space"), arg("position"), arg("orientation"))
        .def_readwrite("space", &JointFrame::space, "The space in which the joint is defined")
        .def_readwrite("position", &JointFrame::position, "The position of the joint")
        .def_readwrite("orientation", &JointFrame::orientation, "The orientation of the joint");

    pybind11::enum_<JointFrame::Space>(m.attr("JointFrame"), "Space", "Coordinate systems in which a joint can be defined")
        .value("Body0", JointFrame::Space::Body0, "The joint is defined in the local space of ``body0``")
        .value("Body1", JointFrame::Space::Body1, "The joint is defined in the local space of ``body1``")
        .value("World", JointFrame::Space::World, "The joint is defined in world space");

    m.def(
        "definePhysicsFixedJoint",
        overload_cast<UsdStagePtr, const SdfPath&, const UsdPrim&, const UsdPrim&, const JointFrame&>(&definePhysicsFixedJoint),
        arg("stage"),
        arg("path"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        R"(
            Creates a fixed joint connecting two rigid bodies.

            A fixed joint connects two prims making them effectively welded together.
            For maximal coordinate (free-body) solvers it is important to fully constrain the two bodies. For reduced coordinate solvers this is may seem
            redundant, but it is important for consistency & cross-solver portability.

            Using the coordinate system specified by the ``jointFrame``, the local position and rotation
            corresponding to ``body0`` and ``body1`` of the joint are automatically calculated.

            Parameters:
                - **stage** - The stage on which to define the joint
                - **path** - The absolute prim path at which to define the joint
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.

            Returns:
                ``UsdPhysics.FixedJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsFixedJoint",
        overload_cast<UsdPrim, const std::string&, const UsdPrim&, const UsdPrim&, const JointFrame&>(&definePhysicsFixedJoint),
        arg("parent"),
        arg("name"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        R"(
            Creates a fixed joint connecting two rigid bodies.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the physics joint
                - **name** - Name of the physics joint
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.

            Returns:
                ``UsdPhysics.FixedJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsFixedJoint",
        overload_cast<UsdPrim, const UsdPrim&, const UsdPrim&, const JointFrame&>(&definePhysicsFixedJoint),
        arg("prim"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        R"(
            Creates a fixed joint connecting two rigid bodies.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the joint. The prim's type will be set to ``UsdPhysics.FixedJoint``.
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.

            Returns:
                ``UsdPhysics.FixedJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsRevoluteJoint",
        overload_cast<
            UsdStagePtr,
            const SdfPath&,
            const UsdPrim&,
            const UsdPrim&,
            const JointFrame&,
            const GfVec3f&,
            std::optional<float>,
            std::optional<float>>(&definePhysicsRevoluteJoint),
        arg("stage"),
        arg("path"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("lowerLimit") = nullptr,
        arg("upperLimit") = nullptr,
        R"(
            Creates a revolute joint, which acts as a hinge around a single axis, connecting two rigid bodies.

            Using the coordinate system specified by the ``jointFrame``, the local position and rotation
            corresponding to ``body0`` and ``body1`` of the joint are automatically calculated.

            The ``axis`` specifies the primary axis for rotation, based on the local joint orientation relative to each body.

            - To rotate around the X-axis, specify (1, 0, 0). To rotate in the opposite direction, specify (-1, 0, 0).
            - To rotate around the Y-axis, specify (0, 1, 0). To rotate in the opposite direction, specify (0, -1, 0).
            - To rotate around the Z-axis, specify (0, 0, 1). To rotate in the opposite direction, specify (0, 0, -1).
            - Any other direction will be aligned to X-axis via a local rotation for both bodies.

            Parameters:
                - **stage** - The stage on which to define the joint
                - **path** - The absolute prim path at which to define the joint
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of rotation
                - **lowerLimit** - The lower limit of the joint (degrees).
                - **upperLimit** - The upper limit of the joint (degrees).

            Returns:
                ``UsdPhysics.RevoluteJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsRevoluteJoint",
        overload_cast<
            UsdPrim,
            const std::string&,
            const UsdPrim&,
            const UsdPrim&,
            const JointFrame&,
            const GfVec3f&,
            std::optional<float>,
            std::optional<float>>(&definePhysicsRevoluteJoint),
        arg("parent"),
        arg("name"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("lowerLimit") = nullptr,
        arg("upperLimit") = nullptr,
        R"(
            Creates a revolute joint, which acts as a hinge around a single axis, connecting two rigid bodies.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the physics joint
                - **name** - Name of the physics joint
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of rotation
                - **lowerLimit** - The lower limit of the joint (degrees).
                - **upperLimit** - The upper limit of the joint (degrees).

            Returns:
                ``UsdPhysics.RevoluteJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsRevoluteJoint",
        overload_cast<UsdPrim, const UsdPrim&, const UsdPrim&, const JointFrame&, const GfVec3f&, std::optional<float>, std::optional<float>>(
            &definePhysicsRevoluteJoint
        ),
        arg("prim"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("lowerLimit") = nullptr,
        arg("upperLimit") = nullptr,
        R"(
            Creates a revolute joint, which acts as a hinge around a single axis, connecting two rigid bodies.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the joint. The prim's type will be set to ``UsdPhysics.RevoluteJoint``.
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of rotation
                - **lowerLimit** - The lower limit of the joint (degrees).
                - **upperLimit** - The upper limit of the joint (degrees).

            Returns:
                ``UsdPhysics.RevoluteJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsPrismaticJoint",
        overload_cast<
            UsdStagePtr,
            const SdfPath&,
            const UsdPrim&,
            const UsdPrim&,
            const JointFrame&,
            const GfVec3f&,
            std::optional<float>,
            std::optional<float>>(&definePhysicsPrismaticJoint),
        arg("stage"),
        arg("path"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("lowerLimit") = nullptr,
        arg("upperLimit") = nullptr,
        R"(
            Creates a prismatic joint, which acts as a slider along a single axis, connecting two rigid bodies.

            Using the coordinate system specified by the ``jointFrame``, the local position and rotation
            corresponding to ``body0`` and ``body1`` of the joint are automatically calculated.

            The ``axis`` specifies the primary axis for rotation, based on the local joint orientation relative to each body.

            - To slide along the X-axis, specify (1, 0, 0). To slide in the opposite direction, specify (-1, 0, 0).
            - To slide along the Y-axis, specify (0, 1, 0). To slide in the opposite direction, specify (0, -1, 0).
            - To slide along the Z-axis, specify (0, 0, 1). To slide in the opposite direction, specify (0, 0, -1).
            - Any other direction will be aligned to X-axis via a local rotation for both bodies.

            The ``lowerLimit`` and ``upperLimit`` are specified as distance along the ``axis`` in
            [linear units of the stage](https://openusd.org/release/api/group___usd_geom_linear_units__group.html).

            Parameters:
                - **stage** - The stage on which to define the joint
                - **path** - The absolute prim path at which to define the joint
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of the joint.
                - **lowerLimit** - The lower limit of the joint (distance).
                - **upperLimit** - The upper limit of the joint (distance).

            Returns:
                ``UsdPhysics.PrismaticJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsPrismaticJoint",
        overload_cast<
            UsdPrim,
            const std::string&,
            const UsdPrim&,
            const UsdPrim&,
            const JointFrame&,
            const GfVec3f&,
            std::optional<float>,
            std::optional<float>>(&definePhysicsPrismaticJoint),
        arg("parent"),
        arg("name"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("lowerLimit") = nullptr,
        arg("upperLimit") = nullptr,
        R"(
            Creates a prismatic joint, which acts as a slider along a single axis, connecting two rigid bodies.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the physics joint
                - **name** - Name of the physics joint
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of the joint.
                - **lowerLimit** - The lower limit of the joint (distance).
                - **upperLimit** - The upper limit of the joint (distance).

            Returns:
                ``UsdPhysics.PrismaticJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsPrismaticJoint",
        overload_cast<UsdPrim, const UsdPrim&, const UsdPrim&, const JointFrame&, const GfVec3f&, std::optional<float>, std::optional<float>>(
            &definePhysicsPrismaticJoint
        ),
        arg("prim"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("lowerLimit") = nullptr,
        arg("upperLimit") = nullptr,
        R"(
            Creates a prismatic joint, which acts as a slider along a single axis, connecting two rigid bodies.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the joint. The prim's type will be set to ``UsdPhysics.PrismaticJoint``.
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of the joint.
                - **lowerLimit** - The lower limit of the joint (distance).
                - **upperLimit** - The upper limit of the joint (distance).

            Returns:
                ``UsdPhysics.PrismaticJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsSphericalJoint",
        overload_cast<
            UsdStagePtr,
            const SdfPath&,
            const UsdPrim&,
            const UsdPrim&,
            const JointFrame&,
            const GfVec3f&,
            std::optional<float>,
            std::optional<float>>(&definePhysicsSphericalJoint),
        arg("stage"),
        arg("path"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("coneAngle0Limit") = nullptr,
        arg("coneAngle1Limit") = nullptr,
        R"(
            Creates a spherical joint, which acts as a ball and socket joint, connecting two rigid bodies.

            Using the coordinate system specified by the ``jointFrame``, the local position and rotation
            corresponding to ``body0`` and ``body1`` of the joint are automatically calculated.

            The ``axis`` specifies the primary axis for rotation, based on the local joint orientation relative to each body.

            - To rotate around the X-axis, specify (1, 0, 0). To rotate in the opposite direction, specify (-1, 0, 0).
            - To rotate around the Y-axis, specify (0, 1, 0). To rotate in the opposite direction, specify (0, -1, 0).
            - To rotate around the Z-axis, specify (0, 0, 1). To rotate in the opposite direction, specify (0, 0, -1).
            - Any other direction will be aligned to X-axis via a local rotation for both bodies.

            For SphericalJoint, the axis specified here is used as the center, and the horizontal and vertical cone angles are limited by ``coneAngle0Limit`` and
            ``coneAngle1Limit``.

            Parameters:
                - **stage** - The stage on which to define the joint
                - **path** - The absolute prim path at which to define the joint
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of the joint.
                - **coneAngle0Limit** - The lower limit of the cone angle (degrees).
                - **coneAngle1Limit** - The upper limit of the cone angle (degrees).

            Returns:
                ``UsdPhysics.SphericalJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsSphericalJoint",
        overload_cast<
            UsdPrim,
            const std::string&,
            const UsdPrim&,
            const UsdPrim&,
            const JointFrame&,
            const GfVec3f&,
            std::optional<float>,
            std::optional<float>>(&definePhysicsSphericalJoint),
        arg("parent"),
        arg("name"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("coneAngle0Limit") = nullptr,
        arg("coneAngle1Limit") = nullptr,
        R"(
            Creates a spherical joint, which acts as a ball and socket joint, connecting two rigid bodies.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the physics joint
                - **name** - Name of the physics joint
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of the joint.
                - **coneAngle0Limit** - The lower limit of the cone angle (degrees).
                - **coneAngle1Limit** - The upper limit of the cone angle (degrees).

            Returns:
                ``UsdPhysics.SphericalJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsSphericalJoint",
        overload_cast<UsdPrim, const UsdPrim&, const UsdPrim&, const JointFrame&, const GfVec3f&, std::optional<float>, std::optional<float>>(
            &definePhysicsSphericalJoint
        ),
        arg("prim"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        arg("coneAngle0Limit") = nullptr,
        arg("coneAngle1Limit") = nullptr,
        R"(
            Creates a spherical joint, which acts as a ball and socket joint, connecting two rigid bodies.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the joint. The prim's type will be set to ``UsdPhysics.SphericalJoint``.
                - **body0** - The first body of the joint
                - **body1** - The second body of the joint
                - **frame** - The position and rotation of the joint in the specified coordinate system.
                - **axis** - The axis of the joint.
                - **coneAngle0Limit** - The lower limit of the cone angle (degrees).
                - **coneAngle1Limit** - The upper limit of the cone angle (degrees).

            Returns:
                ``UsdPhysics.SphericalJoint`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "alignPhysicsJoint",
        &alignPhysicsJoint,
        arg("joint"),
        arg("frame"),
        arg("axis"),
        R"(
            Aligns an existing joint with the specified position, rotation, and axis.

            The Joint's local position & orientation relative to each Body will be authored
            to align to the specified position, orientation, and axis.

            The ``axis`` specifies the primary axis for rotation or translation, based on the local joint orientation relative to each body.

            - To rotate or translate about about the X-axis, specify (1, 0, 0). To operate in the opposite direction, specify (-1, 0, 0).
            - To rotate or translate about about the Y-axis, specify (0, 1, 0). To operate in the opposite direction, specify (0, -1, 0).
            - To rotate or translate about about the Z-axis, specify (0, 0, 1). To operate in the opposite direction, specify (0, 0, -1).
            - Any other direction will be aligned to X-axis via a local rotation or translation for both bodies.

            Args:
                joint: The joint to align
                frame: Specifies the position and rotation of the joint in the specified coordinate system.
                axis: The axis of the joint.

        )"
    );

    m.def(
        "connectPhysicsJoint",
        &connectPhysicsJoint,
        arg("joint"),
        arg("body0"),
        arg("body1"),
        arg("frame"),
        arg("axis"),
        R"(
            Connects an existing joint to the specified body prims and realigns the joint frame accordingly.

            If the joint was previously targetting different bodies, they will be replaced with relationships to the new bodies.

            The Joint's local position & orientation relative to the new bodies will be authored
            to align to the specified position, orientation, and axis.
            If either ``body0`` or ``body1`` is an invalid prim, the corresponding body relationship on the joint will be cleared and the joint will
            be connected between the valid body and the world.

            The ``axis`` specifies the primary axis for rotation or translation, based on the local joint orientation relative to each body.

            - To rotate or translate about about the X-axis, specify (1, 0, 0). To operate in the opposite direction, specify (-1, 0, 0).
            - To rotate or translate about about the Y-axis, specify (0, 1, 0). To operate in the opposite direction, specify (0, -1, 0).
            - To rotate or translate about about the Z-axis, specify (0, 0, 1). To operate in the opposite direction, specify (0, 0, -1).
            - Any other direction will be aligned to X-axis via a local rotation or translation for both bodies.

            Args:
                joint: The joint to align
                body0: The first body of the joint
                body1: The second body of the joint
                frame: Specifies the position and rotation of the joint in the specified coordinate system.
                axis: The axis of the joint.

        )"
    );
}
} // namespace usdex::core::bindings
