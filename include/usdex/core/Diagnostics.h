// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/core/Diagnostics.h
//! @brief Specialized handling of OpenUSD `TfDiagnostic` messages (logs).

#include "usdex/core/Api.h"

#include <pxr/base/tf/diagnosticLite.h>
#include <pxr/base/tf/diagnosticMgr.h>

namespace usdex::core
{

//! @defgroup diagnostics Diagnostic Messages (Logs)
//!
//! Specialized handling of OpenUSD `TfDiagnostic` messages (logs).
//!
//! The `Tf` module from OpenUSD provides various diagnostic logging abilities, including the ability to override the default message handler
//! (which prints to `stderr`) with one or more custom handlers.
//!
//! These functions can be used to control a specialized `TfDiagnosticMgr::Delegate` provided by OpenUSD Exchange. The primary advantages
//! of this `Delegate` are:
//!
//! - Diagnostics can be filtered by `DiagnosticsLevel`.
//! - Diagnostics can be redirected to `stdout`, `stderr`, or muted entirely using `DiagnosticsOutputStream`.
//! - The message formatting is friendlier to end-users.
//!
//! @note Use of this `Delegate` is entirely optional and it is not activated by default when loading this module. To active it, client code
//! must explicitly call `activateDiagnosticsDelegate()`. This is to allow clients to opt-in and to prevent double printing for clients
//! that already have their own `TfDiagnosticMgr::Delegate` implementation.
//!
//! @{

//! Controls the diagnostics that will be emitted when the `Delegate` is active.
enum class DiagnosticsLevel
{
    eFatal = 0, //!< Only `TF_FATAL` are emitted.
    eError, //!< Emit `TF_ERROR` and `TF_FATAL`, but suppress `TF_WARN` and `TF_STATUS` diagnostics.
    eWarning, //!< Emit `TF_WARN`, `TF_ERROR`, and `TF_FATAL`, but suppress `TF_STATUS` diagnostics.
    eStatus //!< All diagnostics are emitted.
};

//! Control the output stream to which diagnostics are logged.
enum class DiagnosticsOutputStream
{
    eNone = 0, //!< All diagnostics are suppressed.
    eStdout, //!< All diagnostics print to the `stdout` stream.
    eStderr //!< All diagnostics print to the `stderr` stream.
};

//! Test whether the `Delegate` is currently active.
//!
//! When active, the `Delegate` replaces the default `TfDiagnosticMgr` printing with a more customized result.
//! See @ref diagnostics for more details.
//!
//! @returns Whether the `Delegate` is active
USDEX_API bool isDiagnosticsDelegateActive();

//! Activates the `Delegate` to specialize `TfDiagnostics` handling.
//!
//! When active, the `Delegate` replaces the default `TfDiagnosticMgr` printing with a more customized result.
//! See @ref diagnostics for more details.
//!
//! @note The delegate is not active when this module loads. Clients must explicitly call this function to activate it.
//! @returns `void`
USDEX_API void activateDiagnosticsDelegate();

//! Deactivates the `Delegate` to restore default `TfDiagnostics` handling.
//!
//! When deactivated, the default `TfDiagnosticMgr` printing is restored, unless some other `Delegate` is still active.
//! See @ref diagnostics for more details.
//! @returns `void`
USDEX_API void deactivateDiagnosticsDelegate();

//! Set the `DiagnosticsLevel` for the `Delegate` to filter `TfDiagnostics` by severity.
//!
//! This can be called at any time, but the filtering will only take affect after calling `activateDiagnosticsDelegate()`.
//! See @ref diagnostics for more details.
//!
//! @param value The highest severity `DiagnosticsLevel` that should be emitted.
//! @returns `void`
USDEX_API void setDiagnosticsLevel(DiagnosticsLevel value);

//! Get the current `DiagnosticsLevel` for the `Delegate`.
//!
//! This can be called at any time, but the filtering will only take affect after calling `activateDiagnosticsDelegate()`.
//! See @ref diagnostics for more details.
//!
//! @returns The current `DiagnosticsLevel` for the `Delegate`.
USDEX_API DiagnosticsLevel getDiagnosticsLevel();

//! Get the `DiagnosticsLevel` for a given `TfDiagnosticType`.
//!
//! @param code The `TfDiagnosticType` to get the `DiagnosticsLevel` for.
//! @returns The `DiagnosticsLevel` for the `TfDiagnosticType`.
USDEX_API DiagnosticsLevel getDiagnosticLevel(pxr::TfDiagnosticType code);

//! Set the `DiagnosticsOutputStream` for the `Delegate` to redirect `TfDiagnostics` to different streams.
//!
//! This can be called at any time, but will only take affect after calling `activateDiagnosticsDelegate()`.
//! See @ref diagnostics for more details.
//!
//! @param value The stream to which all diagnostics should be emitted.
//! @returns `void`
USDEX_API void setDiagnosticsOutputStream(DiagnosticsOutputStream value);

//! Get the current `DiagnosticsOutputStream` for the `Delegate`.
//!
//! This can be called at any time, but will only take affect after calling `activateDiagnosticsDelegate()`.
//! See @ref diagnostics for more details.
//!
//! @returns The current `DiagnosticsOutputStream` for the `Delegate`.
USDEX_API DiagnosticsOutputStream getDiagnosticsOutputStream();

//! }@

} // namespace usdex::core
