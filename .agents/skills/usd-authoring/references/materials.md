<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Materials

`SKILL.md` (rules) is in context. Covers `usdex.core` Preview Materials, `usdex.rtx` MDL Materials, color space utilities, and bindings. Physics materials are in `references/physics.md`.

Author materials under a dedicated scope — typically `UsdUtils.GetMaterialsScopeName()` (defaults to `Looks`) — allocated through the `NameCache` and defined with `usdex.core.defineScope`. Material prim names use the same cache flow.

## Functions

| Function | Use |
| --- | --- |
| `definePreviewMaterial((stage, path) / (parent, name) / (prim), color, [opacity], [roughness], [metallic])` | Portable PBR baseline; works in every USD-aware renderer. Defaults `opacity=1.0`, `roughness=0.5`, `metallic=0.0`. |
| `addEmissiveColorToPreviewMaterial(material, color)` | Add emissive contribution. |
| `add{Diffuse,Normal,Orm,Roughness,Metallic,Opacity,Emissive}TextureToPreviewMaterial(material, sdfAssetPath)` | Each reuses the default UV set (typically `primvars:st`) and sets `wrapS`/`wrapT` to `repeat`. Normal: auto scale/bias for `bmp`/`tga`/`jpg`/`jpeg`/`png`/`tif` (assumed 8-bit raw normals); adjust after the call if not. Opacity: also forces `ior=1.0` and `opacityThreshold = float_epsilon` for cleaner masked geometry. |
| `addPrimvarShaderToPreviewMaterial(material, surfaceInputName, primvarName, [fallbackValue])` | Wire a primvar reader into a surface input. |
| `addPreviewMaterialInterface(material)` | Promote authored shader inputs to top-level Material `UsdShadeInputs`. **Call last**. |
| `usdex.rtx.definePbrMaterial((stage, path) / (parent, name) / (prim), color, [opacity], [roughness], [metallic])` | OmniPBR + Preview multi-context material driven by one Material Interface. |
| `usdex.rtx.defineGlassMaterial(..., [indexOfRefraction])` | OmniGlass + Preview multi-context material. |
| `usdex.rtx.add{Diffuse,Normal,Orm,Roughness,Metallic,Opacity,Emissive}TextureToPbrMaterial` (the Emissive variant takes an extra `[intensity]`) / `addEmissiveColorToPbrMaterial(material, color, [intensity])` | Texture wiring for both MDL and Preview at once. RTX texture functions replace certain Material inputs (e.g. `Color` → `DiffuseTexture`); call at initial authoring, not in a stronger override layer. |
| `usdex.rtx.createMdlShader(material, name, mdlPath, module, [connectMaterialOutputs])` | Add an MDL shader; auto-creates surface / displacement / volume outputs by default. |
| `usdex.rtx.createMdlShaderInput(material, name, value, typeName, [colorSpace])` | Set a Material-level input that drives the MDL graph (e.g. OmniPBR `project_uvw`, `texture_scale`). |
| `bindMaterial(prim, material)` / `bindMaterialSubsets(subsets, materials)` | Direct binding (allPurpose, fallback strength) / parallel-vector subset binding. |
| `computeEffectivePreviewSurfaceShader(material)` / `computeEffectiveMdlSurfaceShader(material)` | Locate the underlying surface shader for direct edits. |
| `removeMaterialInterface(material, [bakeValues])` | Strip the Material Interface. Use *after* `definePbrMaterial` for renderers that cannot load Material Interfaces. |
| `ColorSpace` enum (`eAuto` / `eRaw` / `eSrgb`), `getColorSpaceToken(value)`, `sRgbToLinear(color)` / `linearToSrgb(color)` | `eRaw` for normals / roughness / metallic / opacity / EXR; `eSrgb` for diffuse PNGs. Single-color conversions only — use OpenColorIO for full-pipeline color science. |

For non-default purpose, strength, or instance bindings, fall back to `UsdShadeMaterialBindingAPI` directly after the prim is defined.

## Pattern: PBR + Preview with shared library scope

Order is load-bearing: `definePbrMaterial` first, then `add*Texture*`, then optional `removeMaterialInterface` or extra `createMdlShaderInput` calls. `default_prim`, `source_material`, `target_prim`, and `albedo` / `*_path` come from upstream conversion state.

```python
mat_scope_name = cache.getPrimName(default_prim, UsdUtils.GetMaterialsScopeName())
mat_scope = usdex.core.defineScope(default_prim, mat_scope_name)
mat_name = cache.getPrimName(mat_scope.GetPrim(), source_material.name)
material = usdex.rtx.definePbrMaterial(parent=mat_scope.GetPrim(), name=mat_name, color=albedo)
usdex.rtx.addDiffuseTextureToPbrMaterial(material, Sdf.AssetPath(diffuse_path))
usdex.rtx.addNormalTextureToPbrMaterial(material, Sdf.AssetPath(normal_path))
usdex.rtx.addOrmTextureToPbrMaterial(material, Sdf.AssetPath(orm_path))
usdex.core.bindMaterial(target_prim, material)
```

## Anti-patterns

| Don't | Do |
| --- | --- |
| `UsdShade.Material.Define(...)` plus a hand-built UsdPreviewSurface graph | `usdex.core.definePreviewMaterial(parent, name, color, ...)` |
| Hand-author OmniPBR MDL graph for an RTX target | `usdex.rtx.definePbrMaterial(parent, name, color, ...)` |
| `add*Texture*` after `addPreviewMaterialInterface` and expect promotion | author every `add*Texture*` first, then call `addPreviewMaterialInterface(material)` last |
| `prim.ApplyAPI(UsdShadeMaterialBindingAPI)` + manual `Bind(...)` per prim | `usdex.core.bindMaterial(prim, material)` |
| Manual `pow(c, 2.2)` for a single albedo color | `usdex.core.sRgbToLinear(color)` |
