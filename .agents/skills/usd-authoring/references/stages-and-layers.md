<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Stages and Layers

`SKILL.md` (rules) is in context. Headers: `usdex/core/StageAlgo.h`, `usdex/core/LayerAlgo.h`.

## Functions

| Function | Purpose |
| --- | --- |
| `createStage(identifier, defaultPrimName, upAxis, linearUnits, [massUnits], authoringMetadata, [fileFormatArgs])` | Create a stage with required metadata authored explicitly. Default prim is created as `Scope` if missing — for placeable assets, immediately overwrite it with `defineXform`. `defaultPrimName` must come from `usdex.core.getValidPrimName(asset.name)`; `authoringMetadata` from the `AUTHORING_METADATA` variable. |
| `configureStage(stage, defaultPrimName, upAxis, linearUnits, [massUnits], [authoringMetadata])` | Apply the same metadata to an opened stage without overwriting an existing `creator` key. |
| `saveStage(stage, authoringMetadata, [comment])` | Save every dirty layer; layers without a `creator` key get one. Always pass `AUTHORING_METADATA`. |
| `saveLayer(layer, authoringMetadata, [comment])` / `exportLayer(layer, identifier, authoringMetadata, [comment], [fileFormatArgs])` | Save / export a single `SdfLayer`; export does not modify the source layer. |
| `setLayerAuthoringMetadata` / `hasLayerAuthoringMetadata` / `getLayerAuthoringMetadata` | Direct access to the `creator` key in `customLayerData`. Prefer the save/export helpers; reach for these only when adjusting metadata mid-authoring. |
| `getUsdLayerEncoding(layer)` | Returns `"usda"`, `"usdc"`, `"usd"`, or empty. Use instead of inspecting the file extension. |
| `isEditablePrimLocation(stage, path) / (prim, name) / (prim)` | Validate that opinions can be authored. Used inside the `define*` helpers; call directly when authoring without one. Returns `false` for instance proxies, invalid paths, missing stage. |

`upAxis` should be `UsdGeom.GetFallbackUpAxis()` unless source data dictates otherwise. `linearUnits` is meters per unit (`UsdGeom.LinearUnits.meters` = `1.0`, `centimeters` = `0.01`). `massUnits` is kilograms per unit.

## Encoding

Default to USDC for production geometry, materials, and asset library layers. Use USDA for human-readable interfaces, debug layers, or quick scaffolding. `.usd` can hold either; set `fileFormatArgs={"format": "usda"}` (or `"usdc"`) when ambiguity matters. The asset-structure helpers default content layers to `usda` and library layers to `usdc`.

## OpenUSD 25.11 portability

`UsdcFileFormat`, `UsdaFileFormat`, and `CrateInfo` moved from `Usd` to `Sdf`. Use `usdex.core.getUsdLayerEncoding(layer)` instead of querying the file-format classes directly. For Crate version queries, gate on `Usd.GetVersion()` and use `Sdf.CrateInfo` (≥ 25.11) or `Usd.CrateInfo` (older). To target older runtimes, set `USD_WRITE_NEW_USDC_FILES_AS_VERSION` / `USD_WRITE_NEW_USDA_FILES_AS_VERSION` *before* importing any USD module.

The canonical converter open-or-create entry point: `Sdf.Layer.FindOrOpen(identifier)`; if null, call `usdex.core.createStage(...)`; otherwise `Usd.Stage.Open(identifier)`. Use the same `defaultPrimName=getValidPrimName(...)` and `AUTHORING_METADATA` in both branches.

## Anti-patterns

| Don't | Do |
| --- | --- |
| `Usd.Stage.CreateNew(identifier)` plus manual `UsdGeomSetStageUpAxis` / `UsdGeomSetStageMetersPerUnit` | `usdex.core.createStage(identifier, ..., authoringMetadata=AUTHORING_METADATA)` |
| `Usd.Stage.CreateInMemory()` for a script that ultimately writes to disk | `usdex.core.createStage(...)` (anonymous identifiers are accepted) |
| `stage.GetRootLayer().Save()` / `stage.Save()` | `usdex.core.saveStage(stage, AUTHORING_METADATA)` |
| Hard-coded literal for `defaultPrimName` | `defaultPrimName=usdex.core.getValidPrimName(asset.name)` |
| Ship a placeable asset whose default prim is the `Scope` fallback (or any non-`Xformable` type) | `defineXform(stage, stage.GetDefaultPrim().GetPath())` right after `createStage`; see `references/asset-structure.md` |
| Inspect `layer.identifier.endswith(".usda")` to detect encoding | `usdex.core.getUsdLayerEncoding(layer)` |
