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
    # core
    "version",
    "deprecated",
]

import os

if hasattr(os, "add_dll_directory"):
    __scriptdir = os.path.dirname(os.path.realpath(__file__))
    __dlldir = os.path.abspath(os.path.join(__scriptdir, "../../../../lib"))
    if os.path.exists(__dlldir):
        with os.add_dll_directory(__dlldir):
            from ._usdex_core import *  # noqa
    else:
        # fallback to requiring the client to setup the dll directory
        from ._usdex_core import *  # noqa
else:
    from ._usdex_core import *  # noqa


def deprecated(version: str, message: str):
    """
    Decorator used to deprecate public functions

    Example:

    .. code-block:: python

        @deprecated("0.5", "Use `baz` instead")
        def foo(bar: str) -> str:
            return baz(bar)

    Args:
        version: The major.minor version in which the function was first deprecated
        message: A user facing message about the deprecation, ideally with a suggested alternative function.
            Do not include the version in this message, it will be prefixed automatically.
    """

    def _wrap(func):
        warning = f"`{func.__name__}` was deprecated in v{version} and will be removed in the future. {message}"

        def wrapper(*args, **kwargs):
            from pxr import Tf

            Tf.warn(warning)
            return func(*args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = warning
        return wrapper

    return _wrap
