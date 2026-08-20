# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# The single CMake project for the OpenUSD Exchange SDK. The same file is used by external customers
# (building the default flavor against their own USD via CMAKE_PREFIX_PATH/USDEX_USD_ROOT) and by the
# internal flavor-matrix driver (which only varies the inputs: USD prefix, Python version, ABI).
# Both assemble the runtime tree with `cmake --install --prefix <dir>`.

cmake_minimum_required(VERSION 3.20)
project(usd-exchange CXX)

list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build configuration" FORCE)
endif()

# must precede USDEX_WITH_PYTHON_INT below, which reads USDEX_USD_WITH_PYTHON
include(UsdexUSD)

# Whether OpenUSD itself has Python is the separate USDEX_USD_WITH_PYTHON: a Python-enabled OpenUSD still
# requires the Python development files here even with the bindings off.
option(USDEX_BUILD_PYTHON_BINDINGS "Build the OpenUSD Exchange SDK Python bindings" ON)
# Pins the ABI for the bindings. With the bindings off the version is unconstrained, because only the
# OpenUSD distribution knows which Python it was built against.
set(USDEX_PYTHON_VERSION "3.12" CACHE STRING "Python version for the bindings")
# Relative to the install prefix, or absolute. Left empty here & defaulted to the interpreter's site-packages
# once one is found, so that installing into a prefix makes the modules importable from it.
set(USDEX_INSTALL_PYTHONDIR "" CACHE STRING "Install location for the usdex Python modules")

# OFF by default so a build doesn't require the test-only cxxopts + doctest headers.
option(USDEX_BUILD_TESTS "Build the OpenUSD Exchange SDK C++ tests (requires cxxopts + doctest)" OFF)

# ---------------------------------------------------------------------------- generated headers (Version.h / Feature.h / version.rc)
# These are #included by the C++ sources (and the Windows VERSIONINFO resource). It is recommended to provide an
# exact -DUSDEX_VERSION_STRING / -DUSDEX_BUILD_STRING (with build number + git sha) for local builds; If none is provided, it will be
# derived from the top CHANGELOG.md heading.
# the cache entries are declared before the fallbacks fill them, because setting an existing cache variable
# drops the normal variable of the same name, which would discard whatever the fallback had just derived
set(USDEX_VERSION_STRING "" CACHE STRING "OpenUSD Exchange SDK version string (e.g. 3.0.0-dev)")
set(USDEX_BUILD_STRING "" CACHE STRING "OpenUSD Exchange SDK unique build string")
set(USDEX_COMPANY_NAME "" CACHE STRING "Company name embedded in the Windows VERSIONINFO resource")
if(NOT USDEX_VERSION_STRING)
    file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/CHANGELOG.md" _usdex_changelog_head LIMIT_COUNT 1)
    string(REGEX REPLACE "^#[ \t]*" "" _usdex_changelog_version "${_usdex_changelog_head}")
    set(USDEX_VERSION_STRING "${_usdex_changelog_version}" CACHE STRING "" FORCE)
endif()
if(NOT USDEX_BUILD_STRING)
    set(USDEX_BUILD_STRING "${USDEX_VERSION_STRING}" CACHE STRING "" FORCE)
endif()
string(REGEX MATCH "^([0-9]+)\\.([0-9]+)\\.([0-9]+)" _usdex_version_match "${USDEX_VERSION_STRING}")
if(NOT _usdex_version_match)
    # otherwise this surfaces much later, as a Windows resource compiler error about the generated version.rc
    message(FATAL_ERROR "USDEX_VERSION_STRING '${USDEX_VERSION_STRING}' must begin with <major>.<minor>.<patch>")
endif()
set(USDEX_VERSION_MAJOR "${CMAKE_MATCH_1}")
set(USDEX_VERSION_MINOR "${CMAKE_MATCH_2}")
set(USDEX_VERSION_PATCH "${CMAKE_MATCH_3}")
# withPython() reports the runtime libpython requirement, which comes from OpenUSD, not from the bindings
if(USDEX_USD_WITH_PYTHON)
    set(USDEX_WITH_PYTHON_INT 1)
else()
    set(USDEX_WITH_PYTHON_INT 0)
endif()
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/cmake/Version.h.in" "${CMAKE_CURRENT_SOURCE_DIR}/include/usdex/core/Version.h" @ONLY)
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/cmake/Feature.h.in" "${CMAKE_CURRENT_SOURCE_DIR}/include/usdex/core/Feature.h" @ONLY)
if(WIN32)
    # generate + compile the VERSIONINFO resource so the DLLs carry file/product version, company, and copyright
    enable_language(RC)
    configure_file("${CMAKE_CURRENT_SOURCE_DIR}/cmake/version.rc.in" "${CMAKE_CURRENT_SOURCE_DIR}/version.rc" @ONLY)
