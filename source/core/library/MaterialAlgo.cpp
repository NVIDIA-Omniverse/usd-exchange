// SPDX-FileCopyrightText: Copyright (c) 2022-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "usdex/core/MaterialAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/usd/usdShade/materialBindingAPI.h>
#include <pxr/usd/usdShade/tokens.h>
#include <pxr/usd/usdUtils/pipeline.h>

using namespace pxr;

namespace
{

// Warnings generated by USD 23.11
#if defined(ARCH_OS_WINDOWS) && PXR_VERSION < 2405
#pragma warning(push)
#pragma warning(disable : 4003) // not enough arguments for function-like macro invocation
#endif
// clang-format off
TF_DEFINE_PRIVATE_TOKENS(
    _tokens,
    ((invalid, ""))
    ((colorSpaceAuto, "auto"))
    ((colorSpaceRaw, "raw"))
    ((colorSpacesRBG, "sRGB"))
    // UsdPreviewSurface Shaders
    ((upsId, "UsdPreviewSurface"))
    ((uvReaderId, "UsdPrimvarReader_float2"))
    ((uvTexId, "UsdUVTexture"))
    // Default shader names
    ((upsName, "PreviewSurface"))
    ((uvReaderName, "TexCoordReader"))
    ((uvTexDiffuseName, "DiffuseTexture"))
    ((uvTexNormalsName, "NormalTexture"))
    ((uvTexORMName, "ORMTexture"))
    ((uvTexRoughnessName, "RoughnessTexture"))
    ((uvTexMetallicName, "MetallicTexture"))
    ((uvTexOpacityName, "OpacityTexture"))
    // UsdPreviewSurface I/O
    ((color, "diffuseColor"))
    ((normal, "normal"))
    ((occlusion, "occlusion"))
    ((metallic, "metallic"))
    ((roughness, "roughness"))
    ((opacity, "opacity"))
    ((opacityThreshold, "opacityThreshold"))
    ((ior, "ior"))
    // UsdUVTexture I/O
    ((file, "file"))
    ((sourceColorSpace, "sourceColorSpace"))
    ((st, "st"))
    ((fallback, "fallback"))
    ((scale, "scale"))
    ((bias, "bias"))
    ((rgb, "rgb"))
    ((r, "r"))
    ((g, "g"))
    ((b, "b"))
    // UsdPrimvarReader_float2 I/O
    ((varname, "varname"))
    ((result, "result"))
);
// clang-format on
// Warnings generated by USD 23.11
#if defined(ARCH_OS_WINDOWS) && PXR_VERSION < 2405
#pragma warning(pop)
#endif

bool isShaderType(const UsdShadeShader& shader, const TfToken& shaderId)
{
    TfToken test;
    return shader && shader.GetShaderId(&test) && test == shaderId;
}

// Find or create a float2 texture coordinate primvar reader
UsdShadeShader acquireTexCoordReader(UsdShadeMaterial& material)
{
    SdfPath path = material.GetPath().AppendChild(_tokens->uvReaderName);
    UsdShadeShader uvReader = UsdShadeShader::Get(material.GetPrim().GetStage(), path);
    if (!uvReader)
    {
        uvReader = UsdShadeShader::Define(material.GetPrim().GetStage(), path);
        if (!uvReader)
        {
            TF_RUNTIME_ERROR(
                "Cannot add USD Preview Surface Primvar Reader shader <%s> to <%s>",
                uvReader.GetPath().GetAsString().c_str(),
                material.GetPath().GetAsString().c_str()
            );

            return UsdShadeShader();
        }
    }

    // Whether the shader already existed or not, make sure that the attributes work for the primvar reader
    uvReader.SetShaderId(_tokens->uvReaderId);
    uvReader.CreateInput(_tokens->varname, SdfValueTypeNames->Token).Set(UsdUtilsGetPrimaryUVSetName());
    uvReader.CreateOutput(_tokens->result, SdfValueTypeNames->Float2);

    return uvReader;
}

// Find or create the appropriate TextureReader
UsdShadeShader acquireTextureReader(
    UsdShadeMaterial& material,
    const TfToken& shaderName,
    const SdfAssetPath& texture,
    usdex::core::ColorSpace colorSpace,
    const GfVec4f& fallback
)
{
    // Make sure there is a primvar reader for the UV data ("st")
    UsdShadeShader uvReader = ::acquireTexCoordReader(material);
    if (!uvReader)
    {
        return UsdShadeShader();
    }

    // Create the texture shader
    SdfPath shaderPath = material.GetPath().AppendChild(shaderName);
    UsdShadeShader texShader = UsdShadeShader::Define(material.GetPrim().GetStage(), shaderPath);
    texShader.SetShaderId(_tokens->uvTexId);
    texShader.CreateInput(_tokens->fallback, SdfValueTypeNames->Float4).Set(fallback);
    texShader.CreateInput(_tokens->file, SdfValueTypeNames->Asset).Set(texture);
    texShader.CreateInput(_tokens->sourceColorSpace, SdfValueTypeNames->Token).Set(getColorSpaceToken(colorSpace));
    texShader.CreateInput(_tokens->st, SdfValueTypeNames->Float2).ConnectToSource(uvReader.GetOutput(_tokens->result));

    return texShader;
}

float toLinear(float value)
{
    if (value <= 0.04045f)
    {
        return value / 12.92f;
    }
    else
    {
        float adjusted = (value + 0.055f) / 1.055f;
        return std::pow(adjusted, 2.4f);
    }
}

float fromLinear(float value)
{
    float test = value * 12.92f;
    if (test <= 0.04045f)
    {
        return test;
    }
    else
    {
        float scaled = std::pow(value, 1.0f / 2.4f);
        return (scaled * 1.055f) - 0.055f;
    }
}

} // namespace

