local m = {} -- The main module table

repo_build = require("omni/repo/build")
repo_build.setup_options()

repo_usd = require("_repo/deps/repo_usd/templates/premake/premake5-usd")

-- Setup build flavor options

include("usdex_options")
print("[usdex_build (lua)] Building with usd_flavor="..USD_FLAVOR.." and usd_ver="..USD_VERSION.." and python_ver="..PYTHON_VERSION)

-- Common Global Variables

client = not usdex

target_build_dir = target_build_dir or repo_build.target_dir()
target_bin_dir = target_bin_dir or target_build_dir.."/bin"
target_lib_dir = target_lib_dir or target_build_dir.."/lib"
target_python_dir = target_python_dir or target_build_dir.."/python"
target_deps = target_deps or repo_build.target_deps_dir()

-- note this variable only affects Linux builds
python_version_suffix = PYTHON_VERSION

-- Workspace Helpers

-- Configure workspace defaults.
-- This function will set up the premake workspace to add standard platforms and configurations.
-- The args match `repo_build.setup_workspace()`, but the defaults are changed in some cases.
function m.setup_workspace(args)
    print("[usdex_build (lua)] workspace setup")

    local args = args or {}

    repo_build.setup_workspace({
        windows_x86_64_enabled = args.windows_x86_64_enabled or true,
        linux_x86_64_enabled = args.linux_x86_64_enabled or true,
        linux_aarch64_enabled = args.linux_aarch64_enabled or true,
        macos_universal_enabled = args.macos_universal_enabled or false,
        copy_windows_debug_libs = args.copy_windows_debug_libs or false,
        allow_undefined_symbols_linux = args.allow_undefined_symbols_linux or true,
        extra_warnings = args.extra_warnings or true,
        security_hardening = args.security_hardening or false,
        fix_cpp_version = args.fix_cpp_version or true,
        -- enable modern gcc warnings
        linux_gcc7_warnings = args.linux_gcc7_warnings or false
    })

    repo_build.enable_vstudio_sourcelink()
    repo_build.remove_vstudio_jmc()

    exceptionhandling "On"
    rtti "On"

    filter { "configurations:debug" }
        defines { "TBB_USE_DEBUG=1" }
    filter {}

    filter { "system:windows" }
        defines { "NOMINMAX" }
    filter { "system:linux" }
        buildoptions { "-fvisibility=hidden", "-fdiagnostics-color", "-Wno-deprecated", "-Wconversion" }
    filter {}

    flags { "ShadowedVariables" }
end

-- Common Buildable Artifacts

-- Create a C++ shared library project
-- @param library_name: The base file name for the compiled binary target
-- @param headers: A list of header files to add to the project
-- @param sources: A list of source files to add to the project
function m.shared_library(options)
    kind "SharedLib"
    m.__library(options)
end

-- Create a C++ static library project
-- @param library_name: The base file name for the compiled binary target
-- @param headers: A list of header files to add to the project
-- @param sources: A list of source files to add to the project
function m.static_library(options)
    kind "StaticLib"
    m.__library(options)
end

function m.__library(options)
    -- check options
    if type(options.library_name) ~= "string" then
        error("`library_name` must be specified")
    end

    local library_name = options.library_name
    local headers = options.headers or {}
    local sources = options.sources or {}

    language "C++"
    defines { library_name.."_EXPORTS" }
    location (repo_build.workspace_dir().."/"..library_name)
    includedirs { "include" }
    libdirs { target_lib_dir }
    files { headers, sources }
    filter { "system:windows" }
        if os.isfile("version.rc") then
            files{ "version.rc" }
        end
    filter {}
    targetdir(target_lib_dir)
    targetname(library_name)

end

-- Create a C++ executable ConsoleApp project
-- @param name: The base file name for the compiled binary target
-- @param headers: A list of header files to add to the project
-- @param sources: A list of source files to add to the project
function m.executable(options)
    -- check options
    if type(options.name) ~= "string" then
        error("`name` must be specified")
    end

    local name = options.name
    local sources = options.sources or {}
    local headers = options.headers or {}

    kind "ConsoleApp"
    language "C++"
    location (repo_build.workspace_dir().."/"..name)
    includedirs { "include" }
    libdirs { target_lib_dir }
    files { headers, sources }
    filter { "system:windows" }
        if os.isfile("version.rc") then
            files{ "version.rc" }
        end
    filter {}
    targetdir(target_bin_dir)
    targetname(name)
