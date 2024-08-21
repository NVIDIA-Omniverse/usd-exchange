// SPDX-FileCopyrightText: Copyright (c) 2022-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "usdex/rtx/MaterialAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdShade/materialBindingAPI.h>
#include <pxr/usd/usdShade/tokens.h>
#include <pxr/usd/usdUtils/pipeline.h>

using namespace pxr;

namespace
{
static constexpr const char* g_omniPbrAssetPath("OmniPBR.mdl");

// Warnings generated by USD 23.11
#if defined(ARCH_OS_WINDOWS) && PXR_VERSION < 2405
#pragma warning(push)
#pragma warning(disable : 4003) // not enough arguments for function-like macro invocation
#endif
// clang-format off
TF_DEFINE_PRIVATE_TOKENS(
    _tokens,
    ((defaultValue, "default"))
    ((rangeMin, "range:min"))
    ((rangeMax, "range:max"))
    ((softRangeMin, "soft_range:min"))
    ((softRangeMax, "soft_range:max"))
    ((mdl, "mdl"))
    ((out, "out"))
    ((colorSpaceAuto, "auto"))
    ((colorSpaceRaw, "raw"))
    ((colorSpacesRBG, "sRGB"))
    ((omniPbr, "OmniPBR"))
    ((omniPbrAlbedoColor, "diffuse_color_constant"))
    ((omniPbrRoughness, "reflection_roughness_constant"))
    ((omniPbrRoughnessTexture, "reflectionroughness_texture"))
    ((omniPbrRoughnessTextureInfluence, "reflection_roughness_texture_influence"))
    ((omniPbrMetallic, "metallic_constant"))
    ((omniPbrMetallicTexture, "metallic_texture"))
    ((omniPbrMetallicTextureInfluence, "metallic_texture_influence"))
    ((omniPbrOrmTextureEnabled, "enable_ORM_texture"))
    ((omniPbrOpacity, "opacity_constant"))
    ((omniPbrOpacityEnabled, "enable_opacity"))
    ((omniPbrOpacityTexture, "opacity_texture"))
    ((omniPbrOpacityTextureEnabled, "enable_opacity_texture"))
    ((omniPbrOpacityThreshold, "opacity_threshold"))
    ((omniPbrDiffuseTexture, "diffuse_texture"))
    ((omniPbrNormalTexture, "normalmap_texture"))
    ((omniPbrOrmTexture, "ORM_texture"))
    ((omniGlass, "OmniGlass"))
    ((omniGlassColor, "glass_color"))
    ((omniGlassIor, "glass_ior"))
    ((usdPreviewSurface, "UsdPreviewSurface"))
    ((usdPreviewSurfaceColor, "diffuseColor"))
    ((usdPreviewSurfaceFile, "file"))
    ((usdPreviewSurfaceIor, "ior"))
    ((usdPreviewSurfaceMetallic, "metallic"))
    ((usdPreviewSurfaceNormal, "normal"))
    ((usdPreviewSurfaceOcclusion, "occlusion"))
    ((usdPreviewSurfaceOpacity, "opacity"))
    ((usdPreviewSurfaceRoughness, "roughness"))
    ((materialColor, "Color"))
    ((materialColorInputs, "inputs:Color"))
    ((materialOpacity, "Opacity"))
    ((materialOpacityInputs, "inputs:Opacity"))
    ((materialRoughness, "Roughness"))
    ((materialRoughnessInputs, "inputs:Roughness"))
    ((materialMetallic, "Metallic"))
    ((materialMetallicInputs, "inputs:Metallic"))
    ((materialIor, "IOR"))
    ((materialDiffuseTexture, "DiffuseTexture"))
    ((materialNormalTexture, "NormalTexture"))
    ((materialOpacityTexture, "OpacityTexture"))
    ((materialOrmTexture, "ORMTexture"))
    ((materialRoughnessTexture, "RoughnessTexture"))
    ((materialMetallicTexture, "MetallicTexture"))
);
// clang-format on
// Warnings generated by USD 23.11
#if defined(ARCH_OS_WINDOWS) && PXR_VERSION < 2405
#pragma warning(pop)
#endif

void setFractionalOpacity(UsdStagePtr stage, bool isOn = true)
{
    VtDictionary cld = stage->GetRootLayer()->GetCustomLayerData();
    VtDictionary renderSettings;
    if (auto entry = cld.find("renderSettings"); entry != cld.end())
    {
        renderSettings = *&(entry->second.Get<VtDictionary>());
    }
    renderSettings["rtx:raytracing:fractionalCutoutOpacity"] = isOn;
    cld.SetValueAtPath("renderSettings", VtValue(renderSettings));
    stage->GetRootLayer()->SetCustomLayerData(cld);
}

// Remove a property from a prim within the current edit target
// This is used for removing input properties from shaders and materials
bool removeProperty(UsdStageRefPtr stage, const SdfPath& primPath, const TfToken& propName)
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
                return true;
            }
        }

        TF_WARN(
            "Cannot remove property <%s> from prim <%s>, it doesn't exist in the current edit target layer <%s>",
            propName.GetText(),
            primPath.GetAsString().c_str(),
            layer->GetIdentifier().c_str()
        );
        return false;
    }
    else
    {
        TF_WARN(
            "Failed to get the current edit target layer from stage <%s> while removing property <%s>",
            stage->GetRootLayer()->GetRealPath().c_str(),
            propName.GetText()
        );
        return false;
    }
}

