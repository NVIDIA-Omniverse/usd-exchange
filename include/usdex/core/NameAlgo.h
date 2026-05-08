// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/core/NameAlgo.h
//! @brief Utility functions to generate valid names and display names for `UsdPrims`, and valid property names on `UsdPrims`.

#include "Api.h"

#include <pxr/base/tf/token.h>
#include <pxr/usd/sdf/path.h>
#include <pxr/usd/sdf/primSpec.h>
#include <pxr/usd/usd/prim.h>

#include <string>
#include <vector>


namespace usdex::core
{

//! @defgroup names Prim and Property Names
//!
//! Utility functions to generate valid names and display names for `UsdPrims`, and valid property names on `UsdPrims`.
//!
//! OpenUsd has [strict requirements](https://openusd.org/release/api/group__group__tf___string.html#gaa129b294af3f68d01477d430b70d40c8)
//! on what names are valid for a `UsdObject`, though the specification is evolving over time.
//!
//! Additionally the names of sibling Objects must be unique so that the `SdfPath` that identifies them is unique within the `UsdStage`.
//!
//! Most authoring functions in this library require that the names and paths supplied are valid. While it would be possible for each of these
//! functions to create valid values directly, this workflow can lead to undetected name collisions.
//!
//! The functions below can be used to produce valid `UsdObject` names for any OpenUSD runtime that we support.
//!
//! # Transcoding #
//!
//! Users of OpenUSD in non-English speaking regions and users in a variety of domains (mechanical, manufacturing, electrical, automotive, etc.)
//! often require the ability to name OpenUSD primitives with identifiers that are not allowable by the OpenUSD specification.
//!
//! The OpenUSD specification places the following limitations for object names:
//!
//! - No empty strings.
//! - Must start with characters in the set of `[A-Za-z_]`.
//! - May continue with characters in the set of `[A-Za-z0-9_]`.
//!
//! In OpenUSD 24.03 and beyond, Unicode characters are allowed, however the following limitations remain:
//!
//! - No characters that are part of the lexical structure, i.e. whitespace or newline.
//! - No characters that are part of the syntactic structure, such as arithmetic operators.
//! - No SdfPath separators, i.e. forward slash (`/`), curly brackets (`{}`), square brackets (`[]`), etc.
//! - Cannot start with numeric characters.
//!
//! Typically, [TfMakeValidIdentifier](https://openusd.org/dev/api/group__group__tf___string.html) is used to convert any identifier into a valid
//! identifier. However, it creates a non-bidirectional relationship, for example, something like `カーテンウォール` would be transformed into
//! `_______________`.
//!
//! As an alternative, the default transcoding provided with the functions bellow follows the approach outlined in the [Bi-Directional Transcoding of
//! Invalid Identifiers](https://github.com/PixarAnimationStudios/OpenUSD-proposals/tree/main/proposals/transcoding_invalid_identifiers) proposal.
//! This algorithm can transform any identifier (potentially with invalid characters) into a valid identifier, in a reversible, unique, and easily
//! identifiable manner.
//!
//! - For any legal identifier in a given runtime, this transcoding will produce no changes.
//! - For illegal identifiers, the transcoding will produce a human readable name that meets the requirements of the runtime.
//!
//! If you prefer to avoid transcoding entirely, this behaviour can be disabled via our @ref settings.
//!
//! # Prim Naming Functions #
//!
//! To ensure that a `UsdPrim` is valid use `getValidPrimName()`.
//!
//! When defining multiple prims below a common parent use `getValidChildNames()` to ensure that the names are not only valid, but also unique
//! from one another and existing children.
//!
//! When there is no existing parent, we provide `getValidPrimNames()`.
//!
//! # Property Naming Functions #
//!
//! To ensure that a `UsdProperty` name is valid, use `getValidPropertyName()`. This function differs from Prim Name encoding, as it explicitly
//! handles nested namespaces (e.g. `foo:bar:baz`) and encodes each portion of the namespace independently.
//!
//! When defining multiple properties for the same `UsdPrim`, use `getValidPropertyNames()` to ensure that the names are not only valid, but also
//! unique from one another.
//!
//! # Prim Display Name #
//!
//! Unlike names, "Display Names" support all UTF-8 encoding across all runtimes, as they are simply metadata on the Prim, and are not used to
//! uniquely identify it. You can author UTF-8 binary strings and/or characters directly in a .usda file.
//!
//! Example:
//!
//!     def Cube "cube1" (
//!         displayName = "\xF0\x9F\x9A\x80"
//!     )
//!
//!     def Cube "cube2" (
//!         displayName = "🚀"
//!     )
//!
//! We recommend setting the display name metadata in cases where the native name of an item could not be used for the associated `UsdObject`.
//! This could be because the name was invalid, or because it needed to be allocated a suffix to become unique. In either case the original value
//! can be stored as the display name.
//!
//! However, support for storing a display name on a Prim is not consistent across all versions of OpenUsd. To make this more consistent,
//! we provide functions to manipulate the display name metadata in any OpenUSD runtime.
//!
//! In OpenUSD v25.11, the `displayName` metadata field was deprecated, along with the `UsdObject::Get/SetDisplayName()` functions in favor of
//! using the `uiHints` dictionary metadata fields and UsdUIObjectHints API. The
//! [UI Hints proposal](https://openusd.org/release/api/usd_u_i_page_front.html#usdUI_hintsOverview) outlines this change in more detail.
//! Currently, the `displayName` helper functions in this library only access the original `displayName` metadata field
//! and do not read or write the new `uiHints` dictionary.
//!
//! @{

//! Produce a valid prim name from the input name
//!
//! This is a lossless encoding algorithm that supports all UTF-8 code set (even control characters).
//!
//! @param name The input name
//! @returns A string that is considered valid for use as a prim name.
USDEX_API pxr::TfToken getValidPrimName(const std::string& name);

//! Take a vector of the preferred names and return a matching vector of valid and unique names.
//!
//! @param names A vector of preferred prim names.
//! @param reservedNames A vector of reserved prim names. Names in the vector will not be included in the returns.
//! @returns A vector of valid and unique names.
USDEX_API pxr::TfTokenVector getValidPrimNames(const std::vector<std::string>& names, const pxr::TfTokenVector& reservedNames = {});

//! Take a prim and a preferred name. Return a valid and unique name as the child name of the given prim.
//!
//! @param prim The USD prim where the given prim name should live under.
//! @param name A preferred prim name.
//! @returns A valid and unique name.
USDEX_API pxr::TfToken getValidChildName(const pxr::UsdPrim& prim, const std::string& name);

//! Take a prim and a vector of the preferred names. Return a matching vector of valid and unique names as the child names of the given prim.
//!
//! @param prim The USD prim where the given prim names should live under.
//! @param names A vector of preferred prim names.
//! @returns A vector of valid and unique names.
USDEX_API pxr::TfTokenVector getValidChildNames(const pxr::UsdPrim& prim, const std::vector<std::string>& names);

//! The `NameCache` class provides a mechanism for generating unique and valid names for `UsdPrims` and their `UsdProperties`.
//!
//! The class ensures that generated names are valid according to OpenUSD name requirements and are unique within the context of sibling Prim and
//! Property names.
//!
//! The cache provides a performant alternative to repeated queries by caching generated names and managing reserved names for Prims and Properties.
//!
//! Because reserved names are held in the cache, collisions can be avoided in cases where the Prim or Property has not been authored in the Stage.
//! Names can be requested individually or in bulk, supporting a range of authoring patterns.
//! Cache entries are based on prim path and are not unique between stages or layers.
//!
//! The name cache can be used in several authoring contexts, by providing a particular `parent` type:
//! - `SdfPath`: Useful when generating names before authoring anything in USD.
//! - `UsdPrim`: Useful when authoring in a `UsdStage`.
//! - `SdfPrimSpec`: Useful when authoring in an `SdfLayer`
//!
//! When a cache entry is first created it will be populated with existing names depending on the scope of the supplied parent.
//! - Given an `SdfPath` no names will be reserved
//! - Given a `UsdPrim` it's existing child Prim and Property names (after composition) will be reserved
//! - Given an `SdfPrimSpec` it's existing child Prim and Property names (before composition) will be reserved
//!
//! The parent must be stable to be useable as a cache key.
//! - An `SdfPath` must be an absolute prim path containing no variant selections.
//! - A `UsdPrim` must be valid.
//! - An `SdfPrimSpec` must not be NULL or dormant.
//!
//! The pseudo root cannot have properties, therefore it is not useable as a parent for property related functions.
//!
//! @warning This class does not automatically invalidate cached values based on changes to the prims from which values were cached.
//! Additionally, a separate instance of this class should be used per-thread, calling methods from multiple threads is not safe.
class USDEX_API NameCache
{

public:

