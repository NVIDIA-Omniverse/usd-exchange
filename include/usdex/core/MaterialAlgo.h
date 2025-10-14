// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/Api.h"

#include <pxr/base/gf/vec3f.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usdShade/material.h>
#include <pxr/usd/usdShade/shader.h>

//! @file usdex/core/MaterialAlgo.h
//! @brief Material and Shader Utilities applicable to all render contexts

namespace usdex::core
{

//! @defgroup materials Material and Shader Prims applicable to all render contexts
//!
//! Utility functions for creating, editing, and querying `UsdShadeMaterial` and `UsdShadeShader` objects, as well as conveniences around authoring
//! [UsdPreviewSurface specification](https://openusd.org/release/spec_usdpreviewsurface.html) compliant shader networks for use with the
//! universal render context.
//!
//! # Creating and Binding Materials #
//!
//! This module provides functions for creating materials (`createMaterial()`), binding them to geometry (`bindMaterial()`), and some basic color
//! transformation functions (linear and sRGB only).
//!
//! While some of these implementations are fairly straightforward, they serve to catch & prevent several common mistakes made when authoring
//! materials using the `UsdShade` module directly.
//!
//! # Defining Preview Materials #
//!
//! `UsdPreviewSurface` materials should be supported by all renderers, and are generally used as "fallback" shaders when renderer-specific
//! shaders have not been supplied. While typically serving as fallback/previews, they are still relatively advanced PBR materials and may be
//! suitable as final quality materials, depending on your intended target use case for your USD data.
//!
//! Several functions below assist with authoring and adding textures to Preview Materials, and are a suitable starting point for anyone needing
//! general PBR behavior across a variety of renderers.
//!
//! In the Preview Material functions, we make several assumptions about the source data, which is broadly applicable to many use cases. If more
//! specific behavior is required, `computeEffectivePreviewSurfaceShader()` can be used to locate the underlying surface shader for further direct
//! authoring (or re-wiring) of `UsdShadeInputs`.
//!
//! # Material Interfaces #
//!
//! Several of the functions below refer to a "Material Interface". This is a term for `UsdShadeInputs` which have been authored directly on a
//! `UsdShadeMaterial` prim and connected to lower-level `UsdShadeShader` inputs, to form a shading network that controls the overall appearance
//! of the material. See [UsdShadeNodeGraph](https://openusd.org/release/api/class_usd_shade_node_graph.html#UsdShadeNodeGraph_Interfaces) for a
//! technical explanation of the Interface Inputs.
//!
//! Material Interfaces are useful for a variety of reasons:
//! - They form a "contract" between the Material author and the end-user as to which inputs are available for editing.
//! - They make it simpler for downstream processes, like render delegates, to make assumptions about the material.
//! - Exposing top-level attributes allows a Material prototype to be instanced, while still providing controls that allow each instance to
//!   appear unique.
//!
//! However, Material Interfaces are not consistently supported in every Application & Renderer:
//! - Any USD native application will support Material Interfaces, and many more will also support them for import into their native scene format.
//! - Some even require Material Interfaces; these will ignore edits to Shader prims and only react to edits to Material prims.
//! - But a few others fail to import Material Interfaces into their native scene format.
//!
//! If you would like to use Material Interfaces with Preview Materials, try `addPreviewMaterialInterface()` to auto-generate an interface. Note that
//! this function does not work for multi-context shader networks.
//!
//! If instead you need to target applications that cannot load Material Interfaces, use `removeMaterialInterface()` to clean the content before
//! loading into your target applications.
//!
//! @warning If your data is targetted at USD native applications or other USD Ecosystem leading applications, then using Material Interfaces
//! is recommended. If you favor broad applicability throughout the _entire_ USD Ecosystem, it maybe be preferable to avoid Material Interfaces
//! for the time being.
//!
//! @{

//! Create a `UsdShadeMaterial` as a child of the Prim parent
//!
//! @param parent Parent prim of the new material
//! @param name Name of the material to be created
//! @returns The newly created `UsdShadeMaterial`. Returns an invalid material object on error.
USDEX_API pxr::UsdShadeMaterial createMaterial(pxr::UsdPrim parent, const std::string& name);

//! Authors a direct binding to the given material on this prim.
//!
//! Validates both the prim and the material, applies the `UsdShadeMaterialBindingAPI` to the target prim,
//! and binds the material to the target prim.
//!
//! @note The material is bound with the default "all purpose" used for both full and preview rendering, and with the default "fallback strength"
//! meaning descendant prims can override with a different material. If alternate behavior is desired, use the `UsdShadeMaterialBindingAPI` directly.
//!
//! @param prim The prim that the material will affect
//! @param material The material to bind to the prim
//! @returns Whether the material was successfully bound to the target prim.
USDEX_API bool bindMaterial(pxr::UsdPrim prim, const pxr::UsdShadeMaterial& material);

//! Get the effective surface Shader of a Material for the universal render context.
//!
//! @param material The Material to consider
//! @returns The connected Shader. Returns an invalid shader object on error.
USDEX_API pxr::UsdShadeShader computeEffectivePreviewSurfaceShader(const pxr::UsdShadeMaterial& material);

//! Defines a PBR `UsdShadeMaterial` driven by a `UsdPreviewSurface` shader network for the universal render context.
//!
//! The input parameters reflect a subset of the [UsdPreviewSurface specification](https://openusd.org/release/spec_usdpreviewsurface.html) commonly
//! used when authoring materials using the metallic/metalness workflow (as opposed to the specular workflow). Many other inputs are available and
//! can be authored after calling this function (including switching to the specular workflow).
//!
//! @param stage The stage on which to define the Material
//! @param path The absolute prim path at which to define the Material
//! @param color The diffuse color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial definePreviewMaterial(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.5f,
    const float metallic = 0.0f
);

