// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/core/XformAlgo.h
//! @brief Utility functions to manipulate 3D transformation data on `UsdGeomXformable` Prims.

#include "Api.h"

#include <pxr/base/gf/matrix4d.h>
#include <pxr/base/gf/transform.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usd/timeCode.h>
#include <pxr/usd/usdGeom/xform.h>

#include <optional>
#include <string>


namespace usdex::core
{

//! @defgroup xformable 3D Transformations
//!
//! Utility functions to manipulate 3D transformation data on `UsdGeomXformable` Prims.
//!
//! The [UsdGeomXformable](https://openusd.org/release/api/usd_geom_page_front.html#UsdGeom_Xformable) schema supports a rich set of transform
//! operations from which a resulting matrix can be computed.
//!
//! The flexibility of this system adds complexity to the code required for authoring and retrieving transform information. This module provides
//! functions for authoring and retrieving transformation using a standard suite of transform formats.
//!
//! The goal of these functions is to decouple the caller's preferred transform format from the format in which the transform is stored on the
//! `UsdPrim`. This is accomplished by internally converting between formats as needed, and modifing the storage format when required.
//!
//! # Getting Transforms #
//!
//! The `getLocalTransform` functions will retrieve the local transform of a `UsdPrim` in the format requested.
//! - If the existing [UsdGeomXformOps](https://openusd.org/release/api/class_usd_geom_xform_op.html) can be mapped to the requested format,
//!   then the components will be populated with the values authored.
//! - If there is no clear mapping, then a local transformation matrix will be computed, and the components extracted from that.
//!
//! # Setting Transforms #
//!
//! The `setLocalTransform` functions will set the values of existing `UsdGeomXformOps` on a `UsdPrim` to achieve the transform supplied.
//! - If the given format can be mapped to the existing `UsdGeomXformOps`, or have mappable values extracted, then the values of those will be set.
//! - If the given format (or the value it holds) cannot be mapped to the existing `UsdGeomXformOps`, then new operations will be authored that can.
//! - If no `UsdGeomXformOps` exist, then new ones matching the format will be authored.
//!
//! When a value is set at a given time, all existing time samples will be maintained, even in cases where the operations were changed.
//!
//! @{

//! Enumerates the rotation order of the 3-angle Euler rotation.
enum class RotationOrder
{
    eXyz,
    eXzy,
    eYxz,
    eYzx,
    eZxy,
    eZyx
};

//! Set the local transform of a prim.
//!
//! @param prim The prim to set local transform on.
//! @param transform The transform value to set.
//! @param time Time at which to write the value.
//! @returns A bool indicating if the local transform was set.
USDEX_API bool setLocalTransform(pxr::UsdPrim prim, const pxr::GfTransform& transform, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

//! Set the local transform of an xformable.
//!
//! @param xformable The xformable to set local transform on.
//! @param transform The transform value to set.
//! @param time Time at which to write the value.
//! @returns A bool indicating if the local transform was set.
USDEX_API bool setLocalTransform(
    const pxr::UsdGeomXformable& xformable,
    const pxr::GfTransform& transform,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Set the local transform of a prim from a 4x4 matrix.
//!
//! @param prim The prim to set local transform on.
//! @param matrix The matrix value to set.
//! @param time Time at which to write the value.
//! @returns A bool indicating if the local transform was set.
USDEX_API bool setLocalTransform(pxr::UsdPrim prim, const pxr::GfMatrix4d& matrix, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

//! Set the local transform of an xformable from a 4x4 matrix.
//!
//! @param xformable The xformable to set local transform on.
//! @param matrix The matrix value to set.
//! @param time Time at which to write the value.
//! @returns A bool indicating if the local transform was set.
USDEX_API bool setLocalTransform(
    const pxr::UsdGeomXformable& xformable,
    const pxr::GfMatrix4d& matrix,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Set the local transform of a prim from common transform components.
//!
//! @param prim The prim to set local transform on.
//! @param translation The translation value to set.
//! @param pivot The pivot position value to set.
//! @param rotation The rotation value to set in degrees.
//! @param rotationOrder The rotation order of the rotation value.
//! @param scale The scale value to set.
//! @param time Time at which to write the values.
//! @returns True if the transform was set successfully.
USDEX_API bool setLocalTransform(
    pxr::UsdPrim prim,
    const pxr::GfVec3d& translation,
    const pxr::GfVec3d& pivot,
    const pxr::GfVec3f& rotation,
    const RotationOrder rotationOrder,
    const pxr::GfVec3f& scale,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Set the local transform of an xformable from common transform components.
//!
//! @param xformable The xformable to set local transform on.
//! @param translation The translation value to set.
//! @param pivot The pivot position value to set.
//! @param rotation The rotation value to set in degrees.
//! @param rotationOrder The rotation order of the rotation value.
//! @param scale The scale value to set.
//! @param time Time at which to write the values.
//! @returns True if the transform was set successfully.
USDEX_API bool setLocalTransform(
    const pxr::UsdGeomXformable& xformable,
    const pxr::GfVec3d& translation,
    const pxr::GfVec3d& pivot,
    const pxr::GfVec3f& rotation,
    const RotationOrder rotationOrder,
    const pxr::GfVec3f& scale,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Set the local transform of a prim from common transform components using a quaternion for orientation.
//!
//! @param prim The prim to set local transform on.
//! @param translation The translation value to set.
//! @param orientation The orientation value to set as a quaternion.
//! @param scale The scale value to set - defaults to (1.0, 1.0, 1.0).
//! @param time Time at which to write the values.
//! @returns True if the transform was set successfully.
USDEX_API bool setLocalTransform(
    pxr::UsdPrim prim,
    const pxr::GfVec3d& translation,
    const pxr::GfQuatf& orientation,
    const pxr::GfVec3f& scale = pxr::GfVec3f(1.0f, 1.0f, 1.0f),
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Set the local transform of an xformable from common transform components using a quaternion for orientation.
//!
//! @param xformable The xformable to set local transform on.
//! @param translation The translation value to set.
//! @param orientation The orientation value to set as a quaternion.
//! @param scale The scale value to set - defaults to (1.0, 1.0, 1.0).
//! @param time Time at which to write the values.
//! @returns True if the transform was set successfully.
USDEX_API bool setLocalTransform(
    const pxr::UsdGeomXformable& xformable,
    const pxr::GfVec3d& translation,
    const pxr::GfQuatf& orientation,
    const pxr::GfVec3f& scale = pxr::GfVec3f(1.0f, 1.0f, 1.0f),
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Get the local transform of a prim at a given time.
//!
//! @param prim The prim to get local transform from.
//! @param time Time at which to query the value.
//! @returns Transform value as a transform.
USDEX_API pxr::GfTransform getLocalTransform(const pxr::UsdPrim& prim, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

//! Get the local transform of an xformable at a given time.
//!
//! @param xformable The xformable to get local transform from.
//! @param time Time at which to query the value.
//! @returns Transform value as a transform.
USDEX_API pxr::GfTransform getLocalTransform(const pxr::UsdGeomXformable& xformable, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

//! Get the local transform of a prim at a given time in the form of a 4x4 matrix.
//!
//! @param prim The prim to get local transform from.
//! @param time Time at which to query the value.
//! @returns Transform value as a 4x4 matrix.
USDEX_API pxr::GfMatrix4d getLocalTransformMatrix(const pxr::UsdPrim& prim, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

//! Get the local transform of an xformable at a given time in the form of a 4x4 matrix.
//!
//! @param xformable The xformable to get local transform from.
//! @param time Time at which to query the value.
//! @returns Transform value as a 4x4 matrix.
USDEX_API pxr::GfMatrix4d getLocalTransformMatrix(const pxr::UsdGeomXformable& xformable, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

//! Get the local transform of a prim at a given time in the form of common transform components.
//!
//! @param prim The prim to get local transform from.
//! @param translation Translation result.
//! @param pivot Pivot position result.
//! @param rotation Rotation result in degrees.
//! @param rotationOrder Rotation order the rotation result.
//! @param scale Scale result.
//! @param time Time at which to query the value.
//! @returns `void`
USDEX_API void getLocalTransformComponents(
    const pxr::UsdPrim& prim,
    pxr::GfVec3d& translation,
    pxr::GfVec3d& pivot,
    pxr::GfVec3f& rotation,
    RotationOrder& rotationOrder,
    pxr::GfVec3f& scale,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Get the local transform of an xformable at a given time in the form of common transform components.
//!
//! @param xformable The xformable to get local transform from.
//! @param translation Translation result.
//! @param pivot Pivot position result.
//! @param rotation Rotation result in degrees.
//! @param rotationOrder Rotation order the rotation result.
//! @param scale Scale result.
//! @param time Time at which to query the value.
//! @returns `void`
USDEX_API void getLocalTransformComponents(
    const pxr::UsdGeomXformable& xformable,
    pxr::GfVec3d& translation,
    pxr::GfVec3d& pivot,
    pxr::GfVec3f& rotation,
    RotationOrder& rotationOrder,
    pxr::GfVec3f& scale,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Get the local transform of a prim at a given time in the form of common transform components with quaternion orientation.
//!
//! @param prim The prim to get local transform from.
//! @param translation Translation result.
//! @param pivot Pivot position result.
//! @param orientation Orientation result as a quaternion.
//! @param scale Scale result.
//! @param time Time at which to query the value.
//! @returns `void`
USDEX_API void getLocalTransformComponentsQuat(
    const pxr::UsdPrim& prim,
    pxr::GfVec3d& translation,
    pxr::GfVec3d& pivot,
    pxr::GfQuatf& orientation,
    pxr::GfVec3f& scale,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! Get the local transform of an xformable at a given time in the form of common transform components with quaternion orientation.
//!
//! @param xformable The xformable to get local transform from.
//! @param translation Translation result.
//! @param pivot Pivot position result.
//! @param orientation Orientation result as a quaternion.
//! @param scale Scale result.
//! @param time Time at which to query the value.
//! @returns `void`
USDEX_API void getLocalTransformComponentsQuat(
    const pxr::UsdGeomXformable& xformable,
    pxr::GfVec3d& translation,
    pxr::GfVec3d& pivot,
    pxr::GfQuatf& orientation,
    pxr::GfVec3f& scale,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! @}

//! @defgroup xform Xform Prims
//!
//! Utility functions to create `UsdGeomXform` prims.
//!
//! See [UsdGeomXform](https://openusd.org/release/api/class_usd_geom_xform.html) for details.
//!
//! @{

//! Defines an xform on the stage.
//!
//! @param stage The stage on which to define the xform
//! @param path The absolute prim path at which to define the xform
//! @param transform Optional local transform to set
//!
//! @returns UsdGeomXform schema wrapping the defined UsdPrim. Returns an invalid schema on error.
USDEX_API pxr::UsdGeomXform defineXform(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    std::optional<const pxr::GfTransform> transform = std::nullopt
);

//! Defines an xform on the stage.
//!
//! @param parent Prim below which to define the xform
//! @param name Name of the xform
//! @param transform Optional local transform to set
//!
//! @returns UsdGeomXform schema wrapping the defined UsdPrim. Returns an invalid schema on error.
USDEX_API pxr::UsdGeomXform defineXform(pxr::UsdPrim parent, const std::string& name, std::optional<const pxr::GfTransform> transform = std::nullopt);

//! Defines a basic xform from an existing prim.
//!
//! This converts an existing prim to an Xform type, preserving any existing transform data.
//!
//! @param prim The existing prim to convert to an xform
//! @param transform Optional local transform to set
//!
//! @returns UsdGeomXform schema wrapping the converted UsdPrim.
USDEX_API pxr::UsdGeomXform defineXform(pxr::UsdPrim prim, std::optional<const pxr::GfTransform> transform = std::nullopt);

//! Defines an xform on the stage.
//!
//! @param stage The stage on which to define the xform
//! @param path The absolute prim path at which to define the xform
//! @param matrix The local transform matrix to set
//!
//! @returns UsdGeomXform schema wrapping the defined UsdPrim. Returns an invalid schema on error.
USDEX_API pxr::UsdGeomXform defineXform(pxr::UsdStagePtr stage, const pxr::SdfPath& path, const pxr::GfMatrix4d& matrix);

//! Defines an xform on the stage.
//!
//! @param parent Prim below which to define the xform
//! @param name Name of the xform
//! @param matrix The local transform matrix to set
//!
//! @returns UsdGeomXform schema wrapping the defined UsdPrim. Returns an invalid schema on error.
USDEX_API pxr::UsdGeomXform defineXform(pxr::UsdPrim parent, const std::string& name, const pxr::GfMatrix4d& matrix);

//! Defines a basic xform from an existing prim.
//!
//! This converts an existing prim to an Xform type, preserving any existing transform data.
//!
//! @param prim The existing prim to convert to an xform
//! @param matrix The local transform matrix to set
//!
//! @returns UsdGeomXform schema wrapping the converted UsdPrim.
USDEX_API pxr::UsdGeomXform defineXform(pxr::UsdPrim prim, const pxr::GfMatrix4d& matrix);

//! @}

} // namespace usdex::core
