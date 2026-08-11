// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/core/CameraAlgo.h
//! @brief Utility functions to manipulate `UsdGeomCamera` and `GfCamera` data

#include "Api.h"

#include <pxr/base/gf/camera.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/camera.h>

#include <string>


namespace usdex::core
{

//! @defgroup cameras Camera Prims
//!
//! Utility functions to manipulate `UsdGeomCamera` and `GfCamera` data
//!
//! See [UsdGeomCamera](https://openusd.org/release/api/class_usd_geom_camera.html) and
//! [GfCamera](https://openusd.org/release/api/class_gf_camera.html) for details.
//!
//! @{

//! Defines a basic 3d camera on the stage.
//!
//! Note that `GfCamera` is a simplified form of 3d camera data that does not account for time-sampled data, shutter window,
//! stereo role, or exposure. If you need to author those properties, do so after defining the `UsdGeomCamera`.
//!
//! An invalid UsdGeomCamera will be returned if camera attributes could not be authored successfully.
//!
//! @param stage The stage on which to define the camera
//! @param path The absolute prim path at which to define the camera
//! @param cameraData The camera data to set, including the world space transform matrix
//!
//! @returns UsdGeomCamera schema wrapping the defined UsdPrim.
USDEX_API pxr::UsdGeomCamera defineCamera(pxr::UsdStagePtr stage, const pxr::SdfPath& path, const pxr::GfCamera& cameraData);

//! Defines a basic 3d camera on the stage.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the camera
//! @param name Name of the camera
//! @param cameraData The camera data to set, including the world space transform matrix
//!
//! @returns UsdGeomCamera schema wrapping the defined UsdPrim.
USDEX_API pxr::UsdGeomCamera defineCamera(pxr::UsdPrim parent, const std::string& name, const pxr::GfCamera& cameraData);

//! Defines a basic 3d camera from an existing prim.
//!
//! This converts an existing prim to a Camera type, preserving any existing transform data.
//!
//! @param prim The existing prim to convert to a camera
//! @param cameraData The camera data to set, including the world space transform matrix
//!
//! @returns UsdGeomCamera schema wrapping the converted UsdPrim.
USDEX_API pxr::UsdGeomCamera defineCamera(pxr::UsdPrim prim, const pxr::GfCamera& cameraData);

//! @}

} // namespace usdex::core