// This function will create an MDL prim asset input (materialInputName) and connect it to
// the MDL shader prim asset input (shaderInputName)
//
// precondition: materialPrim and its MDL shader MUST BE VALID
//
// All texture parameters require a sampling mode, or "colorSpace"
UsdShadeInput createMaterialLinkedMdlFileInput(
    UsdShadeMaterial& materialPrim,
    const TfToken& materialInputName,
    const TfToken& shaderInputName,
    const SdfAssetPath& filePath,
    const TfToken& colorSpace
)
{
    UsdShadeShader shaderPrim = usdex::rtx::computeEffectiveMdlSurfaceShader(materialPrim);
    UsdShadeInput matTextureInput = materialPrim.CreateInput(materialInputName, SdfValueTypeNames->Asset);
    matTextureInput.Set(filePath);
    // MDL render context requires that the color space (sampling mode) be an attribute on the file attribute
    UsdAttribute attr = matTextureInput.GetAttr();
    attr.SetColorSpace(colorSpace);
    UsdShadeInput surfaceInput = shaderPrim.CreateInput(shaderInputName, SdfValueTypeNames->Asset);
    surfaceInput.ConnectToSource(matTextureInput);
    return matTextureInput;
}

// Common function to check that a material has an OmniPBR-based MDL & USD Preview Surface shaders
bool verifyValidOmniPbrMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    if (!material)
    {
        TF_WARN(
            "Cannot add texture <%s>, UsdShadeMaterial <%s> is not a valid material",
            texturePath.GetAssetPath().c_str(),
            material.GetPath().GetAsString().c_str()
        );
        return false;
    }
    UsdShadeShader psShader = usdex::core::computeEffectivePreviewSurfaceShader(material);
    if (!psShader)
    {
        TF_WARN(
            "Cannot add texture <%s>, UsdShadeMaterial <%s> does not have a valid USD Preview Surface Shader",
            texturePath.GetAssetPath().c_str(),
            material.GetPath().GetAsString().c_str()
        );
        return false;
    }
    UsdShadeShader mdlShader = usdex::rtx::computeEffectiveMdlSurfaceShader(material);
    if (!mdlShader || (mdlShader.GetPrim() == psShader.GetPrim()))
    {
        TF_WARN(
            "Cannot add texture <%s>, UsdShadeMaterial <%s> does not have a valid MDL Shader",
            texturePath.GetAssetPath().c_str(),
            material.GetPath().GetAsString().c_str()
        );
        return false;
    }
    SdfAssetPath sourceAsset;
    bool sourceAssetSet = mdlShader.GetSourceAsset(&sourceAsset, _tokens->mdl);
    if (!sourceAssetSet || (sourceAsset.GetAssetPath() != std::string(g_omniPbrAssetPath)))
    {
        TF_WARN(
            "Cannot add texture <%s>, the UsdShadeShader <%s> does not have the correct source asset <%s>. It is using <%s>",
            texturePath.GetAssetPath().c_str(),
            mdlShader.GetPath().GetAsString().c_str(),
            g_omniPbrAssetPath,
            sourceAssetSet ? sourceAsset.GetAssetPath().c_str() : ""
        );
        return false;
    }
    return true;
}

//! A utility struct to pass shader input names and values to a function
struct TfTokenValuePair
{
    TfToken inputName;
    VtValue value;
    // Prefer to get this from the VtValue itself but not sure where to get that
    SdfValueTypeName valueTypeName;
};