//! Defines a PBR `UsdShadeMaterial` driven by a `UsdPreviewSurface` shader network for the universal render context.
//!
//! The input parameters reflect a subset of the [UsdPreviewSurface specification](https://openusd.org/release/spec_usdpreviewsurface.html) commonly
//! used when authoring materials using the metallic/metalness workflow (as opposed to the specular workflow). Many other inputs are available and
//! can be authored after calling this function (including switching to the specular workflow).
//!
//! @param parent Prim below which to define the Material
//! @param name Name of the Material
//! @param color The diffuse color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial definePreviewMaterial(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.5f,
    const float metallic = 0.0f
);

//! Defines a PBR `UsdShadeMaterial` driven by a `UsdPreviewSurface` shader network for the universal render context.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the material on. The prim's type will be set to `UsdShadeMaterial`.
//! @param color The diffuse color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial definePreviewMaterial(
    pxr::UsdPrim prim,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.5f,
    const float metallic = 0.0f
);

//! Adds a diffuse texture to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @note If you intend to create a Material Interface, it is preferable to author all initial shader attributes (including textures)
//! *before* calling `addPreviewMaterialInterface()`. This function will not attempt to reconcile any existing inputs on the Material.
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addDiffuseTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a normals texture to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! The UsdPreviewSurface specification requires the texture reader to provide data that is properly scaled and ready to be consumed as a
//! tangent space normal. Textures stored in 8-bit file formats require scale and bias adjustment to transform the normals into tangent space.
//!
//! This module cannot read the provided `texturePath` to inspect the channel data (the file may not resolve locally, or even exist yet).
//! To account for this, it performs the scale and bias adjustment when the `texturePath` extension matches a list of known 8-bit formats:
//! `["bmp", "tga", "jpg", "jpeg", "png", "tif"]`. Similarly, it assumes that the raw normals data was written into the file, regardless of any
//! file format specific color space metadata. If either of these assumptions is incorrect for your source data, you will need to adjust the
//! `scale`, `bias`, and `sourceColorSpace` settings after calling this function.
//!
//! @note If you intend to create a Material Interface, it is preferable to author all initial shader attributes (including textures)
//! *before* calling `addPreviewMaterialInterface()`. This function will not attempt to reconcile any existing inputs on the Material.
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addNormalTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds an ORM (occlusion, roughness, metallic) texture to a preview material
//!
//! An ORM texture is a normal 3-channel image asset, where the R channel represents occlusion, the G channel represents roughness,
//! and the B channel represents metallic/metallness.
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @note If you intend to create a Material Interface, it is preferable to author all initial shader attributes (including textures)
//! *before* calling `addPreviewMaterialInterface()`. This function will not attempt to reconcile any existing inputs on the Material.
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addOrmTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a single channel roughness texture to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @note If you intend to create a Material Interface, it is preferable to author all initial shader attributes (including textures)
//! *before* calling `addPreviewMaterialInterface()`. This function will not attempt to reconcile any existing inputs on the Material.
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addRoughnessTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a single channel metallic texture to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @note If you intend to create a Material Interface, it is preferable to author all initial shader attributes (including textures)
//! *before* calling `addPreviewMaterialInterface()`. This function will not attempt to reconcile any existing inputs on the Material.
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addMetallicTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a single channel opacity texture to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! In addition to driving the `opacity` input, these additional shader inputs will be set explicitly, to produce better masked geometry:
//! - UsdPreviewSurface: `ior = 1.0`
//! - UsdPreviewSurface: `opacityThreshold = float_epsilon` (just greater than zero)
//!
//! @note If you intend to create a Material Interface, it is preferable to author all initial shader attributes (including textures)
//! *before* calling `addPreviewMaterialInterface()`. This function will not attempt to reconcile any existing inputs on the Material.
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addOpacityTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a primvar reader shader to the material prim and connects it to a surface input.
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! @param material The material prim
//! @param surfaceInputName The name of the input on the surface shader (not including the `inputs:` prefix, eg. `diffuseColor`)
//! @param primvarName The name of the primvar to read (not including the `primvars:` prefix, eg. `paintColor`)
//! @param fallbackValue An optional fallback value to use if the primvar is not found
//! @returns Whether or not the primvar shader was added to the material
USDEX_API bool addPrimvarShaderToPreviewMaterial(
    pxr::UsdShadeMaterial& material,
    const std::string& surfaceInputName,
    const std::string& primvarName,
    const pxr::VtValue& fallbackValue = pxr::VtValue()
);

