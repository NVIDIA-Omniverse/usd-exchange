# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Central compiler/linker configuration for the OpenUSD Exchange SDK, exposed as the INTERFACE target
# `usdex_build_options`. It ships with the package and find_package(usd-exchange) re-includes it, so downstream
# consumers inherit the same settings needed to compile against OpenUSD + usdex. usdex C++ targets link it PRIVATE.
#
# Build-hygiene settings that should not be imposed on consumers (warnings-as-errors, security hardening, release
# symbol stripping) are applied only while building the SDK itself, gated behind USDEX_BUILDING_SDK.

include_guard(GLOBAL)

add_library(usdex_build_options INTERFACE)

# C++17, RTTI + exceptions are required by OpenUSD. CMake enables RTTI/exceptions by default on GCC/Clang;
# the MSVC equivalents (/GR /EHsc) are forced below.
target_compile_features(usdex_build_options INTERFACE cxx_std_17)

set(_gnu "$<OR:$<CXX_COMPILER_ID:GNU>,$<CXX_COMPILER_ID:Clang>,$<CXX_COMPILER_ID:AppleClang>>")
set(_msvc "$<CXX_COMPILER_ID:MSVC>")
set(_release "$<CONFIG:Release>")
set(_debug "$<CONFIG:Debug>")
set(_x86_64 "$<STREQUAL:${CMAKE_SYSTEM_PROCESSOR},x86_64>")

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

# GCC/Clang compile flags. -Wno-deprecated must follow -Wall/-Wextra to take effect; it silences the deprecated
# <ext/hash_set> #warning that OpenUSD's headers trigger even from SYSTEM includes.
target_compile_options(usdex_build_options INTERFACE
    "$<${_gnu}:-fvisibility=hidden;-fdiagnostics-color;-pthread>"
    "$<${_gnu}:-Wall;-Wextra;-Wvla;-Wshadow;-Wundef;-Wconversion;-Wno-deprecated>"
    "$<${_gnu}:-g>" # compiled with symbols On in all configs; release shared libs are stripped at link
)
# MSVC compile flags (parity with repo_build's add_windows_support).
target_compile_options(usdex_build_options INTERFACE
    "$<${_msvc}:/utf-8;/bigobj;/permissive-;/Zc:__cplusplus;/W4;/EHsc;/GR;/Zi>"
)
# GCC/Clang link flags: release size/section GC (safe + beneficial for consumers as well).
target_link_options(usdex_build_options INTERFACE
    "$<$<AND:${_gnu},${_release}>:-Wl,-O1;-Wl,--gc-sections>"
)

# SDK-build-only hygiene applied to our own compilation but NOT inherited by downstream consumers (gated behind
# USDEX_BUILDING_SDK): warnings-as-errors, security hardening (stack protection + RELRO/BIND_NOW + CFG), and
# release symbol stripping.
if(USDEX_BUILDING_SDK)
    target_compile_options(usdex_build_options INTERFACE
        "$<${_gnu}:-Werror;-fstack-protector-strong>"
        "$<$<AND:${_gnu},${_x86_64}>:-fstack-clash-protection>"
        "$<${_msvc}:/WX;/guard:cf>"
    )
    target_link_options(usdex_build_options INTERFACE
        "$<${_gnu}:-Wl,-z,relro;-Wl,-z,now>"
        "$<$<AND:${_gnu},${_release}>:-Wl,-s>"
        "$<${_msvc}:/guard:cf>"
    )
endif()
