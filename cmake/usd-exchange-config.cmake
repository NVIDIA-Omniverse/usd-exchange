# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Deprecated compatibility config for find_package(usd-exchange), the package name 3.0.0 shipped. The canonical
# name is `usdex`, matching the usdex:: namespace of the imported targets. This file only delegates, so both names
# provide the same targets, helper functions, and USDEX_PACKAGE_* variables.
#
# It will not be removed before the next major version. Unlike usdex-config.cmake, this file is installed verbatim:
# it substitutes nothing and never resolves a path against the install prefix, so it has no use for PACKAGE_INIT.

# A plain WARNING, not message(DEPRECATION): CMAKE_ERROR_DEPRECATED promotes DEPRECATION to an error, which would
# break the configure of a consumer that is doing nothing worse than using the older name.
message(WARNING
    "find_package(usd-exchange) is deprecated; use find_package(usdex) instead. The package name now matches the "
    "usdex:: target namespace, as CMake requires for a package to be describable in the Common Package "
    "Specification. No target, function, or variable names change, so this is a one-line edit."
)

# Deliberately an include() of the sibling directory rather than find_package(usdex): the path is exact and stays
# relocatable, and it leaves CMAKE_FIND_PACKAGE_NAME as `usd-exchange` so that requested components and the
# resulting <name>_FOUND remain attributed to the name the consumer asked for. It must also stay last, because the
# config returns early when OpenUSD is missing and that return unwinds only the included file.
include("${CMAKE_CURRENT_LIST_DIR}/../usdex/usdex-config.cmake")
