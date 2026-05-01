// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

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
           std::optional<const usdex::core::ColorSpace> colorSpace)
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
        "definePbrMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const GfVec3f&, const float, const float, const float>(&definePbrMaterial),
        arg("stage"),
        arg("path"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.5f,
        arg("metallic") = 0.0f,
        R"(
            Defines a PBR ``UsdShade.Material`` interface that drives both an RTX render context and the universal render context.

            The resulting Material prim will have "Interface" ``UsdShade.Inputs`` which drive both render contexts. See
            `UsdShadeNodeGraph <https://openusd.org/release/api/class_usd_shade_node_graph.html#UsdShadeNodeGraph_Interfaces>`_ for explanations
            of Interfaces.

            Note:

                The use of MDL shaders inside this Material interface is considered an implementation detail of the RTX Renderer.
                Once the RTX Renderer supports OpenPBR or MaterialX shaders we may change the implementation to author those shaders instead of MDL.

            Parameters:
                - **stage** - The stage on which to define the Material
                - **path** - The absolute prim path at which to define the Material
                - **color** - The diffuse color of the Material
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible.
                  Enable Opacity is set to true and Fractional Opacity is enabled in the RT renderer
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined UsdShade.Material. Returns an Invalid prim on error
        )"
    );
    m.def(
        "definePbrMaterial",
        overload_cast<UsdPrim, const std::string&, const GfVec3f&, const float, const float, const float>(&definePbrMaterial),
        arg("parent"),
        arg("name"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.5f,
        arg("metallic") = 0.0f,
        R"(
            Defines a PBR ``UsdShade.Material`` interface that drives both an RTX render context and the universal render context

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
        "definePbrMaterial",
        overload_cast<UsdPrim, const GfVec3f&, const float, const float, const float>(&definePbrMaterial),
        arg("prim"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.5f,
        arg("metallic") = 0.0f,
        R"(
            Defines a PBR ``UsdShade.Material`` interface that drives both an RTX render context and the universal render context

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the Material on
                - **color** - The diffuse color of the Material
                - **opacity** - The Opacity Amount to set. When less than 1.0, Enable Opacity is set to true and Fractional Opacity is enabled in the RT renderer
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined UsdShade.Material. Returns an Invalid prim on error
        )"
    );
    m.def(
        "addEmissiveColorToPbrMaterial",
        &addEmissiveColorToPbrMaterial,
        arg("material"),
        arg("color"),
        arg("intensity") = 1000.0f,
        R"(
            Add an emissive color to a PBR material

            It is expected that the material was created by ``usdex.rtx.definePbrMaterial()``.

            Args:
                material: The UsdShade.Material prim to add the color
                color: The emissive color
                intensity: The intensity of the emissive color
            Returns:
                Whether or not the color was added to the material
        )"
    );
    m.def(
        "addDiffuseTextureToPbrMaterial",
        &addDiffuseTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Add a diffuse texture to a PBR material

            It is expected that the material was created by ``usdex.rtx.definePbrMaterial()``.

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

            It is expected that the material was created by ``usdex.rtx.definePbrMaterial()``.

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

            It is expected that the material was created by ``usdex.rtx.definePbrMaterial()``.

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

            It is expected that the material was created by ``usdex.rtx.definePbrMaterial()``.

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

            It is expected that the material was created by ``usdex.rtx.definePbrMaterial()``.

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

            It is expected that the material was created by ``usdex.rtx.definePbrMaterial()``.

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
        "addEmissiveTextureToPbrMaterial",
        &addEmissiveTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        arg("intensity") = 1000.0f,
        R"(
            Add an emissive texture to a PBR material

            It is expected that the material was created by ``usdex.rtx.definePbrMaterial()``.

            Note:
                The material prim's "EmissiveColor" input will be removed and replaced with "EmissiveTexture".
                Due to the input removal this function should be used at initial authoring time rather than in a stronger layer.

            Args:
                material: The UsdShade.Material prim to add the texture
                texturePath: The Sdf.AssetPath for the texture
                intensity: The intensity of the emissive color

            Returns:
                Whether or not the texture was added to the material
        )"
    );
    m.def(
        "defineGlassMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const GfVec3f&, const float>(&defineGlassMaterial),
        arg("stage"),
        arg("path"),
        arg("color"),
        arg("indexOfRefraction") = 1.491f,
        R"(
            Defines a Glass ``UsdShade.Material`` interface that drives both an RTX render context and the universal render context.

            The resulting Material prim will have "Interface" ``UsdShade.Inputs`` which drive both render contexts. See
            `UsdShadeNodeGraph <https://openusd.org/release/api/class_usd_shade_node_graph.html#UsdShadeNodeGraph_Interfaces>`_ for explanations
            of Interfaces.

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
        "defineGlassMaterial",
        overload_cast<UsdPrim, const std::string&, const GfVec3f&, const float>(&defineGlassMaterial),
        arg("parent"),
        arg("name"),
        arg("color"),
        arg("indexOfRefraction") = 1.491f,
        R"(
            Defines a Glass ``UsdShade.Material`` interface that drives both an RTX render context and the universal render context.

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
    m.def(
        "defineGlassMaterial",
        overload_cast<UsdPrim, const GfVec3f&, const float>(&defineGlassMaterial),
        arg("prim"),
        arg("color"),
        arg("indexOfRefraction") = 1.491f,
        R"(
            Defines a Glass ``UsdShade.Material`` interface that drives both an RTX render context and the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the Material on
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, 1.0-4.0 range

            Returns:
                The newly defined UsdShade.Material. Returns an Invalid prim on error
        )"
    );
}

} // namespace usdex::rtx::bindings
