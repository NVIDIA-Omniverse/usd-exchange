// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include <usdex/test/ScopedDiagnosticChecker.h>

#include <usdex/core/AssetStructure.h>
#include <usdex/core/PrimvarData.h>

#include <pxr/usd/sdf/types.h>
#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdGeom/scope.h>
#include <pxr/usd/usdGeom/tokens.h>

#include <doctest/doctest.h>

#include <optional>

using namespace usdex::core;
using namespace usdex::test;
using namespace pxr;

namespace
{

const TfTokenVector& interpolations()
{
    static const TfTokenVector s_interpolations = { UsdGeomTokens->vertex,
                                                    UsdGeomTokens->varying,
                                                    UsdGeomTokens->faceVarying,
                                                    UsdGeomTokens->uniform,
                                                    UsdGeomTokens->constant };
    return s_interpolations;
}

// Asserts that the PrimvarData constructor & accessors do not detach the VtArray data/indices
// The arguments are intentionally non-const to avoid masking possible detaches.
template <typename T>
void testPrimvarData(const TfToken& interpolation, VtArray<T>& values, int elementSize = -1)
{
    PrimvarData<T> primvarData(interpolation, values, elementSize);

    // access the arrays to ensure it remains attached
    CHECK(primvarData.values()[0] == *values.cbegin());

    CHECK(primvarData.interpolation() == interpolation);
    CHECK(primvarData.values().IsIdentical(values));
    CHECK(primvarData.elementSize() == elementSize);
    CHECK(primvarData.hasIndices() == false);
    CHECK_THROWS_WITH(primvarData.indices(), "It is invalid to call indices() on PrimvarData unless hasIndices() returns true");
    if (elementSize > 0)
    {
        CHECK(primvarData.effectiveSize() == values.size() / elementSize);
    }
    else
    {
        CHECK(primvarData.effectiveSize() == values.size());
    }
    CHECK(primvarData.isValid());
}

// Asserts that the PrimvarData constructor & accessors do not detach the VtArray data/indices
// The arguments are intentionally non-const to avoid masking possible detaches.
template <typename T>
void testPrimvarData(const TfToken& interpolation, VtArray<T>& values, VtIntArray& indices, int elementSize = 1)
{
    PrimvarData<T> primvarData(interpolation, values, indices, elementSize);

    // access the arrays to ensure it remains attached
    CHECK(primvarData.values()[0] == *values.cbegin());
    CHECK(primvarData.indices()[0] == *indices.cbegin());

    CHECK(primvarData.interpolation() == interpolation);
    CHECK(primvarData.values().IsIdentical(values));
    CHECK(primvarData.elementSize() == elementSize);
    CHECK(primvarData.hasIndices() == true);
    CHECK(primvarData.indices().IsIdentical(indices));
    if (elementSize > 0)
    {
        CHECK(primvarData.effectiveSize() == indices.size() / elementSize);
    }
    else
    {
        CHECK(primvarData.effectiveSize() == indices.size());
    }
    CHECK(primvarData.isValid());
}

} // namespace

TEST_CASE("PrimvarData Values")
{
    ScopedDiagnosticChecker check;

    for (const TfToken& interpolation : interpolations())
    {
        VtFloatArray floats = { -1.0, 0.5, 1.5 };
        testPrimvarData<float>(interpolation, floats);

        VtIntArray ints = { -1, 0, 1 };
        testPrimvarData<int>(interpolation, ints);

        VtInt64Array longs = { -1, 0, 1 };
        testPrimvarData<int64_t>(interpolation, longs);

        VtVec3fArray vectors = { { 0, 0, 0 }, { 0, 1, 0 }, { 0, 1, 1 } };
        testPrimvarData<GfVec3f>(interpolation, vectors);

        VtVec2fArray coords = { { 0, 0 }, { 0, 1 }, { 1, 1 } };
        testPrimvarData<GfVec2f>(interpolation, coords);

        VtStringArray strings = { "a", "foo" };
        testPrimvarData<std::string>(interpolation, strings);

        VtTokenArray tokens = { UsdGeomTokens->vertex, UsdGeomTokens->none };
        testPrimvarData<TfToken>(interpolation, tokens);
    }

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    FloatPrimvarData nullInterpolation({}, values);
    CHECK(!nullInterpolation.isValid());

    FloatPrimvarData invalidInterpolation(UsdGeomTokens->cubic, values);
    CHECK(!invalidInterpolation.isValid());
}

