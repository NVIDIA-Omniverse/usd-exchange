# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Assemble the third-party license notices that ship with our binaries.

The notices are listed here rather than crawled out of the packages we consume, because the packages vendor notices for
their own dependencies & build tools, none of which we redistribute. This list is the counterpart to docs/licenses.md,
which documents the same set per module, so the two are maintained together.
"""

import glob
import os
import shutil

import omni.repo.man

# the notice we ship -> where we copy it from
_NOTICES = {
    "materialx-LICENSE.txt": "$root/_build/target-deps/materialx/${config}/PACKAGE-LICENSES/materialx-LICENSE",
    "onetbb-LICENSE.txt": "$root/_build/target-deps/tbb/${config}/PACKAGE-LICENSES/onetbb-LICENSE.txt",
    "openusd-LICENSE.txt": "$root/_build/target-deps/usd/${config}/PACKAGE-LICENSES/openusd-LICENSE.txt",
    "pybind11-LICENSE.txt": "$root/_build/target-deps/pybind11/PACKAGE-LICENSES/pybind11-LICENSE.txt",
    "pybind11-stubgen-LICENSE.txt": "$root/tools/internal-licenses/pybind11-stubgen-LICENSE.txt",
    "pyboost11-LICENSE.txt": "$root/tools/internal-licenses/pyboost11-LICENSE.txt",
    "usd-exchange-LICENSE.md": "$root/LICENSE.md",
}

PACKAGE_NOTICES = tuple(_NOTICES)
# the wheels carry the runtime only, while our vendored copy of pybind11-stubgen ships in the package's dev/ tree
WHEEL_NOTICES = tuple(name for name in _NOTICES if name != "pybind11-stubgen-LICENSE.txt")


def gather(output_dir: str, config: str, notices=PACKAGE_NOTICES):
    """Copy each notice into `output_dir`, raising if any of them cannot be found."""
    os.makedirs(output_dir, exist_ok=True)
    for name in notices:
        pattern = omni.repo.man.resolve_tokens(_NOTICES[name], extra_tokens={"config": config})
        matches = glob.glob(pattern)
        if not matches:
            raise omni.repo.man.ExpectedError(f"Unable to find license file for pattern: {pattern}")
        shutil.copyfile(matches[0], f"{output_dir}/{name}")
