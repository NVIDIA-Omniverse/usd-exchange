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
| `definePolyMesh(..., faceVertexCounts, faceVertexIndices, points, [normals], [uvs], [displayColor], [displayOpacity])` | Authors counts, indices, points, computed `extent`; right-handed orientation (reverse winding upstream if left-handed); forces `subdivisionScheme = none`. For subdiv surfaces, define then author the subdiv attributes manually. Optional primvar args take the typed `PrimvarData` aliases. Normals are authored as `primvars:normals`. |
| `computeMeshNormals(faceVertexCounts, faceVertexIndices, points, [interpolation], [fallback])` | Default `interpolation` is `uniform` (face); `vertex` is area-weighted; `faceVarying` assigns each face's normal to all of its corners. Returns `Vec3fPrimvarData`; the `(mesh, ...)` overload updates in place. Fall back only when source has no normals. |
| `definePartitionedSubsets` / `defineNonOverlappingSubsets` / `defineUnrestrictedSubsets(mesh, names, indices)` | Every-element / disjoint / overlapping. Default `elementType=face`, `familyName=materialBind`. Bind via `bindMaterialSubsets(subsets, materials)` (parallel vectors). |
| `defineLinearBasisCurves(..., curveVertexCounts, points, [wrap], [widths], [normals], [displayColor], [displayOpacity])` | `wrap`: `nonperiodic` (default) / `periodic`. |
| `defineCubicBasisCurves(..., curveVertexCounts, points, [basis], [wrap], [widths], [normals], [displayColor], [displayOpacity])` | `basis`: `bezier` (default), `bspline`, `catmullRom`. `wrap` also allows `pinned` for `bspline` / `catmullRom`. A single prim shares one `wrap` and one `basis`; split when source mixes them. **Authoring `normals` turns curves into oriented ribbons rather than tubes.** |
| `definePointCloud(..., points, [ids], [widths], [normals], [displayColor], [displayOpacity])` | Only `vertex` interpolation is valid for `normals`. `ids` is a raw `VtInt64Array` (not a `PrimvarData`). |
| `defineCube` / `defineSphere` / `defineCone` / `defineCylinder` / `defineCapsule` / `definePlane(..., [displayColor], [displayOpacity])` | Validate path is editable, compute correct extents. Cone / cylinder / capsule / plane accept an `axis` token (`X` / `Y` / `Z`; default `Z`). `displayColor` / `displayOpacity` are scalar (`GfVec3f` / `float`), not primvars. Approximate a rectangular prism via `defineCube` + non-uniform `setLocalTransform` scale; an ellipsoid via `defineSphere` + non-uniform scale. |
| `defineXform((stage, path) / (parent, name) / (prim), [transform])` | Optional `GfTransform` / `GfMatrix4d` lets you author the prim and its transform in one call. |
| `setLocalTransform(prim, ...)` | Overloads: `GfTransform`, `GfMatrix4d`, components (`translation`, `pivot`, `rotation` (degrees), `RotationOrder`, `scale`), or quaternion components (`translation`, `orientation`, `scale`). Reconciles with whatever `xformOp` order is already present. |
| `getLocalTransform` / `getLocalTransformMatrix` / `getLocalTransformComponents` / `getLocalTransformComponentsQuat` | Symmetric reads. `RotationOrder`: `eXyz` (default), `eXzy`, `eYxz`, `eYzx`, `eZxy`, `eZyx`. |

## Primvar data (`PrimvarData.h`)

Wrap every primvar payload in a `PrimvarData` (or typed alias). Construct `(interpolation, values)` non-indexed or `(interpolation, values, indices)` indexed. Validation deferred to `isValid()`.

| Alias | Element | Common use |
| --- | --- | --- |
| `FloatPrimvarData` / `IntPrimvarData` / `Int64PrimvarData` | `float` / `int` / `int64_t` | widths, displayOpacity, shader switches, ids |
| `TokenPrimvarData` / `StringPrimvarData` | `TfToken` / `string` | enum-like / human-readable descriptors (token lifetime is process-long) |
| `Vec2fPrimvarData` / `Vec3fPrimvarData` | `GfVec2f` / `GfVec3f` | UVs / normals, displayColor, vectors |

Methods: `isValid()` (interpolation, non-empty values, indices in range, element-size divisibility), `index()` (collapse duplicates; idempotent), `effectiveSize()` (deduplicated logical count), `isIdentical(other)` (confirms `VtArray` storage was not detached), `getPrimvarData(primvar)` / `setPrimvar(primvar)` (read / write a `UsdGeomPrimvar`). Canonical pattern: build typed `PrimvarData`, call `index()`, pass to the define helper as `normals=` / `uvs=` / `displayColor=` / etc. `elementSize` is rare; leave default.

## Anti-patterns

| Don't | Do |
| --- | --- |
| `UsdGeom.Mesh.Define(stage, path)` then write each attribute by hand | `usdex.core.definePolyMesh(stage, path, counts, indices, points, ...)` |
| Pass raw `VtVec3fArray` for `normals=` | wrap in `Vec3fPrimvarData(interpolation, values[, indices])` |
| Author rectangular prism as a custom mesh | `defineCube` + `setLocalTransform` non-uniform scale |
| `mesh.CreatePrimvar("displayColor", ...)` then `Set(...)` | pass `displayColor=Vec3fPrimvarData(...)` to the define call |
| Compute and author normals when the source already has them | pass the source-provided `Vec3fPrimvarData`; reserve `computeMeshNormals` for missing data |
