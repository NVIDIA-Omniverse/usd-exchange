// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/core/Core.h
//! @brief The main header for this library

#include "Api.h"

//! @brief [usdex::core](https://docs.omniverse.nvidia.com/usd/code-docs/usd-exchange-sdk) provides higher-level convenience functions on top of
//! lower-level [OpenUSD](https://openusd.org/release/index.html) concepts, so developers can quickly adopt OpenUSD best practices when mapping their
//! native data sources to OpenUSD-legible data models.
namespace usdex::core
{

//! @defgroup version Versioning sanity checks
//!
//! Utility functions to verify the expected library versions are being loaded at runtime.
//!
//! The format of the returned strings are not guaranteed to remain consistent from one version
//! to another, nor between the two functions, so please don't try to parse them. Instead, use
//! the macros in Version.h if you need to conditionally perform a version dependant operation.
//!
//! @{

//! Verify the expected usdex modules are being loaded at runtime.
//! @returns A human-readable version string for the usdex modules.
USDEX_API const char* version();

//! Verify the expected usdex modules are being loaded at runtime.
//! @returns A human-readable build version string for the usdex modules.
USDEX_API const char* buildVersion();

//! Verify whether Python support is available.
//! @returns A bool indicating whether Python support is available.
USDEX_API bool withPython();

/// @}


} // namespace usdex::core
