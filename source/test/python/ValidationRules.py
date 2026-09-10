# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

__all__ = [
    "registerNativeValidators",
]

import usd_validation_nvidia

_atomicAssetValidators = (
    usd_validation_nvidia.UsdUtilsFileExtensionValidator,
    usd_validation_nvidia.UsdUtilsPackageEncapsulationValidator,
)


def registerNativeValidators():
    """Register the opt-in `usd_validation_nvidia` AtomicAsset validators.

    ``usdex.test`` calls this on import, so every `usd_validation_nvidia.ValidationEngine` constructed with ``init_rules=True``
    runs these rules, including the engine used by `usdex.test.TestCase`.

    Returns:
        ``None``
    """
    for rule in _atomicAssetValidators:
        usd_validation_nvidia.register_rule("AtomicAsset", skip=not rule.is_implemented())(rule)
