// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/core/PhysicsMaterialAlgo.h
//! @brief Utility functions to create physics materials.

#include "Api.h"

#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdPhysics/materialAPI.h>
#include <pxr/usd/usdShade/material.h>

#include <optional>

namespace usdex::core
{
//! @defgroup physicsmaterials Physics Material Properties for use with Simulation Engines
//!
//! Utility functions to define, apply, and bind physics material properties to collision geometry.
//!
//! When `UsdPhysicsMaterialAPI` is applied on a `UsdShadeMaterial` it specifies various physical properties which should be used during simulation of
//! the bound geometry.
//!
//! In some cases it may be desirable to manage physics materials separately from visual materials, and in other cases it is useful to manage them as
//! one prim.
//!
//! The functions below can be used to create a new physics material, to apply physics properties to a visual material, and to bind a physics material
//! to a rigid body or collider.
//!
//! @note When mixing visual and physical materials, be sure use both `usdex::core::bindMaterial` and `usdex::core::bindPhysicsMaterial` on the target
//! geometry, to ensure the material is used in both rendering and simulation contexts.
//!
//! See [UsdPhysicsMaterialAPI](https://openusd.org/release/api/usd_physics_page_front.html#usdPhysics_physics_materials) for details.
//!
//! @{

//! Creates a Physics Material.
//!
//! When `UsdPhysicsMaterialAPI` is applied on a `UsdShadeMaterial` it specifies various physical properties which should be used during simulation of
//! the bound geometry.
//!
//! See [UsdPhysicsMaterialAPI](https://openusd.org/release/api/class_usd_physics_material_a_p_i.html) for details.
//!
//! @param stage The stage on which to define the material
//! @param path The absolute prim path at which to define the material
//! @param dynamicFriction The dynamic friction of the material
//! @param staticFriction The static friction of the material
//! @param restitution The restitution of the material
//! @param density The density of the material
//!
//! @returns UsdShadeMaterial schema wrapping the defined UsdPrim
USDEX_API pxr::UsdShadeMaterial definePhysicsMaterial(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const float dynamicFriction,
    const std::optional<float> staticFriction = std::nullopt,
    const std::optional<float> restitution = std::nullopt,
    const std::optional<float> density = std::nullopt
);

//! Creates a Physics Material.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the physics material
//! @param name Name of the physics material
//! @param dynamicFriction The dynamic friction of the material
//! @param staticFriction The static friction of the material
//! @param restitution The restitution of the material
//! @param density The density of the material
//!
//! @returns UsdShadeMaterial schema wrapping the defined UsdPrim
USDEX_API pxr::UsdShadeMaterial definePhysicsMaterial(
    pxr::UsdPrim parent,
    const std::string& name,
    const float dynamicFriction,
    const std::optional<float> staticFriction = std::nullopt,
    const std::optional<float> restitution = std::nullopt,
    const std::optional<float> density = std::nullopt
);

//! Creates a Physics Material.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the material. The prim's type will be set to `UsdShadeMaterial`.
//! @param dynamicFriction The dynamic friction of the material
//! @param staticFriction The static friction of the material
//! @param restitution The restitution of the material
//! @param density The density of the material
//!
//! @returns UsdShadeMaterial schema wrapping the defined UsdPrim
USDEX_API pxr::UsdShadeMaterial definePhysicsMaterial(
    pxr::UsdPrim prim,
    const float dynamicFriction,
    const std::optional<float> staticFriction = std::nullopt,
    const std::optional<float> restitution = std::nullopt,
    const std::optional<float> density = std::nullopt
);

//! Adds physical material parameters to an existing Material.
//!
//! Used to apply `UsdPhysicsMaterialAPI` and related properties to an existing `UsdShadeMaterial` (e.g. a visual material).
//!
//! @note When mixing visual and physical materials, be sure use both `usdex::core::bindMaterial` and `usdex::core::bindPhysicsMaterial` on the target
//! geometry, to ensure the material is used in both rendering and simulation contexts.
//!
//! @param material The material prim
//! @param dynamicFriction The dynamic friction of the material
//! @param staticFriction The static friction of the material
//! @param restitution The restitution of the material
//! @param density The density of the material
//!
//! @returns Whether the physics material was successfully added to the material.
USDEX_API bool addPhysicsToMaterial(
    pxr::UsdShadeMaterial& material,
    const float dynamicFriction,
    const std::optional<float> staticFriction = std::nullopt,
    const std::optional<float> restitution = std::nullopt,
    const std::optional<float> density = std::nullopt
);

//! Binds a physics material to a given rigid body or collision geometry.
//!
//! Validates both the prim and the material, applies the `UsdShadeMaterialBindingAPI` to the target prim,
//! and binds the material to the target prim with the "physics" purpose.
//!
//! @note The material is bound with the "physics" purpose, and with the default "fallback strength",
//! meaning descendant prims can override with a different material. If alternate behavior is desired, use the `UsdShadeMaterialBindingAPI` directly.
//!
//! @note We cannot bind materials to prims across different instance boundaries.
//! This function returns an error if `prim` are not placed in an editable location.
//!
//! @param prim The prim that the material will affect
//! @param material The material to bind to the prim
//!
//! @returns Whether the material was successfully bound to the target prim.
USDEX_API bool bindPhysicsMaterial(pxr::UsdPrim prim, const pxr::UsdShadeMaterial& material);

//! @}

} // namespace usdex::core
