// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include <usdex/test/FilesystemUtils.h>
#include <usdex/test/ScopedDiagnosticChecker.h>

#include <usdex/core/AssetStructure.h>
#include <usdex/core/Core.h>
#include <usdex/core/Feature.h>
#include <usdex/core/LayerAlgo.h>
#include <usdex/core/StageAlgo.h>
#include <usdex/core/Version.h>

#include <pxr/base/tf/fileUtils.h>
#include <pxr/base/tf/stringUtils.h>
#include <pxr/base/vt/dictionary.h>
#include <pxr/usd/sdf/fileFormat.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usdGeom/metrics.h>
#include <pxr/usd/usdGeom/scope.h>
#include <pxr/usd/usdGeom/tokens.h>
#include <pxr/usd/usdUtils/pipeline.h>

#include <doctest/doctest.h>

using namespace usdex::test;
using namespace pxr;

namespace
{

std::string getAuthoringMetadata()
{
    return TfStringPrintf("usdex cpp tests: %s, usd_ver: %d, with_python: %d", usdex::core::version(), PXR_VERSION, usdex::core::withPython());
}

void deleteFiles(const std::vector<std::string>& files)
{
    for (const std::string& file : files)
    {
        if (TfIsFile(file))
        {
            TfDeleteFile(file);
        }
    }
}

} // namespace

