// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

// C++ doctests for setEffectiveAttributeValue type coercion paths that Python unit tests
// cannot exercise. Python floating-point literals are converted to double in VtValue,
// so branches that require float (or explicit TfToken/string types) are covered here.

#include <usdex/core/AssetStructure.h>
#include <usdex/core/AttributeAlgo.h>

#include <pxr/base/vt/value.h>
#include <pxr/usd/sdf/valueTypeName.h>
#include <pxr/usd/usd/attribute.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>

#include <doctest/doctest.h>

using namespace pxr;


TEST_CASE("setEffectiveAttributeValue coerces float to double")
{
    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdPrim prim = usdex::core::defineScope(stage, SdfPath("/Scope")).GetPrim();
    UsdAttribute doubleAttr = prim.CreateAttribute(TfToken("doubleAttr"), SdfValueTypeNames->Double, true);

    const bool result = usdex::core::setEffectiveAttributeValue(prim, TfToken("doubleAttr"), VtValue(1.0f));
    CHECK(result);
    CHECK(doubleAttr.HasAuthoredValue());

    double authoredValue = 0.0;
    CHECK(doubleAttr.Get(&authoredValue));
    CHECK(authoredValue == doctest::Approx(1.0));
}

TEST_CASE("setEffectiveAttributeValue coerces float to bool")
{
    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdPrim prim = usdex::core::defineScope(stage, SdfPath("/Scope")).GetPrim();
    UsdAttribute boolAttr = prim.CreateAttribute(TfToken("boolAttr"), SdfValueTypeNames->Bool, true);

    CHECK(usdex::core::setEffectiveAttributeValue(prim, TfToken("boolAttr"), VtValue(1.0f)));
    CHECK(boolAttr.HasAuthoredValue());
    bool authoredValue = false;
    CHECK(boolAttr.Get(&authoredValue));
    CHECK(authoredValue);

    CHECK(usdex::core::setEffectiveAttributeValue(prim, TfToken("boolAttr"), VtValue(0.0f)));
    CHECK(boolAttr.HasAuthoredValue());
    CHECK(boolAttr.Get(&authoredValue));
    CHECK(!authoredValue);
}

TEST_CASE("setEffectiveAttributeValue coerces TfToken to string")
{
    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdPrim prim = usdex::core::defineScope(stage, SdfPath("/Scope")).GetPrim();
    UsdAttribute stringAttr = prim.CreateAttribute(TfToken("stringAttr"), SdfValueTypeNames->String, true);

    const bool result = usdex::core::setEffectiveAttributeValue(prim, TfToken("stringAttr"), VtValue(TfToken("hello")));
    CHECK(result);
    CHECK(stringAttr.HasAuthoredValue());

    std::string authoredValue;
    CHECK(stringAttr.Get(&authoredValue));
    CHECK(authoredValue == "hello");
}

TEST_CASE("setEffectiveAttributeValue coerces string to TfToken")
{
    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdPrim prim = usdex::core::defineScope(stage, SdfPath("/Scope")).GetPrim();
    UsdAttribute tokenAttr = prim.CreateAttribute(TfToken("tokenAttr"), SdfValueTypeNames->Token, true);

    const bool result = usdex::core::setEffectiveAttributeValue(prim, TfToken("tokenAttr"), VtValue(std::string("hello")));
    CHECK(result);
    CHECK(tokenAttr.HasAuthoredValue());

    TfToken authoredValue;
    CHECK(tokenAttr.Get(&authoredValue));
    CHECK(authoredValue == TfToken("hello"));
}
