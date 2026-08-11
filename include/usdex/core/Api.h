// SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

#pragma once

//! @file usdex/core/Api.h
//! @brief Symbol macros for this library

#include "Feature.h"

#ifdef __cplusplus
//! Declares a "C" exported external symbol.  This uses the "C" name decoration style of
//! adding an underscore to the start of the exported name.
#define USDEX_EXTERN_C extern "C"
#else
#define USDEX_EXTERN_C
#endif

#if defined(_WIN32)
//! This import tag will be used when including this header in other libraries.
//! See usdex_core_EXPORTS below.
#define USDEX_IMPORT __declspec(dllimport)
//! This export tag should only be used when tagging exported symbols from within usdex_core itself.
//! See usdex_core_EXPORTS below.
#define USDEX_EXPORT __declspec(dllexport)
#else
//! This import tag will be used when including this header in other libraries.
//! See usdex_core_EXPORTS below.
#define USDEX_IMPORT
//! This export tag should only be used when tagging exported symbols from within usdex_core itself.
//! See usdex_core_EXPORTS below.
#define USDEX_EXPORT __attribute__((visibility("default")))
#endif

//! Deprecate C++ API with an extra versioned message appended
//!
//! @param version: The major.minor version in which the function was first deprecated
//! @param message: A user facing message about the deprecation, ideally with a suggested alternative function.
//!     Do not include the version in this message, it will be appended automatically.
#define USDEX_DEPRECATED(version, message) [[deprecated(message ". It was deprecated in v" version " and will be removed in the future.")]]

//! Define USDEX_API macro based on whether or not we are compiling usdex_core,
//! or including headers for linking to it. Functions that wish to be exported from a .dll/.so
//! should be decorated with USDEX_API.
#ifdef usdex_core_EXPORTS
#define USDEX_API USDEX_EXPORT
#else
#define USDEX_API USDEX_IMPORT
#endif

// Allow consumers to use `pxr::` regardless of PXR_NS value.
// MSVC rejects redundant namespace aliases (C2386), so on Windows we detect
// whether PXR_NS is already "pxr" and skip the alias when it would be redundant.
// GCC/Clang accept redundant aliases per the C++ standard.
#include <pxr/base/arch/defines.h>
#include <pxr/pxr.h>
#if PXR_USE_NAMESPACES
#if defined(ARCH_OS_WINDOWS)
#pragma warning(push)
#pragma warning(disable : 4668)
#define USDEX_PP_CAT_IMPL(a, b) a##b
#define USDEX_PP_CAT(a, b) USDEX_PP_CAT_IMPL(a, b)
#define USDEX_PXR_NS_IS_pxr 1
#if !USDEX_PP_CAT(USDEX_PXR_NS_IS_, PXR_NS)
namespace pxr = ::PXR_NS;
#endif
#undef USDEX_PXR_NS_IS_pxr
#undef USDEX_PP_CAT
#undef USDEX_PP_CAT_IMPL
#pragma warning(pop)
#else
namespace pxr = ::PXR_NS;
#endif
#endif // PXR_USE_NAMESPACES
