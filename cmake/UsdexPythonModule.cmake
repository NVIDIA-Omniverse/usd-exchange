# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Build a pybind11 Python extension module, mirroring repo_build.define_bindings_python:
#   - output named `_<module>` with the interpreter SOABI tag and no `lib` prefix, e.g.
#     `_usdex_core.cpython-310-x86_64-linux-gnu.so` / `_usdex_core.cp310-win_amd64.pyd`
#   - links Python + USD + the usdex library; NO `-Wl,--no-undefined`; no `_DEBUG` define
#     Python arrives as Python3::Module via Python3_add_library(MODULE); a module must not link libpython
#   - installed to `${USDEX_INSTALL_PYTHONDIR}/usdex/<subdir>` next to its pure-python sources

include_guard(GLOBAL)

# Absolute install location of a usdex Python module, which USDEX_INSTALL_PYTHONDIR may give relative to the prefix
function(_usdex_python_module_dir out subdir)
    set(_dir "${USDEX_INSTALL_PYTHONDIR}/usdex/${subdir}")
    if(NOT IS_ABSOLUTE "${_dir}")
        set(_dir "${CMAKE_INSTALL_PREFIX}/${_dir}")
    endif()
    set(${out} "${_dir}" PARENT_SCOPE)
endfunction()

function(usdex_add_python_module target)
    cmake_parse_arguments(ARG "" "MODULE_NAME;SUBDIR" "SOURCES;PY_SOURCES;USD_LIBS;LINK" ${ARGN})

    Python3_add_library(${target} MODULE WITH_SOABI ${ARG_SOURCES})

    # the libs are found relative to wherever the module lands, so that the package stays relocatable
    _usdex_python_module_dir(_usdex_module_dir "${ARG_SUBDIR}")
    set(_usdex_lib_dir "${CMAKE_INSTALL_LIBDIR}")
    if(NOT IS_ABSOLUTE "${_usdex_lib_dir}")
        set(_usdex_lib_dir "${CMAKE_INSTALL_PREFIX}/${_usdex_lib_dir}")
    endif()
    file(RELATIVE_PATH _usdex_lib_rpath "${_usdex_module_dir}" "${_usdex_lib_dir}")

    set_target_properties(${target} PROPERTIES OUTPUT_NAME "_${ARG_MODULE_NAME}"
        INSTALL_RPATH "$ORIGIN/${_usdex_lib_rpath}")

    target_compile_definitions(${target} PRIVATE "MODULE_NAME=${ARG_MODULE_NAME}")
    target_include_directories(${target} PRIVATE "${CMAKE_SOURCE_DIR}/include")
    # pybind11 is third-party: SYSTEM so its headers don't trip our -Werror
    target_include_directories(${target} SYSTEM PRIVATE "${USDEX_PYBIND11_INCLUDE_DIR}")
    target_link_libraries(${target} PRIVATE usdex_build_options usdex_sdk_build_options usdex_usd_headers ${ARG_LINK})
    usdex_target_link_usd(${target} ${ARG_USD_LIBS})

    # install the compiled module beside its pure-python sources (RUNTIME covers the Windows .pyd)
    set(_usdex_dest "${USDEX_INSTALL_PYTHONDIR}/usdex/${ARG_SUBDIR}")
    install(TARGETS ${target} LIBRARY DESTINATION ${_usdex_dest} RUNTIME DESTINATION ${_usdex_dest})
    install(FILES ${ARG_PY_SOURCES} DESTINATION ${_usdex_dest})
endfunction()
