// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include "usdex/core/PrimvarData.h"

#include <pybind11/operators.h>
#include <pybind11/pybind11.h>

#include <sstream>

using namespace usdex::core;
using namespace pybind11;

namespace
{

template <typename T>
void bindPrimvarDataImpl(module& m, const std::string& typeName, const std::string& brief)
{
    static constexpr const char* classDescription = R"(

            This is a read-only class to manage all ``UsdGeom.Primvar`` data as a single object without risk of detaching (copying) arrays.

            ``UsdGeom.Primvars`` are often used when authoring ``UsdGeom.PointBased`` prims (e.g meshes, curves, and point clouds) to describe surface varying
            properties that can affect how a prim is rendered, or to drive a surface deformation.

            However, ``UsdGeom.Primvar`` data can be quite intricate to use, especially with respect to indexed vs non-indexed primvars, element size, the
            complexities of ``Vt.Array`` detach (copy-on-write) semantics, and the ambiguity of "native" attributes vs primvar attributes (e.g. mesh normals).

            This class aims to provide simpler entry points to avoid common mistakes with respect to ``UsdGeom.Primvar`` data handling.

            All of the USD authoring "define" functions in this library accept optional ``PrimvarData`` to define e.g normals, display colors, etc.
        )";
    std::string classDoc = brief + classDescription;

    ::class_<PrimvarData<T>> binder(m, typeName.c_str(), classDoc.c_str());

    binder.def(
        init<const pxr::TfToken&, const pxr::VtArray<T>&, int>(),
        arg("interpolation"),
        arg("values"),
        arg("elementSize") = -1,
        R"(
            Construct non-indexed ``PrimvarData``.

            Note:
                To avoid immediate array iteration, validation does not occur during construction, and is deferred until ``isValid()`` is called.
                This may be counter-intuitive as ``PrimvarData`` provides read-only access, but full validation is often only possible within the context
                of specific surface topology, so premature validation would be redundant.

            Args:
                interpolation: The primvar interpolation. Must match ``UsdGeom.Primvar.IsValidInterpolation()`` to be considered valid.
                values: Read-only accessor to the values array.
                elementSize: Optional element size. This should be fairly uncommon.
                    See [GetElementSize](https://openusd.org/release/api/class_usd_geom_primvar.html#a711c3088ebca00ca75308485151c8590) for details.

            Returns:
                The read-only ``PrimvarData``.
        )"
    );

    binder.def(
        init<const pxr::TfToken&, const pxr::VtArray<T>&, const pxr::VtArray<int>&, int>(),
        arg("interpolation"),
        arg("values"),
        arg("indices"),
        arg("elementSize") = -1,
        R"(
            Construct indexed ``PrimvarData``.

            Note:
                To avoid immediate array iteration, validation does not occur during construction, and is deferred until ``isValid()`` is called.
                This may be counter-intuitive as ``PrimvarData`` provides read-only access, but full validation is often only possible within the context
                of specific surface topology, so premature validation would be redundant.

            Args:
                interpolation: The primvar interpolation. Must match ``UsdGeom.Primvar.IsValidInterpolation()`` to be considered valid.
                values: Read-only accessor to the values array.
                indices: Read-only accessor to the indices array.
                elementSize: Optional element size. This should be fairly uncommon.
                    See [GetElementSize](https://openusd.org/release/api/class_usd_geom_primvar.html#a711c3088ebca00ca75308485151c8590) for details.

            Returns:
                The read-only ``PrimvarData``.
        )"
    );

    binder.def_static(
        "getPrimvarData",
        &PrimvarData<T>::getPrimvarData,
        arg("primvar"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Construct a ``PrimvarData`` from a ``UsdGeom.Primvar`` that has already been authored.

            The primvar may be indexed, non-indexed, with or without elements, or it may not even be validly authored scene description.
            Use ``isValid()`` to confirm that valid data has been gathered.

            Args:
                primvar: The previously authored ``UsdGeom.Primvar``.
                time: The time at which the attribute values are read.

            Returns:
                The read-only ``PrimvarData``.
        )"
    );

