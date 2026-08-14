<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Materials

`SKILL.md` (rules) is in context. Covers `usdex.core` Preview and PBR (OpenPBR) Materials, `usdex.rtx` MDL Materials, color space utilities, and bindings; physics materials are in `references/physics.md`. Author materials under a dedicated scope — typically `UsdUtils.GetMaterialsScopeName()` (defaults to `Looks`) — allocated through the `NameCache` and defined with `usdex.core.defineScope`. Material prim names use the same cache flow.

## Pick the material family

| Family | Render contexts | Use when |
| --- | --- | --- |
| `usdex.core.definePreviewMaterial` | universal (`UsdPreviewSurface`) | Maximum portability, or the target renderer has no MaterialX support. |
| `usdex.core.definePbrMaterial` | `mtlx` (OpenPBR Surface) + universal | Default for new content. Higher fidelity in MaterialX-capable renderers (Storm, RTX) with a Preview Surface fallback everywhere else. Requires the `usdMtlx` plugin, which ships by default. |
| `usdex.rtx.definePbrMaterial` | `mdl` (OmniPBR) + universal | The target is specifically the RTX Renderer and OmniPBR-only features are needed. |

Each family has a glass counterpart: `defineGlassPreviewMaterial`, `defineGlassPbrMaterial`, and `usdex.rtx.defineGlassMaterial(..., [indexOfRefraction], [roughness])`, whose `roughness` drives OmniGlass frosting and the Preview Surface together.

## Functions

| Function | Use |
| --- | --- |
| `definePreviewMaterial((stage, path) / (parent, name) / (prim), color, [opacity], [roughness], [metallic])` | Defaults `opacity=1.0`, `roughness=0.5`, `metallic=0.0`. |
| `defineGlassPreviewMaterial(..., color, [indexOfRefraction], [roughness], [opacity])` | Preview-only glass. Defaults `1.5` / `0.02` / `0.2`. |
| `definePbrMaterial(..., color, [opacity], [roughness], [metallic])` / `defineGlassPbrMaterial(..., color, [indexOfRefraction], [roughness], [previewOpacity])` | Dual-context OpenPBR + Preview Surface from one shared Material Interface. `roughness` defaults to `0.3` for PBR. |
| `add{Color,Normal,Orm,Roughness,Metallic,Opacity,Emissive}TextureToPreviewMaterial(material, sdfAssetPath)` and the matching `...ToPbrMaterial` (`usdex.core` for OpenPBR, `usdex.rtx` for MDL; both Emissive variants take a brightness argument — `[luminance]` in `usdex.core`, `[intensity]` in `usdex.rtx`, each defaulting to `1000.0`) | Each reuses the default UV set (typically `primvars:st`) and sets `wrapS`/`wrapT` to `repeat`. The Pbr variants author every render context of the material in one call. Normal: auto scale/bias for `bmp`/`tga`/`jpg`/`jpeg`/`png`/`tif` (assumed 8-bit raw normals); adjust after the call if not. Opacity: also forces `ior=1.0` and `opacityThreshold = float_epsilon`. RTX texture functions replace certain Material inputs (e.g. `Color` → `ColorTexture`); call at initial authoring, not in a stronger override layer. |
| `addEmissiveColorToPreviewMaterial(material, color)` / `usdex.core.addEmissiveColorToPbrMaterial(material, color, [luminance])` / `usdex.rtx.addEmissiveColorToPbrMaterial(material, color, [intensity])` | Add emissive contribution. Brightness is the `luminance` / `intensity` argument (both default `1000.0`), *not* the color: the PBR variants reject any color component above 1.0. `luminance` is `cd/m^2` (Nits) driving the OpenPBR `emission_luminance` input, exposed on the Material Interface as `emissiveLuminance`; `UsdPreviewSurface` has no luminance input, so the universal context receives the color alone. Not supported on OmniGlass. |
| `addPrimvarShaderToPreviewMaterial(material, surfaceInputName, primvarName, [fallbackValue])` / `addPrimvarShaderToPbrMaterial(...)` | Wire a primvar reader into a surface input. Each affects only its own render context — call both to drive a dual-context material everywhere. |
| `addPreviewMaterialInterface(material)` | Promote authored shader inputs to top-level Material `UsdShadeInputs`. **Call last**. Preview-only: PBR Materials already have an interface and multi-context networks are rejected. |
| `usdex.rtx.createMdlShader(material, name, mdlPath, module, [connectMaterialOutputs])` / `createMdlShaderInput(material, name, value, typeName, [colorSpace])` | Add an MDL shader / set a Material-level input driving the MDL graph (e.g. OmniPBR `project_uvw`, `texture_scale`). |
| `bindMaterial(prim, material)` / `bindMaterialSubsets(subsets, materials)` | Direct binding (allPurpose, fallback strength) / parallel-vector subset binding. |
| `computeEffectivePreviewSurfaceShader(material)` / `computeEffectiveMtlxSurfaceShader(material)` / `computeEffectiveMdlSurfaceShader(material)` | Locate the underlying surface shader of one render context for direct edits — but only for inputs the Material Interface does not already drive (see below). |
| `removeMaterialInterface(material, [bakeValues])` | Strip the Material Interface for renderers that cannot load one. Call *after* all `define*` / `add*` calls. |
| `ColorSpace` enum (`eAuto` / `eRaw` / `eSrgb`), `getColorSpaceToken(value)`, `sRgbToLinear(color)` / `linearToSrgb(color)` | `eRaw` for normals / roughness / metallic / opacity / EXR; `eSrgb` for diffuse PNGs. Single-color conversions only — use OpenColorIO for full-pipeline color science. |

