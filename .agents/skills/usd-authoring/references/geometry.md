<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Geometry

`SKILL.md` (rules) is in context. Covers meshes, curves, point clouds, basic gprims, primvars, and transforms. Headers: `MeshAlgo.h`, `CurvesAlgo.h`, `PointsAlgo.h`, `GprimAlgo.h`, `PrimvarData.h`, `XformAlgo.h`.

## Pick the schema

| Source data | Helper |
| --- | --- |
| Tessellated polygon mesh with topology | `definePolyMesh` |
| Particles or unstructured points | `definePointCloud` |
| Linear lines / 1-D strokes | `defineLinearBasisCurves` |
| Smooth curves (Bezier / B-spline / Catmull-Rom) | `defineCubicBasisCurves` |
| Primitive that fits a basic shape (with non-uniform scale if needed) | `defineCube` / `defineSphere` / `defineCone` / `defineCylinder` / `defineCapsule` / `definePlane` |
| Bounding cage / volume parent | `defineXform` |

## Functions

Each `define*` function below has `(stage, path, ...)`, `(parent, name, ...)`, and `(prim, ...)` overloads (the third converts an existing prim).

| Function | Notes |
| --- | --- |
| `definePolyMesh(..., faceVertexCounts, faceVertexIndices, points, [normals], [uvs], [displayColor], [displayOpacity])` | Authors counts, indices, points, computed `extent`; right-handed orientation (reverse winding upstream if left-handed); forces `subdivisionScheme = none`. For subdiv surfaces, define then author the subdiv attributes manually. Primvar args take the typed `*PrimvarData` aliases. Normals are authored as `primvars:normals`. Emits a `TF_RUNTIME_ERROR` (no prim authored) when indexed topology leaves any points, normals, uvs, displayColor, or displayOpacity value unreferenced — fix the source topology rather than dropping the primvar. |
| `computeMeshNormals(faceVertexCounts, faceVertexIndices, points, [interpolation], [fallback])` | Default `interpolation` is `uniform` (face); `vertex` is area-weighted; `faceVarying` assigns each face's normal to all of its corners. Returns `Vec3fPrimvarData`; the `(mesh, ...)` overload updates in place. Fall back only when source has no normals. |
| `definePartitionedSubsets(mesh, names, indices)` / `defineNonOverlappingSubsets` / `defineUnrestrictedSubsets(mesh, names, indices, elementType, familyName)` | Every-element / disjoint / overlapping. The first two default `elementType=face` and `familyName=materialBind`, and bind via `bindMaterialSubsets(subsets, materials)` (parallel vectors). The overlapping variant cannot be used for material binding: it rejects `materialBind`, which USD requires to be a partition or non-overlapping, and takes both arguments explicitly since there is no sensible default family.
| `defineLinearBasisCurves(..., curveVertexCounts, points, [wrap], [widths], [normals], [displayColor], [displayOpacity])` | `wrap`: `nonperiodic` (default) / `periodic`. |
| `defineCubicBasisCurves(..., curveVertexCounts, points, [basis], [wrap], [widths], [normals], [displayColor], [displayOpacity])` | `basis`: `bezier` (default), `bspline`, `catmullRom`. `wrap` also allows `pinned` for `bspline` / `catmullRom`. A single prim shares one `wrap` and one `basis`; split when source mixes them. **Authoring `normals` turns curves into oriented ribbons rather than tubes.** |
| `definePointCloud(..., points, [ids], [widths], [normals], [displayColor], [displayOpacity])` | Only `vertex` interpolation is valid for `normals`. `ids` is a raw `VtInt64Array` (not a `PrimvarData`). |
| `defineCube` / `defineSphere` / `defineCone` / `defineCylinder` / `defineCapsule` / `definePlane(..., [displayColor], [displayOpacity])` | Validate path is editable, compute correct extents. Cone / cylinder / capsule / plane accept an `axis` token (`X` / `Y` / `Z`; default `Z`). `displayColor` / `displayOpacity` are scalar (`GfVec3f` / `float`), not primvars. Approximate a rectangular prism via `defineCube` + non-uniform `setLocalTransform` scale; an ellipsoid via `defineSphere` + non-uniform scale. |
| `defineXform((stage, path) / (parent, name) / (prim), [transform])` | Optional `GfTransform` / `GfMatrix4d` lets you author the prim and its transform in one call. |
| `setLocalTransform(prim, ...)` | Overloads: `GfTransform`, `GfMatrix4d`, components (`translation`, `pivot`, `rotation` (degrees), `RotationOrder`, `scale`), or quaternion components (`translation`, `orientation`, `scale`). Reconciles with whatever `xformOp` order is already present. |
| `getLocalTransform` / `getLocalTransformMatrix` / `getLocalTransformComponents` / `getLocalTransformComponentsQuat` | Symmetric reads. `RotationOrder`: `eXyz` (default), `eXzy`, `eYxz`, `eYzx`, `eZxy`, `eZyx`. |

