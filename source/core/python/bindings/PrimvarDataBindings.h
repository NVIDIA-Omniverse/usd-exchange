// SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

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
        "createPrimvar",
        [](const PrimvarData<T>& primvarData, pxr::UsdPrim prim, const std::string& name, pybind11::object valueTypeName)
        {
            pxr::SdfValueTypeName sdfValueTypeName;
            if (!valueTypeName.is_none())
            {
                sdfValueTypeName = valueTypeName.cast<pxr::SdfValueTypeName>();
            }
            return primvarData.createPrimvar(prim, name, sdfValueTypeName);
        },
        arg("prim"),
        arg("name"),
        arg("valueTypeName") = pybind11::none(),
        R"(
            Create and author a primvar on a prim from this data.

            Construct ``PrimvarData`` with the desired interpolation, values, indices, and element size, then call this method to create and
            author the primvar on ``prim``. To author at additional times, use ``setPrimvar()``.

            Args:
                prim: The prim on which to create the primvar.
                name: The primvar name (not including the ``primvars:`` prefix).
                valueTypeName: Optional USD value type for the primvar attribute. When omitted, a default array type is chosen for the ``PrimvarData`` value type (for example ``Float3Array`` for ``Vec3fPrimvarData``). For ``Vec3fPrimvarData``, ``Color3fArray``, ``Normal3fArray``, and ``Point3fArray`` are also supported. The scalar types ``Color3f``, ``Normal3f``, and ``Point3f`` are accepted as aliases and are converted to their corresponding array types internally.

            Returns:
                Whether the primvar was successfully created and authored from this data.
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

template <typename Ret, typename Arg>
void bindCreateConstantPrimvarOverloadImpl(
    module& m,
    Ret (*fn)(pxr::UsdPrim, const std::string&, Arg, const pxr::SdfValueTypeName&),
    const char* docstring,
    bool noconvertValue = false
)
{
    auto valueArg = arg("value");
    if (noconvertValue)
    {
        valueArg.noconvert();
    }

    m.def(
        "createConstantPrimvar",
        [fn](pxr::UsdPrim prim, const std::string& name, Arg value, pybind11::object valueTypeName)
        {
            pxr::SdfValueTypeName sdfValueTypeName;
            if (!valueTypeName.is_none())
            {
                sdfValueTypeName = valueTypeName.cast<pxr::SdfValueTypeName>();
            }
            return fn(prim, name, value, sdfValueTypeName);
        },
        arg("prim"),
        arg("name"),
        valueArg,
        arg("valueTypeName") = pybind11::none(),
        docstring
    );
}

template <typename Ret, typename Arg>
void bindCreateConstantPrimvarOverload(
    module& m,
    Ret (*fn)(pxr::UsdPrim, const std::string&, Arg, const pxr::SdfValueTypeName&),
    bool isOverload = true
)
{
    static constexpr const char* primaryDoc = R"(
            Create and author a constant primvar on a prim from a single scalar value.

            This is a convenience wrapper around constructing ``PrimvarData`` with ``constant`` interpolation
            and a single-element values array, then calling ``createPrimvar()``.
            On failure an invalid ``UsdGeom.Primvar`` is returned and a warning is emitted.

            Args:
                prim: The prim on which to create the primvar.
                name: The primvar name (not including the ``primvars:`` prefix).
                value: The constant primvar value.
                valueTypeName: Optional USD array value type for the primvar attribute. When omitted, a default array type is chosen for the value type.

            Returns:
                The authored ``UsdGeom.Primvar``, or an invalid one if authoring failed.
        )";
    static constexpr const char* overloadDoc = R"(
            Create and author a constant primvar on a prim from a single scalar value.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Args:
                prim: The prim on which to create the primvar.
                name: The primvar name (not including the ``primvars:`` prefix).
                value: The constant primvar value.
                valueTypeName: Optional USD array value type for the primvar attribute. When omitted, a default array type is chosen for the value type.

            Returns:
                The authored ``UsdGeom.Primvar``, or an invalid one if authoring failed.
        )";
    bindCreateConstantPrimvarOverloadImpl(m, fn, isOverload ? overloadDoc : primaryDoc);
}

