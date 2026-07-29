# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# OpenUSD discovery. We do NOT rely on the package's pxrConfig.cmake (it is not self-contained: its find_dependency(TBB/OpenSubdiv/Imath)
# calls require configs the package does not bundle and Imath has no skip toggle).
# Instead we add `<usd_root>/include` as a SYSTEM include and link the individual USD libraries by full path out of `<usd_root>/lib`.
#
# Reusable by external consumers via find_package(usd-exchange). Inputs: USDEX_USD_ROOT or a CMAKE_PREFIX_PATH
# entry with include/pxr/pxr.h. When USD is located it provides the `usdex_usd_headers` target, PXR_VERSION, and
# `usdex_target_link_usd()`; absent USD is not an error (usdex links USD privately) until that function is called.

include_guard(GLOBAL)

if(NOT USDEX_USD_ROOT)
    foreach(_prefix IN LISTS CMAKE_PREFIX_PATH)
        if(EXISTS "${_prefix}/include/pxr/pxr.h")
            set(USDEX_USD_ROOT "${_prefix}")
            break()
        endif()
    endforeach()
endif()
# set up USD only when located; absent USD is not an error (see header)
if(USDEX_USD_ROOT AND EXISTS "${USDEX_USD_ROOT}/include/pxr/pxr.h")
    set(USDEX_USD_ROOT "${USDEX_USD_ROOT}" CACHE PATH "OpenUSD install root")
    set(USDEX_USD_INCLUDE_DIR "${USDEX_USD_ROOT}/include")
    set(USDEX_USD_LIB_DIR "${USDEX_USD_ROOT}/lib")

    # usd-minimal is monolithic: one usd_ms lib instead of per-module usd_<name>. Detect via absence of usdGeom.
    file(GLOB _usd_modular_probe "${USDEX_USD_LIB_DIR}/*usdGeom*")
    if(_usd_modular_probe)
        set(USDEX_USD_MONOLITHIC OFF)
    else()
        set(USDEX_USD_MONOLITHIC ON)
    endif()

    file(STRINGS "${USDEX_USD_INCLUDE_DIR}/pxr/pxr.h" _pxr_ver_line REGEX "#define[ \t]+PXR_VERSION[ \t]+[0-9]+")
    string(REGEX MATCH "[0-9]+" PXR_VERSION "${_pxr_ver_line}")
    message(STATUS "usdex: OpenUSD at ${USDEX_USD_ROOT} (PXR_VERSION=${PXR_VERSION})")

    # SYSTEM include + link search dir; rpath-link resolves USD's inter-library deps at link time
    add_library(usdex_usd_headers INTERFACE)
    target_include_directories(usdex_usd_headers SYSTEM INTERFACE "${USDEX_USD_INCLUDE_DIR}")
    target_link_directories(usdex_usd_headers INTERFACE "${USDEX_USD_LIB_DIR}")
    if(UNIX AND NOT APPLE)
        target_link_options(usdex_usd_headers INTERFACE "-Wl,-rpath-link,${USDEX_USD_LIB_DIR}")
    endif()

    # TBB/MaterialX are sibling packages in USD 26+ (the pxr headers still #include <tbb/...>); older distros bundle them
    # under USDEX_USD_ROOT. A provided root must be valid: set-but-missing means the dependency was never fetched.
    if(USDEX_TBB_ROOT)
        if(NOT EXISTS "${USDEX_TBB_ROOT}/include")
            message(FATAL_ERROR "USDEX_TBB_ROOT='${USDEX_TBB_ROOT}' has no include/ directory; ensure the dependency was fetched.")
        endif()
        target_include_directories(usdex_usd_headers SYSTEM INTERFACE "${USDEX_TBB_ROOT}/include")
        target_link_directories(usdex_usd_headers INTERFACE "${USDEX_TBB_ROOT}/lib")
        if(UNIX AND NOT APPLE)
            target_link_options(usdex_usd_headers INTERFACE "-Wl,-rpath-link,${USDEX_TBB_ROOT}/lib")
        endif()
    endif()
    if(USDEX_MATERIALX_ROOT)
        if(NOT EXISTS "${USDEX_MATERIALX_ROOT}/include")
            message(FATAL_ERROR "USDEX_MATERIALX_ROOT='${USDEX_MATERIALX_ROOT}' has no include/ directory; ensure the dependency was fetched.")
        endif()
        target_include_directories(usdex_usd_headers SYSTEM INTERFACE "${USDEX_MATERIALX_ROOT}/include")
        target_link_directories(usdex_usd_headers INTERFACE "${USDEX_MATERIALX_ROOT}/lib")
        if(UNIX AND NOT APPLE)
            target_link_options(usdex_usd_headers INTERFACE "-Wl,-rpath-link,${USDEX_MATERIALX_ROOT}/lib")
        endif()
    endif()
endif()

# Link the named OpenUSD libraries into `target` (handles `usd_`-prefixed and unprefixed names). Monolithic
# builds ignore the names and link the single usd_ms. With Python, also link the USD python bindings + runtime.
function(usdex_target_link_usd target)
    if(NOT TARGET usdex_usd_headers)
        message(FATAL_ERROR "usdex_target_link_usd(${target}) needs OpenUSD: set -DUSDEX_USD_ROOT=<usd-install> or add it to CMAKE_PREFIX_PATH.")
    endif()
    if(USDEX_USD_MONOLITHIC)
        # libusd_usd_ms.so (prefixed) or stock libusd_ms.so
        find_library(USDEX_USDLIB_ms NAMES "usd_usd_ms" "usd_ms" PATHS "${USDEX_USD_LIB_DIR}" NO_DEFAULT_PATH)
        if(NOT USDEX_USDLIB_ms)
            message(FATAL_ERROR "monolithic OpenUSD library (usd_usd_ms/usd_ms) not found in ${USDEX_USD_LIB_DIR}")
        endif()
        target_link_libraries(${target} PRIVATE "${USDEX_USDLIB_ms}")
    else()
        foreach(_name ${ARGN})
            set(_var "USDEX_USDLIB_${_name}")
            find_library(${_var} NAMES "usd_${_name}" "${_name}" PATHS "${USDEX_USD_LIB_DIR}" NO_DEFAULT_PATH)
            if(NOT ${_var})
                message(FATAL_ERROR "OpenUSD library '${_name}' (usd_${_name}/${_name}) not found in ${USDEX_USD_LIB_DIR}")
            endif()
            target_link_libraries(${target} PRIVATE "${${_var}}")
        endforeach()
    endif()
    if(USDEX_WITH_PYTHON)
        find_library(USDEX_USDLIB_python NAMES "usd_python" PATHS "${USDEX_USD_LIB_DIR}" NO_DEFAULT_PATH)
        if(USDEX_USDLIB_python)
            target_link_libraries(${target} PRIVATE "${USDEX_USDLIB_python}")
        endif()
        target_link_libraries(${target} PRIVATE Python3::Python)
    endif()
endfunction()
