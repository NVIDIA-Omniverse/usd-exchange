# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomHook(BuildHookInterface):
    """Force a platform/abi-tagged wheel

    The package bundles precompiled python bindings (`pxr`, `usdex`) and shared libraries
    (`usd_exchange.libs`), so the wheel must be tagged for the building interpreter & platform
    (e.g. ``cp310-cp310-manylinux_2_35_x86_64``) rather than ``py3-none-any``.
    """

    def initialize(self, version, build_data):
        build_data["pure_python"] = False
        build_data["infer_tag"] = True
