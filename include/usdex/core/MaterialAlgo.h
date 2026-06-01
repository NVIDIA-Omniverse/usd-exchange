// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/Api.h"

#include <pxr/base/gf/vec3f.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usdShade/material.h>
#include <pxr/usd/usdShade/shader.h>

#include <vector>

//! @file usdex/core/MaterialAlgo.h
//! @brief Material and Shader Utilities

namespace usdex::core
{

//! @defgroup materials Material and Shader Prims
//!
//! Utility functions for creating, editing, and querying `UsdShadeMaterial` and `UsdShadeShader` objects. This module provides:
//!
//! - **Context-agnostic utilities** for creating and binding materials, querying effective shaders, color space conversion, and primvar
//!   reader connections.
//! - **Preview Materials** for the universal render context, using
//!   [UsdPreviewSurface](https://openusd.org/release/spec_usdpreviewsurface.html) shader networks.
//! - **PBR Materials** for dual-context authoring, using
//!   [OpenPBR Surface](https://academysoftwarefoundation.github.io/OpenPBR/) shader networks for the
//!   [MaterialX](https://kwokcb.github.io/MaterialX_Learn/documents/definitions/definitions_by_group.html) render context
//!   together with a UsdPreviewSurface fallback for the universal render context.
//!
//! # Creating and Binding Materials #
//!
//! This module provides functions for creating materials (`createMaterial()`), binding them to geometry (`bindMaterial()`), and some basic color
//! transformation functions (linear and sRGB only).
//!
//! While some of these implementations are fairly straightforward, they serve to catch & prevent several common mistakes made when authoring
//! materials using the `UsdShade` module directly.
//!
//! # Preview Materials (Universal Render Context) #
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
//! # PBR Materials (MaterialX + Universal Render Contexts) #
//!
//! For higher-fidelity rendering, `definePbrMaterial()` creates a dual-context material with both an
//! [OpenPBR Surface](https://academysoftwarefoundation.github.io/OpenPBR/) shader network for the MaterialX render context and a
//! UsdPreviewSurface shader network for the universal render context. The MaterialX shader nodes used are from the
//! [MaterialX Node Library](https://kwokcb.github.io/MaterialX_Learn/documents/definitions/definitions_by_group.html).
//! This gives renderers that support MaterialX (such as USDView/Storm and
//! [Omniverse RTX](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/templates/OpenPBR.html)) a physically accurate
//! shading result, while still providing a UsdPreviewSurface fallback for renderers that do not.
//!
//! The two shader networks are connected through a shared Material Interface, so editing a material-level input (e.g. color or roughness)
//! drives both networks simultaneously. Each `add*TextureToPbrMaterial()` function authors texture shaders for both render contexts in a
//! single call and maintains this shared interface.
//!
//! @note PBR Materials always create a Material Interface. There is no need to call `addPreviewMaterialInterface()` on a PBR Material.
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
//! For Preview Materials, use `addPreviewMaterialInterface()` to auto-generate an interface. Note that this function does not work for
//! multi-context shader networks. PBR Materials created by `definePbrMaterial()` always include a Material Interface by default.
//!
//! If instead you need to target applications that cannot load Material Interfaces, use `removeMaterialInterface()` to clean the content before
//! loading into your target applications.
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


//! Binds materials to the geometry subsets of the given geometry prim.
//!
//! @note The subsets and materials must be in the same order and the number of subsets must equal the number of materials.
//!
//! @param subsets The geometry subsets to bind the materials to
//! @param materials The materials to bind to the subsets
//! @returns Whether the materials were successfully bound to the subsets.
USDEX_API bool bindMaterialSubsets(const std::vector<pxr::UsdGeomSubset>& subsets, const std::vector<pxr::UsdShadeMaterial>& materials);

//! Get the effective surface Shader of a Material for the universal render context.
//!
//! @param material The Material to consider
//! @returns The connected Shader. Returns an invalid shader object on error.
USDEX_API pxr::UsdShadeShader computeEffectivePreviewSurfaceShader(const pxr::UsdShadeMaterial& material);

//! Get the effective surface Shader of a Material for the MaterialX render context.
//!
//! @param material The Material to consider
//! @returns The connected Shader. Returns an invalid shader object on error.
USDEX_API pxr::UsdShadeShader computeEffectiveMtlxSurfaceShader(const pxr::UsdShadeMaterial& material);

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

//! Defines a Glass PBR `UsdShadeMaterial` driven by a `UsdPreviewSurface` shader network for the universal render context.
//!
//! The input parameters reflect a subset of the [UsdPreviewSurface specification](https://openusd.org/release/spec_usdpreviewsurface.html) commonly
//! used when authoring glass materials.
//!
//! @note To make the color take effect, opacity must be used to make the material sufficiently opaque.
//!
//! @param stage The stage on which to define the Material
//! @param path The absolute prim path at which to define the Material
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, minimum 1.0; suggested maximum 4.0
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial defineGlassPreviewMaterial(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::GfVec3f& color,
    const float indexOfRefraction = 1.5f,
    const float roughness = 0.02f,
    const float opacity = 0.2f
);

//! Defines a Glass PBR `UsdShadeMaterial` driven by a `UsdPreviewSurface` shader network for the universal render context.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the Material
//! @param name Name of the Material
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, minimum 1.0; suggested maximum 4.0
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial defineGlassPreviewMaterial(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::GfVec3f& color,
    const float indexOfRefraction = 1.5f,
    const float roughness = 0.02f,
    const float opacity = 0.2f
);

//! Defines a Glass PBR `UsdShadeMaterial` driven by a `UsdPreviewSurface` shader network for the universal render context.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the material on. The prim's type will be set to `UsdShadeMaterial`.
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, minimum 1.0; suggested maximum 4.0
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial defineGlassPreviewMaterial(
    pxr::UsdPrim prim,
    const pxr::GfVec3f& color,
    const float indexOfRefraction = 1.5f,
    const float roughness = 0.02f,
    const float opacity = 0.2f
);

//! Adds an emissive color to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! @param material The material prim
//! @param color The emissive color
//! @returns Whether or not the emissive color was added to the material
USDEX_API bool addEmissiveColorToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::GfVec3f& color);

