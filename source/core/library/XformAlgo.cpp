// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/XformAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/base/tf/token.h>
#include <pxr/usd/usdGeom/tokens.h>
#include <pxr/usd/usdGeom/xformCommonAPI.h>
#include <pxr/usd/usdGeom/xformOp.h>
#include <pxr/usd/usdGeom/xformable.h>

using namespace pxr;

namespace
{

static const GfRotation g_identityRotation = GfRotation().SetIdentity();
static const GfVec3d g_identityTranslation = GfVec3d(0.0, 0.0, 0.0);


template <class HalfType, class FloatType, class DoubleType, class ValueType>
bool setValueWithPrecision(UsdGeomXformOp& xformOp, const ValueType& value, const UsdTimeCode& time)
{
    switch (xformOp.GetPrecision())
    {
        case UsdGeomXformOp::PrecisionHalf:
        {
            return xformOp.Set(HalfType(FloatType(value)), time);
        }
        case UsdGeomXformOp::PrecisionFloat:
        {
            return xformOp.Set(FloatType(value), time);
        }
        case UsdGeomXformOp::PrecisionDouble:
        {
            return xformOp.Set(DoubleType(value), time);
        }
    }
    return false;
}

UsdGeomXformCommonAPI::RotationOrder convertRotationOrder(const usdex::core::RotationOrder& rotationOrder)
{
    switch (rotationOrder)
    {
        case usdex::core::RotationOrder::eXyz:
            return UsdGeomXformCommonAPI::RotationOrderXYZ;
        case usdex::core::RotationOrder::eXzy:
            return UsdGeomXformCommonAPI::RotationOrderXZY;
        case usdex::core::RotationOrder::eYxz:
            return UsdGeomXformCommonAPI::RotationOrderYXZ;
        case usdex::core::RotationOrder::eYzx:
            return UsdGeomXformCommonAPI::RotationOrderYZX;
        case usdex::core::RotationOrder::eZxy:
            return UsdGeomXformCommonAPI::RotationOrderZXY;
        case usdex::core::RotationOrder::eZyx:
            return UsdGeomXformCommonAPI::RotationOrderZYX;
        default:
            // Default rotation order is XYZ.
            return UsdGeomXformCommonAPI::RotationOrderXYZ;
    }
}

usdex::core::RotationOrder convertRotationOrder(const UsdGeomXformCommonAPI::RotationOrder& rotationOrder)
{
    switch (rotationOrder)
    {
        case UsdGeomXformCommonAPI::RotationOrderXYZ:
            return usdex::core::RotationOrder::eXyz;
        case UsdGeomXformCommonAPI::RotationOrderXZY:
            return usdex::core::RotationOrder::eXzy;
        case UsdGeomXformCommonAPI::RotationOrderYXZ:
            return usdex::core::RotationOrder::eYxz;
        case UsdGeomXformCommonAPI::RotationOrderYZX:
            return usdex::core::RotationOrder::eYzx;
        case UsdGeomXformCommonAPI::RotationOrderZXY:
            return usdex::core::RotationOrder::eZxy;
        case UsdGeomXformCommonAPI::RotationOrderZYX:
            return usdex::core::RotationOrder::eZyx;
        default:
            // Default rotation order is XYZ.
            return usdex::core::RotationOrder::eXyz;
    }
}

GfVec3i getAxisIndices(const usdex::core::RotationOrder& rotationOrder)
{
    switch (rotationOrder)
    {
        case usdex::core::RotationOrder::eXyz:
            return GfVec3i(0, 1, 2);
        case usdex::core::RotationOrder::eXzy:
            return GfVec3i(0, 2, 1);
        case usdex::core::RotationOrder::eYxz:
            return GfVec3i(1, 0, 2);
        case usdex::core::RotationOrder::eYzx:
            return GfVec3i(1, 2, 0);
        case usdex::core::RotationOrder::eZxy:
            return GfVec3i(2, 0, 1);
        case usdex::core::RotationOrder::eZyx:
            return GfVec3i(2, 1, 0);
        default:
            // Default rotation order is XYZ.
            return GfVec3i(0, 1, 2);
    }
}

// Returns true if the transform has a non-identity pivot orientation
bool hasPivotOrientation(const GfTransform& transform)
{
    return transform.GetPivotOrientation() != g_identityRotation;
}

// Returns true if the transform has a non-identity pivot position
bool hasPivotPosition(const GfTransform& transform)
{
    return transform.GetPivotPosition() != g_identityTranslation;
}

// Compute the XYZ rotation values from a Rotation object via decomposition.
GfVec3d computeXyzRotationsFromRotation(const GfRotation& rotate)
{
    const GfVec3d angles = rotate.Decompose(GfVec3d::ZAxis(), GfVec3d::YAxis(), GfVec3d::XAxis());
    return GfVec3d(angles[2], angles[1], angles[0]);
}

GfRotation computeRotation(const GfVec3f& rotations, const usdex::core::RotationOrder rotationOrder)
{
    static const GfVec3d xyzAxes[] = { GfVec3d::XAxis(), GfVec3d::YAxis(), GfVec3d::ZAxis() };
    const GfVec3i indices = getAxisIndices(rotationOrder);

    GfRotation rotation = GfRotation(xyzAxes[indices[0]], rotations[indices[0]]);
    if (rotations[indices[1]] != 0.0)
    {
        rotation = rotation * GfRotation(xyzAxes[indices[1]], rotations[indices[1]]);
    }
    if (rotations[indices[2]] != 0.0)
    {
        rotation = rotation * GfRotation(xyzAxes[indices[2]], rotations[indices[2]]);
    }
    return rotation;
}

GfTransform computeTransformFromComponents(
    const GfVec3d& translation,
    const GfVec3d& pivot,
    const GfVec3f& rotation,
    const usdex::core::RotationOrder rotationOrder,
    const GfVec3f& scale
)
{
    // FUTURE: Refactor this to retain rotations greater than 360 degrees.
    // Right now a rotation greater than 360 will only be retained if it is in the first position and the remaining two are zero
    // otherwise the multiply function will compute a new rotation in a lossy manner.

    // Compute a rotation from the rotation vector and rotation order
    GfRotation rotate = computeRotation(rotation, rotationOrder);

    // Build a transform from the components and computed rotation
    GfTransform transform = GfTransform();
    transform.SetTranslation(translation);
    transform.SetPivotPosition(pivot);
    transform.SetRotation(rotate);
    transform.SetScale(GfVec3d(scale));

    return transform;
}

GfMatrix4d computeMatrixFromComponents(
    const GfVec3d& translation,
    const GfVec3d& pivot,
    const GfVec3f& rotation,
    const usdex::core::RotationOrder rotationOrder,
    const GfVec3f& scale
)
{
    // Build a transform from the components and return it's internal matrix
    const GfTransform transform = computeTransformFromComponents(translation, pivot, rotation, rotationOrder, scale);
    return transform.GetMatrix();
}

// Given a 4x4 matrix compute the values of common components
void computeComponentsFromMatrix(
    const GfMatrix4d& matrix,
    GfVec3d& translation,
    GfVec3d& pivot,
    GfVec3f& rotation,
    usdex::core::RotationOrder& rotationOrder,
    GfVec3f& scale
)
{
    // Get the components from the transform and cast to the expected precision
    const GfTransform transform = GfTransform(matrix);
    translation = transform.GetTranslation();
    pivot = transform.GetPivotPosition();

    // Decompose rotation into a rotationOrder of XYZ and convert from double to float
    rotation = GfVec3f(computeXyzRotationsFromRotation(transform.GetRotation()));
    rotationOrder = usdex::core::RotationOrder::eXyz;

    // Convert scale from double to float
    scale = GfVec3f(transform.GetScale());
}

// Given a 4x4 matrix compute the values of common components with orientation instead of rotation
void computeComponentsFromMatrix(const GfMatrix4d& matrix, GfVec3d& translation, GfVec3d& pivot, GfQuatf& orientation, GfVec3f& scale)
{
    // Get the components from the transform
    const GfTransform transform = GfTransform(matrix);
    translation = transform.GetTranslation();
    pivot = transform.GetPivotPosition();
    orientation = GfQuatf(transform.GetRotation().GetQuat());
    scale = GfVec3f(transform.GetScale());
}

// Overloaded version of UsdGeomXformCommonAPI::GetXformVectorsByAccumulation which treats pivot as a double
void getXformVectorsByAccumulation(
    const UsdGeomXformCommonAPI& xformCommonAPI,
    GfVec3d* translation,
    GfVec3d* pivot,
    GfVec3f* rotation,
    usdex::core::RotationOrder* rotationOrder,
    GfVec3f* scale,
    const UsdTimeCode time
)
{
    // Get the xform vectors in the types expected by the xformCommonAPI
    GfVec3f pivotFloat;
    UsdGeomXformCommonAPI::RotationOrder rotOrder;
    xformCommonAPI.GetXformVectors(translation, rotation, scale, &pivotFloat, &rotOrder, time);

    // Convert types to those expected by usdex_core
    pivot->Set(pivotFloat[0], pivotFloat[1], pivotFloat[2]);
    *rotationOrder = convertRotationOrder(rotOrder);
}

// Overloaded version of UsdGeomXformCommonAPI::GetXformVectorsByAccumulation which treats pivot as a double with quaternion orientation
void getXformVectorsByAccumulation(
    const UsdGeomXformCommonAPI& xformCommonAPI,
    GfVec3d* translation,
    GfVec3d* pivot,
    GfQuatf* orientation,
    GfVec3f* scale,
    const UsdTimeCode time
)
{
    // Get the xform vectors in the types expected by the xformCommonAPI
    GfVec3f pivotFloat;
    GfVec3f rotation;
    UsdGeomXformCommonAPI::RotationOrder rotOrder;
    xformCommonAPI.GetXformVectors(translation, &rotation, scale, &pivotFloat, &rotOrder, time);

    // Convert pivot to double
    pivot->Set(pivotFloat[0], pivotFloat[1], pivotFloat[2]);

    // Convert rotation to quaternion
    GfRotation rot = computeRotation(rotation, convertRotationOrder(rotOrder));
    *orientation = GfQuatf(rot.GetQuat());
}

// Returns whether the authored xformOps are compatible with a matrix value
// The "transformOp" argument will be populated with the existing xformOp if one is authored
bool getMatrixXformOp(const std::vector<UsdGeomXformOp>& xformOps, UsdGeomXformOp* transformOp)
{
    // If there are no existing xformOps then it is compatible
    if (xformOps.empty())
    {
        return true;
    }

    // If there is more than one xformOp then it is not compatible
    if (xformOps.size() > 1)
    {
        return false;
    }

    // The xformOp it must be of type transform but not and inverse op to be compatible
    if (xformOps[0].GetOpType() == UsdGeomXformOp::TypeTransform && !xformOps[0].IsInverseOp())
    {
        *transformOp = std::move(xformOps[0]);
        return true;
    }

    return false;
}

// Ensure that there is an opinion about the xformOpOrder value in the current edit target layer
void ensureXformOpOrderExplicitlyAuthored(UsdGeomXformable& xformable)
{
    UsdAttribute attr = xformable.GetXformOpOrderAttr();
    SdfLayerHandle layer = xformable.GetPrim().GetStage()->GetEditTarget().GetLayer();

    if (!layer->HasSpec(attr.GetPath()))
    {
        VtArray<TfToken> value;
        if (attr.Get(&value))
        {
            attr.Set(value);
        }
    }
}

// Remove all unused xformOps from a prim
void removeUnusedXformOps(UsdGeomXformable& xformable)
{
    UsdPrim prim = xformable.GetPrim();

    bool resetsXformStack;
    std::vector<UsdGeomXformOp> usedXformOps = xformable.GetOrderedXformOps(&resetsXformStack);

    // Get all authored property names and remove xformOp properties
    std::vector<TfToken> propertiesToRemove;
    for (const TfToken& propName : prim.GetAuthoredPropertyNames())
    {
        // Remove all xformOp properties (those starting with "xformOp:")
        if (UsdGeomXformOp::IsXformOp(propName))
        {
            // Check if this xformOp is in the usedXformOps list
            bool isUsed = false;
            for (const UsdGeomXformOp& usedOp : usedXformOps)
            {
                if (usedOp.GetName() == propName)
                {
                    isUsed = true;
                    break;
                }
            }

            // Only add to removal list if not used
            if (!isUsed)
            {
                propertiesToRemove.push_back(propName);
            }
        }
    }

    // Remove the collected properties
    for (const TfToken& propName : propertiesToRemove)
    {
        prim.RemoveProperty(propName);
    }
}


} // namespace

