# 2.1.0-rc1

## Core

### Features

- Added USD 25.08 support
- Added convenience functions for defining basic Gprims (plane, sphere, cube, cone, cylinder, capsule)
- Added Kind configuration helpers for Components and Assemblies
- Added Primvar Shader helpers for preview materials

### Fixes

- Fixed `isEditablePrimLocation()` to prevent authoring new children under instanced prims or their instance proxy descendants

## Pybind

### Features

- Added pybind11 interoperability for `UsdGeom.Sphere`, `UsdGeom.Plane`, `UsdGeom.Cube`, `UsdGeom.Cone`, `UsdGeom.Cylinder`, `UsdGeom.Cylinder_1`, `UsdGeom.Capsule`, and `UsdGeom.Capsule_1`

## Dev Tools

### Features

- Added `usdex.rtx` and `UsdSemantics` to the `usd-exchange` wheel
- Added USD 25.08 support via `install_usdex`
  - USD 25.08+ flavors use oneTBB
  - The python wheels remain on USD 25.05
- Added Linux ARM (aarch64) support for USD 25.02+
  - Available via the python wheels and `install_usdex`

### Fixes

- Fixed code-signing of Windows wheels
- Fixed `install_usdex` bug todo with optional repo_tool dependencies

## Documentation

- Fixed Try the Python Samples guide to use a virtual environment & python wheels

## Dependencies

### Runtime Deps

- OpenUSD 25.08, 25.05 (default) 25.02, 24.11, 24.08, 24.05
- Omni Asset Validator 1.4.2
- Python 3.12.11, 3.11.12, 3.10.18 (default)
- pybind 2.11.1

### Dev Tools

- packman 7.33
- repo_tools (all matching latest public)
- doctest 2.4.5
- cxxopts 2.2.0
- Premake 5.0.0-beta4
- GCC 11.4.0
- MSVC 2019-16.11

# 2.0.1

## Core

### Fixes

- The new `usd-exchange` Python Wheel which is published to PyPi is locked to our default USD 25.05
  - `pip install usd-exchange==2.0.1` strictly uses USD 25.05
  - If other USD flavors are required, please continue to use the `install_usdex` CLI tool or build from source
  - Rather than depend on the public `usd-core` wheel, we directly include the subset of OpenUSD libraries required to use `usdex.core`
    - `usd-core` is not ABI compatible with our minspec (manylinux_2_35 with modern CXX ABI)
    - In the future, if the public `usd-core` package becomes more compatible, we may add it as a dependency instead of packaging the OpenUSD libs
    - In the future, if wheel variants become possible on PyPi we may provide all supported flavors of `usd-exchange` as wheels

# 2.0.0

## Core

### Features

- Added USD 25.05 support
- Added Python 3.12 support for USD 25.05 and 25.02
- Added a new `usd-exchange` Python Wheel which is published to PyPi
  - There is a unique whl specific to each supported USD flavor/version (e.g. `usd-exchange==2.0.0+usd2505`)
  - Rather than depend on the public `usd-core` wheel, we directly include the subset of OpenUSD libraries required to use `usdex.core`
    - `usd-core` is not ABI compatible with our minspec (manylinux_2_35 with modern CXX ABI)
    - In the future, if the public `usd-core` package becomes more compatible, we may add it as a dependency instead of packaging the OpenUSD libs
- Added new `AssetStructure` module following NVIDIA's [Principles of Scalable Asset Structure](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html)
  - Includes new `defineScope`, `defineReference`, and `definePayload` functions for basic asset structure best practices
    - These functions ensure the new prim is defined at an editable location & that relative `AssetPaths` are used whenever possible
  - Includes more advanced functions for authoring according to the Atomic Component structure from the article
- Added new `PhysicsJointAlgo` module to simplify the authoring process
  - Supports authoring for fixed, revolute (hinge), prismatic (slide), and spherical (ball) joints
  - Ensures `PhysicsJoints` are aligned to both bodies when defined and can also re-align joints using `alignPhysicsJoint`
  - Abstracts the local joint frame to a form more suitable for a variety of source data specifications
- Added new `PhysicsMaterialAlgo` module for defining physical materials, adding physical properties to visual materials, and bindings physical materials to collision geometry
- Added `GfQuatf` orientation overloads to `XformAlgo` to accommodate a [translate, orient, scale] `XformOpOrder`
- Added overloads to all `XformAlgo` functions which accept `Xformable` schema
  - Allows call sites to replace the annoying `setLocalTransform(mesh.GetPrim(), ...)` pattern with `setLocalTransform(mesh, ...)`
- Added overloads to all `define` functions which "re-define" an existing `Scope`,  `Xform`, or untyped `Prim` to the specified prim type
  - Enables a two phase "define the structure, then fill in the details" pattern
- Added `kilogramsPerUnit` to the required Stage Metrics for `createStage` and `configureStage`
  - Call sites do not need to change, as it will be authored at a default value of 1 when `massUnits` is not specified