//! Adds a color texture to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`)
//! and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.
//!
//! @note If you intend to create a Material Interface, it is preferable to author all initial shader attributes (including textures)
//! *before* calling `addPreviewMaterialInterface()`. This function will not attempt to reconcile any existing inputs on the Material.
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addColorTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a diffuse texture to a preview material
//!
//! \deprecated Use `addColorTextureToPreviewMaterial` instead
USDEX_DEPRECATED("3.0", "Use `addColorTextureToPreviewMaterial` instead")
USDEX_API bool addDiffuseTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a normals texture to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`)
//! and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.
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
//! and the B channel represents metallic/metalness.
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`)
//! and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.
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
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`)
//! and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.
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
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`)
//! and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.
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
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`)
//! and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.
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

//! Adds an emissive color texture to a preview material
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`)
//! and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.
//!
//! @note If you intend to create a Material Interface, it is preferable to author all initial shader attributes (including textures)
//! *before* calling `addPreviewMaterialInterface()`. This function will not attempt to reconcile any existing inputs on the Material.
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addEmissiveTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a primvar reader shader to the material prim and connects it to a surface input.
//!
//! It is expected that the material was created by `definePreviewMaterial()`
//!
//! @note This function will only work on the surface shader, `UsdPreviewSurface`, not shaders within the shader
//! network. For connecting inputs within a shader network, use `connectPrimvarShader()`.
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

//! Connects a shader input to a primvar reader shader.
//!
//! A primvar reader shader will be created if it does not already exist.
//!
//! @note The shader input must be within a Preview Surface or MaterialX shader network.
//!
//! @param shaderInput The shader input to connect the primvar reader to
//! @param primvarName The name of the primvar to read (not including the `primvars:` prefix, eg. `paintColor`)
//! @param fallbackValue An optional fallback value to use if the primvar is not found
//! @returns Whether or not the primvar shader was connected to the shader input
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
//! contexts, you should instead construct a Material Interface directly, or with targeted end-user interaction.
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

//! Defines an OpenPBR `UsdShadeMaterial` interface that drives both an OpenPBR MaterialX render context and the universal render context.
//!
//! The input parameters reflect a subset of the
//! [open_pbr_surface shader](https://kwokcb.github.io/MaterialX_Learn/documents/definitions/open_pbr_surface.html) definition.
//! Many other inputs are available and can be authored after calling this function.
//!
//! @note The `OpenPBR` definition and texture functions always create a Material Interface
//!
//! @param stage The stage on which to define the Material
//! @param path The absolute prim path at which to define the Material
//! @param color The base color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial definePbrMaterial(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.3f,
    const float metallic = 0.0f
);

//! Defines an OpenPBR `UsdShadeMaterial` interface that drives both an OpenPBR MaterialX render context and the universal render context.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the Material
//! @param name Name of the Material
//! @param color The base color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial definePbrMaterial(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.3f,
    const float metallic = 0.0f
);

//! Defines an OpenPBR `UsdShadeMaterial` interface that drives both an OpenPBR MaterialX render context and the universal render context.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param prim Prim to define the material on. The prim's type will be set to `UsdShadeMaterial`.
//! @param color The base color of the Material
//! @param opacity The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param metallic The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid object on error.
USDEX_API pxr::UsdShadeMaterial definePbrMaterial(
    pxr::UsdPrim prim,
    const pxr::GfVec3f& color,
    const float opacity = 1.0f,
    const float roughness = 0.3f,
    const float metallic = 0.0f
);

