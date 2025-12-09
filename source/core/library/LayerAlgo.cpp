// SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/LayerAlgo.h"

#include <pxr/usd/usd/stage.h>

#if PXR_VERSION < 2511
#include <pxr/usd/usd/usdFileFormat.h>
#include <pxr/usd/usd/usdaFileFormat.h>
#include <pxr/usd/usd/usdcFileFormat.h>
#else
#include <pxr/usd/sdf/usdFileFormat.h>
#include <pxr/usd/sdf/usdaFileFormat.h>
#include <pxr/usd/sdf/usdcFileFormat.h>
#endif

using namespace pxr;

namespace
{

static constexpr const char* g_authoringKey = "creator";

} // namespace

bool usdex::core::hasLayerAuthoringMetadata(const pxr::SdfLayerHandle layer)
{
    VtDictionary data = layer->GetCustomLayerData();
    return data.find(g_authoringKey) != data.end();
}

void usdex::core::setLayerAuthoringMetadata(pxr::SdfLayerHandle layer, const std::string& value)
{
    VtDictionary data = layer->GetCustomLayerData();
    data[g_authoringKey] = value;
    layer->SetCustomLayerData(data);
}

std::string usdex::core::getLayerAuthoringMetadata(const pxr::SdfLayerHandle layer)
{
    VtDictionary data = layer->GetCustomLayerData();
    auto it = data.find(g_authoringKey);
    if (it != data.end())
    {
        return it->second.Get<std::string>();
    }
    return "";
}

bool usdex::core::saveLayer(pxr::SdfLayerHandle layer, std::optional<std::string_view> authoringMetadata, std::optional<std::string_view> comment)
{
    if (authoringMetadata.has_value())
    {
        setLayerAuthoringMetadata(layer, authoringMetadata.value().data());
    }

    bool success;
    if (comment.has_value())
    {
        TF_STATUS("Saving \"%s\" with comment \"%s\"", layer->GetIdentifier().c_str(), comment.value().data());
        layer->SetComment(comment.value().data());
        success = layer->Save();
    }
    else
    {
        TF_STATUS("Saving \"%s\"", layer->GetIdentifier().c_str());
        success = layer->Save();
    }

    return success;
}

bool usdex::core::exportLayer(
    SdfLayerHandle layer,
    const std::string& identifier,
    const std::string& authoringMetadata,
    std::optional<std::string_view> comment,
    const SdfLayer::FileFormatArguments& fileFormatArgs
)
{
    // Early out on an unsupported identifier
    if (identifier.empty() || !UsdStage::IsSupportedFile(identifier))
    {
        TF_WARN("Unable to export SdfLayer to \"%s\" due to an invalid identifier", identifier.c_str());
        return false;
    }

    // Ensure that layer authoring metadata exists.
    if (!hasLayerAuthoringMetadata(layer))
    {
        setLayerAuthoringMetadata(layer, authoringMetadata);
    }

    bool success;
    if (comment.has_value())
    {
        TF_STATUS("Exporting \"%s\" with comment \"%s\"", identifier.c_str(), comment.value().data());

        // Capture the existing comment in the layer so that it can be restored after export.
        // We do not want to modify the source layer, but equally we do not want to have to open the exported layer to make changes.
        const std::string& existingComment = layer->GetComment();
        layer->SetComment(comment.value().data());
        success = layer->Export(identifier, "", fileFormatArgs);
        // Restore the comment
        layer->SetComment(existingComment);
    }
    else
    {
        TF_STATUS("Exporting \"%s\"", identifier.c_str());
        success = layer->Export(identifier, "", fileFormatArgs);
    }

    return success;
}

TfToken usdex::core::getUsdLayerEncoding(const SdfLayerHandle layer)
{
    SdfFileFormatConstPtr fileFormat = layer->GetFileFormat();

#if PXR_VERSION < 2511

    // If the encoding is explicitly usda return that extension
    if (fileFormat == SdfFileFormat::FindById(UsdUsdaFileFormatTokens->Id))
    {
        return UsdUsdaFileFormatTokens->Id;
    }

    // If the encoding is explicitly usdc return that extension
    if (fileFormat == SdfFileFormat::FindById(UsdUsdcFileFormatTokens->Id))
    {
        return UsdUsdcFileFormatTokens->Id;
    }

    if (fileFormat == SdfFileFormat::FindById(UsdUsdFileFormatTokens->Id))
    {
        return UsdUsdFileFormat::GetUnderlyingFormatForLayer(*layer);
    }

#else

    // If the encoding is explicitly usda return that extension
    if (fileFormat == SdfFileFormat::FindById(SdfUsdaFileFormatTokens->Id))
    {
        return SdfUsdaFileFormatTokens->Id;
    }

    // If the encoding is explicitly usdc return that extension
    if (fileFormat == SdfFileFormat::FindById(SdfUsdcFileFormatTokens->Id))
    {
        return SdfUsdcFileFormatTokens->Id;
    }

    if (fileFormat == SdfFileFormat::FindById(SdfUsdFileFormatTokens->Id))
    {
        return SdfUsdFileFormat::GetUnderlyingFormatForLayer(*layer);
    }

#endif

    static TfToken empty;
    return empty;
}
