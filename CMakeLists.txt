# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# The single CMake project for the OpenUSD Exchange SDK. The same file is used by external customers
# (building the default flavor against their own USD via CMAKE_PREFIX_PATH/USDEX_USD_ROOT) and by the
# internal flavor-matrix driver (which only varies the inputs: USD prefix, Python version, ABI, output dirs).

cmake_minimum_required(VERSION 3.20)
project(usd-exchange CXX)

list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
# Match premake's strict `-std=c++17` (GCC defaults to gnu++17 with extensions on).
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build configuration" FORCE)
endif()

# A "flavor" with python_ver "0" is the usd-minimal build with no Python.
set(USDEX_PYTHON_VERSION "3.10" CACHE STRING "Python version for bindings; '0' disables Python")
if(USDEX_PYTHON_VERSION STREQUAL "0")
    set(USDEX_WITH_PYTHON OFF)
else()
    set(USDEX_WITH_PYTHON ON)
endif()

# Output layout. Defaults to a conventional build-dir layout for external consumers; the internal driver
# overrides these to the `_build/$platform/$config/{lib,bin,python}` tree that the downstream tools expect.
set(USDEX_LIB_OUTPUT_DIR "${CMAKE_BINARY_DIR}/lib" CACHE PATH "Shared library output directory")
set(USDEX_BIN_OUTPUT_DIR "${CMAKE_BINARY_DIR}/bin" CACHE PATH "Executable output directory")
set(USDEX_PYTHON_OUTPUT_DIR "${CMAKE_BINARY_DIR}/python" CACHE PATH "Python package output directory")
set(USDEX_INCLUDE_OUTPUT_DIR "${CMAKE_BINARY_DIR}/include" CACHE PATH "Public header staging directory")
set(USDEX_DEV_OUTPUT_DIR "${CMAKE_BINARY_DIR}/dev" CACHE PATH "dev/ tree staging directory (shipped in the package)")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${USDEX_LIB_OUTPUT_DIR}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${USDEX_BIN_OUTPUT_DIR}")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${USDEX_LIB_OUTPUT_DIR}")

include(GNUInstallDirs)  # early: CMAKE_INSTALL_LIBDIR feeds the rpaths + install rules below

# bake $ORIGIN-relative rpaths (not CMake's default absolute build rpath) so the package is relocatable; the
# default suits libs beside their USD siblings, per-target overrides below handle bin/ and the python/ bindings
set(CMAKE_BUILD_WITH_INSTALL_RPATH ON)
set(CMAKE_INSTALL_RPATH "$ORIGIN")

# building the SDK itself: opt into the warnings-as-errors / hardening / strip flags that consumers don't inherit
set(USDEX_BUILDING_SDK ON)
include(UsdexCompilerConfig)

if(USDEX_WITH_PYTHON)
    find_package(Python3 ${USDEX_PYTHON_VERSION} EXACT REQUIRED COMPONENTS Interpreter Development Development.Module)
    if(NOT USDEX_PYBIND11_INCLUDE_DIR)
        find_path(USDEX_PYBIND11_INCLUDE_DIR pybind11/pybind11.h)
    endif()
endif()

include(UsdexUSD)
include(UsdexPythonModule)