endif()

include(GNUInstallDirs)  # early: CMAKE_INSTALL_LIBDIR/BINDIR feed the rpaths + install rules below

# bake $ORIGIN-relative rpaths (not CMake's default absolute build rpath) so the package is relocatable; the
# default suits libs beside their USD siblings, per-target overrides below handle bin/ and the python/ bindings
set(CMAKE_BUILD_WITH_INSTALL_RPATH ON)
set(CMAKE_INSTALL_RPATH "$ORIGIN")

include(UsdexCompilerConfig)

# Compile/link hygiene, applied PRIVATELY to our own targets and never shipped to consumers: strict warnings, hidden visibility, debug symbols
# (GCC/Clang: Debug only; MSVC: separate PDB and parallel compilation), warnings-as-errors, security hardening
# (stack protection + RELRO/BIND_NOW + CFG), release size/section GC, and release symbol stripping. The usage requirements
# consumers inherit are in usdex_build_options.
add_library(usdex_sdk_build_options INTERFACE)
set(_gnu "$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>,$<CXX_COMPILER_ID:AppleClang>>")
set(_msvc "$<CXX_COMPILER_ID:MSVC>")
set(_release "$<CONFIG:Release>")
set(_debug "$<CONFIG:Debug>")
set(_x86_64 "$<STREQUAL:${CMAKE_SYSTEM_PROCESSOR},x86_64>")
target_compile_options(usdex_sdk_build_options INTERFACE
    "$<${_gnu}:-fdiagnostics-color;-fvisibility=hidden;-Wall;-Wextra;-Wvla;-Wshadow;-Wundef;-Wconversion;-Werror;-fstack-protector-strong>"
    "$<$<AND:${_gnu},${_debug}>:-g>"
    "$<$<AND:${_gnu},${_x86_64}>:-fstack-clash-protection>"
    "$<${_msvc}:/W4;/Zi;/WX;/MP;/guard:cf>"
)
target_link_options(usdex_sdk_build_options INTERFACE
    "$<${_gnu}:-Wl,-z,relro;-Wl,-z,now>"
    "$<$<AND:${_gnu},${_release}>:-Wl,-O1;-Wl,--gc-sections;-Wl,-s>"
    "$<${_msvc}:/guard:cf>"
)

if(USDEX_BUILD_PYTHON_BINDINGS)
    usdex_find_python(${USDEX_PYTHON_VERSION} Interpreter)
    if(NOT USDEX_PYBIND11_INCLUDE_DIR)
        find_path(USDEX_PYBIND11_INCLUDE_DIR pybind11/pybind11.h)
    endif()
    if(NOT USDEX_PYBIND11_INCLUDE_DIR)
        message(FATAL_ERROR "pybind11 headers not found. Set -DUSDEX_PYBIND11_INCLUDE_DIR=<dir> or add pybind11 to CMAKE_PREFIX_PATH (or configure without Python bindings via -DUSDEX_BUILD_PYTHON_BINDINGS=OFF).")
    endif()
    if(NOT USDEX_INSTALL_PYTHONDIR)
        # site-packages as the interpreter lays it out, but under our own prefix rather than the interpreter's
        if(WIN32)
            set(_usdex_pythondir "Lib/site-packages")
        else()
            set(_usdex_pythondir "lib/python${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}/site-packages")
        endif()
        set(USDEX_INSTALL_PYTHONDIR "${_usdex_pythondir}" CACHE STRING "" FORCE)
    endif()
elseif(USDEX_USD_WITH_PYTHON)
    # found here rather than on demand in usdex_target_link_usd() so the version lands in this scope for the package config
    usdex_find_python("")
endif()

include(UsdexPythonModule)

