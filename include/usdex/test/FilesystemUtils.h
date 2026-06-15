// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/test/FilesystemUtils.h
//! @brief Utilities for manipulating files and directories in test suites

#include <usdex/core/Api.h>
#include <usdex/core/Version.h>

#include <pxr/base/arch/defines.h>
#include <pxr/base/tf/fileUtils.h>
#include <pxr/base/tf/stringUtils.h>

#if defined(ARCH_OS_WINDOWS)
#pragma warning(push)
#pragma warning(disable : 4245) // 'initializing': conversion from 'int' to 'size_t'
#include <pxr/base/arch/fileSystem.h>
#pragma warning(pop)
#else
#include <pxr/base/arch/fileSystem.h>
#endif

#include <regex>
#include <string>

namespace usdex::test
{

//! @addtogroup doctest
//! @{

//! A scoped class for creating a temporary directory & tearing it down on destruction
class ScopedTmpDir
{

public:

    //! Create a unique temporary subdirectory within the platform standard temp directory.
    ScopedTmpDir()
    {
        // Sanitize Version string
        std::string versionString = std::regex_replace(USDEX_BUILD_STRING, std::regex("[^A-Za-z0-9_-]"), "_");
        std::string prefix = pxr::TfStringPrintf("usdex_%s", versionString.c_str());
        m_path = pxr::ArchMakeTmpSubdir(pxr::ArchNormPath(pxr::ArchGetTmpDir()), prefix);
    }

    //! Delete the temporary subdirectory and all files within it.
    ~ScopedTmpDir()
    {
        pxr::TfRmTree(m_path);
    }

    //! Return the full path of the temporary subdirectory.
    const char* getPath()
    {
        return m_path.c_str();
    }

private:

    std::string m_path;
};

//! Compare identifiers (such as those returned by `SdfLayer::GetIdentifier()`).
//!
//! This function accounts for some platform specific behavior that occurs when resolving identifiers.
inline bool compareIdentifiers(const std::string& first, const std::string& second)
{
    return pxr::ArchNormPath(first) == pxr::ArchNormPath(second);
}

//! @}

} // namespace usdex::test
