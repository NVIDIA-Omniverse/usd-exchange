// SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#include "Transcoding.h"

#include <pxr/base/tf/stringUtils.h>
#include <pxr/base/tf/unicodeUtils.h>

#include <algorithm>
#include <array>
#include <functional>
#include <iostream>
#include <limits>
#include <optional>
#include <random>
#include <tuple>
#include <unordered_set>
#include <vector>

PXR_NAMESPACE_USING_DIRECTIVE

namespace
{
// Types

//! To represent values from 0 to 0x3D
using base62_t = unsigned char;

//! To represent values from 0 to 0x10FFFF
using code_t = uint32_t;

// Constants

constexpr int BASE62 = 62;

constexpr char BOOTSTRING_DELIMITER = '_';

constexpr base62_t BOOTSTRING_THRESHOLD = 31;

constexpr code_t MAX_CODE_POINT = 0x10FFFF;

//! A bootstring prefix which is also a valid ASCII/XID start
constexpr std::string_view BOOTSTRING_PREFIX = "tn__";


// Base62

//! Encodes a base62_t value into a character.
char encodeBase62(const base62_t digit)
{
    if (digit <= 9)
    {
        return static_cast<char>(digit + '0');
    }
    else if (digit >= 10 && digit <= 35)
    {
        return static_cast<char>(digit - 10 + 'A');
    }
    else
    { // (digit >= 36 && digit <= 61)
        return static_cast<char>(digit - 36 + 'a');
    }
}

//! Decodes a base62 character into its numeric form
//! Returns negative if character is not one of base62 characters.
base62_t decodeBase62(const char character)
{
    if (character >= '0' && character <= '9')
    {
        return static_cast<base62_t>(character - '0');
    }
    else if (character >= 'A' && character <= 'Z')
    {
        return static_cast<base62_t>(character - 'A' + 10);
    }
    else if (character >= 'a' && character <= 'z')
    {
        return static_cast<base62_t>(character - 'a' + 36);
    }
    else
    {
        return BASE62 + 1;
    }
}

//! A Fenwick tree or binary indexed tree (BIT) is a data structure that can efficiently
//! update values and calculate prefix sums in an array of values.
struct BinaryIndexedTree
{
    std::vector<size_t> tree;
    size_t most_significant_bit;

    BinaryIndexedTree(const size_t n) : tree(n + 1, 0), most_significant_bit(0)
    {
        size_t v = n + 1;
        while (v >>= 1)
        {
            ++most_significant_bit;
        }
    }

    //! Increase index `i` by 1
    void increase(const size_t i)
    {
        for (size_t idx = i + 1; idx < tree.size(); idx += (idx & (0 - idx)))
        {
            ++tree[idx];
        }
    }

    //! Decrease index `i` by 1
    void decrease(const size_t i)
    {
        for (size_t idx = i + 1; idx < tree.size(); idx += (idx & (0 - idx)))
        {
            --tree[idx];
        }
    }

    //! Increase all indices by 1. It is faster than calling N times `increase`.
    void increaseAll()
    {
        for (size_t i = 0; i < tree.size() - 1; i++)
        {
            ++tree[i + 1];

            size_t idx = i + 1;
            idx += (idx & (0 - idx));
            if (idx < tree.size())
            {
                tree[idx] += tree[i + 1];
            }
        }
    }

    //! Return the sum of all values from 0 to `i` (included).
    size_t sum(const size_t i) const
    {
        size_t sum = 0;
        for (size_t idx = i + 1; idx > 0; idx -= (idx & (0 - idx)))
        {
            sum += tree[idx];
        }
        return sum;
    }