TEST_CASE("PrimvarData Indices")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };

    for (const TfToken& interpolation : interpolations())
    {
        testPrimvarData<float>(interpolation, values, indices);
    }

    FloatPrimvarData outOfRangeIndices(UsdGeomTokens->vertex, values, { 0, 1, 3 });
    CHECK(!outOfRangeIndices.isValid());

    FloatPrimvarData negativeIndices(UsdGeomTokens->vertex, values, { 0, -1, 2 });
    CHECK(!negativeIndices.isValid());
}

TEST_CASE("PrimvarData ElementSize")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };

    for (const TfToken& interpolation : interpolations())
    {
        // just one element
        testPrimvarData<float>(interpolation, values, 3);
        testPrimvarData<float>(interpolation, values, indices, 3);

        // no elements
        testPrimvarData<float>(interpolation, values, 0);
        testPrimvarData<float>(interpolation, values, indices, 0);
        testPrimvarData<float>(interpolation, values, -2);
        testPrimvarData<float>(interpolation, values, indices, -2);
    }

    FloatPrimvarData notEnoughValues(UsdGeomTokens->vertex, values, /* elementSize */ 4);
    CHECK(!notEnoughValues.isValid());

    FloatPrimvarData notEnoughIndices(UsdGeomTokens->vertex, values, indices, /* elementSize */ 2);
    CHECK(!notEnoughIndices.isValid());

    FloatPrimvarData wrongNumberOfValues(UsdGeomTokens->vertex, values, /* elementSize */ 2);
    CHECK(!wrongNumberOfValues.isValid());

    FloatPrimvarData wrongNumberOfIndices(UsdGeomTokens->vertex, values, indices, /* elementSize */ 2);
    CHECK(!wrongNumberOfValues.isValid());
}

TEST_CASE("PrimvarData IsIdentical")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };
    FloatPrimvarData a(UsdGeomTokens->vertex, values, indices);
    CHECK(a.values().IsIdentical(values));
    CHECK(a.indices().IsIdentical(indices));

    // identical
    FloatPrimvarData b = a;
    CHECK(b.isIdentical(a));
    CHECK(a.isIdentical(b));
    // access the arrays to ensure it remains attached
    CHECK(a.values()[0] == b.values()[0]);
    CHECK(a.indices()[0] == b.indices()[0]);
    CHECK(a.isIdentical(b));

    // different but equal data array
    VtFloatArray values2 = { -1.0, 0.5, 1.5 };
    FloatPrimvarData c(UsdGeomTokens->vertex, values2, indices);
    CHECK(!c.isIdentical(a));
    CHECK(!a.isIdentical(c));

    // different but equal indices array
    VtIntArray indices2 = { 0, 1, 2 };
    FloatPrimvarData d(UsdGeomTokens->vertex, values, indices2);
    CHECK(!d.isIdentical(a));
    CHECK(!a.isIdentical(d));
}

TEST_CASE("PrimvarData Equality")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };
    FloatPrimvarData a(UsdGeomTokens->vertex, values, indices);
    CHECK(a.values().IsIdentical(values));
    CHECK(a.indices().IsIdentical(indices));

    // identical
    FloatPrimvarData b = a;
    CHECK(b.values().IsIdentical(values));
    CHECK(b.indices().IsIdentical(indices));
    CHECK(b.values().IsIdentical(a.values()));
    CHECK(b.indices().IsIdentical(a.indices()));
    CHECK(a == b);

    // different but equal data array
    VtFloatArray values2 = { -1.0, 0.5, 1.5 };
    FloatPrimvarData c(UsdGeomTokens->vertex, values2, indices);
    CHECK(!c.values().IsIdentical(a.values()));
    CHECK(c.indices().IsIdentical(a.indices()));
    CHECK(a == c);

    // different but equal indices array
    VtIntArray indices2 = { 0, 1, 2 };
    FloatPrimvarData d(UsdGeomTokens->vertex, values, indices2);
    CHECK(d.values().IsIdentical(a.values()));
    CHECK(!d.indices().IsIdentical(a.indices()));
    CHECK(a == d);
}