//! Connects a surface input to a primvar reader shader.
//!
//! A primvar reader shader will be created if it does not already exist.
//!
//! @param shaderInput The surface input to connect the primvar reader to
//! @param primvarName The name of the primvar to read (not including the `primvars:` prefix, eg. `paintColor`)
//! @param fallbackValue An optional fallback value to use if the primvar is not found
//! @returns Whether or not the primvar shader was connected to the surface input
USDEX_API bool connectPrimvarShader(
    pxr::UsdShadeInput& shaderInput,
    const std::string& primvarName,
    const pxr::VtValue& fallbackValue = pxr::VtValue()
);

//! Adds `UsdShadeInputs` to the material prim to create an "interface" to the underlying Preview Shader network.
//!
//! All non-default-value `UsdShadeInputs` on the effective surface shader for the universal render context will be "promoted" to the
//! `UsdShadeMaterial` as new `UsdShadeInputs`. They will be connected to the original source inputs on the shaders, to drive those values, and they
//! will be authored with a value matching what had been set on the shader inputs at the time this function was called.
//!
//! Additionally, `UsdUVTexture.file` inputs on connected shaders will be promoted to the material, following the same logic as direct surface inputs.
//!
//! @note It is preferable to author all initial shader attributes (including textures) *before* calling `addPreviewMaterialInterface()`.
//!
//! @warning This function will fail if there is any other render context driving the material surface. It is only suitable for use on Preview
//! Shader networks, such as the network generated by `definePreviewMaterial()` and its associated `add*Texture` functions. If you require multiple
//! contexts, you should instead construct a Material Interface directly, or with targetted end-user interaction.
//!
//! @param material The material prim
//! @returns Whether or not the Material inputs were added successfully
USDEX_API bool addPreviewMaterialInterface(pxr::UsdShadeMaterial& material);