//! Adds an emissive color and luminance to an OpenPBR material
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! This drives the OpenPBR `emission_color` and `emission_luminance` inputs in the MaterialX render context, and the UsdPreviewSurface
//! `emissiveColor` input in the universal render context. Two material interface inputs are created to share these values across both
//! render contexts: `emissiveColor` (Color3) and `emissiveLuminance` (Float).
//!
//! @note `emissiveLuminance` is in `cd/m^2` (Candelas per square meter, also known as Nits), per the
//! [OpenPBR Surface specification](https://academysoftwarefoundation.github.io/OpenPBR/). UsdPreviewSurface does not have a separate luminance
//! input, so the universal render context only receives the emissive color (without luminance scaling).
//!
//! @param material The material prim
//! @param color The emissive color
//! @param luminance The emissive luminance in `cd/m^2` (Nits). Must be at least 0.0 (no upper bound). Defaults to 1000.0, which is roughly the
//!     brightness of an indoor LED light panel and produces a clearly visible emission in most scenes.
//! @returns Whether or not the emissive color was added to the material
USDEX_API bool addEmissiveColorToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::GfVec3f& color, const float luminance = 1000.0f);

//! Adds a color texture to an OpenPBR material
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addColorTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a normals texture to an OpenPBR material
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addNormalTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds an ORM (occlusion, roughness, metallic) texture to an OpenPBR material
//!
//! An ORM texture is a normal 3-channel image asset, where the R channel represents occlusion, the G channel represents roughness,
//! and the B channel represents metallic/metalness. The occlusion channel is not used by the OpenPBR definition.
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addOrmTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a single channel roughness texture to an OpenPBR material
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addRoughnessTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a single channel metallic texture to an OpenPBR material
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addMetallicTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds a single channel opacity texture to an OpenPBR material
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @returns Whether or not the texture was added to the material
USDEX_API bool addOpacityTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath);

//! Adds an emissive color texture to an OpenPBR material
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! The texture will be sampled using texture coordinates from the default UV set (generally named `primvars:st`).
//!
//! This authors a tiledimage shader for the MaterialX render context driving the OpenPBR `emission_color` input, and authors a `UsdUVTexture`
//! shader driving the UsdPreviewSurface `emissiveColor` input. The `file` inputs of both texture shaders are connected to a shared material
//! interface input (`EmissiveTexture`).
//!
//! In addition to the texture, this also creates (or reuses) the `emissiveLuminance` material interface input that drives the OpenPBR
//! `emission_luminance` shader input, so the texture is properly scaled by an emission strength. The supplied `luminance` value will overwrite
//! any value previously authored by `addEmissiveColorToPbrMaterial()`.
//!
//! @note `emissiveLuminance` is in `cd/m^2` (Candelas per square meter, also known as Nits), per the
//! [OpenPBR Surface specification](https://academysoftwarefoundation.github.io/OpenPBR/). UsdPreviewSurface does not have a separate luminance
//! input, so the universal render context only receives the emissive texture (without luminance scaling).
//!
//! @param material The material prim
//! @param texturePath The `SdfAssetPath` to the texture file
//! @param luminance The emissive luminance in `cd/m^2` (Nits). Must be at least 0.0 (no upper bound). Defaults to 1000.0, which is roughly the
//!     brightness of an indoor LED light panel and produces a clearly visible emission in most scenes.
//! @returns Whether or not the texture was added to the material
USDEX_API bool addEmissiveTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath, const float luminance = 1000.0f);

//! Defines a Glass `UsdShadeMaterial` interface that drives both an OpenPBR MaterialX render context and the universal render context.
//!
//! The resulting Material prim will have "Interface" `UsdShadeInputs` which drive both render contexts. See @ref materials for details.
//!
//! @note This function generates an [OpenPBR Surface](https://academysoftwarefoundation.github.io/OpenPBR/) MaterialX shader for the MaterialX
//! render context and a `UsdPreviewSurface` shader for the universal render context. The created Material inputs reflect a subset of the available
//! parameters commonly used when authoring glass materials:
//! - `color` - The glass color (drives `transmission_color` on OpenPBR and `diffuseColor` on UsdPreviewSurface)
//! - `ior` - Index of Refraction (drives `specular_ior` on OpenPBR and `ior` on UsdPreviewSurface)
//! - `roughness` - Specular roughness for the glass surface (drives `specular_roughness` on OpenPBR and `roughness` on UsdPreviewSurface)
//! - `opacity` - Controls UsdPreviewSurface `opacity` only; OpenPBR glass transparency is handled via `transmission_weight`
//!
//! @param stage The stage on which to define the Material
//! @param path The absolute prim path at which to define the Material
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, minimum 1.0; soft maximum 3.0
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param previewOpacity The Opacity Amount to set on UsdPreviewSurface, 0.0-1.0 range where 1.0 = opaque and 0.0 = transparent
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid prim on error
USDEX_API pxr::UsdShadeMaterial defineGlassPbrMaterial(
    pxr::UsdStagePtr stage,
    const pxr::SdfPath& path,
    const pxr::GfVec3f& color,
    const float indexOfRefraction = 1.5f,
    const float roughness = 0.02f,
    const float previewOpacity = 0.2f
);

