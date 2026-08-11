# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

__all__ = ["createAssetPayload", "addAssetContent", "addAssetLibrary"]

from typing import Optional

from pxr import Ar, Sdf, Tf, Usd, UsdGeom

from ._StageAlgoBindings import createStage
from ._usdex_core import defineScope, getContentsToken, getLayerAuthoringMetadata, getLibraryToken, getPayloadToken, getValidPrimName


def createAssetPayload(stage: Usd.Stage, format: str = "usda", fileFormatArgs: Optional[dict] = None) -> Optional[Usd.Stage]:
    """
    Create a relative layer within a ``getPayloadToken()`` subdirectory to hold the content of an asset.

    This layer represents the root layer of the Payload that the Asset Interface targets.

    This entry point layer will subLayer the different Content Layers (e.g., Geometry, Materials, etc.) added via ``usdex.core.addAssetContent``.

    Note:
        This function does not create an actual Payload, it is only creating a relative layer that should eventually
        be the target of a Payload (via ``usdex.core.addAssetInterface``).

    Args:
        stage: The stage's edit target identifier will dictate where the relative payload layer will be created.
        format: The file format extension (default: "usda").
        fileFormatArgs: Additional file format-specific arguments to be supplied during stage creation.

    Returns:
        The newly created relative payload layer opened as a new stage. Returns an invalid stage on error.
    """
    # This function should mimic the behavior of the C++ function `usdex::core::createAssetPayload`.
    # It has been re-implemented here rather than bound to python using pybind11 due to issues with the transfer of ownership of the UsdStage object
    # from C++ to Python

    if not stage:
        Tf.Warn("Unable to create asset payload stage due to an invalid asset stage")
        return None

    if stage.GetRootLayer().anonymous:
        Tf.Warn("Unable to create asset payload stage due to an anonymous asset stage")
        return None

    resolver: Ar.Resolver = Ar.GetResolver()

    fileFormatArgs = fileFormatArgs or dict()

    payloadStage: Usd.Stage = createStage(
        resolver.CreateIdentifier(f"./{getPayloadToken()}/{getContentsToken()}.{format}", resolver.Resolve(stage.GetRootLayer().identifier)),
        defaultPrimName=stage.GetDefaultPrim().GetName(),
        upAxis=UsdGeom.GetStageUpAxis(stage),
        linearUnits=UsdGeom.GetStageMetersPerUnit(stage),
        authoringMetadata=getLayerAuthoringMetadata(stage.GetRootLayer()),
        fileFormatArgs=fileFormatArgs,
    )
    if not payloadStage:
        Tf.Warn("Unable to create asset payload stage")
        return None

    # Copy the asset stage's default prim to the asset payload stage
    success = Sdf.CopySpec(
        stage.GetRootLayer(),
        stage.GetDefaultPrim().GetPath(),
        payloadStage.GetRootLayer(),
        payloadStage.GetDefaultPrim().GetPath(),
    )
    if not success:
        Tf.Warn("Unable to copy the asset stage's default prim to the asset payload stage")
        return None

    return payloadStage


def addAssetLibrary(stage: Usd.Stage, name: str, format: str = "usdc", fileFormatArgs: Optional[dict] = None) -> Optional[Usd.Stage]:
    """
    Create a Library Layer from which the Content Layers can reference prims.

    This layer will contain a library of meshes, materials, prototypes for instances, or anything else that can be referenced by
    the Content Layers. It is not intended to be used as a standalone layer. The default prim will have a ``class`` specifier.

    Args:
        stage: The stage's edit target identifier will dictate where the Library Layer will be created.
        name: The name of the library (e.g., "Geometry", "Materials").
        format: The file format extension (default: "usdc").
        fileFormatArgs: Additional file format-specific arguments to be supplied during stage creation.

    Returns:
        The newly created relative layer opened as a new stage. It will be named "<name>Library.<format>"
    """
    # This function should mimic the behavior of the C++ function `usdex::core::addAssetLibrary`.
    # It has been re-implemented here rather than bound to python using pybind11 due to issues with the transfer of ownership of the UsdStage object
    # from C++ to Python

    if not stage:
        Tf.Warn("Unable to add asset library due to an invalid content stage")
        return None

    if stage.GetRootLayer().anonymous:
        Tf.Warn("Unable to add asset library due to an anonymous content stage")
        return None

    resolver: Ar.Resolver = Ar.GetResolver()
    relativeIdentifier = f"./{name}{getLibraryToken()}.{format}"
    identifier = resolver.CreateIdentifier(relativeIdentifier, resolver.Resolve(stage.GetRootLayer().identifier))

    fileFormatArgs = fileFormatArgs or dict()

    libraryStage: Usd.Stage = createStage(
        identifier,
        getValidPrimName(name),
        UsdGeom.GetStageUpAxis(stage),
        UsdGeom.GetStageMetersPerUnit(stage),
        getLayerAuthoringMetadata(stage.GetRootLayer()),
        fileFormatArgs=fileFormatArgs,
    )
    if not libraryStage:
        Tf.Warn("Unable to create a new stage for the asset library")
        return None

    # Create the asset library scope prim (with a class specifier)
    scope = defineScope(libraryStage.GetPseudoRoot(), name)
    if not scope:
        return None
    # Set the specifier to class
    scope.GetPrim().SetSpecifier(Sdf.SpecifierClass)
    return libraryStage


