// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/MaterialAlgo.h"

#include "usdex/core/NameAlgo.h"
#include "usdex/core/StageAlgo.h"

#include <pxr/base/gf/color.h>
#include <pxr/base/gf/colorSpace.h>
#include <pxr/base/tf/stringUtils.h>
#include <pxr/base/vt/dictionary.h>
#include <pxr/usd/ar/resolver.h>
#include <pxr/usd/sdf/attributeSpec.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usdGeom/tokens.h>
#include <pxr/usd/usdShade/materialBindingAPI.h>
#include <pxr/usd/usdShade/nodeGraph.h>
#include <pxr/usd/usdShade/tokens.h>
#include <pxr/usd/usdUtils/pipeline.h>

#if PXR_VERSION >= 2511
#include <pxr/usd/usd/attributeLimits.h>
#endif

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
    // Material interface metadata
    ((uiMin, "uimin"))
    ((uiMax, "uimax"))
    ((uiSoftMin, "uisoftmin"))
    ((uiSoftMax, "uisoftmax"))
    ((limits, "limits"))
    ((hard, "hard"))
    ((soft, "soft"))
    ((minimum, "minimum"))
    ((maximum, "maximum"))
    // UsdPreviewSurface Shaders
    ((upsId, "UsdPreviewSurface"))
    ((uvTexId, "UsdUVTexture"))
    // Default shader names
    ((upsName, "PreviewSurface"))
    ((uvTexColorName, "ColorTexture"))
    ((uvTexNormalsName, "NormalTexture"))
    ((uvTexORMName, "ORMTexture"))
    ((uvTexRoughnessName, "RoughnessTexture"))
    ((uvTexMetallicName, "MetallicTexture"))
    ((uvTexOpacityName, "OpacityTexture"))
    ((uvTexEmissiveName, "EmissiveTexture"))
    // Material interface
    ((materialColor, "color"))
    ((materialEmissiveColor, "emissiveColor"))
    ((materialEmissiveLuminance, "emissiveLuminance"))
    // UsdPreviewSurface I/O
    ((color, "diffuseColor"))
    ((emissiveColor, "emissiveColor"))
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
    ((wrapS, "wrapS"))
    ((wrapT, "wrapT"))
    // UsdPrimvarReader_float2 I/O
    ((varname, "varname"))
    ((result, "result"))
    // MaterialX render context
    ((mtlx, "mtlx"))
    // MaterialX Shader IDs
    ((openPbrSurfaceId, "ND_open_pbr_surface_surfaceshader"))
    ((tiledImageFloatId, "ND_tiledimage_float"))
    ((tiledImageColor3Id, "ND_tiledimage_color3"))
    ((tiledImageVector3Id, "ND_tiledimage_vector3"))
    ((normalMapNodeId, "ND_normalmap"))
    ((separate3Vector3Id, "ND_separate3_vector3"))
    // MaterialX common I/O
    ((mtlxDefault, "default"))
    ((mtlxOut, "out"))
    ((mtlxIn, "in"))
    ((texcoord, "texcoord"))
    ((uvtiling, "uvtiling"))
    ((uvoffset, "uvoffset"))
    ((geomprop, "geomprop"))
    // ND_separate3_vector3 outputs
    ((outx, "outx"))
    ((outy, "outy"))
    ((outz, "outz"))
    // OpenPBR shader prim name
    ((openPbrName, "OpenPBR"))
    // OpenPBR surface shader inputs
    ((base_color, "base_color"))
    ((geometry_opacity, "geometry_opacity"))
    ((specular_roughness, "specular_roughness"))
    ((base_metalness, "base_metalness"))
    ((geometry_normal, "geometry_normal"))
    ((emission_color, "emission_color"))
    ((emission_luminance, "emission_luminance"))
    // OpenPBR glass-specific inputs
    ((base_weight, "base_weight"))
    ((specular_weight, "specular_weight"))
    ((transmission_weight, "transmission_weight"))
    ((transmission_color, "transmission_color"))
    ((specular_ior, "specular_ior"))
    // OpenPBR / MaterialX texture shader prim names (prefixed to avoid conflicts with UPS prim names)
    ((mtlxBaseColorTexName, "MtlxBaseColorTexture"))
    ((mtlxNormalTexName, "MtlxNormalTexture"))
    ((mtlxORMTexName, "MtlxORMTexture"))
    ((mtlxRoughnessTexName, "MtlxRoughnessTexture"))
    ((mtlxMetallicTexName, "MtlxMetallicTexture"))
    ((mtlxOpacityTexName, "MtlxOpacityTexture"))
    ((mtlxEmissiveTexName, "MtlxEmissiveTexture"))
    ((mtlxNormalMapName, "MtlxNormalMap"))
    ((mtlxSeparateOrmName, "MtlxSeparateORM"))
);

bool isShaderType(const UsdShadeShader& shader, const TfToken& shaderId)
{
    TfToken test;
    return shader && shader.GetShaderId(&test) && test == shaderId;
}

