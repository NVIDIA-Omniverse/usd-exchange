// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

#include "usdex/core/AttributeAlgo.h"

#include "usdex/pybind/UsdBindings.h"

#include <pxr/base/vt/array.h>
#include <pxr/usd/usd/attribute.h>

#include <pybind11/pybind11.h>

using namespace usdex::core;
using namespace pybind11;
using namespace pxr;

#define USDEX_TRY_EXTRACT_ARRAY(arrayType)                                                                                                           \
    if (tryExtractAs<arrayType>(pyValue, expectedType, outValue))                                                                                    \
    {                                                                                                                                                \
        return true;                                                                                                                                 \
    }

namespace
{

template <typename T>
bool tryExtractAs(const object& pyValue, const TfType& expectedType, VtValue* outValue)
{
    if (expectedType != TfType::Find<T>())
    {
        return false;
    }

    pyboost11::caster<T> caster(pyValue);
    if (!caster.check())
    {
        return false;
    }

    *outValue = VtValue(caster());
    return true;
}

bool tryConvertPySequenceToVtValue(const object& pyValue, const TfType& expectedType, VtValue* outValue)
{
    USDEX_TRY_EXTRACT_ARRAY(VtFloatArray);
    USDEX_TRY_EXTRACT_ARRAY(VtIntArray);
    USDEX_TRY_EXTRACT_ARRAY(VtInt64Array);
    USDEX_TRY_EXTRACT_ARRAY(VtDoubleArray);
    USDEX_TRY_EXTRACT_ARRAY(VtStringArray);
    USDEX_TRY_EXTRACT_ARRAY(VtTokenArray);
    USDEX_TRY_EXTRACT_ARRAY(VtVec2fArray);
    USDEX_TRY_EXTRACT_ARRAY(VtVec3fArray);
    USDEX_TRY_EXTRACT_ARRAY(VtVec4fArray);
    USDEX_TRY_EXTRACT_ARRAY(VtVec2dArray);
    USDEX_TRY_EXTRACT_ARRAY(VtVec3dArray);
    USDEX_TRY_EXTRACT_ARRAY(VtVec4dArray);

    return false;
}

VtValue pyObjectToVtValue(const UsdPrim& prim, const TfToken& name, const object& pyValue)
{
    if (pyValue.is_none())
    {
        return VtValue();
    }

    if (isinstance<list>(pyValue))
    {
        const UsdAttribute attr = prim.GetAttribute(name);
        if (attr)
        {
            VtValue converted;
            if (tryConvertPySequenceToVtValue(pyValue, attr.GetTypeName().GetType(), &converted))
            {
                return converted;
            }
        }
    }

    pyboost11::caster<VtValue> vtCaster(pyValue);
    if (vtCaster.check())
    {
        return vtCaster();
    }

    return VtValue();
}

} // namespace

namespace usdex::core::bindings
{

void bindAttributeAlgo(module& m)
{
    m.def(
        "setEffectiveAttributeValue",
        [](const UsdPrim& prim, const TfToken& name, const object& pyValue)
        {
            const VtValue value = pyObjectToVtValue(prim, name, pyValue);
            gil_scoped_release release;
            return setEffectiveAttributeValue(prim, name, value);
        },
        arg("prim"),
        arg("name"),
        arg("value"),
        R"(
            Author a value on a defined attribute only if the value differs from the attribute's fallback (default) value.

            This enables sparse authoring of layers that only contain opinions differing from schema defaults.

            The attribute must already be declared on the prim's composed prim definition (for example after
            applying the relevant API schema). If the attribute is not defined, a coding error is emitted and
            no value is authored.

            When the supplied value is equal to the schema fallback (default) value:
            - If the attribute does not have an existing authored opinion, no new opinion will be authored, enabling the current edit target to remain a sparse layer.
            - If the attribute has an authored opinion in a weaker layer, it will be explicitly blocked via ``Usd.Attribute.Block()``, enabling the fallback to become the strongest opinion.
            - If the attribute has an authored opinion only in the current edit target, it will be cleared via ``Usd.Attribute.Clear()``.

            If the supplied value is an empty/invalid sentinel value (for example ``None``), the attribute is also
            blocked via ``Usd.Attribute.Block()``. This prevents opinions on weaker sublayers from contributing to the
            composed value. To remove an opinion from the current edit target without blocking weaker
            layers, call ``Usd.Attribute.Clear()`` directly instead.

            The value must match the attribute's ``SdfValueTypeName``, or be trivially convertible (for example
            ``double`` to ``float``, or a Python ``list`` to a compatible ``Vt.*Array`` type).
            Otherwise a coding error is emitted and no value is authored.

            Args:
                prim: The prim on which to author the attribute
                name: The name of the defined attribute
                value: The value to author when it differs from the schema fallback

            Returns:
                True on success, otherwise False.
        )"
    );
}

} // namespace usdex::core::bindings