UsdShadeMaterial usdex::core::createMaterial(UsdPrim parent, const std::string& name)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_WARN("Unable to create UsdShadeMaterial due to an invalid location: %s", reason.c_str());
        return UsdShadeMaterial();
    }

    SdfPath materialPath = parent.GetPath().AppendChild(TfToken(name));
    UsdStagePtr stage = parent.GetStage();

    UsdShadeMaterial material = UsdShadeMaterial::Define(stage, materialPath);
    return material;
}

bool usdex::core::bindMaterial(UsdPrim prim, const UsdShadeMaterial& material)
{
    UsdPrim matPrim = material.GetPrim();
    if (!matPrim && !prim)
    {
        TF_WARN(
            "UsdPrim <%s> and UsdShadeMaterial <%s> are not valid, cannot bind material to prim",
            prim.GetPath().GetAsString().c_str(),
            material.GetPath().GetAsString().c_str()
        );
        return false;
    }
    if (!matPrim)
    {
        TF_WARN("UsdShadeMaterial <%s> is not valid, cannot bind material to prim", matPrim.GetPath().GetAsString().c_str());
        return false;
    }
    if (!prim)
    {
        TF_WARN("UsdPrim <%s> is not valid, cannot bind material to prim", prim.GetPath().GetAsString().c_str());
        return false;
    }
    UsdShadeMaterialBindingAPI materialBinding = UsdShadeMaterialBindingAPI::Apply(prim);
    return materialBinding.Bind(material);
}

UsdShadeShader usdex::core::computeEffectivePreviewSurfaceShader(const UsdShadeMaterial& material)
{
    if (!material)
    {
        return UsdShadeShader();
    }

    return material.ComputeSurfaceSource({ UsdShadeTokens->universalRenderContext });
}

UsdShadeMaterial usdex::core::definePreviewMaterial(
    UsdStagePtr stage,
    const SdfPath& path,
    const GfVec3f& color,
    const float opacity,
    const float roughness,
    const float metallic
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial due to an invalid location: %s", reason.c_str());
        return UsdShadeMaterial();
    }

    // The opacity value must be within the defined min/max range
    if (opacity < 0.0 || opacity > 1.0)
    {
        reason = TfStringPrintf("Opacity value %f is outside range [0.0 - 1.0].", opacity);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // The roughness value must be within the defined min/max range
    if (roughness < 0.0 || roughness > 1.0)
    {
        reason = TfStringPrintf("Roughness value %f is outside range [0.0 - 1.0].", roughness);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // The metallic value must be within the defined min/max range
    if (metallic < 0.0 || metallic > 1.0)
    {
        reason = TfStringPrintf("Metallic value %f is outside range [0.0 - 1.0].", metallic);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // Define the material. We do not use usdex::core::createMaterial here to avoid double validations.
    UsdShadeMaterial material = UsdShadeMaterial::Define(stage, path);
    if (!material)
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial at \"%s\"", path.GetAsString().c_str());
        return UsdShadeMaterial();
    }

    // Early out if the proposed child shader prim location is invalid
    if (!usdex::core::isEditablePrimLocation(material.GetPrim(), _tokens->upsName, &reason))
    {
        // FUTURE: Cleanup the material prim we just created
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeShader named \"%s\" as a child of \"%s\"",
            _tokens->upsName.GetString().c_str(),
            path.GetAsString().c_str()
        );
        return UsdShadeMaterial();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = material.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Define the surface shader to be used in the universal rendering context
    SdfPath shaderPath = path.AppendChild(_tokens->upsName);
    UsdShadeShader shader = UsdShadeShader::Define(stage, shaderPath);
    shader.SetShaderId(_tokens->upsId);
    material.CreateSurfaceOutput().ConnectToSource(shader.CreateOutput(UsdShadeTokens->surface, SdfValueTypeNames->Token));
    material.CreateDisplacementOutput().ConnectToSource(shader.CreateOutput(UsdShadeTokens->displacement, SdfValueTypeNames->Token));

    // Create default shader inputs to produce a physically based rendering result with the supplied values
    shader.CreateInput(_tokens->color, SdfValueTypeNames->Color3f).Set(color);
    shader.CreateInput(_tokens->opacity, SdfValueTypeNames->Float).Set(opacity);
    shader.CreateInput(_tokens->roughness, SdfValueTypeNames->Float).Set(roughness);
    shader.CreateInput(_tokens->metallic, SdfValueTypeNames->Float).Set(metallic);

    return material;
}

