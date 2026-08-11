// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "usdex/core/Core.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;

namespace usdex::core::bindings
{

void bindCore(module& m)
{
    m.def(
        "version",
        &version,
        R"(
            Verify the expected usdex modules are being loaded at runtime.

            Returns:
                A human-readable version string for the usdex modules.
        )"
    );

    m.def(
        "buildVersion",
        &buildVersion,
        R"(
            Verify the expected usdex modules are being loaded at runtime.

            Returns:
                A human-readable build version string for the usdex modules.
        )"
    );
}

} // namespace usdex::core::bindings