## Editing a value the Material Interface drives

Every input these helpers expose is connected from the shader up to the Material Interface, and a connection beats a value: writing to the shader input succeeds, reports success, and changes nothing, because consumers resolve through the connection. So after `addEmissiveColorToPbrMaterial`, `computeEffectiveMtlxSurfaceShader` plus a write to `inputs:emission_luminance` is silently inert — as is `usdex.core.setEffectiveAttributeValue` on it.

Author the interface input on the Material prim instead — `material.GetInput("emissiveLuminance").Set(value)` — which is the whole point of the interface: one edit drives every render context, and it is the input a DCC or downstream tool will edit too. The helper arguments cover the same values at initial authoring time. Reach for `computeEffective*SurfaceShader` for inputs no helper wired up, or after `removeMaterialInterface` has baked the interface values onto the shaders and dropped the connections.

## Pattern: dual-context PBR with a shared library scope

For non-default purpose, strength, or instance bindings, fall back to `UsdShadeMaterialBindingAPI` directly after the prim is defined. Below, order is load-bearing: `definePbrMaterial` first, then `add*Texture*`, then any optional `removeMaterialInterface`. Swapping `usdex.core` for `usdex.rtx` on the same call sequence produces the MDL variant. `default_prim`, `source_material`, `target_prim`, and `albedo` / `*_path` come from upstream conversion state.

```python
mat_scope_name = cache.getPrimName(default_prim, UsdUtils.GetMaterialsScopeName())
mat_scope = usdex.core.defineScope(default_prim, mat_scope_name)
mat_name = cache.getPrimName(mat_scope.GetPrim(), source_material.name)
material = usdex.core.definePbrMaterial(parent=mat_scope.GetPrim(), name=mat_name, color=albedo)
usdex.core.addColorTextureToPbrMaterial(material, Sdf.AssetPath(color_path))
usdex.core.addNormalTextureToPbrMaterial(material, Sdf.AssetPath(normal_path))
usdex.core.addOrmTextureToPbrMaterial(material, Sdf.AssetPath(orm_path))
usdex.core.bindMaterial(target_prim, material)
```

## Anti-patterns

| Don't | Do |
| --- | --- |
| `UsdShade.Material.Define(...)` plus a hand-built UsdPreviewSurface or MaterialX graph | `usdex.core.definePbrMaterial(parent, name, color, ...)` (or `definePreviewMaterial` for universal-only) |
| Hand-author an OmniPBR MDL graph for an RTX target | `usdex.rtx.definePbrMaterial(parent, name, color, ...)` |
| `addDiffuseTexture*` (deprecated in 3.0) | `addColorTextureToPreviewMaterial` / `addColorTextureToPbrMaterial` |
| `addPreviewMaterialInterface` on a PBR Material, or after `add*Texture*` on a Preview Material | PBR Materials already have an interface; on Preview Materials author every texture first, then call it last |
| Write to a shader input the Material Interface drives (raw `Set`, or `setEffectiveAttributeValue`) — the connection wins and the write is inert | author the interface input on the Material prim (`material.GetInput(name).Set(value)`) |
| `prim.ApplyAPI(UsdShadeMaterialBindingAPI)` + manual `Bind(...)` per prim | `usdex.core.bindMaterial(prim, material)` |
| Manual `pow(c, 2.2)` for a single albedo color | `usdex.core.sRgbToLinear(color)` |
