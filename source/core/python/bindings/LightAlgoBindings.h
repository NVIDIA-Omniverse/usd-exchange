// SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/LightAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

namespace usdex::core::bindings
{

void bindLightAlgo(module& m)
{
    m.def(
        "isLight",
        isLight,
        arg("prim"),
        R"(
            Determines if a UsdPrim has a ``UsdLux.LightAPI`` schema applied

            Args:
                prim: The prim to check for an applied ``UsdLux.LightAPI`` schema

            Returns:
                True if the prim has a ``UsdLux.LightAPI`` schema applied
        )"
    );

    m.def(
        "getLightAttr",
        &getLightAttr,
        arg("defaultAttr"),
        R"(
            Get the "correct" light attribute for a light that could have any combination of authored old and new UsdLux schema attributes

            The new attribute names have "inputs:" prepended to the names to make them connectable.

                - Light has only "intensity" authored: return "intensity" attribute

                - Light has only "inputs:intensity" authored: return "inputs:intensity" attribute

                - Light has both "inputs:intensity" and "intensity" authored: return "inputs:intensity"

            Args:
                defaultAttr: The attribute to read from the light schema: eg. ``UsdLux.RectLight.GetHeightAttr()``

            Returns:
                The attribute from which the light value should be read
        )"
    );

    //////////////////////////
    // "define" section
    //////////////////////////
    m.def(
        "defineDomeLight",
        overload_cast<UsdStagePtr, const SdfPath&, float, std::optional<std::string_view>, const TfToken&>(&defineDomeLight),
        arg("stage"),
        arg("path"),
        arg("intensity") = 1.0f,
        arg("texturePath") = nullptr,
        arg("textureFormat") = pxr::UsdLuxTokens->automatic.GetString(),
        R"(
                Creates a dome light with an optional texture.

                A dome light represents light emitted inward from a distant external environment, such as a sky or IBL light probe.

                Texture Format values:

                    - ``automatic`` - Tries to determine the layout from the file itself.
                    - ``latlong`` - Latitude as X, longitude as Y.
                    - ``mirroredBall`` - An image of the environment reflected in a sphere, using an implicitly orthogonal projection.
                    - ``angular`` - Similar to mirroredBall but the radial dimension is mapped linearly to the angle, for better sampling at the edges.
                    - ``cubeMapVerticalCross`` - Set to "automatic" by default.

                **Note:**

                    The DomeLight schema requires the
                    `dome's top pole to be aligned with the world's +Y axis <https://openusd.org/release/api/class_usd_lux_dome_light.html#details>`_.
                    In USD 23.11 a new `UsdLuxDomeLight_1 <https://openusd.org/release/api/class_usd_lux_dome_light__1.html#details>`_ schema was
                    added which gives control over the pole axis. However, it is not widely supported yet, so we still prefer to author the original
                    DomeLight schema and expect consuming application and renderers to account for the +Y pole axis.

                Parameters:
                    - **stage** - The stage in which the light should be authored
                    - **path** - The path which the light prim should be written to
                    - **intensity** - The intensity value of the dome light
                    - **texturePath** - The path to the texture file to use on the dome light.
                    - **textureFormat** - How the texture should be mapped on the dome light.

                Returns:
                    The dome light if created successfully.
            )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "defineDomeLight",
        overload_cast<UsdPrim, const std::string&, float, std::optional<std::string_view>, const TfToken&>(&defineDomeLight),
        arg("parent"),
        arg("name"),
        arg("intensity") = 1.0f,
        arg("texturePath") = nullptr,
        arg("textureFormat") = pxr::UsdLuxTokens->automatic.GetString(),
        R"(
                Creates a dome light with an optional texture.

                This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

                Parameters:
                    - **parent** - Prim below which to define the light
                    - **name** - Name of the light
                    - **intensity** - The intensity value of the dome light
                    - **texturePath** - The path to the texture file to use on the dome light.
                    - **textureFormat** - How the texture should be mapped on the dome light.

                Returns:
                    The dome light if created successfully.
            )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "defineDomeLight",
        overload_cast<UsdPrim, float, std::optional<std::string_view>, const TfToken&>(&defineDomeLight),
        arg("prim"),
        arg("intensity") = 1.0f,
        arg("texturePath") = nullptr,
        arg("textureFormat") = UsdLuxTokens->automatic.GetString(),
        R"(
            Creates a dome light with an optional texture.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the dome light on. The prim's type will be set to ``UsdLux.DomeLight``.
                - **intensity** - The intensity value of the dome light
                - **texturePath** - The path to the texture file to use on the dome light.
                - **textureFormat** - How the texture should be mapped on the dome light.

            Returns:
                The light if created successfully.
        )"
    );

    m.def(
        "defineRectLight",
        overload_cast<UsdStagePtr, const SdfPath&, float, float, float, std::optional<std::string_view>>(&defineRectLight),
        arg("stage"),
        arg("path"),
        arg("width"),
        arg("height"),
        arg("intensity") = 1.0f,
        arg("texturePath") = nullptr,
        R"(
                Creates a rectangular (rect) light with an optional texture.

                A rect light represents light emitted from one side of a rectangle.

                Parameters:
                    - **stage** - The stage in which the light should be authored
                    - **path** - The path which the light prim should be written to
                    - **width** - The width of the rectangular light, in the local X axis.
                    - **height** - The height of the rectangular light, in the local Y axis.
                    - **intensity** - The intensity value of the rectangular light
                    - **texturePath** - Optional - The path to the texture file to use on the rectangular light.

                Returns:
                    The rect light if created successfully.
            )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "defineRectLight",
        overload_cast<UsdPrim, const std::string&, float, float, float, std::optional<std::string_view>>(&defineRectLight),
        arg("parent"),
        arg("name"),
        arg("width"),
        arg("height"),
        arg("intensity") = 1.0f,
        arg("texturePath") = nullptr,
        R"(
                Creates a rectangular (rect) light with an optional texture.

                This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

                Parameters:
                    - **parent** - Prim below which to define the light
                    - **name** - Name of the light
                    - **width** - The width of the rectangular light, in the local X axis.
                    - **height** - The height of the rectangular light, in the local Y axis.
                    - **intensity** - The intensity value of the rectangular light
                    - **texturePath** - Optional - The path to the texture file to use on the rectangular light.

                Returns:
                    The rect light if created successfully.
            )",
        call_guard<gil_scoped_release>()
    );

    m.def(
        "defineRectLight",
        overload_cast<UsdPrim, float, float, float, std::optional<std::string_view>>(&defineRectLight),
        arg("prim"),
        arg("width"),
        arg("height"),
        arg("intensity") = 1.0f,
        arg("texturePath") = nullptr,
        R"(
            Creates a rectangular (rect) light with an optional texture.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the rectangular light on. The prim's type will be set to ``UsdLux.RectLight``.
                - **width** - The width of the rectangular light, in the local X axis.
                - **height** - The height of the rectangular light, in the local Y axis.
                - **intensity** - The intensity value of the rectangular light.
                - **texturePath** - The path to the texture file to use on the rectangular light.

            Returns:
                The light if created successfully.
        )"
    );
}

} // namespace usdex::core::bindings