end

function m.python_module(options)
    -- check options
    if type(options.module_name) ~= "string" and type(options.bindings_module_name) ~= "string" then
        error("One of `module_name` or `bindings_module_name` must be specified")
    end

    bindings_module_name = options.bindings_module_name
    python_module_name = options.module_name or bindings_module_name:gsub("_", ".")
    module_dir = python_module_name:gsub("%.", "/")
    python_sources = options.python_sources or {}
    bindings_sources = options.bindings_sources or {}

    target_bindings_dir = target_python_dir.."/"..module_dir

    repo_build.prebuild_copy({ python_sources, target_bindings_dir })

    if bindings_sources then

        m.use_pybind()

        defines { "MODULE_NAME="..bindings_module_name }
        includedirs { "include" }
        libdirs { target_lib_dir }
        files { python_sources, bindings_sources }
        targetdir(target_bindings_dir)

        repo_build.define_bindings_python("_"..bindings_module_name, target_deps.."/python", PYTHON_VERSION)

        -- its unclear why repo_build adds "-Wl,--no-undefined", but we don't want it
        -- or we'd have to explicitly link every upstream dependency
        removelinkoptions { "-Wl,--no-undefined" }

        -- this causes a compiliation error in the tbb headers... its doing something for pybind11, but
        -- its not clear what we're losing by removing this, nor how to avoid the tbb issue otherwise.
        removedefines {"_DEBUG"}

    end

end

-- usd-exchange artifacts

function m.use_usdex_core()
    links { "usdex_core" }

    if client == true then
        usdex_path = target_deps.."/usd-exchange"
        usdex_build_path = usdex_path.."/%{cfg.buildcfg}"
        externalincludedirs { usdex_build_path.."/include" }
        syslibdirs { usdex_build_path.."/lib" }
    end
end

function m.use_usdex_rtx()
    m.use_usdex_core()
    links { "usdex_rtx" }
end

-- Common Dependencies

function m.with_python()
    return PYTHON_VERSION ~= "0"
end

function m.use_pybind()
    externalincludedirs { target_deps.."/pybind11/include" }
end

function m.use_python()
    python_folder = target_deps.."/python"

    filter { "system:windows" }
        externalincludedirs { python_folder.."/include" }
        syslibdirs { python_folder.."/libs" }
    filter { "system:linux" }
        externalincludedirs { python_folder.."/include/python"..python_version_suffix }
        syslibdirs { python_folder.."/lib" }
        links { "python"..python_version_suffix }
    filter {}
end

function m.use_cxxopts()
    externalincludedirs { target_deps.."/cxxopts/include" }
end

function m.use_doctest()
    externalincludedirs { target_deps.."/doctest/include" }
    filter { "system:windows" }
        disablewarnings {
            "4805", -- '==': unsafe mix of type 'const bool' and type 'const R' in operation
        }
    filter {}
end

function m.use_usd(usd_libs)
    usd_root = target_deps.."/usd/%{cfg.buildcfg}"
    usd_lib_path = usd_root.."/lib"

    if PYTHON_VERSION == "0" then
        python_root = nil
    else
        python_root = target_deps.."/python"
    end

    repo_usd.use_usd(
        {
            usd_root=usd_root,
            usd_suppress_warnings=true,
            python_root=python_root,
            python_version=PYTHON_VERSION
        },
        usd_libs
    )

    -- Suppress deprecated tbb/atomic.h and tbb/task.h warnings from OpenUSD
    defines { "TBB_SUPPRESS_DEPRECATED_MESSAGES" }

    filter { "system:linux" }
        linkoptions { "-Wl,-rpath-link,"..repo_build.get_abs_path(usd_lib_path) }
    -- repo_usd should be doing this eventually
    filter { "system:windows" }
        if USD_VERSION < "24.11" then
            defines { "BOOST_LIB_TOOLSET=\"vc142\"" }
        end
    filter {}
end

return m