bool usdex::core::setLocalTransform(UsdPrim prim, const GfTransform& transform, UsdTimeCode time)
{
    // Early out with a failure return if the prim is not xformable
    UsdGeomXformable xformable(prim);
    if (!xformable)
    {
        return false;
    }

    // Assuming there is no existing compatible xformOpOrder inspect the transform to identify the most expressive xformOpOrder to use.
    // For performance reasons we want to use a single transform xformOp. See: https://groups.google.com/g/usd-interest/c/MR5DFhQEYSE/m/o7bSnWwNAgAJ

    // However we would ideally retain pivot position so if authored prefer the XformCommonAPI.
    // The XformCommonAPI cannot express pivotOrientation so if it has a non-identity value we need to use a transform xformOp.
    bool needsXformCommonAPI = (hasPivotPosition(transform) && !hasPivotOrientation(transform));

    // Get the existing xformOps and attempt to reuse them if compatible
    bool resetsXformStack;
    std::vector<UsdGeomXformOp> xformOps = xformable.GetOrderedXformOps(&resetsXformStack);
    if (!xformOps.empty())
    {
        // Only try to reuse the matrix xform op if the transform does not need the xformCommonAPI to express it's value
        if (!needsXformCommonAPI)
        {
            // Set the value on an existing transform xformOp if one is already authored
            UsdGeomXformOp transformXformOp;
            if (getMatrixXformOp(xformOps, &transformXformOp) && transformXformOp.IsDefined())
            {
                const GfMatrix4d matrix = transform.GetMatrix();
                transformXformOp.Set(matrix, time);
                ensureXformOpOrderExplicitlyAuthored(xformable);

                return true;
            }
        }

        // FUTURE: Attempt to reuse existing UsdGeomXformCommonAPI xformOps
    }

    // Author using UsdGeomXformCommonAPI if appropriate
    if (needsXformCommonAPI)
    {
        // Modify the xformOpOrder and set xformOp values to achieve the transform
        if (!UsdGeomXformCommonAPI(prim))
        {
            xformable.ClearXformOpOrder();
        }

        const GfVec3d rotation = computeXyzRotationsFromRotation(transform.GetRotation());

        // Get or create the UsdGeomXformCommonAPI xformOps
        UsdGeomXformCommonAPI xformCommonAPI = UsdGeomXformCommonAPI(prim);
        UsdGeomXformCommonAPI::Ops commonXformOps = xformCommonAPI.CreateXformOps(
            UsdGeomXformCommonAPI::RotationOrderXYZ,
            UsdGeomXformCommonAPI::OpTranslate,
            UsdGeomXformCommonAPI::OpPivot,
            UsdGeomXformCommonAPI::OpRotate,
            UsdGeomXformCommonAPI::OpScale
        );

        // Set the UsdGeomXformCommonAPI xformOp values allowing setValueWithPrecision to handle any value type conversions
        setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3d>(commonXformOps.translateOp, transform.GetTranslation(), time);
        setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3d>(commonXformOps.pivotOp, transform.GetPivotPosition(), time);
        setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3d>(commonXformOps.rotateOp, rotation, time);
        setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3d>(commonXformOps.scaleOp, transform.GetScale(), time);
        ensureXformOpOrderExplicitlyAuthored(xformable);

        return true;
    }

    // Modify the xformOpOrder and set xformOp values to achieve the transform
    const GfMatrix4d matrix = transform.GetMatrix();
    UsdGeomXformOp transformXformOp = xformable.MakeMatrixXform();
    transformXformOp.Set(matrix, time);
    ensureXformOpOrderExplicitlyAuthored(xformable);

    return true;
}

