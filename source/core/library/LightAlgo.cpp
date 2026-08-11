// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "usdex/core/LightAlgo.h"

#include "usdex/core/Core.h"
#include "usdex/core/StageAlgo.h"

#include <pxr/base/vt/array.h>
#include <pxr/usd/usdGeom/boundable.h>
#include <pxr/usd/usdGeom/tokens.h>

using namespace pxr;

namespace
{

constexpr const char* g_luxInputsStr = "inputs:";

inline bool initLightApiAttrs(UsdSchemaBase& light, float intensity = 1.0f, float exposure = 0.0f)
{
    auto lightApi = UsdLuxLightAPI(light);
    if (!lightApi)
    {
        TF_RUNTIME_ERROR("UsdLuxLightApi is not compatible with prim at path \"[%s]\"", light.GetPath().GetAsString().c_str());
        return false;
    }

    lightApi.CreateIntensityAttr().Set(intensity);
    lightApi.CreateExposureAttr().Set(exposure);

    return true;
}

bool isValidTextureFormat(const TfToken& textureFormat)
{
#if PXR_VERSION >= 2305
    const TfToken domeLightToken = UsdLuxTokens->DomeLight;
    const TfToken textureFormatToken = UsdLuxTokens->inputsTextureFormat;
#elif PXR_VERSION > 2108
    const TfToken domeLightToken = UsdLuxTokens->domeLight;
    const TfToken textureFormatToken = UsdLuxTokens->inputsTextureFormat;
#else
#error This version of OpenUSD is unsupported: PXR_VERSION
#endif

    // Get allowed tokens for type
    auto primDef = UsdSchemaRegistry::GetInstance().FindConcretePrimDefinition(domeLightToken);
    VtTokenArray allowedTokens = primDef->GetSchemaAttributeSpec(textureFormatToken)->GetAllowedTokens();

    // Check for provided texture format
    return std::find(allowedTokens.begin(), allowedTokens.end(), textureFormat) != allowedTokens.end();
}

void eraseSubstring(std::string& str, const std::string& substr)
{
    size_t pos = str.find(substr);
    if (pos != std::string::npos)
    {
        str.erase(pos, substr.length());
    }
}

// If version < 21.02, prepend "inputs:" to attribute name
// If version >= 21.02, remove "inputs:" from attribute name
TfToken compatName(const TfToken& originalAttrName)
{
    // Convert "inputs:intensity" to "intensity"
    std::string attrName(originalAttrName);
    if (TfStringStartsWith(attrName, g_luxInputsStr))
    {
        ::eraseSubstring(attrName, g_luxInputsStr);
    }

    //\ todo Possible future optimization for TfToken
    // TfToken construction locks synchronize with a global table so we always hesitate when I see their construction.
    // Something to perhaps keep an eye out when profiling, but it's probably not going to be the bottleneck.
    return TfToken(attrName);
}

} // namespace

bool usdex::core::isLight(const UsdPrim& prim)
{
    return prim.HasAPI<UsdLuxLightAPI>();
}

// Universal attribute retrieval for UsdLux attributes updated with the "inputs:" connectible schema change
UsdAttribute usdex::core::getLightAttr(const UsdAttribute& defaultAttr)
{
    // * Light has only "intensity" authored --- return "intensity"
    // * Light has only "inputs:intensity" authored --- return "inputs:intensity"
    // * Light has both "inputs:intensity" and "intensity" authored --- return "inputs:intensity"

    UsdPrim prim = defaultAttr.GetPrim();
    TfToken defaultAttrName = defaultAttr.GetName();
    // assume compatAttr is the one with "inputs:" for now
    UsdAttribute compatAttr = prim.GetAttribute(::compatName(defaultAttrName));
    if (!compatAttr)
    {
        return defaultAttr;
    }
    else if (compatAttr.HasAuthoredValue() && !defaultAttr.HasAuthoredValue())
    {
        return compatAttr;
    }
    return defaultAttr;
}

