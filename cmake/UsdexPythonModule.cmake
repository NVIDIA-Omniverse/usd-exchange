# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Build a pybind11 Python extension module, mirroring repo_build.define_bindings_python:
#   - output named `_<module>` with the interpreter SOABI tag and no `lib` prefix, e.g.
#     `_usdex_core.cpython-310-x86_64-linux-gnu.so` / `_usdex_core.cp310-win_amd64.pyd`
#   - links Python + USD + the usdex library; NO `-Wl,--no-undefined`; no `_DEBUG` define
#   - installed to `python/usdex/<subdir>` next to its pure-python sources

include_guard(GLOBAL)

function(usdex_add_python_module target)
    cmake_parse_arguments(ARG "" "MODULE_NAME;SUBDIR" "SOURCES;PY_SOURCES;USD_LIBS;LINK" ${ARGN})

    Python3_add_library(${target} MODULE WITH_SOABI ${ARG_SOURCES})
    # installed to python/usdex/<subdir>/ -> sibling libs three dirs up ($ORIGIN keeps the package relocatable)
    set_target_properties(${target} PROPERTIES OUTPUT_NAME "_${ARG_MODULE_NAME}"
        INSTALL_RPATH "$ORIGIN/../../../${CMAKE_INSTALL_LIBDIR}")

    target_compile_definitions(${target} PRIVATE "MODULE_NAME=${ARG_MODULE_NAME}")
    target_include_directories(${target} PRIVATE "${CMAKE_SOURCE_DIR}/include")
    # pybind11 is third-party: SYSTEM so its headers don't trip our -Werror
    target_include_directories(${target} SYSTEM PRIVATE "${USDEX_PYBIND11_INCLUDE_DIR}")
    target_link_libraries(${target} PRIVATE usdex_build_options usdex_sdk_build_options usdex_usd_headers Python3::Python ${ARG_LINK})
    usdex_target_link_usd(${target} ${ARG_USD_LIBS})

    # install the compiled module beside its pure-python sources (RUNTIME covers the Windows .pyd)
    install(TARGETS ${target} LIBRARY DESTINATION python/usdex/${ARG_SUBDIR} RUNTIME DESTINATION python/usdex/${ARG_SUBDIR})
    install(FILES ${ARG_PY_SOURCES} DESTINATION python/usdex/${ARG_SUBDIR})
endfunction()