void bindCreateConstantStringPrimvar(module& m)
{
    static constexpr const char* doc = R"(
            Create and author a constant ``String`` or ``Token`` primvar on a prim from a single Python ``str`` value.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Note: In Python, USD tokens such as ``UsdGeom.Tokens.vertex`` are also ``str``. When ``valueTypeName`` is omitted or is ``StringArray``, a ``StringArray`` primvar is authored. When ``valueTypeName`` is ``TokenArray``, a ``TokenArray`` primvar is authored instead.

            Args:
                prim: The prim on which to create the primvar.
                name: The primvar name (not including the ``primvars:`` prefix).
                value: The constant primvar value.
                valueTypeName: Optional USD array value type for the primvar attribute. When omitted, ``StringArray`` is used. Specify ``TokenArray`` to author a ``TokenArray`` primvar.

            Returns:
                The authored ``UsdGeom.Primvar``, or an invalid one if authoring failed.
        )";
    m.def(
        "createConstantPrimvar",
        [](pxr::UsdPrim prim, const std::string& name, const std::string& value, pybind11::object valueTypeName) -> pxr::UsdGeomPrimvar
        {
            pxr::SdfValueTypeName sdfValueTypeName;
            if (!valueTypeName.is_none())
            {
                sdfValueTypeName = valueTypeName.cast<pxr::SdfValueTypeName>();
            }
            if (sdfValueTypeName == pxr::SdfValueTypeNames->TokenArray)
            {
                return createConstantPrimvar(prim, name, pxr::TfToken(value), sdfValueTypeName);
            }
            return createConstantPrimvar(prim, name, value, sdfValueTypeName);
        },
        arg("prim"),
        arg("name"),
        arg("value").noconvert(),
        arg("valueTypeName") = pybind11::none(),
        doc
    );
}

void bindCreateConstantVec3fPrimvar(module& m)
{
    static constexpr const char* doc = R"(
            Create and author a constant ``Float3`` (or color/normal/point) primvar on a prim from a single vector value.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Args:
                prim: The prim on which to create the primvar.
                name: The primvar name (not including the ``primvars:`` prefix).
                value: The constant primvar value.
                valueTypeName: Optional USD value type for the primvar attribute. When omitted, ``Float3Array`` is used. ``Color3fArray``, ``Normal3fArray``, and ``Point3fArray`` are also supported. The scalar types ``Color3f``, ``Normal3f``, and ``Point3f`` are accepted as aliases and are converted to their corresponding array types internally.

            Returns:
                The authored ``UsdGeom.Primvar``, or an invalid one if authoring failed.
        )";
    bindCreateConstantPrimvarOverloadImpl(
        m,
        static_cast<pxr::UsdGeomPrimvar (*)(pxr::UsdPrim, const std::string&, const pxr::GfVec3f&, const pxr::SdfValueTypeName&)>(
            &createConstantPrimvar
        ),
        doc
    );
}

template <typename Arg>
void bindSetConstantPrimvarOverload(module& m, bool (*fn)(pxr::UsdPrim, const std::string&, Arg, pxr::UsdTimeCode), bool isOverload = true)
{
    static constexpr const char* primaryDoc = R"(
            Set data on an existing constant primvar from a single scalar value.

            This is a convenience wrapper around constructing ``PrimvarData`` with ``constant`` interpolation
            and a single-element values array, then calling ``setPrimvar()`` on the existing primvar.
            On failure a warning is emitted.

            Args:
                prim: The prim that owns the primvar.
                name: The primvar name (not including the ``primvars:`` prefix).
                value: The constant primvar value.
                time: The time at which the value is written.

            Returns:
                Whether the primvar was successfully set.
        )";
    static constexpr const char* overloadDoc = R"(
            Set data on an existing constant primvar from a single scalar value.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Args:
                prim: The prim that owns the primvar.
                name: The primvar name (not including the ``primvars:`` prefix).
                value: The constant primvar value.
                time: The time at which the value is written.

            Returns:
                Whether the primvar was successfully set.
        )";
    m.def(
        "setConstantPrimvar",
        [fn](pxr::UsdPrim prim, const std::string& name, Arg value, double time)
        {
            return fn(prim, name, value, pxr::UsdTimeCode(time));
        },
        arg("prim"),
        arg("name"),
        arg("value"),
        arg("time") = pxr::UsdTimeCode::Default().GetValue(),
        isOverload ? overloadDoc : primaryDoc
    );
}

