<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Agent Instructions for the OpenUSD Exchange SDK

## When this applies

Read and follow the linked skills whenever a task involves the OpenUSD Exchange SDK: importing `usdex.core`, `usdex.rtx`, or `usdex.test` in Python; including `<usdex/core/...>`, `<usdex/rtx/...>`, or `<usdex/test/...>` in C++; or authoring / converting / exporting / validating any OpenUSD data via the SDK (`Usd.Stage`, `Sdf.Layer`, `UsdPrim`, `UsdGeomMesh`, `UsdGeomXformable`, `UsdGeomCamera`, `UsdLuxLight`, `UsdShadeMaterial`, `UsdPhysicsJoint`, `.usd` / `.usda` / `.usdc` / `.usdz` files). The skills target Physical AI converters: robotics, simulation, synthetic data, digital twins, and reusable asset libraries.

## Skills

- [.agents/skills/getting-started/SKILL.md](.agents/skills/getting-started/SKILL.md) — environment setup, Python wheel install, native (C++) install via `install_usdex`, project layout, and a smoke-test script. Read this first when bootstrapping or installing.
- [.agents/skills/usd-authoring/SKILL.md](.agents/skills/usd-authoring/SKILL.md) — non-negotiable authoring rules, canonical flow, and an index into topical reference files (stages and layers, names, geometry, materials, asset structure, physics, lights, cameras, diagnostics and testing). Read this whenever you are authoring USD with the SDK.

Load only the reference files inside `usd-authoring/` that the current task actually needs; the `SKILL.md` itself is the index and contains the rules that apply to every domain.
