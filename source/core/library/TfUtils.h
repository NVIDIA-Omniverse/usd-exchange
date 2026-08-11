// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include <string>

namespace usdex::core::detail
{

//! Produce a valid identifier from `in` by replacing invalid characters with "_".
//!
//! This function differs from pxr::TfMakeValidIdentifier in how it handles numeric characters at the start of the value.
//! Rather than replacing the character with an "_" this function will add an "_" prefix.
//!
//! @param in The input value
//! @returns A string that is considered valid for use as an identifier.
std::string makeValidIdentifier(const std::string& in);

} // namespace usdex::core::detail
