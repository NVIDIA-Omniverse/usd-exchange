// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/core/GprimAlgo.h
//! @brief Utility functions to create geometric primitives.

#include "Api.h"

#include <pxr/base/gf/vec3f.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/capsule.h>
#include <pxr/usd/usdGeom/cone.h>
#include <pxr/usd/usdGeom/cube.h>
#include <pxr/usd/usdGeom/cylinder.h>
#include <pxr/usd/usdGeom/plane.h>
#include <pxr/usd/usdGeom/sphere.h>

#include <optional>

namespace usdex::core
{

//! @defgroup gprim Geometric primitives
//!
//! OpenUSD supports various basic geometric primitives, known collectively as
//! [UsdGeomGprims](https://openusd.org/release/api/usd_geom_page_front.html#UsdGeom_Gprim), which are considered more performant for both rendering &
//! simulation.
//!
//! While generally trivial to author, it is important to remember to compute correct extents when deviating from the schema fallback values & to
//! check that the prim target location is writeable. The utility functions in this module expose the usual schema parameters of each `Gprim`, and
//! perform these extra checks.
//!
//! The set of available `Gprims` may not directly match the requirements of other data sources. In some cases, it is possible to "shape" a Gprim to
//! match the input data. For example:
//! - A rectangular prism can be authored using `usdex::core::defineCube` followed by `usdex::core::setLocalTransform` with a non-uniform scale.
//! - An ellipsoid approximation can be authored using `usdex::core::defineSphere` and `usdex::core::setLocalTransform` with a non-uniform scale.
//! - Several Gprims provide an `axis` attribute to orient along `X`, `Y`, or `Z` independantly of any XformOps.
//!
//! @note If the source data cannot be trivially shaped using these mechanisms, it may be necessary to tesselate the input data model and author a
//! mesh using `usdex::core::definePolyMesh`.
//! @{

//! Defines a plane primitive.
//!
//! Defines a plane centered at the origin. The normal vector direction can be specified using `axis` as 'X', 'Y', or 'Z'.
//!
//! While the `width` and `length` specify limits for rendering/visualization, it is common to consider the plane as infinite when used as a physics
//! collision in simulation.
//!
//! @param stage The stage on which to define the plane
//! @param path The absolute prim path at which to define the plane
//! @param width The width of the plane
//! @param length The length of the plane
//! @param axis The axis of the plane
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomPlane schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomPlane definePlane(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const double width = 2.0,
    const double length = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a plane primitive as a child of the `parent` prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the plane
//! @param name Name of the plane
//! @param width The width of the plane
//! @param length The length of the plane
//! @param axis The axis of the plane
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomPlane schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomPlane definePlane(
    pxr::UsdPrim parent,
    const std::string& name,
    const double width = 2.0,
    const double length = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a plane primitive from an existing prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim below which to define the plane
//! @param width The width of the plane
//! @param length The length of the plane
//! @param axis The axis of the plane
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomPlane schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomPlane definePlane(
    pxr::UsdPrim prim,
    const double width = 2.0,
    const double length = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a sphere primitive.
//!
//! Defines a sphere of the specified radius at the origin.
//!
//! @param stage The stage on which to define the sphere
//! @param path The absolute prim path at which to define the sphere
//! @param radius The radius of the sphere
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomSphere schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomSphere defineSphere(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const double radius = 1.0,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a sphere primitive as a child of the `parent` prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the sphere
//! @param name Name of the sphere
//! @param radius The radius of the sphere
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomSphere schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomSphere defineSphere(
    pxr::UsdPrim parent,
    const std::string& name,
    const double radius = 1.0,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a sphere primitive from an existing prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim below which to define the sphere
//! @param radius The radius of the sphere
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomSphere schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomSphere defineSphere(
    pxr::UsdPrim prim,
    const double radius = 1.0,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cube primitive.
//!
//! Defines a cube of the specified size at the origin.
//!
//! @note In order to define a rectangular prism, first call `defineCube` and then adjust relative scale of each axis using
//! `usdex::core::setLocalTransform`.
//!
//! @param stage The stage on which to define the cube
//! @param path The absolute prim path at which to define the cube
//! @param size The size of the cube
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCube schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCube defineCube(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const double size = 2.0,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cube primitive as a child of the `parent` prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the cube
//! @param name Name of the cube
//! @param size The size of the cube
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCube schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCube defineCube(
    pxr::UsdPrim parent,
    const std::string& name,
    const double size = 2.0,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cube primitive from an existing prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim below which to define the cube
//! @param size The size of the cube
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCube schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCube defineCube(
    pxr::UsdPrim prim,
    const double size = 2.0,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cone primitive.
//!
//! Defines a cone of the specified radius and height at the origin.
//! The height direction can be specified using `axis` as 'X', 'Y', or 'Z'.
//!
//! @param stage The stage on which to define the cone
//! @param path The absolute prim path at which to define the cone
//! @param radius The radius of the cone
//! @param height The height of the cone
//! @param axis The axis of the cone
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCone schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCone defineCone(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cone primitive as a child of the `parent` prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the cone
//! @param name Name of the cone
//! @param radius The radius of the cone
//! @param height The height of the cone
//! @param axis The axis of the cone
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCone schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCone defineCone(
    pxr::UsdPrim parent,
    const std::string& name,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cone primitive from an existing prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim below which to define the cone
//! @param radius The radius of the cone
//! @param height The height of the cone
//! @param axis The axis of the cone
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCone schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCone defineCone(
    pxr::UsdPrim prim,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cylinder primitive.
//!
//! Defines a cylinder of the specified radius and height at the origin.
//! The height direction can be specified using `axis` as 'X', 'Y', or 'Z'.
//!
//! @param stage The stage on which to define the cylinder
//! @param path The absolute prim path at which to define the cylinder
//! @param radius The radius of the cylinder
//! @param height The height of the cylinder
//! @param axis The axis of the cylinder
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCylinder schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCylinder defineCylinder(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cylinder primitive as a child of the `parent` prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the cylinder
//! @param name Name of the cylinder
//! @param radius The radius of the cylinder
//! @param height The height of the cylinder
//! @param axis The axis of the cylinder
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCylinder schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCylinder defineCylinder(
    pxr::UsdPrim parent,
    const std::string& name,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a cylinder primitive from an existing prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim below which to define the cylinder
//! @param radius The radius of the cylinder
//! @param height The height of the cylinder
//! @param axis The axis of the cylinder
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCylinder schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCylinder defineCylinder(
    pxr::UsdPrim prim,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a capsule primitive.
//!
//! Defines a capsule of the specified radius and height at the origin.
//! The height direction can be specified using `axis` as 'X', 'Y', or 'Z'.
//! The total height of the capsule is `height` + `radius` + `radius`.
//!
//! @param stage The stage on which to define the capsule
//! @param path The absolute prim path at which to define the capsule
//! @param radius The radius of the capsule
//! @param height The height of the capsule shaft, excluding the end caps
//! @param axis The axis of the capsule
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCapsule schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCapsule defineCapsule(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a capsule primitive as a child of the `parent` prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the capsule
//! @param name Name of the capsule
//! @param radius The radius of the capsule
//! @param height The height of the capsule shaft, excluding the end caps
//! @param axis The axis of the capsule
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCapsule schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCapsule defineCapsule(
    pxr::UsdPrim parent,
    const std::string& name,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! Defines a capsule primitive from an existing prim.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim below which to define the capsule
//! @param radius The radius of the capsule
//! @param height The height of the capsule shaft, excluding the end caps
//! @param axis The axis of the capsule
//! @param displayColor Values to be authored for the display color
//! @param displayOpacity Values to be authored for the display opacity
//!
//! @returns UsdGeomCapsule schema wrapping the defined UsdPrim
USDEX_API pxr::UsdGeomCapsule defineCapsule(
    pxr::UsdPrim prim,
    const double radius = 1.0,
    const double height = 2.0,
    const pxr::TfToken axis = pxr::UsdGeomTokens->z,
    const std::optional<pxr::GfVec3f> displayColor = std::nullopt,
    const std::optional<float> displayOpacity = std::nullopt
);

//! @}

} // namespace usdex::core