//! Find or create the appropriate TextureReader
//!
//! @param material The material to add the texture reader to
//! @param shaderName The name of the texture reader shader to create/find
//! @param texture The path to the texture to read
//! @param colorSpace The color space of the texture
//! @param fallback The fallback value for the texture reader (can be empty to avoid setting a fallback value)
//! @returns The texture reader shader
UsdShadeShader acquirePreviewTextureReader(
    UsdShadeMaterial& material,
    const TfToken& shaderName,
    const SdfAssetPath& texture,
    usdex::core::ColorSpace colorSpace,
    const VtValue& fallback
)
{
    // Create the texture shader
    SdfPath shaderPath = material.GetPath().AppendChild(shaderName);
    UsdShadeShader texShader = UsdShadeShader::Define(material.GetPrim().GetStage(), shaderPath);
    texShader.SetShaderId(_tokens->uvTexId);
    UsdShadeInput fallbackInput = texShader.CreateInput(_tokens->fallback, SdfValueTypeNames->Float4);
    if (!fallback.IsEmpty())
    {
        fallbackInput.Set(fallback);
    }
    else if (!fallbackInput.GetAttr().HasValue())
    {
        fallbackInput.Set(VtValue(GfVec4f(0.0f, 0.0f, 0.0f, 1.0f)));
    }

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

std::string getSdrMetadataValueString(const VtValue& value)
{
    if (value.IsHolding<float>())
    {
        return TfStringPrintf("%g", value.Get<float>());
    }
    if (value.IsHolding<double>())
    {
        return TfStringPrintf("%g", value.Get<double>());
    }
    if (value.IsHolding<int>())
    {
        return TfStringPrintf("%d", value.Get<int>());
    }
    if (value.IsHolding<bool>())
    {
        return value.Get<bool>() ? "true" : "false";
    }
    if (value.IsHolding<GfVec2f>())
    {
        const GfVec2f& vec = value.Get<GfVec2f>();
        return TfStringPrintf("%g, %g", vec[0], vec[1]);
    }
    if (value.IsHolding<GfVec3f>())
    {
        const GfVec3f& vec = value.Get<GfVec3f>();
        return TfStringPrintf("%g, %g, %g", vec[0], vec[1], vec[2]);
    }
    if (value.IsHolding<GfVec4f>())
    {
        const GfVec4f& vec = value.Get<GfVec4f>();
        return TfStringPrintf("%g, %g, %g, %g", vec[0], vec[1], vec[2], vec[3]);
    }
    return TfStringify(value);
}

#if PXR_VERSION < 2511
void setLimitMetadataByField(const UsdAttribute& attr, const TfToken& category, const TfToken& bound, const VtValue& value)
{
    SdfLayerHandle layer = attr.GetStage()->GetEditTarget().GetLayer();
    if (!layer)
    {
        return;
    }

    SdfAttributeSpecHandle attrSpec = layer->GetAttributeAtPath(attr.GetPath());
    if (!attrSpec)
    {
        return;
    }

    VtDictionary limits = attrSpec->GetFieldAs<VtDictionary>(_tokens->limits);
    VtDictionary categoryLimits;
    VtDictionary::const_iterator categoryIt = limits.find(category.GetString());
    if (categoryIt != limits.end() && categoryIt->second.IsHolding<VtDictionary>())
    {
        categoryLimits = categoryIt->second.UncheckedGet<VtDictionary>();
    }

    categoryLimits[bound.GetString()] = value;
    limits[category.GetString()] = VtValue(categoryLimits);
    attrSpec->SetField(_tokens->limits, VtValue(limits));
}
#endif

void setHardMinimum(const UsdAttribute& attr, const VtValue& value)
{
#if PXR_VERSION >= 2511
    attr.GetHardLimits().SetMinimum(value);
#else
    setLimitMetadataByField(attr, _tokens->hard, _tokens->minimum, value);
#endif
}

void setHardMaximum(const UsdAttribute& attr, const VtValue& value)
{
#if PXR_VERSION >= 2511
    attr.GetHardLimits().SetMaximum(value);
#else
    setLimitMetadataByField(attr, _tokens->hard, _tokens->maximum, value);
#endif
}

void setSoftMinimum(const UsdAttribute& attr, const VtValue& value)
{
#if PXR_VERSION >= 2511
    attr.GetSoftLimits().SetMinimum(value);
#else
    setLimitMetadataByField(attr, _tokens->soft, _tokens->minimum, value);
#endif
}

void setSoftMaximum(const UsdAttribute& attr, const VtValue& value)
{
#if PXR_VERSION >= 2511
    attr.GetSoftLimits().SetMaximum(value);
#else
    setLimitMetadataByField(attr, _tokens->soft, _tokens->maximum, value);
#endif
}

void setLimitMetadata(
    const UsdShadeInput& input,
    const VtValue& min,
    const VtValue& max = VtValue(),
    const VtValue& softMin = VtValue(),
    const VtValue& softMax = VtValue()
)
{
    if (!input)
    {
        return;
    }

    const UsdAttribute attr = input.GetAttr();
    input.SetSdrMetadataByKey(_tokens->uiMin, getSdrMetadataValueString(min));
    setHardMinimum(attr, min);
    if (!max.IsEmpty())
    {
        input.SetSdrMetadataByKey(_tokens->uiMax, getSdrMetadataValueString(max));
        setHardMaximum(attr, max);
    }
    if (!softMin.IsEmpty())
    {
        input.SetSdrMetadataByKey(_tokens->uiSoftMin, getSdrMetadataValueString(softMin));
        setSoftMinimum(attr, softMin);
    }
    if (!softMax.IsEmpty())
    {
        input.SetSdrMetadataByKey(_tokens->uiSoftMax, getSdrMetadataValueString(softMax));
        setSoftMaximum(attr, softMax);
    }
}

// Check if the shader is within a Preview Surface shader network
// @note The shader ID must start with "Usd" and must be a child of a UsdShadeMaterial with a universal surface source
// This is a simplified check for the shader ID, and does not check the shader definition itself
bool isPreviewSurfaceNetworkShader(const UsdShadeShader& shader)
{
    // Check that the shader is the child of a UsdShadeMaterial with a universal surface source
    UsdShadeMaterial material = UsdShadeMaterial(shader.GetPrim().GetParent());
    if (!material || !usdex::core::computeEffectivePreviewSurfaceShader(material))
    {
        return false;
    }

    TfToken shaderId;
    shader.GetShaderId(&shaderId);
    return shaderId.GetString().find("Usd") == 0;
}

// Check if the shader is within a MaterialX shader network
// @note The shader ID must start with "ND_" and must be a child of a UsdShadeMaterial with a MaterialX surface source
// This is a simplified check for the shader ID, and does not check the shader definition itself
bool isMtlxNetworkShader(const UsdShadeShader& shader)
{
    // Check that the shader is the child of a UsdShadeMaterial with a MaterialX surface source
    UsdShadeMaterial material = UsdShadeMaterial(shader.GetPrim().GetParent());
    if (!material || !usdex::core::computeEffectiveMtlxSurfaceShader(material))
    {
        return false;
    }

    TfToken shaderId;
    shader.GetShaderId(&shaderId);
    return shaderId.GetString().find("ND_") == 0;
}

bool isSupportedPrimvarType(const UsdShadeInput& shaderInput)
{
    UsdShadeShader shader = UsdShadeShader(shaderInput.GetPrim());
    if (::isPreviewSurfaceNetworkShader(shader))
    {
        static const std::vector<SdfValueTypeName> supportedTypes = {
            SdfValueTypeNames->Color3f,  SdfValueTypeNames->Color4f, SdfValueTypeNames->Float,    SdfValueTypeNames->Float2,
            SdfValueTypeNames->Float3,   SdfValueTypeNames->Float4,  SdfValueTypeNames->Int,      SdfValueTypeNames->String,
            SdfValueTypeNames->Normal3f, SdfValueTypeNames->Point3f, SdfValueTypeNames->Vector3f, SdfValueTypeNames->Matrix4d
        };
        return std::find(supportedTypes.begin(), supportedTypes.end(), shaderInput.GetTypeName()) != supportedTypes.end();
    }
    else if (::isMtlxNetworkShader(shader))
    {
        static const std::vector<SdfValueTypeName> supportedTypes = {
            SdfValueTypeNames->Int, // ND_geompropvalue_integer
            SdfValueTypeNames->Bool, // ND_geompropvalue_boolean
            SdfValueTypeNames->Float, // ND_geompropvalue_float
            SdfValueTypeNames->Color3f, // ND_geompropvalue_color3
            SdfValueTypeNames->Color4f, // ND_geompropvalue_color4
            SdfValueTypeNames->Float2, // ND_geompropvalue_vector2
            SdfValueTypeNames->Float3, // ND_geompropvalue_vector3
            SdfValueTypeNames->Float4, // ND_geompropvalue_vector4
        };
        return std::find(supportedTypes.begin(), supportedTypes.end(), shaderInput.GetTypeName()) != supportedTypes.end();
    }
    else
    {
        return false;
    }
}

bool primTypeCheck(const UsdPrim& prim)
{
    // Early out if the prim is not valid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial on invalid prim");
        return false;
    }

    TfToken originalType = prim.GetTypeName();
    // Material is NOT Xformable, so check if converting from Xform to non-Xformable
    if (originalType == UsdGeomTokens->Xform)
    {
        TF_RUNTIME_ERROR(
            "Cannot redefine at \"%s\" from \"Xform\" to \"Material\" because Material is not Xformable",
            prim.GetPath().GetAsString().c_str()
        );
        return false;
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

    return true;
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
TfToken getPreviewSurfacePrimvarShaderId(const UsdShadeInput& shaderInput, SdfValueTypeName& outTypeName, std::string& outTypeRoleName)
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

//! Get the shader ID for a MaterialX primvar reader shader
//!
//! @param shaderInput The input to the primvar reader shader
//! @param outTypeName The type name of the primvar reader shader (returned by reference)
//! @returns The shader ID for the primvar reader shader
TfToken getMtlxPrimvarShaderId(const UsdShadeInput& shaderInput, SdfValueTypeName& outTypeName)
{
    static constexpr const char* primvarReaderIdPrefix = "ND_geompropvalue_";

    // A mapping of shader input type names to shader IDs
    static const std::unordered_map<SdfValueTypeName, const char*, SdfValueTypeNameHash> typeNameIdMap = {
        { SdfValueTypeNames->Int, "integer" },    { SdfValueTypeNames->Bool, "boolean" },   { SdfValueTypeNames->Float, "float" },
        { SdfValueTypeNames->Color3f, "color3" }, { SdfValueTypeNames->Color4f, "color4" }, { SdfValueTypeNames->Float2, "vector2" },
        { SdfValueTypeNames->Float3, "vector3" }, { SdfValueTypeNames->Float4, "vector4" },
    };
    outTypeName = shaderInput.GetTypeName();
    std::string typeId;
    if (typeNameIdMap.find(outTypeName) != typeNameIdMap.end())
    {
        typeId = typeNameIdMap.at(outTypeName);
    }

    return TfToken(TfStringPrintf("%s%s", primvarReaderIdPrefix, typeId.c_str()));
}

TfToken getPrimvarShaderName(const std::string& primvarName, const std::string& typeRoleName, const std::string& prefix = "Primvar_")
{
    // Make the primvar name valid for the shader prim by first replacing any ':' with '_'
    std::string validPrimvarName = primvarName;
    std::replace(validPrimvarName.begin(), validPrimvarName.end(), ':', '_');
    std::string validShaderName = TfStringPrintf("%s%s_%s", prefix.c_str(), validPrimvarName.c_str(), typeRoleName.c_str());
    return usdex::core::getValidPrimName(validShaderName);
}


//! Consume an input from a shader
//!
//! - if the input exists:
//!     - its value will be returned by reference in `outValue` (if there's a value authored on the input attribute)
//!     - the input value will be cleared if it is authored directly on the input attribute (rather than through a connection)
//! - if the input does not exist:
//!     - a new input will be created with the given type name
//!     - an empty value will be returned by reference in `outValue`
//!
//! @param shader The shader to consume the input from
//! @param inputName The name of the input to consume
//! @param typeName The type name of the input to consume
//! @param outValue The current value of the consumed input (returned by reference)
//! @returns The input that was consumed
UsdShadeInput consumeInput(UsdShadeShader& shader, const TfToken& inputName, const SdfValueTypeName& typeName, VtValue& outValue)
{
    if (!shader)
    {
        return UsdShadeInput();
    }

    UsdShadeInput shaderInput = shader.GetInput(inputName);
    if (shaderInput)
    {
        UsdShadeAttributeVector valueAttrs = shaderInput.GetValueProducingAttributes();
        if (!valueAttrs.empty())
        {
            // valueAttrs[0] may be a connection source rather than a direct value
            if (!valueAttrs[0].Get(&outValue))
            {
                outValue = VtValue();
            }

            // Only clear the authored value if it is authored directly on the input attribute.
            // If the value is coming from a connection, do not clear.
            if (valueAttrs[0] == shaderInput.GetAttr())
            {
                shaderInput.GetAttr().Clear();
            }
        }
        return shaderInput;
    }

    UsdShadeInput input = shader.CreateInput(inputName, typeName);
    outValue = VtValue();
    return input;
}

UsdShadeShader addPbrTiledImageShader(
    UsdShadeMaterial& material,
    const TfToken& shaderPrimName,
    const TfToken& shaderId,
    const VtValue& defaultValue,
    SdfValueTypeName outputType
)
{
    SdfPath shaderPath = material.GetPath().AppendChild(shaderPrimName);
    UsdShadeShader texShader = UsdShadeShader::Define(material.GetPrim().GetStage(), shaderPath);
    texShader.SetShaderId(shaderId);
    UsdShadeInput defaultInput = texShader.CreateInput(_tokens->mtlxDefault, outputType);
    if (!defaultValue.IsEmpty())
    {
        defaultInput.Set(defaultValue);
    }
    else if (!defaultInput.GetAttr().HasValue())
    {
        defaultInput.Set(outputType.GetDefaultValue());
    }
    texShader.CreateInput(_tokens->file, SdfValueTypeNames->Asset);
    texShader.CreateInput(_tokens->uvtiling, SdfValueTypeNames->Float2).Set(GfVec2f(1.0f, 1.0f));
    texShader.CreateInput(_tokens->uvoffset, SdfValueTypeNames->Float2).Set(GfVec2f(0.0f, 0.0f));
    UsdShadeInput texCoordInput = texShader.CreateInput(_tokens->texcoord, SdfValueTypeNames->Float2);

    bool connected = usdex::core::connectPrimvarShader(texCoordInput, UsdUtilsGetPrimaryUVSetName().GetString());
    if (!connected)
    {
        return UsdShadeShader();
    }

    texShader.CreateOutput(_tokens->mtlxOut, outputType);
    return texShader;
}

// Remove a property from a prim within the current edit target
// This is used for removing input properties from shaders and materials
void removeProperty(UsdStageRefPtr stage, const SdfPath& primPath, const TfToken& propName)
{
    SdfLayerHandle layer = stage->GetEditTarget().GetLayer();
    if (layer)
    {
        SdfPrimSpecHandle primSpec = layer->GetPrimAtPath(primPath);
        if (primSpec)
        {
            SdfPropertySpecHandle propSpec = layer->GetPropertyAtPath(primPath.AppendProperty(propName));
            if (propSpec)
            {
                primSpec->RemoveProperty(propSpec);
            }
        }
    }
}

//! Finalize the texture interface for a PBR material
//!
//! - Remove the material inputs that are no longer needed
//! - Create a new material interface input for the texture
//! - Connect the texture reader shader's file input to the material interface input
//! - Set the color space of the material interface input
//!
//! @param material The material to operate on (shaders are contained within and interface inputs are used)
//! @param texShader The texture reader shader to finalize
//! @param texturePath The path to the texture to add
//! @param materialInterfaceName The name of the material interface to connect to the texture reader's file input
//! @param colorSpace The color space of the texture
//! @param materialInputsToRemove The names of the material inputs to remove from the material
//! @returns The material interface input that was created
UsdShadeInput finalizePbrTextureInterface(
    UsdShadeMaterial& material,
    UsdShadeShader& texShader,
    const SdfAssetPath& texturePath,
    const TfToken& materialInterfaceName,
    usdex::core::ColorSpace colorSpace,
    const std::vector<TfToken>& materialInputsToRemove
)
{
    for (const TfToken& inputName : materialInputsToRemove)
    {
        UsdShadeInput matInput = material.GetInput(inputName);
        if (matInput)
        {
            ::removeProperty(material.GetPrim().GetStage(), material.GetPrim().GetPath(), matInput.GetFullName());
        }
    }

    UsdShadeInput matTextureInput = material.CreateInput(materialInterfaceName, SdfValueTypeNames->Asset);
    matTextureInput.Set(texturePath);
    matTextureInput.GetAttr().SetColorSpace(usdex::core::getColorSpaceToken(colorSpace));
    texShader.CreateInput(_tokens->file, SdfValueTypeNames->Asset).ConnectToSource(matTextureInput);
    return matTextureInput;
}

//! Connect the file input of a Preview Surface shader to a material interface input
//!
//! @param material The material to operate on (shaders are contained within and interface inputs are used)
//! @param upsInputName The name of the input from the Preview Surface shader that has a file reader shader
void connectPreviewSurfaceFileInput(UsdShadeInput& materialInput, const TfToken& upsInputName)
{
    UsdShadeMaterial material = UsdShadeMaterial(materialInput.GetPrim());
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    auto sources = previewSurface.GetInput(upsInputName).GetConnectedSources();
    if (sources.size() > 0)
    {
        sources[0].source.GetInput(_tokens->file).ConnectToSource(materialInput);
    }
}

//! Add a float texture to a PBR material
//!
//! - Add the UPS texture
//! - Get the default value for the texture reader
//! - Add the texture reader shader
//! - Connect the texture reader shader's file input to the OpenPBR shader's input
//! - Handle the material interface connection for the texture file
//! - Connect the UPS texture shader's file input to the same material interface
//!
//! @param material The material to operate on (shaders are contained within and interface inputs are used)
//! @param texturePath The path to the texture to add
//! @param surfaceInputName The name of the input on the MTLX shader that will be connected to the texture reader
//! @param defaultValue The default value to use for the texture reader
//! @param textureShaderPrimName The name of the texture reader shader to add
//! @param textureMaterialInterfaceName The name of the material interface to connect to the texture reader's file input
//! @param materialInputNameToRemove The name of the material input to remove from the material
//! @param addUpsTextureFunc The function to call to add the texture to the Preview Surface shader
//! @param upsShaderInputName The name of the input on the Preview Surface shader that will be connected to the texture reader
//! @returns Whether or not the texture was added to the material
bool addFloatTextureToPbrMaterial(
    UsdShadeMaterial& material,
    const SdfAssetPath& texturePath,
    const TfToken& surfaceInputName,
    float defaultValue,
    const TfToken& textureShaderPrimName,
    const TfToken& textureMaterialInterfaceName,
    const TfToken& materialInputNameToRemove,
    std::function<bool(UsdShadeMaterial&, const SdfAssetPath&)> addUpsTextureFunc,
    const TfToken& upsShaderInputName
)
{
    UsdShadeShader surface = usdex::core::computeEffectiveMtlxSurfaceShader(material);
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->openPbrSurfaceId) || !isShaderType(previewSurface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePbrMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // Add the UPS texture
    if (!addUpsTextureFunc(material, texturePath))
    {
        return false;
    }

    VtValue value(defaultValue);
    UsdShadeInput input = ::consumeInput(surface, surfaceInputName, SdfValueTypeNames->Float, value);

    UsdShadeShader texShader = ::addPbrTiledImageShader(
        material, // material
        textureShaderPrimName, // shaderPrimName
        _tokens->tiledImageFloatId, // shaderId
        value, // defaultValue
        SdfValueTypeNames->Float // outputType
    );
    if (!texShader)
    {
        return false;
    }
    input.ConnectToSource(texShader.GetOutput(_tokens->mtlxOut));

    UsdShadeInput matTextureInput = ::finalizePbrTextureInterface(
        material, // material
        texShader, // texShader
        texturePath, // texturePath
        textureMaterialInterfaceName, // materialInterfaceName
        usdex::core::ColorSpace::eRaw, // colorSpace
        { materialInputNameToRemove } // materialInputsToRemove
    );

    // Connect the UPS texture shader's file input to the material interface input
    ::connectPreviewSurfaceFileInput(matTextureInput, upsShaderInputName);
    return true;
}

//! Set the texture wrap mode for a given shader
//!
//! @param shader The shader to set the texture wrap mode for
//! @param wrapMode The wrap mode to set
void setTextureWrapMode(UsdShadeShader& shader, const std::string& wrapMode)
{
    const TfToken wrapModeToken = TfToken(wrapMode);
    if (isShaderType(shader, _tokens->uvTexId))
    {
        shader.CreateInput(_tokens->wrapS, SdfValueTypeNames->Token).Set(wrapModeToken);
        shader.CreateInput(_tokens->wrapT, SdfValueTypeNames->Token).Set(wrapModeToken);
    }
}

struct PrimvarReaderResult
{
    UsdShadeShader reader;
    UsdShadeOutput output;
    SdfValueTypeName outputTypeName;
    bool created = false;

    explicit operator bool() const
    {
        return reader && output;
    }
};

PrimvarReaderResult addPreviewSurfacePrimvarReader(
    const UsdShadeShader& surface,
    const UsdShadeInput& shaderInput,
    const std::string& primvarName,
    const VtValue& fallbackValue
)
{
    PrimvarReaderResult pvr;
    std::string primvarRoleName;
    const TfToken shaderId = ::getPreviewSurfacePrimvarShaderId(shaderInput, pvr.outputTypeName, primvarRoleName);
    const TfToken shaderName = ::getPrimvarShaderName(primvarName, primvarRoleName);
    SdfPath path = surface.GetPrim().GetParent().GetPath().AppendChild(shaderName);

    pvr.reader = UsdShadeShader::Get(shaderInput.GetPrim().GetStage(), path);
    if (!pvr.reader)
    {
        pvr.created = true;
        pvr.reader = UsdShadeShader::Define(shaderInput.GetPrim().GetStage(), path);
        if (!pvr.reader)
        {
            TF_WARN(
                "Cannot add Primvar Reader shader <%s> to <%s>",
                path.GetAsString().c_str(),
                surface.GetPrim().GetParent().GetPath().GetAsString().c_str()
            );
            return PrimvarReaderResult();
        }
    }

    pvr.reader.SetShaderId(shaderId);
    pvr.reader.CreateInput(_tokens->varname, SdfValueTypeNames->String).Set(primvarName);
    pvr.output = pvr.reader.CreateOutput(_tokens->result, pvr.outputTypeName);

    if (!fallbackValue.IsEmpty())
    {
        if (pvr.outputTypeName.GetType() == fallbackValue.GetType())
        {
            pvr.reader.CreateInput(_tokens->fallback, pvr.outputTypeName).Set(fallbackValue);
        }
        else
        {
            TF_WARN(
                "Cannot set fallback on primvar reader <%s> because value type <%s> does not match input type <%s>, no fallback value will be set",
                pvr.reader.GetPath().GetAsString().c_str(),
                fallbackValue.GetType().GetTypeName().c_str(),
                pvr.outputTypeName.GetAsToken().GetText()
            );
        }
    }
    return pvr;
}

PrimvarReaderResult addMtlxPrimvarReader(
    const UsdShadeShader& surface,
    const UsdShadeInput& shaderInput,
    const std::string& primvarName,
    const VtValue& fallbackValue
)
{
    PrimvarReaderResult pvr;
    const TfToken shaderId = ::getMtlxPrimvarShaderId(shaderInput, pvr.outputTypeName);
    const TfToken shaderName = ::getPrimvarShaderName(primvarName, pvr.outputTypeName.GetAsToken().GetString(), "MtlxPrimvar_");
    SdfPath path = surface.GetPrim().GetParent().GetPath().AppendChild(shaderName);

    pvr.reader = UsdShadeShader::Get(shaderInput.GetPrim().GetStage(), path);
    if (!pvr.reader)
    {
        pvr.created = true;
        pvr.reader = UsdShadeShader::Define(shaderInput.GetPrim().GetStage(), path);
        if (!pvr.reader)
        {
            TF_WARN(
                "Cannot add Primvar Reader shader <%s> to <%s>",
                path.GetAsString().c_str(),
                surface.GetPrim().GetParent().GetPath().GetAsString().c_str()
            );
            return PrimvarReaderResult();
        }
    }

    pvr.reader.SetShaderId(shaderId);
    pvr.reader.CreateInput(_tokens->geomprop, SdfValueTypeNames->String).Set(primvarName);
    pvr.output = pvr.reader.CreateOutput(_tokens->mtlxOut, pvr.outputTypeName);

    if (!fallbackValue.IsEmpty())
    {
        if (pvr.outputTypeName.GetType() == fallbackValue.GetType())
        {
            pvr.reader.CreateInput(_tokens->mtlxDefault, pvr.outputTypeName).Set(fallbackValue);
        }
        else
        {
            TF_WARN(
                "Cannot set fallback on primvar reader <%s> because value type <%s> does not match input type <%s>, no fallback value will be set",
                pvr.reader.GetPath().GetAsString().c_str(),
                fallbackValue.GetType().GetTypeName().c_str(),
                pvr.outputTypeName.GetAsToken().GetText()
            );
        }
    }
    return pvr;
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

bool usdex::core::bindMaterialSubsets(const std::vector<UsdGeomSubset>& subsets, const std::vector<UsdShadeMaterial>& materials)
{
    if (subsets.empty() || materials.empty())
    {
        TF_WARN("Unable to bind materials to subsets: The subsets or materials are empty.");
        return false;
    }
    if (subsets.size() != materials.size())
    {
        TF_WARN("Unable to bind materials to subsets: The number of subsets does not equal the number of materials.");
        return false;
    }

    // Early out if the subsets are not valid
    std::string reason;
    for (const auto& subset : subsets)
    {
        if (!usdex::core::isEditablePrimLocation(subset.GetPrim(), &reason))
        {
            std::string primPath;
            if (subset.GetPrim().IsValid())
            {
                primPath = subset.GetPath().GetAsString();
            }
            TF_WARN("Unable to bind materials to subsets: The subset <%s> is not valid: %s", primPath.c_str(), reason.c_str());
            return false;
        }
    }

    // Early out if the materials are not valid
    for (const auto& material : materials)
    {
        if (!usdex::core::isEditablePrimLocation(material.GetPrim(), &reason))
        {
            std::string primPath;
            if (material.GetPrim().IsValid())
            {
                primPath = material.GetPath().GetAsString();
            }
            TF_WARN("Unable to bind materials to subsets: The material <%s> is not valid: %s", primPath.c_str(), reason.c_str());
            return false;
        }
    }

    for (size_t i = 0; i < subsets.size(); ++i)
    {
        const UsdGeomSubset& subset = subsets[i];
        const UsdShadeMaterial& material = materials[i];

        // Bind the material to the subset
        if (!bindMaterial(subset.GetPrim(), material))
        {
            TF_WARN("Unable to bind material <%s> to subset <%s>", material.GetPath().GetAsString().c_str(), subset.GetPath().GetAsString().c_str());
        }
    }
    return true;
}

UsdShadeShader usdex::core::computeEffectivePreviewSurfaceShader(const UsdShadeMaterial& material)
{
    if (!material)
    {
        return UsdShadeShader();
    }

    return material.ComputeSurfaceSource({ UsdShadeTokens->universalRenderContext });
}

UsdShadeShader usdex::core::computeEffectiveMtlxSurfaceShader(const UsdShadeMaterial& material)
{
    if (!material)
    {
        return UsdShadeShader();
    }

    return material.ComputeSurfaceSource({ _tokens->mtlx });
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
    if (!::primTypeCheck(prim))
    {
        return UsdShadeMaterial();
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::definePreviewMaterial(stage, path, color, opacity, roughness, metallic);
}

UsdShadeMaterial usdex::core::defineGlassPreviewMaterial(
    UsdStagePtr stage,
    const SdfPath& path,
    const GfVec3f& color,
    const float indexOfRefraction,
    const float roughness,
    const float opacity
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial due to an invalid location: %s", reason.c_str());
        return UsdShadeMaterial();
    }

    // The color value must be within the defined min/max range
    if (color[0] < 0.0 || color[1] < 0.0 || color[2] < 0.0 || color[0] > 1.0 || color[1] > 1.0 || color[2] > 1.0)
    {
        reason = TfStringPrintf("Color value (%f, %f, %f) is outside range [(0, 0, 0) - (1, 1, 1)].", color[0], color[1], color[2]);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // The IOR value must be at least the physically meaningful lower bound.
    if (indexOfRefraction < 1.0f)
    {
        reason = TfStringPrintf("IOR value %f is below minimum value 1.0.", indexOfRefraction);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // The roughness value must be within the defined min/max range
    if (roughness < 0.0f || roughness > 1.0f)
    {
        reason = TfStringPrintf("Roughness value %f is outside range [0.0 - 1.0].", roughness);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // The opacity value must be within the defined min/max range
    if (opacity < 0.0f || opacity > 1.0f)
    {
        reason = TfStringPrintf("Opacity value %f is outside range [0.0 - 1.0].", opacity);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // Define the material
    UsdShadeMaterial material = usdex::core::definePreviewMaterial(stage, path, color, opacity, roughness);
    if (!material)
    {
        return UsdShadeMaterial();
    }

    // Set ior.
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    UsdShadeInput iorInput = surface.GetInput(_tokens->ior);
    if (!iorInput)
    {
        iorInput = surface.CreateInput(_tokens->ior, SdfValueTypeNames->Float);
    }
    iorInput.Set(indexOfRefraction);

    return material;
}

UsdShadeMaterial usdex::core::defineGlassPreviewMaterial(
    UsdPrim parent,
    const std::string& name,
    const GfVec3f& color,
    const float indexOfRefraction,
    const float roughness,
    const float opacity
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
    return usdex::core::defineGlassPreviewMaterial(stage, path, color, indexOfRefraction, roughness, opacity);
}

UsdShadeMaterial usdex::core::defineGlassPreviewMaterial(
    UsdPrim prim,
    const GfVec3f& color,
    const float indexOfRefraction,
    const float roughness,
    const float opacity
)
{
    if (!::primTypeCheck(prim))
    {
        return UsdShadeMaterial();
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::defineGlassPreviewMaterial(stage, path, color, indexOfRefraction, roughness, opacity);
}

bool usdex::core::addEmissiveColorToPreviewMaterial(UsdShadeMaterial& material, const GfVec3f& color)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    if (color[0] < 0.0 || color[1] < 0.0 || color[2] < 0.0)
    {
        const std::string reason = TfStringPrintf(
            "Color value (%f, %f, %f) is invalid: each component must be at least 0 (no upper bound).",
            color[0],
            color[1],
            color[2]
        );
        TF_RUNTIME_ERROR(
            "Unable to add emissive color to preview material at \"%s\" due to an invalid shader parameter value: %s",
            material.GetPath().GetAsString().c_str(),
            reason.c_str()
        );
        return false;
    }

    UsdShadeInput emissiveColorInput = surface.CreateInput(_tokens->emissiveColor, SdfValueTypeNames->Color3f);
    emissiveColorInput.Set(color);
    return true;
}

bool usdex::core::addColorTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
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
    VtValue colorValue = VtValue();
    UsdShadeInput colorInput = ::consumeInput(surface, _tokens->color, SdfValueTypeNames->Color3f, colorValue);
    if (!colorValue.IsEmpty())
    {
        // Convert the color value to a float4 with alpha 1.0
        colorValue = VtValue(GfVec4f(colorValue.Get<GfVec3f>()[0], colorValue.Get<GfVec3f>()[1], colorValue.Get<GfVec3f>()[2], 1.0f));
    }

    UsdShadeShader textureReader = ::acquirePreviewTextureReader(material, _tokens->uvTexColorName, texturePath, ColorSpace::eAuto, colorValue);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface shader "diffuseColor" to the color texture shader output
    colorInput.ConnectToSource(textureReader.CreateOutput(_tokens->rgb, SdfValueTypeNames->Float3));

    // Set the texture wrap mode to repeat
    setTextureWrapMode(textureReader, "repeat");

    return true;
}

bool usdex::core::addDiffuseTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
{
    return usdex::core::addColorTextureToPreviewMaterial(material, texturePath);
}

bool usdex::core::addNormalTextureToPreviewMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    VtValue fallbackValue = VtValue(GfVec4f(0.0f, 0.0f, 1.0f, 1.0f));
    UsdShadeShader textureReader = ::acquirePreviewTextureReader(material, _tokens->uvTexNormalsName, texturePath, ColorSpace::eRaw, fallbackValue);
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

    // Set the texture wrap mode to repeat
    setTextureWrapMode(textureReader, "repeat");

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
    VtValue fallbackValue = VtValue();
    VtValue roughnessValue(0.5f);
    VtValue metallicValue(0.0f);
    UsdShadeInput occlusionInput = surface.CreateInput(_tokens->occlusion, SdfValueTypeNames->Float);
    UsdShadeInput roughnessInput = ::consumeInput(surface, _tokens->roughness, SdfValueTypeNames->Float, roughnessValue);
    UsdShadeInput metallicInput = ::consumeInput(surface, _tokens->metallic, SdfValueTypeNames->Float, metallicValue);
    if (!roughnessValue.IsEmpty() && !metallicValue.IsEmpty())
    {
        fallbackValue = VtValue(GfVec4f(1.0f, roughnessValue.Get<float>(), metallicValue.Get<float>(), /* unused */ 1.0f));
    }

    UsdShadeShader textureReader = ::acquirePreviewTextureReader(material, _tokens->uvTexORMName, texturePath, ColorSpace::eRaw, fallbackValue);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface shader "occlusion", "roughness", "metallic" to the ORM tex shader outputs
    // unlike most textures, ORM needs to drive multiple floats on the surface
    occlusionInput.ConnectToSource(textureReader.CreateOutput(_tokens->r, SdfValueTypeNames->Float));
    roughnessInput.ConnectToSource(textureReader.CreateOutput(_tokens->g, SdfValueTypeNames->Float));
    metallicInput.ConnectToSource(textureReader.CreateOutput(_tokens->b, SdfValueTypeNames->Float));

    // Set the texture wrap mode to repeat
    setTextureWrapMode(textureReader, "repeat");

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
    VtValue fallbackValue = VtValue();
    VtValue roughnessValue(0.5f);
    UsdShadeInput roughnessInput = ::consumeInput(surface, _tokens->roughness, SdfValueTypeNames->Float, roughnessValue);
    if (!roughnessValue.IsEmpty())
    {
        fallbackValue = VtValue(GfVec4f(roughnessValue.Get<float>(), /* unused */ 0.0f, /* unused */ 0.0f, /* unused */ 1.0f));
    }

    UsdShadeShader textureReader = ::acquirePreviewTextureReader(material, _tokens->uvTexRoughnessName, texturePath, ColorSpace::eRaw, fallbackValue);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface shader "roughness" to the roughness tex shader output
    roughnessInput.ConnectToSource(textureReader.CreateOutput(_tokens->r, SdfValueTypeNames->Float));

    // Set the texture wrap mode to repeat
    setTextureWrapMode(textureReader, "repeat");

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
    VtValue fallbackValue = VtValue();
    VtValue metallicValue(0.0f);
    UsdShadeInput metallicInput = ::consumeInput(surface, _tokens->metallic, SdfValueTypeNames->Float, metallicValue);
    if (!metallicValue.IsEmpty())
    {
        fallbackValue = VtValue(GfVec4f(metallicValue.Get<float>(), /* unused */ 0.0f, /* unused */ 0.0f, /* unused */ 1.0f));
    }

    UsdShadeShader textureReader = ::acquirePreviewTextureReader(material, _tokens->uvTexMetallicName, texturePath, ColorSpace::eRaw, fallbackValue);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface "metallic" to the metallic tex shader output
    metallicInput.ConnectToSource(textureReader.CreateOutput(_tokens->r, SdfValueTypeNames->Float));

    // Set the texture wrap mode to repeat
    setTextureWrapMode(textureReader, "repeat");

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
    VtValue fallbackValue = VtValue();
    VtValue opacityValue(1.0f);
    UsdShadeInput opacityInput = ::consumeInput(surface, _tokens->opacity, SdfValueTypeNames->Float, opacityValue);
    if (!opacityValue.IsEmpty())
    {
        fallbackValue = VtValue(GfVec4f(opacityValue.Get<float>(), /* unused */ 0.0f, /* unused */ 0.0f, /* unused */ 1.0f));
    }

    UsdShadeShader textureReader = ::acquirePreviewTextureReader(material, _tokens->uvTexOpacityName, texturePath, ColorSpace::eRaw, fallbackValue);
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

    // Set the texture wrap mode to repeat
    setTextureWrapMode(textureReader, "repeat");

    return true;
}

bool usdex::core::addEmissiveTextureToPreviewMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePreviewMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // read the current emissive color to use as the fallback for when the texture is missing
    VtValue colorValue = VtValue();
    UsdShadeInput emissiveColorInput = ::consumeInput(surface, _tokens->emissiveColor, SdfValueTypeNames->Color3f, colorValue);
    if (!colorValue.IsEmpty())
    {
        // Convert the color value to a float4 with unused alpha 1.0
        colorValue = VtValue(GfVec4f(colorValue.Get<GfVec3f>()[0], colorValue.Get<GfVec3f>()[1], colorValue.Get<GfVec3f>()[2], 1.0f));
    }

    UsdShadeShader textureReader = ::acquirePreviewTextureReader(material, _tokens->uvTexEmissiveName, texturePath, ColorSpace::eAuto, colorValue);
    if (!textureReader)
    {
        return false;
    }

    // Connect the PreviewSurface "emissiveColor" to the emissive tex shader output
    emissiveColorInput.ConnectToSource(textureReader.CreateOutput(_tokens->rgb, SdfValueTypeNames->Float3));

    // Set the texture wrap mode to repeat
    setTextureWrapMode(textureReader, "repeat");

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

bool usdex::core::addPrimvarShaderToPbrMaterial(
    UsdShadeMaterial& material,
    const std::string& surfaceInputName,
    const std::string& primvarName,
    const VtValue& fallbackValue
)
{
    UsdShadeShader surface = usdex::core::computeEffectiveMtlxSurfaceShader(material);
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->openPbrSurfaceId) || !isShaderType(previewSurface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePbrMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }
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

    UsdShadeShader shader = UsdShadeShader(shaderInput.GetPrim());
    if (!shader)
    {
        TF_WARN("UsdShadeInput <%s> is not contained within a shader.", shaderInput.GetBaseName().GetText());
        return false;
    }

    if (!isSupportedPrimvarType(shaderInput))
    {
        TfToken shaderId;
        shader.GetShaderId(&shaderId);

        TF_WARN(
            "Cannot connect primvar <%s> to input <%s> on shader <%s> because the input type <%s> is not supported by %s",
            primvarName.c_str(),
            shaderInput.GetBaseName().GetText(),
            shader.GetPrim().GetPath().GetAsString().c_str(),
            shaderInput.GetTypeName().GetAsToken().GetText(),
            shaderId.GetText()
        );
        return false;
    }

    // This is the only functionality that we need from connectableAPIBehavior
    if (shaderInput.GetConnectability() == UsdShadeTokens->interfaceOnly)
    {
        TF_WARN(
            "Cannot connect primvar <%s> to input <%s> on shader <%s> because its connectability is interfaceOnly",
            primvarName.c_str(),
            shaderInput.GetBaseName().GetText(),
            shader.GetPrim().GetPath().GetAsString().c_str()
        );
        return false;
    }

    PrimvarReaderResult pvr;
    if (::isPreviewSurfaceNetworkShader(shader))
    {
        pvr = ::addPreviewSurfacePrimvarReader(shader, shaderInput, primvarName, fallbackValue);
    }
    else if (::isMtlxNetworkShader(shader))
    {
        pvr = ::addMtlxPrimvarReader(shader, shaderInput, primvarName, fallbackValue);
    }
    else
    {
        TF_WARN(
            "Cannot connect primvar <%s> to input <%s> on shader <%s> because the shader is not a Preview Surface or MaterialX shader",
            primvarName.c_str(),
            shaderInput.GetBaseName().GetText(),
            shader.GetPrim().GetPath().GetAsString().c_str()
        );
        return false;
    }

    if (!pvr)
    {
        return false;
    }

    if (pvr.output.GetTypeName() != pvr.outputTypeName)
    {
        TF_RUNTIME_ERROR(
            "Cannot connect primvar <%s> to input <%s> because the existing shader output type <%s> does not match the input type <%s>",
            primvarName.c_str(),
            shaderInput.GetBaseName().GetText(),
            pvr.output.GetTypeName().GetAsToken().GetText(),
            pvr.outputTypeName.GetAsToken().GetText()
        );
        return false;
    }

    bool connected = shaderInput.ConnectToSource(pvr.output);
    if (!connected)
    {
        TF_WARN("Cannot connect primvar <%s> to input <%s>", primvarName.c_str(), shaderInput.GetBaseName().GetText());
        if (pvr.created)
        {
            pvr.reader.GetPrim().GetStage()->RemovePrim(pvr.reader.GetPrim().GetPath());
        }
        return false;
    }
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
            effectiveSurfaceOutputs.size()
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
                // We can't generally determine which inputs on a shader are relevant to the given output. It may be all inputs
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
                // copy the color space from the input to the destination
                UsdAttribute inputAttr = input.GetAttr();
                if (inputAttr.HasColorSpace())
                {
                    UsdAttribute destAttr = dest.GetAttr();
                    destAttr.SetColorSpace(inputAttr.GetColorSpace());
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

UsdShadeMaterial usdex::core::definePbrMaterial(
    UsdStagePtr stage,
    const SdfPath& path,
    const GfVec3f& color,
    const float opacity,
    const float roughness,
    const float metallic
)
{
    // Define the Preview Material first -- it validates location, parameter ranges, and creates the UPS shader network
    UsdShadeMaterial material = usdex::core::definePreviewMaterial(stage, path, color, opacity, roughness, metallic);
    if (!material)
    {
        return UsdShadeMaterial();
    }

    // Early out if the proposed child OpenPBR shader prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(material.GetPrim(), _tokens->openPbrName, &reason))
    {
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeShader named \"%s\" as a child of \"%s\"",
            _tokens->openPbrName.GetString().c_str(),
            path.GetAsString().c_str()
        );
        return UsdShadeMaterial();
    }

    // Define the OpenPBR surface shader for the mtlx rendering context
    SdfPath shaderPath = path.AppendChild(_tokens->openPbrName);
    UsdShadeShader shader = UsdShadeShader::Define(stage, shaderPath);
    shader.SetShaderId(_tokens->openPbrSurfaceId);
    material.CreateSurfaceOutput(_tokens->mtlx).ConnectToSource(shader.CreateOutput(UsdShadeTokens->surface, SdfValueTypeNames->Token));

    // Create the shared material interface inputs (names match UPS / RTX conventions).
    // definePreviewMaterial authored values directly on the UPS shader inputs; we now create
    // material-level inputs and connect both the UPS and OpenPBR shaders to them.
    UsdShadeInput colorInput = material.CreateInput(_tokens->materialColor, SdfValueTypeNames->Color3f);
    UsdShadeInput opacityInput = material.CreateInput(_tokens->opacity, SdfValueTypeNames->Float);
    UsdShadeInput roughnessInput = material.CreateInput(_tokens->roughness, SdfValueTypeNames->Float);
    UsdShadeInput metallicInput = material.CreateInput(_tokens->metallic, SdfValueTypeNames->Float);

    // Author MaterialX OpenPBR UI limits on the material interface.
    setLimitMetadata(
        colorInput, /* input */
        VtValue(GfVec3f(0.0f, 0.0f, 0.0f)), /* min */
        VtValue(GfVec3f(1.0f, 1.0f, 1.0f)) /* max */
    );
    setLimitMetadata(
        opacityInput, /* input */
        VtValue(0.0f), /* min */
        VtValue(1.0f) /* max */
    );
    setLimitMetadata(
        roughnessInput, /* input */
        VtValue(0.0f), /* min */
        VtValue(1.0f) /* max */
    );
    setLimitMetadata(
        metallicInput, /* input */
        VtValue(0.0f), /* min */
        VtValue(1.0f) /* max */
    );

    colorInput.Set(color);
    opacityInput.Set(opacity);
    roughnessInput.Set(roughness);
    metallicInput.Set(metallic);

    // Connect the OpenPBR shader inputs to the material interface
    shader.CreateInput(_tokens->base_color, SdfValueTypeNames->Color3f).ConnectToSource(colorInput);
    shader.CreateInput(_tokens->geometry_opacity, SdfValueTypeNames->Float).ConnectToSource(opacityInput);
    shader.CreateInput(_tokens->specular_roughness, SdfValueTypeNames->Float).ConnectToSource(roughnessInput);
    shader.CreateInput(_tokens->base_metalness, SdfValueTypeNames->Float).ConnectToSource(metallicInput);

    // Connect the UPS shader inputs to the same material interface.
    // After connecting, clear the authored values that definePreviewMaterial set directly on the shader
    // so the material interface connection is the sole value source.
    UsdShadeShader previewShader = usdex::core::computeEffectivePreviewSurfaceShader(material);
    previewShader.GetInput(_tokens->color).ConnectToSource(colorInput);
    previewShader.GetInput(_tokens->opacity).ConnectToSource(opacityInput);
    previewShader.GetInput(_tokens->roughness).ConnectToSource(roughnessInput);
    previewShader.GetInput(_tokens->metallic).ConnectToSource(metallicInput);

    previewShader.GetInput(_tokens->color).GetAttr().Clear();
    previewShader.GetInput(_tokens->opacity).GetAttr().Clear();
    previewShader.GetInput(_tokens->roughness).GetAttr().Clear();
    previewShader.GetInput(_tokens->metallic).GetAttr().Clear();

    return material;
}

UsdShadeMaterial usdex::core::definePbrMaterial(
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
    return usdex::core::definePbrMaterial(stage, path, color, opacity, roughness, metallic);
}

UsdShadeMaterial usdex::core::definePbrMaterial(UsdPrim prim, const GfVec3f& color, const float opacity, const float roughness, const float metallic)
{
    if (!::primTypeCheck(prim))
    {
        return UsdShadeMaterial();
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::definePbrMaterial(stage, path, color, opacity, roughness, metallic);
}

UsdShadeMaterial usdex::core::defineGlassPbrMaterial(
    UsdStagePtr stage,
    const SdfPath& path,
    const GfVec3f& color,
    const float indexOfRefraction,
    const float roughness,
    const float previewOpacity
)
{
    // Define the Preview Material first -- it validates location, parameter ranges, and creates the UPS shader network
    UsdShadeMaterial material = defineGlassPreviewMaterial(stage, path, color, indexOfRefraction, roughness, previewOpacity);
    if (!material)
    {
        return UsdShadeMaterial();
    }

    // Early out if the proposed child OpenPBR shader prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(material.GetPrim(), _tokens->openPbrName, &reason))
    {
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeShader named \"%s\" as a child of \"%s\"",
            _tokens->openPbrName.GetString().c_str(),
            path.GetAsString().c_str()
        );
        return UsdShadeMaterial();
    }

    // Define the OpenPBR surface shader for the MaterialX render context
    SdfPath openPbrPath = path.AppendChild(_tokens->openPbrName);
    UsdShadeShader openPbrShader = UsdShadeShader::Define(stage, openPbrPath);
    openPbrShader.SetShaderId(_tokens->openPbrSurfaceId);
    material.CreateSurfaceOutput(_tokens->mtlx).ConnectToSource(openPbrShader.CreateOutput(UsdShadeTokens->surface, SdfValueTypeNames->Token));

    // Create Material Interface inputs
    UsdShadeInput materialColorInput = material.CreateInput(_tokens->materialColor, SdfValueTypeNames->Color3f);
    UsdShadeInput materialIorInput = material.CreateInput(_tokens->ior, SdfValueTypeNames->Float);
    UsdShadeInput materialRoughnessInput = material.CreateInput(_tokens->roughness, SdfValueTypeNames->Float);
    UsdShadeInput materialOpacityInput = material.CreateInput(_tokens->opacity, SdfValueTypeNames->Float);

    // Author MaterialX OpenPBR UI limits on the material interface.
    setLimitMetadata(
        materialColorInput, /* input */
        VtValue(GfVec3f(0.0f, 0.0f, 0.0f)), /* min */
        VtValue(GfVec3f(1.0f, 1.0f, 1.0f)) /* max */
    );
    setLimitMetadata(
        materialIorInput, /* input */
        VtValue(0.0f), /* min */
        VtValue(), /* max */
        VtValue(1.0f), /* softMin */
        VtValue(3.0f) /* softMax */
    );
    setLimitMetadata(
        materialRoughnessInput, /* input */
        VtValue(0.0f), /* min */
        VtValue(1.0f) /* max */
    );
    setLimitMetadata(
        materialOpacityInput, /* input */
        VtValue(0.0f), /* min */
        VtValue(1.0f) /* max */
    );

    // Set supplied values on the material interface
    materialColorInput.Set(color);
    materialIorInput.Set(indexOfRefraction);
    materialRoughnessInput.Set(roughness);
    materialOpacityInput.Set(previewOpacity);

    // Set fixed OpenPBR inputs and connect driven inputs to the material interface
    openPbrShader.CreateInput(_tokens->base_weight, SdfValueTypeNames->Float).Set(0.0f);
    openPbrShader.CreateInput(_tokens->specular_weight, SdfValueTypeNames->Float).Set(1.0f);
    openPbrShader.CreateInput(_tokens->transmission_weight, SdfValueTypeNames->Float).Set(1.0f);
    openPbrShader.CreateInput(_tokens->transmission_color, SdfValueTypeNames->Color3f).ConnectToSource(materialColorInput);
    openPbrShader.CreateInput(_tokens->specular_ior, SdfValueTypeNames->Float).ConnectToSource(materialIorInput);
    openPbrShader.CreateInput(_tokens->specular_roughness, SdfValueTypeNames->Float).ConnectToSource(materialRoughnessInput);

    // Connect UPS driven inputs to the material interface.
    // Opacity is only connected to UPS -- OpenPBR handles glass transparency via transmission_weight, not geometry_opacity.
    // After connecting, clear the authored values that definePreviewMaterial set directly on the shader
    // so the material interface connection is the sole value source.
    UsdShadeShader previewShader = usdex::core::computeEffectivePreviewSurfaceShader(material);
    previewShader.GetInput(_tokens->color).ConnectToSource(materialColorInput);
    previewShader.GetInput(_tokens->ior).ConnectToSource(materialIorInput);
    previewShader.GetInput(_tokens->opacity).ConnectToSource(materialOpacityInput);
    previewShader.GetInput(_tokens->roughness).ConnectToSource(materialRoughnessInput);

    previewShader.GetInput(_tokens->color).GetAttr().Clear();
    previewShader.GetInput(_tokens->ior).GetAttr().Clear();
    previewShader.GetInput(_tokens->opacity).GetAttr().Clear();
    previewShader.GetInput(_tokens->roughness).GetAttr().Clear();

    return material;
}

UsdShadeMaterial usdex::core::defineGlassPbrMaterial(
    UsdPrim parent,
    const std::string& name,
    const GfVec3f& color,
    const float indexOfRefraction,
    const float roughness,
    const float previewOpacity
)
{
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial due to an invalid location: %s", reason.c_str());
        return UsdShadeMaterial();
    }

    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineGlassPbrMaterial(stage, path, color, indexOfRefraction, roughness, previewOpacity);
}

UsdShadeMaterial usdex::core::defineGlassPbrMaterial(
    UsdPrim prim,
    const GfVec3f& color,
    const float indexOfRefraction,
    const float roughness,
    const float previewOpacity
)
{
    if (!::primTypeCheck(prim))
    {
        return UsdShadeMaterial();
    }

    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::defineGlassPbrMaterial(stage, path, color, indexOfRefraction, roughness, previewOpacity);
}

bool usdex::core::addEmissiveColorToPbrMaterial(UsdShadeMaterial& material, const GfVec3f& color, const float luminance)
{
    UsdShadeShader surface = usdex::core::computeEffectiveMtlxSurfaceShader(material);
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->openPbrSurfaceId) || !isShaderType(previewSurface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePbrMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    if (color[0] > 1.0 || color[1] > 1.0 || color[2] > 1.0)
    {
        const std::string r = TfStringPrintf("Color value (%f, %f, %f) is invalid: each component must be at most 1.0.", color[0], color[1], color[2]);
        TF_RUNTIME_ERROR(
            "Unable to add emissive color to OpenPBR material at \"%s\" due to an invalid shader parameter value: %s",
            material.GetPath().GetAsString().c_str(),
            r.c_str()
        );
        return false;
    }

    if (luminance < 0.0)
    {
        const std::string reason = TfStringPrintf("Luminance value %f is invalid: must be at least 0.0 (no upper bound).", luminance);
        TF_RUNTIME_ERROR(
            "Unable to add emissive color to PBR material at \"%s\" due to an invalid shader parameter value: %s",
            material.GetPath().GetAsString().c_str(),
            reason.c_str()
        );
        return false;
    }

    // Add the emissive color to the UPS shader first. This sets `emissiveColor` directly on the UPS shader; we'll re-route it through the
    // material interface below.
    if (!usdex::core::addEmissiveColorToPreviewMaterial(material, color))
    {
        return false;
    }

    // Create or reuse the material interface inputs that drive both render contexts. UsdPreviewSurface has no luminance input, so the
    // luminance interface only drives OpenPBR.
    UsdShadeInput materialEmissiveColorInput = material.CreateInput(_tokens->materialEmissiveColor, SdfValueTypeNames->Color3f);
    UsdShadeInput materialEmissiveLuminanceInput = material.CreateInput(_tokens->materialEmissiveLuminance, SdfValueTypeNames->Float);

    setLimitMetadata(
        materialEmissiveColorInput, /* input */
        VtValue(GfVec3f(0.0f, 0.0f, 0.0f)), /* min */
        VtValue(GfVec3f(1.0f, 1.0f, 1.0f)) /* max */
    );
    setLimitMetadata(
        materialEmissiveLuminanceInput, /* input */
        VtValue(0.0f), /* min */
        VtValue(), /* max */
        VtValue(), /* softMin */
        VtValue(1000.0f) /* softMax */
    );

    materialEmissiveColorInput.Set(color);
    materialEmissiveLuminanceInput.Set(luminance);

    // Connect the OpenPBR shader inputs to the material interface
    surface.CreateInput(_tokens->emission_color, SdfValueTypeNames->Color3f).ConnectToSource(materialEmissiveColorInput);
    surface.CreateInput(_tokens->emission_luminance, SdfValueTypeNames->Float).ConnectToSource(materialEmissiveLuminanceInput);

    // Connect the UPS shader's emissiveColor to the material interface and clear the direct value, so the connection is the sole opinion
    UsdShadeShader previewShader = usdex::core::computeEffectivePreviewSurfaceShader(material);
    previewShader.CreateInput(_tokens->emissiveColor, SdfValueTypeNames->Color3f).ConnectToSource(materialEmissiveColorInput);
    previewShader.GetInput(_tokens->emissiveColor).GetAttr().Clear();

    return true;
}

bool usdex::core::addColorTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectiveMtlxSurfaceShader(material);
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->openPbrSurfaceId) || !isShaderType(previewSurface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePbrMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // Add the UPS color texture first
    if (!usdex::core::addColorTextureToPreviewMaterial(material, texturePath))
    {
        return false;
    }

    // Read and remove the current color from the OpenPBR shader to use as the Mtlx texture fallback
    VtValue colorValue = VtValue();
    UsdShadeInput colorInput = ::consumeInput(surface, _tokens->base_color, SdfValueTypeNames->Color3f, colorValue);

    UsdShadeShader texShader = ::addPbrTiledImageShader(
        material, // material
        _tokens->mtlxBaseColorTexName, // shaderPrimName
        _tokens->tiledImageColor3Id, // shaderId
        colorValue, // defaultValue
        SdfValueTypeNames->Color3f // outputType
    );
    if (!texShader)
    {
        return false;
    }
    colorInput.ConnectToSource(texShader.GetOutput(_tokens->mtlxOut));

    // Create a shared material interface input for the texture file, removing the scalar color input.
    // Both the Mtlx and UPS texture shaders connect their file inputs to this.
    UsdShadeInput matTextureInput = ::finalizePbrTextureInterface(
        material, // material
        texShader, // texShader
        texturePath, // texturePath
        _tokens->uvTexColorName, // materialInterfaceName
        ColorSpace::eSrgb, // colorSpace
        { _tokens->materialColor } // materialInputsToRemove
    );

    // Connect the UPS texture shader's file input to the material interface input
    ::connectPreviewSurfaceFileInput(matTextureInput, _tokens->color);

    return true;
}

bool usdex::core::addNormalTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectiveMtlxSurfaceShader(material);
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->openPbrSurfaceId) || !isShaderType(previewSurface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePbrMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // Add the UPS normal texture first
    if (!usdex::core::addNormalTextureToPreviewMaterial(material, texturePath))
    {
        return false;
    }
    GfVec3f defaultNormal(0.5f, 0.5f, 1.0f);
    VtValue fallbackNormalValue;
    UsdShadeInput normalInput = ::consumeInput(surface, _tokens->geometry_normal, SdfValueTypeNames->Float3, fallbackNormalValue);

    // We're going to force the setting of the default value here to ensure that the texture shader has a valid default value
    if (fallbackNormalValue.IsEmpty())
    {
        fallbackNormalValue = VtValue(defaultNormal);
    }

    UsdShadeShader texShader = ::addPbrTiledImageShader(
        material, // material
        _tokens->mtlxNormalTexName, // shaderPrimName
        _tokens->tiledImageVector3Id, // shaderId
        fallbackNormalValue, // defaultValue
        SdfValueTypeNames->Float3 // outputType
    );
    if (!texShader)
    {
        return false;
    }

    SdfPath shaderPath = material.GetPath().AppendChild(_tokens->mtlxNormalMapName);
    UsdShadeShader normalMapShader = UsdShadeShader::Define(material.GetPrim().GetStage(), shaderPath);
    normalMapShader.SetShaderId(_tokens->normalMapNodeId);
    normalMapShader.CreateInput(_tokens->mtlxIn, SdfValueTypeNames->Float3).ConnectToSource(texShader.GetOutput(_tokens->mtlxOut));
    normalMapShader.CreateInput(_tokens->scale, SdfValueTypeNames->Float).Set(1.0f);

    normalInput.ConnectToSource(normalMapShader.CreateOutput(_tokens->mtlxOut, SdfValueTypeNames->Float3));

    UsdShadeInput matTextureInput = ::finalizePbrTextureInterface(
        material, // material
        texShader, // texShader
        texturePath, // texturePath
        _tokens->uvTexNormalsName, // materialInterfaceName
        ColorSpace::eRaw, // colorSpace
        {} // materialInputsToRemove
    );

    // Connect the UPS normal texture shader's file input to the material interface input
    ::connectPreviewSurfaceFileInput(matTextureInput, _tokens->normal);

    return true;
}

bool usdex::core::addOrmTextureToPbrMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    UsdShadeShader surface = usdex::core::computeEffectiveMtlxSurfaceShader(material);
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->openPbrSurfaceId) || !isShaderType(previewSurface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePbrMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    // Add the UPS ORM texture first
    if (!usdex::core::addOrmTextureToPreviewMaterial(material, texturePath))
    {
        return false;
    }

    VtValue roughnessValue(0.3f);
    VtValue metallicValue(0.0f);
    UsdShadeInput roughnessInput = ::consumeInput(surface, _tokens->specular_roughness, SdfValueTypeNames->Float, roughnessValue);
    UsdShadeInput metallicInput = ::consumeInput(surface, _tokens->base_metalness, SdfValueTypeNames->Float, metallicValue);
    VtValue fallbackOrmValue = VtValue();
    if (!roughnessValue.IsEmpty() && !metallicValue.IsEmpty())
    {
        fallbackOrmValue = VtValue(GfVec3f(0.0f, roughnessValue.Get<float>(), metallicValue.Get<float>()));
    }

    UsdShadeShader texShader = ::addPbrTiledImageShader(
        material, // material
        _tokens->mtlxORMTexName, // shaderPrimName
        _tokens->tiledImageVector3Id, // shaderId
        fallbackOrmValue, // defaultValue
        SdfValueTypeNames->Float3 // outputType
    );
    if (!texShader)
    {
        return false;
    }

    SdfPath shaderPath = material.GetPath().AppendChild(_tokens->mtlxSeparateOrmName);
    UsdShadeShader vectorSepShader = UsdShadeShader::Define(material.GetPrim().GetStage(), shaderPath);
    vectorSepShader.SetShaderId(_tokens->separate3Vector3Id);
    vectorSepShader.CreateInput(_tokens->mtlxIn, SdfValueTypeNames->Float3).ConnectToSource(texShader.GetOutput(_tokens->mtlxOut));

    // The occlusion channel is not used by the OpenPBR definition, but conceptually outx = outputs[0], outy = outputs[1], outz = outputs[2]
    vectorSepShader.CreateOutput(_tokens->outx, SdfValueTypeNames->Float);
    UsdShadeOutput outy = vectorSepShader.CreateOutput(_tokens->outy, SdfValueTypeNames->Float);
    UsdShadeOutput outz = vectorSepShader.CreateOutput(_tokens->outz, SdfValueTypeNames->Float);

    roughnessInput.ConnectToSource(outy);
    metallicInput.ConnectToSource(outz);

    UsdShadeInput matTextureInput = ::finalizePbrTextureInterface(
        material, // material
        texShader, // texShader
        texturePath, // texturePath
        _tokens->uvTexORMName, // materialInterfaceName
        ColorSpace::eRaw, // colorSpace
        { _tokens->roughness, _tokens->metallic } // materialInputsToRemove
    );

    // Connect the UPS ORM texture shader's file input to the material interface input
    ::connectPreviewSurfaceFileInput(matTextureInput, _tokens->occlusion);

    return true;
}

bool usdex::core::addRoughnessTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
{
    return ::addFloatTextureToPbrMaterial(
        material, // material
        texturePath, // texturePath
        _tokens->specular_roughness, // surfaceInputName
        0.3f, // defaultValue
        _tokens->mtlxRoughnessTexName, // textureShaderPrimName
        _tokens->uvTexRoughnessName, // materialInterfaceName
        _tokens->roughness, // materialInputNameToRemove
        usdex::core::addRoughnessTextureToPreviewMaterial, // addUpsTextureFunc
        _tokens->roughness // upsShaderInputName
    );
}

bool usdex::core::addMetallicTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
{
    return ::addFloatTextureToPbrMaterial(
        material, // material
        texturePath, // texturePath
        _tokens->base_metalness, // surfaceInputName
        0.0f, // defaultValue
        _tokens->mtlxMetallicTexName, // textureShaderPrimName
        _tokens->uvTexMetallicName, // materialInterfaceName
        _tokens->metallic, // materialInputNameToRemove
        usdex::core::addMetallicTextureToPreviewMaterial, // addUpsTextureFunc
        _tokens->metallic // upsShaderInputName
    );
}

bool usdex::core::addOpacityTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath)
{
    return ::addFloatTextureToPbrMaterial(
        material, // material
        texturePath, // texturePath
        _tokens->geometry_opacity, // surfaceInputName
        1.0f, // defaultValue
        _tokens->mtlxOpacityTexName, // textureShaderPrimName
        _tokens->uvTexOpacityName, // materialInterfaceName
        _tokens->opacity, // materialInputNameToRemove
        usdex::core::addOpacityTextureToPreviewMaterial, // addUpsTextureFunc
        _tokens->opacity // upsShaderInputName
    );
}

