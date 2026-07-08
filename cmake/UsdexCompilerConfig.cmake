# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Usage requirements for compiling against the OpenUSD Exchange SDK and OpenUSD, exposed as the INTERFACE target
# `usdex_build_options`. It ships with the package and find_package(usd-exchange) re-includes it, so downstream
# consumers inherit these settings; our own C++ targets link it PRIVATE too.
#
# Build hygiene that should not be imposed on consumers (strict warnings, hidden visibility, hardening, release
# stripping) is applied privately to our own targets via usdex_sdk_build_options in the top-level CMakeLists.txt.

include_guard(GLOBAL)

add_library(usdex_build_options INTERFACE)

# C++17, RTTI + exceptions are required by OpenUSD. CMake enables RTTI/exceptions by default on GCC/Clang;
# the MSVC equivalents (/GR /EHsc) are forced below.
target_compile_features(usdex_build_options INTERFACE cxx_std_17)

set(_gnu "$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>,$<CXX_COMPILER_ID:AppleClang>>")
set(_msvc "$<CXX_COMPILER_ID:MSVC>")
set(_debug "$<CONFIG:Debug>")

# Preprocessor defines (parity with premake): NDEBUG/DEBUG, TBB, file offsets, libstdc++ ABI, NOMINMAX.
target_compile_definitions(usdex_build_options INTERFACE
    TBB_SUPPRESS_DEPRECATED_MESSAGES
    "$<${_debug}:DEBUG>"
    "$<${_debug}:TBB_USE_DEBUG=1>"
    "$<$<NOT:${_debug}>:NDEBUG>"
)
if(UNIX AND NOT APPLE)
    # Always the modern libstdc++ ABI; old-ABI (_GLIBCXX_USE_CXX11_ABI=0) flavors are no longer supported.
    target_compile_definitions(usdex_build_options INTERFACE
        _FILE_OFFSET_BITS=64
        _GLIBCXX_USE_CXX11_ABI=1
    )
endif()
if(WIN32)
    target_compile_definitions(usdex_build_options INTERFACE NOMINMAX)
endif()

# GCC/Clang usage requirements consumers need to compile against usdex + OpenUSD: -pthread (OpenUSD's headers are
# threaded) and -Wno-deprecated (OpenUSD pulls in a deprecated libstdc++ backward header whose #warning fires even
# through SYSTEM includes, breaking consumers that build with -Werror).
target_compile_options(usdex_build_options INTERFACE
    "$<${_gnu}:-pthread;-Wno-deprecated>"
)
# MSVC usage requirements: exceptions/RTTI + conformance + large-object support needed to compile OpenUSD headers.
target_compile_options(usdex_build_options INTERFACE
    "$<${_msvc}:/utf-8;/bigobj;/permissive-;/Zc:__cplusplus;/EHsc;/GR>"
)
