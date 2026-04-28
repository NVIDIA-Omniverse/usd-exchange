# Reference: Asset Structure

`SKILL.md` (rules) is in context. Header: `usdex/core/AssetStructure.h`. Implements [NVIDIA's Principles of Scalable Asset Structure](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html); treat as a sample implementation if a target pipeline diverges.

## Placeable default prim

Conversion outputs are *placed* into larger scenes (referenced into assemblies, instanced into layouts, posed by simulators). The default prim must therefore be **Xformable** — define it with `defineXform`, never leave it as the `Scope` that `createStage` falls back to and never use `defineScope` for it. Classify reusable assets with Kind via `configureComponentHierarchy` (atomic models) or `configureAssemblyHierarchy` (compositions); `addAssetInterface` already sets component kind for the multi-layer flow.

## Tokens

Use the SDK getters wherever you would type a directory or scope name; pass directly into `addAsset*`. `getAssetToken()`, `getContentsToken()`, `getGeometryToken()`, `getMaterialsToken()`, `getPhysicsToken()` (layer + scope per domain), `getLibraryToken()` (library filename suffix), `getPayloadToken()` / `getTexturesToken()` (subdirs).

## Functions

| Function | Purpose / defaults |
| --- | --- |
| `defineScope((stage, path) / (parent, name) / (prim))` | Define / convert a `UsdGeomScope` with editability checks. For transformless grouping *beneath* a placeable root — not for the default prim of a placeable asset (use `defineXform`). |
| `defineReference((stage, path, source_prim) / (parent, source_prim, [name]))` | Reference an in-memory prim; resolves to a relative `assetPath` when possible. `name` defaults to source prim's name. |
| `defineReference((stage, path, sourceIdentifier, [primPath]) / (parent, name, sourceIdentifier, [primPath]))` | Reference an external file. Relative paths anchor to the edit-target layer; URI-like identifiers (containing `://`) bypass anchoring. |
| `definePayload(...)` | Same overload set as `defineReference`. |
| `createAssetPayload(stage, [format], [fileFormatArgs])` | Payload entry layer (sublayered by Content Layers) inside a `Payload/` subdir. Default `format="usda"`. |
| `addAssetLibrary(stage, name, [format], [fileFormatArgs])` | `<name>Library.<format>` next to the payload. Default `format="usdc"`; library default prim has `class` specifier. |
| `addAssetContent(stage, name, [format], [fileFormatArgs], [prependLayer], [createScope])` | `<name>.<format>` added to the stage's sublayer stack. Defaults `usda`, `prependLayer=True`, `createScope=True`. |
| `addAssetInterface(stage, source)` | Wires the Asset Layer (current `stage`) to payload `source`'s default prim, sets component kind, authors extents hint. |
| `configureComponentHierarchy(prim)` | Sets `prim.kind = "component"`, demotes descendant `component` to `subcomponent`, clears other authored kinds on descendants. |
| `configureAssemblyHierarchy(prim)` | Sets `prim.kind = "assembly"`, sets descendants with model children to `group`, leaves descendant `component` alone. |

`createAssetPayload` returns the Payload Layer as a stage. `addAssetLibrary` / `addAssetContent` operate on the *current edit target* of the stage you pass — call them on the payload stage, not the asset stage. `addAssetInterface` already sets component kind; reach for `configureComponentHierarchy` only when retrofitting.

## Atomic Component layer tree

1. **Asset Layer** (entry, USDA) — payloads the contents.
2. **Asset Payload Layer** (`<Payload>/Contents.usda`) — sublayers all Content Layers.
3. **Content Layers** (`<Payload>/Geometry.usda`, `Materials.usda`, `Physics.usda`) — domain-specific opinions.
4. **Library Layers** (`<Payload>/<Domain>Library.usdc`) — reusable prototypes referenced by the Content Layers.

Sequence: `createStage(...)` → `defineXform` on the default prim (set `displayName` if transcoded) → `payloadStage = createAssetPayload(assetStage)` → per domain `addAssetLibrary(payloadStage, getGeometryToken())` and author prototypes via `define*` → per domain `addAssetContent(payloadStage, getGeometryToken())` and author content as `defineReference` to library prototypes plus `setLocalTransform` → `addAssetInterface(assetStage, payloadStage)` → `usdex.core.saveStage(assetStage, AUTHORING_METADATA)`.

For monolithic single-layer assets, skip the payload helpers entirely. For very large hierarchies, consider `prim.SetInstanceable(True)` on references after the helpers do their work.

## Anti-patterns

| Don't | Do |
| --- | --- |
| `prim.GetReferences().AddReference(...)` / `prim.GetPayloads().AddPayload(...)` | `usdex.core.defineReference(...)` / `definePayload(...)` with a cached `name` |
| Leave the default prim as the `Scope` fallback, or `defineScope` it, on a placeable asset | `defineXform(stage, defaultPrimPath)` (then `configureComponentHierarchy` / `configureAssemblyHierarchy` for Kind) |
| `UsdGeomScope.Define(stage, path)` | `defineScope(parent, cached_name)` after allocating the name through the cache |
| Hard-code domain strings for layer or scope names | `getGeometryToken()` / `getMaterialsToken()` / `getPhysicsToken()` |
| `Usd.ModelAPI(prim).SetKind("component")` and walk descendants by hand | `configureComponentHierarchy(prim)` (or rely on `addAssetInterface`) |
| Edit `layer.subLayerPaths` directly to assemble the payload | `addAssetContent(payloadStage, name)` |
