// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/core/AssetStructure.h
//! @brief Utility functions to create atomic models based on sound asset structure principles

#include "Api.h"

#include <pxr/usd/sdf/path.h>
#include <pxr/usd/usd/prim.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/scope.h>

#include <optional>
#include <string>
#include <string_view>

namespace usdex::core
{

//! @defgroup assetstructure Asset Structure
//!
//! Utility functions for creating Assets following NVIDIA's
//! [Principles of Scalable Asset Structure](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html).
//!
//! An asset is a named, versioned, and structured container of one or more resources which may include composable OpenUSD layers, textures,
//! volumetric data, and more.
//!
//! This module aims to codify asset structures that have been proven scalable and have broad import compatibility across a wide range of OpenUSD
//! enabled applications, while guiding and simplifying the development process for new OpenUSD Exporters.
//!
//! # Principles of Scalable Asset Structure #
//!
//! When developing an asset structure, the following principles can guide toward a scalable structure:
//!
//! - Legibility:
//!   - Use descriptive names for layers, scopes, and prims. This might mean using a name like `LargeCardboardBox` or `ID-2023_5678`,
//!     depending on the context.
//!   - The tokens used in this module for files, directories, scopes, and layer names can make things clear and consistent.
//! - Modularity:
//!   - The structure should facilitate iterative improvement of reusable content.
//!   - The functions in this module use relative paths to allow for asset relocation.
//!   - The asset library layer concept allows for the reuse of content within an asset.
//!   - Splitting content into different layers per domain (Geometry, Materials, Physics, etc) enables reuse and iteration across workflows.
//! - Performance:
//!   - The structure should accelerate content read and write speeds for users and processes.
//!   - This could refer to an individual working within an asset or the ability to render millions of preview instances.
//!   - This module creates a payload (allowing for deactivation) with extents hints so that the asset can be used in a larger scene.
//!   - This module allows the use of text USDA files for lightweight human-readable layers and binary USDC files for heavy data.
//! - Navigability:
//!   - The structure should facilitate discovery of elements while retaining flexibility.
//!   - The assets should be structured around multiple hierarchical paths (file, directory, prim paths, model hierarchy, etc.).
//!   - This module offers functions to generate consistent asset structures.
//!
//! # Basic Structure #
//!
//! Almost all asset structures require the use of:
//! - [Scopes](https://openusd.org/release/api/class_usd_geom_scope.html)
//! - [References](https://openusd.org/release/glossary.html#usdglossary-references)
//! - [Payloads](https://openusd.org/release/glossary.html#usdglossary-payload)
//!
//! While Scopes are easily defined using UsdGeom, it is easy to forget to check if the target location is editable.
//! `usdex::core::defineScope` prevents this simple mistake.
//!
//! References and Payloads can be more complex. The `usdex::core::defineReference` and `usdex::core::definePayload` functions
//! provide a simple interface to create them, ensuring to author a relative `AssetPath` whenever possible (for portability).
//!
//! # Atomic Models #
//!
//! Atomic models are entirely self contained, have no external dependencies, and are usually
//! [Components](https://openusd.org/release/glossary.html?highlight=kind#usdglossary-component) in the
//! [Model Hierarchy](https://openusd.org/release/glossary.html?highlight=kind#usdglossary-modelhierarchy).
//!
//! Because model hierarchy/kind is difficult to maintain manually, two functions are provided to help:
//! - `usdex::core::configureComponentHierarchy`: Configures a component hierarchy, setting all descendant `components` to `subcomponent`
//! - `usdex::core::configureAssemblyHierarchy`: Configures an assembly hierarchy, setting all authored descendant kinds to `group` until a
//! `component` is found
//!
//! The following diagram shows the file, directory, layer, and reference structure of an atomic model:
//!
//! @code{.unparsed}
//!
//! +---------------------------+     +-----------------------------+
//! | Asset Layer w/ Interface  |     | Asset Content Layer         |
//! +---------------------------+     +-----------------------------+
//! | Flower                    | +---> Physics.usda                |
//! |  {                        | |   |  {                          |
//! |   defaultPrim=/Flower     | |   |   defaultPrim=/Flower       |
//! |  }                        | |   |  }                          |
//! |                           | |   |                             |
//! |  Xform Flower             | |   |  Xform Flower               |
//! |   payloads[               | |   |   Scope Geometry            |
//! |    ./Payload/Contents.usda| |   |    # physics attrs applied  |
//! |   ]           |           | |   |    # to prims               |
//! +---------------+-----------+ |   |   Scope Physics             |
//!                 |             |   |    Material PhysicsMaterial |
//!                 |             |   +-----------------------------+
//!                 |             |
//!                 |             |   +-----------------------------+
//! +---------------v-----------+ |   | Asset Content Layer         |
//! | Asset Payload Layer       | |   +-----------------------------+
//! +---------------------------+ | +-> Materials.usda              |+------------------------+
//! | Contents.usda             | | | |  {                          || Asset Library Layer    |
//! |  {                        | | | |   defaultPrim=/Flower       |+------------------------+
//! |   defaultPrim=/Flower     | | | |  }                          || MaterialsLibrary.usdc  |
//! |   sublayers[              | | | |                             ||  {                     |
//! |    ./Physics.usda---------+-+ | |  Xform Flower               ||  defaultPrim=/Materials|
//! |    ./Materials.usda-------+---+ |   Scope Materials           ||  }                     |
//! |    ./Geometry.usda--------+--+  | +->Material Clay            ||                        |
//! |  }                        |  |  | |   reference[              ||  Scope Materials       |
//! |                           |  |  | |    ./MaterialsLibrary.usdc++-->Material Clay        |
//! |  Xform Flower             |  |  | |   ]                       ||   Material GreenStem   |
//! +---------------------------+  |  | | over Geometry             ||   Material PinkPetal   |
//!                                |  | |  over Planter {           |+------------------------+
//!                                |  | +----material:binding=Clay  |
//!                                |  |    }                        |
//!                                |  +-----------------------------+
//!                                |
//!                                |  +-----------------------------+
//!                                |  | Asset Content Layer         |
//!                                |  +-----------------------------+
//!                                +--> Geometry.usda               |+------------------------+
//!                                   |  {                          || Asset Library Layer    |
//!                                   |   defaultPrim=/Flower       |+------------------------+
//!                                   |  }                          || GeometryLibrary.usdc   |
//!                                   |                             ||  {                     |
//!                                   |  Xform Flower               ||   defaultPrim=/Geometry|
//!                                   |   Scope Geometry            ||  }                     |
//!                                   |    Mesh Planter             ||                        |
//!                                   |     reference[              ||  Scope Geometry        |
//!                                   |      ./GeometryLibrary.usdc-++-->Mesh Planter         |
//!                                   |     ]                       ||   Mesh Stem            |
//!                                   |    ...                      ||   Mesh Petals          |
//!                                   +-----------------------------++------------------------+
//! @endcode
//!
//! ## Authoring an Atomic Model ##
//!
//! An example sequence for authoring the Flower atomic asset:
//! 1. Create the primary layer for the asset using `usdex::core::createStage`, setting the defaultPrim to `/Flower`
//! 2. Create a relative layer within a Payload subdirectory to hold the content of the asset using `usdex::core::createAssetPayload`
//! 3. Add a geometry library using `usdex::core::addAssetLibrary(stage, "Geometry")`
//!   - Add planter, stem, and petals meshes to the geometry library
//! 4. Add a materials library using `usdex::core::addAssetLibrary(stage, "Materials")`
//!   - Add clay, green stem, and pink petals materials to the materials library
//! 5. Add a geometry content layer using `usdex::core::addAssetContent(stage, "Geometry")`
//!   - Add planter, stem, and petals references that contain xformOps
//! 6. Add a materials content layer using `usdex::core::addAssetContent(stage, "Materials")`
//!   - Add clay, green stem, and pink petals references and bind them to the geometry
//! 7. Add the asset interface to the primary layer using `usdex::core::addAssetInterface`
//!   - This creates a payload to the contents within the primary layer, configures asset information, and adds extents hints
//!
//! @note These asset structure functions are highly opinionated and implement best practices following NVIDIA's
//! [Principles of Scalable Asset Structure](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html).
//! They provide broad import compatibility across a wide range of OpenUSD enabled applications. However, if you require more
//! flexibility to suit one specific application, renderer, or custom pipeline, these functions may serve you better as a sample implementation
//! rather than something you call directly.
//!
//! @{

//! Get the Asset token
//!
//! @returns The Asset token
USDEX_API const pxr::TfToken& getAssetToken();

//! Get the token for the Contents layer
//!
//! @returns The token for the Contents layer
USDEX_API const pxr::TfToken& getContentsToken();

//! Get the token for the Geometry layer and scope
//!
//! @returns The token for the Geometry layer and scope
USDEX_API const pxr::TfToken& getGeometryToken();

//! Get the token for the Library layer
//!
//! @returns The token for the Library layer
USDEX_API const pxr::TfToken& getLibraryToken();

//! Get the token for the Materials layer and scope
//!
//! @returns The token for the Materials layer and scope
USDEX_API const pxr::TfToken& getMaterialsToken();

//! Get the token for the Payload directory
//!
//! @returns The token for the Payload directory
USDEX_API const pxr::TfToken& getPayloadToken();

//! Get the token for the Physics layer and scope
//!
//! @returns The token for the Physics layer and scope
USDEX_API const pxr::TfToken& getPhysicsToken();

//! Get the token for the Textures directory
//!
//! @returns The token for the Textures directory
USDEX_API const pxr::TfToken& getTexturesToken();

//! Defines a scope on the stage.
//!
//! A scope is a simple grouping primitive that is useful for organizing prims in a scene.
//!
//! @param stage The stage on which to define the scope
//! @param path The absolute prim path at which to define the scope
//!
//! @returns UsdGeomScope schema wrapping the defined UsdPrim. Returns an invalid schema on error.
USDEX_API pxr::UsdGeomScope defineScope(pxr::UsdStagePtr stage, const pxr::SdfPath& path);

//! Defines a scope on the stage.
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent Prim below which to define the scope
//! @param name Name of the scope
//!
//! @returns UsdGeomScope schema wrapping the defined UsdPrim. Returns an invalid schema on error.
USDEX_API pxr::UsdGeomScope defineScope(pxr::UsdPrim parent, const std::string& name);

//! Defines a scope from an existing prim.
//!
//! This converts an existing prim to a Scope type.
//!
//! @param prim The existing prim to convert to a scope
//!
//! @returns UsdGeomScope schema wrapping the defined UsdPrim. Returns an invalid schema on error.
USDEX_API pxr::UsdGeomScope defineScope(pxr::UsdPrim prim);

//! Define a reference to a prim
//!
//! This creates a reference prim that targets a prim in another layer (external reference) or the same layer (internal reference).
//! The reference's assetPath will be set to the relative identifier between the stage's edit target and the source's stage if it's
//! an external reference with a valid relative path.
//!
//! For more information, see:
//! - https://openusd.org/release/glossary.html#usdglossary-references
//! - https://openusd.org/release/api/class_usd_references.html#details
//!
//! @param stage The stage on which to define the reference
//! @param path The absolute prim path at which to define the reference
//! @param source The prim to reference
//!
//! @returns The newly created reference prim. Returns an invalid prim on error.
USDEX_API pxr::UsdPrim defineReference(pxr::UsdStagePtr stage, const pxr::SdfPath& path, const pxr::UsdPrim& source);

//! Define a reference to a prim as a child of the `parent` prim
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent The parent prim to add the reference to
//! @param source The prim to reference
//! @param name The name of the reference. If not provided, uses the source prim's name
//!
//! @returns The newly created reference prim. Returns an invalid prim on error.
USDEX_API pxr::UsdPrim defineReference(pxr::UsdPrim parent, const pxr::UsdPrim& source, std::optional<std::string_view> name = std::nullopt);

//! Define a payload to a prim
//!
//! This creates a payload prim that targets a prim in another layer (external payload) or the same layer (internal payload)
//! The payload's assetPath will be set to the relative identifier between the stage's edit target and the source's stage if it's
//! an external payload with a valid relative path.
//!
//! For more information, see:
//! - https://openusd.org/release/glossary.html#usdglossary-payload
//! - https://openusd.org/release/api/class_usd_payloads.html#details
//!
//! @param stage The stage on which to define the payload
//! @param path The absolute prim path at which to define the payload
//! @param source The payload to add
//!
//! @returns The newly created payload prim. Returns an invalid prim on error.
USDEX_API pxr::UsdPrim definePayload(pxr::UsdStagePtr stage, const pxr::SdfPath& path, const pxr::UsdPrim& source);

//! Define a payload to a prim as a child of the `parent` prim
//!
//! This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.
//!
//! @param parent The parent prim to add the payload to
//! @param source The payload to add
//! @param name The name of the payload. If not provided, uses the source prim's name
//!
//! @returns The newly created payload prim. Returns an invalid prim on error.
USDEX_API pxr::UsdPrim definePayload(pxr::UsdPrim parent, const pxr::UsdPrim& source, std::optional<std::string_view> name = std::nullopt);

//! Create a relative layer within a `getPayloadToken()` subdirectory to hold the content of an asset
//!
//! This layer represents the root layer of the Payload that the Asset Interface targets.
//!
//! This entry point layer will subLayer the different Content Layers (e.g., Geometry, Materials, etc.) added via `addAssetContent()`.
//!
//! @note This function does not create an actual Payload, it is only creating a relative layer that should eventually
//! be the target of a Payload (via `addAssetInterface()`).
//!
//! @param stage The stage's edit target identifier will dictate where the relative payload layer will be created
//! @param format The file format extension (default: "usda")
//! @param fileFormatArgs Additional file format-specific arguments to be supplied during stage creation.
//! @returns The newly created relative payload layer opened as a new stage. Returns an invalid stage on error.
USDEX_API pxr::UsdStageRefPtr createAssetPayload(
    pxr::UsdStagePtr stage,
    const std::string& format = "usda",
    const pxr::SdfLayer::FileFormatArguments& fileFormatArgs = pxr::SdfLayer::FileFormatArguments()
);

//! Create a Library Layer from which the Content Layers can reference prims
//!
//! This layer will contain a library of meshes, materials, prototypes for instances, or anything else that can be referenced by
//! the Content Layers. It is not intended to be used as a standalone layer. The default prim will have a `class` specifier.
//!
//! @param stage The stage's edit target identifier will dictate where the Library Layer will be created
//! @param name The name of the library (e.g., "Geometry", "Materials")
//! @param format The file format extension (default: "usdc")
//! @param fileFormatArgs Additional file format-specific arguments to be supplied during stage creation.
//! @returns The newly created relative layer opened as a new stage. It will be named "<name>Library.<format>"
USDEX_API pxr::UsdStageRefPtr addAssetLibrary(
    pxr::UsdStagePtr stage,
    const std::string& name,
    const std::string& format = "usdc",
    const pxr::SdfLayer::FileFormatArguments& fileFormatArgs = pxr::SdfLayer::FileFormatArguments()
);

//! Create a specific Content Layer and add it as a sublayer to the stage's edit target
//!
//! Any Prim data can be authored in the Content Layer, there are no specific restrictions or requirements.
//!
//! However, it is recommended to use a unique Content Layer for each domain (Geometry, Materials, Physics, etc.)
//! and to ensure only domain-specific opinions are authored in that Content Layer. This provides a clear separation
//! of concerns and allows for easier reuse of assets across domains as each layer can be enabled/disabled (muted) independently.
//!
//! @param stage The stage's edit target will determine where the Content Layer is created and will have its subLayers updated with the new content
//! @param name The name of the Content Layer (e.g., "Geometry", "Materials", "Physics")
//! @param format The file format extension (default: "usda")
//! @param fileFormatArgs Additional file format-specific arguments to be supplied during stage creation.
//! @param prependLayer Whether to prepend (or append) the layer to the sublayer stack (default: true)
//! @param createScope Whether to create a scope in the content stage (default: true)
//! @returns The newly created Content Layer opened as a new stage. Returns an invalid stage on error.
USDEX_API pxr::UsdStageRefPtr addAssetContent(
    pxr::UsdStagePtr stage,
    const std::string& name,
    const std::string& format = "usda",
    const pxr::SdfLayer::FileFormatArguments& fileFormatArgs = pxr::SdfLayer::FileFormatArguments(),
    bool prependLayer = true,
    bool createScope = true
);

//! Add an Asset Interface to a stage, which payloads a source stage's contents
//!
//! This function creates a payload to the source stage's contents as the default prim on the stage.
//!
//! It (re)configures the stage with the source stage's metadata, payloads the defaultPrim from the source stage, and annotates the Asset
//! Interface with USD model metadata including component kind, asset name, and extents hint.
//!
//! @param stage The stage's edit target will become the Asset Interface
//! @param source The stage that the Asset Interface will target as a Payload
//! @returns True if the Asset Interface was added successfully, false otherwise
USDEX_API bool addAssetInterface(pxr::UsdStagePtr stage, const pxr::UsdStagePtr source);

//! Configure a prim and its descendants to establish a proper asset component hierarchy
//!
//! Sets the kind of the prim to "component" and adjusts the kinds of all descendant prims to maintain
//! a valid USD model hierarchy. Any descendant prim that currently has the kind "component" will be
//! changed to "subcomponent". Any descendant prim that has an authored kind other than "component"
//! or "subcomponent" will have its kind cleared (set to an empty token).
//!
//! This function is commonly used when configuring asset interfaces to ensure the model hierarchy
//! follows USD best practices for components.
//!
//! @param prim The prim to configure as a component. This prim and all its descendants will be processed.
//! @returns True if the component hierarchy was successfully configured, false otherwise.
USDEX_API bool configureComponentHierarchy(pxr::UsdPrim prim);

//! Configure a prim and its descendants to establish a proper asset assembly hierarchy
//!
//! Sets the kind of the prim to "assembly" and adjusts the kinds of all descendant prims to maintain
//! a valid USD model hierarchy. Any descendant prim with an invalid kind will be changed to "group".
//! Descendant prims with "component" kind are left unchanged to preserve the component hierarchy.
//!
//! If a prim has no authored kind, it will be set to "group" if it has descendant model prims.
//!
//! This function is commonly used when configuring complex assets that contain multiple components
//! to ensure the model hierarchy follows USD best practices for assemblies.
//!
//! @param prim The prim to configure as an assembly. This prim and all its descendants will be processed.
//! @returns True if the assembly hierarchy was successfully configured, false otherwise.
USDEX_API bool configureAssemblyHierarchy(pxr::UsdPrim prim);

//! @}

} // namespace usdex::core