bool usdex::core::setLocalTransform(UsdPrim prim, const GfMatrix4d& matrix, UsdTimeCode time)
{
    // Early out with a failure return if the prim is not xformable
    UsdGeomXformable xformable(prim);
    if (!xformable)
    {
        return false;
    }

    // Get the existing xformOps and attempt to reuse them if compatible
    bool resetsXformStack;
    std::vector<UsdGeomXformOp> xformOps = xformable.GetOrderedXformOps(&resetsXformStack);
    if (!xformOps.empty())
    {
        // Set the value on an existing transform xformOp if one is already authored
        UsdGeomXformOp transformXformOp;
        if (getMatrixXformOp(xformOps, &transformXformOp) && transformXformOp.IsDefined())
        {
            transformXformOp.Set(matrix, time);
            ensureXformOpOrderExplicitlyAuthored(xformable);

            return true;
        }

        // FUTURE: Attempt to reuse existing UsdGeomXformCommonAPI xformOps
    }

    // Assuming there is no existing compatible xformOpOrder
    // Modify the xformOpOrder to use the most expressive xformOp stack and set xformOp values to achieve the transform
    UsdGeomXformOp transformXformOp = xformable.MakeMatrixXform();
    transformXformOp.Set(matrix, time);
    ensureXformOpOrderExplicitlyAuthored(xformable);

    return true;
}