def addAssetContent(
    stage: Usd.Stage,
    name: str,
    format: str = "usda",
    fileFormatArgs: Optional[dict] = None,
    prependLayer: bool = True,
    createScope: bool = True,
) -> Optional[Usd.Stage]:
    """
    Create a specific Content Layer and add it as a sublayer to the stage's edit target.

    Any Prim data can be authored in the Content Layer, there are no specific restrictions or requirements.

    However, it is recommended to use a unique Content Layer for each domain (Geometry, Materials, Physics, etc.)
    and to ensure only domain-specific opinions are authored in that Content Layer. This provides a clear separation
    of concerns and allows for easier reuse of assets across domains as each layer can be enabled/disabled (muted) independently.

    Args:
        stage: The stage's edit target will determine where the Content Layer is created and will have its subLayers updated with the new content
        name: The name of the Content Layer (e.g., "Geometry", "Materials", "Physics")
        format: The file format extension (default: "usda").
        fileFormatArgs: Additional file format-specific arguments to be supplied during stage creation.
        prependLayer: Whether to prepend (or append) the layer to the sublayer stack (default: True).
        createScope: Whether to create a scope in the content stage (default: True).

    Returns:
        The newly created Content Layer opened as a new stage. Returns an invalid stage on error.
    """
    # This function should mimic the behavior of the C++ function `usdex::core::addAssetContent`.
    # It has been re-implemented here rather than bound to python using pybind11 due to issues with the transfer of ownership of the UsdStage object
    # from C++ to Python

    if not stage:
        Tf.Warn("Unable to add asset content due to an invalid payload stage")
        return None

    if stage.GetRootLayer().anonymous:
        Tf.Warn("Unable to add asset content due to an anonymous payload stage")
        return None

    resolver: Ar.Resolver = Ar.GetResolver()
    relativeIdentifier = f"./{name}.{format}"
    identifier = resolver.CreateIdentifier(relativeIdentifier, resolver.Resolve(stage.GetRootLayer().identifier))

    defaultPrim = stage.GetDefaultPrim()
    if not defaultPrim:
        Tf.Warn("Unable to add asset content due to an invalid default prim")
        return None

    fileFormatArgs = fileFormatArgs or dict()

    contentStage: Usd.Stage = createStage(
        identifier,
        defaultPrimName=defaultPrim.GetName(),
        upAxis=UsdGeom.GetStageUpAxis(stage),
        linearUnits=UsdGeom.GetStageMetersPerUnit(stage),
        authoringMetadata=getLayerAuthoringMetadata(stage.GetRootLayer()),
        fileFormatArgs=fileFormatArgs,
    )
    if not contentStage:
        Tf.Warn("Unable to create a new stage for the asset content")
        return None

    subLayerPaths = stage.GetRootLayer().subLayerPaths
    if prependLayer:
        subLayerPaths.insert(0, relativeIdentifier)
    else:
        subLayerPaths.append(relativeIdentifier)

    success = Sdf.CopySpec(
        stage.GetRootLayer(),
        stage.GetDefaultPrim().GetPath(),
        contentStage.GetRootLayer(),
        contentStage.GetDefaultPrim().GetPath(),
    )
    if not success:
        Tf.Warn("Unable to copy the payload stage's default prim to the asset content stage")
        return None

    if createScope:
        scope = defineScope(contentStage.GetDefaultPrim(), name)
        if not scope:
            Tf.Warn("Unable to create a scope in the asset content stage")
            return None

    return contentStage
