# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
__all__ = ["createStage"]

from typing import Optional

from pxr import Sdf, Tf, Usd

from ._usdex_core import configureStage


def createStage(
    identifier: str,
    defaultPrimName: str,
    upAxis: str,
    linearUnits: float,
    authoringMetadata: str,
    fileFormatArgs: Optional[dict] = None,
    massUnits: Optional[float] = None,
) -> Optional[Usd.Stage]:
    """
    Create and configure a `Usd.Stage` so that the defining metadata is explicitly authored.

    See `configureStage` for more details.

    Note:

        The extension of the `identifier` must be associated with a file format that supports editing.

    Args:
        identifier: The identifier to be used for the root layer of this stage.
        defaultPrimName: Name of the root prim root prim.
        upAxis: The up axis for all the geometry contained in the stage.
        linearUnits: The meters per unit for all linear measurements in the stage, eg. `UsdGeom.LinearUnits.meters`
        authoringMetadata: The provenance information from the host application. See `setLayerAuthoringMetadata` for details.
        fileFormatArgs: Additional file format-specific arguments to be supplied during Stage creation.
        massUnits: The kilograms per unit for all mass measurements in the stage, defaults to `UsdPhysics.MassUnits.kilograms`.

    Returns:
        The newly created stage or None
    """
    # This function should mimic the behavior of the C++ function `usdex::core::createStage`.
    # It has been re-implemented here rather than bound to python using pybind11 due to issues with the transfer of ownership of the UsdStage object
    # from C++ to Python

    # Early out for an unsupported identifier
    if not identifier or not Usd.Stage.IsSupportedFile(identifier):
        Tf.Warn(f'Unable to create UsdStage at "{identifier}" due to an invalid identifier')
        return None

    # Create the stage in memory to avoid adding the identifier to the registry in cases where the call fails due to invalid argument values
    # This differs for the C++ implementation only because we do not want to expose the validation logic via the API
    stage = Usd.Stage.CreateInMemory(identifier)

    # Configure the stage and early out on failure
    # Note that the warnings from this call will not exactly match the more contextual ones from the C++ logic
    if massUnits is None:
        if not configureStage(stage, defaultPrimName, upAxis, linearUnits, authoringMetadata):
            return None
    else:
        if not configureStage(stage, defaultPrimName, upAxis, linearUnits, massUnits, authoringMetadata):
            return None

    # Export the stage to the desired identifier
    comment = ""
    fileFormatArgs = fileFormatArgs or dict()
    if not stage.GetRootLayer().Export(identifier, comment, fileFormatArgs):
        return None

    # If the layer is already loaded reload it and return a stage wrapping the layer
    # Without the reload the state of the layer will not reflect what was just exported
    layer = Sdf.Layer.Find(identifier)
    if layer:
        if not layer.Reload(force=True):
            return None
        return Usd.Stage.Open(layer)

    # Return a stage wrapping the exported layer
    return Usd.Stage.Open(identifier)
