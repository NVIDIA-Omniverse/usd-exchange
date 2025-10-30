// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/PhysicsJointAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/base/gf/homogeneous.h>
#include <pxr/base/gf/rotation.h>
#include <pxr/base/gf/vec4f.h>
#include <pxr/usd/usdGeom/xformCache.h>
#include <pxr/usd/usdPhysics/prismaticJoint.h>
#include <pxr/usd/usdPhysics/revoluteJoint.h>
#include <pxr/usd/usdPhysics/sphericalJoint.h>
#include <pxr/usd/usdPhysics/tokens.h>

#include <algorithm>
#include <limits>
#include <optional>

using namespace pxr;

namespace
{
// Calculates the rotation of a vector along the x-axis.
GfQuatd alignVectorToXAxis(const GfVec3f& axis)
{
    if (axis.GetLength() < std::numeric_limits<float>::epsilon())
    {
        return GfQuatd::GetIdentity();
    }

    // If the vector is already aligned with the X-axis or directly opposite
    // Handle these edge cases to prevent division by zero or incorrect axis.
    if (std::abs(axis[0] - 1.0f) < std::numeric_limits<float>::epsilon())
    {
        // When axis is (1, 0, 0).
        return GfQuatd::GetIdentity();
    }
    else if (std::abs(axis[0] + 1.0f) < std::numeric_limits<float>::epsilon())
    {
        // When axis is (-1, 0, 0).
        // If aligned with negative X-axis, rotate 180 degrees around Y-axis (or Z-axis)
        return GfQuatd(0.0, 0.0, 1.0, 0.0); // Quaternion for 180 deg around Y-axis (w=0, x=0, y=sin(90), z=0)
    }

    // Calculate the rotation axis (cross product of XAxis and axis)
    const GfVec3f rotationAxis = GfCross(GfVec3f(1.0f, 0.0f, 0.0f), axis);
    const GfVec3f rotationAxisNorm = rotationAxis.GetNormalized();
    if (rotationAxisNorm.GetLength() < std::numeric_limits<float>::epsilon())
    {
        return GfQuatd::GetIdentity();
    }

    // Calculate the angle (dot product of axis and XAxis)
    const double dotProduct = GfDot(axis, GfVec3f::XAxis());

    // Clip to avoid floating point errors
    const double angle = std::acos(std::min(std::max(dotProduct, -1.0), 1.0));

    // Construct the quaternion (wxyz order)
    const double w = std::cos(angle / 2.0);
    const double x = rotationAxisNorm[0] * std::sin(angle / 2.0);
    const double y = rotationAxisNorm[1] * std::sin(angle / 2.0);
    const double z = rotationAxisNorm[2] * std::sin(angle / 2.0);

    return GfQuatd(w, x, y, z);
}

// Get the axis alignment and orientation for the given axis.
void getAxisAlignment(const GfVec3f& axis, TfToken& axisToken, GfQuatd& orientation)
{
    const GfVec3f _axis = axis.GetNormalized();
    axisToken = UsdPhysicsTokens->x;
    if (_axis.GetLength() < std::numeric_limits<float>::epsilon())
    {
        orientation = GfQuatf::GetIdentity();
        return;
    }

    if (std::abs(_axis[0] - 1.0f) < std::numeric_limits<float>::epsilon())
    {
        // When _axis is (1, 0, 0).
        axisToken = UsdPhysicsTokens->x;
    }
    else if (std::abs(_axis[1] - 1.0f) < std::numeric_limits<float>::epsilon())
    {
        // When _axis is (0, 1, 0).
        axisToken = UsdPhysicsTokens->y;
    }
    else if (std::abs(_axis[2] - 1.0f) < std::numeric_limits<float>::epsilon())
    {
        // When _axis is (0, 0, 1).
        axisToken = UsdPhysicsTokens->z;
    }
    else if (std::abs(_axis[0] + 1.0f) < std::numeric_limits<float>::epsilon())
    {
        // When _axis is (-1, 0, 0).
        axisToken = UsdPhysicsTokens->x;
        const auto axisToX = GfQuatd(_axis[1], _axis[2], _axis[0], 0.0);
        orientation = orientation * axisToX;
    }
    else if (std::abs(_axis[1] + 1.0f) < std::numeric_limits<float>::epsilon())
    {
        // When _axis is (0, -1, 0).
        axisToken = UsdPhysicsTokens->y;
        const auto axisToY = GfQuatd(_axis[0], _axis[1], _axis[2], 0.0);
        orientation = orientation * axisToY;
    }
    else if (std::abs(_axis[2] + 1.0f) < std::numeric_limits<float>::epsilon())
    {
        // When _axis is (0, 0, -1).
        axisToken = UsdPhysicsTokens->z;
        const auto axisToZ = GfQuatd(_axis[1], _axis[2], _axis[0], 0.0);
        orientation = orientation * axisToZ;
    }
    else
    {
        // If neither XYZ applies, rotation is performed around _axis.
        axisToken = UsdPhysicsTokens->x;
        const auto rotation = alignVectorToXAxis(_axis);
        orientation = orientation * rotation;
    }
}

// Compute the local transform of the joint.
// This function calculates the local position and rotation (orientation) of body0 and body1, which are the parameters of the physics joint.
// Transforms the 'position' and 'orientation' given in the coordinate system of 'frameSpace' into local coordinates of 'targetSpace' (body0 or
// body1).
std::pair<GfVec3d, GfQuatd> computeLocalTransform(
    const GfMatrix4d& targetBodyTransform,
    const GfMatrix4d& otherBodyTransform,
    const usdex::core::JointFrame::Space& targetSpace,
    const usdex::core::JointFrame::Space& frameSpace,
    const GfVec3d& position,
    const GfQuatd& orientation
)
{
    GfVec3d worldPos = position;
    GfQuatd worldRot = orientation;

    // If the transformation on body0 is for frameSpace = body0, it will be returned as local coordinates.
    // If the transformation on body1 is for frameSpace = body1, it will be returned as local coordinates.
    if ((frameSpace == usdex::core::JointFrame::Space::Body0 && targetSpace == usdex::core::JointFrame::Space::Body0) ||
        (frameSpace == usdex::core::JointFrame::Space::Body1 && targetSpace == usdex::core::JointFrame::Space::Body1))
    {
        return { position, orientation };
    }

    // When transforming on body1, if frameSpace is body0, convert position and rotation to world coordinates.
    else if (frameSpace == usdex::core::JointFrame::Space::Body0 && targetSpace == usdex::core::JointFrame::Space::Body1)
    {
        worldPos = otherBodyTransform.Transform(position);
        worldRot = otherBodyTransform.RemoveScaleShear().ExtractRotation().GetQuat() * orientation;
    }

    // When transforming on body0, if frameSpace is body1, convert position and rotation to world coordinates.
    else if (frameSpace == usdex::core::JointFrame::Space::Body1 && targetSpace == usdex::core::JointFrame::Space::Body0)
    {
        worldPos = otherBodyTransform.Transform(position);
        worldRot = otherBodyTransform.RemoveScaleShear().ExtractRotation().GetQuat() * orientation;
    }
    // Otherwise, worldPos and worldRot contain the position and rotation in world coordinates, respectively.

    // The world transformation matrix for body0 or body1 is in 'targetBodyTransform'.
    // This matrix is used to convert to local coordinate position and rotation by multiplying with the inverse matrix.
    // USD physics does not allow unequal scales and shear components to be introduced in joint localRot.
    // Therefore, we first remove the scale and shear from the matrix.
    GfVec3d localPos = targetBodyTransform.GetInverse().Transform(GfVec3d(worldPos));
    GfQuatd localRot = targetBodyTransform.RemoveScaleShear().ExtractRotation().GetInverse().GetQuat() * worldRot;
    return { localPos, localRot };
}

// Specify basic parameters of Physics Joint.
void setPhysicsJoint(
    UsdPhysicsJoint& joint,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    std::optional<GfVec3f> axis = std::nullopt
)
{
    GfQuatd _orientation = frame.orientation;

    // Set the axis.
    if (axis.has_value())
    {
        GfVec3f _axis = axis.value();

        // Get the axis alignment and orientation for the given axis.
        // The third argument specifies the rotation value as the input value.
        // The return value will be stored in the second argument as either 'X', 'Y', or 'Z'. The converted rotation value will be stored in the third
        // argument.
        TfToken axisToken;
        getAxisAlignment(_axis, axisToken, _orientation);

        UsdPhysicsRevoluteJoint revoluteJoint = UsdPhysicsRevoluteJoint(joint);
        if (revoluteJoint)
        {
            revoluteJoint.GetAxisAttr().Set(axisToken);
        }
        UsdPhysicsPrismaticJoint prismaticJoint = UsdPhysicsPrismaticJoint(joint);
        if (prismaticJoint)
        {
            prismaticJoint.GetAxisAttr().Set(axisToken);
        }
        UsdPhysicsSphericalJoint sphericalJoint = UsdPhysicsSphericalJoint(joint);
        if (sphericalJoint)
        {
            sphericalJoint.GetAxisAttr().Set(axisToken);
        }
    }

    // Get the local to world coordinate transformation matrix for body0 and body1.
    auto xformCache = UsdGeomXformCache();
    const GfMatrix4d body0Transform = body0 ? xformCache.GetLocalToWorldTransform(body0) : GfMatrix4d(1.0);
    const GfMatrix4d body1Transform = body1 ? xformCache.GetLocalToWorldTransform(body1) : GfMatrix4d(1.0);

    if (body0)
    {
        // Compute the local position and rotation of body0.
        auto [localPos, localRot] = computeLocalTransform(
            body0Transform,
            body1Transform,
            usdex::core::JointFrame::Space::Body0,
            frame.space,
            frame.position,
            _orientation
        );
        joint.GetLocalPos0Attr().Set(GfVec3f(localPos));
        joint.GetLocalRot0Attr().Set(GfQuatf(localRot));
    }

    if (body1)
    {
        // Compute the local position and rotation of body1.
        auto [localPos, localRot] = computeLocalTransform(
            body1Transform,
            body0Transform,
            usdex::core::JointFrame::Space::Body1,
            frame.space,
            frame.position,
            _orientation
        );
        joint.GetLocalPos1Attr().Set(GfVec3f(localPos));
        joint.GetLocalRot1Attr().Set(GfQuatf(localRot));
    }
}

// Validate the arguments when creating each physics joint.
bool validatePhysicsJointArguments(
    UsdStagePtr stage,
    const SdfPath& path,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    std::string* reason
)
{
    // Early out if the proposed prim location is invalid
    std::string _reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &_reason))
    {
        *reason = TfStringPrintf("An invalid location: %s", _reason.c_str());
        return false;
    }

    if (!body0 && !body1)
    {
        *reason = TfStringPrintf("Body0 or Body1 are not specified. One of these must exist.");
        return false;
    }
    if (body0 && !UsdGeomXformable(body0))
    {
        *reason = TfStringPrintf("Body0( \"%s\" ) is not a UsdGeomXformable", body0.GetPath().GetAsString().c_str());
        return false;
    }
    if (body1 && !UsdGeomXformable(body1))
    {
        *reason = TfStringPrintf("Body1( \"%s\" ) is not a UsdGeomXformable", body1.GetPath().GetAsString().c_str());
        return false;
    }
    if (!body0 && frame.space == usdex::core::JointFrame::Space::Body0)
    {
        *reason = TfStringPrintf("Body0 is specified in the JointFrame Space, but Body0 does not exist.");
        return false;
    }
    if (!body1 && frame.space == usdex::core::JointFrame::Space::Body1)
    {
        *reason = TfStringPrintf("Body1 is specified in the JointFrame Space, but Body1 does not exist.");
        return false;
    }
    return true;
}

} // namespace