TEST_CASE("PrimvarData Inequality")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };
    FloatPrimvarData original(UsdGeomTokens->vertex, values, indices);

    // different interpolation
    FloatPrimvarData diffInterpolation(UsdGeomTokens->varying, values, indices);
    CHECK(original != diffInterpolation);

    // no indices
    FloatPrimvarData noIndices(UsdGeomTokens->vertex, values);
    CHECK(original != noIndices);

    // different data array
    VtFloatArray values2 = { -1.0, 0.5, 1.5, 2.0 };
    FloatPrimvarData diffValues(UsdGeomTokens->vertex, values2, indices);
    CHECK(original != diffValues);

    // different indices array
    VtIntArray indices2 = { 2, 1, 0 };
    FloatPrimvarData diffIndices(UsdGeomTokens->vertex, values, indices2);
    CHECK(original != diffIndices);

    // different elementSize
    FloatPrimvarData diffElemSize(UsdGeomTokens->vertex, values, indices, 3);
    CHECK(original != diffElemSize);
}

TEST_CASE("PrimvarData Copy Constructor")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };
    FloatPrimvarData a(UsdGeomTokens->vertex, values, indices);
    CHECK(a.values().IsIdentical(values));
    CHECK(a.indices().IsIdentical(indices));

    FloatPrimvarData b(a);
    CHECK(b.values().IsIdentical(values));
    CHECK(b.indices().IsIdentical(indices));
    CHECK(b.values().IsIdentical(a.values()));
    CHECK(b.indices().IsIdentical(a.indices()));
    CHECK(a == b);
}

TEST_CASE("PrimvarData in optionals do not detach")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };
    std::optional<FloatPrimvarData> optional = FloatPrimvarData(UsdGeomTokens->vertex, values, indices);
    CHECK(optional.has_value());
    CHECK(optional.value().values().IsIdentical(values));
    CHECK(optional.value().indices().IsIdentical(indices));

    // access the arrays to ensure it remains attached
    CHECK(optional.value().values()[0] == -1.0);
    CHECK(optional.value().indices()[0] == 0);
    CHECK(optional.value().values().IsIdentical(values));
    CHECK(optional.value().indices().IsIdentical(indices));
}

TEST_CASE("PrimvarData Moves")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };
    FloatPrimvarData a(UsdGeomTokens->vertex, values, indices);
    CHECK(a.values().IsIdentical(values));
    CHECK(a.indices().IsIdentical(indices));

    FloatPrimvarData b = std::move(a);
    CHECK(b.values().IsIdentical(values));
    CHECK(b.indices().IsIdentical(indices));
    CHECK(a.values().empty());
    CHECK(!a.hasIndices());

    std::optional<const FloatPrimvarData> c = std::move(b);
    CHECK(c.has_value());
    CHECK(c.value().values().IsIdentical(values));
    CHECK(c.value().indices().IsIdentical(indices));
    CHECK(b.values().empty());
    CHECK(!b.hasIndices());

    std::optional<const FloatPrimvarData> d = std::exchange(c, std::nullopt);
    CHECK(d.has_value());
    CHECK(d.value().values().IsIdentical(values));
    CHECK(d.value().indices().IsIdentical(indices));
    CHECK(!c.has_value());
}