    binder.def(
        "setPrimvar",
        &PrimvarData<T>::setPrimvar,
        arg("primvar"),
        arg("time") = UsdTimeCode::Default().GetValue(),
        R"(
            Set data on an existing ``UsdGeom.Primvar`` from a ``PrimvarData`` that has already been authored.

            Any existing authored data on the primvar will be overwritten or blocked with the ``PrimvarData`` members.

            To copy data from one ``UsdGeom.Primvar`` to another, use ``data: PrimvarData = PrimvarData.get(primvar: UsdGeom.Primvar)`` to gather the data,
            then use ``setPrimvar(primvar: UsdGeom.Primvar)`` to author it.

            Args:
                primvar: The previously authored ``UsdGeom.Primvar``.
                time: The time at which the attribute values are written.

            Returns:
                Whether the ``UsdGeom.Primvar`` was completely authored from the member data.
                Any failure to author may leave the primvar in an unknown state (e.g. it may have been partially authored).
        )"
    );

    binder.def(
        "interpolation",
        &PrimvarData<T>::interpolation,
        R"(
            The geometric interpolation.

            It may be an invalid interpolation. Use ``PrimvarData.isValid()`` or ``UsdGeom.Primvar.IsValidInterpolation()`` to confirm.

            Returns:
                The geometric interpolation.
        )"
    );

    binder.def(
        "values",
        &PrimvarData<T>::values,
        R"(
            Access to the values array.

            Bear in mind the values may need to be accessed via ``indices()`` or using an ``elementSize()`` stride.

            It may contain an empty or invalid values array.

            Returns:
                The primvar values.
        )"
    );

    binder.def(
        "hasIndices",
        &PrimvarData<T>::hasIndices,
        R"(
            Whether this is indexed or non-indexed ``PrimvarData``

            Returns:
                Whether this is indexed or non-indexed ``PrimvarData``.
        )"
    );

    binder.def(
        "indices",
        &PrimvarData<T>::indices,
        R"(
            Access to the indices array.

            This method throws a runtime error if the ``PrimvarData`` is not indexed. For exception-free access, check ``hasIndices()`` before calling this.

            Note:
                It may contain an empty or invalid indices array. Use ``PrimvarData.isValid()`` to validate that the indices are not out-of-range.

            Returns:
                The primvar indices
        )"
    );

    binder.def(
        "elementSize",
        &PrimvarData<T>::elementSize,
        R"(
            The element size.

            Any value less than 1 is considered "non authored" and indicates no element size. This should be the most common case, as element size is a
            fairly esoteric extension of ``UsdGeom.Primvar`` data to account for non-typed array strides such as spherical harmonics float[9] arrays.

            See ``UsdGeom.Primvar.GetElementSize()`` for more details.

            Returns:
                The primvar element size.
        )"
    );

    binder.def(
        "effectiveSize",
        &PrimvarData<T>::effectiveSize,
        R"(
            The effective size of the data, having accounted for values, indices, and element size.

            This is the number of variable values that "really" exist, as far as a consumer is concerned. The indices & elementSize are used as a storage
            optimization, but the consumer should consider the effective size as the number of "deduplicated" individual values.

            Returns:
                The effective size of the data.
        )"
    );

    binder.def(
        "isValid",
        &PrimvarData<T>::isValid,
        R"(
            Whether the data is valid or invalid.

            This is a validation check with respect to the ``PrimvarData`` itself & the requirements of ``UsdGeom.Prim``. It does not validate with respect to
            specific surface topology data, as no such data is available or consistant across ``UsdGeom.PointBased`` prim types.

            This validation checks the following, in this order, and returns false if any condition fails:

                - The interpolation matches ``UsdGeom.Primvar.IsValidInterpolation()``.
                - The values are not empty. Note that individual values may be invalid (e.g ``NaN`` values on a ``Vt.FloatArray``) but this will not be
                  considered a failure, as some workflows allow for ``NaN`` to indicate non-authored elements or "holes" within the data.
                - If it is non-indexed, and has elements, that the values divide evenly by elementSize.
                - If it is indexed, and has elements, that the indices divide evenly by elementSize.
                - If it is indexed, that the indices are all within the expected range of the values array.

            Returns:
                Whether the data is valid or invalid.
        )"
    );

    binder.def(
        "isIdentical",
        &PrimvarData<T>::isIdentical,
        arg("other"),
        R"(
            Check that all data between two ``PrimvarData`` objects is identical.

            This differs from the equality operator in that it ensures the ``Vt.Array`` values and indices have not detached.

            Args:
                other: The other ``PrimvarData``.

            Returns:
                True if all the member data is equal and arrays are identical.
        )"
    );

    binder.def(
        "index",
        &PrimvarData<T>::index,
        R"(
            Update the values and indices of this ``PrimvarData`` object to avoid duplicate values.

            Updates will not be made in the following conditions:
                - If element size is greater than one.
                - If the existing indexing is efficient.
                - If there are no duplicate values.
                - If the existing indices are invalid

            Returns:
                True if the values and/or indices were modified.
        )"
    );

    binder.def(
        "hasUnindexedValues",
        &PrimvarData<T>::hasUnindexedValues,
        R"(
            Check whether any entries in the values array are never referenced by the indices.

            If ``hasIndices()`` is false, returns false.

            Returns:
                True if at least one value slot is not the target of any index.
        )"
    );

    binder.def(
        self == self,
        R"(
            Check that all data between two ``PrimvarData`` objects is identical.

            This differs from the equality operator in that it ensures the ``Vt.Array`` values and indices have not detached.

            Args:
                other: The other ``PrimvarData``.

            Returns:
                True if all the member data is equal (but not necessarily identical arrays).
        )"
    );

    binder.def(
        self != self,
        R"(
            Check for in-equality between two ``PrimvarData`` objects.

            Args:
                other: The other ``PrimvarData``.

            Returns:
                True if any member data is not equal (but does not guarantee identical arrays).
        )"
    );

    binder.def(
        "__str__",
        [typeName](const PrimvarData<T>& primvar)
        {
            std::stringstream ss;
            ss << "usdex.core." << typeName << "(";
            ss << "interpolation=\"" << primvar.interpolation() << "\"";
#if defined(_WIN32)
            __pragma(warning(push));
            __pragma(warning(disable : 4459)); // disable warning C4459: declaration of 'self' hides global declaration
#endif
            ss << ", values=" << primvar.values();
            if (primvar.hasIndices())
            {
                ss << ", indices=" << primvar.indices();
            }
#if defined(_WIN32)
            __pragma(warning(pop));
#endif
            ss << ", elementSize=" << primvar.elementSize();
            ss << ")";
            return ss.str();
        }
    );
}

} // namespace