UsdPhysicsFixedJoint usdex::core::definePhysicsFixedJoint(
    UsdStagePtr stage,
    const SdfPath& path,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame
)
{
    // Check the arguments when creating each joint.
    std::string reason;
    if (!validatePhysicsJointArguments(stage, path, body0, body1, frame, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsFixedJoint at \"%s\": %s", path.GetAsString().c_str(), reason.c_str());
        return UsdPhysicsFixedJoint();
    }

    auto joint = UsdPhysicsFixedJoint::Define(stage, path);
    if (!joint)
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsFixedJoint at \"%s\"", path.GetAsString().c_str());
        return UsdPhysicsFixedJoint();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = joint.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Specifies the bodies to be connected to the joint.
    if (body0)
    {
        if (!joint.GetBody0Rel().SetTargets(SdfPathVector({ body0.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body0( \"%s\" ) for PhysicsFixedJoint at \"%s\"",
                body0.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return UsdPhysicsFixedJoint();
        }
    }
    if (body1)
    {
        if (!joint.GetBody1Rel().SetTargets(SdfPathVector({ body1.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body1( \"%s\" ) for PhysicsFixedJoint at \"%s\"",
                body1.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return UsdPhysicsFixedJoint();
        }
    }

    // Set the physics joint.
    setPhysicsJoint(joint, body0, body1, frame);

    return joint;
}

UsdPhysicsFixedJoint usdex::core::definePhysicsFixedJoint(
    UsdPrim parent,
    const std::string& name,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsFixedJoint due to an invalid location: %s", reason.c_str());
        return UsdPhysicsFixedJoint();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return definePhysicsFixedJoint(stage, path, body0, body1, frame);
}

UsdPhysicsFixedJoint usdex::core::definePhysicsFixedJoint(
    UsdPrim prim,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsFixedJoint on invalid prim");
        return UsdPhysicsFixedJoint();
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsFixedJoint due to an invalid location: %s", reason.c_str());
        return UsdPhysicsFixedJoint();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return definePhysicsFixedJoint(stage, path, body0, body1, frame);
}

UsdPhysicsRevoluteJoint usdex::core::definePhysicsRevoluteJoint(
    UsdStagePtr stage,
    const SdfPath& path,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> lowerLimit,
    std::optional<float> upperLimit
)
{
    // Check the arguments when creating each joint.
    std::string reason;
    if (!validatePhysicsJointArguments(stage, path, body0, body1, frame, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsRevoluteJoint at \"%s\": %s", path.GetAsString().c_str(), reason.c_str());
        return UsdPhysicsRevoluteJoint();
    }

    auto joint = UsdPhysicsRevoluteJoint::Define(stage, path);
    if (!joint)
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsRevoluteJoint at \"%s\"", path.GetAsString().c_str());
        return UsdPhysicsRevoluteJoint();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = joint.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Specifies the bodies to be connected to the joint.
    if (body0)
    {
        if (!joint.GetBody0Rel().SetTargets(SdfPathVector({ body0.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body0( \"%s\" ) for PhysicsRevoluteJoint at \"%s\"",
                body0.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return UsdPhysicsRevoluteJoint();
        }
    }
    if (body1)
    {
        if (!joint.GetBody1Rel().SetTargets(SdfPathVector({ body1.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body1( \"%s\" ) for PhysicsRevoluteJoint at \"%s\"",
                body1.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return UsdPhysicsRevoluteJoint();
        }
    }

    // Set the physics joint.
    setPhysicsJoint(joint, body0, body1, frame, axis);

    if (lowerLimit.has_value())
    {
        joint.GetLowerLimitAttr().Set(lowerLimit.value());
    }
    if (upperLimit.has_value())
    {
        joint.GetUpperLimitAttr().Set(upperLimit.value());
    }

    return joint;
}

UsdPhysicsRevoluteJoint usdex::core::definePhysicsRevoluteJoint(
    UsdPrim parent,
    const std::string& name,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> lowerLimit,
    std::optional<float> upperLimit
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsRevoluteJoint due to an invalid location: %s", reason.c_str());
        return UsdPhysicsRevoluteJoint();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return definePhysicsRevoluteJoint(stage, path, body0, body1, frame, axis, lowerLimit, upperLimit);
}

UsdPhysicsRevoluteJoint usdex::core::definePhysicsRevoluteJoint(
    UsdPrim prim,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> lowerLimit,
    std::optional<float> upperLimit
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsRevoluteJoint on invalid prim");
        return UsdPhysicsRevoluteJoint();
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsRevoluteJoint due to an invalid location: %s", reason.c_str());
        return UsdPhysicsRevoluteJoint();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return definePhysicsRevoluteJoint(stage, path, body0, body1, frame, axis, lowerLimit, upperLimit);
}

UsdPhysicsPrismaticJoint usdex::core::definePhysicsPrismaticJoint(
    UsdStagePtr stage,
    const SdfPath& path,
    const UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> lowerLimit,
    std::optional<float> upperLimit
)
{
    // Check the arguments when creating each joint.
    std::string reason;
    if (!validatePhysicsJointArguments(stage, path, body0, body1, frame, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsPrismaticJoint at \"%s\": %s", path.GetAsString().c_str(), reason.c_str());
        return UsdPhysicsPrismaticJoint();
    }

    auto joint = UsdPhysicsPrismaticJoint::Define(stage, path);
    if (!joint)
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsPrismaticJoint at \"%s\"", path.GetAsString().c_str());
        return UsdPhysicsPrismaticJoint();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = joint.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Specifies the bodies to be connected to the joint.
    if (body0)
    {
        if (!joint.GetBody0Rel().SetTargets(SdfPathVector({ body0.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body0( \"%s\" ) for PhysicsPrismaticJoint at \"%s\"",
                body0.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return UsdPhysicsPrismaticJoint();
        }
    }
    if (body1)
    {
        if (!joint.GetBody1Rel().SetTargets(SdfPathVector({ body1.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body1( \"%s\" ) for PhysicsPrismaticJoint at \"%s\"",
                body1.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return UsdPhysicsPrismaticJoint();
        }
    }

    // Set the physics joint.
    setPhysicsJoint(joint, body0, body1, frame, axis);

    if (lowerLimit.has_value())
    {
        joint.GetLowerLimitAttr().Set(lowerLimit.value());
    }
    if (upperLimit.has_value())
    {
        joint.GetUpperLimitAttr().Set(upperLimit.value());
    }

    return joint;
}

UsdPhysicsPrismaticJoint usdex::core::definePhysicsPrismaticJoint(
    UsdPrim parent,
    const std::string& name,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> lowerLimit,
    std::optional<float> upperLimit
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsPrismaticJoint due to an invalid location: %s", reason.c_str());
        return UsdPhysicsPrismaticJoint();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return definePhysicsPrismaticJoint(stage, path, body0, body1, frame, axis, lowerLimit, upperLimit);
}

UsdPhysicsPrismaticJoint usdex::core::definePhysicsPrismaticJoint(
    UsdPrim prim,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> lowerLimit,
    std::optional<float> upperLimit
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsPrismaticJoint on invalid prim");
        return UsdPhysicsPrismaticJoint();
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsPrismaticJoint due to an invalid location: %s", reason.c_str());
        return UsdPhysicsPrismaticJoint();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return definePhysicsPrismaticJoint(stage, path, body0, body1, frame, axis, lowerLimit, upperLimit);
}

UsdPhysicsSphericalJoint usdex::core::definePhysicsSphericalJoint(
    UsdStagePtr stage,
    const SdfPath& path,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> coneAngle0Limit,
    std::optional<float> coneAngle1Limit
)
{
    // Check the arguments when creating each joint.
    std::string reason;
    if (!validatePhysicsJointArguments(stage, path, body0, body1, frame, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsSphericalJoint at \"%s\": %s", path.GetAsString().c_str(), reason.c_str());
        return UsdPhysicsSphericalJoint();
    }

    auto joint = UsdPhysicsSphericalJoint::Define(stage, path);
    if (!joint)
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsSphericalJoint at \"%s\"", path.GetAsString().c_str());
        return UsdPhysicsSphericalJoint();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = joint.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Specifies the bodies to be connected to the joint.
    if (body0)
    {
        if (!joint.GetBody0Rel().SetTargets(SdfPathVector({ body0.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body0( \"%s\" ) for PhysicsSphericalJoint at \"%s\"",
                body0.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return UsdPhysicsSphericalJoint();
        }
    }
    if (body1)
    {
        if (!joint.GetBody1Rel().SetTargets(SdfPathVector({ body1.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body1( \"%s\" ) for PhysicsSphericalJoint at \"%s\"",
                body1.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return UsdPhysicsSphericalJoint();
        }
    }

    // Set the physics joint.
    setPhysicsJoint(joint, body0, body1, frame, axis);

    if (coneAngle0Limit.has_value())
    {
        joint.GetConeAngle0LimitAttr().Set(coneAngle0Limit.value());
    }
    if (coneAngle1Limit.has_value())
    {
        joint.GetConeAngle1LimitAttr().Set(coneAngle1Limit.value());
    }

    return joint;
}

UsdPhysicsSphericalJoint usdex::core::definePhysicsSphericalJoint(
    UsdPrim parent,
    const std::string& name,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> coneAngle0Limit,
    std::optional<float> coneAngle1Limit
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsSphericalJoint due to an invalid location: %s", reason.c_str());
        return UsdPhysicsSphericalJoint();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return definePhysicsSphericalJoint(stage, path, body0, body1, frame, axis, coneAngle0Limit, coneAngle1Limit);
}

UsdPhysicsSphericalJoint usdex::core::definePhysicsSphericalJoint(
    UsdPrim prim,
    const UsdPrim& body0,
    const UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis,
    std::optional<float> coneAngle0Limit,
    std::optional<float> coneAngle1Limit
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsSphericalJoint on invalid prim");
        return UsdPhysicsSphericalJoint();
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define PhysicsSphericalJoint due to an invalid location: %s", reason.c_str());
        return UsdPhysicsSphericalJoint();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return definePhysicsSphericalJoint(stage, path, body0, body1, frame, axis, coneAngle0Limit, coneAngle1Limit);
}

void usdex::core::alignPhysicsJoint(UsdPhysicsJoint joint, const usdex::core::JointFrame& frame, const GfVec3f& axis)
{
    // Get body0 and body1 assigned from the joint.
    SdfPathVector body0Targets, body1Targets;
    joint.GetBody0Rel().GetTargets(&body0Targets);
    joint.GetBody1Rel().GetTargets(&body1Targets);

    // If no body is assigned, do nothing.
    if (body0Targets.empty() && body1Targets.empty())
    {
        TF_RUNTIME_ERROR("Unable to align PhysicsJoint on invalid joint");
        return;
    }

    const UsdPrim body0 = body0Targets.empty() ? UsdPrim() : joint.GetPrim().GetStage()->GetPrimAtPath(body0Targets[0]);
    const UsdPrim body1 = body1Targets.empty() ? UsdPrim() : joint.GetPrim().GetStage()->GetPrimAtPath(body1Targets[0]);

    if (!body0 && frame.space == usdex::core::JointFrame::Space::Body0)
    {
        TF_RUNTIME_ERROR("Body0 is not specified for PhysicsJoint at \"%s\"", joint.GetPrim().GetPath().GetAsString().c_str());
        return;
    }
    if (!body1 && frame.space == usdex::core::JointFrame::Space::Body1)
    {
        TF_RUNTIME_ERROR("Body1 is not specified for PhysicsJoint at \"%s\"", joint.GetPrim().GetPath().GetAsString().c_str());
        return;
    }

    // Set the physics joint.
    setPhysicsJoint(joint, body0, body1, frame, axis);
}

void usdex::core::connectPhysicsJoint(
    UsdPhysicsJoint joint,
    const pxr::UsdPrim& body0,
    const pxr::UsdPrim& body1,
    const usdex::core::JointFrame& frame,
    const GfVec3f& axis
)
{
    if (!body0 && frame.space == usdex::core::JointFrame::Space::Body0)
    {
        TF_RUNTIME_ERROR("Body0 is not specified for PhysicsJoint at \"%s\"", joint.GetPrim().GetPath().GetAsString().c_str());
        return;
    }
    if (!body1 && frame.space == usdex::core::JointFrame::Space::Body1)
    {
        TF_RUNTIME_ERROR("Body1 is not specified for PhysicsJoint at \"%s\"", joint.GetPrim().GetPath().GetAsString().c_str());
        return;
    }

    const SdfPath path = joint.GetPrim().GetPath();

    if (!body0 && !body1)
    {
        TF_RUNTIME_ERROR("Body0 and Body1 are not specified for PhysicsJoint at \"%s\"", path.GetAsString().c_str());
        return;
    }

    // Specifies the bodies to be connected to the joint.
    if (body0)
    {
        if (!joint.GetBody0Rel().SetTargets(SdfPathVector({ body0.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body0( \"%s\" ) for PhysicsJoint at \"%s\"",
                body0.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return;
        }
    }
    else if (!joint.GetBody0Rel().ClearTargets(true /* removeSpec */))
    {
        TF_RUNTIME_ERROR("Unable to clear body0 relationships for PhysicsJoint at \"%s\"", path.GetAsString().c_str());
        return;
    }

    if (body1)
    {
        if (!joint.GetBody1Rel().SetTargets(SdfPathVector({ body1.GetPath() })))
        {
            TF_RUNTIME_ERROR(
                "Unable to set body1( \"%s\" ) for PhysicsJoint at \"%s\"",
                body1.GetPath().GetAsString().c_str(),
                path.GetAsString().c_str()
            );
            return;
        }
    }
    else if (!joint.GetBody1Rel().ClearTargets(true /* removeSpec */))
    {
        TF_RUNTIME_ERROR("Unable to clear body1 relationships for PhysicsJoint at \"%s\"", path.GetAsString().c_str());
        return;
    }

    // Set the physics joint.
    setPhysicsJoint(joint, body0, body1, frame, axis);
}