TEST_CASE("createAssetPayload invalid asset payload stage")
{
    UsdStageRefPtr assetPayloadStage = nullptr;

    // invalid asset stage
    {
        ScopedDiagnosticChecker check({ { TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid asset stage" } });
        assetPayloadStage = usdex::core::createAssetPayload(nullptr);
    }
    CHECK(assetPayloadStage == nullptr);

    // anonymous asset stage
    {
        ScopedDiagnosticChecker check({ { TF_DIAGNOSTIC_WARNING_TYPE, ".*anonymous asset stage" } });
        assetPayloadStage = usdex::core::createAssetPayload(UsdStage::CreateInMemory());
    }
    CHECK(assetPayloadStage == nullptr);
}

TEST_CASE("createAssetPayload valid asset stage")
{
    const std::string defaultPrimName = "Root";
    const TfToken& upAxis = UsdGeomTokens->y;
    const double linearUnits = UsdGeomLinearUnits::meters;
    const std::string authoringMetadata = ::getAuthoringMetadata();
    const char* stageExtensions[] = { "usda", "usdc", "usda" };
    // note: "usd" extension will be encoded with "usda" intentionally (non-default)
    const char* expectedEncodings[] = { "usda", "usdc", "usda" };

    for (size_t i = 0; i < sizeof(stageExtensions) / sizeof(stageExtensions[0]); i++)
    {
        const char* stageExtension = stageExtensions[i];
        const char* expectedEncoding = expectedEncodings[i];
        UsdStageRefPtr assetStage = nullptr;
        UsdStageRefPtr assetPayloadStage = nullptr;
        usdex::test::ScopedTmpDir tmpDir;
        std::string assetStageIdentifier = TfStringPrintf("%s/test.usda", tmpDir.getPath());

        // create asset stage
        assetStage = usdex::core::createStage(assetStageIdentifier, defaultPrimName, upAxis, linearUnits, authoringMetadata);
        CHECK(assetStage != nullptr);

        // create asset payload stage
        SdfLayer::FileFormatArguments fileFormatArgs = { { "format", expectedEncoding } };
        assetPayloadStage = usdex::core::createAssetPayload(assetStage, stageExtension, fileFormatArgs);
        CHECK(assetPayloadStage != nullptr);
        std::string fullIdentifier = TfStringPrintf(
            "%s/%s/%s.%s",
            tmpDir.getPath(),
            usdex::core::getPayloadToken().GetText(),
            usdex::core::getContentsToken().GetText(),
            stageExtension
        );
        CHECK(usdex::test::compareIdentifiers(assetPayloadStage->GetRootLayer()->GetIdentifier(), fullIdentifier));
        CHECK(usdex::core::getUsdLayerEncoding(assetPayloadStage->GetRootLayer()) == expectedEncoding);
        CHECK(usdex::core::hasLayerAuthoringMetadata(assetPayloadStage->GetRootLayer()));
        CHECK(usdex::core::getLayerAuthoringMetadata(assetPayloadStage->GetRootLayer()) == authoringMetadata);

        assetStage = nullptr;
        assetPayloadStage = nullptr;
        ::deleteFiles({ assetStageIdentifier, fullIdentifier });
    }
}

TEST_CASE("addAssetContent invalid payload stage")
{
    UsdStageRefPtr assetPayloadStage = nullptr;

    // invalid payload stage
    {
        ScopedDiagnosticChecker check({ { TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid payload stage" } });
        assetPayloadStage = usdex::core::addAssetContent(nullptr, "test");
    }
    CHECK(assetPayloadStage == nullptr);

    // anonymous payload stage
    {
        ScopedDiagnosticChecker check({ { TF_DIAGNOSTIC_WARNING_TYPE, ".*anonymous payload stage" } });
        assetPayloadStage = usdex::core::addAssetContent(UsdStage::CreateInMemory(), "test");
    }
    CHECK(assetPayloadStage == nullptr);
}

TEST_CASE("addAssetContent valid payload stage")
{
    const std::string defaultPrimName = "Root";
    const TfToken& upAxis = UsdGeomTokens->y;
    const double linearUnits = UsdGeomLinearUnits::meters;
    const std::string authoringMetadata = ::getAuthoringMetadata();
    const TfToken assetContentNames[] = { usdex::core::getGeometryToken(), UsdUtilsGetMaterialsScopeName(), usdex::core::getPhysicsToken() };
    const char* stageExtensions[] = { "usda", "usdc", "usda" };
    // note: "usd" extension will be encoded with "usda" intentionally (non-default)
    const char* expectedEncodings[] = { "usda", "usdc", "usda" };

    for (size_t i = 0; i < sizeof(stageExtensions) / sizeof(stageExtensions[0]); i++)
    {
        const char* stageExtension = stageExtensions[i];
        const char* expectedEncoding = expectedEncodings[i];
        UsdStageRefPtr assetStage = nullptr;
        UsdStageRefPtr assetPayloadStage = nullptr;
        UsdStageRefPtr assetContentStage = nullptr;
        usdex::test::ScopedTmpDir tmpDir;
        std::string assetStageIdentifier = TfStringPrintf("%s/test.%s", tmpDir.getPath(), stageExtension);
        std::vector<std::string> generatedFiles = { assetStageIdentifier };

        // create asset stage
        assetStage = usdex::core::createStage(assetStageIdentifier, defaultPrimName, upAxis, linearUnits, authoringMetadata);
        CHECK(assetStage != nullptr);

        // create asset payload stage
        assetPayloadStage = usdex::core::createAssetPayload(assetStage);
        CHECK(assetPayloadStage != nullptr);

        /////////////////////////////////
        // add asset content stage (prependLayer = true, createScope = true)
        SdfLayer::FileFormatArguments fileFormatArgs = { { "format", expectedEncoding } };
        assetContentStage = usdex::core::addAssetContent(assetPayloadStage, assetContentNames[0], stageExtension, fileFormatArgs);
        CHECK(assetContentStage != nullptr);

        // check that the asset content stage is a usda file
        CHECK(usdex::core::getUsdLayerEncoding(assetContentStage->GetRootLayer()) == expectedEncoding);
        CHECK(usdex::core::hasLayerAuthoringMetadata(assetContentStage->GetRootLayer()));
        CHECK(usdex::core::getLayerAuthoringMetadata(assetContentStage->GetRootLayer()) == authoringMetadata);

        // check that the asset content stage is a sublayer of the asset payload stage
        std::string relativeIdentifier = TfStringPrintf("./%s.%s", assetContentNames[0].GetText(), stageExtension);
        SdfSubLayerProxy subLayerPaths = assetPayloadStage->GetRootLayer()->GetSubLayerPaths();
        // check that there is only one sublayer and that it's the correct identifier
        CHECK(subLayerPaths.size() == 1);
        CHECK(subLayerPaths.Find(relativeIdentifier) == 0);

        // check that the asset content stage is the correct identifier
        std::string assetContentStageIdentifier = TfStringPrintf(
            "%s/%s/%s.%s",
            tmpDir.getPath(),
            usdex::core::getPayloadToken().GetText(),
            assetContentNames[0].GetText(),
            stageExtension
        );
        CHECK(usdex::test::compareIdentifiers(assetContentStage->GetRootLayer()->GetIdentifier(), assetContentStageIdentifier));
        generatedFiles.push_back(assetContentStageIdentifier);

        // check that the asset content stage has a default prim and it's the correct name
        UsdPrim defaultPrim = assetContentStage->GetDefaultPrim();
        CHECK(defaultPrim.GetName() == defaultPrimName);

        // check that the asset content stage has a correctly named scope
        UsdPrim prim = assetContentStage->GetPrimAtPath(defaultPrim.GetPath().AppendChild(TfToken(assetContentNames[0])));
        CHECK(prim);
        UsdGeomScope scopePrim = UsdGeomScope(prim);
        CHECK(scopePrim);

        /////////////////////////////////
        // add asset content stage (prependLayer = false, createScope = true)
        assetContentStage = usdex::core::addAssetContent(
            assetPayloadStage,
            assetContentNames[1],
            stageExtension,
            SdfLayer::FileFormatArguments(),
            false,
            true
        );
        CHECK(assetContentStage != nullptr);

        // check that the asset content stage is a sublayer of the asset payload stage
        relativeIdentifier = TfStringPrintf("./%s.%s", assetContentNames[1].GetText(), stageExtension);
        subLayerPaths = assetPayloadStage->GetRootLayer()->GetSubLayerPaths();
        // check that there are two sublayers and that the second one is the correct identifier
        CHECK(subLayerPaths.size() == 2);
        CHECK(subLayerPaths.Find(relativeIdentifier) == 1);

        // check that the asset content stage is the correct identifier
        assetContentStageIdentifier = TfStringPrintf(
            "%s/%s/%s.%s",
            tmpDir.getPath(),
            usdex::core::getPayloadToken().GetText(),
            assetContentNames[1].GetText(),
            stageExtension
        );
        CHECK(usdex::test::compareIdentifiers(assetContentStage->GetRootLayer()->GetIdentifier(), assetContentStageIdentifier));
        generatedFiles.push_back(assetContentStageIdentifier);

        /////////////////////////////////
        // add asset content stage (prependLayer = true, createScope = false)
        assetContentStage = usdex::core::addAssetContent(
            assetPayloadStage,
            assetContentNames[2],
            stageExtension,
            SdfLayer::FileFormatArguments(),
            true,
            false
        );
        CHECK(assetContentStage != nullptr);

        // check that the asset content stage is a sublayer of the asset payload stage
        relativeIdentifier = TfStringPrintf("./%s.%s", assetContentNames[2].GetText(), stageExtension);
        subLayerPaths = assetPayloadStage->GetRootLayer()->GetSubLayerPaths();
        // check that there are three sublayers and that the third one is the correct identifier
        CHECK(subLayerPaths.size() == 3);
        CHECK(subLayerPaths.Find(relativeIdentifier) == 0);

        // check that the asset content stage is the correct identifier
        assetContentStageIdentifier = TfStringPrintf(
            "%s/%s/%s.%s",
            tmpDir.getPath(),
            usdex::core::getPayloadToken().GetText(),
            assetContentNames[2].GetText(),
            stageExtension
        );
        CHECK(usdex::test::compareIdentifiers(assetContentStage->GetRootLayer()->GetIdentifier(), assetContentStageIdentifier));
        generatedFiles.push_back(assetContentStageIdentifier);

        // check that the asset content stage has a default prim and it's the correct name
        defaultPrim = assetContentStage->GetDefaultPrim();
        CHECK(defaultPrim.GetName() == defaultPrimName);
        prim = assetContentStage->GetPrimAtPath(defaultPrim.GetPath().AppendChild(assetContentNames[2]));
        CHECK(!prim);

        assetStage = nullptr;
        assetPayloadStage = nullptr;
        assetContentStage = nullptr;
        ::deleteFiles(generatedFiles);
    }
}

TEST_CASE("addAssetLibrary invalid content stage")
{
    UsdStageRefPtr assetLibraryStage = nullptr;

    // invalid payload stage
    {
        ScopedDiagnosticChecker check({ { TF_DIAGNOSTIC_WARNING_TYPE, ".*invalid payload stage" } });
        assetLibraryStage = usdex::core::addAssetLibrary(nullptr, "test");
    }
    CHECK(assetLibraryStage == nullptr);

    // anonymous payload stage
    {
        ScopedDiagnosticChecker check({ { TF_DIAGNOSTIC_WARNING_TYPE, ".*anonymous payload stage" } });
        assetLibraryStage = usdex::core::addAssetLibrary(UsdStage::CreateInMemory(), "test");
    }
    CHECK(assetLibraryStage == nullptr);
}

TEST_CASE("addAssetLibrary valid content stage")
{
    const std::string defaultPrimName = "Root";
    const TfToken& upAxis = UsdGeomTokens->y;
    const double linearUnits = UsdGeomLinearUnits::meters;
    const std::string authoringMetadata = ::getAuthoringMetadata();
    const std::string libraryName(usdex::core::getGeometryToken().GetString());
    const char* formats[] = { "usda", "usdc", "usd" };
    // note: "usd" extension will be encoded with "usda" intentionally (non-default)
    const char* expectedEncodings[] = { "usda", "usdc", "usda" };

    for (size_t i = 0; i < sizeof(formats) / sizeof(formats[0]); i++)
    {
        const char* format = formats[i];
        const char* expectedEncoding = expectedEncodings[i];
        UsdStageRefPtr assetPayloadStage = nullptr;
        UsdStageRefPtr assetLibraryStage = nullptr;
        usdex::test::ScopedTmpDir tmpDir;

        // create asset payload stage directly
        std::string assetPayloadStageIdentifier = TfStringPrintf(
            "%s/%s/%s.usda",
            tmpDir.getPath(),
            usdex::core::getPayloadToken().GetText(),
            usdex::core::getContentsToken().GetText()
        );
        assetPayloadStage = usdex::core::createStage(assetPayloadStageIdentifier, defaultPrimName, upAxis, linearUnits, authoringMetadata);
        CHECK(assetPayloadStage != nullptr);

        SdfLayer::FileFormatArguments fileFormatArgs = { { "format", expectedEncoding } };
        assetLibraryStage = usdex::core::addAssetLibrary(assetPayloadStage, libraryName, format, fileFormatArgs);
        CHECK(assetLibraryStage != nullptr);

        // check that the library stage file path is correct
        std::string expectedLibraryIdentifier = TfStringPrintf(
            "%s/%s/%s%s.%s",
            tmpDir.getPath(),
            usdex::core::getPayloadToken().GetText(),
            libraryName.c_str(),
            usdex::core::getLibraryToken().GetText(),
            format
        );
        CHECK(usdex::test::compareIdentifiers(assetLibraryStage->GetRootLayer()->GetIdentifier(), expectedLibraryIdentifier));

        // check that the library stage has the correct encoding (usdc by default)
        CHECK(usdex::core::getUsdLayerEncoding(assetLibraryStage->GetRootLayer()) == expectedEncoding);

        // check that the library stage has the correct default prim name and it has a class specifier
        UsdPrim defaultPrim = assetLibraryStage->GetDefaultPrim();
        CHECK(defaultPrim.GetName() == libraryName);
        CHECK(defaultPrim.GetSpecifier() == SdfSpecifierClass);

        // check stage metadata
        CHECK(UsdGeomGetStageUpAxis(assetLibraryStage) == upAxis);
        CHECK(UsdGeomGetStageMetersPerUnit(assetLibraryStage) == linearUnits);
        CHECK(usdex::core::hasLayerAuthoringMetadata(assetLibraryStage->GetRootLayer()));
        CHECK(usdex::core::getLayerAuthoringMetadata(assetLibraryStage->GetRootLayer()) == authoringMetadata);

        assetPayloadStage = nullptr;
        assetLibraryStage = nullptr;
        ::deleteFiles({ assetPayloadStageIdentifier, expectedLibraryIdentifier });
    }
}

TEST_CASE("addAssetLibrary default format")
{
    const std::string defaultPrimName = "Root";
    const TfToken& upAxis = UsdGeomTokens->y;
    const double linearUnits = UsdGeomLinearUnits::meters;
    const std::string authoringMetadata = ::getAuthoringMetadata();
    const std::string libraryName(usdex::core::getGeometryToken().GetString());

    UsdStageRefPtr assetPayloadStage = nullptr;
    UsdStageRefPtr assetLibraryStage = nullptr;
    usdex::test::ScopedTmpDir tmpDir;

    // create asset payload stage directly
    std::string assetPayloadStageIdentifier = TfStringPrintf(
        "%s/%s/%s.usda",
        tmpDir.getPath(),
        usdex::core::getPayloadToken().GetText(),
        usdex::core::getContentsToken().GetText()
    );
    assetPayloadStage = usdex::core::createStage(assetPayloadStageIdentifier, defaultPrimName, upAxis, linearUnits, authoringMetadata);
    CHECK(assetPayloadStage != nullptr);

    // test with default format (should be usdc)
    assetLibraryStage = usdex::core::addAssetLibrary(assetPayloadStage, libraryName);
    CHECK(assetLibraryStage != nullptr);

    // check that the library stage file path is correct (should use usdc by default)
    std::string expectedLibraryIdentifier = TfStringPrintf(
        "%s/%s/%s%s.usdc",
        tmpDir.getPath(),
        usdex::core::getPayloadToken().GetText(),
        libraryName.c_str(),
        usdex::core::getLibraryToken().GetText()
    );
    CHECK(usdex::test::compareIdentifiers(assetLibraryStage->GetRootLayer()->GetIdentifier(), expectedLibraryIdentifier));

    // check that the library stage has the correct encoding (usdc by default)
    CHECK(usdex::core::getUsdLayerEncoding(assetLibraryStage->GetRootLayer()) == "usdc");
}
