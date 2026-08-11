// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include <usdex/core/Core.h>
#include <usdex/core/Feature.h>
#include <usdex/core/Version.h>

#include <doctest/doctest.h>

#include <string>

TEST_CASE("Version and Features")
{
    CHECK(std::string(usdex::core::version()) == USDEX_VERSION_STRING);
    CHECK(std::string(usdex::core::buildVersion()) == USDEX_BUILD_STRING);
    CHECK(usdex::core::withPython() == USDEX_WITH_PYTHON);
}
