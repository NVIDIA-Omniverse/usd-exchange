<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Physics

`SKILL.md` (rules) is in context. Headers: `usdex/core/PhysicsJointAlgo.h`, `usdex/core/PhysicsMaterialAlgo.h`. Geometry and visual materials are in their own files.

## Conventions

- Pass `massUnits=UsdPhysics.MassUnits.kilograms` (or your source value) to `createStage` / `configureStage` when physics is involved; defaults to kilograms when omitted.
- Gravity is derived from `upAxis` and `linearUnits` unless explicitly authored on the scene.
- Define visual / collision geometry via `usdex.core.define*` *first*, then apply API schemas — the helpers run editability checks.

## Scenes, bodies, colliders

`UsdPhysicsScene` has no helper. Allocate the scene name through the cache (`scene_name = cache.getPrimName(parent, scene_label)` where `scene_label` is a converter constant or source-derived variable) and call `UsdPhysics.Scene.Define(stage, parent.GetPath().AppendChild(scene_name))`. One scene per stage in normal use. Apply `UsdPhysics.RigidBodyAPI.Apply(prim)` on any `UsdGeomXformable` that simulates as a free body and `UsdPhysics.CollisionAPI.Apply(prim)` on any `UsdGeomGprim` that should collide. A static collider (e.g. ground plane) gets `CollisionAPI` only.

## Functions

| Function | Use |
| --- | --- |
| `definePhysicsMaterial((stage, path) / (parent, name) / (prim), dynamicFriction, [staticFriction], [restitution], [density])` | `UsdShadeMaterial` with `UsdPhysicsMaterialAPI` applied. Use when physics materials are managed separately from visuals. |
| `addPhysicsToMaterial(material, dynamicFriction, [staticFriction], [restitution], [density])` | Apply `UsdPhysicsMaterialAPI` to an existing visual `UsdShadeMaterial`. |
| `bindPhysicsMaterial(prim, material)` | Bind with the `physics` purpose, fallback strength. When one Material drives both rendering and simulation, call **both** `bindMaterial` and `bindPhysicsMaterial`. |
| `definePhysicsFixedJoint((stage, path) / (parent, name) / (prim), body0, body1, frame)` | Welds two bodies. Required even on reduced-coordinate solvers for cross-solver portability. |
| `definePhysicsRevoluteJoint(..., [axis], [lowerLimit], [upperLimit])` | Hinge around `axis` (default `(1,0,0)`); limits in degrees. Non-canonical axes are aligned to X via local rotations on both bodies. |
| `definePhysicsPrismaticJoint(..., [axis], [lowerLimit], [upperLimit])` | Slider along `axis`; limits in stage linear units. |
| `definePhysicsSphericalJoint(..., [axis], [coneAngle0Limit], [coneAngle1Limit])` | Ball-and-socket; cone limits in degrees. |
| `alignPhysicsJoint(joint, frame, [axis])` / `connectPhysicsJoint(joint, body0, body1, frame, [axis])` | Re-author local positions/orientations / repoint a joint at new bodies (or world if either body is invalid) and realign. |

`JointFrame` carries `space` (`Body0` / `Body1` / `World`), `position: GfVec3d`, `orientation: GfQuatd`. Doubles avoid precision loss before the schema cast to floats. The SDK derives body-local alignment from the frame, so the converter does not compute body-local transforms. For a free-floating chain, leave `body0` invalid on the first joint — the SDK connects it to world.

## Pattern: chain of capsules with fixed joints

Convention from the Samples: define geometry through `usdex.core` helpers, apply the API schemas, then express `JointFrame` in body1 space. `body_label` and `joint_label` are converter constants; `source` is the source object.

```python
body_names = cache.getPrimNames(parent.GetPath(), [source.name] * count)
joint_names = cache.getPrimNames(joints_xform.GetPath(), [joint_label] * count)
prev = parent
for i, body_name in enumerate(body_names):
    capsule = usdex.core.defineCapsule(parent, body_name, radius=r, height=h, axis=UsdGeom.Tokens.x)
    UsdPhysics.RigidBodyAPI.Apply(capsule.GetPrim())
    UsdPhysics.CollisionAPI.Apply(capsule.GetPrim())
    frame = usdex.core.JointFrame(usdex.core.JointFrame.Space.Body1, Gf.Vec3d(-h * 0.5, 0, 0), Gf.Quatd.GetIdentity())
    usdex.core.definePhysicsFixedJoint(joints_xform.GetPrim(), joint_names[i], prev.GetPrim(), capsule.GetPrim(), frame)
    prev = capsule
```

## Anti-patterns

| Don't | Do |
| --- | --- |
| Apply only one of `RigidBodyAPI` / `CollisionAPI` to a body that should collide | apply both — rigid bodies that collide need rigid-body *and* collision APIs |
| Compute body-local transforms by hand for every joint | author one `JointFrame` in the source's natural space; let the helper derive both body-locals |
| Skip `bindMaterial` because `bindPhysicsMaterial` was called | call **both** when one Material covers visuals and physics |
| `UsdPhysicsFixedJoint.Define(...)` then write `localPos0` / `localRot0` / `localPos1` / `localRot1` manually | `usdex.core.definePhysicsFixedJoint(parent, name, body0, body1, frame)` |
| Hard-code a string literal for the scene name | route a `scene_label` variable through `cache.getPrimName(parent, scene_label)` |
