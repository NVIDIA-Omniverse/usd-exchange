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

    # OpenUSD's public headers expose TBB symbols directly in some cases, so anything compiling against them needs TBB.
    # NVIDIA ships TBB as a separate package with no CMake config, so USDEX_TBB_ROOT points at it explicitly.
    # Otherwise fall back to a standard find_package(TBB). If neither is present the USD-header compile surfaces the
    # missing <tbb/...> itself.
    if(USDEX_TBB_ROOT)
        if(NOT EXISTS "${USDEX_TBB_ROOT}/include")
            message(FATAL_ERROR "USDEX_TBB_ROOT='${USDEX_TBB_ROOT}' has no include/ directory; ensure the dependency was fetched.")
        endif()
        target_include_directories(usdex_usd_headers SYSTEM INTERFACE "${USDEX_TBB_ROOT}/include")
        target_link_directories(usdex_usd_headers INTERFACE "${USDEX_TBB_ROOT}/lib")
        if(UNIX AND NOT APPLE)
            target_link_options(usdex_usd_headers INTERFACE "-Wl,-rpath-link,${USDEX_TBB_ROOT}/lib")
        endif()
    else()
        find_package(TBB QUIET)
        if(TARGET TBB::tbb)
            target_link_libraries(usdex_usd_headers INTERFACE TBB::tbb)
        endif()
    endif()

    # MaterialX is a sibling package too, but neither usdex nor OpenUSD's core headers #include it.
    # Only consumers that use the UsdMtlx schemas require it.
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
# builds ignore the names and link the single usd_ms. A Python-enabled installed package records its matching
# Python version. USDEX_PYTHON_ROOT lets consumers point the helper at that development runtime.
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

    # USD's public headers inline TBB, so executables must link it. Resolve release/debug separately and select via
    # optimized/debug so a combined external TBB dir links the config-correct one, not always release.
    if(USDEX_TBB_ROOT)
        if(WIN32)
            set(_usdex_tbb_release_names tbb12)
            set(_usdex_tbb_debug_names tbb12_debug)
        else()
            set(_usdex_tbb_release_names tbb)
            set(_usdex_tbb_debug_names tbb_debug)
        endif()
        find_library(USDEX_USDLIB_tbb_RELEASE NAMES ${_usdex_tbb_release_names} PATHS "${USDEX_TBB_ROOT}/lib" NO_DEFAULT_PATH)
        find_library(USDEX_USDLIB_tbb_DEBUG NAMES ${_usdex_tbb_debug_names} PATHS "${USDEX_TBB_ROOT}/lib" NO_DEFAULT_PATH)
        if(USDEX_USDLIB_tbb_RELEASE AND USDEX_USDLIB_tbb_DEBUG)
            target_link_libraries(${target} PRIVATE optimized "${USDEX_USDLIB_tbb_RELEASE}" debug "${USDEX_USDLIB_tbb_DEBUG}")
        elseif(USDEX_USDLIB_tbb_RELEASE)
            target_link_libraries(${target} PRIVATE "${USDEX_USDLIB_tbb_RELEASE}")
        elseif(USDEX_USDLIB_tbb_DEBUG)
            target_link_libraries(${target} PRIVATE "${USDEX_USDLIB_tbb_DEBUG}")
        else()
            message(FATAL_ERROR "oneTBB library not found in '${USDEX_TBB_ROOT}/lib'")
        endif()
    endif()

    # The top-level project sets USDEX_WITH_PYTHON and USDEX_PYTHON_VERSION for an SDK source build. An installed
    # package restores this information under package-specific names. This keeps the SDK ABI requirements unchanged.
    set(_usdex_with_python "${USDEX_WITH_PYTHON}")
    set(_usdex_python_version "${USDEX_PYTHON_VERSION}")
    if(DEFINED USDEX_PACKAGE_WITH_PYTHON)
        set(_usdex_with_python "${USDEX_PACKAGE_WITH_PYTHON}")
        set(_usdex_python_version "${USDEX_PACKAGE_PYTHON_VERSION}")
    endif()

    if(_usdex_with_python)
        if(NOT TARGET Python3::Python)
            if(USDEX_PYTHON_ROOT)
                set(Python3_ROOT_DIR "${USDEX_PYTHON_ROOT}")
            endif()
            find_package(Python3 ${_usdex_python_version} EXACT REQUIRED COMPONENTS Development)
        endif()

        find_library(USDEX_USDLIB_python NAMES "usd_python" PATHS "${USDEX_USD_LIB_DIR}" NO_DEFAULT_PATH)
        if(NOT USDEX_USDLIB_python)
            message(FATAL_ERROR "Python-enabled OpenUSD library 'usd_python' was not found in ${USDEX_USD_LIB_DIR}")
        endif()
        target_link_libraries(${target} PRIVATE "${USDEX_USDLIB_python}" Python3::Python)
    endif()
endfunction()