//! Add a single channel texture to an OmniPBR material (roughness, metallic, opacity)
//!
//! The color space (sampling mode) will be set to raw.
//!
//! ---------------------------------------------------------------------------------------------------------------
//! | Material prim
//! |-- input <matValueToken> (float, connected to MDL and USD PS shader inputs) - removed
//! |-- input <matTextureInputToken> (asset connected to MDL and USD PS shader texture inputs, set to texturePath)
//!   | MDL Shader prim ("MDLShader")
//!   |-- input <omniPBShaderValueToken> (float, set to old matValueToken value as fallback)
//!   |-- input <omniPbrTextureToken> (asset, connected to mat input)
//!   |-- input[s] <omniPbrInputValues> (MDL "enable", "influence" inputs are inconsistent so allow a list)
//!   | USD Preview Surface Shader prim ("UsdPreviewSurface")
//!   |-- input <usdShaderInputToken> (float, connected to texture shader output)
//!   | USD Preview Surface Shader prim (<usdTextureShaderToken>)
//!   |-- input fallback (float, set to old matValueToken value as fallback)
//!   |-- input file (asset, connected to mat input)
//! ---------------------------------------------------------------------------------------------------------------//!
//! @param material The UsdShadeMaterial prim to add the texture
//! @param texturePath The SdfAssetPath to the texture file
//! @param matValueToken The Material input name to remove, will be read to grab the fallback value
//! @param matValueInputsToken The Material input name to remove (with "inputs:" prepended)
//! @param matTextureInputToken The Material input name for the added texture input
//! @param omniPbrFallbackValueToken The MDL shader input that was formally connected to the matValueToken input
//! @param omniPbrInputValues A list of inputs that will be set on the MDL shader (enable, influence, etc.)
//! @param omniPbrTextureToken The MDL Shader input name for the texture
//! @param usdShaderInputToken The USD Preview Surface input to connect to the texture shader
//!
//! @returns Whether or not the texture was added to the material
bool addSingleChannelTextureToPbrMaterial(
    UsdShadeMaterial& material,
    const SdfAssetPath& texturePath,
    const TfToken& matValueToken,
    const TfToken& matValueInputsToken,
    const TfToken& matTextureInputToken,
    const TfToken& omniPbrFallbackValueToken,
    std::vector<TfTokenValuePair> omniPbrInputValues,
    const TfToken& omniPbrTextureToken,
    const TfToken& usdShaderInputToken
)
{
    // Because we have a texture, remove the material input that USDEX created
    // Copy the value first and set it to the MDL shader inputs
    float channelValue = 1.0f;
    UsdShadeInput input = material.GetInput(matValueToken);
    if (input)
    {
        input.Get<float>(&channelValue);
        usdex::rtx::createMdlShaderInput(material, omniPbrFallbackValueToken, VtValue(channelValue), SdfValueTypeNames->Float);
        ::removeProperty(material.GetPrim().GetStage(), material.GetPrim().GetPath(), matValueInputsToken);
    }

    // These need to be set for MDL to use this type texture file
    for (const TfTokenValuePair& pair : omniPbrInputValues)
    {
        usdex::rtx::createMdlShaderInput(material, pair.inputName, pair.value, pair.valueTypeName);
    }

    UsdShadeInput matTextureInput = ::createMaterialLinkedMdlFileInput(
        material,
        matTextureInputToken,
        omniPbrTextureToken,
        texturePath,
        _tokens->colorSpaceRaw
    );

    // Connect the texture shader to the material interface. Note this makes unchecked assumptions about the behavior of `definePreviewMaterial`
    // and `add*TextureToPreviewMaterial` in the core library. If those implementations change, this code needs to be adjusted to match.
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    UsdShadeConnectionSourceInfo info = previewSurface.GetInput(usdShaderInputToken).GetConnectedSources()[0];
    info.source.GetInput(_tokens->usdPreviewSurfaceFile).ConnectToSource(matTextureInput);

    return true;
}

} // namespace

UsdShadeShader usdex::rtx::createMdlShader(
    UsdShadeMaterial& material,
    const std::string& name,
    const SdfAssetPath& mdlPath,
    const TfToken& module,
    bool connectMaterialOutputs
)
{
    UsdPrim materialPrim = material.GetPrim();

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(materialPrim, name, &reason))
    {
        TF_WARN("Unable to create UsdShadeShader due to an invalid location: %s", reason.c_str());
        return UsdShadeShader();
    }

    SdfPath shaderPath = materialPrim.GetPath().AppendChild(TfToken(name));
    UsdStagePtr stage = materialPrim.GetStage();

    UsdShadeShader shader = UsdShadeShader::Define(stage, shaderPath);
    shader.SetSourceAsset(mdlPath, _tokens->mdl);
    shader.SetSourceAssetSubIdentifier(module, _tokens->mdl);
    if (connectMaterialOutputs)
    {
        UsdShadeOutput shaderOutput = shader.CreateOutput(_tokens->out, SdfValueTypeNames->Token);
        material.CreateSurfaceOutput(_tokens->mdl).ConnectToSource(shaderOutput);
        material.CreateVolumeOutput(_tokens->mdl).ConnectToSource(shaderOutput);
        material.CreateDisplacementOutput(_tokens->mdl).ConnectToSource(shaderOutput);
    }
    return shader;
}