TEST_CASE("PrimvarData getPrimvarData")
{
    ScopedDiagnosticChecker check;

    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    SdfPath path("/Prim");
    UsdGeomScope scope = UsdGeomScope::Define(stage, path);
    UsdGeomPrimvarsAPI primvarsApi(scope.GetPrim());
    CHECK(primvarsApi);

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };

    UsdGeomPrimvar flatPrimvar = primvarsApi.CreateNonIndexedPrimvar<VtFloatArray>(
        TfToken("flat"),
        SdfValueTypeNames->FloatArray,
        values,
        UsdGeomTokens->vertex
    );
    FloatPrimvarData flatData = FloatPrimvarData::getPrimvarData(flatPrimvar);
    CHECK(flatData.interpolation() == UsdGeomTokens->vertex);
    CHECK(flatData.values().IsIdentical(values));
    CHECK(flatData.elementSize() == -1);
    CHECK(flatData.isValid());

    UsdGeomPrimvar elementsPrimvar = primvarsApi.CreateNonIndexedPrimvar<VtFloatArray>(
        TfToken("flatElements"),
        SdfValueTypeNames->FloatArray,
        values,
        UsdGeomTokens->vertex,
        3
    );
    FloatPrimvarData elementsData = FloatPrimvarData::getPrimvarData(elementsPrimvar);
    CHECK(elementsData.interpolation() == UsdGeomTokens->vertex);
    CHECK(elementsData.values().IsIdentical(values));
    CHECK(elementsData.elementSize() == 3);
    CHECK(elementsData.isValid());

    UsdGeomPrimvar indexedPrimvar = primvarsApi.CreateIndexedPrimvar<VtFloatArray>(
        TfToken("indexed"),
        SdfValueTypeNames->FloatArray,
        values,
        indices,
        UsdGeomTokens->vertex
    );
    FloatPrimvarData indexedData = FloatPrimvarData::getPrimvarData(indexedPrimvar);
    CHECK(indexedData.interpolation() == UsdGeomTokens->vertex);
    CHECK(indexedData.values().IsIdentical(values));
    CHECK(indexedData.indices().IsIdentical(indices));
    CHECK(indexedData.elementSize() == -1);
    CHECK(indexedData.isValid());

    UsdGeomPrimvar indexedElementsPrimvar = primvarsApi.CreateIndexedPrimvar<VtFloatArray>(
        TfToken("indexedElemets"),
        SdfValueTypeNames->FloatArray,
        values,
        indices,
        UsdGeomTokens->vertex,
        3
    );
    FloatPrimvarData indexedElementsData = FloatPrimvarData::getPrimvarData(indexedElementsPrimvar);
    CHECK(indexedElementsData.interpolation() == UsdGeomTokens->vertex);
    CHECK(indexedElementsData.values().IsIdentical(values));
    CHECK(indexedElementsData.indices().IsIdentical(indices));
    CHECK(indexedElementsData.elementSize() == 3);
    CHECK(indexedElementsData.isValid());

    UsdAttribute attr = scope.GetPrim().CreateAttribute(TfToken("notPrimvar"), SdfValueTypeNames->FloatArray);
    UsdGeomPrimvar notPrimvar(attr);
    CHECK(!notPrimvar);
    FloatPrimvarData badData = FloatPrimvarData::getPrimvarData(notPrimvar);
    CHECK(badData.interpolation() == UsdGeomTokens->constant);
    CHECK(badData.values() == VtFloatArray());
    CHECK(badData.elementSize() == -1);
    CHECK(!badData.isValid());

    VtFloatArray emptyValues;
    UsdGeomPrimvar emptyPrimvar = primvarsApi.CreateNonIndexedPrimvar<VtFloatArray>(
        TfToken("empty"),
        SdfValueTypeNames->FloatArray,
        emptyValues,
        UsdGeomTokens->vertex
    );
    FloatPrimvarData emptyData = FloatPrimvarData::getPrimvarData(emptyPrimvar);
    CHECK(emptyData.interpolation() == UsdGeomTokens->vertex);
    CHECK(emptyData.values().IsIdentical(emptyValues));
    CHECK(emptyData.elementSize() == -1);
    CHECK(!emptyData.isValid());

    IntPrimvarData wrongData = IntPrimvarData::getPrimvarData(flatPrimvar); // flatPrimvar contains float data not int data
    CHECK(wrongData.interpolation() == UsdGeomTokens->constant);
    CHECK(wrongData.values() == VtIntArray());
    CHECK(wrongData.elementSize() == -1);
    CHECK(!wrongData.isValid());
}