    //! Reverse operation to `sum`, i.e. return the first index whose sum is `sum`.
    std::optional<size_t> lower(size_t sum) const
    {
        size_t idx = 0;
        size_t bitmask = static_cast<size_t>(1) << most_significant_bit;
        while (bitmask > 0)
        {
            const size_t current = idx | bitmask;
            bitmask >>= 1;
            if (current < tree.size() && tree[current] < sum)
            {
                idx = current;
                sum -= tree[current];
            }
        }
        if (sum > 1)
        {
            return std::nullopt;
        }
        return idx;
    }
};

// Format functions

/// Equivalent to TfIsUtf8CodePointXidStart, but for ASCII characters.
bool IsASCIIStart(const uint32_t value)
{
    return ((value >= 'A' && value <= 'Z') || (value == '_') || (value >= 'a' && value <= 'z'));
}

/// Equivalent to TfIsUtf8CodePointXidContinue, but for ASCII characters.
bool IsASCIIContinue(const uint32_t value)
{
    return ((value >= '0' && value <= '9') || (value >= 'A' && value <= 'Z') || (value == '_') || (value >= 'a' && value <= 'z'));
}

bool IsStart(const TfUtf8CodePoint value, const usdex::core::detail::TranscodingFormat format)
{
    if (format == usdex::core::detail::TranscodingFormat::ASCII)
    {
        return IsASCIIStart(value.AsUInt32());
    }
    else if (format == usdex::core::detail::TranscodingFormat::UTF8_XID)
    {
        return IsASCIIStart(value.AsUInt32()) || TfIsUtf8CodePointXidStart(value);
    }
    return false;
}

bool IsContinue(const TfUtf8CodePoint value, const usdex::core::detail::TranscodingFormat format)
{
    if (format == usdex::core::detail::TranscodingFormat::ASCII)
    {
        return IsASCIIContinue(value.AsUInt32());
    }
    else if (format == usdex::core::detail::TranscodingFormat::UTF8_XID)
    {
        return TfIsUtf8CodePointXidContinue(value);
    }
    return false;
}

// Bootstring

//! Encodes variable length integers `number` and appends it to string `out`.
void encodeVariableLength(std::ostringstream& oss, uint64_t number)
{
    base62_t threshold = BOOTSTRING_THRESHOLD;
    while (number >= threshold)
    {
        const base62_t digit = threshold + static_cast<base62_t>((number - threshold) % (BASE62 - threshold));
        oss << encodeBase62(digit);
        number = (number - threshold) / (BASE62 - threshold);
    }
    // number < threshold
    oss << encodeBase62(static_cast<base62_t>(number));
}

//! Decodes variable length integers starting at index.
//! Returns false if:
//! - while decoding we run out of indices.
//! - the characters do not belong to base62.
std::optional<uint64_t> decodeVariableLength(TfUtf8CodePointIterator& it)
{
    uint64_t number = 0;
    uint64_t weight = 1;
    base62_t threshold = BOOTSTRING_THRESHOLD;
    while (true)
    {
        if (it == TfUtf8CodePointIterator::PastTheEndSentinel{})
        {
            // Out of index.
            return std::nullopt;
        }
        const code_t codePoint = (*it).AsUInt32();
        if (codePoint > MAX_CODE_POINT)
        {
            // Out of value
            return std::nullopt;
        }
        const char character = static_cast<char>(codePoint);
        ++it;
        const base62_t digit = decodeBase62(character);
        if (digit > BASE62)
        {
            // Invalid character.
            return std::nullopt;
        }
        if (digit > (std::numeric_limits<uint64_t>::max() - number) / weight)
        {
            // Overflow
            return std::nullopt;
        }
        number += digit * weight;
        if (digit < threshold)
        {
            break;
        }
        if (weight > std::numeric_limits<uint64_t>::max() / (BASE62 - threshold))
        {
            // Overflow
            return std::nullopt;
        }
        weight *= (BASE62 - threshold);
    }
    return number;
}

std::optional<std::string> encodeBootstring(const std::string& inputString, const usdex::core::detail::TranscodingFormat format)
{
    std::ostringstream oss;
    size_t numberCodePoints = 0;
    for (const TfUtf8CodePoint value : TfUtf8CodePointView{ inputString })
    {
        if (value == TfUtf8InvalidCodePoint)
        {
            return std::nullopt;
        }
        if (IsContinue(value, format))
        {
            oss << TfUtf8CodePoint(value);
        }
        ++numberCodePoints;
    }

    if (oss.tellp() > 0)
    {
        oss << BOOTSTRING_DELIMITER;
    }

    BinaryIndexedTree tree(numberCodePoints);
    std::vector<std::tuple<uint32_t, size_t>> extendedCodes;
    size_t encodedPoints = 0;
    {
        size_t codePosition = 0;
        for (const TfUtf8CodePoint value : TfUtf8CodePointView{ inputString })
        {
            if (IsContinue(value, format))
            {
                tree.increase(codePosition);
                ++encodedPoints;
            }
            else
            {
                extendedCodes.emplace_back(value.AsUInt32(), codePosition);
            }
            ++codePosition;
        }
    }
    std::sort(extendedCodes.begin(), extendedCodes.end());

    code_t prevCodePoint = 0;
    for (const auto& it : extendedCodes)
    {
        const code_t codePoint = std::get<0>(it);
        const size_t codePosition = std::get<1>(it);

        uint64_t delta = tree.sum(codePosition);
        if (codePoint - prevCodePoint > (std::numeric_limits<uint64_t>::max() - delta) / (encodedPoints + 1))
        {
            // Overflow
            return std::nullopt;
        }
        delta += (codePoint - prevCodePoint) * (encodedPoints + 1);
        encodeVariableLength(oss, delta);
        prevCodePoint = codePoint;

        tree.increase(codePosition);
        ++encodedPoints;
    }

    return oss.str();
}

std::optional<std::string> decodeBootstring(const std::string& inputString)
{
    size_t delimiterPosition = 0;
    {
        size_t position = 0;
        for (const TfUtf8CodePoint value : TfUtf8CodePointView{ inputString })
        {
            if (value == TfUtf8InvalidCodePoint)
            {
                return std::nullopt;
            }
            if (value == TfUtf8CodePointFromAscii(BOOTSTRING_DELIMITER))
            {
                delimiterPosition = position;
            }
            ++position;
        }
    }

    std::vector<std::tuple<uint32_t, size_t>> values;
    {
        auto it = TfUtf8CodePointView{ inputString }.begin();
        if (delimiterPosition > 0)
        {
            size_t position = 0;
            for (; it != TfUtf8CodePointIterator::PastTheEndSentinel{};)
            {
                values.emplace_back((*it).AsUInt32(), position);
                ++it;
                ++position;
                if (position == delimiterPosition)
                {
                    break;
                }
            }
            ++it; // skip delimiter
        }

        size_t decodedPoints = values.size();
        code_t codePoint = 0;
        for (; it != TfUtf8CodePointIterator::PastTheEndSentinel{};)
        {
            const std::optional<uint64_t> ret = decodeVariableLength(it);
            if (!ret)
            {
                // Could not decode variable-length integer.
                return std::nullopt;
            }
            const uint64_t value = *ret;
            codePoint += (code_t)(value / (decodedPoints + 1));
            const size_t position = value % (decodedPoints + 1);

            ++decodedPoints;
            values.emplace_back(codePoint, position);
        }
    }

    BinaryIndexedTree tree(values.size());
    tree.increaseAll();
    std::vector<uint32_t> codePoints(values.size());
    for (auto it = values.rbegin(); it != values.rend(); ++it)
    {
        const code_t value = std::get<0>(*it);
        const size_t position = std::get<1>(*it);
        const std::optional<size_t> ret = tree.lower(position + 1);
        if (!ret)
        {
            return std::nullopt;
        }
        const size_t index = *ret;
        codePoints[index] = value;
        tree.decrease(index);
    }
    std::ostringstream oss;
    for (const auto codePoint : codePoints)
    {
        oss << TfUtf8CodePoint(codePoint);
    }
    return oss.str();
}
} // namespace

std::string usdex::core::detail::encodeIdentifier(const std::string& inputString, const usdex::core::detail::TranscodingFormat format)
{
    std::optional<std::string> ret = encodeBootstring(inputString, format);
    if (!ret)
    {
        // Invalid input string, returns empty.
        return "";
    }
    const std::string& output = *ret;
    std::string result;
    result.append(BOOTSTRING_PREFIX);
    result.append(output);
    if (output == inputString + BOOTSTRING_DELIMITER) // i.e. unchanged.
    {
        const auto it = TfUtf8CodePointView{ inputString }.begin();
        if (IsStart(*it, format))
        {
            return inputString;
        }
        else
        {
            return result;
        }
    }
    return result;
}

std::string usdex::core::detail::decodeIdentifier(const std::string& inputString)
{
    if (inputString.substr(0, 4) == BOOTSTRING_PREFIX)
    {
        const std::string substr = inputString.substr(4, inputString.size() - 1);
        const std::optional<std::string> ret = decodeBootstring(substr);
        if (!ret)
        {
            // Invalid input string, returns same string.
            return inputString;
        }
        return *ret;
    }
    return inputString;
}
