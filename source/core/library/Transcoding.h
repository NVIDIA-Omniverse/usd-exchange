// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include <string>


namespace usdex::core::detail
{

//! Encoding algorithm produces different output depending on Format.
enum class TranscodingFormat
{
    //! The identifier is composed only of alphanumerics characters and underscore.
    ASCII,

    //! The identifier is composed of UTF-8 non-control characters.
    UTF8_XID
};

//! Encodes an identifier using the Bootstring algorithm.
//! For more information see [Encoding
//! Procedure](https://github.com/PixarAnimationStudios/OpenUSD-proposals/tree/main/proposals/transcoding_invalid_identifiers#encoding-procedure)
//!
//! @param inputString The input string
//! @param format The format to apply in transcoding
std::string encodeIdentifier(const std::string& inputString, const TranscodingFormat format);

//! Decodes an identifier using the Bootstring algorithm.
//! For more information see [Decoding
//! Procedure](https://github.com/PixarAnimationStudios/OpenUSD-proposals/tree/main/proposals/transcoding_invalid_identifiers#decoding-procedure)
//!
//! @param inputString The input string
std::string decodeIdentifier(const std::string& inputString);

} // namespace usdex::core::detail