    NameCache();
    ~NameCache();

    //! Make a name valid and unique for use as the name of a child of the given prim.
    //!
    //! An invalid token is returned on failure.
    //!
    //! @param parent The parent path
    //! @param name Preferred name
    //! @returns Valid and unique name token
    pxr::TfToken getPrimName(const pxr::SdfPath& parent, const std::string& name);

    //! Make a name valid and unique for use as the name of a child of the given prim.
    //!
    //! An invalid token is returned on failure.
    //!
    //! @param parent The parent prim
    //! @param name Preferred name
    //! @returns Valid and unique name token
    pxr::TfToken getPrimName(const pxr::UsdPrim& parent, const std::string& name);

    //! Make a name valid and unique for use as the name of a child of the given prim.
    //!
    //! An invalid token is returned on failure.
    //!
    //! @param parent The parent prim spec
    //! @param name Preferred name
    //! @returns Valid and unique name token
    pxr::TfToken getPrimName(const pxr::SdfPrimSpecHandle parent, const std::string& name);

    //! Make a list of names valid and unique for use as the names of a children of the given prim.
    //!
    //! @param parent The parent path
    //! @param names Preferred names
    //! @returns A vector of Valid and unique name tokens ordered to match the preferred names
    pxr::TfTokenVector getPrimNames(const pxr::SdfPath& parent, const std::vector<std::string>& names);