# ---------------------------------------------------------------------------- usdex_core
file(GLOB USDEX_CORE_SOURCES CONFIGURE_DEPENDS source/core/library/*.cpp)
add_library(usdex_core SHARED ${USDEX_CORE_SOURCES})
target_include_directories(usdex_core PUBLIC "$<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}/include>" "$<INSTALL_INTERFACE:include>")
target_link_libraries(usdex_core PRIVATE usdex_build_options usdex_sdk_build_options usdex_usd_headers)
usdex_target_link_usd(usdex_core ar arch gf kind pcp plug sdf tf usd usdGeom usdLux usdMtlx usdPhysics usdShade usdUI usdUtils vt work)

# ---------------------------------------------------------------------------- usdex_rtx
file(GLOB USDEX_RTX_SOURCES CONFIGURE_DEPENDS source/rtx/library/*.cpp)
add_library(usdex_rtx SHARED ${USDEX_RTX_SOURCES})
target_include_directories(usdex_rtx PUBLIC "$<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}/include>" "$<INSTALL_INTERFACE:include>")
target_link_libraries(usdex_rtx PRIVATE usdex_build_options usdex_sdk_build_options usdex_usd_headers usdex_core)
usdex_target_link_usd(usdex_rtx arch gf sdf tf usd usdGeom usdShade usdUtils vt)

# embed the Windows VERSIONINFO resource (generated above) into both DLLs
if(WIN32)
    target_sources(usdex_core PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/version.rc")
    target_sources(usdex_rtx PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/version.rc")
endif()

# ---------------------------------------------------------------------------- python bindings
if(USDEX_BUILD_PYTHON_BINDINGS)
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
    install(FILES ${USDEX_TEST_PY} DESTINATION ${USDEX_INSTALL_PYTHONDIR}/usdex/test)
endif()

# ---------------------------------------------------------------------------- test_usdex_core (doctest)
if(USDEX_BUILD_TESTS)
    # cxxopts/doctest are header-only third-party; discover on CMAKE_PREFIX_PATH unless explicitly provided.
    find_path(USDEX_CXXOPTS_INCLUDE_DIR cxxopts.hpp)
    find_path(USDEX_DOCTEST_INCLUDE_DIR doctest/doctest.h)

    file(GLOB USDEX_CORE_TEST_SOURCES CONFIGURE_DEPENDS source/core/tests/doctest/*.cpp)
    add_executable(test_usdex_core ${USDEX_CORE_TEST_SOURCES})
    # bin/ -> sibling libs one dir up
    set_target_properties(test_usdex_core PROPERTIES INSTALL_RPATH "$ORIGIN/../${CMAKE_INSTALL_LIBDIR}")
    target_link_libraries(test_usdex_core PRIVATE usdex_build_options usdex_sdk_build_options usdex_usd_headers usdex_core)
    target_include_directories(test_usdex_core SYSTEM PRIVATE "${USDEX_CXXOPTS_INCLUDE_DIR}" "${USDEX_DOCTEST_INCLUDE_DIR}")
    usdex_target_link_usd(test_usdex_core arch gf sdf tf usd usdGeom usdPhysics usdUtils vt)
endif()

# the packman config shipped in dev/ so consumers can fetch the runtime deps install_usdex needs
file(WRITE "${CMAKE_BINARY_DIR}/config.packman.xml" [==[<config remotes="cloudfront">
    <remote2 name="cloudfront">
        <transport actions="download" protocol="https" packageLocation="d4i3qtqj3r0z5.cloudfront.net/${name}@${version}" />
    </remote2>
</config>
]==])

# ---------------------------------------------------------------------------- install rules (assemble the runtime tree)
# `cmake --install --prefix <dir>` produces the relocatable tree (libs, headers, python, dev/, find_package config).
# The internal driver installs into `_build/$platform/$config`; external consumers pick their own prefix.
include(CMakePackageConfigHelpers)

# build target names keep the usdex_ prefix so artifact filenames are unchanged
set_target_properties(usdex_core PROPERTIES EXPORT_NAME core)
set_target_properties(usdex_rtx PROPERTIES EXPORT_NAME rtx)
install(TARGETS usdex_core usdex_rtx EXPORT usdex-targets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)
install(DIRECTORY include/usdex DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT usdex-targets NAMESPACE usdex:: FILE usd-exchange-targets.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange)
# the ABI consumers must match is the Python that was linked, not the one the bindings asked for
set(USDEX_PACKAGE_PYTHON_VERSION "")
if(USDEX_USD_WITH_PYTHON)
    set(USDEX_PACKAGE_PYTHON_VERSION "${Python3_VERSION_MAJOR}.${Python3_VERSION_MINOR}")
endif()
configure_package_config_file(cmake/usd-exchange-config.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/usd-exchange-config.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/usd-exchange-config.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange)
# shipped so consumers get usdex_target_link_usd() + usdex_usd_headers for their own OpenUSD usage
install(FILES cmake/UsdexUSD.cmake DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange)
# shipped so consumers inherit the shared compile settings (usdex_build_options) rather than replicating them
install(FILES cmake/UsdexCompilerConfig.cmake DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/usd-exchange)
# dev/ tooling consumers use to run install_usdex (not part of the find_package contract)
install(DIRECTORY tools/repoman tools/vscode tools/packman DESTINATION dev/tools)
install(FILES "${CMAKE_BINARY_DIR}/config.packman.xml" DESTINATION dev/tools/packman)
if(TARGET test_usdex_core)
    install(TARGETS test_usdex_core RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
