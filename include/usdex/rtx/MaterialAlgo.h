// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/MaterialAlgo.h"

#include "usdex/rtx/Api.h"

#include <pxr/base/gf/vec3f.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usdShade/material.h>
#include <pxr/usd/usdShade/shader.h>

#include <optional>

//! @file usdex/rtx/MaterialAlgo.h
//! @brief Material and Shader Prims for use with the RTX Renderer

//! @brief [usdex::rtx](https://docs.omniverse.nvidia.com/usd/code-docs/usd-exchange-sdk) provides utility functions for creating, editing, and
//! querying [UsdShade](https://openusd.org/release/api/usd_shade_page_front.html) data models which represent [MDL Materials and
//! Shaders](https://www.nvidia.com/en-us/design-visualization/technologies/material-definition-language) for use with the RTX Renderer.
namespace usdex::rtx
{

//! @defgroup rtx_materials Material and Shader Prims for use with the RTX Renderer
//!
//! Utility functions for creating, editing, and querying MDL Materials and Shaders for use with the RTX Renderer.
//!
//! # Authoring MDL Shaders for the RTX Renderer #
//!
//! This module provides functions for creating `UsdShadeShaders` that map to
//! [MDL Shaders](https://www.nvidia.com/en-us/design-visualization/technologies/material-definition-language) and `UsdShadeInputs` that map to
//! MDL Inputs.
//!
//! # Defining Materials for the RTX Renderer #
//!
//! The RTX Renderer supports several types of `UsdShadeShaders`, but it is most performant & results will be more photorealistic when using
//! MDL shaders, especially those from the Core MDL Materials, like:
//! - [OmniPBR](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/materials.html#omnipbr)
//! - [OmniGlass](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/materials.html#omniglass)
//!
//! Several functions below assist with authoring and adding textures to PBR and Glass Materials that are specifically tailored for the RTX Renderer.
//!
//! To make the authored USD data more portable across the USD Ecosystem, these functions also author a Preview shader network (see @ref materials),
//! and both shader networks are driven from a top-level "Material Interface" on the `UsdShadeMaterial` prim. The resulting USD can be rendered in
//! the RTX Renderer for the highest fidelity results, as well as in any other USD capable renderer for a lower fidelity preview.
//!
//! @warning If your data is targetted at the RTX Renderer, or other USD native applications or USD Ecosystem leading applications, then using
//! Material Interfaces is recommended. If you favor broad applicability throughout the _entire_ USD Ecosystem, it may be be preferable to avoid
//! Material Interfaces for the time being. In this case, you can call `usdex::core::removeMaterialInterface` after `usdex::rtx::definePbrMaterial`
//!
//! @{

//! Create a UsdShadeShader as a child of the UsdShadeMaterial argument with the specified MDL
//!
//! @param material Parent UsdShadeMaterial for the shader to be created
//! @param name Name of the shader to be created
//! @param mdlPath Absolute or relative path to the MDL asset
//! @param module Name of the MDL module to set as source asset sub-identifier for the shader
//! @param connectMaterialOutputs If true, creates surface, displacement and volume outputs on the material and connects them to the shader output
//! @returns The newly created UsdShadeShader.  Returns an Invalid prim on error.
USDEX_RTX_API pxr::UsdShadeShader createMdlShader(
    pxr::UsdShadeMaterial& material,
    const std::string& name,
    const pxr::SdfAssetPath& mdlPath,
    const pxr::TfToken& module,
    bool connectMaterialOutputs = true
);

//! Create an MDL shader input
//!
//! If the shader input already exists and is a different type, defined in the current edit target layer -> it will be removed and recreated.
//!
//! If the shader input already exists and has a connected source -> the source will be disconnected before being set.
//!
//! @note When creating texture asset inputs (diffuse, normal, roughness, etc.) it is important to set the colorSpace parameter so that
//!       the textures are sampled correctly.  Typically, diffuse is "auto", which resolves to "sRGB".  Normal, roughness, and other textures
//!       should be "raw".
//!
//! @param material The UsdShadeMaterial prim that contains the MDL shader
//! @param name Name of the input to be created
//! @param value The value assigned to the input
//! @param typeName The value type of the input
//! @param colorSpace If set, the newly created input's colorSpace attribute
//! @returns The newly created UsdShadeInput input.  Returns an Invalid UsdShadeInput on error.
USDEX_RTX_API pxr::UsdShadeInput createMdlShaderInput(
    pxr::UsdShadeMaterial& material,
    const pxr::TfToken& name,
    const pxr::VtValue& value,
    const pxr::SdfValueTypeName& typeName,
    std::optional<const usdex::core::ColorSpace> colorSpace = std::nullopt
);

//! Get the effective surface Shader of a Material for the MDL render context.
//!
//! @param material The Material to consider
//! @returns The connected Shader. Returns an invalid object on error.
USDEX_RTX_API pxr::UsdShadeShader computeEffectiveMdlSurfaceShader(const pxr::UsdShadeMaterial& material);

//! Defines a PBR `UsdShadeMaterial` interface that drives both an RTX render context and the universal render context.
//!
//! The resulting Material prim will have "Interface" `UsdShadeInputs` which drive both render contexts. See @ref rtx_materials for details.
//!
//! @note The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
//! Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.
//!
//! @param stage The stage on which to define the Material
//! @param path The absolute prim path at which to define the Material
//! @param color The diffuse color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible.
//! Enable Opacity will be set to true and Fractional Opacity will be enabled in the RT renderer.
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid prim on error
USDEX_RTX_API pxr::UsdShadeMaterial definePbrMaterial(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.5f,
    const float metallic = 0.0f
);

//! Defines a PBR `UsdShadeMaterial` interface that drives both an RTX render context and the universal render context.
//!
//! The resulting Material prim will have "Interface" `UsdShadeInputs` which drive both render contexts. See @ref rtx_materials for details.
//!
//! @note The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
//! Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.
//!
//! @param parent Prim below which to define the Material
//! @param name Name of the Material
//! @param color The diffuse color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible.
//! Enable Opacity will be set to true and Fractional Opacity will be enabled in the RT renderer.
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid prim on error
USDEX_RTX_API pxr::UsdShadeMaterial definePbrMaterial(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.5f,
    const float metallic = 0.0f
);

//! Defines a PBR `UsdShadeMaterial` interface that drives both an RTX render context and the universal render context.
//!
//! The resulting Material prim will have "Interface" `UsdShadeInputs` which drive both render contexts. See @ref rtx_materials for details.
//!
//! @note The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
//! Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.
//!
//! @param prim Prim to define the Material on
//! @param color The diffuse color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible.
//! Enable Opacity will be set to true and Fractional Opacity will be enabled in the RT renderer.
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid prim on error
USDEX_RTX_API pxr::UsdShadeMaterial definePbrMaterial(
    pxr::UsdPrim prim,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.5f,
    const float metallic = 0.0f
);

//! Adds an emissive color to the PBR material
//!
//! It is expected that the material was created by `usdex::rtx::definePbrMaterial()`.
//!
//! @param material The UsdShadeMaterial prim to add the color
//! @param color The emissive color
//! @param intensity The intensity of the emissive color
//! @returns Whether or not the color was added to the material
USDEX_RTX_API bool addEmissiveColorToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::GfVec3f& color, const float intensity);

