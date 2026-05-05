// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/core/StageAlgo.h
//! @brief Utility functions to provide consistant authoring of `UsdStages`

#include "Api.h"

#include <pxr/base/tf/token.h>
#include <pxr/usd/usd/stage.h>

#include <optional>
#include <string_view>

namespace usdex::core
{

//! @defgroup stage_metadata UsdStage Configuration
//!
//! Utility functions to provide consistant authoring of `UsdStages`
//!
//! When authoring `UsdStages` it is important to configure certain metrics & metadata on the root `SdfLayer` of the stage. While this is trivial
//! using various `Usd` and `UsdGeom` public methods, it is also easy to forget, and difficult to discover.
//!
//! These functions assist authoring applications in setting stage metrics and authoring metadata (see @ref layers), so that each application can
//! produce consistant metadata on the `SdfLayers` it exports.

//! @{

//! Create and configure a `UsdStage` so that the defining metadata is explicitly authored.
//!
//! See `configureStage` for more details.
//!
//! @note The extension of the `identifier` must be associated with a file format that supports editing.
//!
//! @param identifier The identifier to be used for the root layer of this stage.
//! @param defaultPrimName Name of the default root prim.
//! @param upAxis The up axis for all the geometry contained in the stage.
//! @param linearUnits The meters per unit for all linear measurements in the stage, eg. `UsdGeomLinearUnits::meters`
//! @param massUnits The kilograms per unit for all mass measurements in the stage, eg. `UsdPhysicsMassUnits::kilograms`
//! @param authoringMetadata The provenance information from the host application. See @ref layers for details.
//!    If the "creator" key already exists, it will not be overwritten & this data will be ignored.
//! @param fileFormatArgs Additional file format-specific arguments to be supplied during Stage creation.
//! @returns The newly created stage or a null pointer.
USDEX_API pxr::UsdStageRefPtr createStage(
    const std::string& identifier,
    const std::string& defaultPrimName,
    const pxr::TfToken& upAxis,
    const double linearUnits,
    const double massUnits,
    const std::string& authoringMetadata,
    const pxr::SdfLayer::FileFormatArguments& fileFormatArgs = pxr::SdfLayer::FileFormatArguments()
);

//! Create and configure a `UsdStage` so that the defining metadata is explicitly authored.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param identifier The identifier to be used for the root layer of this stage.
//! @param defaultPrimName Name of the default root prim.
//! @param upAxis The up axis for all the geometry contained in the stage.
//! @param linearUnits The meters per unit for all linear measurements in the stage, eg. `UsdGeomLinearUnits::meters`
//! @param authoringMetadata The provenance information from the host application. See @ref layers for details.
//!    If the "creator" key already exists, it will not be overwritten & this data will be ignored.
//! @param fileFormatArgs Additional file format-specific arguments to be supplied during Stage creation.
//! @returns The newly created stage or a null pointer.
USDEX_API pxr::UsdStageRefPtr createStage(
    const std::string& identifier,
    const std::string& defaultPrimName,
    const pxr::TfToken& upAxis,
    const double linearUnits,
    const std::string& authoringMetadata,
    const pxr::SdfLayer::FileFormatArguments& fileFormatArgs = pxr::SdfLayer::FileFormatArguments()
);

//! Configure a stage so that the defining metadata is explicitly authored.
//!
//! The default prim will be used as the target of a Reference or Payload to this layer when no explicit prim path is specified.
//! A root prim with the given `defaultPrimName` will be defined on the stage if one is not already specified.
//! If a new prim is defined then the prim type will be set to `Scope`.
//!
//! The stage metrics of [Up Axis](https://openusd.org/release/api/group___usd_geom_up_axis__group.html#details),
//! [Linear Units](https://openusd.org/release/api/group___usd_geom_linear_units__group.html#details) and
//! [Mass Units](https://openusd.org/release/api/usd_physics_page_front.html#usdPhysics_units) will be authored.
//!
//! The root layer will be annotated with authoring metadata, unless previously annotated. This is to preserve
//! authoring metadata on referenced layers that came from other applications. See @ref layers for more details
//! on `setLayerAuthoringMetadata`.
//!
//! @param stage The stage to be configured.
//! @param defaultPrimName Name of the default root prim.
//! @param upAxis The up axis for all the geometry contained in the stage.
//! @param linearUnits The meters per unit for all linear measurements in the stage, eg. `UsdGeomLinearUnits::meters`
//! @param massUnits The kilograms per unit for all mass measurements in the stage, eg. `UsdPhysicsMassUnits::kilograms`
//! @param authoringMetadata The provenance information from the host application. See @ref layers for details.
//! @returns A bool indicating if the metadata was successfully authored.
USDEX_API bool configureStage(
    pxr::UsdStagePtr stage,
    const std::string& defaultPrimName,
    const pxr::TfToken& upAxis,
    const double linearUnits,
    const double massUnits,
    std::optional<std::string_view> authoringMetadata = std::nullopt
);

//! Configure a stage so that the defining metadata is explicitly authored.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param stage The stage to be configured.
//! @param defaultPrimName Name of the default root prim.
//! @param upAxis The up axis for all the geometry contained in the stage.
//! @param linearUnits The meters per unit for all linear measurements in the stage, eg. `UsdGeomLinearUnits::meters`
//! @param authoringMetadata The provenance information from the host application. See @ref layers for details.
//! @returns A bool indicating if the metadata was successfully authored.
USDEX_API bool configureStage(
    pxr::UsdStagePtr stage,
    const std::string& defaultPrimName,
    const pxr::TfToken& upAxis,
    const double linearUnits,
    std::optional<std::string_view> authoringMetadata = std::nullopt
);

//! Save the given `UsdStage` with metadata applied to all dirty layers.
//!
//! Save all dirty layers and sublayers contributing to this stage.
//!
//! All dirty layers will be annotated with authoring metadata, unless previously annotated. This is to preserve
//! authoring metadata on referenced layers that came from other applications. See @ref layers for more details
//! on `setLayerAuthoringMetadata`.
//!
//! The comment will be authored in all layers as the SdfLayer comment.
//!
//! @param stage The stage to be saved.
//! @param authoringMetadata The provenance information from the host application. See @ref layers for details.
//!    If the "creator" key already exists on a given layer, it will not be overwritten & this data will be ignored.
//! @param comment The comment will be authored in all dirty layers as the `Sdf.Layer` comment.
USDEX_API void saveStage(
    pxr::UsdStagePtr stage,
    std::optional<std::string_view> authoringMetadata = std::nullopt,
    std::optional<std::string_view> comment = std::nullopt
);

//! @}

//! @defgroup stage_hierarchy UsdStage Hierarchy
//!
//! Utility functions to avoid common mistakes when manipulating the prim hierarchy of a `UsdStage`.
//!
//! @{

//! Validate that prim opinions could be authored at this path on the stage
//!
//! This validates that the `stage` and `path` are valid, and that the path is absolute.
//! If a prim already exists at the given path it must not be an instance proxy.
//!
//! If the location is invalid and `reason` is non-null, an error message describing the validation error will be set.
//!
//! @param stage The Stage to consider.
//! @param path The Path to consider.
//! @param reason The output message for failed validation.
//! @returns True if the location is valid, or false otherwise.
USDEX_API bool isEditablePrimLocation(const pxr::UsdStagePtr stage, const pxr::SdfPath& path, std::string* reason);

//! Validate that prim opinions could be authored for a child prim with the given name
//!
//! This validates that the `prim` is valid, and that the name is a valid identifier.
//! If a prim already exists at the given path it must not be an instance proxy.
//!
//! If the location is invalid and `reason` is non-null, an error message describing the validation error will be set.
//!
//! @param prim The UsdPrim which would be the parent of the proposed location.
//! @param name The name which would be used for the UsdPrim at the proposed location.
//! @param reason The output message for failed validation.
//! @returns True if the location is valid, or false otherwise.
USDEX_API bool isEditablePrimLocation(const pxr::UsdPrim& prim, const std::string& name, std::string* reason);

//! Validate that prim opinions could be authored for a prim
//!
//! This validates that the `prim` is valid and not be an instance proxy.
//!
//! If the location is invalid and `reason` is non-null, an error message describing the validation error will be set.
//!
//! @param prim The UsdPrim tp consider.
//! @param reason The output message for failed validation.
//! @returns True if the location is valid, or false otherwise.
USDEX_API bool isEditablePrimLocation(const pxr::UsdPrim& prim, std::string* reason);

//! @}

} // namespace usdex::core