TEST_CASE("PrimvarData setPrimvar")
{
    ScopedDiagnosticChecker check;

    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    SdfPath path("/Prim");
    UsdGeomScope scope = UsdGeomScope::Define(stage, path);
    UsdGeomPrimvarsAPI primvarsApi(scope.GetPrim());
    CHECK(primvarsApi);

    UsdGeomPrimvar primvar = primvarsApi.CreatePrimvar(TfToken("flat"), SdfValueTypeNames->FloatArray, UsdGeomTokens->vertex);
    CHECK(primvar);

    VtFloatArray values = { -1.0, 0.5, 1.5 };
    VtIntArray indices = { 0, 1, 2 };

    FloatPrimvarData flatData = FloatPrimvarData(UsdGeomTokens->uniform, values);
    CHECK(flatData.setPrimvar(primvar));
    CHECK(primvar.GetInterpolation() == flatData.interpolation());
    VtFloatArray authoredValues;
    primvar.Get(&authoredValues);
    CHECK(authoredValues.IsIdentical(flatData.values()));
    CHECK(!primvar.IsIndexed());
    CHECK(!primvar.HasAuthoredElementSize());

    FloatPrimvarData indexedData = FloatPrimvarData(UsdGeomTokens->vertex, values, indices);
    CHECK(indexedData.setPrimvar(primvar));
    CHECK(primvar.GetInterpolation() == indexedData.interpolation());
    primvar.Get(&authoredValues);
    CHECK(authoredValues.IsIdentical(indexedData.values()));
    CHECK(primvar.IsIndexed());
    VtIntArray authoredIndices;
    primvar.GetIndices(&authoredIndices);
    CHECK(authoredIndices.IsIdentical(indexedData.indices()));
    CHECK(!primvar.HasAuthoredElementSize());

    FloatPrimvarData indexedElementsData = FloatPrimvarData(UsdGeomTokens->uniform, values, indices, 3);
    CHECK(indexedElementsData.setPrimvar(primvar));
    CHECK(primvar.GetInterpolation() == indexedElementsData.interpolation());
    primvar.Get(&authoredValues);
    CHECK(authoredValues.IsIdentical(indexedElementsData.values()));
    CHECK(primvar.IsIndexed());
    primvar.GetIndices(&authoredIndices);
    CHECK(authoredIndices.IsIdentical(indexedElementsData.indices()));
    CHECK(primvar.HasAuthoredElementSize());
    CHECK(primvar.GetElementSize() == indexedElementsData.elementSize());

    // now that the primvar has authored indices, setting from data without indices will block the indices
    CHECK(flatData.setPrimvar(primvar));
    CHECK(primvar.GetInterpolation() == flatData.interpolation());
    primvar.Get(&authoredValues);
    CHECK(authoredValues.IsIdentical(flatData.values()));
    CHECK(!primvar.IsIndexed());
    // we cannot block element size but it should be reset
    CHECK(primvar.HasAuthoredElementSize());
    CHECK(primvar.GetElementSize() != flatData.elementSize());
    CHECK(primvar.GetElementSize() == 1);

    UsdAttribute attr = scope.GetPrim().CreateAttribute(TfToken("notPrimvar"), SdfValueTypeNames->FloatArray);
    UsdGeomPrimvar notPrimvar(attr);
    CHECK(!notPrimvar);
    CHECK(!flatData.setPrimvar(notPrimvar));

    FloatPrimvarData badInterpolation = FloatPrimvarData(UsdGeomTokens->cubic, values);
    {
        ScopedDiagnosticChecker checkErrors({ { TF_DIAGNOSTIC_CODING_ERROR_TYPE, "Attempt to set invalid primvar interpolation \"cubic\".*" } });
        CHECK(!badInterpolation.setPrimvar(primvar));
    }

    IntPrimvarData wrongDataType = IntPrimvarData(UsdGeomTokens->vertex, indices);
    {
        ScopedDiagnosticChecker checkErrors({ { TF_DIAGNOSTIC_CODING_ERROR_TYPE, ".*expected 'VtArray<float>', got 'VtArray<int>'.*" } });
        CHECK(!wrongDataType.setPrimvar(primvar)); // the primvar requires FloatArray values
    }
}