- Added `getLayerAuthoringMetadata` to retrieve previously authored creator metadata
- Added `getDiagnosticLevel` for mapping `TfDiagnosticType` to `usdex::core::DiagnosticsLevel`
- Added `USDEX_VERSION_STRING` macro to `Version.h`
- Added `buildVersion()` and changed behavior of `version()` (see Breaking Changes below)

### Fixes

- Prevent `bindMaterial()` from allowing bindings across instance boundaries
- All `PointsBased` define functions now emit `TF_RUNTIME_ERROR` if the points array is empty
- Fixed default `time` bindings in all `XformAlgo` functions
  - Runtime behavior is unchanged, it is just technically correct in the code now

### Breaking Changes

- Dropped USD 23.11 support
  - The source code may still compile for this flavor, but it is not being maintained in CI nor distributed as binary artifacts
- `usdex_core` now links `kind`, `work`, and `usdPhysics` directly
  - `usdPhysics` is the only new runtime requirement; the others were indirectly linked previously
- Replaced the sidecar `omni_transcoding` library with an internal implementation in `usdex_core`
  - The `USDEX_ENABLE_OMNI_TRANSCODING` `TfEnvSetting` was renamed `USDEX_ENABLE_TRANSCODING`
  - The behavior is unchanged, but build & distribution scripts need to be updated to avoid linking the other library
  - Note there is not currently any public function to decode an identifier
- `version()` now returns the simple semantic `USDEX_VERSION_STRING`
  - Use the new `buildVersion()` to retrieve the full `USDEX_BUILD_STRING` with semver and metadata
- Changed `hasLayerAuthoringMetadata` to accept a `const SdfLayerHandle` rather than a non-const `SdfLayerHandle`

## Pybind

### Features

- Added pybind11 interoperability for `Gf.Quatd`, `Gf.Quatf`, `UsdGeom.Scope`, `UsdGeom.Xformable`, `UsdPhysics.Joint`, `UsdPhysics.FixedJoint`, `UsdPhysics.RevoluteJoint`, `UsdPhysics.PrismaticJoint`, `UsdPhysics.SphericalJoint`

## RTX

### Features

- Added overloads to all `define` functions which "re-define" an existing `Scope`,  `Xform`, or untyped `Prim` to the specified prim type
  - Enables a two phase "define the structure, then fill in the details" pattern

### Breaking Changes

- `usdex_rtx` now links `usdGeom` directly

## Test

### Features

- `usdex.test` and `omni.asset_validator` can be used via the new `usd-exchange` wheel via the optional "test" extras
  - `pip install usd-exchange[test]`
- Added level filtering to `ScopedDiagnosticChecker`, which can be used to ignore status messages while still asserting warnings and errors
- Added `TestCase.tmpDir()` which is useful for structured asset testing
- The new `omni.asset_validator` module includes some optional `numpy` implementations which improve performance if `numpy` is available in the environment

### Fixes

- Fixed `usdex.test` to properly bootstrap `omni.asset_validator` when used outside of the `repo_test` harness
- Fixed `TestCase.tmpFile()` directory caching issue

### Breaking Changes

- The new `omni.asset_validator` module also requires the `omni.capabilities` module
  - Both modules ship in the same package & install via the optional `test` group for the `usd-exchange` wheels and for the `install_usdex` CLI
- `DefineFunctionTestCase` asserts the new "redefine `Prim`" overloads exist for each define function
- `DefineFunctionTestCase` now serializes `self.rootLayer` rather than using an anonymous layer
- Inlined `compareIdentifiers` in `usdex/test/FilesystemUtils.h`

## Dev Tools

### Features

- An `omni_asset_validate` CLI is included when using the `usd-exchange` wheel with the optional "test" extras (e.g. `pip install usd-exchange[test]`)
- `repo_version_header` now outputs a `<namespace>_VERSION_STRING` macro alongside `<namespace>_BUILD_STRING`

### Fixes

- Fixed `install_usdex` to use a fully qualified packman remote name
- Fixed `repo_version_header` to error when `macro_namespace` is unspecified, to prevent accidental un-namespaced macros

## Documentation

- Re-wrote the Getting Started guide as a minimal first step using Python Wheels
- Moved Try the Samples to a dedicated guide which follows the new Getting Started guide
- Moved Native Application Development to a dedicated guide
- Moved Testing and Debugging to a dedicated guide
- Added Python Wheels to the Deployment Guide and changed Docker deployment to use the wheels
- Added Physics and Asset Structure sections to the USD Authoring Guide
- Updated Dev Tools to recommend Python Wheels before `install_usdex` and to expand on Asset Validator use cases in USD Exchange workflows
- Updated License Notices as all dependencies are now permissive OSS
- Replaced social media links with more relevant links to GitHub and developer.nvidia.com/usd

## Dependencies

### Runtime Deps

- OpenUSD 25.05 (default) 25.02, 24.11, 24.08, 24.05
- Omni Asset Validator 1.1.6
- Python 3.12.11, 3.11.12, 3.10.18 (default)
- pybind 2.11.1

### Dev Tools

- packman 7.31
- repo_tools (all matching latest public)
- doctest 2.4.5
- cxxopts 2.2.0
- Premake 5.0.0-beta4
- GCC 11.4.0
- MSVC 2019-16.11