# ---------------------------------------------------------------------------- usdex_core
file(GLOB USDEX_CORE_SOURCES CONFIGURE_DEPENDS source/core/library/*.cpp)
add_library(usdex_core SHARED ${USDEX_CORE_SOURCES})
target_include_directories(usdex_core PUBLIC "$<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}/include>" "$<INSTALL_INTERFACE:include>")
target_link_libraries(usdex_core PRIVATE usdex_build_options usdex_usd_headers)
usdex_target_link_usd(usdex_core ar arch gf kind pcp plug sdf tf usd usdGeom usdLux usdPhysics usdShade usdUtils vt work)

# ---------------------------------------------------------------------------- usdex_rtx
file(GLOB USDEX_RTX_SOURCES CONFIGURE_DEPENDS source/rtx/library/*.cpp)
add_library(usdex_rtx SHARED ${USDEX_RTX_SOURCES})
target_include_directories(usdex_rtx PUBLIC "$<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}/include>" "$<INSTALL_INTERFACE:include>")
target_link_libraries(usdex_rtx PRIVATE usdex_build_options usdex_usd_headers usdex_core)
usdex_target_link_usd(usdex_rtx arch gf sdf tf usd usdGeom usdShade usdUtils vt)

# ---------------------------------------------------------------------------- python bindings
if(USDEX_WITH_PYTHON)
    file(GLOB USDEX_CORE_BINDINGS CONFIGURE_DEPENDS source/core/python/bindings/*.cpp)
    file(GLOB USDEX_CORE_PY CONFIGURE_DEPENDS source/core/python/*.py)
    usdex_add_python_module(usdex_core_python
        MODULE_NAME usdex_core SUBDIR core
        SOURCES ${USDEX_CORE_BINDINGS} PY_SOURCES ${USDEX_CORE_PY}
        LINK usdex_core
        USD_LIBS gf sdf tf usd usdGeom usdLux usdPhysics usdShade vt
    )

    file(GLOB USDEX_RTX_BINDINGS CONFIGURE_DEPENDS source/rtx/python/bindings/*.cpp)
    file(GLOB USDEX_RTX_PY CONFIGURE_DEPENDS source/rtx/python/*.py)
    usdex_add_python_module(usdex_rtx_python
        MODULE_NAME usdex_rtx SUBDIR rtx
        SOURCES ${USDEX_RTX_BINDINGS} PY_SOURCES ${USDEX_RTX_PY}
        LINK usdex_rtx usdex_core
        USD_LIBS gf sdf tf usd usdShade vt
    )

    # pure-python usdex.test module (no compiled component)
    file(GLOB USDEX_TEST_PY CONFIGURE_DEPENDS source/test/python/*.py)
    add_custom_target(usdex_test_py ALL COMMENT "Stage usdex.test python module")
    add_custom_command(TARGET usdex_test_py POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E make_directory "${USDEX_PYTHON_OUTPUT_DIR}/usdex/test" VERBATIM)
    foreach(_py ${USDEX_TEST_PY})
        add_custom_command(TARGET usdex_test_py POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_if_different "${_py}" "${USDEX_PYTHON_OUTPUT_DIR}/usdex/test/" VERBATIM)
    endforeach()
endif()

# ---------------------------------------------------------------------------- test_usdex_core (doctest)
# cxxopts/doctest are header-only third-party; discover on CMAKE_PREFIX_PATH unless explicitly provided.
find_path(USDEX_CXXOPTS_INCLUDE_DIR cxxopts.hpp)
find_path(USDEX_DOCTEST_INCLUDE_DIR doctest/doctest.h)

file(GLOB USDEX_CORE_TEST_SOURCES CONFIGURE_DEPENDS source/core/tests/doctest/*.cpp)
add_executable(test_usdex_core ${USDEX_CORE_TEST_SOURCES})
# bin/ -> sibling libs one dir up
set_target_properties(test_usdex_core PROPERTIES INSTALL_RPATH "$ORIGIN/../${CMAKE_INSTALL_LIBDIR}")
target_link_libraries(test_usdex_core PRIVATE usdex_build_options usdex_usd_headers usdex_core)
target_include_directories(test_usdex_core SYSTEM PRIVATE "${USDEX_CXXOPTS_INCLUDE_DIR}" "${USDEX_DOCTEST_INCLUDE_DIR}")
usdex_target_link_usd(test_usdex_core arch gf sdf tf usd usdGeom usdPhysics usdUtils vt)
# TBB (oneTBB at USD >= 25.08) is required directly because the tests use TfErrorMark
if(PXR_VERSION GREATER_EQUAL 2508)
    set(_tbb_names tbb12 tbb)
else()
    set(_tbb_names tbb)
endif()
find_library(USDEX_TBB NAMES ${_tbb_names} PATHS "${USDEX_USD_LIB_DIR}" NO_DEFAULT_PATH)
if(USDEX_TBB)
    target_link_libraries(test_usdex_core PRIVATE "${USDEX_TBB}")
endif()

# ---------------------------------------------------------------------------- header staging (build tree)
# downstream tools read <build>/include
add_custom_target(usdex_stage_headers ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory_if_different "${CMAKE_SOURCE_DIR}/include" "${USDEX_INCLUDE_OUTPUT_DIR}"
    COMMENT "Stage public headers to ${USDEX_INCLUDE_OUTPUT_DIR}"
    VERBATIM
)

# ---------------------------------------------------------------------------- dev/ staging (shipped in package)
# the repoman/vscode/packman tooling consumers use to run install_usdex (find_package config is staged to lib/cmake)
file(WRITE "${CMAKE_BINARY_DIR}/config.packman.xml" [==[<config remotes="cloudfront">
    <remote2 name="cloudfront">
        <transport actions="download" protocol="https" packageLocation="d4i3qtqj3r0z5.cloudfront.net/${name}@${version}" />
    </remote2>
</config>
]==])
add_custom_target(usdex_stage_dev ALL
    COMMAND ${CMAKE_COMMAND} -E copy_directory_if_different "${CMAKE_SOURCE_DIR}/tools/repoman" "${USDEX_DEV_OUTPUT_DIR}/tools/repoman"
    COMMAND ${CMAKE_COMMAND} -E copy_directory_if_different "${CMAKE_SOURCE_DIR}/tools/vscode" "${USDEX_DEV_OUTPUT_DIR}/tools/vscode"
    COMMAND ${CMAKE_COMMAND} -E copy_directory_if_different "${CMAKE_SOURCE_DIR}/tools/packman" "${USDEX_DEV_OUTPUT_DIR}/tools/packman"
    COMMAND ${CMAKE_COMMAND} -E copy_if_different "${CMAKE_BINARY_DIR}/config.packman.xml" "${USDEX_DEV_OUTPUT_DIR}/tools/packman/config.packman.xml"
    COMMENT "Stage dev/ tree to ${USDEX_DEV_OUTPUT_DIR}"
    VERBATIM
)

# ---------------------------------------------------------------------------- install rules (external find_package)
include(CMakePackageConfigHelpers)

install(TARGETS usdex_core usdex_rtx EXPORT usdex-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(DIRECTORY include/usdex DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
# component so the driver can install just the config (libs/headers are already in the build tree)
install(EXPORT usdex-targets NAMESPACE usdex:: FILE usd-exchange-targets.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange COMPONENT usdex_cmake_config)
configure_package_config_file(cmake/usd-exchange-config.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/usd-exchange-config.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/usd-exchange-config.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange COMPONENT usdex_cmake_config)
# shipped so consumers get usdex_target_link_usd() + usdex_usd_headers for their own OpenUSD usage
install(FILES cmake/UsdexUSD.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange COMPONENT usdex_cmake_config)
# shipped so consumers inherit the shared compile settings (usdex_build_options) rather than replicating them
install(FILES cmake/UsdexCompilerConfig.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange COMPONENT usdex_cmake_config)
if(USDEX_WITH_PYTHON)
    # the staged python tree (compiled modules + pure-python) is produced during the build
    install(DIRECTORY "${USDEX_PYTHON_OUTPUT_DIR}/usdex" DESTINATION python)
endif()
