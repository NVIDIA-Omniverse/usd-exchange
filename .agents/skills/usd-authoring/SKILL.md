---
name: usd-authoring
description: Author USD content with the OpenUSD Exchange SDK. Use whenever you import usdex.core, usdex.rtx, or usdex.test (Python) or include any usdex/* C++ headers, or when you read/write Usd.Stage / Sdf.Layer / UsdPrim / UsdGeom* / UsdLux* / UsdShade* / UsdPhysics* data via the SDK.
---

# USD Authoring with the OpenUSD Exchange SDK

## When to apply

Apply when a task imports `usdex.core` / `usdex.rtx` / `usdex.test` in Python, or includes `<usdex/core/...>` / `<usdex/rtx/...>` / `<usdex/test/...>` in C++, or authors / converts / exports / validates OpenUSD data of any kind (`Usd.Stage`, `Sdf.Layer`, `UsdPrim`, `UsdGeomMesh`, `UsdGeomXformable`, `UsdGeomCamera`, `UsdLuxLight`, `UsdShadeMaterial`, `UsdPhysics*`, `.usd*` files). Stop when the task moves to non-USD work.

The audience is Physical AI converter / pipeline authors: robotics, simulation, synthetic data, digital twins, reusable asset libraries.

## Non-negotiables

These rules apply to every snippet you write and every API you call. Do not relax them with "this example is illustrative" or "this is just for teaching" reasoning.

### Use the SDK helpers; do not call raw OpenUSD where a helper exists

| Domain | Use this | Not this |
| --- | --- | --- |
| Stage creation | `usdex.core.createStage` | `Usd.Stage.CreateNew`, `Usd.Stage.CreateInMemory` plus manual metadata |
| Stage configuration | `usdex.core.configureStage` | `UsdGeomSetStageUpAxis` + `UsdGeomSetStageMetersPerUnit` + manual `creator` write |
| Stage save | `usdex.core.saveStage` | `stage.Save()` / `stage.GetRootLayer().Save()` |
| Single-layer save / export | `usdex.core.saveLayer` / `usdex.core.exportLayer` | `layer.Save()` / `layer.Export()` |
| Transforms | `usdex.core.setLocalTransform` (or pass `transform` to `defineXform` / `defineCamera`) | `UsdGeomXformCommonAPI`, `AddTranslateOp` / `AddRotateOp` / `AddScaleOp` / `AddTransformOp` |
| Names (prims) | `usdex.core.NameCache.getPrimName(s)` or `getValidPrimName(s)` / `getValidChildName(s)` | string literals, `Tf.MakeValidIdentifier`, `TfMakeValidIdentifier` |
| Names (properties) | `getValidPropertyName(s)` or `NameCache.getPropertyName(s)` | string literals for property names |
| References | `usdex.core.defineReference` | `prim.GetReferences().AddReference(...)` |
| Payloads | `usdex.core.definePayload` | `prim.GetPayloads().AddPayload(...)` |
| Scopes | `usdex.core.defineScope` | `UsdGeomScope.Define` |
| Xforms / meshes / curves / points / gprims / cameras / lights / preview materials / physics joints / physics materials | the matching `usdex.core.define*` helper | `Usd<Schema>.Define` plus attribute writes |
| RTX MDL materials | `usdex.rtx.definePbrMaterial` / `defineGlassMaterial` | hand-rolled MDL shader graphs |
| Primvars (normals, UVs, widths, displayColor, displayOpacity, ids, custom) | wrap in `usdex.core.PrimvarData` (or `Vec3fPrimvarData` / `Vec2fPrimvarData` / `FloatPrimvarData` / `Int64PrimvarData` / `IntPrimvarData` / `TokenPrimvarData` / `StringPrimvarData`) | direct `CreatePrimvar` + raw `VtArray` writes |

Raw schema is allowed (and required) only for APIs without a helper — e.g. `UsdPhysicsRigidBodyAPI.Apply`, `UsdPhysicsCollisionAPI.Apply`, `UsdPhysics.Scene.Define`, `UsdLux.LightAPI.CreateColorAttr` — and only **after** the prim has been defined via the helper.

### Names

Every prim name you author — including names you "own" (asset names, scope names, default-prim names, throwaway example names) — flows through the name pipeline. Never pass a string literal to a `usdex.core.define*` / `usdex.rtx.define*` / `defineScope` / `createMaterial` `name=` argument. Never pass a string literal to `defaultPrimName=`. Use a variable populated from `NameCache.getPrimName(parent, source.name)`, `getValidChildName(parent, source.name)`, or `getValidPrimName(asset.name)`.

For property names, the same rule applies via `getValidPropertyName(s)` or `NameCache.getPropertyName(s)`.

### Authoring metadata

Every call to `createStage` / `configureStage` / `saveStage` / `saveLayer` / `exportLayer` must take an `authoringMetadata` value, and that value must be a variable (e.g. `AUTHORING_METADATA`), not a string literal. The variable should describe the host application and version (for example, `"My Converter 2026.1, usdex_ver: <ver>"`).

### Validation

If `usdex.test` is available, regression tests should subclass `usdex.test.TestCase` and call `self.assertIsValidUsd(stage)` on every produced stage. Diagnostic-checking tests use `usdex.test.ScopedDiagnosticChecker`. Outside of tests, run the [Omniverse Asset Validator](../../docs/devtools.md#asset-validator) on output. See `reference-diagnostics-and-testing.md`.

## Canonical authoring flow (prose, not code)

The flow below applies whether you are writing one stage or an asset library. The reference files expand each step.

1. Activate the diagnostics delegate so SDK status messages stop printing to stdout. See `reference-diagnostics-and-testing.md`.
2. Allocate a single `NameCache` for the whole conversion. Use it for every prim and property name you author. See `reference-names.md`.
3. Define a module-level `AUTHORING_METADATA` string from the host application's identity and version. Pass it to every stage / layer call.
4. Create the stage with `usdex.core.createStage`, supplying `defaultPrimName=getValidPrimName(asset.name)`, `upAxis`, `linearUnits` (and `massUnits` if physics is involved), and `authoringMetadata=AUTHORING_METADATA`. See `reference-stages-and-layers.md`.
5. For placeable assets (the typical converter output), define the default prim as `Xform` via `usdex.core.defineXform` — never leave it as the `Scope` fallback that `createStage` creates. Classify reusable assets with `configureComponentHierarchy` / `configureAssemblyHierarchy` (or rely on `addAssetInterface` for the multi-layer flow). See `reference-asset-structure.md`.
6. Author content under the default prim using `usdex.core.define*` / `usdex.rtx.define*` helpers. For each prim:
    - Allocate the name through the cache.
    - Call the matching `define*` helper, passing typed data and any `PrimvarData`.
    - Apply API schemas (e.g. `UsdPhysicsRigidBodyAPI.Apply`) only after the prim is defined.
    - Set the local transform via `usdex.core.setLocalTransform` or by passing a transform to the `define*` helper.
7. For multi-layer asset structure (Atomic Component, Library + Content + Interface layers), use `createAssetPayload` / `addAssetLibrary` / `addAssetContent` / `addAssetInterface`. See `reference-asset-structure.md`.
8. For materials, prefer `definePreviewMaterial` for portability and `usdex.rtx.definePbrMaterial` / `defineGlassMaterial` for RTX. Bind with `bindMaterial` / `bindMaterialSubsets`. See `reference-materials.md`.
9. For physics, define visual / collision geometry first, then apply `UsdPhysicsRigidBodyAPI` / `UsdPhysicsCollisionAPI`, define `UsdPhysics.Scene` (raw schema), and use `definePhysicsFixedJoint` / `definePhysicsRevoluteJoint` / `definePhysicsPrismaticJoint` / `definePhysicsSphericalJoint` for joints. See `reference-physics.md`.
10. Save with `usdex.core.saveStage(stage, AUTHORING_METADATA)`. For single-layer flows, use `saveLayer` / `exportLayer` instead. See `reference-stages-and-layers.md`.
11. Validate the result with `omni.asset_validator.ValidationEngine` or `usdex.test.TestCase.assertIsValidUsd`. See `reference-diagnostics-and-testing.md`.

## Reference index

Load only the files needed for the current task; this `SKILL.md` already contains the rules that apply to every domain.

| File | Read when the task involves |
| --- | --- |
| `reference-stages-and-layers.md` | Creating, configuring, saving, or exporting stages / layers; choosing USDA vs USDC; layer authoring metadata; `Usd` → `Sdf` API moves in USD 25.11. |
| `reference-names.md` | Any prim or property name; `NameCache`; `displayName` metadata; transcoding; the `USDEX_ENABLE_TRANSCODING` env setting. |
| `reference-geometry.md` | Meshes, curves, points, basic gprims (sphere/cube/cone/cylinder/capsule/plane), subsets, primvars, normals computation. |
| `reference-materials.md` | UsdPreviewSurface materials, RTX MDL materials, textures, material interfaces, bindings, color space, primvar shaders. |
| `reference-asset-structure.md` | Atomic Component assets, Library / Content / Interface layers, `defineReference` / `definePayload`, scopes, kinds. |
| `reference-physics.md` | UsdPhysics scenes, rigid bodies, colliders, joints, physics materials, friction / restitution / density. |
| `reference-lights.md` | `UsdLuxDomeLight`, `UsdLuxRectLight`, generic `UsdLuxLightAPI` attributes, the `inputs:` rename, dome pole axis. |
| `reference-cameras.md` | `UsdGeomCamera` via `GfCamera`. |
| `reference-diagnostics-and-testing.md` | Diagnostics delegate, `TF_DEBUG`, `usdex.test.TestCase`, `ScopedDiagnosticChecker`, Asset Validator. |

## External references

- [Authoring USD Data](../../docs/authoring-usd.md) — the SDK's own authoring narrative.
- [OpenUSD Exchange Samples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples) — full end-to-end converters in matched C++ and Python.
- [Principles of Scalable Asset Structure](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html) — background for the Asset Structure module.
