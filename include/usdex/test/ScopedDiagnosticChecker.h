// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/test/ScopedDiagnosticChecker.h
//! @brief A scoped class to capture and assert expected `TfDiagnostics` and `TfErrorMarks` for use in a `doctest` suite.

#include <usdex/core/Diagnostics.h>

#include <pxr/base/tf/diagnosticMgr.h>
#include <pxr/base/tf/enum.h>
#include <pxr/base/tf/errorMark.h>
#include <pxr/usd/usdUtils/coalescingDiagnosticDelegate.h>

#include <doctest/doctest.h>

#include <regex>

//! @brief [usdex::test](https://docs.omniverse.nvidia.com/usd/code-docs/usd-exchange-sdk) provides [doctest](https://github.com/doctest/doctest)
//! based test utilities for validating in-memory [OpenUSD](https://openusd.org/release/index.html) data for consistency and correctness.
namespace usdex::test
{

//! @defgroup doctest Test USD Authoring within doctest test suites.
//!
//! In C++ `usdex::test` uses the [doctest](https://github.com/doctest/doctest) testing framework. The utility classes and functions
//! within this group use doctest commands in their implementations directly and as such are expected to be used within a running doctest
//! context.
//!
//! @{

//! A scoped class to capture and assert expected `TfDiagnostics` and `TfErrorMarks` for use in a `doctest` suite.
//!
//! Construct a `ScopedDiagnosticChecker` and a list of expected diagnostic messages.
//!
//! Each `DiagnosticPattern` must contain:
//!     - One `TfDiagnosticType` (e.g `TF_DIAGNOSTIC_STATUS_TYPE`)
//!     - A regex pattern matching the expected diagnostic commentary (message)
//!
//! On context exit, the `ScopedDiagnosticChecker` will assert that all expected `TfDiagnostics` and `TfErrorMarks` were emmitted.
//!
//! @note `TfErrorMarks` will be diagnosed before any general `TfDiagnostics`. The supplied list of expected values should account for this.
//!
//! Example:
//!
//!     #include <usdex/test/ScopedDiagnosticChecker.h>
//!     #include <pxr/base/tf/diagnostic.h>
//!
//!     #define DOCTEST_CONFIG_IMPLEMENTATION_IN_DLL
//!     #include <doctest/doctest.h>
//!
//!     using namespace pxr;
//!
//!     TEST_CASE("My Test Case")
//!     {
//!         {
//!             usdex::test::ScopedDiagnosticChecker check({ { TF_DIAGNOSTIC_WARNING_TYPE, ".*foo" } });
//!             TF_WARN("This message ends in foo");
//!         }
//!     }
class ScopedDiagnosticChecker
{

public:

    //! A vector of expected `TfDiagnosticTypes` and `std::regex` compliant match patterns.
    using DiagnosticPatterns = std::vector<std::pair<pxr::TfEnum, std::string>>;

    //! Construct a default `ScopedDiagnosticChecker` to assert that no `TfDiagnostics` or `TfErrorMarks` are emitted.
    ScopedDiagnosticChecker() = default;

    //! Construct a `ScopedDiagnosticChecker` with a vector of expected `DiagnosticPattern` pairs.
    ScopedDiagnosticChecker(DiagnosticPatterns expected) : m_expected{ std::move(expected) }
    {
        // disable the usdex output stream
        m_originalOutputStream = usdex::core::getDiagnosticsOutputStream();
        usdex::core::setDiagnosticsOutputStream(usdex::core::DiagnosticsOutputStream::eNone);
    };

    //! On destruction the `ScopedDiagnosticChecker` will assert the expected `TfDiagnostics` and `TfErrorMarks` were emitted using doctest `CHECK`
    ~ScopedDiagnosticChecker()
    {
        auto diagnostics = m_delegate.TakeUncoalescedDiagnostics();

        if (m_expected.empty())
        {
            CHECK(m_errors.IsClean());
            CHECK(diagnostics.size() == 0);
        }
        else if (diagnostics.size() != m_expected.size())
        {
            CHECK(!m_errors.IsClean());
        }

        size_t i = 0;
        for (const pxr::TfError& error : m_errors)
        {
            CHECK(i < m_expected.size());
            if (i >= m_expected.size())
            {
                return;
            }
            CHECK(error.GetErrorCode() == m_expected[i].first);
            CHECK_MESSAGE(
                std::regex_match(error.GetCommentary(), std::regex(m_expected[i].second)),
                pxr::TfStringPrintf("\n\tPattern: %s\n\tCommentary: %s", m_expected[i].second.c_str(), error.GetCommentary().c_str())
            );
            ++i;
        }

        for (auto& diagnostic : diagnostics)
        {
            CHECK(i < m_expected.size());
            if (i >= m_expected.size())
            {
                return;
            }
            CHECK(diagnostic->GetDiagnosticCode() == m_expected[i].first);
            CHECK_MESSAGE(
                std::regex_match(diagnostic->GetCommentary(), std::regex(m_expected[i].second)),
                pxr::TfStringPrintf("\n\tPattern: %s\n\tCommentary: %s", m_expected[i].second.c_str(), diagnostic->GetCommentary().c_str())
            );
            ++i;
        }

        // ensure we have found all expected diagnostics
        CHECK(i == m_expected.size());

        // dismiss the errors so they don't propagate to stderr
        m_errors.Clear();

        // restore the usdex output stream
        usdex::core::setDiagnosticsOutputStream(m_originalOutputStream);
    };

private:

    pxr::TfErrorMark m_errors;
    pxr::UsdUtilsCoalescingDiagnosticDelegate m_delegate;
    DiagnosticPatterns m_expected;
    usdex::core::DiagnosticsOutputStream m_originalOutputStream;
};

//! @}

} // namespace usdex::test
