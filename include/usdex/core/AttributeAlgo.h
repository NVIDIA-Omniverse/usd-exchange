// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/core/AttributeAlgo.h
//! @brief Utility functions for authoring schema-defined `UsdAttribute` values.

#include "Api.h"

#include <pxr/base/tf/token.h>
#include <pxr/base/vt/value.h>
#include <pxr/usd/usd/prim.h>

namespace usdex::core
{

//! @defgroup attributes Schema-defined Attributes
//!
//! Utility functions for authoring values on [UsdAttribute](https://openusd.org/release/api/class_usd_attribute.html)
//! properties that are declared by applied API or typed prim schemas.
//!
//! These helpers are especially useful when authoring from codeless schemas that do not provide generated
//! schema accessors or `TfToken` constants for attribute names.
//!
//! @{

//! Author a value on a defined attribute only if the value differs from the attribute's fallback (default) value.
//!
//! This enables sparse authoring of layers that only contain opinions differing from schema defaults.
//!
//! The attribute must already be declared on the prim's composed prim definition (for example after applying
//! the relevant API schema). If the attribute is not defined, a coding error is emitted and no value is authored.
//!
//! When the supplied value is equal to the schema fallback (default) value:
//! - If the attribute does not have an existing authored opinion, no new opinion will be authored, enabling the current edit target to remain a
//! sparse layer.
//! - If the attribute has an authored opinion in a weaker layer, it will be explicitly blocked via ``Usd.Attribute.Block()``, enabling the fallback
//! to become the strongest opinion.
//! - If the attribute has an authored opinion only in the current edit target, it will be cleared via ``Usd.Attribute.Clear()``.
//!
//! If the supplied value is an empty/invalid sentinal value, the attribute is also blocked via
//! `UsdAttribute::Block()`. This prevents opinions on weaker sublayers from contributing to the
//! composed value. To remove an opinion from the current edit target without blocking weaker
//! layers, call `UsdAttribute::Clear()` directly instead.
//!
//! The value must match the attribute's `SdfValueTypeName`, or be trivially convertible (for example `double` to
//! `float`). In Python, a `list` may be supplied for array-typed attributes and will be converted to the
//! corresponding `VtArray` type. Otherwise a coding error is emitted and no value is authored.
//!
//! @param prim The prim on which to author the attribute
//! @param name The name of the defined attribute
//! @param value The value to author when it differs from the schema fallback
//! @returns True on success, otherwise false
USDEX_API bool setEffectiveAttributeValue(const pxr::UsdPrim& prim, const pxr::TfToken& name, const pxr::VtValue& value);

//! @}

} // namespace usdex::core