# 1.2.0

## Core

### Features

- Added Python 3.12 support for USD 25.02

### Fixes

- Prevent `bindMaterial()` from allowing bindings across instance boundaries
- All define PointBased functions now emit `TF_RUNTIME_ERROR` if the points array is empty

## Dependencies

### Runtime Deps

- OpenUSD 25.02, 24.11, 24.08 (default), 24.05, 23.11
- Omni Transcoding 1.0.0
- Omni Asset Validator 0.16.2
- pybind 2.11.1

### Dev Tools

- packman 7.31
- repo_tools (all matching latest public)
- doctest 2.4.5
- cxxopts 2.2.0
- Premake 5.0.0-beta4
- GCC 11.4.0
- MSVC 2019-16.11
- Python 3.10.18 (default), 3.11.12, 3.12.11

# 1.1.0

OpenUSD Exchange SDK is now provided under the Apache License, Version 2.0

## Core

### Features

- Added USD 25.02 support
- Added USD 24.11 support
- Added `NameCache` class for generating unique and valid names for `UsdPrims` and their `UsdProperties`
  - It can be used in several authoring contexts, with overloads for `SdfPath`, `UsdPrim` and `SdfPrimSpecHandle`
  - Deprecated `ValidChildNameCache` in favor of `NameCache`
- Improved python deprecation warnings

### Fixes

- Fixed attribute type for `UsdUvTexture.inputs:varname`

## Pybind

### Features

- Added support for `pxr_python` in USD 24.11+

## Test

### Fixes

- Fixed file extension bug in `TestCase.tmpLayer`

## Documentation

- Added `pybind` section to C++ API docs
- Updated docs to explain `boost::python` vs `pxr_python`
- Added guidance around `SdfLayer` encoding & Crate Version portability to the Authoring USD Data Guide
- Updated all license notices & attributions associated with change to Apache License, Version 2.0
- Updated Contributing Guide to accept code contributions via Developer Certificate of Origin
- Added explanation of optional NVIDIA SLA dependencies & how to disable them.

## Dependencies

### Runtime Deps

- OpenUSD 25.02, 24.11, 24.08 (default), 24.05, 23.11
- Omni Transcoding 1.0.0
- Omni Asset Validator 0.16.2
- pybind 2.11.1

### Dev Tools

- packman 7.27
- repo_tools (all matching latest public)
- doctest 2.4.5
- cxxopts 2.2.0
- Premake 5.0.0-beta4
- GCC 11.4.0
- MSVC 2019-16.11
- Python 3.10.16 (default), 3.11.11

# 1.0.0

## Core

### Features

- Added `usdex_core` shared library and `usdex.core` python module, which provide higher-level convenience functions on top of lower-level OpenUSD concepts, so developers can quickly adopt OpenUSD best practices when mapping their native data sources to OpenUSD-legible data models.

## Pybind


### Features

- Added `usdex/pybind`, a header-only cxx utility to enable seamless flow between `pybind11` & `boost_python`.
- Added bindings for all USD types exposed in the public API of the `usdex_core` library
  - Note: A minimal subset of USD types is supported. More types may be added in the future.

## RTX

### Features

- Added `usdex_rtx` shared library and `usdex.rtx` python module, which provide utility functions for creating, editing, and querying `UsdShade` data models which represent MDL Materials and Shaders for use with the RTX Renderer.

## Test

### Features

- Added `usdex.test`, a python module which provides `unittest` based test utilities for validating in-memory OpenUSD data for consistency and correctness.
- Added `usdex/test`, a header-only cxx utility which provides a more minimal set of `doctest` based test utilities.

## Dev Tools

### Features

- Added `install_usdex` tool to download and install precompiled OpenUSD Exchange binaries and all of its runtime dependencies.
  - This tool supports a variety of USD flavors & versions. See `repo install_usdex --help` or the [online docs](devtools.md#install_usdex) for details.
- Vendored `omni.asset_validator` python module for validating that USD Data output is compliant and conforms to expected standards.
  - This can be installed via `repo install_usdex --install-test`

## Documentation

- Added C++ and Python API docs for all public functions and classes.
- Added Getting Started article to help learn about & integrate the SDK into a project.
- Added Authoring USD Data article to briefly introduce each group of functions from `usdex_core` and `usdex_rtx`.
- Added Runtime Requirements article to exhaustively list the files required by our runtime.
- Added Deployment Options article explaining how to approach common deployments (e.g cli, docker container, DCC Plugin)
- Added License Notices article covering OpenUSD Exchange SDK and all its runtime dependencies.
- Added Dev Tools article to explain `install_usdex` and Omni Asset Validator.

## Dependencies

### Runtime Deps

- OpenUSD 24.08 (default), 24.05, 23.11
- Omni Transcoding 1.0.0
- Omni Asset Validator 0.14.2
- pybind 2.11.1

### Dev Tools

- packman 7.24.1
- repo_tools (all matching latest public)
- doctest 2.4.5
- cxxopts 2.2.0
- Premake 5.0.0-beta2
- GCC 11.4.0
- MSVC 2019-16.11
- Python 3.10.15 (default), 3.11.10
