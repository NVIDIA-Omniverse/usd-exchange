// SPDX-FileCopyrightText: Copyright (c) 2022-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

//! @file usdex/core/XformAlgo.h
//! @brief Utilities for manipulating UsdGeomXform and UsdGeomXformable Prims

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

//! @defgroup xformable UsdGeomXformable Algorithms
//!
//! Utility functions to manipulate `UsdPrim` transformation data.
//!
//! See `UsdGeomXformable` for details.
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

//! Set the local transform of a prim from a 4x4 matrix.
//!
//! @param prim The prim to set local transform on.
//! @param matrix The matrix value to set.
//! @param time Time at which to write the value.
//! @returns A bool indicating if the local transform was set.
USDEX_API bool setLocalTransform(pxr::UsdPrim prim, const pxr::GfMatrix4d& matrix, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

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

//! Get the local transform of a prim at a given time.
//!
//! @param prim The prim to get local transform from.
//! @param time Time at which to query the value.
//! @returns Transform value as a transform.
USDEX_API pxr::GfTransform getLocalTransform(const pxr::UsdPrim& prim, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

//! Get the local transform of a prim at a given time in the form of a 4x4 matrix.
//!
//! @param prim The prim to get local transform from.
//! @param time Time at which to query the value.
//! @returns Transform value as a 4x4 matrix.
USDEX_API pxr::GfMatrix4d getLocalTransformMatrix(const pxr::UsdPrim& prim, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

//! Get the local transform of a prim at a given time in the form of common transform components.
//!
//! @param prim The prim to get local transform from.
//! @param translation Translation result.
//! @param pivot Pivot position result.
//! @param rotation Rotation result in degrees.
//! @param rotationOrder Rotation order the rotation result.
//! @param scale Scale result.
//! @param time Time at which to query the value.
USDEX_API void getLocalTransformComponents(
    const pxr::UsdPrim& prim,
    pxr::GfVec3d& translation,
    pxr::GfVec3d& pivot,
    pxr::GfVec3f& rotation,
    RotationOrder& rotationOrder,
    pxr::GfVec3f& scale,
    pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()
);

//! @}

//! @defgroup xform UsdGeomXform Algorithms
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

//! @}

} // namespace usdex::core