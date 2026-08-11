// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "MaterialAlgoBindings.h"

using namespace usdex::rtx::bindings;
using namespace pybind11;

namespace
{

PYBIND11_MODULE(_usdex_rtx, m)
{
    bindMaterialAlgo(m);
}

} // namespace
