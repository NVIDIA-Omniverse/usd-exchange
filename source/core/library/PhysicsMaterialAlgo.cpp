// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "usdex/core/PhysicsMaterialAlgo.h"

#include "usdex/core/StageAlgo.h"

#include <pxr/usd/usdPhysics/materialAPI.h>
#include <pxr/usd/usdPhysics/tokens.h>
#include <pxr/usd/usdShade/materialBindingAPI.h>

#include <optional>

using namespace pxr;

UsdShadeMaterial usdex::core::definePhysicsMaterial(
    UsdStagePtr stage,
    const SdfPath& path,
    const float dynamicFriction,
    const std::optional<float> staticFriction,
    const std::optional<float> restitution,
    const std::optional<float> density
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(stage, path, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial due to an invalid location: %s", reason.c_str());
        return UsdShadeMaterial();
    }

    auto material = UsdShadeMaterial::Define(stage, path);
    if (!material)
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial at \"%s\"", path.GetAsString().c_str());
        return UsdShadeMaterial();
    }

    // Explicitly author the specifier and type name
    UsdPrim prim = material.GetPrim();
    prim.SetSpecifier(SdfSpecifierDef);
    prim.SetTypeName(prim.GetTypeName());

    if (!usdex::core::addPhysicsToMaterial(material, dynamicFriction, staticFriction, restitution, density))
    {
        TF_RUNTIME_ERROR("Unable to add physics material parameters to material at \"%s\"", path.GetAsString().c_str());
        return UsdShadeMaterial();
    }

    return material;
}

UsdShadeMaterial usdex::core::definePhysicsMaterial(
    UsdPrim parent,
    const std::string& name,
    const float dynamicFriction,
    const std::optional<float> staticFriction,
    const std::optional<float> restitution,
    const std::optional<float> density
)
{
    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(parent, name, &reason))
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial due to an invalid location: %s", reason.c_str());
        return UsdShadeMaterial();
    }

    auto stage = parent.GetStage();
    const SdfPath path = parent.GetPath().AppendChild(TfToken(name));
    return usdex::core::definePhysicsMaterial(stage, path, dynamicFriction, staticFriction, restitution, density);
}

UsdShadeMaterial usdex::core::definePhysicsMaterial(
    UsdPrim prim,
    const float dynamicFriction,
    const std::optional<float> staticFriction,
    const std::optional<float> restitution,
    const std::optional<float> density
)
{
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to define UsdShadeMaterial on invalid prim");
        return UsdShadeMaterial();
    }

    auto stage = prim.GetStage();
    const SdfPath path = prim.GetPath();
    return usdex::core::definePhysicsMaterial(stage, path, dynamicFriction, staticFriction, restitution, density);
}

bool usdex::core::addPhysicsToMaterial(
    UsdShadeMaterial& material,
    const float dynamicFriction,
    const std::optional<float> staticFriction,
    const std::optional<float> restitution,
    std::optional<float> density
)
{
    auto prim = material.GetPrim();
    if (!prim)
    {
        TF_RUNTIME_ERROR("Unable to add physics material parameters to invalid material");
        return false;
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to add physics material parameters to invalid prim: %s", reason.c_str());
        return false;
    }

    // Specify the parameters of the Physics Material.
    auto materialAPI = UsdPhysicsMaterialAPI::Apply(prim);

    materialAPI.GetDynamicFrictionAttr().Set(dynamicFriction);
    if (staticFriction.has_value())
    {
        materialAPI.GetStaticFrictionAttr().Set(staticFriction.value());
    }
    if (restitution.has_value())
    {
        materialAPI.GetRestitutionAttr().Set(restitution.value());
    }
    if (density.has_value())
    {
        materialAPI.GetDensityAttr().Set(density.value());
    }

    return true;
}

bool usdex::core::bindPhysicsMaterial(UsdPrim prim, const UsdShadeMaterial& material)
{
    if (!prim || !material)
    {
        TF_RUNTIME_ERROR("Unable to bind physics material to invalid prim or material");
        return false;
    }

    // Early out if the proposed prim location is invalid
    std::string reason;
    if (!usdex::core::isEditablePrimLocation(prim, &reason))
    {
        TF_RUNTIME_ERROR("Unable to bind material to invalid prim: %s", reason.c_str());
        return false;
    }

    auto materialBindingAPI = UsdShadeMaterialBindingAPI::Apply(prim);
    if (!materialBindingAPI.Bind(material, UsdShadeTokens->fallbackStrength, TfToken("physics")))
    {
        TF_RUNTIME_ERROR("Unable to bind physics material to prim: %s", prim.GetPath().GetAsString().c_str());
        return false;
    }

    return true;
}