UsdShadeInput usdex::rtx::createMdlShaderInput(
    UsdShadeMaterial& material,
    const TfToken& name,
    const VtValue& value,
    const SdfValueTypeName& typeName,
    std::optional<const usdex::core::ColorSpace> colorSpace
)
{
    if (!material)
    {
        TF_WARN("Invalid UsdShadeMaterial, cannot create MDL shader input <%s>", name.GetText());
        return UsdShadeInput();
    }

    UsdShadeShader shaderPrim = usdex::rtx::computeEffectiveMdlSurfaceShader(material);
    if (!shaderPrim)
    {
        TF_WARN("Cannot create MDL shader input, no MDL shader found in UsdShadeMaterial <%s>", material.GetPath().GetAsString().c_str());
        return UsdShadeInput();
    }

    UsdShadeInput existingInput = shaderPrim.GetInput(name);
    if (existingInput && existingInput.GetTypeName() != typeName)
    {
        if (!::removeProperty(shaderPrim.GetPrim().GetStage(), shaderPrim.GetPrim().GetPath(), existingInput.GetFullName()))
        {
            TF_RUNTIME_ERROR(
                "Unable to create UsdShadeInput <%s> in material <%s> because input already exists as type <%s> in another layer",
                name.GetText(),
                material.GetPath().GetAsString().c_str(),
                existingInput.GetTypeName().GetAsToken().GetText()
            );
            return UsdShadeInput();
        }
    }
    else if (existingInput && existingInput.HasConnectedSource())
    {
        if (!existingInput.DisconnectSource())
        {
            TF_WARN(
                "Failure disconnecting the existing source in UsdShadeInput <%s> in material <%s>",
                name.GetText(),
                material.GetPath().GetAsString().c_str()
            );
        }
    }

    UsdShadeInput surfaceInput = shaderPrim.CreateInput(name, typeName);
    if (!surfaceInput)
    {
        TF_RUNTIME_ERROR("Unable to create UsdShadeInput <%s> in material <%s>", name.GetText(), material.GetPath().GetAsString().c_str());
        return UsdShadeInput();
    }

    surfaceInput.Set(value);
    const UsdAttribute& attr = surfaceInput.GetAttr();
    if (colorSpace.has_value())
    {
        attr.SetColorSpace(usdex::core::getColorSpaceToken(colorSpace.value()));
    }
    return surfaceInput;
}

UsdShadeShader usdex::rtx::computeEffectiveMdlSurfaceShader(const UsdShadeMaterial& material)
{
    if (!material)
    {
        return UsdShadeShader();
    }

    return material.ComputeSurfaceSource({ _tokens->mdl });
}