bool usdex::core::addEmissiveTextureToPbrMaterial(pxr::UsdShadeMaterial& material, const pxr::SdfAssetPath& texturePath, const float luminance)
{
    UsdShadeShader surface = usdex::core::computeEffectiveMtlxSurfaceShader(material);
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!isShaderType(surface, _tokens->openPbrSurfaceId) || !isShaderType(previewSurface, _tokens->upsId))
    {
        TF_WARN("Material <%s> must first be defined using definePbrMaterial()", material.GetPath().GetAsString().c_str());
        return false;
    }

    if (luminance < 0.0)
    {
        const std::string reason = TfStringPrintf("Luminance value %f is invalid: must be at least 0.0 (no upper bound).", luminance);
        TF_RUNTIME_ERROR(
            "Unable to add emissive texture to PBR material at \"%s\" due to an invalid shader parameter value: %s",
            material.GetPath().GetAsString().c_str(),
            reason.c_str()
        );
        return false;
    }

    // Add the UPS emissive texture first
    if (!usdex::core::addEmissiveTextureToPreviewMaterial(material, texturePath))
    {
        return false;
    }

    // Read and remove the current emission_color from the OpenPBR shader to use as the Mtlx texture fallback
    VtValue colorValue = VtValue();
    UsdShadeInput emissionColorInput = ::consumeInput(surface, _tokens->emission_color, SdfValueTypeNames->Color3f, colorValue);

    UsdShadeShader texShader = ::addPbrTiledImageShader(
        material, // material
        _tokens->mtlxEmissiveTexName, // shaderPrimName
        _tokens->tiledImageColor3Id, // shaderId
        colorValue, // defaultValue
        SdfValueTypeNames->Color3f // outputType
    );
    if (!texShader)
    {
        return false;
    }
    emissionColorInput.ConnectToSource(texShader.GetOutput(_tokens->mtlxOut));

    // Create a shared material interface input for the texture file, removing the scalar emissive color input.
    // Both the Mtlx and UPS texture shaders connect their file inputs to this.
    UsdShadeInput matTextureInput = ::finalizePbrTextureInterface(
        material, // material
        texShader, // texShader
        texturePath, // texturePath
        _tokens->uvTexEmissiveName, // materialInterfaceName
        ColorSpace::eAuto, // colorSpace
        { _tokens->materialEmissiveColor } // materialInputsToRemove
    );

    // Connect the UPS texture shader's file input to the material interface input
    ::connectPreviewSurfaceFileInput(matTextureInput, _tokens->emissiveColor);

    // Create or reuse the material interface input that drives OpenPBR's emission_luminance, then set the supplied luminance.
    // This overwrites any value previously authored by addEmissiveColorToPbrMaterial().
    UsdShadeInput materialEmissiveLuminanceInput = material.CreateInput(_tokens->materialEmissiveLuminance, SdfValueTypeNames->Float);
    setLimitMetadata(
        materialEmissiveLuminanceInput, /* input */
        VtValue(0.0f), /* min */
        VtValue(), /* max */
        VtValue(), /* softMin */
        VtValue(1000.0f) /* softMax */
    );
    materialEmissiveLuminanceInput.Set(luminance);
    surface.CreateInput(_tokens->emission_luminance, SdfValueTypeNames->Float).ConnectToSource(materialEmissiveLuminanceInput);

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
            TF_CODING_ERROR("Invalid ColorSpace value: %d", static_cast<int>(value));
            return _tokens->invalid;
        }
    }
}

GfVec3f usdex::core::sRgbToLinear(const GfVec3f& color)
{
    const GfColorSpace srgbColorSpace(GfColorSpaceNames->SRGBRec709);
    return GfColorSpace(GfColorSpaceNames->LinearRec709).Convert(srgbColorSpace, color).GetRGB();
}

GfVec3f usdex::core::linearToSrgb(const GfVec3f& color)
{
    const GfColorSpace srgbColorSpace(GfColorSpaceNames->SRGBRec709);
    return srgbColorSpace.Convert(GfColorSpace(GfColorSpaceNames->LinearRec709), color).GetRGB();
}
