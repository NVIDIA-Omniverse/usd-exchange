// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "usdex/core/AttributeAlgo.h"

#include <pxr/base/tf/diagnostic.h>
#include <pxr/base/tf/stringUtils.h>
#include <pxr/usd/sdf/attributeSpec.h>
#include <pxr/usd/sdf/schema.h>
#include <pxr/usd/usd/attribute.h>
#include <pxr/usd/usd/primDefinition.h>
#include <pxr/usd/usd/stage.h>

#include <algorithm>

using namespace pxr;

namespace
{

// Get the schema fallback value for the given attribute.
VtValue getSchemaFallbackValue(const UsdPrim& prim, const TfToken& attrName, const UsdAttribute& attr)
{
    VtValue fallback;
    if (prim.GetPrimDefinition().GetAttributeFallbackValue(attrName, &fallback))
    {
        return fallback;
    }

    if (!attr.HasAuthoredValue())
    {
        VtValue resolved;
        if (attr.Get(&resolved))
        {
            return resolved;
        }
    }

    return VtValue();
}

// Cast the value to the attribute type.
bool castValueToAttributeType(const UsdAttribute& attr, const VtValue& value, VtValue* castValue, std::string* reason)
{
    const TfType expectedType = attr.GetTypeName().GetType();
    const TfType valueType = value.GetType();

    if (valueType == expectedType)
    {
        *castValue = value;
        return true;
    }

    // Common conversions for converter clients.
    if (valueType == TfType::Find<double>() && expectedType == TfType::Find<float>())
    {
        *castValue = VtValue(static_cast<float>(value.UncheckedGet<double>()));
        return true;
    }
    if (valueType == TfType::Find<float>() && expectedType == TfType::Find<double>())
    {
        *castValue = VtValue(static_cast<double>(value.UncheckedGet<float>()));
        return true;
    }
    if (valueType == TfType::Find<int>() && expectedType == TfType::Find<float>())
    {
        *castValue = VtValue(static_cast<float>(value.UncheckedGet<int>()));
        return true;
    }
    if (valueType == TfType::Find<int>() && expectedType == TfType::Find<double>())
    {
        *castValue = VtValue(static_cast<double>(value.UncheckedGet<int>()));
        return true;
    }
    if (valueType == TfType::Find<bool>() && expectedType == TfType::Find<int>())
    {
        *castValue = VtValue(static_cast<int>(value.UncheckedGet<bool>() ? 1 : 0));
        return true;
    }
    if (valueType == TfType::Find<bool>() && expectedType == TfType::Find<float>())
    {
        *castValue = VtValue(static_cast<float>(value.UncheckedGet<bool>() ? 1.0f : 0.0f));
        return true;
    }
    if (valueType == TfType::Find<bool>() && expectedType == TfType::Find<double>())
    {
        *castValue = VtValue(static_cast<double>(value.UncheckedGet<bool>() ? 1.0 : 0.0));
        return true;
    }
    if (valueType == TfType::Find<int>() && expectedType == TfType::Find<bool>())
    {
        *castValue = VtValue(static_cast<bool>(value.UncheckedGet<int>() != 0));
        return true;
    }
    if (valueType == TfType::Find<float>() && expectedType == TfType::Find<bool>())
    {
        *castValue = VtValue(static_cast<bool>(value.UncheckedGet<float>() != 0.0f));
        return true;
    }
    if (valueType == TfType::Find<double>() && expectedType == TfType::Find<bool>())
    {
        *castValue = VtValue(static_cast<bool>(value.UncheckedGet<double>() != 0.0));
        return true;
    }
    if (valueType == TfType::Find<GfVec2f>() && expectedType == TfType::Find<GfVec2d>())
    {
        *castValue = VtValue(GfVec2d(value.UncheckedGet<GfVec2f>()));
        return true;
    }
    if (valueType == TfType::Find<GfVec2d>() && expectedType == TfType::Find<GfVec2f>())
    {
        *castValue = VtValue(GfVec2f(value.UncheckedGet<GfVec2d>()));
        return true;
    }
    if (valueType == TfType::Find<GfVec3f>() && expectedType == TfType::Find<GfVec3d>())
    {
        *castValue = VtValue(GfVec3d(value.UncheckedGet<GfVec3f>()));
        return true;
    }
    if (valueType == TfType::Find<GfVec3d>() && expectedType == TfType::Find<GfVec3f>())
    {
        *castValue = VtValue(GfVec3f(value.UncheckedGet<GfVec3d>()));
        return true;
    }
    if (valueType == TfType::Find<GfVec4f>() && expectedType == TfType::Find<GfVec4d>())
    {
        *castValue = VtValue(GfVec4d(value.UncheckedGet<GfVec4f>()));
        return true;
    }
    if (valueType == TfType::Find<GfVec4d>() && expectedType == TfType::Find<GfVec4f>())
    {
        *castValue = VtValue(GfVec4f(value.UncheckedGet<GfVec4d>()));
        return true;
    }
    if (valueType == TfType::Find<GfQuatf>() && expectedType == TfType::Find<GfQuatd>())
    {
        *castValue = VtValue(GfQuatd(value.UncheckedGet<GfQuatf>()));
        return true;
    }
    if (valueType == TfType::Find<GfQuatd>() && expectedType == TfType::Find<GfQuatf>())
    {
        *castValue = VtValue(GfQuatf(value.UncheckedGet<GfQuatd>()));
        return true;
    }
    if (valueType == TfType::Find<TfToken>() && expectedType == TfType::Find<std::string>())
    {
        *castValue = VtValue(value.UncheckedGet<TfToken>().GetString());
        return true;
    }
    if (valueType == TfType::Find<std::string>() && expectedType == TfType::Find<TfToken>())
    {
        *castValue = VtValue(TfToken(value.UncheckedGet<std::string>().c_str()));
        return true;
    }

    *reason = TfStringPrintf(
        "Value type \"%s\" cannot be converted to attribute type \"%s\" for \"%s\"",
        valueType.GetTypeName().c_str(),
        expectedType.GetTypeName().c_str(),
        attr.GetName().GetString().c_str()
    );
    return false;
}

// Check if the attribute has an authored default in the given layer.
bool hasAuthoredDefaultInLayer(const SdfLayerHandle& layer, const SdfPath& path)
{
    const SdfAttributeSpecHandle spec = layer->GetAttributeAtPath(path);
    return spec && spec->HasField(SdfFieldKeys->Default);
}

// Check if the attribute has an authored opinion in a weaker layer.
bool hasAuthoredOpinionInWeakerLayer(const UsdAttribute& attr)
{
    const UsdStageWeakPtr stage = attr.GetPrim().GetStage();
    if (!stage)
    {
        return false;
    }

    const SdfLayerHandle editLayer = stage->GetEditTarget().GetLayer();
    if (!editLayer)
    {
        return false;
    }

    const SdfPath path = attr.GetPath();
    const SdfLayerHandleVector layerStack = stage->GetLayerStack(/* includeSessionLayers = */ false);
    const auto editLayerIt = std::find(layerStack.begin(), layerStack.end(), editLayer);
    if (editLayerIt == layerStack.end())
    {
        return attr.HasAuthoredValue();
    }

    for (auto layerIt = editLayerIt + 1; layerIt != layerStack.end(); ++layerIt)
    {
        if (hasAuthoredDefaultInLayer(*layerIt, path))
        {
            return true;
        }
    }
    return false;
}

// Revert the attribute to the schema fallback value.
void revertAttributeToFallback(const UsdAttribute& attr)
{
    if (!attr.HasAuthoredValue())
    {
        return;
    }

    if (hasAuthoredOpinionInWeakerLayer(attr))
    {
        attr.Block();
        return;
    }

    attr.Clear();
}

} // namespace

