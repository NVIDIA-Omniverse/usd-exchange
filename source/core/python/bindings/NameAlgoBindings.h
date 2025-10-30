// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/NameAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include "pxr/base/arch/pragmas.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;

namespace usdex::core::bindings
{

void bindNameAlgo(module& m)
{
    m.def(
        "getValidPrimName",
        &getValidPrimName,
        arg("name"),
        R"(
            Produce a valid prim name from the input name

            Args:
                name: The input name

            Returns:
                A string that is considered valid for use as a prim name.
        )"
    );

    m.def(
        "getValidPrimNames",
        &getValidPrimNames,
        arg("names"),
        arg("reservedNames") = list(),
        R"(
            Take a vector of the preferred names and return a matching vector of valid and unique names.

            Args:
                names: A vector of preferred prim names.
                reservedNames: A vector of reserved prim names. Names in the vector will not be included in the returns.

            Returns:
                A vector of valid and unique names.
        )"
    );

    m.def(
        "getValidChildName",
        &getValidChildName,
        arg("prim"),
        arg("name"),
        R"(
            Take a prim and a preferred name. Return a valid and unique name as the child name of the given prim.

            Args:
                prim: The USD prim where the given prim name should live under.
                names: A preferred prim name.

            Returns:
                A valid and unique name.
        )"
    );

    m.def(
        "getValidChildNames",
        &getValidChildNames,
        arg("prim"),
        arg("names"),
        R"(
            Take a prim and a vector of the preferred names. Return a matching vector of valid and unique names as the child names of the given prim.

            Args:
                prim: The USD prim where the given prim names should live under.
                names: A vector of preferred prim names.

            Returns:
                A vector of valid and unique names.
        )"
    );

    m.def(
        "getValidPropertyName",
        &getValidPropertyName,
        arg("name"),
        R"(
            Produce a valid property name using the Bootstring algorithm.

            Args:
                name: The input name

            Returns:
                A string that is considered valid for use as a property name.
        )"
    );

    m.def(
        "getValidPropertyNames",
        &getValidPropertyNames,
        arg("names"),
        arg("reservedNames") = list(),
        R"(
            Take a vector of the preferred names and return a matching vector of valid and unique names.

            Args:
                names: A vector of preferred property names.
                reservedNames: A vector of reserved prim names. Names in the vector will not be included in the return.

            Returns:
                A vector of valid and unique names.
        )"
    );

    ::class_<NameCache>(
        m,
        "NameCache",
        R"(
            The `NameCache` class provides a mechanism for generating unique and valid names for `UsdPrims` and their `UsdProperties`.

            The class ensures that generated names are valid according to OpenUSD name requirements and are unique within the context of sibling Prim and Property names.

            The cache provides a performant alternative to repeated queries by caching generated names and managing reserved names for Prims and Properties.

            Because reserved names are held in the cache, collisions can be avoided in cases where the Prim or Property has not been authored in the Stage.
            Names can be requested individually or in bulk, supporting a range of authoring patterns.
            Cache entries are based on prim path and are not unique between stages or layers.

            The name cache can be used in several authoring contexts, by providing a particular `parent` type:
            - `SdfPath`: Useful when generating names before authoring anything in USD.
            - `UsdPrim`: Useful when authoring in a `UsdStage`.
            - `SdfPrimSpec`: Useful when authoring in an `SdfLayer`

            When a cache entry is first created it will be populated with existing names depending on the scope of the supplied parent.
            - Given an `SdfPath` no names will be reserved
            - Given a `UsdPrim` it's existing child Prim and Property names (after composition) will be reserved
            - Given an `SdfPrimSpec` it's existing child Prim and Property names (before composition) will be reserved

            The parent must be stable to be useable as a cache key.
            - An `SdfPath` must be an absolute prim path containing no variant selections.
            - A `UsdPrim` must be valid.
            - An `SdfPrimSpec` must not be NULL or dormant.

            The pseudo root cannot have properties, therefore it is not useable as a parent for property related functions.

            Warning:

                This class does not automatically invalidate cached values based on changes to the prims from which values were cached.
                Additionally, a separate instance of this class should be used per-thread, calling methods from multiple threads is not safe.
        )"
    )

        .def(::init())

        .def(
            "getPrimName",
            overload_cast<const SdfPath&, const std::string&>(&NameCache::getPrimName),
            arg("parent"),
            arg("name"),
            R"(
                Make a name valid and unique for use as the name of a child of the given prim.

                An invalid token is returned on failure.

                Parameters:
                    - **parent** - The parent prim path
                    - **name** - Preferred name

                Returns:
                    Valid and unique name token
            )"
        )

        .def(
            "getPrimName",
            overload_cast<const UsdPrim&, const std::string&>(&NameCache::getPrimName),
            arg("parent"),
            arg("name"),
            R"(
                Make a name valid and unique for use as the name of a child of the given prim.

                An invalid token is returned on failure.

                Parameters:
                    - **parent** - The parent prim
                    - **name** - Preferred name

                Returns:
                    Valid and unique name token
            )"
        )

        .def(
            "getPrimName",
            overload_cast<const SdfPrimSpecHandle, const std::string&>(&NameCache::getPrimName),
            arg("parent"),
            arg("name"),
            R"(
                Make a name valid and unique for use as the name of a child of the given prim.

                An invalid token is returned on failure.

                Parameters:
                    - **parent** - The parent prim spec
                    - **name** - Preferred name

                Returns:
                    Valid and unique name token
            )"
        )

        .def(
            "getPrimNames",
            overload_cast<const SdfPath&, const std::vector<std::string>&>(&NameCache::getPrimNames),
            arg("parent"),
            arg("names"),
            R"(
                Make a list of names valid and unique for use as the names of a children of the given prim.

                Parameters:
                    - **parent** - The parent prim path
                    - **names** - Preferred names

                Returns:
                    A vector of Valid and unique name tokens ordered to match the preferred names
            )"
        )

        .def(
            "getPrimNames",
            overload_cast<const UsdPrim&, const std::vector<std::string>&>(&NameCache::getPrimNames),
            arg("parent"),
            arg("names"),
            R"(
                Make a list of names valid and unique for use as the names of a children of the given prim.

                Parameters:
                    - **parent** - The parent prim
                    - **names** - Preferred names

                Returns:
                    A vector of Valid and unique name tokens ordered to match the preferred names
            )"
        )

        .def(
            "getPrimNames",
            overload_cast<const SdfPrimSpecHandle, const std::vector<std::string>&>(&NameCache::getPrimNames),
            arg("parent"),
            arg("names"),
            R"(
                Make a list of names valid and unique for use as the names of a children of the given prim.

                Parameters:
                    - **parent** - The parent prim spec
                    - **names** - Preferred names

                Returns:
                    A vector of Valid and unique name tokens ordered to match the preferred names
            )"
        )

        .def(
            "getPropertyName",
            overload_cast<const SdfPath&, const std::string&>(&NameCache::getPropertyName),
            arg("parent"),
            arg("name"),
            R"(
                Make a name valid and unique for use as the name of a property on the given prim.

                An invalid token is returned on failure.

                Parameters:
                    - **parent** - The parent prim path
                    - **name** - Preferred name

                Returns:
                    Valid and unique name token
            )"
        )

        .def(
            "getPropertyName",
            overload_cast<const UsdPrim&, const std::string&>(&NameCache::getPropertyName),
            arg("parent"),
            arg("name"),
            R"(
                Make a name valid and unique for use as the name of a property on the given prim.

                An invalid token is returned on failure.

                Parameters:
                    - **parent** - The parent prim
                    - **name** - Preferred name

                Returns:
                    Valid and unique name token
            )"
        )

        .def(
            "getPropertyName",
            overload_cast<const SdfPrimSpecHandle, const std::string&>(&NameCache::getPropertyName),
            arg("parent"),
            arg("name"),
            R"(
                Make a name valid and unique for use as the name of a property on the given prim.

                An invalid token is returned on failure.

                Parameters:
                    - **parent** - The parent prim spec
                    - **name** - Preferred name

                Returns:
                    Valid and unique name token
            )"
        )

        .def(
            "getPropertyNames",
            overload_cast<const SdfPath&, const std::vector<std::string>&>(&NameCache::getPropertyNames),
            arg("parent"),
            arg("names"),
            R"(
                Make a list of names valid and unique for use as the names of properties on the given prim.

                Parameters:
                    - **parent** - The parent prim path
                    - **names** - Preferred names

                Returns:
                    A vector of Valid and unique name tokens ordered to match the preferred names
            )"
        )

        .def(
            "getPropertyNames",
            overload_cast<const UsdPrim&, const std::vector<std::string>&>(&NameCache::getPropertyNames),
            arg("parent"),
            arg("names"),
            R"(
                Make a list of names valid and unique for use as the names of properties on the given prim.

                Parameters:
                    - **parent** - The parent prim
                    - **names** - Preferred names

                Returns:
                    A vector of Valid and unique name tokens ordered to match the preferred names
            )"
        )

        .def(
            "getPropertyNames",
            overload_cast<const SdfPrimSpecHandle, const std::vector<std::string>&>(&NameCache::getPropertyNames),
            arg("parent"),
            arg("names"),
            R"(
                Make a list of names valid and unique for use as the names of properties on the given prim.

                Parameters:
                    - **parent** - The parent prim spec
                    - **names** - Preferred names

                Returns:
                    A vector of Valid and unique name tokens ordered to match the preferred names
            )"
        )

        .def(
            "updatePrimNames",
            overload_cast<const UsdPrim&>(&NameCache::updatePrimNames),
            arg("parent"),
            R"(
                Update the reserved child names for a prim to include existing children.

                Parameters:
                    - **parent** - The parent prim

            )"
        )

        .def(
            "updatePrimNames",
            overload_cast<const SdfPrimSpecHandle>(&NameCache::updatePrimNames),
            arg("parent"),
            R"(
                Update the reserved child names for a prim to include existing children.

                Parameters:
                    - **parent** - The parent prim

            )"
        )

        .def(
            "updatePropertyNames",
            overload_cast<const UsdPrim&>(&NameCache::updatePropertyNames),
            arg("parent"),
            R"(
                Update the reserved property names for a prim to include existing properties.

                Parameters:
                    - **parent** - The parent prim

            )"
        )

        .def(
            "updatePropertyNames",
            overload_cast<const SdfPrimSpecHandle>(&NameCache::updatePropertyNames),
            arg("parent"),
            R"(
                Update the reserved property names for a prim to include existing properties.

                Parameters:
                    - **parent** - The parent prim

            )"
        )

        .def(
            "update",
            overload_cast<const UsdPrim&>(&NameCache::update),
            arg("parent"),
            R"(
                Update the reserved child and property names for a prim to include existing children and properties.

                Parameters:
                    - **parent** - The parent prim

            )"
        )

        .def(
            "update",
            overload_cast<const SdfPrimSpecHandle>(&NameCache::update),
            arg("parent"),
            R"(
                Update the reserved child and property names for a prim to include existing children and properties.

                Parameters:
                    - **parent** - The parent prim

            )"
        )

        .def(
            "clearPrimNames",
            overload_cast<const SdfPath&>(&NameCache::clearPrimNames),
            arg("parent"),
            R"(
                Clear the reserved child names for a prim.

                Parameters:
                    - **parent** - The parent prim path

            )"
        )

        .def(
            "clearPrimNames",
            overload_cast<const UsdPrim&>(&NameCache::clearPrimNames),
            arg("parent"),
            R"(
                Clear the reserved child names for a prim.

                Parameters:
                    - **parent** - The parent prim path

            )"
        )

        .def(
            "clearPrimNames",
            overload_cast<const SdfPrimSpecHandle>(&NameCache::clearPrimNames),
            arg("parent"),
            R"(
                Clear the reserved child names for a prim.

                Parameters:
                    - **parent** - The parent prim path

            )"
        )

        .def(
            "clearPropertyNames",
            overload_cast<const SdfPath&>(&NameCache::clearPropertyNames),
            arg("parent"),
            R"(
                Clear the reserved property names for a prim.

                Parameters:
                    - **parent** - The parent prim path

            )"
        )

        .def(
            "clearPropertyNames",
            overload_cast<const UsdPrim&>(&NameCache::clearPropertyNames),
            arg("parent"),
            R"(
                Clear the reserved property names for a prim.

                Parameters:
                    - **parent** - The parent prim

            )"
        )

        .def(
            "clearPropertyNames",
            overload_cast<const SdfPrimSpecHandle>(&NameCache::clearPropertyNames),
            arg("parent"),
            R"(
                Clear the reserved property names for a prim.

                Parameters:
                    - **parent** - The parent prim spec

            )"
        )

        .def(
            "clear",
            overload_cast<const SdfPath&>(&NameCache::clear),
            arg("parent"),
            R"(
                Clear the reserved prim and property names for a prim.

                Parameters:
                    - **parent** - The parent prim path

            )"
        )

        .def(
            "clear",
            overload_cast<const UsdPrim&>(&NameCache::clear),
            arg("parent"),
            R"(
                Clear the reserved prim and property names for a prim.

                Parameters:
                    - **parent** - The parent prim

            )"
        )

        .def(
            "clear",
            overload_cast<const SdfPrimSpecHandle>(&NameCache::clear),
            arg("parent"),
            R"(
                Clear the reserved prim and property names for a prim.

                Parameters:
                    - **parent** - The parent prim spec

            )"
        );

    // FUTURE: Remove when the deprecated ValidChildNameCache class is removed
    ARCH_PRAGMA_PUSH
    ARCH_PRAGMA_DEPRECATED_POSIX_NAME

    ::class_<ValidChildNameCache>(
        m,
        "ValidChildNameCache",
        R"(
            A caching mechanism for valid and unique child prim names.

            For best performance, this object should be reused for multiple name requests.

            It is not valid to request child names from prims from multiple stages as only the prim path is used as the cache key.

            Warning:

                This class does not automatically invalidate cached values based on changes to the stage from which values were cached.
                Additionally, a separate instance of this class should be used per-thread, calling methods from multiple threads is not safe.
        )"
    )

        .def(::init())

        .def(
            "getValidChildNames",
            &ValidChildNameCache::getValidChildNames,
            arg("prim"),
            arg("names"),
            R"(
                Take a prim and a vector of the preferred names. Return a matching vector of valid and unique names as the child names of the given prim.

                Args:

                    prim: The USD prim where the given prim names should live under.
                    names: A vector of preferred prim names.

                Returns:
                    A vector of valid and unique names.
            )"
        )

        .def(
            "getValidChildName",
            &ValidChildNameCache::getValidChildName,
            arg("prim"),
            arg("name"),
            R"(

                Take a prim and a preferred name. Return a valid and unique name for use as the child name of the given prim.

                Args:
                    prim: The prim that the child name should be valid for.
                    names: Preferred prim name.

                Returns:
                    Valid and unique name.
            )"
        )

        .def(
            "update",
            &ValidChildNameCache::update,
            arg("prim"),
            R"(
            Update the name cache for a Prim to include all existing children.

            This does not clear the cache, so any names that have been previously returned will still be reserved.

            Args:
                prim: The prim that child names should be updated for.
        )"
        )

        .def(
            "clear",
            &ValidChildNameCache::clear,
            arg("clear"),
            R"(
            Clear the name cache for a Prim.

            Args:
                prim: The prim that child names should be cleared for.
        )"
        );

    // FUTURE: Remove when the deprecated ValidChildNameCache class is removed
    ARCH_PRAGMA_POP

    m.def(
        "getDisplayName",
        &getDisplayName,
        arg("prim"),
        R"(
            Return this prim's display name (metadata).

            Args:
                prim: The prim to get the display name from

            Returns:
                Authored value, or an empty string if no display name has been set.

        )"
    );
    m.def(
        "setDisplayName",
        &setDisplayName,
        arg("prim"),
        arg("name"),
        R"(
            Sets this prim's display name (metadata)

            DisplayName is meant to be a descriptive label, not necessarily an alternate identifier; therefore there is no restriction on which
            characters can appear in it

            Args:
                prim: The prim to set the display name for
                name: The value to set

            Returns:
                True on success, otherwise false

        )"
    );
    m.def(
        "clearDisplayName",
        &clearDisplayName,
        arg("prim"),
        R"(
            Clears this prim's display name (metadata) in the current EditTarget (only)

            Args:
                prim: The prim to clear the display name for

            Returns:
                True on success, otherwise false

        )"
    );
    m.def(
        "blockDisplayName",
        &blockDisplayName,
        arg("prim"),
        R"(
            Block this prim's display name (metadata)

            The fallback value will be explicitly authored to cause the value to resolve as if there were no authored value opinions in weaker layers

            Args:
                prim: The prim to block the display name for

            Returns:
                True on success, otherwise false

        )"
    );
    m.def(
        "computeEffectiveDisplayName",
        &computeEffectiveDisplayName,
        arg("prim"),
        R"(
            Calculate the effective display name of this prim

            If the display name is un-authored or empty then the prim's name is returned

            Args:
                prim: The prim to compute the display name for

            Returns:
                The effective display name

        )"
    );
}

} // namespace usdex::core::bindings