bool usdex::core::setLocalTransform(
    UsdPrim prim,
    const GfVec3d& translation,
    const GfVec3d& pivot,
    const GfVec3f& rotation,
    const usdex::core::RotationOrder rotationOrder,
    const GfVec3f& scale,
    UsdTimeCode time
)
{
    // Early out with a failure return if the prim is not xformable
    UsdGeomXformable xformable(prim);
    if (!xformable)
    {
        return false;
    }

    // We would ideally retain pivot position so if it is non-identity prefer the XformCommonAPI.
    bool needsXformCommonAPI = (pivot != g_identityTranslation);

    // Get the existing xformOps and attempt to reuse them if compatible
    bool resetsXformStack;
    std::vector<UsdGeomXformOp> xformOps = xformable.GetOrderedXformOps(&resetsXformStack);
    if (!xformOps.empty())
    {
        // Only try to reuse the matrix xform op if the transform does not need the xformCommonAPI to express it's value
        if (!needsXformCommonAPI)
        {
            // Set the value on an existing transform xformOp if one is already authored
            UsdGeomXformOp transformXformOp;
            if (getMatrixXformOp(xformOps, &transformXformOp) && transformXformOp.IsDefined())
            {
                const GfMatrix4d matrix = computeMatrixFromComponents(translation, pivot, rotation, rotationOrder, scale);
                transformXformOp.Set(matrix, time);
                ensureXformOpOrderExplicitlyAuthored(xformable);

                return true;
            }
        }

        // FUTURE: Attempt to reuse existing UsdGeomXformCommonAPI xformOps
    }

    // Modify the xformOpOrder and set xformOp values to achieve the transform
    if (!UsdGeomXformCommonAPI(prim))
    {
        xformable.ClearXformOpOrder();
    }

    const UsdGeomXformCommonAPI::RotationOrder rotationOrderEnum = convertRotationOrder(rotationOrder);

    // Get or create the UsdGeomXformCommonAPI xformOps
    UsdGeomXformCommonAPI xformCommonAPI = UsdGeomXformCommonAPI(prim);
    UsdGeomXformCommonAPI::Ops commonXformOps = xformCommonAPI.CreateXformOps(
        rotationOrderEnum,
        UsdGeomXformCommonAPI::OpTranslate,
        UsdGeomXformCommonAPI::OpPivot,
        UsdGeomXformCommonAPI::OpRotate,
        UsdGeomXformCommonAPI::OpScale
    );

    // Set the UsdGeomXformCommonAPI xformOp values allowing setValueWithPrecision to handle any value type conversions
    setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3d>(commonXformOps.translateOp, translation, time);
    setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3d>(commonXformOps.pivotOp, pivot, time);
    setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3f>(commonXformOps.rotateOp, rotation, time);
    setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3f>(commonXformOps.scaleOp, scale, time);

    removeUnusedXformOps(xformable);
    ensureXformOpOrderExplicitlyAuthored(xformable);

    return true;
}

