# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""
`usdex.rtx <https://docs.omniverse.nvidia.com/usd/code-docs/usd-exchange-sdk/latest/docs/python-usdex-rtx.html>`_ provides utility functions for creating,
editing, and querying `UsdShade <https://openusd.org/release/api/usd_shade_page_front.html>`_ data models which represent
`MDL Materials and Shaders <https://www.nvidia.com/en-us/design-visualization/technologies/material-definition-language>`_ for use with the
RTX Renderer.
"""

__all__ = [
    # MDL shader utils
    "createMdlShader",
    "createMdlShaderInput",
    "computeEffectiveMdlSurfaceShader",
    # Need to be split up to handle UPS, Mtlx, Mdl
    "defineOmniPbrMaterial",
    "defineOmniGlassMaterial",
    "addDiffuseTextureToPbrMaterial",
    "addNormalTextureToPbrMaterial",
    "addOrmTextureToPbrMaterial",
    "addRoughnessTextureToPbrMaterial",
    "addMetallicTextureToPbrMaterial",
    "addOpacityTextureToPbrMaterial",
]

import os

if hasattr(os, "add_dll_directory"):
    __scriptdir = os.path.dirname(os.path.realpath(__file__))
    __dlldir = os.path.abspath(os.path.join(__scriptdir, "../../../lib"))
    __whl_libdir = os.path.abspath(os.path.join(__scriptdir, "../../usd_exchange.libs"))
    if os.path.exists(__dlldir):
        with os.add_dll_directory(__dlldir):
            from ._usdex_rtx import *  # noqa
    elif os.path.exists(__whl_libdir):
        with os.add_dll_directory(__whl_libdir):
            from ._usdex_rtx import *  # noqa
    else:
        # fallback to requiring the client to setup the dll directory
        from ._usdex_rtx import *  # noqa
else:
    from ._usdex_rtx import *  # noqa