UsdShadeMaterial usdex::rtx::defineOmniPbrMaterial(
    UsdStagePtr stage,
    const SdfPath& path,
    const GfVec3f& color,
    const float opacity,
    const float roughness,
    const float metallic
)
{
    // Define the Preview Material first, as it validates the same set of criteria
    UsdShadeMaterial material = usdex::core::definePreviewMaterial(stage, path, color, opacity, roughness, metallic);
    if (!material)
    {
        // Do not report the reason as the function we called will have already logged the diagnostic for us.
        return UsdShadeMaterial();
    }

    // Define the surface shader to be used in the "mdl" rendering context
    static constexpr const char* s_mdlShaderName = "MDLShader";
    static const SdfAssetPath s_mdlAssetPath = SdfAssetPath(g_omniPbrAssetPath);
    UsdShadeShader mdlShader = usdex::rtx::createMdlShader(material, s_mdlShaderName, s_mdlAssetPath, _tokens->omniPbr);
    if (!mdlShader)
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeShader named \"%s\" as a child of \"%s\"", s_mdlShaderName, path.GetAsString().c_str());
        // TODO: OM-109366 - Cleanup any authored prims before returning a failure
        return UsdShadeMaterial();
    }

    // Expose inputs on the material that will be connected to the corresponding inputs on the surface shaders
    // This acts as a Material interface from which value changes will be reflected across multiple renderers
    UsdShadeInput materialColorInput = material.CreateInput(_tokens->materialColor, SdfValueTypeNames->Color3f);
    UsdShadeInput materialOpacityInput = material.CreateInput(_tokens->materialOpacity, SdfValueTypeNames->Float);
    UsdShadeInput materialRoughnessInput = material.CreateInput(_tokens->materialRoughness, SdfValueTypeNames->Float);
    UsdShadeInput materialMetallicInput = material.CreateInput(_tokens->materialMetallic, SdfValueTypeNames->Float);

    // Set the min, max and default metadata on the material interface
    // We would copy this metadata from the connected MDL shader inputs, however the Sdr registry for MDL shaders may not be available.
    // Instead we author the same values that are enforced within this function.
    materialColorInput.GetAttr().SetCustomDataByKey(_tokens->defaultValue, VtValue(GfVec3f(0.2f, 0.2f, 0.2f)));

    materialOpacityInput.GetAttr().SetCustomDataByKey(_tokens->defaultValue, VtValue(1.0f));
    materialOpacityInput.GetAttr().SetCustomDataByKey(_tokens->rangeMin, VtValue(0.0f));
    materialOpacityInput.GetAttr().SetCustomDataByKey(_tokens->rangeMax, VtValue(1.0f));

    materialRoughnessInput.GetAttr().SetCustomDataByKey(_tokens->defaultValue, VtValue(0.5f));
    materialRoughnessInput.GetAttr().SetCustomDataByKey(_tokens->rangeMin, VtValue(0.0f));
    materialRoughnessInput.GetAttr().SetCustomDataByKey(_tokens->rangeMax, VtValue(1.0f));

    materialMetallicInput.GetAttr().SetCustomDataByKey(_tokens->defaultValue, VtValue(0.0f));
    materialMetallicInput.GetAttr().SetCustomDataByKey(_tokens->rangeMin, VtValue(0.0f));
    materialMetallicInput.GetAttr().SetCustomDataByKey(_tokens->rangeMax, VtValue(1.0f));

    // Set the supplied values on the material interface
    materialColorInput.Set(color);
    materialOpacityInput.Set(opacity);
    materialRoughnessInput.Set(roughness);
    materialMetallicInput.Set(metallic);

    // Create MDL shader inputs to produce a physically based rendering result with the supplied values
    // Inputs are either set or connected to the material interface
    mdlShader.CreateInput(_tokens->omniPbrAlbedoColor, SdfValueTypeNames->Color3f).ConnectToSource(materialColorInput);
    mdlShader.CreateInput(_tokens->omniPbrOpacity, SdfValueTypeNames->Float).ConnectToSource(materialOpacityInput);
    mdlShader.CreateInput(_tokens->omniPbrRoughness, SdfValueTypeNames->Float).ConnectToSource(materialRoughnessInput);
    mdlShader.CreateInput(_tokens->omniPbrMetallic, SdfValueTypeNames->Float).ConnectToSource(materialMetallicInput);

    // Enable opacity and set the required render settings if the material is not fully opaque
    if (opacity < 1.0f)
    {
        mdlShader.CreateInput(_tokens->omniPbrOpacityEnabled, SdfValueTypeNames->Bool).Set(true);
        setFractionalOpacity(stage);
    }

    // Create default shader inputs to produce a physically based rendering result with the supplied values. Note these will have already been
    // created when we called `definePreviewMaterial`. Since `CreateInput` will Get if it already exists, it is safe to call here, and protects
    // us incase the underlying implementation stops creating these directly.
    UsdShadeShader previewShader = usdex::core::computeEffectivePreviewSurfaceShader(material);
    previewShader.CreateInput(_tokens->usdPreviewSurfaceColor, SdfValueTypeNames->Color3f).ConnectToSource(materialColorInput);
    previewShader.CreateInput(_tokens->usdPreviewSurfaceOpacity, SdfValueTypeNames->Float).ConnectToSource(materialOpacityInput);
    previewShader.CreateInput(_tokens->usdPreviewSurfaceRoughness, SdfValueTypeNames->Float).ConnectToSource(materialRoughnessInput);
    previewShader.CreateInput(_tokens->usdPreviewSurfaceMetallic, SdfValueTypeNames->Float).ConnectToSource(materialMetallicInput);

    return material;
}

UsdShadeMaterial usdex::rtx::defineOmniPbrMaterial(
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
    return usdex::rtx::defineOmniPbrMaterial(stage, path, color, opacity, roughness, metallic);
}

