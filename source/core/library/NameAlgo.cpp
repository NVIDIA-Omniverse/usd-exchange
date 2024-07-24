// SPDX-FileCopyrightText: Copyright (c) 2022-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#include "usdex/core/NameAlgo.h"

#include "TfUtils.h"
#include "UsdUtils.h"

#include <pxr/base/tf/stringUtils.h>
#include <pxr/usd/sdf/primSpec.h>
#include <pxr/usd/sdf/schema.h>
#include <pxr/usd/sdf/spec.h>

#include <functional>

using namespace pxr;

namespace
{

TF_DEFINE_PRIVATE_TOKENS(_tokens, (error));

struct ValidNameCache
{
    //! Names that can not be allocated
    TfTokenVector usedNames;

    // The start index to be used for making a given name unique
    std::unordered_map<std::string, size_t> startIndices;
};

void reserveNames(ValidNameCache& cache, const TfTokenVector& names)
{
    cache.usedNames.reserve(cache.usedNames.size() + names.size());
    for (const TfToken& name : names)
    {
        cache.usedNames.push_back(name);
    }
}

void reserveChildNames(ValidNameCache& cache, const UsdPrim& prim)
{
    reserveNames(cache, prim.GetAllChildrenNames());
}


TfTokenVector getValidNames(
    const std::vector<std::string>& names,
    std::function<const std::string(const std::string&)> getValidNameFunc,
    ValidNameCache& cache
)
{
    // Early exist if no names given.
    if (names.empty())
    {
        return TfTokenVector{};
    }

    // Construct an appropriately sized vector to hold resulting names
    TfTokenVector result;
    result.reserve(names.size());

    // When requesting large amounts of child paths for the same base name cache the index so that names are not considered multiple times
    std::unordered_map<std::string, size_t> startIndices;

    for (size_t nameIndex = 0; nameIndex < names.size(); ++nameIndex)
    {
        // Keep the original name
        const std::string& originalName = names[nameIndex];

        // Make the name valid before checking uniqueness
        const std::string validName = getValidNameFunc(originalName);

        // Check if the valid name is already used. Increment a numeric suffix on the original name until an available one is found
        std::string name = validName;
        while (true)
        {
            const TfToken& nameToken = TfToken(name);
            if (std::find(cache.usedNames.begin(), cache.usedNames.end(), nameToken) == cache.usedNames.end())
            {
                // Avoid allocating suffixed names that exist in the list of supplied names
                // This increases the number of cases where the requested name is returned unchanged
                if (name == validName || std::find(names.begin() + nameIndex + 1, names.end(), name) == names.end())
                {
                    result.push_back(nameToken);
                    cache.usedNames.push_back(nameToken);
                    break;
                }
            }

            // Get the latest index for this name and build a new name.
            size_t& index = cache.startIndices[originalName];

            index++;
            name = getValidNameFunc(TfStringPrintf("%s_%zu", originalName.c_str(), index));
        }
    }

    return result;
}

} // namespace

TfToken usdex::core::getValidPrimName(const std::string& name)
{
    return TfToken(usdex::core::detail::makeValidIdentifier(name));
}

TfTokenVector usdex::core::getValidPrimNames(const std::vector<std::string>& names, const TfTokenVector& reservedNames)
{
    ValidNameCache cache;
    reserveNames(cache, reservedNames);
    return getValidNames(names, usdex::core::getValidPrimName, cache);
}

TfToken usdex::core::getValidChildName(const pxr::UsdPrim& prim, const std::string& name)
{
    ValidChildNameCache cache;
    cache.update(prim);
    TfToken result = cache.getValidChildName(prim, name);
    if (result == _tokens->error)
    {
        TF_RUNTIME_ERROR(
            "Could not produce a valid child name for <%s> based on the preferred name %s",
            prim.GetPath().GetAsString().c_str(),
            name.c_str()
        );
    }
    return result;
}

TfTokenVector usdex::core::getValidChildNames(const UsdPrim& prim, const std::vector<std::string>& names)
{
    ValidNameCache cache;
    reserveChildNames(cache, prim);
    return getValidNames(names, usdex::core::getValidPrimName, cache);
}

class usdex::core::ValidChildNameCache::CacheImpl
{
public:

    CacheImpl()
    {
    }

    ~CacheImpl()
    {
    }

    TfTokenVector getValidChildNames(const UsdPrim& prim, const std::vector<std::string>& names)
    {
        auto insertIt = m_cache.insert(std::make_pair(prim.GetPath(), ValidNameCache()));

        // If the insert succeeded it is a new cache entry so we need to reserve the existing child names
        if (insertIt.second)
        {
            reserveChildNames(insertIt.first->second, prim);
        }

        return getValidNames(names, usdex::core::getValidPrimName, insertIt.first->second);
    }

