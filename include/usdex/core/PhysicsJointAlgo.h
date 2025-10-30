// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/core/PhysicsJointAlgo.h
//! @brief Utility functions to create physics joints.

#include "Api.h"

#include <pxr/base/gf/quatf.h>
#include <pxr/base/gf/vec3f.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdPhysics/fixedJoint.h>
#include <pxr/usd/usdPhysics/joint.h>
#include <pxr/usd/usdPhysics/prismaticJoint.h>
#include <pxr/usd/usdPhysics/revoluteJoint.h>
#include <pxr/usd/usdPhysics/sphericalJoint.h>

#include <math.h>
#include <optional>

namespace usdex::core
{
//! @defgroup physicsjoints Physics Joint Prims
//!
//! [PhysicsJoint](https://openusd.org/release/api/usd_physics_page_front.html#usdPhysics_joints) Prims define constraints which reduce the
//! degrees of freedom between two bodies.
//!
//! The `PhysicsJoint` prims can be thought of as existing in two places at once: relative to each body that they constrain.
//! Properly defining `PhysicsJoints` relative to both bodies can be arduous, especially given differences in source data specification across
//! maximal coordinate (free-body) and reduced coordinate solvers.
//!
//! This module simplifies the authoring process and ensures `PhysicsJoints` are aligned to both bodies, regardless of the source data specification.
//!
//! @{

//! Specifies a position and rotation in the coordinate system specified by ``space``
//!
//! @note The `position` and `orientation` are stored as doubles to avoid precision loss when aligning the joint to each body. This differs from the
//! `UsdPhysicsJoint` schema, which stores them as floats. The final authored values on the `PhysicsJoint` prim will be cast down to floats to align
//! with the schema.
class JointFrame
{
public:

    //! Coordinate systems in which a joint can be defined
    // clang-format off
    enum class Space
    {
        Body0, //!< The joint is defined in the local space of `body0`
        Body1, //!< The joint is defined in the local space of `body1`
        World, //!< The joint is defined in world space
    };
    // clang-format on

    Space space; //!< The space in which the joint is defined
    pxr::GfVec3d position; //!< The position of the joint
    pxr::GfQuatd orientation; //!< The orientation of the joint
};

//! Creates a fixed joint connecting two rigid bodies.
//!
//! A fixed joint connects two prims making them effectively welded together.
//! For maximal coordinate (free-body) solvers it is important to fully constrain the two bodies. For reduced coordinate solvers this is may seem
//! redundant, but it is important for consistency & cross-solver portability.
//!
//! Using the coordinate system specified by the `jointFrame`, the local position and rotation
//! corresponding to `body0` and `body1` of the joint are automatically calculated.
//!
//! @param stage The stage on which to define the joint
//! @param path The absolute prim path at which to define the joint
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//!
//! @returns UsdPhysicsFixedJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsFixedJoint definePhysicsFixedJoint(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame
);

//! Creates a fixed joint connecting two rigid bodies.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the physics joint
//! @param name Name of the physics joint
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//!
//! @returns UsdPhysicsFixedJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsFixedJoint definePhysicsFixedJoint(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame
);

//! Creates a fixed joint connecting two rigid bodies.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the joint. The prim's type will be set to `UsdPhysicsFixedJoint`.
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//!
//! @returns UsdPhysicsFixedJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsFixedJoint definePhysicsFixedJoint(
    pxr::UsdPrim prim,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame
);

//! Creates a revolute joint, which acts as a hinge around a single axis, connecting two rigid bodies.
//!
//! Using the coordinate system specified by the `jointFrame`, the local position and rotation
//! corresponding to `body0` and `body1` of the joint are automatically calculated.
//!
//! The `axis` specifies the primary axis for rotation, based on the local joint orientation relative to each body.
//!
//!   - To rotate around the X-axis, specify (1, 0, 0). To rotate in the opposite direction, specify (-1, 0, 0).
//!   - To rotate around the Y-axis, specify (0, 1, 0). To rotate in the opposite direction, specify (0, -1, 0).
//!   - To rotate around the Z-axis, specify (0, 0, 1). To rotate in the opposite direction, specify (0, 0, -1).
//!   - Any other direction will be aligned to X-axis via a local rotation for both bodies.
//!
//! @param stage The stage on which to define the joint
//! @param path The absolute prim path at which to define the joint
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of rotation
//! @param lowerLimit The lower limit of the joint (degrees).
//! @param upperLimit The upper limit of the joint (degrees).
//!
//! @returns UsdPhysicsRevoluteJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsRevoluteJoint definePhysicsRevoluteJoint(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> lowerLimit = std::nullopt,
    std::optional<float> upperLimit = std::nullopt
);