bool usdex::core::setLocalTransform(UsdPrim prim, const GfVec3d& translation, const GfQuatf& orientation, const GfVec3f& scale, UsdTimeCode time)
{
    UsdGeomXformable xformable(prim);
    if (!xformable)
    {
        return false;
    }

    // Get existing xformOps
    bool resetsXformStack;
    std::vector<UsdGeomXformOp> xformOps = xformable.GetOrderedXformOps(&resetsXformStack);

    // Map to store existing ops by type and name
    std::map<std::pair<UsdGeomXformOp::Type, TfToken>, UsdGeomXformOp> existingOps;
    for (const UsdGeomXformOp& op : xformOps)
    {
        if (!op.IsInverseOp())
        {
            existingOps[std::make_pair(op.GetOpType(), op.GetName())] = op;
        }
    }

    // Clear xformOpOrder and xformOps to rebuild it
    xformable.ClearXformOpOrder();

    static const std::string xformNamespace("xformOp:");
    std::vector<UsdGeomXformOp> newXformOps;

    // 1. Translation
    static const std::string translateOpNameString(xformNamespace + UsdGeomXformOp::GetOpTypeToken(UsdGeomXformOp::TypeTranslate).GetString());
    static const TfToken translateOpName(translateOpNameString);
    auto translateIt = existingOps.find(std::make_pair(UsdGeomXformOp::TypeTranslate, translateOpName));
    if (translateIt != existingOps.end())
    {
        newXformOps.push_back(translateIt->second);
        setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3d>(translateIt->second, translation, time);
    }
    else
    {
        newXformOps.push_back(xformable.AddTranslateOp());
        newXformOps.back().Set(translation, time);
    }

    // 2. Orientation
    static const std::string orientOpNameString(xformNamespace + UsdGeomXformOp::GetOpTypeToken(UsdGeomXformOp::TypeOrient).GetString());
    static const TfToken orientOpName(orientOpNameString);
    auto orientIt = existingOps.find(std::make_pair(UsdGeomXformOp::TypeOrient, orientOpName));
    if (orientIt != existingOps.end())
    {
        newXformOps.push_back(orientIt->second);
        setValueWithPrecision<GfQuath, GfQuatf, GfQuatd, GfQuatf>(orientIt->second, orientation, time);
    }
    else
    {
        newXformOps.push_back(xformable.AddOrientOp());
        newXformOps.back().Set(orientation, time);
    }

    // 3. Scale
    static const std::string scaleOpNameString(xformNamespace + UsdGeomXformOp::GetOpTypeToken(UsdGeomXformOp::TypeScale).GetString());
    static const TfToken scaleOpName(scaleOpNameString);
    auto scaleIt = existingOps.find(std::make_pair(UsdGeomXformOp::TypeScale, scaleOpName));
    if (scaleIt != existingOps.end())
    {
        newXformOps.push_back(scaleIt->second);
        setValueWithPrecision<GfVec3h, GfVec3f, GfVec3d, GfVec3f>(scaleIt->second, scale, time);
    }
    else
    {
        newXformOps.push_back(xformable.AddScaleOp());
        newXformOps.back().Set(scale, time);
    }

    // Set the xform op order
    xformable.SetXformOpOrder(newXformOps);
    removeUnusedXformOps(xformable);
    ensureXformOpOrderExplicitlyAuthored(xformable);
    return true;
}

