<!-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Reference: Schema-defined Attributes

`SKILL.md` (rules) is in context. Header: `usdex/core/AttributeAlgo.h`. Covers authoring values on attributes declared by a typed or applied API schema, once the prim exists via a `define*` helper.

## Functions

| Function | Use |
| --- | --- |
| `setEffectiveAttributeValue(prim, name, value)` | Author `value` on the already-declared attribute `name` only when it differs from the schema fallback. Returns `False` (with a runtime error) if the attribute is not in the prim's composed definition. |

`name` is the attribute's name exactly as its schema declares it, namespaces included (`physics:mass`), so it is a literal you read off the schema rather than a name you allocate. Pass a plain `str` in Python — there is no `Tf.Token` type — or a `TfToken` in C++. The value must match the attribute's `SdfValueTypeName` or be trivially convertible (`double` → `float`); Python accepts a `list` for array-typed attributes. Reach for the `PrimvarData` helpers for primvars instead.

## Why it matters

Sparse layers compose better and diff smaller. When the supplied value equals the schema fallback, the function does the right thing per case rather than writing a redundant opinion:

| Existing state | Result |
| --- | --- |
| No authored opinion | Nothing authored — the edit target stays sparse. |
| Authored in a weaker layer | Blocked via `Usd.Attribute.Block()`, so the fallback wins. |
| Authored in the current edit target | Cleared via `Usd.Attribute.Clear()`. |

An empty / invalid sentinel value also blocks the attribute. To drop an opinion from the current edit target *without* shadowing weaker layers, call `Usd.Attribute.Clear()` directly instead.

This is most valuable with codeless schemas, which generate no accessors or token constants — there is no `CreateFooAttr()` to call, so the alternative is a raw `prim.GetAttribute(name).Set(value)` that cannot see the fallback.

## Anti-patterns

| Don't | Do |
| --- | --- |
| `prim.CreateAttribute(name, typeName)` for an attribute a schema already declares | apply the schema (or use the `define*` helper), then `setEffectiveAttributeValue(prim, name, value)` |
| `prim.GetAttribute(name).Set(value)` for every source value, fallbacks included | `setEffectiveAttributeValue(prim, name, value)` so schema-default values stay unauthored |
| Compare against a hard-coded default before writing | let the function compare against the composed schema fallback |