UsdLuxDomeLight usdex::core::defineDomeLight(
    UsdStagePtr stage,
    const SdfPath& path,
    float intensity,
    std::optional<std::string_view> texturePath,
    const TfToken& textureFormat
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxDomeLight due to an invalid location: %s", reason.c_str());
        return UsdLuxDomeLight();
    }

    if (texturePath.has_value() && !isValidTextureFormat(textureFormat))
    {
        TF_RUNTIME_ERROR(
            "Token \"[%s]\" is not a valid texture format token. See documentation of defineDomeLight for valid options.",
            textureFormat.data()
        );
        return UsdLuxDomeLight();
    }

    auto light = UsdLuxDomeLight::Define(stage, path);

    if (!light)
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxDomeLight at \"%s\"", path.GetAsString().c_str());
        return UsdLuxDomeLight();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = light.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    if (!initLightApiAttrs(light, intensity))
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxDomeLight at \"%s\"", path.GetAsString().c_str());
        return UsdLuxDomeLight();
    }

    if (texturePath.has_value())
    {
        light.CreateTextureFileAttr().Set(SdfAssetPath(texturePath.value().data()));
        light.CreateTextureFormatAttr().Set(textureFormat);
    }

    return light;
}

UsdLuxDomeLight usdex::core::defineDomeLight(
    UsdPrim parent,
    const std::string& name,
    float intensity,
    std::optional<std::string_view> texturePath,
    const TfToken& textureFormat
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxDomeLight due to an invalid location: %s", reason.c_str());
        return UsdLuxDomeLight();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineDomeLight(stage, path, intensity, texturePath, textureFormat);
}

UsdLuxDomeLight usdex::core::defineDomeLight(UsdPrim prim, float intensity, std::optional<std::string_view> texturePath, const TfToken& textureFormat)
{
    // Early out if the prim is not valid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxDomeLight on invalid prim");
        return UsdLuxDomeLight();
    }

    // Warn if original prim is not Scope or Xform
    TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"DomeLight\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::defineDomeLight(stage, path, intensity, texturePath, textureFormat);
}

UsdLuxRectLight usdex::core::defineRectLight(
    UsdStagePtr stage,
    const SdfPath& path,
    float width,
    float height,
    float intensity,
    std::optional<std::string_view> texturePath
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxRectLight due to an invalid location: %s", reason.c_str());
        return UsdLuxRectLight();
    }

    auto light = UsdLuxRectLight::Define(stage, path);

    if (!light)
    {
        TF_RUNTIME_ERROR("Light schema is not compatible with prim at \"%s\"", path.GetAsString().c_str());
        return UsdLuxRectLight();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = light.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    if (!initLightApiAttrs(light, intensity))
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxRectLight at \"%s\"", path.GetAsString().c_str());
        return UsdLuxRectLight();
    }

    light.CreateWidthAttr().Set(width);
    light.CreateHeightAttr().Set(height);
    if (auto boundable = UsdGeomBoundable(prim))
    {
        VtVec3fArray extent;
        UsdGeomBoundable::ComputeExtentFromPlugins(boundable, UsdTimeCode::Default(), &extent);
        boundable.CreateExtentAttr().Set(extent);
    }

    if (texturePath.has_value())
    {
        light.CreateTextureFileAttr().Set(SdfAssetPath(texturePath.value().data()));
    }

    return light;
}

UsdLuxRectLight usdex::core::defineRectLight(
    UsdPrim parent,
    const std::string& name,
    float width,
    float height,
    float intensity,
    std::optional<std::string_view> texturePath
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxRectLight due to an invalid location: %s", reason.c_str());
        return UsdLuxRectLight();
    }

    // Call overloaded function
    UsdStageWeakPtr stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::defineRectLight(stage, path, width, height, intensity, texturePath);
}

UsdLuxRectLight usdex::core::defineRectLight(UsdPrim prim, float width, float height, float intensity, std::optional<std::string_view> texturePath)
{
    // Early out if the prim is not valid
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdLuxRectLight on invalid prim");
        return UsdLuxRectLight();
    }

    // Warn if original prim is not Scope or Xform
    TfToken originalType = prim.GetTypeName();
    if (originalType != UsdGeomTokens->Scope && originalType != UsdGeomTokens->Xform && !originalType.IsEmpty())
    {
        TF_WARN(
            "Redefining prim at \"%s\" from type \"%s\" to \"RectLight\". Expected original type to be \"\" or \"Scope\" or \"Xform\".",
            prim.GetPath().GetAsString().c_str(),
            originalType.GetText()
        );
    }

    // Call the stage/path version
    UsdStageWeakPtr stage = prim.GetStage();
    const SdfPath& path = prim.GetPath();
    return usdex::core::defineRectLight(stage, path, width, height, intensity, texturePath);
}