TEST_CASE("PrimvarData Time Samples")
{
    ScopedDiagnosticChecker check;

    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    SdfPath path("/Prim");
    UsdGeomScope scope = UsdGeomScope::Define(stage, path);
    UsdGeomPrimvarsAPI primvarsApi(scope.GetPrim());
    CHECK(primvarsApi);

    UsdGeomPrimvar primvar = primvarsApi.CreatePrimvar(TfToken("sampled"), SdfValueTypeNames->FloatArray, UsdGeomTokens->vertex);
    CHECK(primvar);

    VtIntArray indices = { 0, 1, 2 };
    std::vector<double> times = { UsdTimeCode::EarliestTime().GetValue(), 0, 0.25, 1, 10.5 };

    // write several samples
    for (double time : times)
    {
        VtFloatArray values = { (float)time - 1.0f, (float)time, (float)time + 1.5f };
        FloatPrimvarData sample = FloatPrimvarData(UsdGeomTokens->vertex, values, indices);
        CHECK(sample.setPrimvar(primvar, time));
        CHECK(primvar.GetInterpolation() == sample.interpolation());
        VtFloatArray authoredValues;
        primvar.Get(&authoredValues, time);
        CHECK(authoredValues.IsIdentical(sample.values()));
        CHECK(primvar.IsIndexed());
        VtIntArray authoredIndices;
        primvar.GetIndices(&authoredIndices, time);
        CHECK(authoredIndices.IsIdentical(sample.indices()));
        CHECK(!primvar.HasAuthoredElementSize());
    }

    // read the samples back
    for (double time : times)
    {
        FloatPrimvarData sample = FloatPrimvarData::getPrimvarData(primvar, time);
        CHECK(sample.interpolation() == primvar.GetInterpolation());
        VtFloatArray authoredValues;
        primvar.Get(&authoredValues, time);
        CHECK(sample.values().IsIdentical(authoredValues));
        CHECK(sample.hasIndices());
        VtIntArray authoredIndices;
        primvar.GetIndices(&authoredIndices, time);
        CHECK(sample.indices().IsIdentical(authoredIndices));
        CHECK(sample.elementSize() == -1);
    }
}

TEST_CASE("PrimvarData hasUnindexedValues")
{
    ScopedDiagnosticChecker check;

    VtFloatArray values = { 0.0f, 1.0f, 2.0f };
    VtIntArray indices = { 0, 1, 2 };

    // Non-indexed primvar data
    FloatPrimvarData nonIndexedData(UsdGeomTokens->vertex, values);
    CHECK(!nonIndexedData.hasUnindexedValues());

    // Indexed primvar data
    FloatPrimvarData indexedData(UsdGeomTokens->vertex, values, indices);
    CHECK(!indexedData.hasUnindexedValues());

    // Indexed primvar data with unused values
    VtIntArray floatUnusedIndices = { 0, 1, 1 };
    FloatPrimvarData floatIndexedWithUnused(UsdGeomTokens->vertex, values, floatUnusedIndices);
    CHECK(floatIndexedWithUnused.hasUnindexedValues());

    // Non-indexed primvar data (GfVec3f)
    VtVec3fArray vec3Values = { GfVec3f(0.0f, 0.0f, 0.0f), GfVec3f(1.0f, 1.0f, 1.0f), GfVec3f(2.0f, 2.0f, 2.0f) };
    Vec3fPrimvarData vec3NonIndexed(UsdGeomTokens->vertex, vec3Values);
    CHECK(!vec3NonIndexed.hasUnindexedValues());

    // Indexed primvar data (GfVec3f)
    Vec3fPrimvarData vec3Indexed(UsdGeomTokens->vertex, vec3Values, indices);
    CHECK(!vec3Indexed.hasUnindexedValues());

    // Indexed primvar data with unused values (GfVec3f)
    VtIntArray vec3UnusedIndices = { 0, 2, 2 };
    Vec3fPrimvarData vec3IndexedWithUnused(UsdGeomTokens->vertex, vec3Values, vec3UnusedIndices);
    CHECK(vec3IndexedWithUnused.hasUnindexedValues());
}

