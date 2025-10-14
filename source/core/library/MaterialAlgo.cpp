// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/MaterialAlgo.h"

#include "usdex/core/NameAlgo.h"
#include "usdex/core/StageAlgo.h"

#include <pxr/base/tf/stringUtils.h>
#include <pxr/usd/ar/resolver.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usdGeom/tokens.h>
#include <pxr/usd/usdShade/materialBindingAPI.h>
#include <pxr/usd/usdShade/nodeGraph.h>
#include <pxr/usd/usdShade/tokens.h>
#include <pxr/usd/usdUtils/pipeline.h>

#include <unordered_map>

using namespace pxr;

namespace
{

TF_DEFINE_PRIVATE_TOKENS(
    _tokens,
    ((invalid, ""))
    ((colorSpaceAuto, "auto"))
    ((colorSpaceRaw, "raw"))
    ((colorSpacesRBG, "sRGB"))
    // UsdPreviewSurface Shaders
    ((upsId, "UsdPreviewSurface"))
    ((uvTexId, "UsdUVTexture"))
    // Default shader names
    ((upsName, "PreviewSurface"))
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

bool isShaderType(const UsdShadeShader& shader, const TfToken& shaderId)
{
    TfToken test;
    return shader && shader.GetShaderId(&test) && test == shaderId;
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
    // Create the texture shader
    SdfPath shaderPath = material.GetPath().AppendChild(shaderName);
    UsdShadeShader texShader = UsdShadeShader::Define(material.GetPrim().GetStage(), shaderPath);
    texShader.SetShaderId(_tokens->uvTexId);
    texShader.CreateInput(_tokens->fallback, SdfValueTypeNames->Float4).Set(fallback);
    texShader.CreateInput(_tokens->file, SdfValueTypeNames->Asset).Set(texture);
    texShader.CreateInput(_tokens->sourceColorSpace, SdfValueTypeNames->Token).Set(getColorSpaceToken(colorSpace));

    UsdShadeInput stInput = texShader.CreateInput(_tokens->st, SdfValueTypeNames->Float2);
    bool connected = usdex::core::connectPrimvarShader(stInput, UsdUtilsGetPrimaryUVSetName().GetString());
    if (!connected)
    {
        return UsdShadeShader();
    }

    return texShader;
}

// Check if the file extension for the texture asset matches a set of known 8 bit texture formats
// Note, the UsdShadInput provided is expected to be for an SdfAssetPath for the shader's texture file input
bool isEightBitTextureFormat(const UsdShadeInput& textureAssetPathInput)
{
    SdfAssetPath resolvedTexturePath;
    textureAssetPathInput.Get(&resolvedTexturePath);

    static const std::vector<std::string> s_eightBitFormats = { "bmp", "tga", "jpg", "jpeg", "png", "tif" };
    std::string ext = ArGetResolver().GetExtension(resolvedTexturePath.GetResolvedPath());
    return std::find(s_eightBitFormats.begin(), s_eightBitFormats.end(), ext) != s_eightBitFormats.end();
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

bool isSupportedPrimvarType(const UsdShadeInput& shaderInput)
{
    static const std::vector<SdfValueTypeName> supportedTypes = {
        SdfValueTypeNames->Color3f,  SdfValueTypeNames->Color4f, SdfValueTypeNames->Float,    SdfValueTypeNames->Float2,
        SdfValueTypeNames->Float3,   SdfValueTypeNames->Float4,  SdfValueTypeNames->Int,      SdfValueTypeNames->String,
        SdfValueTypeNames->Normal3f, SdfValueTypeNames->Point3f, SdfValueTypeNames->Vector3f, SdfValueTypeNames->Matrix4d
    };
    return std::find(supportedTypes.begin(), supportedTypes.end(), shaderInput.GetTypeName()) != supportedTypes.end();
}

//! Get the shader ID and type name for a primvar reader shader
//!
//! color3f/4f shader input types are converted to float3/4 types for the outputs and fallback values
//! normal3f/point3f/vector3f/matrix4d shader input types use a "role" name for the shader ID
//! see USD Preview Surface Shader specification: https://openusd.org/release/spec_usdpreviewsurface.html#primvar-reader
//!
//! @param shaderInput The input to the primvar reader shader
//! @param outTypeName The type name of the primvar reader shader (returned by reference)
//! @returns The shader ID for the primvar reader shader
TfToken getPrimvarShaderId(const UsdShadeInput& shaderInput, SdfValueTypeName& outTypeName, std::string& outTypeRoleName)
{
    static constexpr const char* primvarReaderIdPrefix = "UsdPrimvarReader_";

    static const std::unordered_map<SdfValueTypeName, SdfValueTypeName, SdfValueTypeNameHash> typeNameMap = {
        { SdfValueTypeNames->Color3f, SdfValueTypeNames->Float3 },
        { SdfValueTypeNames->Color4f, SdfValueTypeNames->Float4 },
    };

    static const std::unordered_map<SdfValueTypeName, const char*, SdfValueTypeNameHash> typeNameRoleMap = {
        { SdfValueTypeNames->Normal3f, "normal" },
        { SdfValueTypeNames->Point3f, "point" },
        { SdfValueTypeNames->Vector3f, "vector" },
        { SdfValueTypeNames->Matrix4d, "matrix" },
    };

    outTypeName = shaderInput.GetTypeName();
    if (typeNameMap.find(outTypeName) != typeNameMap.end())
    {
        outTypeName = typeNameMap.at(outTypeName);
    }

    // Some primvar types (normal, point, vector, matrix) have unexpected shader IDs
    outTypeRoleName = outTypeName.GetAsToken().GetString();
    if (typeNameRoleMap.find(outTypeName) != typeNameRoleMap.end())
    {
        outTypeRoleName = typeNameRoleMap.at(outTypeName);
    }
    return TfToken(TfStringPrintf("%s%s", primvarReaderIdPrefix, outTypeRoleName.c_str()));
}

TfToken getPrimvarShaderName(const std::string& primvarName, const std::string& typeRoleName)
{
    static constexpr const char* primvarReaderNamePrefix = "Primvar_";
    // Make the primvar name valid for the shader prim by first replacing any ':' with '_'
    std::string validPrimvarName = primvarName;
    std::replace(validPrimvarName.begin(), validPrimvarName.end(), ':', '_');
    std::string validShaderName = TfStringPrintf("%s%s_%s", primvarReaderNamePrefix, validPrimvarName.c_str(), typeRoleName.c_str());
    return usdex::core::getValidPrimName(validShaderName);
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

    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim.GetStage(), prim.GetPath(), &reason))
    {
        TF_WARN("Cannot bind material due to an invalid location: %s", reason.c_str());
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

UsdShadeMaterial usdex::core::definePreviewMaterial(
    UsdPrim prim,
    const GfVec3f& color,
    const float opacity,
    const float roughness,
    const float metallic
)
{
    // Early out if the prim is not valid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial on invalid prim");
        return UsdShadeMaterial();
    }

    TfToken originalType = prim.GetTypeName();
    // Material is NOT Xformable, so check if converting from Xform to non-Xformable
    if (originalType == UsdGeomTokens->Xform)
    {
        TF_RUNTIME_ERROR(
            "Cannot redefine at \"%s\" from \"Xform\" to \"Material\" because Material is not Xformable",
            prim.GetPath().GetAsString().c_str()
        );
        return UsdShadeMaterial();
    }

    // Warn if converting from non-Scope prims
    if (originalType != UsdGeomTokens->Scope && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"Material\". Expected original type to be \"\" or \"Scope\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
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
    if (colorInput)
    {
        UsdShadeAttributeVector valueAttrs = colorInput.GetValueProducingAttributes();
        if (!valueAttrs.empty())
        {
            valueAttrs[0].Get(&color);
            if (valueAttrs[0] == colorInput.GetAttr())
            {
                colorInput.GetAttr().Clear();
            }
        }
    }
    else
    {
        colorInput = surface.CreateInput(_tokens->color, SdfValueTypeNames->Color3f);
    }
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

    if (isEightBitTextureFormat(textureReader.GetInput(_tokens->file)))
    {
        // set the scale and bias to adjust normals into tangent space
        textureReader.CreateInput(_tokens->scale, SdfValueTypeNames->Float4).Set(GfVec4f(2, 2, 2, 1));
        textureReader.CreateInput(_tokens->bias, SdfValueTypeNames->Float4).Set(GfVec4f(-1, -1, -1, 0));
    }

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
    if (roughnessInput)
    {
        UsdShadeAttributeVector valueAttrs = roughnessInput.GetValueProducingAttributes();
        if (!valueAttrs.empty())
        {
            valueAttrs[0].Get(&roughness);
            if (valueAttrs[0] == roughnessInput.GetAttr())
            {
                roughnessInput.GetAttr().Clear();
            }
        }
    }
    else
    {
        roughnessInput = surface.CreateInput(_tokens->roughness, SdfValueTypeNames->Float);
    }
    UsdShadeInput metallicInput = surface.GetInput(_tokens->metallic);
    if (metallicInput)
    {
        UsdShadeAttributeVector valueAttrs = metallicInput.GetValueProducingAttributes();
        if (!valueAttrs.empty())
        {
            valueAttrs[0].Get(&metallic);
            if (valueAttrs[0] == metallicInput.GetAttr())
            {
                metallicInput.GetAttr().Clear();
            }
        }
    }
    else
    {
        metallicInput = surface.CreateInput(_tokens->metallic, SdfValueTypeNames->Float);
    }
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
    if (roughnessInput)
    {
        UsdShadeAttributeVector valueAttrs = roughnessInput.GetValueProducingAttributes();
        if (!valueAttrs.empty())
        {
            valueAttrs[0].Get(&roughness);
            if (valueAttrs[0] == roughnessInput.GetAttr())
            {
                roughnessInput.GetAttr().Clear();
            }
        }
    }
    else
    {
        roughnessInput = surface.CreateInput(_tokens->roughness, SdfValueTypeNames->Float);
    }
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
    if (metallicInput)
    {
        UsdShadeAttributeVector valueAttrs = metallicInput.GetValueProducingAttributes();
        if (!valueAttrs.empty())
        {
            valueAttrs[0].Get(&metallic);
            if (valueAttrs[0] == metallicInput.GetAttr())
            {
                metallicInput.GetAttr().Clear();
            }
        }
    }
    else
    {
        metallicInput = surface.CreateInput(_tokens->metallic, SdfValueTypeNames->Float);
    }
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
    if (opacityInput)
    {
        UsdShadeAttributeVector valueAttrs = opacityInput.GetValueProducingAttributes();
        if (!valueAttrs.empty())
        {
            valueAttrs[0].Get(&opacity);
            if (valueAttrs[0] == opacityInput.GetAttr())
            {
                opacityInput.GetAttr().Clear();
            }
        }
    }
    else
    {
        opacityInput = surface.CreateInput(_tokens->opacity, SdfValueTypeNames->Float);
    }

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

bool usdex::core::addPrimvarShaderToPreviewMaterial(
    UsdShadeMaterial& material,
    const std::string& surfaceInputName,
    const std::string& primvarName,
    const VtValue& fallbackValue
)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // Get the input and type name needed to create the primvar reader
    UsdShadeInput shaderInput = surface.GetInput(TfToken(surfaceInputName));
    if (shaderInput)
    {
        return usdex::core::connectPrimvarShader(shaderInput, primvarName, fallbackValue);
    }
    else
    {
        TF_WARN(
            "Cannot add primvar <%s> to input <%s> on surface shader <%s> because there is no input with that name",
            primvarName.c_str(),
            surfaceInputName.c_str(),
            surface.GetPrim().GetPath().GetAsString().c_str()
        );
        return false;
    }
}

bool usdex::core::connectPrimvarShader(pxr::UsdShadeInput& shaderInput, const std::string& primvarName, const pxr::VtValue& fallbackValue)
{
    if (!shaderInput)
    {
        TF_WARN("UsdShadeInput is not valid.");
        return false;
    }
    if (primvarName.empty() || primvarName != usdex::core::getValidPropertyName(primvarName))
    {
        TF_WARN(
            "Cannot connect primvar <%s> to input <%s> because the primvar name is invalid",
            primvarName.c_str(),
            shaderInput.GetBaseName().GetText()
        );
        return false;
    }

    UsdShadeShader surface = UsdShadeShader(shaderInput.GetPrim());
    if (!surface)
    {
        TF_WARN("UsdShadeInput <%s> is not contained within a surface shader.", shaderInput.GetBaseName().GetText());
        return false;
    }

    if (!isSupportedPrimvarType(shaderInput))
    {
        TF_WARN(
            "Cannot connect primvar <%s> to input <%s> on surface shader <%s> because the input type <%s> is not supported by UsdPreviewSurface",
            primvarName.c_str(),
            shaderInput.GetBaseName().GetText(),
            surface.GetPrim().GetPath().GetAsString().c_str(),
            shaderInput.GetTypeName().GetAsToken().GetText()
        );
        return false;
    }

    // This is the only functionality that we need from connectableAPIBehavior
    if (shaderInput.GetConnectability() == UsdShadeTokens->interfaceOnly)
    {
        TF_WARN(
            "Cannot connect primvar <%s> to input <%s> on surface shader <%s> because its connectability is interfaceOnly",
            primvarName.c_str(),
            shaderInput.GetBaseName().GetText(),
            surface.GetPrim().GetPath().GetAsString().c_str()
        );
        return false;
    }

    SdfValueTypeName outputTypeName;
    std::string primvarRoleName;
    const TfToken shaderId = ::getPrimvarShaderId(shaderInput, outputTypeName, primvarRoleName);

    // Acquire the primvar reader, named as "Primvar_$primvarName_$typeName"
    const TfToken shaderName = ::getPrimvarShaderName(primvarName, primvarRoleName);
    SdfPath path = surface.GetPrim().GetParent().GetPath().AppendChild(shaderName);

    bool primvarReaderCreated = false;
    UsdShadeShader primvarReader = UsdShadeShader::Get(shaderInput.GetPrim().GetStage(), path);
    if (!primvarReader)
    {
        primvarReaderCreated = true;
        primvarReader = UsdShadeShader::Define(shaderInput.GetPrim().GetStage(), path);
        if (!primvarReader)
        {
            TF_WARN(
                "Cannot add Primvar Reader shader <%s> to <%s>",
                path.GetAsString().c_str(),
                surface.GetPrim().GetParent().GetPath().GetAsString().c_str()
            );
            return false;
        }
    }

    // Whether or not the shader already existed, make sure that the attributes work for the primvar reader
    primvarReader.SetShaderId(shaderId);
    primvarReader.CreateInput(_tokens->varname, SdfValueTypeNames->String).Set(primvarName);
    UsdShadeOutput primvarOutput = primvarReader.CreateOutput(_tokens->result, outputTypeName);

    // Set the fallback value if it is provided
    if (!fallbackValue.IsEmpty())
    {
        if (outputTypeName.GetType() == fallbackValue.GetType())
        {
            primvarReader.CreateInput(_tokens->fallback, outputTypeName).Set(fallbackValue);
        }
        else
        {
            TF_WARN(
                "Cannot set fallback on primvar reader <%s> because value type <%s> does not match input type <%s>, no fallback value will be set",
                primvarReader.GetPath().GetAsString().c_str(),
                fallbackValue.GetType().GetTypeName().c_str(),
                outputTypeName.GetAsToken().GetText()
            );
        }
    }

    // If the output already exists with a different type we need to update the output type name manually
    if (primvarOutput.GetTypeName() != outputTypeName)
    {
        TF_RUNTIME_ERROR(
            "Cannot connect primvar <%s> to input <%s> because the existing shader output type <%s> does not match the input type <%s>",
            primvarName.c_str(),
            shaderInput.GetBaseName().GetText(),
            primvarOutput.GetTypeName().GetAsToken().GetText(),
            outputTypeName.GetAsToken().GetText()
        );
        return false;
    }

    // Connect the primvar reader output to the surface shader input
    bool connected = shaderInput.ConnectToSource(primvarOutput);
    if (!connected)
    {
        TF_WARN("Cannot connect primvar <%s> to input <%s>", primvarName.c_str(), shaderInput.GetBaseName().GetText());
        // Remove the primvar reader if it was created
        if (primvarReaderCreated)
        {
            primvarReader.GetPrim().GetStage()->RemovePrim(primvarReader.GetPrim().GetPath());
        }
        return false;
    }
    // Remove the authored value from the input so the connection provides the only opinion
    shaderInput.GetAttr().Clear();

    return true;
}

bool usdex::core::addPreviewMaterialInterface(pxr::UsdShadeMaterial& material)
{
    if (!material)
    {
        TF_RUNTIME_ERROR("UsdShadeMaterial <%s> is not valid.", material.GetPath().GetAsString().c_str());
        return false;
    }

    UsdShadeShader previewSurface = computeEffectivePreviewSurfaceShader(material);
    if (!previewSurface)
    {
        TF_RUNTIME_ERROR(
            "UsdShadeMaterial <%s> does not have a valid surface shader for the universal render context.",
            material.GetPath().GetAsString().c_str()
        );
        return false;
    }

    // Ensure this is the only surface shader. The implementation of this function is ill-suited for multi render context shader networks, as one
    // of the primary goals of Material Interfaces are to be a common interface across all render contexts. This function will instead produce
    // inputs that are uniquely named based on the UsdPreviewSurface specification, and may not map one-to-one with other contexts.
    UsdShadeAttributeVector effectiveSurfaceOutputs;
    for (const UsdShadeOutput& output : material.GetSurfaceOutputs())
    {
        for (const auto& outputAttr : output.GetValueProducingAttributes())
        {
            effectiveSurfaceOutputs.push_back(outputAttr);
        }
    }
    if (effectiveSurfaceOutputs.size() > 1 || effectiveSurfaceOutputs.empty())
    {
        TF_RUNTIME_ERROR(
            "UsdShadeMaterial <%s> has %zu effective surface outputs. This function is not suitable for multi-context shader networks.",
            material.GetPath().GetAsString().c_str(),
            size_t(effectiveSurfaceOutputs.size()) // explicit cast as the type changed from uint32_t to size_t in usd 24.08
        );
        return false;
    }

    std::vector<TfToken> inputNames;
    std::vector<UsdShadeInput> inputsToPromote;
    for (UsdShadeInput input : previewSurface.GetInputs(/* onlyAuthored */ true))
    {
        for (auto inputAttr : input.GetValueProducingAttributes())
        {
            // Direct value producing inputs with authored values should be promoted
            if (UsdShadeUtils::GetType(inputAttr.GetName()) == UsdShadeAttributeType::Input && inputAttr.HasAuthoredValue())
            {
                TfToken baseName = UsdShadeUtils::GetBaseNameAndType(inputAttr.GetName()).first;
                UsdShadeShader inputShader = UsdShadeShader(inputAttr.GetPrim());
                inputsToPromote.push_back(inputShader.GetInput(baseName));
                inputNames.push_back(baseName);
            }
            else if (UsdShadeUtils::GetType(inputAttr.GetName()) == UsdShadeAttributeType::Output)
            {
                // We can't generally determine which inputs on a shader are relevant to the given output. It may be be all inputs
                // or may be some specific subset. We can make an exception for UsdUvTexture shaders, as we know the `file` input
                // is the primary user-facing input.
                // FUTURE: Consider a parameter to control this. Maybe we should cross the shader boundary for all shaders, or for
                // some user specified subset.
                UsdShadeShader inputShader = UsdShadeShader(inputAttr.GetPrim());
                if (isShaderType(inputShader, _tokens->uvTexId))
                {
                    inputsToPromote.push_back(inputShader.GetInput(_tokens->file));
                    inputNames.push_back(inputShader.GetPrim().GetName());
                }
            }
        }
    }

    for (size_t i = 0; i < inputsToPromote.size(); ++i)
    {
        TfToken& sourceName = inputNames[i];
        UsdShadeInput& destination = inputsToPromote[i];
        // the source might already exist, because a previously promoted input could be listed multiple times
        UsdShadeInput source = material.GetInput(sourceName);
        if (!source)
        {
            // FUTURE: consider handling SdrMetadata
            source = material.CreateInput(sourceName, destination.GetTypeName());
        }

        // transfer the current value from destination to source
        VtValue value;
        if (destination.Get(&value) && !source.Set(value))
        {
            TF_WARN(
                "Failed to transfer value from <%s> to <%s>",
                destination.GetAttr().GetPath().GetAsString().c_str(),
                source.GetAttr().GetPath().GetAsString().c_str()
            );
        }

        if (destination.ConnectToSource(source))
        {
            // remove the authored value from the destination, so the connection provides the only opinion
            destination.GetAttr().Clear();
        }
        else
        {
            TF_WARN(
                "Failed to connect <%s> to <%s>",
                source.GetAttr().GetPath().GetAsString().c_str(),
                destination.GetAttr().GetPath().GetAsString().c_str()
            );
        }
    }

    return true;
}

bool usdex::core::removeMaterialInterface(UsdShadeMaterial& material, bool bakeValues)
{
    if (!material)
    {
        TF_RUNTIME_ERROR("UsdShadeMaterial <%s> is not valid.", material.GetPath().GetAsString().c_str());
        return false;
    }

    bool overallStatus = true;
    for (UsdShadeNodeGraph::InterfaceInputConsumersMap::value_type& pair : material.ComputeInterfaceInputConsumersMap())
    {
        bool status = true;
        UsdShadeInput input = pair.first;
        std::vector<UsdShadeInput>& destinations = pair.second;
        for (UsdShadeInput& dest : destinations)
        {
            // first attempt to clear the source connection. in the simple case of a single layer / non-composed connection this will be sufficient.
            dest.ClearSources();
            // if the connection comes via composition, it may have survived the clear, and we need to explicitly disconnect it
            if (!dest.GetConnectedSources().empty() && !dest.DisconnectSource(input.GetAttr()))
            {
                // if disconnecting failed, we need to track the result and warn the caller
                status = false;
                overallStatus = false;
                TF_WARN(
                    "Failed to disconnect <%s> from <%s>",
                    dest.GetAttr().GetPath().GetAsString().c_str(),
                    input.GetAttr().GetPath().GetAsString().c_str()
                );
            }

            if (bakeValues)
            {
                VtValue value;
                if (input.Get(&value) && !dest.Set(value))
                {
                    TF_WARN(
                        "Failed to transfer value from <%s> to <%s>",
                        input.GetAttr().GetPath().GetAsString().c_str(),
                        dest.GetAttr().GetPath().GetAsString().c_str()
                    );
                }
            }
        }
        if (!status)
        {
            // we shouldn't remove the input if there are still connected destinations
            // we don't need to emit a diagnostic as the warning will have been emitted above
            continue;
        }

        // finally, remove the input from the material
        if (!input.GetPrim().RemoveProperty(input.GetFullName()))
        {
            // if the input comes from composition, the best we can do is block it
            input.GetAttr().Block();
        }
    }

    return overallStatus;
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
            TF_CODING_ERROR("Invalid ColorSpace value: %d", static_cast<int>(value));
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
