# Reference: Lights

`SKILL.md` (rules) is in context. Header: `usdex/core/LightAlgo.h`. The SDK helpers cover dome and rect lights specifically; for distant / sphere / cylinder / disk / geometry lights, author raw `UsdLux*` schema and place under a `defineXform` parent.

## Functions

| Function | Notable defaults |
| --- | --- |
| `defineDomeLight((stage, path) / (parent, name) / (prim), [intensity], [texturePath], [textureFormat])` | `intensity=1.0`, `textureFormat=UsdLuxTokens.automatic` |
| `defineRectLight((stage, path) / (parent, name) / (prim), width, height, [intensity], [texturePath])` | `intensity=1.0` |
| `isLight(prim)` | True if `UsdLuxLightAPI` is applied. |
| `getLightAttr(defaultAttr)` | Returns the "correct" attribute — the new `inputs:` form when authored, otherwise the legacy form. Pass the schema accessor's result (e.g. `UsdLuxRectLight.GetIntensityAttr()`). |

Dome `textureFormat` tokens: `automatic` (detect from file), `latlong` (latitude X / longitude Y), `mirroredBall` (sphere reflection, orthogonal), `angular` (radial-linear, better edge sampling), `cubeMapVerticalCross` (mapped via `automatic`).

## Pole-axis caveat

`UsdLuxDomeLight` requires the dome's top pole to align with **+Y** regardless of stage `upAxis`. USD 23.11 added `UsdLuxDomeLight_1` with a configurable pole axis but support is not widespread — keep authoring `DomeLight` and rely on consumers to honour +Y. Renderers using a Z-up dome (Kit/RTX) typically expect a -90° X rotation; expose it as a host-side toggle rather than baking it.

## `inputs:` rename

USD 21.02 added the `inputs:` prefix to `UsdLuxLight` / `UsdLuxLightFilter` attributes. When reading, always route through `getLightAttr(...)` so either form resolves. When writing extra attributes the helpers do not author (e.g. light color, exposure, diffuse / specular contribution), use `UsdLuxLightAPI(prim).CreateColorAttr().Set(value)` etc. — the API schema accessors author the modern `inputs:` form.

After `usdex.core.createStage`, allocate the light name through the cache, call the matching helper, then place with `setLocalTransform`. For dome textures, use a relative `Sdf.AssetPath` resolved against the asset's `Textures/` subdirectory (`usdex.core.getTexturesToken()`).

## Anti-patterns

| Don't | Do |
| --- | --- |
| `UsdLux.RectLight.Define(stage, path)` plus manual `width` / `height` / `inputs:intensity` writes | `usdex.core.defineRectLight(parent, name, width, height, intensity=...)` with `name` from the cache |
| `light.GetIntensityAttr().Get()` (may miss `inputs:intensity`) | `usdex.core.getLightAttr(light.GetIntensityAttr()).Get()` |
| Hard-code dome rotation for a Z-up renderer in the converter | leave the dome unrotated; expose a renderer-specific toggle externally |
| Skip `setLocalTransform` for a dome because it's "global" | `setLocalTransform` is still the right way to author orientation overrides |