namespace usdex::core::bindings
{

void bindPrimvarData(module& m)
{
    bindPrimvarDataImpl<float>(m, "FloatPrimvarData", "``PrimvarData`` that holds ``Vt.FloatArray`` values (e.g widths or scale factors).");
    bindPrimvarDataImpl<int64_t>(m, "Int64PrimvarData", "``PrimvarData`` that holds ``Vt.Int64Array`` values (e.g ids that might be very large).");
    bindPrimvarDataImpl<int>(
        m,
        "IntPrimvarData",
        "``PrimvarData`` that holds ``Vt.IntArray`` values (e.g simple switch values or booleans consumable by shaders)."
    );
    bindPrimvarDataImpl<std::string>(m, "StringPrimvarData", "``PrimvarData`` that holds ``Vt.StringArray`` values (e.g human readable descriptors).");
    bindPrimvarDataImpl<TfToken>(
        m,
        "TokenPrimvarData",
        R"(
            ``PrimvarData`` that holds ``Vt.TokenArray`` values (e.g more efficient human readable descriptors).

            This is a more efficient format than raw strings if you have many repeated values across different prims.

            Note:
                ``TfToken`` lifetime lasts the entire process. Too many tokens in memory may consume resources somewhat unexpectedly.
        )"
    );
    bindPrimvarDataImpl<GfVec2f>(m, "Vec2fPrimvarData", "``PrimvarData`` that holds ``Vt.Vec2fArray`` values (e.g texture coordinates).");
    bindPrimvarDataImpl<GfVec3f>(
        m,
        "Vec3fPrimvarData",
        "``PrimvarData`` that holds ``Vt.Vec3fArray`` values (e.g normals, colors, or other vectors)."
    );
}

} // namespace usdex::core::bindings