UsdShadeMaterial usdex::core::definePreviewMaterial(
    UsdPrim parent,
    const std::string& name,
    const GfVec3f& color,
    const float opacity,
    const float roughness,
    const float metallic
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial due to an invalid location: %s", reason.c_str());
        return UsdShadeMaterial();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::definePreviewMaterial(stage, path, color, opacity, roughness, metallic);
}

bool usdex::core::addDiffuseTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // read the current color to use as the fallback for when the texture is missing
    // it should have been created by `definePreviewMaterial()` but just incase someone decides
    // to call this function with their own UsdPreviewSurface wired in, we can accommodate
    GfVec3f color(0.0f, 0.0f, 0.0f);
    UsdShadeInput colorInput = surface.GetInput(_tokens->color);
    if (!colorInput)
    {
        colorInput = surface.CreateInput(_tokens->color, SdfValueTypeNames->Color3f);
        colorInput.Set(color);
    }
    colorInput.Get(&color);
    GfVec4f fallback(color[0], color[1], color[2], 1.0f);

    UsdShadeShader textureReader = ::acquireTextureReader(material, _tokens->uvTexDiffuseName, texturePath, ColorSpace::eAuto, fallback);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface shader "diffuseColor" to the diffuse texture shader output
    colorInput.ConnectToSource(textureReader.CreateOutput(_tokens->rgb, SdfValueTypeNames->Float3));

    return true;
}

bool usdex::core::addNormalTextureToPreviewMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    GfVec4f fallback(0.0f, 0.0f, 1.0f, 1.0f);
    UsdShadeShader textureReader = ::acquireTextureReader(material, _tokens->uvTexNormalsName, texturePath, ColorSpace::eRaw, fallback);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface shader "normal" to the normals texture shader output
    UsdShadeOutput texShaderOutput = textureReader.CreateOutput(_tokens->rgb, SdfValueTypeNames->Float3);
    surface.CreateInput(_tokens->normal, SdfValueTypeNames->Normal3f).ConnectToSource(texShaderOutput);

    // set the scale and bias to adjust normals into tangent space
    // note we are assuming the texture is an 8-bit channel that requires adjustment,
    // since we can't directly access the texture (it might not even exist yet).
    textureReader.CreateInput(_tokens->scale, SdfValueTypeNames->Float4).Set(GfVec4f(2, 2, 2, 1));
    textureReader.CreateInput(_tokens->bias, SdfValueTypeNames->Float4).Set(GfVec4f(-1, -1, -1, 0));

    return true;
}

bool usdex::core::addOrmTextureToPreviewMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // read the current roughness and metallic to use as the fallback for when the texture is missing
    // they should have been created by `definePreviewMaterial()` but just incase someone decides
    // to call this function with their own UsdPreviewSurface wired in, we can accommodate
    float roughness = 0.5f;
    float metallic = 0.0f;
    UsdShadeInput occlusionInput = surface.CreateInput(_tokens->occlusion, SdfValueTypeNames->Float);
    UsdShadeInput roughnessInput = surface.GetInput(_tokens->roughness);
    if (!roughnessInput)
    {
        roughnessInput = surface.CreateInput(_tokens->roughness, SdfValueTypeNames->Float);
        roughnessInput.Set(roughness);
    }
    UsdShadeInput metallicInput = surface.GetInput(_tokens->metallic);
    if (!metallicInput)
    {
        metallicInput = surface.CreateInput(_tokens->metallic, SdfValueTypeNames->Float);
        metallicInput.Set(metallic);
    }
    surface.GetInput(_tokens->roughness).Get(&roughness);
    surface.GetInput(_tokens->metallic).Get(&metallic);
    GfVec4f fallback(1.0f, roughness, metallic, /* unused */ 1.0f);

    UsdShadeShader textureReader = ::acquireTextureReader(material, _tokens->uvTexORMName, texturePath, ColorSpace::eRaw, fallback);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface shader "occlusion", "roughness", "metallic" to the ORM tex shader outputs
    // unlike most textures, ORM needs to drive multiple floats on the surface
    occlusionInput.ConnectToSource(textureReader.CreateOutput(_tokens->r, SdfValueTypeNames->Float));
    roughnessInput.ConnectToSource(textureReader.CreateOutput(_tokens->g, SdfValueTypeNames->Float));
    metallicInput.ConnectToSource(textureReader.CreateOutput(_tokens->b, SdfValueTypeNames->Float));

    return true;
}