GfTransform usdex::core::getLocalTransform(const UsdPrim& prim, UsdTimeCode time)
{
    // Initialize an identity transform as the fallback return
    GfTransform transform = GfTransform();

    // Early out if the prim is not xformable
    UsdGeomXformable xformable(prim);
    if (!xformable)
    {
        return transform;
    }

    // Attempt to extract existing xformOp values
    UsdGeomXformCommonAPI xformCommonAPI = UsdGeomXformCommonAPI(prim);
    if (xformCommonAPI)
    {
        // Extract transform components
        GfVec3d translation;
        GfVec3d pivot;
        GfVec3f rotation;
        usdex::core::RotationOrder rotOrder;
        GfVec3f scale;
        getXformVectorsByAccumulation(xformCommonAPI, &translation, &pivot, &rotation, &rotOrder, &scale, time);

        // Construct and return a transform from the components
        return computeTransformFromComponents(translation, pivot, rotation, rotOrder, scale);
    }

    // Compute the local transform matrix and populate the result from that
    GfMatrix4d matrix;
    bool resetsXformStack;
    if (xformable.GetLocalTransformation(&matrix, &resetsXformStack, time))
    {
        transform.SetMatrix(matrix);
    }

    return transform;
}

GfMatrix4d usdex::core::getLocalTransformMatrix(const UsdPrim& prim, UsdTimeCode time)
{
    // Initialize an identity matrix as the fallback return
    GfMatrix4d matrix = GfMatrix4d(1.0);

    // Early out if the prim is not xformable
    UsdGeomXformable xformable(prim);
    if (!xformable)
    {
        return matrix;
    }

    // Compute the local transform matrix and populate the result from that
    bool resetsXformStack;
    if (!xformable.GetLocalTransformation(&matrix, &resetsXformStack, time))
    {
        matrix.SetIdentity();
    }

    return matrix;
}

void usdex::core::getLocalTransformComponents(
    const UsdPrim& prim,
    GfVec3d& translation,
    GfVec3d& pivot,
    GfVec3f& rotation,
    usdex::core::RotationOrder& rotationOrder,
    GfVec3f& scale,
    UsdTimeCode time
)
{
    // Initialize as identity
    translation.Set(0.0, 0.0, 0.0);
    pivot.Set(0.0, 0.0, 0.0);
    rotation.Set(0.0, 0.0, 0.0);
    rotationOrder = usdex::core::RotationOrder::eXyz;
    scale.Set(1.0, 1.0, 1.0);

    // Early out if the prim is not xformable
    UsdGeomXformable xformable(prim);
    if (!xformable)
    {
        return;
    }

    // Attempt to extract existing xformOp values
    UsdGeomXformCommonAPI xformCommonAPI = UsdGeomXformCommonAPI(prim);
    if (xformCommonAPI)
    {
        // Extract transform components
        getXformVectorsByAccumulation(xformCommonAPI, &translation, &pivot, &rotation, &rotationOrder, &scale, time);
        return;
    }

    // Compute the local transform matrix and populate the result from that
    GfMatrix4d matrix;
    bool resetsXformStack;
    if (xformable.GetLocalTransformation(&matrix, &resetsXformStack, time))
    {
        computeComponentsFromMatrix(matrix, translation, pivot, rotation, rotationOrder, scale);
        return;
    }
}