bool usdex::rtx::addDiffuseTextureToPbrMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    if (!verifyValidOmniPbrMaterial(material, texturePath))
    {
        return false;
    }

    if (!usdex::core::addDiffuseTextureToPreviewMaterial(material, texturePath))
    {
        // Do not report the reason as the function we called will have already logged the diagnostic for us.
        return false;
    }

    // Because we have a texture, remove this "Color" material input that USDEX created
    // Copy the value and set it to the MDL color input
    GfVec3f color(1.0f);
    UsdShadeInput matColorInput = material.GetInput(_tokens->materialColor);
    if (matColorInput)
    {
        matColorInput.Get<GfVec3f>(&color);
        createMdlShaderInput(material, _tokens->omniPbrAlbedoColor, VtValue(color), SdfValueTypeNames->Color3f);
        ::removeProperty(material.GetPrim().GetStage(), material.GetPrim().GetPath(), _tokens->materialColorInputs);
    }
    UsdShadeInput matTextureInput = ::createMaterialLinkedMdlFileInput(
        material,
        _tokens->materialDiffuseTexture,
        _tokens->omniPbrDiffuseTexture,
        texturePath,
        _tokens->colorSpaceAuto
    );

    // Connect the texture shader to the material interface. Note this makes unchecked assumptions about the behavior of `definePreviewMaterial`
    // and `addDiffuseTextureToPreviewMaterial` in the core library. If those implementations change, this code needs to be adjusted to match.
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    UsdShadeConnectionSourceInfo info = previewSurface.GetInput(_tokens->usdPreviewSurfaceColor).GetConnectedSources()[0];
    info.source.GetInput(_tokens->usdPreviewSurfaceFile).ConnectToSource(matTextureInput);

    return true;
}

bool usdex::rtx::addNormalTextureToPbrMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    if (!verifyValidOmniPbrMaterial(material, texturePath))
    {
        return false;
    }

    if (!usdex::core::addNormalTextureToPreviewMaterial(material, texturePath))
    {
        // Do not report the reason as the function we called will have already logged the diagnostic for us.
        return false;
    }

    UsdShadeInput matTextureInput = ::createMaterialLinkedMdlFileInput(
        material,
        _tokens->materialNormalTexture,
        _tokens->omniPbrNormalTexture,
        texturePath,
        _tokens->colorSpaceRaw
    );

    // Connect the texture shader to the material interface. Note this makes unchecked assumptions about the behavior of `definePreviewMaterial`
    // and `addNormalTextureToPreviewMaterial` in the core library. If those implementations change, this code needs to be adjusted to match.
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    UsdShadeConnectionSourceInfo info = previewSurface.GetInput(_tokens->usdPreviewSurfaceNormal).GetConnectedSources()[0];
    info.source.GetInput(_tokens->usdPreviewSurfaceFile).ConnectToSource(matTextureInput);

    return true;
}

bool usdex::rtx::addOpacityTextureToPbrMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    if (!verifyValidOmniPbrMaterial(material, texturePath))
    {
        return false;
    }

    if (!usdex::core::addOpacityTextureToPreviewMaterial(material, texturePath))
    {
        // Do not report the reason as the function we called will have already logged the diagnostic for us.
        return false;
    }

    std::vector<TfTokenValuePair> tokenValuePairs = {
        { _tokens->omniPbrOpacityEnabled, VtValue(true), SdfValueTypeNames->Bool },
        { _tokens->omniPbrOpacityTextureEnabled, VtValue(true), SdfValueTypeNames->Bool },
        { _tokens->omniPbrOpacityThreshold, VtValue(std::numeric_limits<float>::epsilon()), SdfValueTypeNames->Float }
    };

    return addSingleChannelTextureToPbrMaterial(
        material,
        texturePath,
        _tokens->materialOpacity,
        _tokens->materialOpacityInputs,
        _tokens->materialOpacityTexture,
        _tokens->omniPbrOpacity,
        tokenValuePairs,
        _tokens->omniPbrOpacityTexture,
        _tokens->usdPreviewSurfaceOpacity
    );
}

bool usdex::rtx::addRoughnessTextureToPbrMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    if (!verifyValidOmniPbrMaterial(material, texturePath))
    {
        return false;
    }

    if (!usdex::core::addRoughnessTextureToPreviewMaterial(material, texturePath))
    {
        // Do not report the reason as the function we called will have already logged the diagnostic for us.
        return false;
    }

    std::vector<TfTokenValuePair> tokenValuePairs = { { _tokens->omniPbrRoughnessTextureInfluence, VtValue(1.0f), SdfValueTypeNames->Float } };

    return addSingleChannelTextureToPbrMaterial(
        material,
        texturePath,
        _tokens->materialRoughness,
        _tokens->materialRoughnessInputs,
        _tokens->materialRoughnessTexture,
        _tokens->omniPbrRoughness,
        tokenValuePairs,
        _tokens->omniPbrRoughnessTexture,
        _tokens->usdPreviewSurfaceRoughness
    );
}