    //! Make a list of names valid and unique for use as the names of a children of the given prim.
    //!
    //! @param parent The parent prim
    //! @param names Preferred names
    //! @returns A vector of Valid and unique name tokens ordered to match the preferred names
    pxr::TfTokenVector getPrimNames(const pxr::UsdPrim& parent, const std::vector<std::string>& names);

    //! Make a list of names valid and unique for use as the names of a children of the given prim.
    //!
    //! @param parent The parent prim spec
    //! @param names Preferred names
    //! @returns A vector of Valid and unique name tokens ordered to match the preferred names
    pxr::TfTokenVector getPrimNames(const pxr::SdfPrimSpecHandle parent, const std::vector<std::string>& names);

    //! Make a name valid and unique for use as the name of a property on the given prim.
    //!
    //! An invalid token is returned on failure.
    //!
    //! @param parent The prim path
    //! @param name Preferred name
    //! @returns Valid and unique name token
    pxr::TfToken getPropertyName(const pxr::SdfPath& parent, const std::string& name);

    //! Make a name valid and unique for use as the name of a property on the given prim.
    //!
    //! An invalid token is returned on failure.
    //!
    //! @param parent The parent prim
    //! @param name Preferred name
    //! @returns Valid and unique name token
    pxr::TfToken getPropertyName(const pxr::UsdPrim& parent, const std::string& name);

    //! Make a name valid and unique for use as the name of a property on the given prim.
    //!
    //! An invalid token is returned on failure.
    //!
    //! @param parent The parent prim spec
    //! @param name Preferred name
    //! @returns Valid and unique name token
    pxr::TfToken getPropertyName(const pxr::SdfPrimSpecHandle parent, const std::string& name);