//! Creates a revolute joint, which acts as a hinge around a single axis, connecting two rigid bodies.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the physics joint
//! @param name Name of the physics joint
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of rotation
//! @param lowerLimit The lower limit of the joint (degrees).
//! @param upperLimit The upper limit of the joint (degrees).
//!
//! @returns UsdPhysicsRevoluteJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsRevoluteJoint definePhysicsRevoluteJoint(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> lowerLimit = std::nullopt,
    std::optional<float> upperLimit = std::nullopt
);

//! Creates a revolute joint, which acts as a hinge around a single axis, connecting two rigid bodies.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the joint. The prim's type will be set to `UsdPhysicsRevoluteJoint`.
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of rotation
//! @param lowerLimit The lower limit of the joint (degrees).
//! @param upperLimit The upper limit of the joint (degrees).
//!
//! @returns UsdPhysicsRevoluteJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsRevoluteJoint definePhysicsRevoluteJoint(
    pxr::UsdPrim prim,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> lowerLimit = std::nullopt,
    std::optional<float> upperLimit = std::nullopt
);

//! Creates a prismatic joint, which acts as a slider along a single axis, connecting two rigid bodies.
//!
//! Using the coordinate system specified by the `jointFrame`, the local position and rotation
//! corresponding to `body0` and `body1` of the joint are automatically calculated.
//!
//! The `axis` specifies the primary axis for rotation, based on the local joint orientation relative to each body.
//!
//!   - To slide along the X-axis, specify (1, 0, 0). To slide in the opposite direction, specify (-1, 0, 0).
//!   - To slide along the Y-axis, specify (0, 1, 0). To slide in the opposite direction, specify (0, -1, 0).
//!   - To slide along the Z-axis, specify (0, 0, 1). To slide in the opposite direction, specify (0, 0, -1).
//!   - Any other direction will be aligned to X-axis via a local rotation for both bodies.
//!
//! The `lowerLimit` and `upperLimit` are specified as distance along the `axis` in
//! [linear units of the stage](https://openusd.org/release/api/group___usd_geom_linear_units__group.html).
//!
//! @param stage The stage on which to define the joint
//! @param path The absolute prim path at which to define the joint
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of the joint.
//! @param lowerLimit The lower limit of the joint (distance).
//! @param upperLimit The upper limit of the joint (distance).
//!
//! @returns UsdPhysicsPrismaticJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsPrismaticJoint definePhysicsPrismaticJoint(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> lowerLimit = std::nullopt,
    std::optional<float> upperLimit = std::nullopt
);

//! Creates a prismatic joint, which acts as a slider along a single axis, connecting two rigid bodies.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the physics joint
//! @param name Name of the physics joint
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of the joint.
//! @param lowerLimit The lower limit of the joint (distance).
//! @param upperLimit The upper limit of the joint (distance).
//!
//! @returns UsdPhysicsPrismaticJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsPrismaticJoint definePhysicsPrismaticJoint(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> lowerLimit = std::nullopt,
    std::optional<float> upperLimit = std::nullopt
);

//! Creates a prismatic joint, which acts as a slider along a single axis, connecting two rigid bodies.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the joint. The prim's type will be set to `UsdPhysicsPrismaticJoint`.
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of the joint.
//! @param lowerLimit The lower limit of the joint (distance).
//! @param upperLimit The upper limit of the joint (distance).
//!
//! @returns UsdPhysicsPrismaticJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsPrismaticJoint definePhysicsPrismaticJoint(
    pxr::UsdPrim prim,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> lowerLimit = std::nullopt,
    std::optional<float> upperLimit = std::nullopt
);

//! Creates a spherical joint, which acts as a ball and socket joint, connecting two rigid bodies.
//!
//! Using the coordinate system specified by the `jointFrame`, the local position and rotation
//! corresponding to `body0` and `body1` of the joint are automatically calculated.
//!
//! The `axis` specifies the primary axis for rotation, based on the local joint orientation relative to each body.
//!
//!   - To rotate around the X-axis, specify (1, 0, 0). To rotate in the opposite direction, specify (-1, 0, 0).
//!   - To rotate around the Y-axis, specify (0, 1, 0). To rotate in the opposite direction, specify (0, -1, 0).
//!   - To rotate around the Z-axis, specify (0, 0, 1). To rotate in the opposite direction, specify (0, 0, -1).
//!   - Any other direction will be aligned to X-axis via a local rotation for both bodies.
//!
//! For SphericalJoint, the axis specified here is used as the center, and the horizontal and vertical cone angles are limited by `coneAngle0Limit`
//! and `coneAngle1Limit`.
//!
//! @param stage The stage on which to define the joint
//! @param path The absolute prim path at which to define the joint
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of the joint.
//! @param coneAngle0Limit The lower limit of the cone angle (degrees).
//! @param coneAngle1Limit The upper limit of the cone angle (degrees).
//!
//! @returns UsdPhysicsSphericalJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsSphericalJoint definePhysicsSphericalJoint(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> coneAngle0Limit = std::nullopt,
    std::optional<float> coneAngle1Limit = std::nullopt
);

