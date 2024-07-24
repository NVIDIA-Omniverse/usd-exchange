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

//! @file usdex/core/Core.h
//! @brief The main header for this library

#include "Api.h"

//! @brief The namespace for the OpenUSD Exchange SDK Core Library.
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

//! Verify whether Python support is available.
//! @returns A bool indicating whether Python support is available.
USDEX_API bool withPython();

/// @}


} // namespace usdex::core