TEST_CASE("PrimvarData createPrimvar scalar TfToken success")
{
    ScopedDiagnosticChecker check;

    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdGeomScope scope = usdex::core::defineScope(stage, SdfPath("/Scope"));
    CHECK(scope);
    UsdPrim prim = scope.GetPrim();

    const TfToken value("item1");
    TokenPrimvarData data(UsdGeomTokens->constant, VtTokenArray({ value }));
    CHECK(data.createPrimvar(prim, "tokenAttr"));
    CHECK(data.isValid());
    CHECK(data.interpolation() == UsdGeomTokens->constant);
    CHECK(data.values() == VtTokenArray({ value }));

    UsdGeomPrimvarsAPI primvarsApi(prim);
    UsdGeomPrimvar primvar = primvarsApi.GetPrimvar(TfToken("tokenAttr"));
    CHECK(primvar);
    CHECK(primvar.GetTypeName() == SdfValueTypeNames->TokenArray);
    CHECK(primvar.GetInterpolation() == UsdGeomTokens->constant);
    VtTokenArray authoredValues;
    primvar.Get(&authoredValues);
    CHECK(authoredValues == data.values());
}

TEST_CASE("PrimvarData createPrimvar scalar TfToken failure")
{
    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdGeomScope scope = usdex::core::defineScope(stage, SdfPath("/Scope"));
    CHECK(scope);
    UsdPrim prim = scope.GetPrim();

    ScopedDiagnosticChecker check({ { TF_DIAGNOSTIC_WARNING_TYPE, ".*Cannot create primvar.*name is invalid.*" } });
    TokenPrimvarData data(UsdGeomTokens->constant, VtTokenArray({ TfToken("item1") }));
    CHECK(!data.createPrimvar(prim, ""));
    CHECK(data.isValid());
}

TEST_CASE("createConstantPrimvar TfToken")
{
    ScopedDiagnosticChecker check;

    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdGeomScope scope = usdex::core::defineScope(stage, SdfPath("/Scope"));
    CHECK(scope);
    UsdPrim prim = scope.GetPrim();

    const TfToken value("item1");
    UsdGeomPrimvar primvar = createConstantPrimvar(prim, "tokenAttr", value);
    CHECK(primvar);
    CHECK(primvar.GetTypeName() == SdfValueTypeNames->TokenArray);
    CHECK(primvar.GetInterpolation() == UsdGeomTokens->constant);
    VtTokenArray authoredValues;
    primvar.Get(&authoredValues);
    CHECK(authoredValues == VtTokenArray({ value }));
}

TEST_CASE("setConstantPrimvar TfToken")
{
    ScopedDiagnosticChecker check;

    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdGeomScope scope = usdex::core::defineScope(stage, SdfPath("/Scope"));
    CHECK(scope);
    UsdPrim prim = scope.GetPrim();

    // Create a constant primvar with an initial value
    const TfToken initial("item1");
    UsdGeomPrimvar primvar = createConstantPrimvar(prim, "tokenAttr", initial);
    CHECK(primvar);
    CHECK(primvar.GetTypeName() == SdfValueTypeNames->TokenArray);

    // Update the primvar with a new value
    const TfToken updated("item2");
    CHECK(setConstantPrimvar(prim, "tokenAttr", updated));

    // Verify the updated value
    VtTokenArray authoredValues;
    primvar.Get(&authoredValues);
    CHECK(authoredValues == VtTokenArray({ updated }));
    CHECK(primvar.GetInterpolation() == UsdGeomTokens->constant);
}