void usdex::core::getLocalTransformComponentsQuat(
    const UsdPrim& prim,
    GfVec3d& translation,
    GfVec3d& pivot,
    GfQuatf& orientation,
    GfVec3f& scale,
    UsdTimeCode time
)
{
    // Initialize with identity values
    translation.Set(0.0, 0.0, 0.0);
    pivot.Set(0.0, 0.0, 0.0);
    orientation = GfQuatf::GetIdentity();
    scale.Set(1.0, 1.0, 1.0);

    UsdGeomXformable xformable(prim);
    if (!xformable)
    {
        return;
    }

    // Attempt to extract existing xformOp values using XformCommonAPI
    UsdGeomXformCommonAPI xformCommonAPI = UsdGeomXformCommonAPI(prim);
    if (xformCommonAPI)
    {
        // Extract transform components
        getXformVectorsByAccumulation(xformCommonAPI, &translation, &pivot, &orientation, &scale, time);
        return;
    }

    // If XformCommonAPI doesn't work, try to extract from individual xformOps
    bool resetsXformStack;
    std::vector<UsdGeomXformOp> xformOps = xformable.GetOrderedXformOps(&resetsXformStack);
    bool foundOrientationOp = false;

    // Check for matrix xformOp first
    UsdGeomXformOp matrixXformOp;
    if (getMatrixXformOp(xformOps, &matrixXformOp) && matrixXformOp.IsDefined())
    {
        GfMatrix4d matrix;
        if (matrixXformOp.Get(&matrix, time))
        {
            computeComponentsFromMatrix(matrix, translation, pivot, orientation, scale);
            return;
        }
    }

    // Process each xform op
    for (const UsdGeomXformOp& op : xformOps)
    {
        if (op.IsInverseOp())
        {
            continue;
        }

        switch (op.GetOpType())
        {
            case UsdGeomXformOp::TypeTranslate:
            {
                GfVec3d value;
                if (op.Get(&value, time))
                {
                    // Check if this is a pivot op by looking for the pivot suffix
                    if (op.HasSuffix(UsdGeomTokens->pivot))
                    {
                        pivot = value;
                    }
                    else
                    {
                        translation = value;
                    }
                }
                break;
            }
            case UsdGeomXformOp::TypeOrient:
            {
                GfQuatf value;
                if (op.Get(&value, time))
                {
                    orientation = value;
                    foundOrientationOp = true;
                }
                break;
            }
            case UsdGeomXformOp::TypeScale:
            {
                GfVec3f value;
                if (op.Get(&value, time))
                {
                    scale = value;
                }
                break;
            }
            default:
                break;
        }
    }

    // If we didn't find an orientation xformOp, try to compute it from the matrix
    if (!foundOrientationOp)
    {
        GfMatrix4d matrix;
        if (xformable.GetLocalTransformation(&matrix, &resetsXformStack, time))
        {
            GfTransform transform;
            transform.SetMatrix(matrix);
            orientation = GfQuatf(transform.GetRotation().GetQuat());
        }
    }
}

UsdGeomXform usdex::core::defineXform(UsdStagePtr stage, const SdfPath& path, std::optional<const pxr::GfTransform> transform)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomXform due to an invalid location: %s", reason.c_str());
        return UsdGeomXform();
    }

    // Define the Xform and check that this was successful
    UsdGeomXform xform = UsdGeomXform::Define(stage, path);
    if (!xform)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomXform at \"%s\"", path.GetAsString().c_str());
        return UsdGeomXform();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = xform.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Set the local transform if one was supplied
    if (transform.has_value())
    {
        usdex::core::setLocalTransform(prim, transform.value(), UsdTimeCode::Default());
    }

    return xform;
}

UsdGeomXform usdex::core::defineXform(UsdPrim parent, const std::string& name, std::optional<const pxr::GfTransform> transform)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomXform due to an invalid location: %s", reason.c_str());
        return UsdGeomXform();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineXform(stage, path, transform);
}

UsdGeomXform usdex::core::defineXform(UsdPrim prim, std::optional<const pxr::GfTransform> transform)
{
    // Early out if the prim is invalid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomXform due to an invalid prim");
        return UsdGeomXform();
    }

    // Warn if original prim is not Scope or Xform
    TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Xform\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::defineXform(stage, path, transform);
}

UsdGeomXform usdex::core::defineXform(UsdStagePtr stage, const SdfPath& path, const pxr::GfMatrix4d& matrix)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomXform due to an invalid location: %s", reason.c_str());
        return UsdGeomXform();
    }

    // Define the Xform and check that this was successful
    UsdGeomXform xform = UsdGeomXform::Define(stage, path);
    if (!xform)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomXform at \"%s\"", path.GetAsString().c_str());
        return UsdGeomXform();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = xform.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Set the local transform if one was supplied
    usdex::core::setLocalTransform(prim, matrix, UsdTimeCode::Default());

    return xform;
}

UsdGeomXform usdex::core::defineXform(UsdPrim parent, const std::string& name, const pxr::GfMatrix4d& matrix)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomXform due to an invalid location: %s", reason.c_str());
        return UsdGeomXform();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineXform(stage, path, matrix);
}

UsdGeomXform usdex::core::defineXform(UsdPrim prim, const pxr::GfMatrix4d& matrix)
{
    // Early out if the prim is invalid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdGeomXform due to an invalid prim");
        return UsdGeomXform();
    }

    // Warn if original prim is not Scope or Xform
    TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Xform\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::defineXform(stage, path, matrix);
}