    //! Make a list of names valid and unique for use as the names of properties on the given prim.
    //!
    //! @param parent The parent path
    //! @param names Preferred names
    //! @returns A vector of Valid and unique name tokens ordered to match the preferred names
    pxr::TfTokenVector getPropertyNames(const pxr::SdfPath& parent, const std::vector<std::string>& names);

    //! Make a list of names valid and unique for use as the names of properties on the given prim.
    //!
    //! @param parent The parent prim
    //! @param names Preferred names
    //! @returns A vector of Valid and unique name tokens ordered to match the preferred names
    pxr::TfTokenVector getPropertyNames(const pxr::UsdPrim& parent, const std::vector<std::string>& names);

    //! Make a list of names valid and unique for use as the names of properties on the given prim.
    //!
    //! @param parent The parent prim spec
    //! @param names Preferred names
    //! @returns A vector of Valid and unique name tokens ordered to match the preferred names
    pxr::TfTokenVector getPropertyNames(const pxr::SdfPrimSpecHandle parent, const std::vector<std::string>& names);

    //! Update the reserved child names for a prim to include existing children.
    //!
    //! @param parent The parent prim.
    //! @returns `void`
    void updatePrimNames(const pxr::UsdPrim& parent);

    //! Update the reserved child names for a prim to include existing children.
    //!
    //! @param parent The parent prim spec.
    //! @returns `void`
    void updatePrimNames(const pxr::SdfPrimSpecHandle parent);

    //! Update the reserved property names for a prim to include existing properties.
    //!
    //! @param parent The parent prim.
    //! @returns `void`
    void updatePropertyNames(const pxr::UsdPrim& parent);

    //! Update the reserved property names for a prim to include existing properties.
    //!
    //! @param parent The parent prim spec.
    //! @returns `void`
    void updatePropertyNames(const pxr::SdfPrimSpecHandle parent);

    //! Update the reserved child and property names for a prim to include existing children and properties.
    //!
    //! @param parent The parent prim.
    //! @returns `void`
    void update(const pxr::UsdPrim& parent);

    //! Update the reserved child and property names for a prim to include existing children and properties.
    //!
    //! @param parent The parent prim spec.
    //! @returns `void`
    void update(const pxr::SdfPrimSpecHandle parent);

    //! Clear the reserved child names for a prim.
    //!
    //! @param parent The parent prim path
    //! @returns `void`
    void clearPrimNames(const pxr::SdfPath& parent);

    //! Clear the reserved child names for a prim.
    //!
    //! @param parent The parent prim
    //! @returns `void`
    void clearPrimNames(const pxr::UsdPrim& parent);

    //! Clear the reserved child names for a prim.
    //!
    //! @param parent The parent prim spec
    //! @returns `void`
    void clearPrimNames(const pxr::SdfPrimSpecHandle parent);

    //! Clear the reserved property names for a prim.
    //!
    //! @param parent The parent prim path
    //! @returns `void`
    void clearPropertyNames(const pxr::SdfPath& parent);

    //! Clear the reserved property names for a prim.
    //!
    //! @param parent The parent prim
    //! @returns `void`
    void clearPropertyNames(const pxr::UsdPrim& parent);

    //! Clear the reserved property names for a prim.
    //!
    //! @param parent The parent prim spec
    //! @returns `void`
    void clearPropertyNames(const pxr::SdfPrimSpecHandle parent);

    //! Clear the reserved prim and property names for a prim.
    //!
    //! @param parent The parent prim path
    //! @returns `void`
    void clear(const pxr::SdfPath& parent);

    //! Clear the reserved prim and property names for a prim.
    //!
    //! @param parent The parent prim
    //! @returns `void`
    void clear(const pxr::UsdPrim& parent);

    //! Clear the reserved prim and property names for a prim.
    //!
    //! @param parent The parent prim spec
    //! @returns `void`
    void clear(const pxr::SdfPrimSpecHandle parent);

private:

    class NameCacheImpl;
    NameCacheImpl* m_impl;
};

//! A caching mechanism for valid and unique child prim names.
//!
//! For best performance, this object should be reused for multiple name requests.
//!
//! It is not valid to request child names from prims from multiple stages as only the prim path is used as the cache key.
//!
//! @warning This class does not automatically invalidate cached values based on changes to the stage from which values were cached.
//! Additionally, a separate instance of this class should be used per-thread, calling methods from multiple threads is not safe.
//! \deprecated Use the NameCache class instead
class USDEX_API ValidChildNameCache
{

public:

    USDEX_DEPRECATED("1.1", "Use the NameCache class instead")
    ValidChildNameCache();
    ~ValidChildNameCache();

    //! Take a prim and a vector of the preferred names. Return a matching vector of valid and unique names as the child names of the given prim.
    //!
    //! @param prim The USD prim where the given prim names should live under.
    //! @param names A vector of preferred prim names.
    //! @returns A vector of valid and unique names.
    pxr::TfTokenVector getValidChildNames(const pxr::UsdPrim& prim, const std::vector<std::string>& names);

    //! Take a prim and a preferred name. Return a valid and unique name for use as the child name of the given prim.
    //!
    //! @param prim The prim that the child name should be valid for.
    //! @param name Preferred prim name.
    //! @returns Valid and unique name.
    pxr::TfToken getValidChildName(const pxr::UsdPrim& prim, const std::string& name);

    //! Update the name cache for a Prim to include all existing children.
    //!
    //! This does not clear the cache, so any names that have been previously returned will still be reserved.
    //!
    //! @param prim The prim that child names should be updated for.
    //! @returns `void`
    void update(const pxr::UsdPrim& prim);

    //! Clear the name cache for a Prim.
    //!
    //! @param prim The prim that child names should be cleared for.
    //! @returns `void`
    void clear(const pxr::UsdPrim& prim);

private:

    class CacheImpl;
    CacheImpl* m_impl;
};

//! Produce a valid property name using the Bootstring algorithm.
//!
//! @param name The input name
//! @returns A string that is considered valid for use as a property name.
USDEX_API pxr::TfToken getValidPropertyName(const std::string& name);

//! Take a vector of the preferred names and return a matching vector of valid and unique names.
//!
//! @param names A vector of preferred property names.
//! @param reservedNames A vector of reserved property names. Names in the vector will not be included in the return.
//! @returns A vector of valid and unique names.
USDEX_API pxr::TfTokenVector getValidPropertyNames(const std::vector<std::string>& names, const pxr::TfTokenVector& reservedNames = {});

//! Return this prim's display name (metadata)
//!
//! @param prim The prim to get the display name from
//! @returns Authored value, or an empty string if no display name has been set
USDEX_API std::string getDisplayName(const pxr::UsdPrim& prim);

//! Sets this prim's display name (metadata).
//!
//! DisplayName is meant to be a descriptive label, not necessarily an alternate identifier; therefore there is no restriction on which characters can
//! appear in it
//!
//! @param prim The prim to set the display name for
//! @param name The value to set
//! @returns True on success, otherwise false
USDEX_API bool setDisplayName(pxr::UsdPrim prim, const std::string& name);

//! Clears this prim's display name (metadata) in the current EditTarget (only)
//!
//! @param prim The prim to clear the display name for
//! @returns True on success, otherwise false
USDEX_API bool clearDisplayName(pxr::UsdPrim prim);

//! Block this prim's display name (metadata)
//!
//! The fallback value will be explicitly authored to cause the value to resolve as if there were no authored value opinions in weaker layers
//!
//! @param prim The prim to block the display name for
//! @returns True on success, otherwise false
USDEX_API bool blockDisplayName(pxr::UsdPrim prim);

//! Calculate the effective display name of this prim
//!
//! If the display name is un-authored or empty then the prim's name is returned
//!
//! @param prim The prim to compute the display name for
//! @returns The effective display name
USDEX_API std::string computeEffectiveDisplayName(const pxr::UsdPrim& prim);

//! @}

} // namespace usdex::core