bool usdex::core::setEffectiveAttributeValue(const UsdPrim& prim, const TfToken& name, const VtValue& value)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to author attribute \"%s\" on an invalid prim", name.GetText());
        return false;
    }

    UsdAttribute attr = prim.GetAttribute(name);
    if (!attr)
    {
        TF_RUNTIME_ERROR("Attribute \"%s\" is not defined on prim <%s>", name.GetText(), prim.GetPath().GetText());
        return false;
    }

    if (value.IsEmpty())
    {
        // to set the default/fallback, we must block instead of Set(None)
        // which means there will be no authored value
        attr.Block();
        return true;
    }

    // Cast the value to the attribute type.
    std::string reason;
    VtValue castValue;
    if (!::castValueToAttributeType(attr, value, &castValue, &reason))
    {
        TF_RUNTIME_ERROR("Incompatible value type for attribute \"%s\" on prim <%s>: %s", name.GetText(), prim.GetPath().GetText(), reason.c_str());
        return false;
    }

    // If the value is equal to the schema fallback value, skip authoring.
    const VtValue fallback = ::getSchemaFallbackValue(prim, name, attr);
    if (castValue == fallback)
    {
        ::revertAttributeToFallback(attr);
        return true;
    }

    if (!attr.Set(castValue))
    {
        TF_RUNTIME_ERROR("Failed to write attribute \"%s\" on prim <%s> in the current edit target", name.GetText(), prim.GetPath().GetText());
        return false;
    }

    return true;
}
