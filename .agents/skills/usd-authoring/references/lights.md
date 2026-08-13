<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Lights

`SKILL.md` (rules) is in context. Header: `usdex/core/LightAlgo.h`. The SDK helpers cover dome and rect lights specifically; for distant / sphere / cylinder / disk / geometry lights, author raw `UsdLux*` schema and place under a `defineXform` parent.

## Functions

| Function | Notable defaults |
| --- | --- |
| `defineDomeLight((stage, path) / (parent, name) / (prim), [intensity], [texturePath], [textureFormat])` | `intensity=1.0`, `textureFormat=UsdLuxTokens.automatic` |
| `defineRectLight((stage, path) / (parent, name) / (prim), width, height, [intensity], [texturePath])` | `intensity=1.0` |
| `isLight(prim)` | True if `UsdLuxLightAPI` is applied. |
| `getLightAttr(defaultAttr)` | Returns the attribute to read from — the `inputs:` form when authored, otherwise a legacy unprefixed opinion. Pass the schema accessor's result (e.g. `UsdLuxRectLight.GetIntensityAttr()`). |

Dome `textureFormat` tokens: `automatic` (detect from file), `latlong` (latitude X / longitude Y), `mirroredBall` (sphere reflection, orthogonal), `angular` (radial-linear, better edge sampling), `cubeMapVerticalCross` (mapped via `automatic`).

After `usdex.core.createStage`, allocate the light name through the cache, call the matching helper, then place with `setLocalTransform`. For dome textures, use a relative `Sdf.AssetPath` resolved against the asset's `Textures/` subdirectory (`usdex.core.getTexturesToken()`).

## Pole-axis caveat

`UsdLuxDomeLight` requires the dome's top pole to align with **+Y** regardless of stage `upAxis`. USD 23.11 added `UsdLuxDomeLight_1` with a configurable pole axis but support is not widespread — keep authoring `DomeLight` and rely on consumers to honour +Y. Renderers using a Z-up dome (Kit/RTX) typically expect a -90° X rotation; expose it as a host-side toggle rather than baking it.

## Attribute names

Every supported runtime declares light attributes only in their connectable `inputs:` form; there is no unprefixed `intensity` in the schema, and `UsdLuxRectLight.GetIntensityAttr()` resolves to `inputs:intensity`. So to write the attributes the helpers do not author (light color, exposure, diffuse / specular contribution), pass the `inputs:` name to `usdex.core.setEffectiveAttributeValue` — the unprefixed spelling is not in the prim definition and fails with a runtime error:

```python
usdex.core.setEffectiveAttributeValue(light.GetPrim(), "inputs:color", Gf.Vec3f(1.0, 0.9, 0.8))
usdex.core.setEffectiveAttributeValue(light.GetPrim(), "inputs:exposure", 2.5)
```

This holds for lights you author with raw schema (distant, sphere, cylinder, disk, geometry) as much as for the ones with helpers.

Reading incoming data is the asymmetric case, and the reason `getLightAttr` exists: lights authored before the `inputs:` prefix landed in USD 21.02 carry the unprefixed name as an authored opinion, and the schema accessor cannot see it — `GetIntensityAttr()` still resolves to `inputs:intensity` and reports no authored value while the file says otherwise. Route reads of data you did not author through `getLightAttr(light.GetIntensityAttr())`, which prefers the `inputs:` attribute and falls back to the legacy one.

## Anti-patterns

| Don't | Do |
| --- | --- |
| `UsdLux.RectLight.Define(stage, path)` plus manual `width` / `height` / `inputs:intensity` writes | `usdex.core.defineRectLight(parent, name, width, height, intensity=...)` with `name` from the cache |
| `light.GetIntensityAttr().Get()` on data you did not author (misses a legacy unprefixed opinion) | `usdex.core.getLightAttr(light.GetIntensityAttr()).Get()` |
| Hard-code dome rotation for a Z-up renderer in the converter | leave the dome unrotated; expose a renderer-specific toggle externally |
| Skip `setLocalTransform` for a dome because it's "global" | `setLocalTransform` is still the right way to author orientation overrides |