bool usdex::core::setLocalTransform(const UsdGeomXformable& xformable, const GfTransform& transform, UsdTimeCode time)
{
    if (!xformable)
    {
        TF_RUNTIME_ERROR("UsdGeomXformable <%s> is not valid.", xformable.GetPrim().GetPath().GetAsString().c_str());
        return false;
    }

    return setLocalTransform(xformable.GetPrim(), transform, time);
}

bool usdex::core::setLocalTransform(const UsdGeomXformable& xformable, const GfMatrix4d& matrix, UsdTimeCode time)
{
    if (!xformable)
    {
        TF_RUNTIME_ERROR("UsdGeomXformable <%s> is not valid.", xformable.GetPrim().GetPath().GetAsString().c_str());
        return false;
    }

    return setLocalTransform(xformable.GetPrim(), matrix, time);
}

bool usdex::core::setLocalTransform(
    const UsdGeomXformable& xformable,
    const GfVec3d& translation,
    const GfVec3d& pivot,
    const GfVec3f& rotation,
    const usdex::core::RotationOrder rotationOrder,
    const GfVec3f& scale,
    UsdTimeCode time
)
{
    if (!xformable)
    {
        TF_RUNTIME_ERROR("UsdGeomXformable <%s> is not valid.", xformable.GetPrim().GetPath().GetAsString().c_str());
        return false;
    }

    return setLocalTransform(xformable.GetPrim(), translation, pivot, rotation, rotationOrder, scale, time);
}

bool usdex::core::setLocalTransform(
    const UsdGeomXformable& xformable,
    const GfVec3d& translation,
    const GfQuatf& orientation,
    const GfVec3f& scale,
    UsdTimeCode time
)
{
    if (!xformable)
    {
        TF_RUNTIME_ERROR("UsdGeomXformable <%s> is not valid.", xformable.GetPrim().GetPath().GetAsString().c_str());
        return false;
    }

    return setLocalTransform(xformable.GetPrim(), translation, orientation, scale, time);
}

GfTransform usdex::core::getLocalTransform(const UsdGeomXformable& xformable, UsdTimeCode time)
{
    if (!xformable)
    {
        TF_RUNTIME_ERROR("UsdGeomXformable <%s> is not valid.", xformable.GetPrim().GetPath().GetAsString().c_str());
        return GfTransform();
    }

    return getLocalTransform(xformable.GetPrim(), time);
}

GfMatrix4d usdex::core::getLocalTransformMatrix(const UsdGeomXformable& xformable, UsdTimeCode time)
{
    if (!xformable)
    {
        TF_RUNTIME_ERROR("UsdGeomXformable <%s> is not valid.", xformable.GetPrim().GetPath().GetAsString().c_str());
        return GfMatrix4d(1.0);
    }

    return getLocalTransformMatrix(xformable.GetPrim(), time);
}

void usdex::core::getLocalTransformComponents(
    const UsdGeomXformable& xformable,
    GfVec3d& translation,
    GfVec3d& pivot,
    GfVec3f& rotation,
    usdex::core::RotationOrder& rotationOrder,
    GfVec3f& scale,
    UsdTimeCode time
)
{
    if (!xformable)
    {
        TF_RUNTIME_ERROR("UsdGeomXformable <%s> is not valid.", xformable.GetPrim().GetPath().GetAsString().c_str());
        // Set identity values and return
        translation.Set(0.0, 0.0, 0.0);
        pivot.Set(0.0, 0.0, 0.0);
        rotation.Set(0.0, 0.0, 0.0);
        rotationOrder = usdex::core::RotationOrder::eXyz;
        scale.Set(1.0, 1.0, 1.0);
        return;
    }

    getLocalTransformComponents(xformable.GetPrim(), translation, pivot, rotation, rotationOrder, scale, time);
}

void usdex::core::getLocalTransformComponentsQuat(
    const UsdGeomXformable& xformable,
    GfVec3d& translation,
    GfVec3d& pivot,
    GfQuatf& orientation,
    GfVec3f& scale,
    UsdTimeCode time
)
{
    if (!xformable)
    {
        TF_RUNTIME_ERROR("UsdGeomXformable <%s> is not valid.", xformable.GetPrim().GetPath().GetAsString().c_str());
        // Set identity values and return
        translation.Set(0.0, 0.0, 0.0);
        pivot.Set(0.0, 0.0, 0.0);
        orientation = GfQuatf::GetIdentity();
        scale.Set(1.0, 1.0, 1.0);
        return;
    }

    getLocalTransformComponentsQuat(xformable.GetPrim(), translation, pivot, orientation, scale, time);
}
