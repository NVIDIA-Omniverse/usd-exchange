// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/AssetStructure.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

namespace usdex::core::bindings
{

void bindAssetStructure(module& m)
{
    // The bindings for createAssetPayload and addAssetContent are hand rolled in `python/bindings/_AssetStructureBindings.py` due to issues with
    // cleanly passing ownership of a UsdStageRefPtr from C++ to Python using pybind11

    m.def(
        "defineScope",
        overload_cast<UsdStagePtr, const SdfPath&>(&defineScope),
        arg("stage"),
        arg("path"),
        R"(
            Defines a scope on the stage.

            A scope is a simple grouping primitive that is useful for organizing prims in a scene.

            Parameters:
                - **stage** - The stage on which to define the scope
                - **path** - The absolute prim path at which to define the scope

            Returns:
                A ``UsdGeom.Scope`` schema wrapping the defined ``Usd.Prim``. Returns an invalid schema on error.

        )"
    );

    m.def(
        "defineScope",
        overload_cast<UsdPrim, const std::string&>(&defineScope),
        arg("parent"),
        arg("name"),
        R"(
            Defines a scope on the stage.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the scope
                - **name** - Name of the scope

            Returns:
                A ``UsdGeom.Scope`` schema wrapping the defined ``Usd.Prim``. Returns an invalid schema on error.

        )"
    );

    m.def(
        "defineScope",
        overload_cast<UsdPrim>(&defineScope),
        arg("prim"),
        R"(
            Defines a scope from an existing prim.

            This converts an existing prim to a Scope type.

            Parameters:
                - **prim** - The existing prim to convert to a scope

            Returns:
                A ``UsdGeom.Scope`` schema wrapping the defined ``Usd.Prim``. Returns an invalid schema on error.

        )"
    );

    m.def(
        "configureComponentHierarchy",
        &configureComponentHierarchy,
        arg("prim"),
        R"(
            Configure a prim and its descendants to establish a proper asset component hierarchy.

            Sets the kind of the prim to "component" and adjusts the kinds of all descendant prims to maintain
            a valid USD model hierarchy. Any descendant prim that currently has the kind "component" will be
            changed to "subcomponent". Any descendant prim that has an authored kind other than "component"
            or "subcomponent" will have its kind cleared (set to an empty token).

            If a prim has no authored kind, it will be set to "group" if it has descendant model prims.

            This function is commonly used when configuring asset interfaces to ensure the model hierarchy
            follows USD best practices for components.

            Args:
                prim: The prim to configure as a component. This prim and all its descendants will be processed.

            Returns:
                True if the component hierarchy was successfully configured, false otherwise.

        )"
    );

    m.def(
        "configureAssemblyHierarchy",
        &configureAssemblyHierarchy,
        arg("prim"),
        R"(
            Configure a prim and its descendants to establish a proper asset assembly hierarchy.

            Sets the kind of the prim to "assembly" and adjusts the kinds of all descendant prims to maintain
            a valid USD model hierarchy. Any descendant prim with an invalid kind will be changed to "group".
            Descendant prims with "component" kind are left unchanged to preserve the component hierarchy.

            This function is commonly used when configuring complex assets that contain multiple components
            to ensure the model hierarchy follows USD best practices for assemblies.

            Args:
                prim: The prim to configure as an assembly. This prim and all its descendants will be processed.

            Returns:
                True if the assembly hierarchy was successfully configured, false otherwise.

        )"
    );

    m.def(
        "addAssetInterface",
        &addAssetInterface,
        arg("stage"),
        arg("source"),
        R"(
            Add an Asset Interface to a stage, which payloads a source stage's contents.

            This function creates a payload to the source stage's contents as the default prim on the stage.

            It (re)configures the stage with the source stage's metadata, payloads the defaultPrim from the source stage, and annotates the Asset
            Interface with USD model metadata including component kind, asset name, and extents hint.

            Args:
                stage: The stage's edit target will become the Asset Interface
                source: The stage that the Asset Interface will target as a Payload

            Returns:
                True if the Asset Interface was added successfully, false otherwise.

        )"
    );

    m.def(
        "getAssetToken",
        &getAssetToken,
        R"(
            Get the Asset token.

            Returns:
                The Asset token.

        )"
    );

    m.def(
        "getContentsToken",
        &getContentsToken,
        R"(
            Get the token for the Contents layer.

            Returns:
                The token for the Contents layer.

        )"
    );

    m.def(
        "getGeometryToken",
        &getGeometryToken,
        R"(
            Get the token for the Geometry layer and scope.

            Returns:
                The token for the Geometry layer and scope.

        )"
    );

    m.def(
        "getLibraryToken",
        &getLibraryToken,
        R"(
            Get the token for the Library layer.

            Returns:
                The token for the Library layer.

        )"
    );

    m.def(
        "getMaterialsToken",
        &getMaterialsToken,
        R"(
            Get the token for the Materials layer and scope.

            Returns:
                The token for the Materials layer and scope.

        )"
    );

    m.def(
        "getPayloadToken",
        &getPayloadToken,
        R"(
            Get the token for the Payload directory.

            Returns:
                The token for the Payload directory.

        )"
    );

    m.def(
        "getPhysicsToken",
        &getPhysicsToken,
        R"(
            Get the token for the Physics layer and scope.

            Returns:
                The token for the Physics layer and scope.

        )"
    );

    m.def(
        "getTexturesToken",
        &getTexturesToken,
        R"(
            Get the token for the Textures directory.

            Returns:
                The token for the Textures directory.

        )"
    );

    m.def(
        "defineReference",
        overload_cast<UsdStagePtr, const SdfPath&, const UsdPrim&>(&defineReference),
        arg("stage"),
        arg("path"),
        arg("source"),
        R"(
            Define a reference to a prim.

            This creates a reference prim that targets a prim in another layer (external reference) or the same layer (internal reference).

            The reference's assetPath will be set to the relative identifier between the stage's edit target and the source's stage if it's
            an external reference with a valid relative path.

            For more information, see:
                - https://openusd.org/release/glossary.html#usdglossary-references
                - https://openusd.org/release/api/class_usd_references.html#details

            Parameters:
                - **stage** - The stage on which to define the reference
                - **path** - The absolute prim path at which to define the reference
                - **source** - The prim to reference

            Returns:
                The newly created reference prim. Returns an invalid prim on error.

        )"
    );

    m.def(
        "defineReference",
        overload_cast<UsdPrim, const UsdPrim&, std::optional<std::string_view>>(&defineReference),
        arg("parent"),
        arg("source"),
        arg("name") = nullptr,
        R"(
            Define a reference to a prim as a child of the ``parent`` prim

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - The parent prim to add the reference to
                - **source** - The prim to reference
                - **name** - The name of the reference. If not provided, uses the source prim's name

            Returns:
                The newly created reference prim. Returns an invalid prim on error.

        )"
    );

    m.def(
        "definePayload",
        overload_cast<UsdStagePtr, const SdfPath&, const UsdPrim&>(&definePayload),
        arg("stage"),
        arg("path"),
        arg("source"),
        R"(
            Define a payload to a prim.

            This creates a payload prim that targets a prim in another layer (external payload) or the same layer (internal payload).

            The payload's assetPath will be set to the relative identifier between the stage's edit target and the source's stage if it's
            an external payload with a valid relative path.

            For more information, see:
                - https://openusd.org/release/glossary.html#usdglossary-payload
                - https://openusd.org/release/api/class_usd_payloads.html#details

            Parameters:
                - **stage** - The stage on which to define the payload
                - **path** - The absolute prim path at which to define the payload
                - **source** - The payload to add

            Returns:
                The newly created payload prim. Returns an invalid prim on error.

        )"
    );

    m.def(
        "definePayload",
        overload_cast<UsdPrim, const UsdPrim&, std::optional<std::string_view>>(&definePayload),
        arg("parent"),
        arg("source"),
        arg("name") = nullptr,
        R"(
            Define a payload to a prim as a child of the ``parent`` prim

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - The parent prim to add the payload to
                - **source** - The payload to add
                - **name** - The name of the payload. If not provided, uses the source prim's name

            Returns:
                The newly created payload prim. Returns an invalid prim on error.

        )"
    );
}

} // namespace usdex::core::bindings