//! Adds a diffuse texture to the PBR material
//!
//! It is expected that the material was created by `usdex::rtx::definePbrMaterial()`.
//!
//! @note The material prim's "Color" input will be removed and replaced with "DiffuseTexture".
//!       Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.
//!
//! @param material The UsdShadeMaterial prim to add the texture
//! @param texturePath The SdfAssetPath to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_RTX_API bool addDiffuseTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a normal texture to the PBR material
//!
//! It is expected that the material was created by `usdex::rtx::definePbrMaterial()`.
//!
//! @param material The UsdShadeMaterial prim to add the texture
//! @param texturePath The SdfAssetPath to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_RTX_API bool addNormalTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds an ORM (occlusion, roughness, metallic) texture to the PBR material
//!
//! It is expected that the material was created by `usdex::rtx::definePbrMaterial()`.
//!
//! @note The material prim's "Roughness" and "Metallic" inputs will be removed and replaced with "ORMTexture".
//!       Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.
//!
//! @param material The UsdShadeMaterial prim to add the texture
//! @param texturePath The SdfAssetPath to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_RTX_API bool addOrmTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a roughness texture to the PBR material
//!
//! It is expected that the material was created by `usdex::rtx::definePbrMaterial()`.
//!
//! @note The material prim's "Roughness" input will be removed and replaced with "RoughnessTexture".
//!       Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.
//!
//! @param material The UsdShadeMaterial prim to add the texture
//! @param texturePath The SdfAssetPath to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_RTX_API bool addRoughnessTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a metallic texture to the PBR material
//!
//! It is expected that the material was created by `usdex::rtx::definePbrMaterial()`.
//!
//! @note The material prim's "Metallic" input will be removed and replaced with "MetallicTexture".
//!       Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.
//!
//! @param material The UsdShadeMaterial prim to add the texture
//! @param texturePath The SdfAssetPath to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_RTX_API bool addMetallicTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds an opacity texture to the PBR material
//!
//! It is expected that the material was created by `usdex::rtx::definePbrMaterial()`.
//!
//! @note The material prim's "Opacity" input will be removed and replaced with "OpacityTexture".
//!       Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.
//!
//! These shader parameters will be set to produce better masked geometry:
//! - MDL OmniPBR: `opacity_threshold = float_epsilon` (just greater than zero)
//! - UsdPreviewSurface: `ior = 1.0`
//! - UsdPreviewSurface: `opacityThreshold = float_epsilon` (just greater than zero)
//!
//! @param material The UsdShadeMaterial prim to add the texture
//! @param texturePath The SdfAssetPath to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_RTX_API bool addOpacityTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds an emissive texture to the PBR material
//!
//! It is expected that the material was created by `usdex::rtx::definePbrMaterial()`.
//!
//! @note The material prim's "EmissiveColor" input will be removed and replaced with "EmissiveTexture".
//!       Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.
//!
//! @param material The UsdShadeMaterial prim to add the texture
//! @param texturePath The SdfAssetPath to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_RTX_API bool addEmissiveTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Defines a Glass `UsdShadeMaterial` interface that drives both an RTX render context and the universal render context.
//!
//! The resulting Material prim will have "Interface" `UsdShadeInputs` which drive both render contexts. See @ref rtx_materials for details.
//!
//! Note: The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
//! Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.
//!
//! @param stage The stage on which to define the Material
//! @param path The absolute prim path at which to define the Material
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, 1.0-4.0 range
//! @returns The newly defined UsdShadeMaterial. Returns an Invalid prim on error
USDEX_RTX_API pxr::UsdShadeMaterial defineGlassMaterial(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::GfVec3f& color,
    const float indexOfRefraction = 1.491f
);

