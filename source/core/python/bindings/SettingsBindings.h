// SPDX-FileCopyrightText: Copyright (c) 2022-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

#include "usdex/core/Settings.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;

namespace usdex::core::bindings
{

void bindSettings(module& m)
{
    m.attr("enableOmniTranscodingSetting") = USDEX_ENABLE_OMNI_TRANSCODING._name;
}

} // namespace usdex::core::bindings