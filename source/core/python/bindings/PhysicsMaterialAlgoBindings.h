// SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/PhysicsMaterialAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

namespace usdex::core::bindings
{

void bindPhysicsMaterialAlgo(module& m)
{
    m.def(
        "definePhysicsMaterial",
        overload_cast<UsdStagePtr, const SdfPath&, const float, const std::optional<float>, const std::optional<float>, const std::optional<float>>(
            &definePhysicsMaterial
        ),
        arg("stage"),
        arg("path"),
        arg("dynamicFriction"),
        arg("staticFriction") = nullptr,
        arg("restitution") = nullptr,
        arg("density") = nullptr,
        R"(
            Creates a Physics Material.

            When ``UsdPhysics.MaterialAPI`` is applied on a ``UsdShade.Material`` it specifies various physical properties which should be used during simulation of
            the bound geometry.

            See [UsdPhysicsMaterialAPI](https://openusd.org/release/api/class_usd_physics_material_a_p_i.html) for details.

            Parameters:
                - **stage** - The stage on which to define the material
                - **path** - The absolute prim path at which to define the material
                - **dynamicFriction** - The dynamic friction of the material
                - **staticFriction** - The static friction of the material
                - **restitution** - The restitution of the material
                - **density** - The density of the material

            Returns:
                ``UsdShade.Material`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsMaterial",
        overload_cast<UsdPrim, const std::string&, const float, const std::optional<float>, const std::optional<float>, const std::optional<float>>(
            &definePhysicsMaterial
        ),
        arg("parent"),
        arg("name"),
        arg("dynamicFriction"),
        arg("staticFriction") = nullptr,
        arg("restitution") = nullptr,
        arg("density") = nullptr,
        R"(
            Creates a Physics Material.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **parent** - Prim below which to define the physics material
                - **name** - Name of the physics material
                - **dynamicFriction** - The dynamic friction of the material
                - **staticFriction** - The static friction of the material
                - **restitution** - The restitution of the material
                - **density** - The density of the material

            Returns:
                ``UsdShade.Material`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "definePhysicsMaterial",
        overload_cast<UsdPrim, const float, const std::optional<float>, const std::optional<float>, const std::optional<float>>(&definePhysicsMaterial
        ),
        arg("prim"),
        arg("dynamicFriction"),
        arg("staticFriction") = nullptr,
        arg("restitution") = nullptr,
        arg("density") = nullptr,
        R"(
            Creates a Physics Material.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Parameters:
                - **prim** - Prim to define the material. The prim's type will be set to ``UsdShade.Material``.
                - **dynamicFriction** - The dynamic friction of the material
                - **staticFriction** - The static friction of the material
                - **restitution** - The restitution of the material
                - **density** - The density of the material

            Returns:
                ``UsdShade.Material`` schema wrapping the defined ``Usd.Prim``.
        )"
    );

    m.def(
        "addPhysicsToMaterial",
        &addPhysicsToMaterial,
        arg("material"),
        arg("dynamicFriction"),
        arg("staticFriction") = nullptr,
        arg("restitution") = nullptr,
        arg("density") = nullptr,
        R"(
            Adds physical material parameters to an existing Material.

            Used to apply ``UsdPhysics.MaterialAPI`` and related properties to an existing ``UsdShade.Material`` (e.g. a visual material).

            Note:
                When mixing visual and physical materials, be sure use both ``usdex.core.bindMaterial`` and ``usdex.core.bindPhysicsMaterial`` on the target geometry, to ensure the
                material is used in both rendering and simulation contexts.

            Args:
                material: The material to add the physics material parameters to
                dynamicFriction: The dynamic friction of the material
                staticFriction: The static friction of the material
                restitution: The restitution of the material
                density: The density of the material

            Returns:
                ``True`` if the physics material parameters were successfully added to the material, ``False`` otherwise.
        )"
    );

    m.def(
        "bindPhysicsMaterial",
        &bindPhysicsMaterial,
        arg("prim"),
        arg("material"),
        R"(
            Binds a physics material to a given rigid body or collision geometry.

            Validates both the prim and the material, applies the ``UsdShade.MaterialBindingAPI`` to the target prim,
            and binds the material to the target prim with the "physics" purpose.

            Note:
                The material is bound with the "physics" purpose, and with the default "fallback strength",
                meaning descendant prims can override with a different material. If alternate behavior is desired,
                use the ``UsdShade.MaterialBindingAPI`` directly.

            Note:
                We cannot bind materials to prims across different instance boundaries.
                This function returns an error if ``prim`` and ``material`` are not placed in an editable location.

            Args:
                prim: The prim to bind the material to
                material: The physics material to bind to the prim

            Returns:
                ``True`` if the material was successfully bound to the target prim, ``False`` otherwise.
        )"
    );
}

} // namespace usdex::core::bindings
