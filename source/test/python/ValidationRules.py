# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

__all__ = [
    "registerNativeValidators",
]

import usd_validation_nvidia

# Rule categories mapped to the native OpenUSD validators that `usd_validation_nvidia` does not currently expose.
# Every other native validator is deliberately absent, as `usd_validation_nvidia` implements an equivalent check
# already and adapting it would report the same issue twice.
_nativeValidators = {
    "Material": [
        "usdShadeValidators:EncapsulationMaterialValidator",
        "usdShadeValidators:MaterialBindingCollectionValidator",
        "usdShadeValidators:MaterialBindingRelationships",
        "usdShadeValidators:ShaderSdrCompliance",
    ],
    "Geometry": [
        "usdShadeValidators:SubsetsMaterialBindFamily",
    ],
    "AtomicAsset": [
        "usdUtilsValidators:FileExtensionValidator",
        "usdUtilsValidators:PackageEncapsulationValidator",
    ],
    "Basic": [
        "usdValidation:AttributeTypeMismatch",
    ],
}


def registerNativeValidators():
    """Register `usd_validation_nvidia` rules that adapt native OpenUSD validators

    ``usdex.test`` calls this on import, so every `usd_validation_nvidia.ValidationEngine` constructed with ``init_rules=True``
    runs these rules, including the engine used by `usdex.test.TestCase`.

    Returns:
        ``None``
    """
    registered = {
        rule.validator_name()
        for rule in usd_validation_nvidia.CategoryRuleRegistry().rules
        if issubclass(rule, usd_validation_nvidia.UsdValidatorAdapter)
    }
    for category, names in _nativeValidators.items():
        for name in names:
            rule = type(
                name.rpartition(":")[2],
                (usd_validation_nvidia.UsdValidatorAdapter,),
                {"validator_name": classmethod(lambda cls, name=name: name)},
            )
            # skip when the runtime does not provide the validator, and when `usd_validation_nvidia` already adapts it, so a release
            # that exposes its own adapters supersedes ours rather than reporting the same issue twice
            skip = name not in usd_validation_nvidia.UsdValidatorAdapter or name in registered
            usd_validation_nvidia.register_rule(category, skip=skip)(rule)