bool usdex::core::addRoughnessTextureToPreviewMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // read the current roughness to use as the fallback for when the texture is missing
    // it should have been created by `definePreviewMaterial()` but just incase someone decides to call this function
    // with their own UsdPreviewSurface wired in, we can accommodate
    float roughness = 0.5f;
    UsdShadeInput roughnessInput = surface.GetInput(_tokens->roughness);
    if (!roughnessInput)
    {
        roughnessInput = surface.CreateInput(_tokens->roughness, SdfValueTypeNames->Float);
        roughnessInput.Set(roughness);
    }
    surface.GetInput(_tokens->roughness).Get(&roughness);
    GfVec4f fallback(roughness, /* unused */ 0.0f, /* unused */ 0.0f, /* unused */ 1.0f);

    UsdShadeShader textureReader = ::acquireTextureReader(material, _tokens->uvTexRoughnessName, texturePath, ColorSpace::eRaw, fallback);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface shader "roughness" to the roughness tex shader output
    roughnessInput.ConnectToSource(textureReader.CreateOutput(_tokens->r, SdfValueTypeNames->Float));

    return true;
}

bool usdex::core::addMetallicTextureToPreviewMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // read the current metallic to use as the fallback for when the texture is missing
    // it should have been created by `definePreviewMaterial()` but just incase someone decides
    // to call this function with their own UsdPreviewSurface wired in, we can accommodate
    float metallic = 0.0f;
    UsdShadeInput metallicInput = surface.GetInput(_tokens->metallic);
    if (!metallicInput)
    {
        metallicInput = surface.CreateInput(_tokens->metallic, SdfValueTypeNames->Float);
        metallicInput.Set(metallic);
    }
    surface.GetInput(_tokens->metallic).Get(&metallic);
    GfVec4f fallback(metallic, /* unused */ 0.0f, /* unused */ 0.0f, /* unused */ 1.0f);

    UsdShadeShader textureReader = ::acquireTextureReader(material, _tokens->uvTexMetallicName, texturePath, ColorSpace::eRaw, fallback);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface "metallic" to the metallic tex shader output
    metallicInput.ConnectToSource(textureReader.CreateOutput(_tokens->r, SdfValueTypeNames->Float));

    return true;
}


bool usdex::core::addOpacityTextureToPreviewMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // read the current opacity to use as the fallback for when the texture is missing
    float opacity = 1.0f;
    UsdShadeInput opacityInput = surface.GetInput(_tokens->opacity);
    if (!opacityInput)
    {
        opacityInput = surface.CreateInput(_tokens->opacity, SdfValueTypeNames->Float);
        opacityInput.Set(opacity);
    }
    surface.GetInput(_tokens->opacity).Get(&opacity);
    GfVec4f fallback(opacity, /* unused */ 0.0f, /* unused */ 0.0f, /* unused */ 1.0f);

    UsdShadeShader textureReader = ::acquireTextureReader(material, _tokens->uvTexOpacityName, texturePath, ColorSpace::eRaw, fallback);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface "opacity" to the opacity tex shader output
    opacityInput.ConnectToSource(textureReader.CreateOutput(_tokens->r, SdfValueTypeNames->Float));

    // IOR should be 1.0 for a PBR style material, it causes mask/opacity issues if not
    surface.CreateInput(_tokens->ior, SdfValueTypeNames->Float).Set(1.0f);
    // Geometric cutouts work better with opacity threshold set to above 0
    surface.CreateInput(_tokens->opacityThreshold, SdfValueTypeNames->Float).Set(std::numeric_limits<float>::epsilon());

    return true;
}

const pxr::TfToken& usdex::core::getColorSpaceToken(ColorSpace value)
{
    switch (value)
    {
        case usdex::core::ColorSpace::eAuto:
        {
            return _tokens->colorSpaceAuto;
        }
        case usdex::core::ColorSpace::eRaw:
        {
            return _tokens->colorSpaceRaw;
        }
        case usdex::core::ColorSpace::eSrgb:
        {
            return _tokens->colorSpacesRBG;
        }
        default:
        {
            TF_CODING_ERROR("Invalid ColorSpace value: %d", value);
            return _tokens->invalid;
        }
    }
}

GfVec3f usdex::core::sRgbToLinear(const GfVec3f& color)
{
    return GfVec3f(toLinear(color[0]), toLinear(color[1]), toLinear(color[2]));
}

GfVec3f usdex::core::linearToSrgb(const GfVec3f& color)
{
    return GfVec3f(fromLinear(color[0]), fromLinear(color[1]), fromLinear(color[2]));
}
