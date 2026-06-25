// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#include "usdex/core/PrimvarData.h"

namespace usdex::core
{

// explicitly instantiate each of the types we defined in the public header.
template class PrimvarData<float>;
template class PrimvarData<int64_t>;
template class PrimvarData<int>;
template class PrimvarData<std::string>;
template class PrimvarData<pxr::TfToken>;
template class PrimvarData<pxr::GfVec2f>;
template class PrimvarData<pxr::GfVec3f>;

FloatPrimvarData createConstantPrimvar(pxr::UsdPrim prim, const std::string& name, float value, const pxr::SdfValueTypeName& valueTypeName)
{
    return detail::createConstantPrimvarImpl(prim, name, value, valueTypeName);
}

Int64PrimvarData createConstantPrimvar(pxr::UsdPrim prim, const std::string& name, int64_t value, const pxr::SdfValueTypeName& valueTypeName)
{
    return detail::createConstantPrimvarImpl(prim, name, value, valueTypeName);
}

IntPrimvarData createConstantPrimvar(pxr::UsdPrim prim, const std::string& name, int value, const pxr::SdfValueTypeName& valueTypeName)
{
    return detail::createConstantPrimvarImpl(prim, name, value, valueTypeName);
}

StringPrimvarData createConstantPrimvar(
    pxr::UsdPrim prim,
    const std::string& name,
    const std::string& value,
    const pxr::SdfValueTypeName& valueTypeName
)
{
    return detail::createConstantPrimvarImpl(prim, name, value, valueTypeName);
}

TokenPrimvarData createConstantPrimvar(
    pxr::UsdPrim prim,
    const std::string& name,
    const pxr::TfToken& value,
    const pxr::SdfValueTypeName& valueTypeName
)
{
    return detail::createConstantPrimvarImpl(prim, name, value, valueTypeName);
}

Vec2fPrimvarData createConstantPrimvar(
    pxr::UsdPrim prim,
    const std::string& name,
    const pxr::GfVec2f& value,
    const pxr::SdfValueTypeName& valueTypeName
)
{
    return detail::createConstantPrimvarImpl(prim, name, value, valueTypeName);
}

Vec3fPrimvarData createConstantPrimvar(
    pxr::UsdPrim prim,
    const std::string& name,
    const pxr::GfVec3f& value,
    const pxr::SdfValueTypeName& valueTypeName
)
{
    return detail::createConstantPrimvarImpl(prim, name, value, valueTypeName);
}

} // namespace usdex::core
