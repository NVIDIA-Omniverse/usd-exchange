// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/StageAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;

namespace usdex::core::bindings
{

void bindStageAlgo(module& m)
{
    // The bindings for createStage have been hand rolled in `python/bindings/_StageAlgoBindings.py` due to issues with cleanly passing ownership
    // of a UsdStageRefPtr from C++ to Python using pybind11

    m.def(
        "configureStage",
        overload_cast<UsdStagePtr, const std::string&, const TfToken&, double, double, std::optional<std::string_view>>(&configureStage),
        arg("stage"),
        arg("defaultPrimName"),
        arg("upAxis"),
        arg("linearUnits"),
        arg("massUnits"),
        arg("authoringMetadata") = nullptr,
        R"(
            Configure a stage so that the defining metadata is explicitly authored.

            The default prim will be used as the target of a Reference or Payload to this layer when no explicit prim path is specified.
            A root prim with the given ``defaultPrimName`` will be defined on the stage.
            If a new prim is defined then the type name will be set to ``Scope``.

            The stage metrics of `Up Axis <https://openusd.org/release/api/group___usd_geom_up_axis__group.html#details>`_,
            `Linear Units <https://openusd.org/release/api/group___usd_geom_linear_units__group.html#details>`_ and
            `Mass Units <https://openusd.org/release/api/usd_physics_page_front.html#usdPhysics_units>`_ will be authored.

            The root layer will be annotated with authoring metadata, unless previously annotated. This is to preserve
            authoring metadata on referenced layers that came from other applications. See ``setLayerAuthoringMetadata`` for more details.

            Parameters:
                - **stage** - The stage to be configured.
                - **defaultPrimName** - Name of the default root prim.
                - **upAxis** - The up axis for all the geometry contained in the stage.
                - **linearUnits** - The meters per unit for all linear measurements in the stage.
                - **massUnits** - The kilograms per unit for all mass measurements in the stage.
                - **authoringMetadata** - The provenance information from the host application. See ``setLayerAuthoringMetadata`` for details.

            Returns:
                A bool indicating if the metadata was successfully authored.

        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "configureStage",
        overload_cast<UsdStagePtr, const std::string&, const TfToken&, double, std::optional<std::string_view>>(&configureStage),
        arg("stage"),
        arg("defaultPrimName"),
        arg("upAxis"),
        arg("linearUnits"),
        arg("authoringMetadata") = nullptr,
        R"(
            Configure a stage so that the defining metadata is explicitly authored.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

           Parameters:
                - **stage** - The stage to be configured.
                - **defaultPrimName** - Name of the default root prim.
                - **upAxis** - The up axis for all the geometry contained in the stage.
                - **linearUnits** - The meters per unit for all linear measurements in the stage.
                - **authoringMetadata** - The provenance information from the host application. See ``setLayerAuthoringMetadata`` for details.

            Returns:
                A bool indicating if the metadata was successfully authored.

        )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "saveStage",
        &saveStage,
        arg("stage"),
        arg("authoringMetadata") = nullptr,
        arg("comment") = nullptr,
        R"(
            Save the given ``Usd.Stage`` with metadata applied to all dirty layers.

            Save all dirty layers and sublayers contributing to this stage.

            All dirty layers will be annotated with authoring metadata, unless previously annotated. This is to preserve
            authoring metadata on referenced layers that came from other applications.

            The comment will be authored in all layers as the SdfLayer comment.

            Args:
                stage: The stage to be saved.
                authoringMetadata: The provenance information from the host application. See ``setLayerAuthoringMetadata`` for details.
                    If the "creator" key already exists on a given layer, it will not be overwritten & this data will be ignored.
                comment: The comment will be authored in all dirty layers as the ``Sdf.Layer`` comment.
        )"
    );

    m.def(
        "isEditablePrimLocation",
        [](const UsdStagePtr stage, const SdfPath path)
        {
            std::string reason;
            bool result = isEditablePrimLocation(stage, path, &reason);
            return pybind11::make_tuple(result, reason);
        },
        arg("stage"),
        arg("path"),
        R"(
            Validate that prim opinions could be authored at this path on the stage

            This validates that the ``stage`` and ``path`` are valid, and that the path is absolute.
            If a prim already exists at the given path it must not be an instance proxy.

            If the location is invalid and ``reason`` is non-null, an error message describing the validation error will be set.

            Parameters:
                - **stage** - The stage to consider.
                - **path** - The absolute to consider.

            Returns:
                Tuple[bool, str] with a bool indicating if the location is valid, and the string is a non-empty reason if the location is invalid.
        )"
    );

    m.def(
        "isEditablePrimLocation",
        [](const UsdPrim prim, const std::string& nameStr)
        {
            std::string reason;
            bool result = isEditablePrimLocation(prim, nameStr, &reason);
            return pybind11::make_tuple(result, reason);
        },
        arg("prim"),
        arg("name"),
        R"(
            Validate that prim opinions could be authored for a child prim with the given name

            This validates that the ``prim`` is valid, and that the ``name`` is a valid identifier.
            If a prim already exists at the given path it must not be an instance proxy.

            If the location is invalid and ``reason`` is non-null, an error message describing the validation error will be set.

            Parameters:
                - **parent** - The UsdPrim which would be the parent of the proposed location.
                - **name** - The name which would be used for the UsdPrim at the proposed location.

            Returns:
                Tuple[bool, str] with a bool indicating if the location is valid, and the string is a non-empty reason if the location is invalid.

        )"
    );

    m.def(
        "isEditablePrimLocation",
        [](const UsdPrim prim)
        {
            std::string reason;
            bool result = isEditablePrimLocation(prim, &reason);
            return pybind11::make_tuple(result, reason);
        },
        arg("prim"),
        R"(
            Validate that prim opinions could be authored for the prim

            This validates that the ``prim`` is valid and not be an instance proxy.

            If the location is invalid and ``reason`` is non-null, an error message describing the validation error will be set.

            Parameters:
                - **prim** - The UsdPrim to consider.

            Returns:
                Tuple[bool, str] with a bool indicating if the location is valid, and the string is a non-empty reason if the location is invalid.

        )"
    );
}

} // namespace usdex::core::bindings
