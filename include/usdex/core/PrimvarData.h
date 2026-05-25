// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

//! @file usdex/core/PrimvarData.h
//! @brief A class to manage and validate `UsdGeomPrimvar` data prior to authoring

#include "Api.h"

#include <pxr/base/gf/vec2f.h>
#include <pxr/base/gf/vec3f.h>
#include <pxr/base/tf/token.h>
#include <pxr/base/vt/array.h>
#include <pxr/usd/usdGeom/primvar.h>

namespace usdex::core
{

//! @defgroup primvars Primvar Data Management
//!
//! Utilities to author and inspect [UsdGeomPrimvars](https://openusd.org/release/api/class_usd_geom_primvar.html)
//!
//! `UsdGeomPrimvars` are often used when authoring `UsdGeomPointBased` prims (e.g meshes, curves, and point clouds) to describe surface varying
//! properties that can affect how a prim is rendered, or to drive a surface deformation.
//!
//! However, `UsdGeomPrimvar` data can be quite intricate to use, especially with respect to indexed vs non-indexed primvars, element size, the
//! complexities of `VtArray` detach (copy-on-write) semantics, and the ambiguity of "native" attributes vs primvar attributes (e.g. mesh normals).
//!
//! These classes aim to provide simpler entry points to avoid common mistakes with respect to `UsdGeomPrimvar` data handling.
//!
//! @{

//! A templated read-only class to manage the components of `UsdGeomPrimvar` data as a single object without risk of detaching (copying) arrays.
//!
//! All of the USD authoring "define" functions in this library accept optional `PrimvarData` to define e.g normals, display colors, etc.
template <typename T>
class PrimvarData
{

public:

    //! Construct non-indexed `PrimvarData`.
    //!
    //! @note To avoid immediate array iteration, validation does not occur during construction, and is deferred until `isValid()` is called.
    //!     This may be counter-intuitive as `PrimvarData` provides read-only access, but full validation is often only possible within the context
    //!     of specific surface topology, so premature validation would be redundant.
    //!
    //! @param interpolation The primvar interpolation. Must match `UsdGeomPrimvar::IsValidInterpolation()` to be considered valid.
    //! @param values Read-only accessor to the values array.
    //! @param elementSize Optional element size. This should be fairly uncommon.
    //!     See [GetElementSize](https://openusd.org/release/api/class_usd_geom_primvar.html#a711c3088ebca00ca75308485151c8590) for details.
    //!
    //! @returns The read-only `PrimvarData`.
    PrimvarData(const pxr::TfToken& interpolation, const pxr::VtArray<T>& values, int elementSize = -1);

    //! Construct indexed `PrimvarData`.
    //!
    //! @note To avoid immediate array iteration, validation does not occur during construction, and is deferred until `isValid()` is called.
    //!     This may be counter-intuitive as `PrimvarData` provides read-only access, but full validation is often only possible within the context
    //!     of specific surface topology, so premature validation would be redundant.
    //!
    //! @param interpolation The primvar interpolation. Must match `UsdGeomPrimvar::IsValidInterpolation()` to be considered valid.
    //! @param values Read-only accessor to the values array.
    //! @param indices Read-only accessor to the indices array.
    //! @param elementSize Optional element size. This should be fairly uncommon.
    //!     See [GetElementSize](https://openusd.org/release/api/class_usd_geom_primvar.html#a711c3088ebca00ca75308485151c8590) for details.
    //!
    //! @returns The read-only `PrimvarData`.
    PrimvarData(const pxr::TfToken& interpolation, const pxr::VtArray<T>& values, const pxr::VtArray<int>& indices, int elementSize = -1);

    //! Construct a `PrimvarData` from a `UsdGeomPrimvar` that has already been authored.
    //!
    //! The primvar may be indexed, non-indexed, with or without elements, or it may not even be validly authored scene description.
    //! Use `isValid()` to confirm that valid data has been gathered.
    //!
    //! @param primvar The previously authored `UsdGeomPrimvar`.
    //! @param time The time at which the attribute values are read.
    //!
    //! @returns The read-only `PrimvarData`.
    static PrimvarData getPrimvarData(const pxr::UsdGeomPrimvar& primvar, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default());

    //! Set data on an existing `UsdGeomPrimvar` from a `PrimvarData` that has already been authored.
    //!
    //! Any existing authored data on the primvar will be overwritten or blocked with the `PrimvarData` members.
    //!
    //! To copy data from one `UsdGeomPrimvar` to another, use `PrimvarData::get(UsdGeomPrimvar&)` to gather the data,
    //! then use `setPrimvar(UsdGeomPrimvar&)` to author it.
    //!
    //! @param primvar The previously authored `UsdGeomPrimvar`.
    //! @param time The time at which the attribute values are written.
    //!
    //! @returns Whether the `UsdGeomPrimvar` was completely authored from the member data.
    //!     Any failure to author may leave the primvar in an unknown state (e.g. it may have been partially authored).
    bool setPrimvar(pxr::UsdGeomPrimvar& primvar, pxr::UsdTimeCode time = pxr::UsdTimeCode::Default()) const;

    //! The geometric interpolation.
    //!
    //! It may be an invalid interpolation. Use `PrimvarData::isValid()` or `UsdGeomPrimvar::IsValidInterpolation()` to confirm.
    //!
    //! @returns The geometric interpolation.
    const pxr::TfToken& interpolation() const;

    //! Read-only access to the values array.
    //!
    //! Bear in mind the values may need to be accessed via `indices()` or using an `elementSize()` stride.
    //!
    //! It may contain an empty or invalid values array.
    //!
    //! @returns The primvar values.
    const pxr::VtArray<T>& values() const;