bool usdex::rtx::addMetallicTextureToPbrMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    if (!verifyValidOmniPbrMaterial(material, texturePath))
    {
        return false;
    }

    if (!usdex::core::addMetallicTextureToPreviewMaterial(material, texturePath))
    {
        // Do not report the reason as the function we called will have already logged the diagnostic for us.
        return false;
    }

    std::vector<TfTokenValuePair> tokenValuePairs = { { _tokens->omniPbrMetallicTextureInfluence, VtValue(1.0f), SdfValueTypeNames->Float } };

    return addSingleChannelTextureToPbrMaterial(
        material,
        texturePath,
        _tokens->materialMetallic,
        _tokens->materialMetallicInputs,
        _tokens->materialMetallicTexture,
        _tokens->omniPbrMetallic,
        tokenValuePairs,
        _tokens->omniPbrMetallicTexture,
        _tokens->usdPreviewSurfaceMetallic
    );
}

bool usdex::rtx::addOrmTextureToPbrMaterial(UsdShadeMaterial& material, const SdfAssetPath& texturePath)
{
    if (!verifyValidOmniPbrMaterial(material, texturePath))
    {
        return false;
    }

    if (!usdex::core::addOrmTextureToPreviewMaterial(material, texturePath))
    {
        // Do not report the reason as the function we called will have already logged the diagnostic for us.
        return false;
    }

    // Because we have a texture, remove the "Metallic" & "Roughness" material inputs that USDEX created
    // Copy the values first and set it to the MDL shader inputs
    float metallic = 0.0f;
    UsdShadeInput input = material.GetInput(_tokens->materialMetallic);
    if (input)
    {
        input.Get<float>(&metallic);
        createMdlShaderInput(material, _tokens->omniPbrMetallic, VtValue(metallic), SdfValueTypeNames->Float);
        ::removeProperty(material.GetPrim().GetStage(), material.GetPrim().GetPath(), _tokens->materialMetallicInputs);
    }

    float roughness = 0.5f;
    input = material.GetInput(_tokens->materialRoughness);
    if (input)
    {
        input.Get<float>(&roughness);
        createMdlShaderInput(material, _tokens->omniPbrRoughness, VtValue(roughness), SdfValueTypeNames->Float);
        ::removeProperty(material.GetPrim().GetStage(), material.GetPrim().GetPath(), _tokens->materialRoughnessInputs);
    }

    // These need to be set for MDL to use an ORM map
    createMdlShaderInput(material, _tokens->omniPbrRoughnessTextureInfluence, VtValue(1.0f), SdfValueTypeNames->Float);
    createMdlShaderInput(material, _tokens->omniPbrMetallicTextureInfluence, VtValue(1.0f), SdfValueTypeNames->Float);
    createMdlShaderInput(material, _tokens->omniPbrOrmTextureEnabled, VtValue(true), SdfValueTypeNames->Bool);
    UsdShadeInput matTextureInput = ::createMaterialLinkedMdlFileInput(
        material,
        _tokens->materialOrmTexture,
        _tokens->omniPbrOrmTexture,
        texturePath,
        _tokens->colorSpaceRaw
    );

    // Connect the texture shader to the material interface. Note this makes unchecked assumptions about the behavior of `definePreviewMaterial`
    // and `addOrmTextureToPreviewMaterial` in the core library. If those implementations change, this code needs to be adjusted to match.
    UsdShadeShader previewSurface = usdex::core::computeEffectivePreviewSurfaceShader(material);
    UsdShadeConnectionSourceInfo info = previewSurface.GetInput(_tokens->usdPreviewSurfaceOcclusion).GetConnectedSources()[0];
    info.source.GetInput(_tokens->usdPreviewSurfaceFile).ConnectToSource(matTextureInput);

    return true;
}

