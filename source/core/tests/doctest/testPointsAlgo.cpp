// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include <usdex/test/ScopedDiagnosticChecker.h>

#include <usdex/core/PointsAlgo.h>

#include <pxr/base/tf/getenv.h>
#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdGeom/tokens.h>

#include <doctest/doctest.h>

#include <iostream>

using namespace usdex::core;
using namespace usdex::test;
using namespace pxr;

namespace
{

static constexpr const char* s_vtArrayStacksEnvVar = "VT_LOG_STACK_ON_ARRAY_DETACH_COPY";

} // namespace

TEST_CASE("definePointCloud accepts nullopt")
{
    ScopedDiagnosticChecker check;

    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    SdfPath path("/Points");
    VtVec3fArray points = { { 0, 0, 0 }, { 1, 1, 1 } };
    VtFloatArray widths = { 5, 10 };

    if (TfGetenvBool(s_vtArrayStacksEnvVar, false))
    {
        std::cerr << "BEGIN Expected Array Detach: 15 TfTokenArray detach warnings may appear after this call. ";
        std::cerr << "See https://github.com/PixarAnimationStudios/OpenUSD/pull/2816 for details." << std::endl;
    }
    UsdGeomPoints pointCloud = usdex::core::definePointCloud(
        stage,
        path,
        points,
        std::nullopt, // ids
        FloatPrimvarData(UsdGeomTokens->vertex, widths)
    );
    if (TfGetenvBool(s_vtArrayStacksEnvVar, false))
    {
        std::cerr << "END Expected Array Detach: Detach stack warnings after this may indicate an issue." << std::endl;
    }
    CHECK(pointCloud);

    UsdAttribute idsAttr = pointCloud.GetIdsAttr();
    CHECK(idsAttr);
    CHECK(idsAttr.IsDefined()); // its blocked, so it is defined
    CHECK(!idsAttr.HasAuthoredValue()); // but it has no value

    UsdGeomPrimvarsAPI primvarsApi(pointCloud);
    CHECK(primvarsApi);

    UsdGeomPrimvar primvar = primvarsApi.GetPrimvar(UsdGeomTokens->widths);
    CHECK(primvar.IsDefined());
    CHECK(primvar.HasAuthoredValue());
    CHECK(primvar.HasAuthoredInterpolation());
    CHECK(primvar.GetInterpolation() == UsdGeomTokens->vertex);
    VtArray<float> authoredWidths;
    primvar.Get(&authoredWidths);
    CHECK(authoredWidths.IsIdentical(widths));
}

TEST_CASE("definePointCloud does not detach arrays")
{
    ScopedDiagnosticChecker check;

    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    SdfPath path("/Points");
    VtVec3fArray points = { { 0, 0, 0 }, { 1, 1, 1 } };
    VtInt64Array ids = { 0, 1 };
    VtFloatArray widths = { 5, 10 };
    VtIntArray widthsIndices = { 0, 1 };
    VtVec3fArray normals = { { 1, 0, 0 }, { 0, 1, 0 } };
    VtIntArray normalsIndices = { 0, 1 };
    VtVec3fArray colors = { { 1, 0, 0 }, { 0, 1, 0 } };
    VtIntArray colorIndices = { 0, 1 };
    VtFloatArray opacities = { 0.8f };
    VtIntArray opacityIndices = { 0, 0 };

    UsdGeomPoints pointCloud = usdex::core::definePointCloud(
        stage,
        path,
        points,
        ids,
        FloatPrimvarData(UsdGeomTokens->vertex, widths, widthsIndices),
        Vec3fPrimvarData(UsdGeomTokens->vertex, normals, normalsIndices),
        Vec3fPrimvarData(UsdGeomTokens->vertex, colors, colorIndices),
        FloatPrimvarData(UsdGeomTokens->vertex, opacities, opacityIndices)
    );
    CHECK(pointCloud);

    UsdAttribute idsAttr = pointCloud.GetIdsAttr();
    CHECK(idsAttr.IsDefined());
    CHECK(idsAttr.HasAuthoredValue());
    VtInt64Array authoredIds;
    idsAttr.Get(&authoredIds);
    CHECK(authoredIds.IsIdentical(ids));

    UsdGeomPrimvarsAPI primvarsApi(pointCloud);
    CHECK(primvarsApi);

    UsdGeomPrimvar primvar = primvarsApi.GetPrimvar(UsdGeomTokens->widths);
    CHECK(primvar.IsDefined());
    CHECK(primvar.HasAuthoredValue());
    CHECK(primvar.HasAuthoredInterpolation());
    CHECK(primvar.GetInterpolation() == UsdGeomTokens->vertex);
    VtFloatArray authoredWidths;
    primvar.Get(&authoredWidths);
    CHECK(authoredWidths.IsIdentical(widths));
    CHECK(primvar.IsIndexed());
    VtIntArray authoredIndices;
    primvar.GetIndices(&authoredIndices);
    CHECK(authoredIndices.IsIdentical(widthsIndices));

    primvar = primvarsApi.GetPrimvar(UsdGeomTokens->normals);
    CHECK(primvar.IsDefined());
    CHECK(primvar.HasAuthoredValue());
    CHECK(primvar.HasAuthoredInterpolation());
    CHECK(primvar.GetInterpolation() == UsdGeomTokens->vertex);
    VtVec3fArray authoredNormals;
    primvar.Get(&authoredNormals);
    CHECK(authoredNormals.IsIdentical(normals));
    CHECK(primvar.IsIndexed());
    primvar.GetIndices(&authoredIndices);
    CHECK(authoredIndices.IsIdentical(normalsIndices));

    primvar = pointCloud.GetDisplayColorPrimvar();
    CHECK(primvar.IsDefined());
    CHECK(primvar.HasAuthoredValue());
    CHECK(primvar.HasAuthoredInterpolation());
    CHECK(primvar.GetInterpolation() == UsdGeomTokens->vertex);
    VtVec3fArray authoredColors;
    primvar.Get(&authoredColors);
    CHECK(authoredColors.IsIdentical(colors));
    CHECK(primvar.IsIndexed());
    primvar.GetIndices(&authoredIndices);
    CHECK(authoredIndices.IsIdentical(colorIndices));

    primvar = pointCloud.GetDisplayOpacityPrimvar();
    CHECK(primvar.IsDefined());
    CHECK(primvar.HasAuthoredValue());
    CHECK(primvar.HasAuthoredInterpolation());
    CHECK(primvar.GetInterpolation() == UsdGeomTokens->vertex);
    VtFloatArray authoredOpacities;
    primvar.Get(&authoredOpacities);
    CHECK(authoredOpacities.IsIdentical(opacities));
    CHECK(primvar.IsIndexed());
    primvar.GetIndices(&authoredIndices);
    CHECK(authoredIndices.IsIdentical(opacityIndices));
}
