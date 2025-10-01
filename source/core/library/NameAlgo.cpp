// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/NameAlgo.h"

#include "TfUtils.h"

#include <pxr/base/tf/stringUtils.h>
#include <pxr/usd/sdf/childrenView.h>
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

// Implemented as a pass through to support template functions
void reserveChildNames(ValidNameCache&, const SdfPath&)
{
}

void reserveChildNames(ValidNameCache& cache, const UsdPrim& prim)
{
    reserveNames(cache, prim.GetAllChildrenNames());
}

void reserveChildNames(ValidNameCache& cache, const SdfPrimSpecHandle parent)
{
    TfTokenVector names;
    for (const auto& child : parent->GetNameChildren().values())
    {
        names.push_back(child->GetNameToken());
    }
    reserveNames(cache, names);
}

// Implemented as a pass through to support template functions
void reserveChildPropertyNames(ValidNameCache&, const SdfPath&)
{
}

void reserveChildPropertyNames(ValidNameCache& cache, const UsdPrim& prim)
{
    reserveNames(cache, prim.GetPropertyNames());
}

void reserveChildPropertyNames(ValidNameCache& cache, const SdfPrimSpecHandle parent)
{
    TfTokenVector names;
    for (const auto& child : parent->GetProperties().values())
    {
        names.push_back(child->GetNameToken());
    }
    reserveNames(cache, names);
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
    NameCache cache;
    cache.updatePrimNames(prim);
    TfToken result = cache.getPrimName(prim, name);
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


class usdex::core::NameCache::NameCacheImpl
{
public:

    NameCacheImpl()
    {
    }

    ~NameCacheImpl()
    {
    }

    template <class T>
    TfToken getPrimName(const T& parent, const std::string& name)
    {
        std::string reason;
        if (!isValidParent(parent, true, &reason))
        {
            TF_RUNTIME_ERROR("Unable to get prim name: %s", reason.c_str());
            return TfToken();
        }

        const TfTokenVector validNames = uncheckedGetPrimNames(parent, { name });
        return validNames.size() > 0 ? validNames[0] : TfToken();
    }

    template <class T>
    TfTokenVector getPrimNames(const T& parent, const std::vector<std::string>& names)
    {
        std::string reason;
        if (!isValidParent(parent, true, &reason))
        {
            TF_RUNTIME_ERROR("Unable to get prim names: %s", reason.c_str());
            return TfTokenVector();
        }
        return uncheckedGetPrimNames(parent, names);
    }

    template <class T>
    TfToken getPropertyName(const T& parent, const std::string& name)
    {
        std::string reason;
        if (!isValidParent(parent, false, &reason))
        {
            TF_RUNTIME_ERROR("Unable to get property name: %s", reason.c_str());
            return TfToken();
        }

        const TfTokenVector validNames = uncheckedGetPropertyNames(parent, { name });
        return validNames.size() > 0 ? validNames[0] : TfToken();
    }

    template <class T>
    TfTokenVector getPropertyNames(const T& parent, const std::vector<std::string>& names)
    {
        std::string reason;
        if (!isValidParent(parent, false, &reason))
        {
            TF_RUNTIME_ERROR("Unable to get property names: %s", reason.c_str());
            return TfTokenVector();
        }
        return uncheckedGetPropertyNames(parent, names);
    }

    template <class T>
    void updatePrimNames(const T& parent)
    {
        std::string reason;
        if (!isValidParent(parent, true, &reason))
        {
            TF_RUNTIME_ERROR("Unable to update prim names: %s", reason.c_str());
            return;
        }

        auto insertIt = m_primNameCache.insert(std::make_pair(getCacheKey(parent), ::ValidNameCache()));
        reserveChildNames(insertIt.first->second, parent);
    }

    template <class T>
    void updatePropertyNames(const T& parent)
    {
        std::string reason;
        if (!isValidParent(parent, false, &reason))
        {
            TF_RUNTIME_ERROR("Unable to update property names: %s", reason.c_str());
            return;
        }

        auto insertIt = m_propertyNameCache.insert(std::make_pair(getCacheKey(parent), ::ValidNameCache()));
        reserveChildPropertyNames(insertIt.first->second, parent);
    }

    template <class T>
    void update(const T& parent)
    {
        std::string reason;
        if (!isValidParent(parent, true, &reason))
        {
            TF_RUNTIME_ERROR("Unable to update prim and property names: %s", reason.c_str());
            return;
        }

        auto insertPrimIt = m_primNameCache.insert(std::make_pair(getCacheKey(parent), ::ValidNameCache()));
        reserveChildNames(insertPrimIt.first->second, parent);

        auto insertPropertyIt = m_propertyNameCache.insert(std::make_pair(getCacheKey(parent), ::ValidNameCache()));
        reserveChildPropertyNames(insertPropertyIt.first->second, parent);
    }

    template <class T>
    void clearPrimNames(const T& parent)
    {
        std::string reason;
        if (!isValidParent(parent, true, &reason))
        {
            TF_RUNTIME_ERROR("Unable to clear prim names: %s", reason.c_str());
            return;
        }

        m_primNameCache.erase(getCacheKey(parent));
    }

    template <class T>
    void clearPropertyNames(const T& parent)
    {
        std::string reason;
        if (!isValidParent(parent, false, &reason))
        {
            TF_RUNTIME_ERROR("Unable to clear property names: %s", reason.c_str());
            return;
        }

        m_propertyNameCache.erase(getCacheKey(parent));
    }

    template <class T>
    void clear(const T& parent)
    {
        std::string reason;
        if (!isValidParent(parent, true, &reason))
        {
            TF_RUNTIME_ERROR("Unable to clear prim and property names: %s", reason.c_str());
            return;
        }

        m_primNameCache.erase(getCacheKey(parent));
        m_propertyNameCache.erase(getCacheKey(parent));
    }

private:

    bool isValidParent(const SdfPath& parent, bool allowPseudoRoot, std::string* reason)
    {
        // The absolute root path is always valid despite not being a prim path
        if (parent.IsAbsoluteRootPath())
        {
            if (allowPseudoRoot)
            {
                return true;
            }
            else
            {
                if (reason != nullptr)
                {
                    *reason = TfStringPrintf(
                        "Parent path \"%s\" is not usable as a name cache key, must not be pseudo root.",
                        parent.GetAsString().c_str()
                    );
                }
                return false;
            }
        }

        // Only prim paths represent a stable cache key
        if (!parent.IsPrimPath())
        {
            if (reason != nullptr)
            {
                *reason = TfStringPrintf("Parent path \"%s\" is not usable as a name cache key, must be a prim path.", parent.GetAsString().c_str());
            }
            return false;
        }

        // Paths containing variant selections do not represent a stable cache key
        if (parent.ContainsPrimVariantSelection())
        {
            if (reason != nullptr)
            {
                *reason = TfStringPrintf(
                    "Parent path \"%s\" is not usable as a name cache key, must not contain variant selections.",
                    parent.GetAsString().c_str()
                );
            }
            return false;
        }

        // Relative paths do not represent a stable cache key
        if (!parent.IsAbsolutePath())
        {
            if (reason != nullptr)
            {
                *reason = TfStringPrintf("Parent path \"%s\" is not usable as a name cache key, must be absolute.", parent.GetAsString().c_str());
            }
            return false;
        }

        return true;
    }

    bool isValidParent(const UsdPrim& parent, bool allowPseudoRoot, std::string* reason)
    {
        // Invalid prims do not represent a stable cache key
        if (!parent.IsValid())
        {
            if (reason != nullptr)
            {
                *reason = "Parent prim is not usable as a name cache key. Prim must be valid.";
            }
            return false;
        }

        if (!allowPseudoRoot && parent.IsPseudoRoot())
        {
            if (reason != nullptr)
            {
                *reason = TfStringPrintf(
                    "Parent prim \"%s\" is not usable as a name cache key, must not be pseudo root.",
                    parent.GetPath().GetAsString().c_str()
                );
            }
            return false;
        }

        return true;
    }

    bool isValidParent(const SdfPrimSpecHandle parent, bool allowPseudoRoot, std::string* reason)
    {
        // Check for null pointer
        if (parent == nullptr)
        {
            if (reason != nullptr)
            {
                *reason = "Parent prim spec is not usable as a name cache key. Prim spec must not be null.";
            }
            return false;
        }

        // Invalid or expired objects do not represent a stable cache key
        if (parent->IsDormant())
        {
            if (reason != nullptr)
            {
                *reason = "Parent prim spec is not usable as a name cache key. Prim spec must be valid.";
            }
            return false;
        }

        if (!allowPseudoRoot && parent->GetPath() == SdfPath::AbsoluteRootPath())
        {
            if (reason != nullptr)
            {
                *reason = TfStringPrintf(
                    "Parent prim spec \"%s\" is not usable as a name cache key, must not be pseudo root.",
                    parent->GetPath().GetAsString().c_str()
                );
            }
            return false;
        }

        return true;
    }

    const SdfPath getCacheKey(const SdfPath& parent)
    {
        return parent;
    }

    const SdfPath getCacheKey(const UsdPrim& parent)
    {
        return parent.GetPath();
    }

    const SdfPath getCacheKey(const SdfPrimSpecHandle parent)
    {
        return parent->GetPath();
    }

    template <class T>
    TfTokenVector uncheckedGetPrimNames(const T& parent, const std::vector<std::string>& names)
    {
        auto insertIt = m_primNameCache.insert(std::make_pair(getCacheKey(parent), ::ValidNameCache()));
        if (insertIt.second)
        {
            reserveChildNames(insertIt.first->second, parent);
        }
        return getValidNames(names, usdex::core::getValidPrimName, insertIt.first->second);
    }

    template <class T>
    TfTokenVector uncheckedGetPropertyNames(const T& parent, const std::vector<std::string>& names)
    {
        auto insertIt = m_propertyNameCache.insert(std::make_pair(getCacheKey(parent), ::ValidNameCache()));
        if (insertIt.second)
        {
            reserveChildPropertyNames(insertIt.first->second, parent);
        }
        return getValidNames(names, usdex::core::getValidPropertyName, insertIt.first->second);
    }

    std::map<SdfPath, ::ValidNameCache> m_primNameCache;
    std::map<SdfPath, ::ValidNameCache> m_propertyNameCache;
};

usdex::core::NameCache::NameCache() : m_impl(new NameCacheImpl)
{
}

usdex::core::NameCache::~NameCache()
{
    delete m_impl;
}

TfToken usdex::core::NameCache::getPrimName(const SdfPath& parent, const std::string& name)
{
    return m_impl->getPrimName(parent, name);
}

TfToken usdex::core::NameCache::getPrimName(const UsdPrim& parent, const std::string& name)
{
    return m_impl->getPrimName(parent, name);
}

TfToken usdex::core::NameCache::getPrimName(const SdfPrimSpecHandle parent, const std::string& name)
{
    return m_impl->getPrimName(parent, name);
}

TfTokenVector usdex::core::NameCache::getPrimNames(const SdfPath& parent, const std::vector<std::string>& names)
{
    return m_impl->getPrimNames(parent, names);
}

TfTokenVector usdex::core::NameCache::getPrimNames(const UsdPrim& parent, const std::vector<std::string>& names)
{
    return m_impl->getPrimNames(parent, names);
}

TfTokenVector usdex::core::NameCache::getPrimNames(const SdfPrimSpecHandle parent, const std::vector<std::string>& names)
{
    return m_impl->getPrimNames(parent, names);
}

TfToken usdex::core::NameCache::getPropertyName(const SdfPath& parent, const std::string& name)
{
    return m_impl->getPropertyName(parent, name);
}

TfToken usdex::core::NameCache::getPropertyName(const UsdPrim& parent, const std::string& name)
{
    return m_impl->getPropertyName(parent, name);
}

TfToken usdex::core::NameCache::getPropertyName(const SdfPrimSpecHandle parent, const std::string& name)
{
    return m_impl->getPropertyName(parent, name);
}

TfTokenVector usdex::core::NameCache::getPropertyNames(const SdfPath& parent, const std::vector<std::string>& names)
{
    return m_impl->getPropertyNames(parent, names);
}

TfTokenVector usdex::core::NameCache::getPropertyNames(const UsdPrim& parent, const std::vector<std::string>& names)
{
    return m_impl->getPropertyNames(parent, names);
}

TfTokenVector usdex::core::NameCache::getPropertyNames(const SdfPrimSpecHandle parent, const std::vector<std::string>& names)
{
    return m_impl->getPropertyNames(parent, names);
}

void usdex::core::NameCache::updatePrimNames(const UsdPrim& parent)
{
    return m_impl->updatePrimNames(parent);
}

void usdex::core::NameCache::updatePrimNames(const SdfPrimSpecHandle parent)
{
    return m_impl->updatePrimNames(parent);
}

void usdex::core::NameCache::updatePropertyNames(const UsdPrim& parent)
{
    return m_impl->updatePropertyNames(parent);
}

void usdex::core::NameCache::updatePropertyNames(const SdfPrimSpecHandle parent)
{
    return m_impl->updatePropertyNames(parent);
}

void usdex::core::NameCache::update(const UsdPrim& parent)
{
    return m_impl->update(parent);
}

void usdex::core::NameCache::update(const SdfPrimSpecHandle parent)
{
    return m_impl->update(parent);
}

void usdex::core::NameCache::clearPrimNames(const SdfPath& parent)
{
    return m_impl->clearPrimNames(parent);
}

void usdex::core::NameCache::clearPrimNames(const UsdPrim& parent)
{
    return m_impl->clearPrimNames(parent);
}

void usdex::core::NameCache::clearPrimNames(const SdfPrimSpecHandle parent)
{
    return m_impl->clearPrimNames(parent);
}

void usdex::core::NameCache::clearPropertyNames(const SdfPath& parent)
{
    return m_impl->clearPropertyNames(parent);
}

void usdex::core::NameCache::clearPropertyNames(const UsdPrim& parent)
{
    return m_impl->clearPropertyNames(parent);
}

void usdex::core::NameCache::clearPropertyNames(const SdfPrimSpecHandle parent)
{
    return m_impl->clearPropertyNames(parent);
}

void usdex::core::NameCache::clear(const SdfPath& parent)
{
    return m_impl->clear(parent);
}

void usdex::core::NameCache::clear(const UsdPrim& parent)
{
    return m_impl->clear(parent);
}

void usdex::core::NameCache::clear(const SdfPrimSpecHandle parent)
{
    return m_impl->clear(parent);
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
