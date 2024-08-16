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

#include "usdex/pybind/UsdBindings.h"

#include "usdex/rtx/MaterialAlgo.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

using namespace usdex::rtx;
using namespace pybind11;
using namespace pxr;

namespace usdex::rtx::bindings
{

void bindMaterialAlgo(module& m)
{
    ::enum_<ColorSpace>(m, "ColorSpace", "Texture color space (encoding) types")
        .value("eAuto", ColorSpace::eAuto, "Check for gamma or metadata in the texture itself")
        .value("eRaw", ColorSpace::eRaw, "Use linear sampling (used for Normal, Roughness, Metallic, Opacity textures)")
        .value("eSrgb", ColorSpace::eSrgb, "Use sRGB sampling (typically used for Diffuse textures)");
    m.def(
        "sRgbToLinear",
        &sRgbToLinear,
        arg("color"),
        R"(
            Translate an sRGB color value to linear color space

            Many 3D modeling applications define colors in RGB (0-255) or sRGB (0-1) color space
            MDL uses a linear color space that aligns with how light and color behave in the natural world

            Args:
                color: sRGB representation of a color to be translated to linear color space
            Returns:
                The translated color in linear color space
        )"
    );
    m.def(
        "linearToSrgb",
        &linearToSrgb,
        arg("color"),
        R"(
            Translate a linear color value to sRGB color space

            Many 3D modeling applications define colors in RGB (0-255) or sRGB (0-1) color space
            MDL uses a linear color space that aligns with how light and color behave in the natural world

            Args:
                color: linear representation of a color to be translated to sRGB color space
            Returns:
                The translated color in sRGB color space
        )"
    );
    m.def(
        "createMaterial",
        &createMaterial,
        arg("parent"),
        arg("name"),
        R"(
            Create a UsdShade.Material as the child of the Usd.Prim argument

            Args:
                parent: Parent Usd.Prim for the material to be created
                name: Name of the material to be created
            Returns:
                The newly created UsdShade.Material. Returns an Invalid prim on error.
        )"
    );
    m.def(
        "createMdlShader",
        &createMdlShader,
        arg("material"),
        arg("name"),
        arg("mdlPath"),
        arg("module"),
        arg("connectMaterialOutputs") = true,
        R"(
            Create a UsdShade.Shader as a child of the UsdShade.Material argument with the specified MDL

            Args:
                material: Parent UsdShade.Material for the shader to be created
                name: Name of the shader to be created
                mdlPath: Absolute or relative path to the MDL asset
                module: Name of the MDL module to set as source asset sub-identifier for the shader
                connectMaterialOutputs: If true, it creates the surface, volume and displacement outputs of the material and connects them to the shader output
            Returns:
                the newly created UsdShade.Shader. Returns an Invalid prim on error.
        )"
    );
    m.def(
        "createMdlShaderInput",
        [](UsdShadeMaterial& material,
           const TfToken& name,
           const VtValue& value,
           const SdfValueTypeName& typeName,
           std::optional<const ColorSpace> colorSpace)
        {
            VtValue castValue = value;
            // Cast some types because Python doesn't map string-Token/SdfAssetPath and double/float values properly
            if (typeName == SdfValueTypeNames->Asset)
            {
                castValue = VtValue::Cast<SdfAssetPath>(value);
            }
            else if (typeName == SdfValueTypeNames->Token)
            {
                castValue = VtValue::Cast<TfToken>(value);
            }
            else if (typeName == SdfValueTypeNames->Float)
            {
                castValue = VtValue::Cast<float>(value);
            }
            return createMdlShaderInput(material, name, castValue, typeName, colorSpace);
        },
        arg("material"),
        arg("name"),
        arg("value"),
        arg("typeName"),
        arg("colorSpace") = nullptr,
        R"(
            Create an MDL shader input

            If the shader input already exists and is a different type, defined in the current edit target layer -> it will be removed and recreated

            If the shader input already exists and has a connected source -> the source will be disconnected before being set

            Note:
                When creating texture asset inputs (diffuse, normal, roughness, etc.) it is important to set the colorSpace parameter so that
                the textures are sampled correctly.  Typically, diffuse is "auto", which resolves to "sRGB".  Normal, roughness, and other textures
                should be "raw".

            Args:
                material: The UsdShade.Material prim that contains the MDL shader
                name: Name of the input to be created
                value: The value assigned to the input
                typeName: The Sdf.ValueTypeName of the input
                colorSpace: If set, the newly created input's colorSpace attribute

            Returns:
                The newly created Usd.Shade.Input input.  Returns an Invalid Usd.Shade.Input on error.
        )"
    );
    m.def(
        "bindMaterial",
        &bindMaterial,
        arg("prim"),
        arg("material"),
        R"(
            Binds a UsdShade.Material to a Usd.Prim

            Args:
                prim: Usd.Prim to hind the material to
                material: UsdShade.Material to bind to the prim
        )"
    );

    m.def(
        "computeEffectiveMdlSurfaceShader",
        &computeEffectiveMdlSurfaceShader,
        arg("material"),
        R"(
            Get the effective surface Shader of a Material for the MDL render context.

            If no valid Shader is connected to the MDL render context then the universal render context will be considered.

            Args:
                material: The Material to consider

            Returns:
                The connected Shader. Returns an invalid object on error.
        )"
    );

    m.def(
        "computeEffectivePreviewSurfaceShader",
        &computeEffectivePreviewSurfaceShader,
        arg("material"),
        R"(
            Get the effective surface Shader of a Material for the universal render context.

            Args:
                material: The Material to consider

            Returns:
                The connected Shader. Returns an invalid object on error.
        )"
    );

    m.def(
        "defineOmniPbrMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const GfVec3f&, const float, const float, const float>(&defineOmniPbrMaterial),
        arg("stage"),
        arg("path"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.5f,
        arg("metallic") = 0.0f,
        R"(
            Defines an OmniPBR ``UsdShade.Material`` interface that drives both an RTX render context and a UsdPreviewSurface context

            MDL and UsdPreviewSurface use a linear color space, please convert RGB and sRGB values to linear

            Note:
                The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
                Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.

            Parameters:
                - **stage** - The stage on which to define the Material
                - **path** - The absolute prim path at which to define the Material
                - **color** - The diffuse color of the Material
                - **opacity** - The Opacity Amount to set. When less than 1.0, Enable Opacity is set to true and Fractional Opacity is enabled in the RT renderer
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined UsdShade.Material. Returns an Invalid prim on error
        )"
    );
    m.def(
        "defineOmniPbrMaterial",
        overload_cast<UsdPrim, const std::string&, const GfVec3f&, const float, const float, const float>(&defineOmniPbrMaterial),
        arg("parent"),
        arg("name"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.5f,
        arg("metallic") = 0.0f,
        R"(
            Defines an OmniPBR ``UsdShade.Material`` interface that drives both an RTX render context and a UsdPreviewSurface context

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the Material
                - **name** - Name of the Material
                - **color** - The diffuse color of the Material
                - **opacity** - The Opacity Amount to set. When less than 1.0, Enable Opacity is set to true and Fractional Opacity is enabled in the RT renderer
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined UsdShade.Material. Returns an Invalid prim on error
        )"
    );
    m.def(
        "addDiffuseTextureToPbrMaterial",
        &addDiffuseTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Add a diffuse texture to a PBR material

            It is expected that the material was created by the Connect SDK's defineOmniPbrMaterial() function.

            Note:
                The material prim's "Color" input will be removed and replaced with "DiffuseTexture".
                Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.

            Args:
                material: The UsdShade.Material prim to add the texture
                texturePath: The Sdf.AssetPath for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );
    m.def(
        "addNormalTextureToPbrMaterial",
        &addNormalTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Add a normal texture to a PBR material

            It is expected that the material was created by the Connect SDK's defineOmniPbrMaterial() function.

            Args:
                material: The UsdShade.Material prim to add the texture
                texturePath: The Sdf.AssetPath for the texture

            Returns:
                Whether or not the texture was added to the material

        )"
    );
    m.def(
        "addOrmTextureToPbrMaterial",
        &addOrmTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Add an ORM texture to a PBR material

            It is expected that the material was created by the Connect SDK's defineOmniPbrMaterial() function.

            Note:
                The material prim's "Roughness" and "Metallic" inputs will be removed and replaced with "ORMTexture".
                Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.

            Args:
                material: The UsdShade.Material prim to add the texture
                texturePath: The Sdf.AssetPath for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );
    m.def(
        "addRoughnessTextureToPbrMaterial",
        &addRoughnessTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Add a roughness texture to a PBR material

            It is expected that the material was created by the Connect SDK's defineOmniPbrMaterial() function.

            Note:
                The material prim's "Roughness" input will be removed and replaced with "RoughnessTexture".
                Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.

            Args:
                material: The UsdShade.Material prim to add the texture
                texturePath: The Sdf.AssetPath for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );
    m.def(
        "addMetallicTextureToPbrMaterial",
        &addMetallicTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Add a metallic texture to a PBR material

            It is expected that the material was created by the Connect SDK's defineOmniPbrMaterial() function.

            Note:
                The material prim's "Metallic" input will be removed and replaced with "MetallicTexture".
                Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.

            Args:
                material: The UsdShade.Material prim to add the texture
                texturePath: The Sdf.AssetPath for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );
    m.def(
        "addOpacityTextureToPbrMaterial",
        &addOpacityTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Add an Opacity texture to a PBR material

            It is expected that the material was created by the Connect SDK's defineOmniPbrMaterial() function.

            Note:
                The material prim's "Opacity" input will be removed and replaced with "OpacityTexture".
                Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.

            These shader parameters will be set to produce better masked geometry:
            - MDL OmniPBR: ``opacity_threshold = float_epsilon`` (just greater than zero)
            - UsdPreviewSurface: ``ior = 1.0``
            - UsdPreviewSurface: ``opacityThreshold = float_epsilon`` (just greater than zero)

            Args:
                material: The UsdShade.Material prim to add the texture
                texturePath: The Sdf.AssetPath for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );
    m.def(
        "defineOmniGlassMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const GfVec3f&, const float>(&defineOmniGlassMaterial),
        arg("stage"),
        arg("path"),
        arg("color"),
        arg("indexOfRefraction") = 1.491f,
        R"(
            Defines an OmniGlass ``UsdShade.Material`` interface that drives both an RTX render context and a UsdPreviewSurface context

            MDL and UsdPreviewSurface use a linear color space, please convert RGB and sRGB values to linear

            Note:
                The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
                Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.

            Parameters:
                - **stage** - The stage on which to define the Material
                - **path** - The absolute prim path at which to define the Material
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, 1.0-4.0 range

            Returns:
                The newly defined UsdShade.Material. Returns an Invalid prim on error
        )"
    );
    m.def(
        "defineOmniGlassMaterial",
        overload_cast<UsdPrim, const std::string&, const GfVec3f&, const float>(&defineOmniGlassMaterial),
        arg("parent"),
        arg("name"),
        arg("color"),
        arg("indexOfRefraction") = 1.491f,
        R"(
            Defines an OmniGlass ``UsdShade.Material`` interface that drives both an RTX render context and a UsdPreviewSurface context

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the Material
                - **name** - Name of the Material
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, 1.0-4.0 range

            Returns:
                The newly defined UsdShade.Material. Returns an Invalid prim on error
        )"
    );
}

} // namespace usdex::rtx::bindings