//! Creates a spherical joint, which acts as a ball and socket joint, connecting two rigid bodies.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the physics joint
//! @param name Name of the physics joint
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of the joint.
//! @param coneAngle0Limit The lower limit of the cone angle (degrees).
//! @param coneAngle1Limit The upper limit of the cone angle (degrees).
//!
//! @returns UsdPhysicsSphericalJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsSphericalJoint definePhysicsSphericalJoint(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> coneAngle0Limit = std::nullopt,
    std::optional<float> coneAngle1Limit = std::nullopt
);

//! Creates a spherical joint, which acts as a ball and socket joint, connecting two rigid bodies.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the joint. The prim's type will be set to `UsdPhysicsSphericalJoint`.
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of the joint.
//! @param coneAngle0Limit The lower limit of the cone angle (degrees).
//! @param coneAngle1Limit The upper limit of the cone angle (degrees).
//!
//! @returns UsdPhysicsSphericalJoint schema wrapping the defined UsdPrim
USDEX_API pxr::UsdPhysicsSphericalJoint definePhysicsSphericalJoint(
    pxr::UsdPrim prim,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f),
    std::optional<float> coneAngle0Limit = std::nullopt,
    std::optional<float> coneAngle1Limit = std::nullopt
);

//! Aligns an existing joint with the specified position, rotation, and axis.
//!
//! The Joint's local position & orientation relative to each Body will be authored
//! to align to the specified position, orientation, and axis.
//!
//! The `axis` specifies the primary axis for rotation or translation, based on the local joint orientation relative to each body.
//!
//!   - To rotate or translate about the X-axis, specify (1, 0, 0). To operate in the opposite direction, specify (-1, 0, 0).
//!   - To rotate or translate about about the Y-axis, specify (0, 1, 0). To operate in the opposite direction, specify (0, -1, 0).
//!   - To rotate or translate about about the Z-axis, specify (0, 0, 1). To operate in the opposite direction, specify (0, 0, -1).
//!   - Any other direction will be aligned to X-axis via a local rotation or translation for both bodies.
//!
//! @param joint The joint to align
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of the joint.
USDEX_API void alignPhysicsJoint(pxr::UsdPhysicsJoint joint, const JointFrame& frame, const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f));

//! Connects an existing joint to the specified body prims and realigns the joint frame accordingly.
//!
//! If the joint was previously targetting different bodies, they will be replaced with relationships to the new bodies.
//!
//! If either `body0` or `body1` is an invalid prim, the corresponding body relationship on the joint will be cleared and the joint will
//! be connected between the valid body and the world.
//!
//! The Joint's local position & orientation relative to the new bodies will be authored
//! to align to the specified position, orientation, and axis.
//!
//! The `axis` specifies the primary axis for rotation or translation, based on the local joint orientation relative to each body.
//!
//!   - To rotate or translate about the X-axis, specify (1, 0, 0). To operate in the opposite direction, specify (-1, 0, 0).
//!   - To rotate or translate about about the Y-axis, specify (0, 1, 0). To operate in the opposite direction, specify (0, -1, 0).
//!   - To rotate or translate about about the Z-axis, specify (0, 0, 1). To operate in the opposite direction, specify (0, 0, -1).
//!   - Any other direction will be aligned to X-axis via a local rotation or translation for both bodies.
//!
//! @param joint The joint to align
//! @param body0 The first body of the joint
//! @param body1 The second body of the joint
//! @param frame The position and rotation of the joint in the specified coordinate system.
//! @param axis The axis of the joint.
USDEX_API void connectPhysicsJoint(
    pxr::UsdPhysicsJoint joint,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const JointFrame& frame,
    const pxr::GfVec3f& axis = pxr::GfVec3f(1.0f, 0.0f, 0.0f)
);

//! @}

} // namespace usdex::core
