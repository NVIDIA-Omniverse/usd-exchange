// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/Diagnostics.h"

#include "usdex/pybind/UsdBindings.h"

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;

namespace usdex::core::bindings
{

void bindDiagnostics(module& m)
{
    pybind11::enum_<DiagnosticsLevel>(m, "DiagnosticsLevel", "Controls the diagnostics that will be emitted when the ``Delegate`` is active.")
        .value("eFatal", DiagnosticsLevel::eFatal, "Only ``Tf.Fatal`` are emitted.")
        .value("eError", DiagnosticsLevel::eError, "Emit ``Tf.Error`` and ``Tf.Fatal``, but suppress ``Tf.Warn`` and ``Tf.Status`` diagnostics.")
        .value("eWarning", DiagnosticsLevel::eWarning, "Emit ``Tf.Warn``, ``Tf.Error``, and ``Tf.Fatal``, but suppress ``Tf.Status`` diagnostics.")
        .value("eStatus", DiagnosticsLevel::eStatus, "All diagnostics are emitted.");

    pybind11::enum_<DiagnosticsOutputStream>(m, "DiagnosticsOutputStream", "Control the output stream to which diagnostics are logged.")
        .value("eNone", DiagnosticsOutputStream::eNone, "All diagnostics are suppressed.")
        .value("eStdout", DiagnosticsOutputStream::eStdout, "All diagnostics print to the ``stdout`` stream.")
        .value("eStderr", DiagnosticsOutputStream::eStderr, "All diagnostics print to the ``stderr`` stream.");

    m.def(
        "isDiagnosticsDelegateActive",
        &isDiagnosticsDelegateActive,
        R"(
            Test whether the ``Delegate`` is currently active.

            When active, the ``Delegate`` replaces the default ``TfDiagnosticMgr`` printing with a more customized result.
            See ``activateDiagnosticsDelegate()`` for more details.

            Returns:
                Whether the `Delegate` is active
        )"
    );

    m.def(
        "activateDiagnosticsDelegate",
        &activateDiagnosticsDelegate,
        R"(
            Activates the ``Delegate`` to specialize ``TfDiagnostics`` handling.

            The ``Tf`` module from OpenUSD provides various diagnostic logging abilities, including the ability to override the default message
            handler (which prints to ``stderr``) with one or more custom handlers.

            This function can be used to activate a specialized ``TfDiagnosticMgr::Delegate`` provided by OpenUSD Exchange. The primary advantages
            of this ``Delegate`` are:

            - Diagnostics can be filtered by ``DiagnosticsLevel``.
            - Diagnostics can be redirected to ``stdout``, ``stderr``, or muted entirely using ``DiagnosticsOutputStream``.
            - The message formatting is friendlier to end-users.

            Note:
                Use of this ``Delegate`` is entirely optional and it is not activated by default when loading this module. To active it, client code
                must explicitly call ``activateDiagnosticsDelegate()``. This is to allow clients to opt-in and to prevent double printing for clients
                that already have their own ``TfDiagnosticMgr::Delegate`` implementation.

            Returns:
                ``None``
        )"
    );

    m.def(
        "deactivateDiagnosticsDelegate",
        &deactivateDiagnosticsDelegate,
        R"(
            Deactivates the ``Delegate`` to restore default ``TfDiagnostics`` handling.

            When deactivated, the default ``TfDiagnosticMgr`` printing is restored, unless some other ``Delegate`` is still active.

            Returns:
                ``None``
        )"
    );

    m.def(
        "setDiagnosticsLevel",
        &setDiagnosticsLevel,
        arg("value"),
        R"(
            Set the ``DiagnosticsLevel`` for the ``Delegate`` to filter ``TfDiagnostics`` by severity.

            This can be called at any time, but the filtering will only take affect after calling ``activateDiagnosticsDelegate()``.

            Args:
                value: The highest severity ``DiagnosticsLevel`` that should be emitted.

            Returns:
                ``None``
        )"
    );

    m.def(
        "getDiagnosticsLevel",
        &getDiagnosticsLevel,
        R"(
            Get the current ``DiagnosticsLevel`` for the ``Delegate``.

            This can be called at any time, but the filtering will only take affect after calling ``activateDiagnosticsDelegate()``.

            Returns:
                The current ``DiagnosticsLevel`` for the ``Delegate``.
        )"
    );

    m.def(
        "getDiagnosticLevel",
        &getDiagnosticLevel,
        arg("code"),
        R"(
            Get the ``DiagnosticsLevel`` for a given ``TfDiagnosticType``.

            Args:
                code: The ``TfDiagnosticType`` to get the ``DiagnosticsLevel`` for.

            Returns:
                The ``DiagnosticsLevel`` for the ``TfDiagnosticType``.
        )"
    );

    m.def(
        "setDiagnosticsOutputStream",
        &setDiagnosticsOutputStream,
        arg("value"),
        R"(
            Set the ``DiagnosticsOutputStream`` for the ``Delegate`` to redirect ``Tf.Diagnostics`` to different streams.

            This can be called at any time, but will only take affect after calling ``activateDiagnosticsDelegate()``.

            Args:
                value: The stream to which all diagnostics should be emitted.

            Returns:
                ``None``
        )"
    );

    m.def(
        "getDiagnosticsOutputStream",
        &getDiagnosticsOutputStream,
        R"(
            Get the current ``DiagnosticsOutputStream`` for the ``Delegate``.

            This can be called at any time, but will only take affect after calling ``activateDiagnosticsDelegate()``.

            Returns:
                The current ``DiagnosticsOutputStream`` for the ``Delegate``.
        )"
    );
}

} // namespace usdex::core::bindings
