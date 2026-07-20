// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/NameAlgo.h"

#include <pxr/base/tf/diagnostic.h>
#include <pxr/base/tf/stringUtils.h>
#include <pxr/base/tf/token.h>
#include <pxr/base/vt/array.h>
#include <pxr/usd/sdf/types.h>
#include <pxr/usd/usdGeom/primvarsAPI.h>
#include <pxr/usd/usdGeom/tokens.h>

#include <map>
#include <string>

namespace usdex::core
{

template <typename T>
PrimvarData<T>::PrimvarData(const pxr::TfToken& interpolation, const pxr::VtArray<T>& values, int elementSize)
    : m_interpolation(interpolation), m_elementSize(elementSize), m_values(values)
{
}

template <typename T>
PrimvarData<T>::PrimvarData(const pxr::TfToken& interpolation, const pxr::VtArray<T>& values, const pxr::VtArray<int>& indices, int elementSize)
    : m_interpolation(interpolation), m_elementSize(elementSize), m_values(values), m_indices(indices)
{
}

template <typename T>
PrimvarData<T> PrimvarData<T>::getPrimvarData(const pxr::UsdGeomPrimvar& primvar, pxr::UsdTimeCode time)
{
    if (!primvar)
    {
        return PrimvarData<T>(pxr::UsdGeomTokens->constant, {}, -1);
    }

    int elementSize = primvar.HasAuthoredElementSize() ? primvar.GetElementSize() : -1;

    pxr::VtArray<T> values;
    if (!primvar.Get<pxr::VtArray<T>>(&values, time))
    {
        return PrimvarData<T>(pxr::UsdGeomTokens->constant, {}, -1);
    }

    if (primvar.IsIndexed())
    {
        pxr::VtIntArray indices;
        primvar.GetIndices(&indices, time);
        return PrimvarData<T>(primvar.GetInterpolation(), values, indices, elementSize);
    }
    else
    {
        return PrimvarData<T>(primvar.GetInterpolation(), values, elementSize);
    }
}

template <typename T>
bool PrimvarData<T>::setPrimvar(pxr::UsdGeomPrimvar& primvar, pxr::UsdTimeCode time) const
{
    if (!primvar)
    {
        return false;
    }

    if (!primvar.SetInterpolation(m_interpolation))
    {
        return false;
    }

    if (!primvar.Set(m_values, time))
    {
        return false;
    }

    // Author an explicit opinion about the indices to ensure weaker opinions are overriden
    if (hasIndices())
    {
        if (!primvar.SetIndices(m_indices, time))
        {
            return false;
        }
    }
    else
    {
        primvar.BlockIndices();
    }

    if (m_elementSize > 0)
    {
        primvar.SetElementSize(m_elementSize);
    }
    else if (primvar.HasAuthoredElementSize())
    {
        // if the elementSize was previously authored, we need to reset it as there is no way to block element size
        primvar.SetElementSize(1);
    }

    return true;
}

namespace detail
{

template <typename T>
pxr::SdfValueTypeName getPrimvarArrayTypeName();

template <>
inline pxr::SdfValueTypeName getPrimvarArrayTypeName<float>()
{
    return pxr::SdfValueTypeNames->FloatArray;
}

template <>
inline pxr::SdfValueTypeName getPrimvarArrayTypeName<int>()
{
    return pxr::SdfValueTypeNames->IntArray;
}

template <>
inline pxr::SdfValueTypeName getPrimvarArrayTypeName<int64_t>()
{
    return pxr::SdfValueTypeNames->Int64Array;
}

template <>
inline pxr::SdfValueTypeName getPrimvarArrayTypeName<std::string>()
{
    return pxr::SdfValueTypeNames->StringArray;
}

template <>
inline pxr::SdfValueTypeName getPrimvarArrayTypeName<pxr::TfToken>()
{
    return pxr::SdfValueTypeNames->TokenArray;
}

template <>
inline pxr::SdfValueTypeName getPrimvarArrayTypeName<pxr::GfVec2f>()
{
    return pxr::SdfValueTypeNames->TexCoord2fArray;
}

template <>
inline pxr::SdfValueTypeName getPrimvarArrayTypeName<pxr::GfVec3f>()
{
    return pxr::SdfValueTypeNames->Float3Array;
}

template <typename T>
inline bool isCompatiblePrimvarArrayType(const pxr::SdfValueTypeName& typeName)
{
    return typeName == getPrimvarArrayTypeName<T>();
}

template <>
inline bool isCompatiblePrimvarArrayType<pxr::GfVec3f>(const pxr::SdfValueTypeName& typeName)
{
    return typeName == pxr::SdfValueTypeNames->Float3Array || typeName == pxr::SdfValueTypeNames->Color3fArray ||
           typeName == pxr::SdfValueTypeNames->Normal3fArray || typeName == pxr::SdfValueTypeNames->Point3fArray ||
           typeName == pxr::SdfValueTypeNames->Color3f || typeName == pxr::SdfValueTypeNames->Normal3f || typeName == pxr::SdfValueTypeNames->Point3f;
}

template <typename T>
inline pxr::SdfValueTypeName resolvePrimvarArrayTypeName(const pxr::SdfValueTypeName& typeName)
{
    return typeName;
}

template <>
inline pxr::SdfValueTypeName resolvePrimvarArrayTypeName<pxr::GfVec3f>(const pxr::SdfValueTypeName& typeName)
{
    if (typeName == pxr::SdfValueTypeNames->Color3f)
    {
        return pxr::SdfValueTypeNames->Color3fArray;
    }
    if (typeName == pxr::SdfValueTypeNames->Normal3f)
    {
        return pxr::SdfValueTypeNames->Normal3fArray;
    }
    if (typeName == pxr::SdfValueTypeNames->Point3f)
    {
        return pxr::SdfValueTypeNames->Point3fArray;
    }
    return typeName;
}

template <typename T>
pxr::UsdGeomPrimvar createConstantPrimvarImpl(
    pxr::UsdPrim prim,
    const std::string& name,
    const T& value,
    const pxr::SdfValueTypeName& valueTypeName = pxr::SdfValueTypeName()
)
{
    PrimvarData<T> data(pxr::UsdGeomTokens->constant, pxr::VtArray<T>(1, value));
    if (!data.createPrimvar(prim, name, valueTypeName))
    {
        return pxr::UsdGeomPrimvar();
    }
    return pxr::UsdGeomPrimvarsAPI(prim).GetPrimvar(pxr::TfToken(name));
}

template <typename T>
bool setConstantPrimvarImpl(pxr::UsdPrim prim, const std::string& name, const T& value, pxr::UsdTimeCode time)
{
    std::string reason;
    if (!prim)
    {
        reason = "the prim is invalid";
    }
    else
    {
        pxr::UsdGeomPrimvar primvar = pxr::UsdGeomPrimvarsAPI(prim).GetPrimvar(pxr::TfToken(name));
        if (!primvar)
        {
            reason = pxr::TfStringPrintf("on prim <%s> the primvar does not exist", prim.GetPath().GetText());
        }
        else
        {
            PrimvarData<T> data(pxr::UsdGeomTokens->constant, pxr::VtArray<T>(1, value));
            if (data.setPrimvar(primvar, time))
            {
                return true;
            }
            reason = pxr::TfStringPrintf("on prim <%s> failed to set primvar data", prim.GetPath().GetText());
        }
    }

    // this is a TF_WARN, but we have expanded the code manually to inject the class namespaces
    pxr::Tf_PostWarningHelper(
        pxr::TfCallContext(__ARCH_FILE__, __ARCH_FUNCTION__, __LINE__, __ARCH_PRETTY_FUNCTION__),
        pxr::TF_DIAGNOSTIC_WARNING_TYPE,
        "Cannot set primvar <%s>: %s",
        name.c_str(),
        reason.c_str()
    );
    return false;
}

} // namespace detail

template <typename T>
bool PrimvarData<T>::createPrimvar(pxr::UsdPrim prim, const std::string& name, const pxr::SdfValueTypeName& valueTypeName) const
{
    std::string reason;
    if (!prim)
    {
        reason = "the prim is invalid";
    }
    else if (name.empty() || name != getValidPropertyName(name).GetString())
    {
        reason = pxr::TfStringPrintf("on prim <%s> the name is invalid", prim.GetPath().GetText());
    }
    else if (!isValid())
    {
        reason = pxr::TfStringPrintf("on prim <%s> the primvar data is invalid", prim.GetPath().GetText());
    }
    else if (valueTypeName && !detail::isCompatiblePrimvarArrayType<T>(valueTypeName))
    {
        reason = pxr::TfStringPrintf("on prim <%s> the value type is incompatible with the primvar data", prim.GetPath().GetText());
    }
    else
    {
        const pxr::TfToken validName = getValidPropertyName(name);
        const pxr::SdfValueTypeName typeName = valueTypeName ? detail::resolvePrimvarArrayTypeName<T>(valueTypeName) :
                                                               detail::getPrimvarArrayTypeName<T>();
        pxr::UsdGeomPrimvar primvar = pxr::UsdGeomPrimvarsAPI(prim).CreatePrimvar(validName, typeName, m_interpolation);
        if (!primvar)
        {
            reason = pxr::TfStringPrintf("on prim <%s> CreatePrimvar failed", prim.GetPath().GetText());
        }
        else if (!setPrimvar(primvar))
        {
            reason = pxr::TfStringPrintf("on prim <%s> failed to author primvar data", prim.GetPath().GetText());
        }
        else
        {
            return true;
        }
    }

    // this is a TF_WARN, but we have expanded the code manually to inject the class namespaces
    pxr::Tf_PostWarningHelper(
        pxr::TfCallContext(__ARCH_FILE__, __ARCH_FUNCTION__, __LINE__, __ARCH_PRETTY_FUNCTION__),
        pxr::TF_DIAGNOSTIC_WARNING_TYPE,
        "Cannot create primvar <%s>: %s",
        name.c_str(),
        reason.c_str()
    );
    return false;
}

template <typename T>
const pxr::TfToken& PrimvarData<T>::interpolation() const
{
    return m_interpolation;
}

template <typename T>
const pxr::VtArray<T>& PrimvarData<T>::values() const
{
    return m_values;
}

template <typename T>
bool PrimvarData<T>::hasIndices() const
{
    return !m_indices.empty();
}

template <typename T>
const pxr::VtArray<int>& PrimvarData<T>::indices() const
{
    if (!m_indices.empty())
    {
        return m_indices;
    }

    throw std::runtime_error("It is invalid to call indices() on PrimvarData unless hasIndices() returns true");
}

template <typename T>
int PrimvarData<T>::elementSize() const
{
    return m_elementSize;
}

template <typename T>
size_t PrimvarData<T>::effectiveSize() const
{
    if (m_elementSize > 0)
    {
        return m_indices.empty() ? m_values.size() / m_elementSize : m_indices.size() / m_elementSize;
    }
    else
    {
        return m_indices.empty() ? m_values.size() : m_indices.size();
    }
}

template <typename T>
bool PrimvarData<T>::isValid() const
{
    if (!pxr::UsdGeomPrimvar::IsValidInterpolation(m_interpolation))
    {
        return false;
    }

    if (m_values.empty())
    {
        return false;
    }

    if (m_indices.empty())
    {
        if (m_elementSize > 0 && (m_values.size() % m_elementSize))
        {
            return false;
        }
    }
    else
    {
        if (m_elementSize > 0 && (m_indices.size() % m_elementSize))
        {
            return false;
        }

        size_t maxIndex = m_values.size() - 1;
        for (const int i : indices())
        {
            if (i < 0 || (size_t)i > maxIndex)
            {
                return false;
            }
        }
    }

    return true;
}

template <typename T>
bool PrimvarData<T>::isIdentical(const PrimvarData& other) const
{
    return (
        (m_interpolation == other.interpolation()) && (m_elementSize == other.elementSize()) && (this->hasIndices() == other.hasIndices()) &&
        m_values.IsIdentical(other.values()) && m_indices.IsIdentical(other.indices())
    );
}

template <typename T>
bool PrimvarData<T>::index()
{
    // Abort indexing if the element size is greater than one
    // We do not fully understand the correct manner by which indexing should be described when element size is involved.
    if (m_elementSize > 1)
    {
        // this is a TF_RUNTIME_ERROR, but we have expanded the code manually to inject the class namespaces
        pxr::Tf_PostErrorHelper(
            pxr::TfCallContext(__ARCH_FILE__, __ARCH_FUNCTION__, __LINE__, __ARCH_PRETTY_FUNCTION__),
            pxr::TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
            "Unable to index PrimvarData due to element size greater than one"
        );
        return false;
    }

    // Compute the flattened values so that indexing can be performed on indexed or non-indexed data
    pxr::VtArray<T> flattenedValues;
    if (this->hasIndices())
    {
        flattenedValues.reserve(m_indices.size());
        for (const auto& index : m_indices)
        {
            if (size_t(index) < m_values.size())
            {
                flattenedValues.push_back(m_values[index]);
            }
            else
            {
                // Abort indexing if existing indices are outside the value range
                // this is a TF_RUNTIME_ERROR, but we have expanded the code manually to inject the class namespaces
                pxr::Tf_PostErrorHelper(
                    pxr::TfCallContext(__ARCH_FILE__, __ARCH_FUNCTION__, __LINE__, __ARCH_PRETTY_FUNCTION__),
                    pxr::TF_DIAGNOSTIC_RUNTIME_ERROR_TYPE,
                    "Unable to index PrimvarData due to existing indices outside the range of existing values"
                );
                return false;
            }
        }
    }
    else
    {
        flattenedValues = m_values;
    }

    // Compute the indices and indexed values
    pxr::VtArray<T> indexedValues;
    pxr::VtIntArray indices;
    indices.reserve(flattenedValues.size());

    std::unordered_map<size_t, int> indexMap;
    for (const auto& value : flattenedValues)
    {
        auto insertIt = indexMap.insert(std::make_pair(pxr::VtHashValue(value), static_cast<int>(indexedValues.size())));

        // If the insert succeeded it is a new value and should be added to the values array
        if (insertIt.second)
        {
            indexedValues.push_back(value);
        }

        indices.push_back(insertIt.first->second);
    }

    // Do not update the values and indices if their sizes have not changed.
    // Otherwise we are simply shuffling the data rather than actually changing the indexing.
    if (m_values.size() == indexedValues.size() && m_indices.size() == indices.size())
    {
        return false;
    }

    // Do not update the values and indices if the indices and values are the same size and the data is currently not indexed.
    // Otherwise we are authoring redundant indexing as there are no duplicate values.
    if (indexedValues.size() == indices.size() && m_indices.empty())
    {
        return false;
    }

    // Update the values and indices
    m_values = indexedValues;
    m_indices = indices;

    return true;
}

template <typename T>
bool PrimvarData<T>::hasUnindexedValues() const
{
    if (!this->hasIndices())
    {
        return false;
    }
    const size_t size = this->values().size();
    std::vector<bool> used(size, false);
    const size_t indexCount = this->indices().size();
    for (size_t i = 0; i < indexCount; ++i)
    {
        used[this->indices()[i]] = true;
    }
    for (size_t i = 0; i < used.size(); ++i)
    {
        if (!used[i])
        {
            return true;
        }
    }
    return false;
}

template <typename T>
bool PrimvarData<T>::operator==(const PrimvarData<T>& other) const
{
    return (
        (m_interpolation == other.interpolation()) && (m_elementSize == other.elementSize()) && (this->hasIndices() == other.hasIndices()) &&
        (m_values == other.values()) && (m_indices == other.indices())
    );
}

template <typename T>
bool PrimvarData<T>::operator!=(const PrimvarData<T>& other) const
{
    return !(*this == other);
}

} // namespace usdex::core