UsdShadeMaterial usdex::rtx::defineOmniGlassMaterial(UsdStagePtr stage, const SdfPath& path, const GfVec3f& color, const float indexOfRefraction)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial due to an invalid location: %s", reason.c_str());
        return UsdShadeMaterial();
    }

    // The color value must be within the defined min, max range
    if (color[0] < 0.0 || color[1] < 0.0 || color[2] < 0.0 || color[0] > 1.0 || color[1] > 1.0 || color[2] > 1.0)
    {
        reason = TfStringPrintf("Color value (%g, %g, %g)  is outside range [(0, 0, 0) - (1, 1, 1)].", color[0], color[1], color[2]);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // The index of refraction value must be within the defined soft min, soft max range
    if (indexOfRefraction < 1.0 || indexOfRefraction > 4.0)
    {
        reason = TfStringPrintf("IOR value %g is outside range [1.0 - 4.0].", indexOfRefraction);
        TF_RUNTIME_ERROR(
            "Unable to define UsdShadeMaterial at \"%s\" due to an invalid shader parameter value: %s",
            path.GetAsString().c_str(),
            reason.c_str()
        );
        return UsdShadeMaterial();
    }

    // Define the material
    // We do not use usdex::rtx::createMaterial here to avoid double validations
    UsdShadeMaterial material = UsdShadeMaterial::Define(stage, path);
    if (!material)
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial at \"%s\"", path.GetAsString().c_str());
        return UsdShadeMaterial();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = material.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    // Define the surface shader to be used in the "mdl" rendering context
    static const std::string mdlShaderName = "MDLShader";
    const SdfAssetPath mdlAssetPath = SdfAssetPath("OmniGlass.mdl");
    UsdShadeShader mdlShader = usdex::rtx::createMdlShader(material, mdlShaderName, mdlAssetPath, _tokens->omniGlass);
    if (!mdlShader)
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeShader named \"%s\" as a child of \"%s\"", mdlShaderName.c_str(), path.GetAsString().c_str());
        return UsdShadeMaterial();
    }

    // Define the surface shader to be used in the universal rendering context
    // The shader parameters will produce a low fidelity approximation of the "mdl" rendering context for use with non-RTX renderers
    static constexpr const char* s_previewShaderName = "PreviewSurface";
    if (!usdex::core::isEditablePrimLocation(prim, s_previewShaderName, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeShader named \"%s\" as a child of \"%s\"", s_previewShaderName, path.GetAsString().c_str());
        return UsdShadeMaterial();
    }
    UsdShadeShader previewShader = UsdShadeShader::Define(stage, prim.GetPath().AppendChild(TfToken(s_previewShaderName)));
    previewShader.SetShaderId(_tokens->usdPreviewSurface);
    material.CreateSurfaceOutput().ConnectToSource(previewShader.CreateOutput(UsdShadeTokens->surface, SdfValueTypeNames->Token));
    material.CreateDisplacementOutput().ConnectToSource(previewShader.CreateOutput(UsdShadeTokens->displacement, SdfValueTypeNames->Token));

    // Expose inputs on the material that will be connected to the corresponding inputs on the surface shaders
    // This acts as a Material interface from which value changes will be reflected across multiple renderers
    UsdShadeInput materialColorInput = material.CreateInput(_tokens->materialColor, SdfValueTypeNames->Color3f);
    UsdShadeInput materialIorInput = material.CreateInput(_tokens->materialIor, SdfValueTypeNames->Float);

    // Set the min, max and default metadata on the material interface
    // We would copy this metadata from the connected MDL shader inputs, however the Sdr registry for MDL shaders may not be available.
    // Instead we author the same values that are enforced within this function.
    materialColorInput.GetAttr().SetCustomDataByKey(_tokens->defaultValue, VtValue(GfVec3f(1.0, 1.0, 1.0)));
    materialColorInput.GetAttr().SetCustomDataByKey(_tokens->rangeMin, VtValue(GfVec3f(0.0, 0.0, 0.0)));
    materialColorInput.GetAttr().SetCustomDataByKey(_tokens->rangeMax, VtValue(GfVec3f(1.0, 1.0, 1.0)));

    materialIorInput.GetAttr().SetCustomDataByKey(_tokens->defaultValue, VtValue(1.491f));
    materialIorInput.GetAttr().SetCustomDataByKey(_tokens->softRangeMin, VtValue(1.0f));
    materialIorInput.GetAttr().SetCustomDataByKey(_tokens->softRangeMax, VtValue(4.0f));

    // Set the supplied values on the material interface
    materialColorInput.Set(color);
    materialIorInput.Set(indexOfRefraction);

    // Create MDL shader inputs to produce a glass result with the supplied values
    // Inputs are either set or connected to the material interface
    mdlShader.CreateInput(_tokens->omniGlassColor, SdfValueTypeNames->Color3f).ConnectToSource(materialColorInput);
    mdlShader.CreateInput(_tokens->omniGlassIor, SdfValueTypeNames->Float).ConnectToSource(materialIorInput);

    // Create default shader inputs to produce a glass result with the supplied values
    // Inputs are either set or connected to the material interface
    // Set "opacity" to 0.0 so that the "UsdPreviewSurface" mimics the behavior of OmniGlass.mdl
    previewShader.CreateInput(_tokens->usdPreviewSurfaceColor, SdfValueTypeNames->Color3f).ConnectToSource(materialColorInput);
    previewShader.CreateInput(_tokens->usdPreviewSurfaceIor, SdfValueTypeNames->Float).ConnectToSource(materialIorInput);
    previewShader.CreateInput(_tokens->usdPreviewSurfaceOpacity, SdfValueTypeNames->Float).Set(0.0f);

    return material;
}

UsdShadeMaterial usdex::rtx::defineOmniGlassMaterial(UsdPrim parent, const std::string& name, const GfVec3f& color, const float indexOfRefraction)
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
    return usdex::rtx::defineOmniGlassMaterial(stage, path, color, indexOfRefraction);
}
