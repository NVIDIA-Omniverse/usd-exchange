# Reference: Names

`SKILL.md` (rules) is in context. Header: `usdex/core/NameAlgo.h`. The non-negotiable is firm: route every prim and property name through this module — never pass a string literal as a `name=` or `defaultPrimName=` argument.

## Validity

OpenUSD identifiers must be non-empty, start with `[A-Za-z_]`, and continue with `[A-Za-z0-9_]`. Property names allow `:` only as a namespace separator; each segment is itself a valid identifier. USD ≥ 24.03 also accepts XID (Unicode) identifiers, still excluding lexical / syntactic / `SdfPath` separators and leading digits. The SDK applies a reversible Bootstring-style transcoding so foreign characters round-trip into legal identifiers (e.g. `カーテンウォール` survives, unlike `Tf.MakeValidIdentifier`'s lossy `_______________`). Disable globally via the `USDEX_ENABLE_TRANSCODING` env setting if downstream tooling cannot tolerate transcoded names. The functions below also enforce sibling uniqueness so `SdfPath` stays unique.

## Functions

| Function | Use when |
| --- | --- |
| `getValidPrimName(name)` / `getValidPrimNames(names, [reservedNames])` | No parent context (e.g. `defaultPrimName` for a brand-new stage). |
| `getValidChildName(parent, name)` / `getValidChildNames(parent, names)` | Author one or many prims under an existing parent without remembering names later. |
| `getValidPropertyName(name)` / `getValidPropertyNames(names, [reservedNames])` | Property names; preserves `:` namespaces. |
| `setDisplayName(prim, name)` / `getDisplayName(prim)` / `clearDisplayName(prim)` / `blockDisplayName(prim)` / `computeEffectiveDisplayName(prim)` | Read/write/clear/block the `displayName` metadata, or compute the effective value (falls back to prim name). |

USD 25.11 deprecated `displayName` in favor of `uiHints` via `UsdUIObjectHints`; the SDK helpers still operate on the original `displayName` metadata only.

### `NameCache` — preferred for any non-trivial converter

Use one cache per conversion (per thread). Parent it to whichever stable type fits: `SdfPath` (pre-USD), `UsdPrim` (composed stage), or `SdfPrimSpec` (specific layer). The first call populates the cache from existing children; the cache does not auto-invalidate.

| Method | Notes |
| --- | --- |
| `getPrimName(parent, name)` / `getPrimNames(parent, names)` | Allocate child prim names. |
| `getPropertyName(parent, name)` / `getPropertyNames(parent, names)` | Allocate property names. The pseudo-root cannot have properties. |
| `update(parent)` / `updatePrimNames(parent)` / `updatePropertyNames(parent)` | Refresh after authoring outside the cache. |
| `clear(parent)` / `clearPrimNames(parent)` / `clearPropertyNames(parent)` | Drop reservations for one parent. |

`ValidChildNameCache` is deprecated since 1.1; do not use it.

## Picking the right helper

| Situation | Pick |
| --- | --- |
| Single one-off name, no cache nearby | `getValidChildName(parent, source.name)` |
| Multiple names from the same source list | `getValidChildNames(parent, source_names)` |
| Whole-converter authoring with many parents | one shared `NameCache`, called as `cache.getPrimName(parent, source.name)` |
| Stage default prim | `getValidPrimName(asset.name)` |
| Property name (including `:` namespaces) | `getValidPropertyName(source.property_name)` or `cache.getPropertyName(parent, source.property_name)` |

When the source name had to be transcoded or made unique, set `displayName` to the original via `usdex.core.setDisplayName(prim, source.name)` after the prim is defined.

## Anti-patterns

| Don't | Do |
| --- | --- |
| Pass a literal name to a `define*` helper | route via `cache.getPrimName(parent, source.name)` |
| `Tf.MakeValidIdentifier(name)` | `usdex.core.getValidPrimName(name)` (preserves the original via display name) |
| Re-allocate names from `getValidChildNames` repeatedly per parent | one `NameCache` for the whole conversion |
| Hard-coded literal `defaultPrimName` | `defaultPrimName=usdex.core.getValidPrimName(asset.name)` |
| `prim.SetDisplayName(...)` directly | `usdex.core.setDisplayName(prim, source.name)` after the prim is defined |
