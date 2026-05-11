<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Cameras

`SKILL.md` (rules) is in context. Header: `usdex/core/CameraAlgo.h`.

## Functions

| Function | Use |
| --- | --- |
| `defineCamera((stage, path) / (parent, name) / (prim), gfCamera)` | Define a `UsdGeomCamera` (stage/path or parent/name) or convert an existing prim. The helper writes the full `Gf.Camera` state — projection, focal length, focus distance, fStop, clipping range, world-space transform if set. Returns invalid on validation failure. |

`Gf.Camera` covers projection (`perspective` / `orthographic`), aperture and offsets, focal length / focus distance / fStop, clipping range, and transform. It does **not** cover time samples, shutter window (`shutterOpen` / `shutterClose`), stereo role, or exposure — author those on the schema after `defineCamera` returns (e.g. `UsdGeomCamera(prim).GetShutterOpenAttr().Set(value, time)`).

Set the transform either on `Gf.Camera` before `defineCamera` (the helper writes it through) or via `usdex.core.setLocalTransform` afterward. Do not author both in the same pass. Use `cache.getPrimNames(parent, source_camera_names)` to allocate batched names when authoring multiple cameras under one parent.

## Anti-patterns

| Don't | Do |
| --- | --- |
| `UsdGeom.Camera.Define(stage, path)` plus per-attribute writes | populate `Gf.Camera` and call `usdex.core.defineCamera(parent, name, gfCam)` |
| Hard-code a literal name argument | `name=cache.getPrimName(parent, source.name)` |
| Author shutter / exposure / stereo via `Gf.Camera` | author on the schema after `defineCamera` returns |
| Mix `gfCamera.transform = ...` and `setLocalTransform` for the same prim in the same pass | choose one |