## Primvar data (`PrimvarData.h`)

Wrap every primvar payload in the matching typed alias (`Vec3fPrimvarData`, `Vec2fPrimvarData`, `FloatPrimvarData`, `Int64PrimvarData`, `IntPrimvarData`, `TokenPrimvarData`, `StringPrimvarData`). The bare `PrimvarData` is the C++ template `usdex::core::PrimvarData<T>` and is not a Python public symbol — Python code references the aliases only. Construct `(interpolation, values)` non-indexed or `(interpolation, values, indices)` indexed; validation deferred to `isValid()`; automated indexing with `index()`.

| Alias | Element | Common use |
| --- | --- | --- |
| `FloatPrimvarData` / `IntPrimvarData` / `Int64PrimvarData` | `float` / `int` / `int64_t` | widths, displayOpacity, shader switches, ids |
| `TokenPrimvarData` / `StringPrimvarData` | `TfToken` / `string` | enum-like / human-readable descriptors (token lifetime is process-long) |
| `Vec2fPrimvarData` / `Vec3fPrimvarData` | `GfVec2f` / `GfVec3f` | UVs / normals, displayColor, vectors |

Methods: `isValid()` (interpolation, non-empty values, indices in range, element-size divisibility), `index()` (collapse duplicates; idempotent), `hasUnindexedValues()` (values never referenced by the indices — the condition `definePolyMesh` rejects), `effectiveSize()` (deduplicated logical count), `isIdentical(other)` (confirms `VtArray` storage was not detached), `getPrimvarData(primvar)` / `setPrimvar(primvar)` (read / write an existing `UsdGeomPrimvar`). Canonical pattern: build typed `PrimvarData`, call `index()`, pass to the define helper as `normals=` / `uvs=` / `displayColor=` / etc. `elementSize` is rare; leave default.

For primvars no define helper covers, author them from the same typed data rather than by hand: `data.createPrimvar(prim, name, [valueTypeName])` creates and authors the primvar in one call, with `name` excluding the `primvars:` prefix. For a single scalar, `createConstantPrimvar(prim, name, value, [valueTypeName])` and `setConstantPrimvar(prim, name, value, [time])` skip the `PrimvarData` construction — `set*` requires the primvar to exist and takes a `UsdTimeCode` for time-sampled writes. `valueTypeName` selects the authored USD type and must be an array type; omitted, each alias picks its own default (`Float3Array` for `Vec3fPrimvarData`, `TexCoord2fArray` for `Vec2fPrimvarData`, `IntArray` for `IntPrimvarData`, and so on). Only `Vec3fPrimvarData` offers a choice worth making: it also accepts `Color3fArray` / `Normal3fArray` / `Point3fArray` to carry the role, and promotes the scalar spellings (`Color3f`, `Normal3f`, `Point3f`) to those array forms. Every other alias accepts nothing but its own array type — `Sdf.ValueTypeNames.Int` for an `int`, or `Float2Array` for a `Vec2f`, both fail with "the value type is incompatible with the primvar data" and author nothing. The one useful exception: a Python `str` value takes either `StringArray` or `TokenArray`, which is how you choose between them given there is no `Tf.Token` type.

## Anti-patterns

| Don't | Do |
| --- | --- |
| `UsdGeom.Mesh.Define(stage, path)` then write each attribute by hand | `usdex.core.definePolyMesh(stage, path, counts, indices, points, ...)` |
| Pass raw `VtVec3fArray` for `normals=` | wrap in `Vec3fPrimvarData(interpolation, values[, indices])` |
| Author rectangular prism as a custom mesh | `defineCube` + `setLocalTransform` non-uniform scale |
| `mesh.CreatePrimvar("displayColor", ...)` then `Set(...)` | pass `displayColor=Vec3fPrimvarData(...)` to the define call; for primvars no helper covers use `<alias>.createPrimvar` or `createConstantPrimvar` |
| Compute and author normals when the source already has them | pass the source-provided `Vec3fPrimvarData`; reserve `computeMeshNormals` for missing data |