void bindSetConstantStringPrimvar(module& m)
{
    static constexpr const char* doc = R"(
            Set data on an existing constant ``String`` or ``Token`` primvar from a single Python ``str`` value.

            This is an overloaded member function, provided for convenience. It differs from the above function only in what arguments it accepts.

            Note: In Python, USD tokens such as ``UsdGeom.Tokens.vertex`` are also ``str``. When the existing primvar is a ``TokenArray``,
            the value is automatically interpreted as a ``TfToken``. For all other primvar types, the value is treated as a ``str``.

            Args:
                prim: The prim that owns the primvar.
                name: The primvar name (not including the ``primvars:`` prefix).
                value: The constant primvar value.
                time: The time at which the value is written.

            Returns:
                Whether the primvar was successfully set.
        )";
    m.def(
        "setConstantPrimvar",
        [](pxr::UsdPrim prim, const std::string& name, const std::string& value, double time) -> bool
        {
            pxr::UsdGeomPrimvar primvar = pxr::UsdGeomPrimvarsAPI(prim).GetPrimvar(pxr::TfToken(name));
            if (primvar && primvar.GetTypeName() == pxr::SdfValueTypeNames->TokenArray)
            {
                return setConstantPrimvar(prim, name, pxr::TfToken(value), pxr::UsdTimeCode(time));
            }
            return setConstantPrimvar(prim, name, value, pxr::UsdTimeCode(time));
        },
        arg("prim"),
        arg("name"),
        arg("value").noconvert(),
        arg("time") = pxr::UsdTimeCode::Default().GetValue(),
        doc
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

    bindCreateConstantPrimvarOverload(
        m,
        static_cast<pxr::UsdGeomPrimvar (*)(pxr::UsdPrim, const std::string&, float, const pxr::SdfValueTypeName&)>(&createConstantPrimvar),
        false
    );
    bindCreateConstantPrimvarOverload(
        m,
        static_cast<pxr::UsdGeomPrimvar (*)(pxr::UsdPrim, const std::string&, int, const pxr::SdfValueTypeName&)>(&createConstantPrimvar)
    );
    bindCreateConstantPrimvarOverload(
        m,
        static_cast<pxr::UsdGeomPrimvar (*)(pxr::UsdPrim, const std::string&, int64_t, const pxr::SdfValueTypeName&)>(&createConstantPrimvar)
    );
    bindCreateConstantStringPrimvar(m);
    bindCreateConstantPrimvarOverload(
        m,
        static_cast<pxr::UsdGeomPrimvar (*)(pxr::UsdPrim, const std::string&, const pxr::GfVec2f&, const pxr::SdfValueTypeName&)>(
            &createConstantPrimvar
        )
    );
    bindCreateConstantVec3fPrimvar(m);

    bindSetConstantPrimvarOverload(m, static_cast<bool (*)(pxr::UsdPrim, const std::string&, float, pxr::UsdTimeCode)>(&setConstantPrimvar), false);
    bindSetConstantPrimvarOverload(m, static_cast<bool (*)(pxr::UsdPrim, const std::string&, int, pxr::UsdTimeCode)>(&setConstantPrimvar));
    bindSetConstantPrimvarOverload(m, static_cast<bool (*)(pxr::UsdPrim, const std::string&, int64_t, pxr::UsdTimeCode)>(&setConstantPrimvar));
    bindSetConstantStringPrimvar(m);
    bindSetConstantPrimvarOverload(
        m,
        static_cast<bool (*)(pxr::UsdPrim, const std::string&, const pxr::GfVec2f&, pxr::UsdTimeCode)>(&setConstantPrimvar)
    );
    bindSetConstantPrimvarOverload(
        m,
        static_cast<bool (*)(pxr::UsdPrim, const std::string&, const pxr::GfVec3f&, pxr::UsdTimeCode)>(&setConstantPrimvar)
    );
}

} // namespace usdex::core::bindings