//! Defines a Glass `UsdShadeMaterial` interface that drives both an OpenPBR MaterialX render context and the universal render context.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @note This function generates an [OpenPBR Surface](https://academysoftwarefoundation.github.io/OpenPBR/) MaterialX shader for the MaterialX
//! render context and a `UsdPreviewSurface` shader for the universal render context. Material inputs are created to control the look:
//! - `color` - The glass color (drives `transmission_color` on OpenPBR and `diffuseColor` on UsdPreviewSurface)
//! - `ior` - Index of Refraction (drives `specular_ior` on OpenPBR and `ior` on UsdPreviewSurface)
//! - `roughness` - Specular roughness for the glass surface (drives `specular_roughness` on OpenPBR and `roughness` on UsdPreviewSurface)
//! - `opacity` - Controls UsdPreviewSurface `opacity` only; OpenPBR glass transparency is handled via `transmission_weight`
//!
//! @param parent Prim below which to define the Material
//! @param name Name of the Material
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, minimum 1.0; soft maximum 3.0
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param previewOpacity The Opacity Amount to set on UsdPreviewSurface, 0.0-1.0 range where 1.0 = opaque and 0.0 = transparent
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid prim on error
USDEX_API pxr::UsdShadeMaterial defineGlassPbrMaterial(
    pxr::UsdPrim parent,
    const std::string& name,
    const pxr::GfVec3f& color,
    const float indexOfRefraction = 1.5f,
    const float roughness = 0.02f,
    const float previewOpacity = 0.2f
);

//! Defines a Glass `UsdShadeMaterial` interface that drives both an OpenPBR MaterialX render context and the universal render context.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @note This function generates an [OpenPBR Surface](https://academysoftwarefoundation.github.io/OpenPBR/) MaterialX shader for the MaterialX
//! render context and a `UsdPreviewSurface` shader for the universal render context. Material inputs are created to control the look:
//! - `color` - The glass color (drives `transmission_color` on OpenPBR and `diffuseColor` on UsdPreviewSurface)
//! - `ior` - Index of Refraction (drives `specular_ior` on OpenPBR and `ior` on UsdPreviewSurface)
//! - `roughness` - Specular roughness for the glass surface (drives `specular_roughness` on OpenPBR and `roughness` on UsdPreviewSurface)
//! - `opacity` - Controls UsdPreviewSurface `opacity` only; OpenPBR glass transparency is handled via `transmission_weight`
//!
//! @param prim Prim to define the material on. The prim's type will be set to `UsdShadeMaterial`.
//! @param color The color of the Material
//! @param indexOfRefraction The Index of Refraction to set, minimum 1.0; soft maximum 3.0
//! @param roughness The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
//! @param previewOpacity The Opacity Amount to set on UsdPreviewSurface, 0.0-1.0 range where 1.0 = opaque and 0.0 = transparent
//! @returns The newly defined `UsdShadeMaterial`. Returns an Invalid prim on error
USDEX_API pxr::UsdShadeMaterial defineGlassPbrMaterial(
    pxr::UsdPrim prim,
    const pxr::GfVec3f& color,
    const float indexOfRefraction = 1.5f,
    const float roughness = 0.02f,
    const float previewOpacity = 0.2f
);

//! Adds a primvar reader shader to the material prim and connects it to a surface input.
//!
//! It is expected that the material was created by `definePbrMaterial()`
//!
//! @note This function will only work on the surface shader `ND_open_pbr_surface_surfaceshader`, not shaders within the shader
//! network. For connecting inputs within a shader network, use `connectPrimvarShader()`.
//!
//! @param material The material prim
//! @param surfaceInputName The name of the input on the surface shader (not including the `inputs:` prefix, eg. `base_color`)
//! @param primvarName The name of the primvar to read (not including the `primvars:` prefix, eg. `paintColor`)
//! @param fallbackValue An optional fallback value to use if the primvar is not found
//! @returns Whether or not the primvar shader was added to the material
USDEX_API bool addPrimvarShaderToPbrMaterial(
    pxr::UsdShadeMaterial& material,
    const std::string& surfaceInputName,
    const std::string& primvarName,
    const pxr::VtValue& fallbackValue = pxr::VtValue()
);

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