//! Removes any `UsdShadeInputs` found on the material prim.
//!
//! All `UsdShadeInputs` on the `UsdShadeMaterial` will be disconnected from any underlying shader inputs, then removed from the material.
//! The current values may be optionally "baked down" onto the shader inputs in order to retain the current material behavior, or may be
//! discarded in order to revert to a default appearance based on the shader definitions.
//!
//! @note While `addPreviewMaterialInterface` is specific to Preview Material shader networks, `removeMaterialInterface` *affects all render contexts*
//! and will remove all `UsdShadeInputs` returned via `UsdShadeMaterial::GetInterfaceInputs()`, baking down the values onto all consumer shaders,
//! regardless of render context.
//!
//! @param material The material prim
//! @param bakeValues Whether or not the current Material inputs values are set on the underlying Shader inputs
//! @returns Whether or not the Material inputs were removed successfully
USDEX_API bool removeMaterialInterface(pxr::UsdShadeMaterial& material, bool bakeValues = true);

//! Texture color space (encoding) types
// clang-format off
enum class ColorSpace
{
    eAuto, //!< Check for gamma or metadata in the texture itself
    eRaw,  //!< Use linear sampling (typically used for Normal, Roughness, Metallic, Opacity textures, or when using high dynamic range file formats like EXR)
    eSrgb, //!< Use sRGB sampling (typically used for Diffuse textures when using PNG files)
};
// clang-format on

//! Get the `TfToken` matching a given `ColorSpace`
//!
//! The token representation is typically used when setting shader inputs, such as `inputs:sourceColorSpace` on `UsdUVTexture`.
//!
//! @param value The `ColorSpace`
//! @returns The token for the given ``ColorSpace`` value
USDEX_API const pxr::TfToken& getColorSpaceToken(ColorSpace value);

//! Translate an sRGB color value to linear color space
//!
//! Many 3D modeling applications define colors in sRGB (0-1) color space. Many others use a linear color space that aligns with how light and color
//! behave in the natural world. When authoring `UsdShadeShader` color input data, including external texture assets, you may need to translate
//! between color spaces.
//!
//! @note Color is a complex topic in 3D rendering and providing utilities covering the full breadth of color science is beyond the scope of this
//! module. See this [MathWorks article](https://www.mathworks.com/help/images/understanding-color-spaces-and-color-space-conversion.html) for a
//! relatively brief introduction. If you need more specific color handling please use a dedicated color science library like
//! [OpenColorIO](https://opencolorio.org).
//!
//! @param color sRGB representation of a color to be translated to linear color space
//! @returns The translated color in linear color space
USDEX_API pxr::GfVec3f sRgbToLinear(const pxr::GfVec3f& color);

//! Translate a linear color value to sRGB color space
//!
//! Many 3D modeling applications define colors in sRGB (0-1) color space. Many others use a linear color space that aligns with how light and color
//! behave in the natural world. When authoring `UsdShadeShader` color input data, including external texture assets, you may need to translate
//! between color spaces.
//!
//! @note Color is a complex topic in 3D rendering and providing utilities covering the full breadth of color science is beyond the scope of this
//! module. See this [MathWorks article](https://www.mathworks.com/help/images/understanding-color-spaces-and-color-space-conversion.html) for a
//! relatively brief introduction. If you need more specific color handling please use a dedicated color science library like
//! [OpenColorIO](https://opencolorio.org).
//!
//! @param color linear representation of a color to be translated to sRGB color space
//! @returns The color in sRGB color space
USDEX_API pxr::GfVec3f linearToSrgb(const pxr::GfVec3f& color);

//! @}

} // namespace usdex::core
