// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "TfUtils.h"

#include "usdex/core/Settings.h"

#include "Debug.h"
#include "Transcoding.h"

namespace
{

// Alternate implementation of TfMakeValidIdentifier
std::string makeValidIdentifierExtended(const std::string& in)
{
    std::string result;

    if (in.empty())
    {
        result.push_back('_');
        return result;
    }

    char const* p = in.c_str();

    // This is where this function deviates from TfMakeValidIdentifier
    // For a numeric first character we push back "_[0-9]" rather than just "_"
    // This reduces the number of avoidable name collisions generated as a result of name validation
    if (('0' <= *p && *p <= '9'))
    {
        result.reserve(in.size() + 1);
        result.push_back('_');
        result.push_back(*p);
    }
    else
    {
        result.reserve(in.size());
        if (!(('a' <= *p && *p <= 'z') || ('A' <= *p && *p <= 'Z') || *p == '_'))
        {
            result.push_back('_');
        }
        else
        {
            result.push_back(*p);
        }
    }

    for (++p; *p; ++p)
    {
        if (!(('a' <= *p && *p <= 'z') || ('A' <= *p && *p <= 'Z') || ('0' <= *p && *p <= '9') || *p == '_'))
        {
            result.push_back('_');
        }
        else
        {
            result.push_back(*p);
        }
    }

    return result;
}

} // namespace

std::string usdex::core::detail::makeValidIdentifier(const std::string& in)
{
    static bool s_enableTranscoding = TfGetEnvSetting(USDEX_ENABLE_TRANSCODING);
    if (s_enableTranscoding)
    {
        std::string out = usdex::core::detail::encodeIdentifier(in, usdex::core::detail::TranscodingFormat::ASCII);
        if (out.empty())
        {
            // It is possible that the encoding fails, in which case we should fall back to replacing invalid characters.
            TF_INFO(USDEX_TRANSCODING_ERROR).Msg("Boot string encoding of \"%s\" failed. Resorting to character substitution.\n", in.c_str());
            return makeValidIdentifierExtended(in);
        }
        else
        {
            return out;
        }
    }
    else
    {
        return makeValidIdentifierExtended(in);
    }
}
