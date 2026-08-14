<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Diagnostics and Testing

`SKILL.md` (rules) is in context. Covers the SDK's diagnostic delegate, `TF_DEBUG`, the `usdex.test` Python module, `usdex/test/*.h` C++ utilities, and [USD Validation](../../../../docs/devtools.md#asset-validator).

## Diagnostics delegate (`usdex/core/Diagnostics.h`)

Opt-in `TfDiagnosticMgr::Delegate` that filters by severity, redirects streams, and formats messages for end users. Once active, status-level chatter from `createStage` / `saveStage` is hidden.

| Function | Notes |
| --- | --- |
| `activateDiagnosticsDelegate()` / `deactivateDiagnosticsDelegate()` / `isDiagnosticsDelegateActive()` | Install / remove / query. Not active by default — call once near program start. |
| `setDiagnosticsLevel(value)` / `getDiagnosticsLevel()` / `getDiagnosticLevel(diagnosticType)` | Severity filter and per-type lookup. |
| `setDiagnosticsOutputStream(value)` / `getDiagnosticsOutputStream()` | Stream redirect. |

Enums: `DiagnosticsLevel` = `eFatal`, `eError`, `eWarning` (default after activation), `eStatus`. `DiagnosticsOutputStream` = `eNone`, `eStdout`, `eStderr`.

## `TF_DEBUG`

SDK-specific symbol: `USDEX_TRANSCODING_ERROR` (failure encoding a `UsdPrim` / `UsdProperty` name). Useful general OpenUSD symbols: `PLUG_LOAD`, `PLUG_REGISTRATION`, `USD_CHANGES`, `USD_STAGE_LIFETIMES`, `AR_RESOLVER_INIT`. Combine with wildcards: `TF_DEBUG=USDEX_*`, `TF_DEBUG='PLUG_* AR_*'`, `TF_DEBUG=*`. Debugger break: `TF_ATTACH_DEBUGGER_ON_ERROR`, `TF_ATTACH_DEBUGGER_ON_FATAL_ERROR`, `TF_ATTACH_DEBUGGER_ON_WARNING`, or `TF_DEBUG=TF_ATTACH_DEBUGGER*`.

## USD Validation

`pip install "usd-exchange[test]"` (or `repo install_usdex --install-test` for native builds) provides the `usd_validation_nvidia` package and the `nvidia_usd_validate` CLI. Validate every output before declaring a converter pass complete: `engine = usd_validation_nvidia.ValidationEngine(init_rules=True)`; `engine.validate(stage_or_path)` returns a `Result` whose `issues()` is an `IssuesList`. Filter with `usd_validation_nvidia.IssuePredicates.Or(*predicates)`. CLI usage is in the [USD Validation CLI sample](https://github.com/NVIDIA-Omniverse/usd-exchange-samples/blob/main/source/validateUsd/README.md); C++ tests still rely on `doctest`.

Coverage is NVIDIA's own rules plus OpenUSD's, the latter adapted from the native `UsdValidation` registry (`usdGeom` / `usdPhysics` / `usdShade` / `usdSkel` / `usdUtils` validators, plus `usdLux` on USD 26.08+). Importing `usdex.test` widens that: it registers adapters for native validators the package does not wrap itself. Import it before constructing an engine, or use `usdex.test.TestCase`, which does both. All of it — the `usd_validation_nvidia` package and the native validator plugins its adapters load — installs only with `[test]` / `--install-test`, so validation is an authoring and CI gate rather than something a runtime-only deployment can perform. The native validators re-compose the stage, so a diagnostic raised during authoring can be emitted more than once across a validated run — assert on content, not on occurrence counts.

Shader compliance resolves each shader id through `Sdr`, so a shader whose node definition the runtime cannot parse is reported as non compliant. MDL is the usual case, as its parser ships with Omniverse rather than OpenUSD, so validating `usdex.rtx` materials outside of Omniverse reports every MDL shader. Bypass them with an issue predicate matching `sourceType 'mdl' ... not found in sdrRegistry`, via `issuePredicates=` or a `defaultValidationIssuePredicates` class attribute.

## `usdex.test` (Python)

`usdex.test.TestCase` — `unittest.TestCase` subclass that activates the diagnostics delegate in `setUpClass`.

| Member | Purpose |
| --- | --- |
| `defaultPrimName` (`"Root"`), `defaultUpAxis` (`UsdGeom.Tokens.y`), `defaultLinearUnits` (`UsdGeom.LinearUnits.meters`), `defaultAuthoringMetadata` | Defaults for setting up a stage in tests. Use via `cls.defaultAuthoringMetadata`. |
| `defaultValidationIssuePredicates` | Override on a subclass to ignore specific validator issues. |
| `validationEngine` (per test) | Pre-initialized `usd_validation_nvidia.ValidationEngine`. |
| `assertIsValidUsd(asset, [issuePredicates], [msg])` / `assertIsInvalidUsd(asset, issuePredicates)` | Pass-or-fail / must-fail validation. `asset` is a `Usd.Stage` or path. |
| `assertSdfLayerIdentifier`, `assertAttributeHasAuthoredValue`, `assertRotationsAlmostEqual` | Layer identifier check, default-time / time-sample check, `Gf.Rotation` / `Gf.Quatf` / `Gf.Quatd` comparison (same concrete type). |
| `tmpFile([name], [ext])` / `tmpLayer([name], [ext])` / `tmpDir([name])` | Per-test temp filesystem helpers; cleaned up in `tearDownClass`. |
| `isUsdOlderThan(version)` | Gate version-specific assertions. |

`usdex.test.ScopedDiagnosticChecker` — context manager that captures `Tf.Diagnostics` / `Tf.ErrorMarks` and asserts the expected sequence on exit. Args: `testCase`, `expected: List[(Tf.DiagnosticType, regex)]` in emission order (errors precede general diagnostics), and a `level` severity filter (default `eStatus`).

`usdex.test.DefineFunctionTestCase` — abstract `TestCase` subclass for testing custom `define*` helpers. Override `defineFunc`, `requiredArgs`, `schema`, `typeName`, `requiredPropertyNames` and inherit standard tests for stage/path success, parent/name success, weaker-vs-stronger sublayer authoring, redefinition, and invalid stage / path / parent / name / prim.

## `usdex/test/*.h` (C++)

`ScopedDiagnosticChecker.h` is a doctest helper: construct with `DiagnosticPatterns` (`vector<pair<TfEnum, string>>`); on destruction it asserts via doctest `CHECK`. Errors precede general diagnostics — order the expected list accordingly. `FilesystemUtils.h` provides temp-path helpers. Build a doctest binary (`#define DOCTEST_CONFIG_IMPLEMENTATION_IN_DLL` then `#include <doctest/doctest.h>`) and use these inside `TEST_CASE` blocks.

## Anti-patterns

| Don't | Do |
| --- | --- |
| `print(stage.ExportToString())` to debug authoring | activate the diagnostics delegate, run the converter, check the validator report |
| Catch `Tf.ErrorException` and silently continue | let the delegate surface it; in tests use `ScopedDiagnosticChecker` |
| Build a custom `unittest.TestCase` and reimplement validation | subclass `usdex.test.TestCase` and call `self.assertIsValidUsd(...)` |
| `TF_DEBUG=*` permanently in production | scope per debugging session, or use targeted symbols like `TF_DEBUG=USDEX_*` |
