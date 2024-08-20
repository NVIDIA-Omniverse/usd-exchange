# SPDX-FileCopyrightText: Copyright (c) 2022-2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

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
    if os.path.exists(__dlldir):
        with os.add_dll_directory(__dlldir):
            from ._usdex_rtx import *  # noqa
    else:
        # fallback to requiring the client to setup the dll directory
        from ._usdex_rtx import *  # noqa
else:
    from ._usdex_rtx import *  # noqa