    TfToken getValidChildName(const UsdPrim& prim, const std::string& name)
    {
        const std::vector<std::string> names = { name };
        const TfTokenVector validNames = getValidChildNames(prim, names);
        return validNames.size() > 0 ? validNames[0] : _tokens->error;
    }

    void update(const UsdPrim& prim)
    {
        auto insertIt = m_cache.insert(std::make_pair(prim.GetPath(), ValidNameCache()));
        reserveChildNames(insertIt.first->second, prim);
    }

    void clear(const UsdPrim& prim)
    {
        m_cache.erase(prim.GetPath());
    }

private:

    std::map<SdfPath, ValidNameCache> m_cache;
};

usdex::core::ValidChildNameCache::ValidChildNameCache() : m_impl(new CacheImpl)
{
}

usdex::core::ValidChildNameCache::~ValidChildNameCache()
{
    delete m_impl;
}

TfTokenVector usdex::core::ValidChildNameCache::getValidChildNames(const UsdPrim& prim, const std::vector<std::string>& names)
{
    return m_impl->getValidChildNames(prim, names);
}

TfToken usdex::core::ValidChildNameCache::getValidChildName(const UsdPrim& prim, const std::string& name)
{
    return m_impl->getValidChildName(prim, name);
}

void usdex::core::ValidChildNameCache::update(const UsdPrim& prim)
{
    m_impl->update(prim);
}

void usdex::core::ValidChildNameCache::clear(const UsdPrim& prim)
{
    m_impl->clear(prim);
}

TfToken usdex::core::getValidPropertyName(const std::string& name)
{
    // Split the name based on the ":" delimiter
    std::vector<std::string> tokens = TfStringSplit(name, ":");

    // Add an empty token if the original name produced no tokens.
    // This is most likely to occur if the incoming name was empty.
    if (tokens.empty())
    {
        tokens.push_back("");
    }

    // Make each token a valid identifier using bootstring encoding
    std::vector<std::string> validTokens;
    validTokens.reserve(tokens.size());
    for (const std::string& token : tokens)
    {
        validTokens.push_back(usdex::core::detail::makeValidIdentifier(token));
    }

    // Join the namespaces again using the ":" delimiter
    return TfToken(TfStringJoin(validTokens, ":"));
}

TfTokenVector usdex::core::getValidPropertyNames(const std::vector<std::string>& names, const TfTokenVector& reservedNames)
{
    ValidNameCache cache;
    reserveNames(cache, reservedNames);
    return getValidNames(names, usdex::core::getValidPropertyName, cache);
}

std::string usdex::core::getDisplayName(const UsdPrim& prim)
{
#if PXR_VERSION >= 2302
    return prim.GetDisplayName();
#else
    // This function acts as a shim as "UsdObject::GetDisplayName" is not available before OpenUsd version 23.02
    for (const auto& primSpec : prim.GetPrimStack())
    {
        const VtValue displayName = primSpec->GetField(SdfFieldKeys->DisplayName);
        if (!displayName.IsEmpty())
        {
            if (displayName.IsHolding<std::string>())
            {
                return displayName.UncheckedGet<std::string>();
            }
            return "";
        }
    }
    return "";
#endif // PXR_VERSION >= 2302
}

bool usdex::core::setDisplayName(UsdPrim prim, const std::string& name)
{
#if PXR_VERSION >= 2302
    return prim.SetDisplayName(name);
#else
    // This function acts as a shim as "UsdObject::SetDisplayName" is not available before OpenUsd version 23.02
    if (SdfPrimSpecHandle primSpec = SdfCreatePrimInLayer(prim.GetStage()->GetEditTarget().GetLayer(), prim.GetPath()))
    {
        return primSpec->SetField(SdfFieldKeys->DisplayName, name);
    }
    return false;
#endif // PXR_VERSION >= 2302
}

bool usdex::core::clearDisplayName(UsdPrim prim)
{
#if PXR_VERSION >= 2302
    return prim.ClearDisplayName();
#else
    // This function acts as a shim as "UsdObject::ClearDisplayName" is not available before OpenUsd version 23.02
    if (SdfPrimSpecHandle primSpec = prim.GetStage()->GetEditTarget().GetLayer()->GetPrimAtPath(prim.GetPath()))
    {
        return primSpec->ClearField(SdfFieldKeys->DisplayName);
    }
    return false;
#endif // PXR_VERSION >= 2302
}

bool usdex::core::blockDisplayName(UsdPrim prim)
{
    // Setting the value to the fallback value of "" will essentially block the display name.
    // Subsequent calls to `computeEffectiveDisplayName` will return the Prim name as they would in the absence of any authored display name.
    return usdex::core::setDisplayName(prim, "");
}

std::string usdex::core::computeEffectiveDisplayName(const UsdPrim& prim)
{
    // Return the display name metadata if it has a value other than an empty string
    std::string displayName = usdex::core::getDisplayName(prim);
    if (!displayName.empty())
    {
        return displayName;
    }

    // Otherwise return the prim name
    return prim.GetName().GetString();
}
