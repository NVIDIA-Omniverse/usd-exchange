// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
        "bindMaterialSubsets",
        &bindMaterialSubsets,
        arg("subsets"),
        arg("materials"),
        R"(
            Binds materials to the given geometry subsets.

            Note:
                ``subsets`` and ``materials`` must have the same length; each material is bound to the subset at the same index.

            Args:
                subsets: List of ``UsdGeom.Subset`` objects to receive bindings
                materials: List of ``UsdShade.Material`` objects, one per subset

            Returns:
                Whether all materials were successfully bound to their subsets.
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
        "computeEffectiveMtlxSurfaceShader",
        &computeEffectiveMtlxSurfaceShader,
        arg("material"),
        R"(
            Get the effective surface Shader of a Material for the MaterialX render context.

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
        "defineGlassPreviewMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const GfVec3f&, const float, const float, const float>(&defineGlassPreviewMaterial),
        arg("stage"),
        arg("path"),
        arg("color"),
        arg("indexOfRefraction") = 1.5f,
        arg("roughness") = 0.02f,
        arg("opacity") = 0.2f,
        R"(
            Defines a Glass PBR ``UsdShade.Material`` driven by a ``UsdPreviewSurface`` shader network for the universal render context.

            The input parameters reflect a subset of the `UsdPreviewSurface specification <https://openusd.org/release/spec_usdpreviewsurface.html>`_ commonly.
            To make the color take effect, opacity must be used to make the material sufficiently opaque.

            Parameters:
                - **stage** - The stage on which to define the Material
                - **path** - The absolute prim path at which to define the Material
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, minimum 1.0; suggested maximum 4.0
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid object on error.
        )"
    );

    m.def(
        "defineGlassPreviewMaterial",
        overload_cast<UsdPrim, const std::string&, const GfVec3f&, const float, const float, const float>(&defineGlassPreviewMaterial),
        arg("parent"),
        arg("name"),
        arg("color"),
        arg("indexOfRefraction") = 1.5f,
        arg("roughness") = 0.02f,
        arg("opacity") = 0.2f,
        R"(
            Defines a Glass PBR ``UsdShade.Material`` driven by a ``UsdPreviewSurface`` shader network for the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the Material
                - **name** - Name of the Material
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, minimum 1.0; suggested maximum 4.0
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid object on error.
        )"
    );

    m.def(
        "defineGlassPreviewMaterial",
        overload_cast<UsdPrim, const GfVec3f&, const float, const float, const float>(&defineGlassPreviewMaterial),
        arg("prim"),
        arg("color"),
        arg("indexOfRefraction") = 1.5f,
        arg("roughness") = 0.02f,
        arg("opacity") = 0.2f,
        R"(
            Defines a Glass PBR ``UsdShade.Material`` driven by a ``UsdPreviewSurface`` shader network for the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the material on. The prim's type will be set to ``UsdShade.Material``.
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, minimum 1.0; suggested maximum 4.0
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid object on error.
        )"
    );

    m.def(
        "addEmissiveColorToPreviewMaterial",
        &addEmissiveColorToPreviewMaterial,
        arg("material"),
        arg("color"),
        R"(
            Adds an emissive color to a preview material

            It is expected that the material was created by ``definePreviewMaterial()``

            Args:
                material: The material prim
                color: The emissive color

            Returns:
                Whether or not the emissive color was added to the material
        )"
    );

    m.def(
        "definePbrMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const GfVec3f&, const float, const float, const float>(&definePbrMaterial),
        arg("stage"),
        arg("path"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.3f,
        arg("metallic") = 0.0f,
        R"(
            Defines an OpenPBR ``UsdShade.Material`` interface that drives both an OpenPBR MaterialX render context and the universal render context.

            Parameters:
                - **stage** - The stage on which to define the Material
                - **path** - The absolute prim path at which to define the Material
                - **color** - The base color of the Material
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid object on error.
        )"
    );

    m.def(
        "definePbrMaterial",
        overload_cast<UsdPrim, const std::string&, const GfVec3f&, const float, const float, const float>(&definePbrMaterial),
        arg("parent"),
        arg("name"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.3f,
        arg("metallic") = 0.0f,
        R"(
            Defines an OpenPBR ``UsdShade.Material`` interface that drives both an OpenPBR MaterialX render context and the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the Material
                - **name** - Name of the Material
                - **color** - The base color of the Material
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid object on error.
        )"
    );

    m.def(
        "definePbrMaterial",
        overload_cast<UsdPrim, const GfVec3f&, const float, const float, const float>(&definePbrMaterial),
        arg("prim"),
        arg("color"),
        arg("opacity") = 1.0f,
        arg("roughness") = 0.3f,
        arg("metallic") = 0.0f,
        R"(
            Defines an OpenPBR ``UsdShade.Material`` interface that drives both an OpenPBR MaterialX render context and the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the material on. The prim's type will be set to ``UsdShade.Material``.
                - **color** - The base color of the Material
                - **opacity** - The Opacity Amount to set, 0.0-1.0 range where 1.0 = opaque and 0.0 = invisible
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **metallic** - The Metallic Amount to set, 0.0-1.0 range where 1.0 = max metallic and 0.0 = no metallic

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid object on error.
        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "defineGlassPbrMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const GfVec3f&, const float, const float, const float>(&defineGlassPbrMaterial),
        arg("stage"),
        arg("path"),
        arg("color"),
        arg("indexOfRefraction") = 1.5f,
        arg("roughness") = 0.02f,
        arg("previewOpacity") = 0.2f,
        R"(
            Defines a Glass ``UsdShade.Material`` interface that drives both an OpenPBR MaterialX render context and the universal render context.

            Note:
                This function generates an `OpenPBR Surface <https://academysoftwarefoundation.github.io/OpenPBR/>`_ MaterialX shader for the
                MaterialX render context and a ``UsdPreviewSurface`` shader for the universal render context.
                Material inputs are created to control the look:

                - **color** - The glass color
                - **ior** - Index of Refraction
                - **roughness** - Specular roughness for the glass surface
                - **opacity** - Controls ``UsdPreviewSurface`` opacity only; OpenPBR glass transparency is handled via ``transmission_weight``

            Parameters:
                - **stage** - The stage on which to define the Material
                - **path** - The absolute prim path at which to define the Material
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, minimum 1.0; soft maximum 3.0
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **previewOpacity** - The Opacity Amount to set on ``UsdPreviewSurface``, 0.0-1.0 range where 1.0 = opaque and 0.0 = transparent

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid prim on error
        )"
    );

    m.def(
        "defineGlassPbrMaterial",
        overload_cast<UsdPrim, const std::string&, const GfVec3f&, const float, const float, const float>(&defineGlassPbrMaterial),
        arg("parent"),
        arg("name"),
        arg("color"),
        arg("indexOfRefraction") = 1.5f,
        arg("roughness") = 0.02f,
        arg("previewOpacity") = 0.2f,
        R"(
            Defines a Glass ``UsdShade.Material`` interface that drives both an OpenPBR MaterialX render context and the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Note:
                This function generates an `OpenPBR Surface <https://academysoftwarefoundation.github.io/OpenPBR/>`_ MaterialX shader for the
                MaterialX render context and a ``UsdPreviewSurface`` shader for the universal render context.
                Material inputs are created to control the look:

                - **color** - The glass color
                - **ior** - Index of Refraction
                - **roughness** - Specular roughness for the glass surface
                - **opacity** - Controls ``UsdPreviewSurface`` opacity only; OpenPBR glass transparency is handled via ``transmission_weight``

            Parameters:
                - **parent** - Prim below which to define the Material
                - **name** - Name of the Material
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, minimum 1.0; soft maximum 3.0
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **previewOpacity** - The Opacity Amount to set on ``UsdPreviewSurface``, 0.0-1.0 range where 1.0 = opaque and 0.0 = transparent

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid prim on error
        )"
    );

    m.def(
        "defineGlassPbrMaterial",
        overload_cast<UsdPrim, const GfVec3f&, const float, const float, const float>(&defineGlassPbrMaterial),
        arg("prim"),
        arg("color"),
        arg("indexOfRefraction") = 1.5f,
        arg("roughness") = 0.02f,
        arg("previewOpacity") = 0.2f,
        R"(
            Defines a Glass ``UsdShade.Material`` interface that drives both an OpenPBR MaterialX render context and the universal render context.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Note:
                This function generates an `OpenPBR Surface <https://academysoftwarefoundation.github.io/OpenPBR/>`_ MaterialX shader for the
                MaterialX render context and a ``UsdPreviewSurface`` shader for the universal render context.
                Material inputs are created to control the look:

                - **color** - The glass color
                - **ior** - Index of Refraction
                - **roughness** - Specular roughness for the glass surface
                - **opacity** - Controls ``UsdPreviewSurface`` opacity only; OpenPBR glass transparency is handled via ``transmission_weight``

            Parameters:
                - **prim** - Prim to define the material on. The prim's type will be set to ``UsdShade.Material``.
                - **color** - The color of the Material
                - **indexOfRefraction** - The Index of Refraction to set, minimum 1.0; soft maximum 3.0
                - **roughness** - The Roughness Amount to set, 0.0-1.0 range where 1.0 = flat and 0.0 = glossy
                - **previewOpacity** - The Opacity Amount to set on ``UsdPreviewSurface``, 0.0-1.0 range where 1.0 = opaque and 0.0 = transparent

            Returns:
                The newly defined ``UsdShade.Material``. Returns an Invalid object on error.
        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "addEmissiveColorToPbrMaterial",
        &addEmissiveColorToPbrMaterial,
        arg("material"),
        arg("color"),
        arg("luminance") = 1000.0f,
        R"(
            Adds an emissive color and luminance to an OpenPBR material

            It is expected that the material was created by ``definePbrMaterial()``

            This drives the OpenPBR ``emission_color`` and ``emission_luminance`` inputs in the MaterialX render context, and the
            UsdPreviewSurface ``emissiveColor`` input in the universal render context. Two material interface inputs are created (or reused)
            to share these values across both render contexts: ``emissiveColor`` (Color3) and ``emissiveLuminance`` (Float).

            Note:

                ``emissiveLuminance`` is in ``cd/m^2`` (Candelas per square meter, also known as Nits), per the
                `OpenPBR Surface specification <https://academysoftwarefoundation.github.io/OpenPBR/>`_. UsdPreviewSurface does not have a
                separate luminance input, so the universal render context only receives the emissive color (without luminance scaling).

            Args:
                material: The material prim
                color: The emissive color
                luminance: The emissive luminance in ``cd/m^2`` (Nits). Must be at least 0.0 (no upper bound). Defaults to 1000.0, which is
                    roughly the brightness of an indoor LED light panel and produces a clearly visible emission in most scenes.

            Returns:
                Whether or not the emissive color was added to the material
        )"
    );

    m.def(
        "addColorTextureToPbrMaterial",
        &addColorTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds a color texture to an OpenPBR material

            It is expected that the material was created by ``definePbrMaterial()``

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

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
            Adds a normals texture to an OpenPBR material

            It is expected that the material was created by ``definePbrMaterial()``

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

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
            Adds an ORM (occlusion, roughness, metallic) texture to an OpenPBR material

            It is expected that the material was created by ``definePbrMaterial()``

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

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
            Adds a single channel roughness texture to an OpenPBR material

            It is expected that the material was created by ``definePbrMaterial()``

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

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
            Adds a single channel metallic texture to an OpenPBR material

            It is expected that the material was created by ``definePbrMaterial()``

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

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
            Adds a single channel opacity texture to an OpenPBR material

            It is expected that the material was created by ``definePbrMaterial()``

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addEmissiveTextureToPbrMaterial",
        &addEmissiveTextureToPbrMaterial,
        arg("material"),
        arg("texturePath"),
        arg("luminance") = 1000.0f,
        R"(
            Adds an emissive color texture to an OpenPBR material

            It is expected that the material was created by ``definePbrMaterial()``

            In addition to the texture, this also creates (or reuses) the ``emissiveLuminance`` material interface input that drives the OpenPBR
            ``emission_luminance`` shader input, so the texture is properly scaled by an emission strength. The supplied ``luminance`` value will
            overwrite any value previously authored by ``addEmissiveColorToPbrMaterial()``.

            Note:

                ``emissiveLuminance`` is in ``cd/m^2`` (Candelas per square meter, also known as Nits), per the
                `OpenPBR Surface specification <https://academysoftwarefoundation.github.io/OpenPBR/>`_. UsdPreviewSurface does not have a
                separate luminance input, so the universal render context only receives the emissive texture (without luminance scaling).

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture
                luminance: The emissive luminance in ``cd/m^2`` (Nits). Must be at least 0.0 (no upper bound). Defaults to 1000.0, which is
                    roughly the brightness of an indoor LED light panel and produces a clearly visible emission in most scenes.

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addPrimvarShaderToPbrMaterial",
        [](UsdShadeMaterial& material, const std::string& surfaceInputName, const std::string& primvarName, const VtValue& fallbackValue)
        {
            VtValue castValue = fallbackValue;
            if (fallbackValue.GetType() == SdfValueTypeNames->Double.GetType())
            {
                castValue = VtValue::Cast<float>(fallbackValue);
            }
            return addPrimvarShaderToPbrMaterial(material, surfaceInputName, primvarName, castValue);
        },
        arg("material"),
        arg("surfaceInputName"),
        arg("primvarName"),
        arg("fallbackValue") = nullptr,
        R"(
            Adds a Primvar Reader shader to the OpenPBR material and connects it to a surface input.

            It is expected that the material was created by ``definePbrMaterial()``.

            Note:

                This function will only work on the surface shader ``open_pbr_surface_surfaceshader``, not shaders within the shader network.
                For connecting inputs within a shader network, use ``connectPrimvarShader()``.

            Args:
                material: The material prim
                surfaceInputName: The name of the input on the surface shader (not including the ``inputs:`` prefix, eg. ``base_color``)
                primvarName: The name of the primvar to read (not including the ``primvars:`` prefix, eg. ``paintColor``)
                fallbackValue: An optional fallback value to use if the primvar is not found
            Returns:
                Whether the primvar shader was successfully added and connected.
        )"
    );

    m.def(
        "addColorTextureToPreviewMaterial",
        &addColorTextureToPreviewMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds a color texture to a preview material

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``)
            and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.

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

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``)
            and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.

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
            and the B channel represents metallic/metalness.

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``)
            and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.

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

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``)
            and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.

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

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``)
            and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.

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

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``)
            and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.

            Args:
                material: The material prim
                texturePath: The ``Sdf.AssetPath`` for the texture

            Returns:
                Whether or not the texture was added to the material
        )"
    );

    m.def(
        "addEmissiveTextureToPreviewMaterial",
        &addEmissiveTextureToPreviewMaterial,
        arg("material"),
        arg("texturePath"),
        R"(
            Adds an emissive color texture to a preview material

            It is expected that the material was created by ``definePreviewMaterial()``

            The texture will be sampled using texture coordinates from the default UV set (generally named ``primvars:st``)
            and will be set to "repeat", wrapping around the texture if UV coordinates exceed the [0,1] range in either axis.

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

            Note:

                This function will only work on the surface shader ``UsdPreviewSurface``, not shaders within the shader network.
                For connecting inputs within a shader network, use ``connectPrimvarShader()``.

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
            Connects a shader input to a primvar reader shader.

            A primvar reader shader will be created if it does not already exist.

            Args:
                shaderInput: The shader input (``UsdShade.Input``) to connect the primvar reader to
                primvarName: The name of the primvar to read (not including the ``primvars:`` prefix, eg. ``paintColor``)
                fallbackValue: An optional fallback value to use if the primvar is not found

            Returns:
                Whether or not the primvar shader was connected to the shader input
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
                require multiple contexts, you should instead construct a Material Interface directly, or with targeted end-user interaction.

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
