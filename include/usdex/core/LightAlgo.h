// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/core/LightAlgo.h
//! @brief Utility functions to define, manipulate, and read `UsdLux` Light Prims.

#include "Api.h"

#include <pxr/base/tf/token.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdLux/domeLight.h>
#include <pxr/usd/usdLux/rectLight.h>
#include <pxr/usd/usdLux/tokens.h>

#include <optional>
#include <string>
#include <string_view>

namespace usdex::core
{
//! @defgroup lights Light Prims
//!
//! Utility functions to define, manipulate, and read `UsdLux` Light Prims.
//!
//! # Defining UsdLux Lights #
//!
//! When creating some USD light types it's sometimes ambiguous as to what attributes should be set.
//! These light definition helper functions provide an argument set that make these optional arguments clear.
//!
//! # Accessing UsdLux Light Attributes #
//!
//! In USD 21.02 many UsdLux Light attributes changed. Input attributes for `UsdLuxLight` and `UsdLuxLightFilter` schemas are now
//! connectable and have been renamed to include the `inputs:` prefix.
//!
//! The `getLightAttr()` function provides the "correct" light attribute depending on which attributes are authored,
//! favoring the newer `inputs:` attributes.  This is to help with existing USD files containing lights that were authored with
//! older light schema that didn't include `inputs:` attributes.
//!
//! [UsdLux Light CHANGELOG note for 21.02](https://github.com/PixarAnimationStudios/USD/blob/release/CHANGELOG.md#2102---2021-01-18)
//!
//! @{

//! Determines if a UsdPrim has a `UsdLuxLightAPI` schema applied
//!
//! @param prim The prim to check for an applied `UsdLuxLightAPI` schema
//! @returns True if the prim has a `UsdLuxLightAPI` schema applied
USDEX_API bool isLight(const pxr::UsdPrim& prim);

//! Get the "correct" light attribute for a light that could have any combination of authored old and new UsdLux schema attributes
//!
//! The new attribute names have "inputs:" prepended to the names to make them connectable.
//! - Light has only "intensity" authored - return "intensity" attribute
//! - Light has only "inputs:intensity" authored - return "inputs:intensity" attribute
//! - Light has both "inputs:intensity" and "intensity" authored - return "inputs:intensity"
//!
//! See @ref lights for more details.
//!
//! @param defaultAttr The attribute to read from the light schema: eg. `UsdLuxRectLight::GetHeightAttr()`
//! @returns The attribute from which the light value should be read
USDEX_API pxr::UsdAttribute getLightAttr(const pxr::UsdAttribute& defaultAttr);

//! Creates a dome light with an optional texture.
//!
//! A dome light represents light emitted inward from a distant external environment, such as a sky or IBL light probe.
//!
//! Texture Format values:
//!
//! - `automatic` - Tries to determine the layout from the file itself.
//! - `latlong` - Latitude as X, longitude as Y.
//! - `mirroredBall` - An image of the environment reflected in a sphere, using an implicitly orthogonal projection.
//! - `angular` - Similar to mirroredBall but the radial dimension is mapped linearly to the angle, for better sampling at the edges.
//! - `cubeMapVerticalCross` - Set to "automatic" by default.
//!
//! @note The DomeLight schema requires the
//! [dome's top pole to be aligned with the world's +Y axis](https://openusd.org/release/api/class_usd_lux_dome_light.html#details).
//! In USD 23.11 a new [UsdLuxDomeLight_1](https://openusd.org/release/api/class_usd_lux_dome_light__1.html#details) schema was added which gives
//! control over the pole axis. However, it is not widely supported yet, so we still prefer to author the original DomeLight schema and expect
//! consuming application and renderers to account for the +Y pole axis.
//!
//! @param stage: The stage in which the dome light should be authored
//! @param path: The path which the dome light prim should be written to
//! @param intensity: The intensity value of the dome light
//! @param texturePath: The path to the texture file to use on the dome light.
//! @param textureFormat: How the texture should be mapped on the dome light.
//!
//! @returns The light if created successfully.
USDEX_API pxr::UsdLuxDomeLight defineDomeLight(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    float intensity = 1.0f,
    std::optional<std::string_view> texturePath = std::nullopt,
    const pxr::TfToken& textureFormat = pxr::UsdLuxTokens->automatic
);

//! Creates a dome light with an optional texture.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the light
//! @param name Name of the light
//! @param intensity: The intensity value of the dome light
//! @param texturePath: The path to the texture file to use on the dome light.
//! @param textureFormat: How the texture should be mapped on the dome light.
//!
//! @returns The light if created successfully.
USDEX_API pxr::UsdLuxDomeLight defineDomeLight(
    pxr::UsdPrim parent,
    const std::string& name,
    float intensity = 1.0f,
    std::optional<std::string_view> texturePath = std::nullopt,
    const pxr::TfToken& textureFormat = pxr::UsdLuxTokens->automatic
);

//! Creates a dome light with an optional texture.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the dome light on. The prim's type will be set to `UsdLuxDomeLight`.
//! @param intensity: The intensity value of the dome light
//! @param texturePath: The path to the texture file to use on the dome light.
//! @param textureFormat: How the texture should be mapped on the dome light.
//!
//! @returns The light if created successfully.
USDEX_API pxr::UsdLuxDomeLight defineDomeLight(
    pxr::UsdPrim prim,
    float intensity = 1.0f,
    std::optional<std::string_view> texturePath = std::nullopt,
    const pxr::TfToken& textureFormat = pxr::UsdLuxTokens->automatic
);

//! Creates a rectangular (rect) light with an optional texture.
//!
//! A rect light represents light emitted from one side of a rectangle.
//!
//! @param stage: The stage in which the rectangular light should be authored
//! @param path: The path which the rectangular light prim should be written to
//! @param width: The width of the rectangular light, in the local X axis.
//! @param height: The height of the rectangular light, in the local Y axis.
//! @param intensity: The intensity value of the rectangular light.
//! @param texturePath: The path to the texture file to use on the rectangular light.
//!
//! @returns The light if created successfully.
USDEX_API pxr::UsdLuxRectLight defineRectLight(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    float width,
    float height,
    float intensity = 1.0f,
    std::optional<std::string_view> texturePath = std::nullopt
);

//! Creates a rectangular (rect) light with an optional texture.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the light
//! @param name Name of the light
//! @param width: The width of the rectangular light, in the local X axis.
//! @param height: The height of the rectangular light, in the local Y axis.
//! @param intensity: The intensity value of the rectangular light.
//! @param texturePath: The path to the texture file to use on the rectangular light.
//!
//! @returns The light if created successfully.
USDEX_API pxr::UsdLuxRectLight defineRectLight(
    pxr::UsdPrim parent,
    const std::string& name,
    float width,
    float height,
    float intensity = 1.0f,
    std::optional<std::string_view> texturePath = std::nullopt
);

//! Creates a rectangular (rect) light with an optional texture.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the rectangular light on. The prim's type will be set to `UsdLuxRectLight`.
//! @param width: The width of the rectangular light, in the local X axis.
//! @param height: The height of the rectangular light, in the local Y axis.
//! @param intensity: The intensity value of the rectangular light.
//! @param texturePath: The path to the texture file to use on the rectangular light.
//!
//! @returns The light if created successfully.
USDEX_API pxr::UsdLuxRectLight defineRectLight(
    pxr::UsdPrim prim,
    float width,
    float height,
    float intensity = 1.0f,
    std::optional<std::string_view> texturePath = std::nullopt
);

//! @}

} // namespace usdex::core
