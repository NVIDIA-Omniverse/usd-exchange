// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/MaterialAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

namespace usdex::core::bindings
{

void bindMaterialAlgo(module& m)
{
    m.def(
        "createMaterial",
        &createMaterial,
        arg("parent"),
        arg("name"),
        R"(
            Create a ``UsdShade.Material`` as the child of the Prim parent

            Args:
                parent: Parent prim of the material
                name: Name of the material to be created
            Returns:
                The newly created ``UsdShade.Material``. Returns an invalid material object on error.
        )"
    );

    m.def(
        "bindMaterial",
        &bindMaterial,
        arg("prim"),
        arg("material"),
        R"(
            Authors a direct binding to the given material on this prim.

            Validates both the prim and the material, applies the ``UsdShade.MaterialBindingAPI`` to the target prim,
            and binds the material to the target prim.

            Note:
                The material is bound with the default "all purpose" used for both full and preview rendering, and with the default "fallback strength"
                meaning descendant prims can override with a different material. If alternate behavior is desired, use the
                ``UsdShade.MaterialBindingAPI`` directly.

            Args:
                prim: The prim that the material will affect
                material: The material to bind to the prim

            Returns:
                Whether the material was successfully bound to the target prim.
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
                The connected Shader. Returns an invalid shader object on error.
        )"
    );

    m.def(
        "definePreviewMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const GfVec3f&, const float, const float, const float>(&definePreviewMaterial),
        arg("stage"),
        arg("path"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.5f,
        arg("metallic") = 0.0f,
        R"(
            Defines a PBR ``UsdShade.Material`` driven by a ``UsdPreviewSurface`` shader network for the universal render context.

            The input parameters reflect a subset of the `UsdPreviewSurface specification <https://openusd.org/release/spec_usdpreviewsurface.html>`_
            commonly used when authoring materials using the metallic/metalness workflow (as opposed to the specular workflow). Many other inputs are
            available and can be authored after calling this function (including switching to the specular workflow).

            Parameters:
                - **stage** - The stage on which to define the Material
                - **path** - The absolute prim path at which to define the Material
                - **color** - The diffuse color of the Material
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid prim on error
        )"
    );

    m.def(
        "definePreviewMaterial",
        overload_cast<UsdPrim, const std::string&, const GfVec3f&, const float, const float, const float>(&definePreviewMaterial),
        arg("parent"),
        arg("name"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.5f,
        arg("metallic") = 0.0f,
        R"(
            Defines a PBR ``UsdShade.Material`` driven by a ``UsdPreviewSurface`` shader network for the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the Material
                - **name** - Name of the Material
                - **color** - The diffuse color of the Material
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid prim on error
        )"
    );

    m.def(
        "definePreviewMaterial",
        overload_cast<UsdPrim, const GfVec3f&, const float, const float, const float>(&definePreviewMaterial),
        arg("prim"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.5f,
        arg("metallic") = 0.0f,
        R"(
            Defines a PBR ``UsdShade.Material`` driven by a ``UsdPreviewSurface`` shader network for the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the material on. The prim's type will be set to ``UsdShade.Material``.
                - **color** - The diffuse color of the Material
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid object on error.
        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "addDiffuseTextureToPreviewMaterial",
        &addDiffuseTextureToPreviewMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds a diffuse texture to a preview material

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``).

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addNormalTextureToPreviewMaterial",
        &addNormalTextureToPreviewMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds a normals texture to a preview material

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``).

            The UsdPreviewSurface specification requires the texture reader to provide data that is properly scaled and ready to be consumed as a
            tangent space normal. Textures stored in 8-bit file formats require scale and bias adjustment to transform the normals into tangent space.

            This module cannot read the provided ``texturePath`` to inspect the channel data (the file may not resolve locally, or even exist yet).
            To account for this, it performs the scale and bias adjustment when the `texturePath` extension matches a list of known 8-bit formats:
            ``["bmp", "tga", "jpg", "jpeg", "png", "tif"]``. Similarly, it assumes that the raw normals data was written into the file, regardless of
            any file format specific color space metadata. If either of these assumptions is incorrect for your source data, you will need to adjust
            the ``scale``, ``bias``, and ``sourceColorSpace`` settings after calling this function.

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addOrmTextureToPreviewMaterial",
        &addOrmTextureToPreviewMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds an ORM (occlusion, roughness, metallic) texture to a preview material

            An ORM texture is a normal 3-channel image asset, where the R channel represents occlusion, the G channel represents roughness,
            and the B channel represents metallic/metallness.

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``).

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addRoughnessTextureToPreviewMaterial",
        &addRoughnessTextureToPreviewMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds a single channel roughness texture to a preview material

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``).

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addMetallicTextureToPreviewMaterial",
        &addMetallicTextureToPreviewMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds a single channel metallic texture to a preview material

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``).

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addOpacityTextureToPreviewMaterial",
        &addOpacityTextureToPreviewMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds a single channel opacity texture to a preview material

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``).

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addPrimvarShaderToPreviewMaterial",
        [](UsdShadeMaterial& material, const std::string& surfaceInputName, const std::string& primvarName, const VtValue& fallbackValue)
        {
            VtValue castValue = fallbackValue;
            if (fallbackValue.GetType() == SdfValueTypeNames->Double.GetType())
            {
                castValue = VtValue::Cast<float>(fallbackValue);
            }
            return addPrimvarShaderToPreviewMaterial(material, surfaceInputName, primvarName, castValue);
        },
        arg("material"),
        arg("surfaceInputName"),
        arg("primvarName"),
        arg("fallbackValue") = nullptr,
        R"(
            Adds a Primvar Reader shader to the preview material and connects it to a surface input.

            It is expected that the material was created by ``definePreviewMaterial()``.

            Args:
                - material: The material prim
                - surfaceInputName: The name of the input on the surface shader (not including the ``inputs:`` prefix, eg. ``diffuseColor``)
                - primvarName: The name of the primvar to read (not including the ``primvars:`` prefix, eg. ``paintColor``)
                - fallbackValue: An optional fallback value to use if the primvar is not found
            Returns:
                Whether the primvar shader was successfully added and connected.
        )"
    );

    m.def(
        "connectPrimvarShader",
        [](UsdShadeInput& shaderInput, const std::string& primvarName, const VtValue& fallbackValue)
        {
            VtValue castValue = fallbackValue;
            if (fallbackValue.GetType() == SdfValueTypeNames->Double.GetType())
            {
                castValue = VtValue::Cast<float>(fallbackValue);
            }
            return connectPrimvarShader(shaderInput, primvarName, castValue);
        },
        arg("shaderInput"),
        arg("primvarName"),
        arg("fallbackValue") = nullptr,
        R"(
            Connects a surface input to a primvar reader shader.

            A primvar reader shader will be created if it does not already exist.

            Args:
                shaderInput: The surface input (``UsdShade.Input``) to connect the primvar reader to
                primvarName: The name of the primvar to read (not including the ``primvars:`` prefix, eg. ``paintColor``)
                fallbackValue: An optional fallback value to use if the primvar is not found

            Returns:
                Whether or not the primvar shader was connected to the surface input
        )"
    );

    m.def(
        "addPreviewMaterialInterface",
        &addPreviewMaterialInterface,
        arg("material"),
        R"(
            Adds ``UsdShade.Inputs`` to the material prim to create an "interface" to the underlying Preview Shader network.

            All non-default-value ``UsdShade.Inputs`` on the effective surface shader for the universal render context will be "promoted" to the
            ``UsdShade.Material`` as new ``UsdShade.Inputs``. They will be connected to the original source inputs on the shaders, to drive those
            values, and they will be authored with a value matching what had been set on the shader inputs at the time this function was called.

            Additionally, ``UsdUVTexture.file`` inputs on connected shaders will be promoted to the material, following the same logic as direct
            surface inputs.

            Note:

                It is preferable to author all initial shader attributes (including textures) *before* calling ``addPreviewMaterialInterface()``.

            Warning:

                This function will fail if there is any other render context driving the material surface. It is only suitable for use on Preview
                Shader networks, such as the network generated by ``definePreviewMaterial()`` and its associated ``add*Texture`` functions. If you
                require multiple contexts, you should instead construct a Material Interface directly, or with targetted end-user interaction.

            Args:
                material: The material prim

            Returns:
                Whether or not the Material inputs were added successfully
        )"
    );

    m.def(
        "removeMaterialInterface",
        &removeMaterialInterface,
        arg("material"),
        arg("bakeValues") = true,
        R"(
            Removes any ``UsdShade.Inputs`` found on the material prim.

            All ``UsdShade.Inputs`` on the ``UsdShade.Material`` will be disconnected from any underlying shader inputs, then removed from the
            material. The current values may be optionally "baked down" onto the shader inputs in order to retain the current material behavior,
            or may be discarded in order to revert to a default appearance based on the shader definitions.

            Note:

                While ``addPreviewMaterialInterface`` is specific to Preview Material shader networks, ``removeMaterialInterface`` *affects all
                render contexts* and will remove all ``UsdShade.Inputs`` returned via ``UsdShade.Material.GetInterfaceInputs()``, baking down the
                values onto all consumer shaders, regardless of render context.

            Args:
                material: The material prim
                bakeValues: Whether or not the current Material inputs values are set on the underlying Shader inputs

            Returns:
                Whether or not the Material inputs were removed successfully
        )"
    );

    ::enum_<ColorSpace>(m, "ColorSpace", "Texture color space (encoding) types")
        .value("eAuto", ColorSpace::eAuto, "Check for gamma or metadata in the texture itself")
        .value(
            "eRaw",
            ColorSpace::eRaw,
            "Use linear sampling (typically used for Normal, Roughness, Metallic, Opacity textures, or when using high dynamic range file formats like EXR)"
        )
        .value("eSrgb", ColorSpace::eSrgb, "Use sRGB sampling (typically used for Diffuse textures when using PNG files)");

    m.def(
        "getColorSpaceToken",
        &getColorSpaceToken,
        arg("value"),
        R"(
            Get the `str` matching a given `ColorSpace`

            The string representation is typically used when setting shader inputs, such as ``inputs:sourceColorSpace`` on ``UsdUVTexture``.

            Args:
                value: The ``ColorSpace``

            Returns:
                The `str` for the given ``ColorSpace`` value
        )"
    );

    m.def(
        "sRgbToLinear",
        &sRgbToLinear,
        arg("color"),
        R"(
            Translate an sRGB color value to linear color space

            Many 3D modeling applications define colors in sRGB (0-1) color space. Many others use a linear color space that aligns with how light
            and color behave in the natural world. When authoring ``UsdShade.Shader`` color input data, including external texture assets, you may
            need to translate between color spaces.

            Note:

                Color is a complex topic in 3D rendering and providing utilities covering the full breadth of color science is beyond the scope of this
                module. See this [MathWorks article](https://www.mathworks.com/help/images/understanding-color-spaces-and-color-space-conversion.html)
                for a relatively brief introduction. If you need more specific color handling please use a dedicated color science library like
                [OpenColorIO](https://opencolorio.org).

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

            Many 3D modeling applications define colors in sRGB (0-1) color space. Many others use a linear color space that aligns with how light
            and color behave in the natural world. When authoring ``UsdShade.Shader`` color input data, including external texture assets, you may
            need to translate between color spaces.

            Note:

                Color is a complex topic in 3D rendering and providing utilities covering the full breadth of color science is beyond the scope of this
                module. See this [MathWorks article](https://www.mathworks.com/help/images/understanding-color-spaces-and-color-space-conversion.html)
                for a relatively brief introduction. If you need more specific color handling please use a dedicated color science library like
                [OpenColorIO](https://opencolorio.org).

            Args:
                color: linear representation of a color to be translated to sRGB color space

            Returns:
                The translated color in sRGB color space
        )"
    );
}

} // namespace usdex::core::bindings