    //! Whether this is indexed or non-indexed `PrimvarData`
    //!
    //! @returns Whether this is indexed or non-indexed `PrimvarData`.
    bool hasIndices() const;

    //! Read-only access to the indices array.
    //!
    //! This method throws a runtime error if the `PrimvarData` is not indexed. For exception-free access, check `hasIndices()` before calling this.
    //!
    //! @note It may contain an empty or invalid indices array. Use `PrimvarData::isValid()` to validate that the indices are not out-of-range.
    //!
    //! @returns The primvar indices.
    const pxr::VtArray<int>& indices() const;

    //! The element size.
    //!
    //! Any value less than 1 is considered "non authored" and indicates no element size. This should be the most common case, as element size is a
    //! fairly esoteric extension of `UsdGeomPrimvar` data to account for non-typed array strides such as spherical harmonics float[9] arrays.
    //!
    //! See [GetElementSize](https://openusd.org/release/api/class_usd_geom_primvar.html#a711c3088ebca00ca75308485151c8590) for more details.
    //!
    //! @returns The primvar element size.
    int elementSize() const;

    //! The effective size of the data, having accounted for values, indices, and element size.
    //!
    //! This is the number of variable values that "really" exist, as far as a consumer is concerned. The indices & elementSize are used as a storage
    //! optimization, but the consumer should consider the effective size as the number of "deduplicated" individual values.
    //!
    //! @returns The effective size of the data.
    size_t effectiveSize() const;

    //! Whether the data is valid or invalid.
    //!
    //! This is a validation check with respect to the `PrimvarData` itself & the requirements of `UsdGeomPrim`. It does not validate with respect to
    //! specific surface topology data, as no such data is available or consistant across `UsdGeomPointBased` prim types.
    //!
    //! This validation checks the following, in this order, and returns false if any condition fails:
    //!  - The interpolation matches `UsdGeomPrimvar::IsValidInterpolation()`.
    //!  - The values are not empty. Note that individual values may be invalid (e.g `NaN` values on a `VtFloatArray`) but this will not be
    //!     considered a failure, as some workflows allow for `NaN` to indicate non-authored elements or "holes" within the data.
    //!  - If it is non-indexed, and has elements, that the values divide evenly by elementSize.
    //!  - If it is indexed, and has elements, that the indices divide evenly by elementSize.
    //!  - If it is indexed, that the indices are all within the expected range of the values array.
    //!
    //! @returns Whether the data is valid or invalid.
    bool isValid() const;

    //! Check that all data between two `PrimvarData` objects is identical.
    //!
    //! This differs from the equality operator in that it ensures the `VtArray` values and indices have not detached.
    //!
    //! @param other The other `PrimvarData`.
    //!
    //! @returns True if all the member data is equal and arrays are identical.
    bool isIdentical(const PrimvarData& other) const;

    //! Update the values and indices of this `PrimvarData` object to avoid duplicate values.
    //!
    //! Updates will not be made in the following conditions:
    //!  - If element size is greater than one.
    //!  - If the existing indexing is efficient.
    //!  - If there are no duplicate values.
    //!  - If the existing indices are invalid
    //!
    //! @returns True if the values and/or indices were modified.
    bool index();

    //! Check whether any entries in the values array are never referenced by the indices.
    //!
    //! If `hasIndices()` is false, returns false.
    //!
    //! @returns True if at least one value slot is not the target of any index.
    bool hasUnindexedValues() const;

    //! Check for equality between two `PrimvarData` objects.
    //!
    //! @param other The other `PrimvarData`.
    //!
    //! @returns True if all the member data is equal (but not necessarily identical arrays).
    bool operator==(const PrimvarData& other) const;

    //! Check for in-equality between two `PrimvarData` objects.
    //!
    //! @param other The other `PrimvarData`.
    //!
    //! @returns True if any member data is not equal (but does not check for identical arrays).
    bool operator!=(const PrimvarData& other) const;

private:

    pxr::TfToken m_interpolation;
    int m_elementSize;
    pxr::VtArray<T> m_values;
    pxr::VtArray<int> m_indices;
};

//! An alias for `PrimvarData` that holds `VtFloatArray` values (e.g widths or scale factors).
using FloatPrimvarData = PrimvarData<float>;
//! An alias for `PrimvarData` that holds `VtInt64Array` values (e.g ids that might be very large).
using Int64PrimvarData = PrimvarData<int64_t>;
//! An alias for `PrimvarData` that holds `VtIntArray` values (e.g simple switch values or booleans consumable by shaders).
using IntPrimvarData = PrimvarData<int>;
//! An alias for `PrimvarData` that holds `VtStringArray` values (e.g human readable descriptors).
using StringPrimvarData = PrimvarData<std::string>;
//! An alias for `PrimvarData` that holds `VtTokenArray` values (e.g more efficient human readable descriptors).
//!
//! This is a more efficient format than raw strings if you have many repeated values across different prims.
//!
//! @note `TfToken` lifetime lasts the entire process. Too many tokens in memory may consume resources somewhat unexpectedly.
using TokenPrimvarData = PrimvarData<pxr::TfToken>;
//! An alias for `PrimvarData` that holds `VtVec2fArray` values (e.g texture coordinates).
using Vec2fPrimvarData = PrimvarData<pxr::GfVec2f>;
//! An alias for `PrimvarData` that holds `VtVec3fArray` values (e.g normals, colors, or other vectors).
using Vec3fPrimvarData = PrimvarData<pxr::GfVec3f>;

//! @}

} // namespace usdex::core

#include "usdex/core/PrimvarData.inl"