//! Defines a Glass `UsdShadeMaterial` interface that drives both an RTX render context and the universal render context.
//!
//! The resulting Material prim will have "Interface" `UsdShadeInputs` which drive both render contexts. See @ref rtx_materials for details.
//!
//! Note: The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
//! Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.
//!
//! @param parent Prim below which to define the Material
//! @param name Name of the Material
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, 1.0-4.0 range
//! @returns The newly defined UsdShadeMaterial. Returns an Invalid prim on error
USDEX_RTX_API pxr::UsdShadeMaterial defineGlassMaterial(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::GfVec3f& color,
    const float indexOfRefraction = 1.491f
);

//! Defines a Glass `UsdShadeMaterial` interface that drives both an RTX render context and the universal render context.
//!
//! The resulting Material prim will have "Interface" `UsdShadeInputs` which drive both render contexts. See @ref rtx_materials for details.
//!
//! Note: The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
//! Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.
//!
//! @param prim Prim to define the Material on
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, 1.0-4.0 range
//! @returns The newly defined UsdShadeMaterial. Returns an Invalid prim on error
USDEX_RTX_API pxr::UsdShadeMaterial defineGlassMaterial(pxr::UsdPrim prim, const pxr::GfVec3f& color, const float indexOfRefraction);

//! @}

} // namespace usdex::rtx
