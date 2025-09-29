-- Shared build scripts from repo_build package
repo_build = require("omni/repo/build")
repo_build.root = os.getcwd()

-- module to simplify premake setup further
usdex = true
usdex_build = require("tools/premake/usdex_build")

workspace "usd-exchange-sdk"
    usdex_build.setup_workspace({security_hardening=true})

project "devtools"
    kind "Utility"
    repo_build.prebuild_link({
        { "include", target_build_dir.."/include" },
        { "tools/repoman", target_build_dir.."/dev/tools/repoman" },
        { "tools/vscode", target_build_dir.."/dev/tools/vscode" },
    })
    -- serialize hardcoded usdex_options
    io.writefile(
        "_build/generated/usdex_options.lua",
        "USD_FLAVOR = \""..USD_FLAVOR.."\"\n"..
        "USD_VERSION = \""..USD_VERSION.."\"\n"..
        "PYTHON_VERSION = \""..PYTHON_VERSION.."\"\n"
    )
    -- copy usdex_build and serialized options
    repo_build.prebuild_copy({
        { "tools/premake/usdex_build.lua", target_build_dir.."/dev/tools/premake" },
        { "_build/generated/usdex_options.lua", target_build_dir.."/dev/tools/premake" },
    })
     -- generate a public packman config
     io.writefile(
        "_build/generated/config.packman.xml",
        "<config remotes=\"cloudfront\">\n"..
        "    <remote2 name=\"cloudfront\">\n"..
        "        <transport actions=\"download\" protocol=\"https\" packageLocation=\"d4i3qtqj3r0z5.cloudfront.net/${name}@${version}\" />\n"..
        "    </remote2>\n"..
        "</config>\n"
    )
    -- copy packman and generated public config
    repo_build.prebuild_copy({
        { "tools/packman", target_build_dir.."/dev/tools/packman" },
        { "_build/generated/config.packman.xml", target_build_dir.."/dev/tools/packman" },
    })

group "core"

    namespace = "usdex_core"

    project "core_library"
        usdex_build.use_usd({ "ar", "arch", "gf", "kind", "pcp", "plug", "sdf", "tf", "usd", "usdGeom", "usdLux", "usdPhysics", "usdShade", "usdUtils", "vt", "work" })
        usdex_build.shared_library{
            library_name = namespace,
            headers = { "include/usdex/core/*.h", "include/usdex/core/*.inl" },
            sources = { "source/core/library/*.cpp", "source/core/library/*.h" },
        }

    if usdex_build.with_python() then
        project "core_python"
            dependson { "core_library" }
            usdex_build.use_usd({"gf", "sdf", "tf", "usd", "usdGeom", "usdLux", "usdPhysics","usdShade", "vt"})
            usdex_build.use_usdex_core()
            usdex_build.python_module{
                bindings_module_name = namespace,
                bindings_sources = "source/core/python/bindings/*.cpp",
                python_sources = "source/core/python/*.py",
            }
    end

    project "core_test_executable"
        dependson { "core_library" }
        usdex_build.use_cxxopts()
        usdex_build.use_doctest()
        usdex_build.use_usd({"arch", "gf", "sdf", "tf", "usd", "usdGeom", "usdPhysics", "usdUtils", "vt"})
        usdex_build.use_usdex_core()
        -- Select correct TBB/oneTBB library based on USD version
        local _useOneTbb = USD_VERSION >= "25.08"
        filter { "system:windows", "configurations:release" }
            links { _useOneTbb and "tbb12" or "tbb" } -- required by use of TfErrorMarks
        filter { "system:windows", "configurations:debug" }
            links { _useOneTbb and "tbb12_debug" or "tbb_debug" } -- required by use of TfErrorMarks
        filter { "system:linux", "configurations:release" }
            links { "tbb" } -- required by use of TfErrorMarks
        filter { "system:linux", "configurations:debug" }
            links { "tbb_debug" } -- required by use of TfErrorMarks
        filter {}
        usdex_build.executable{
            name = "test_"..namespace,
            headers = { "source/core/tests/doctest/*.h" },
            sources = { "source/core/tests/doctest/*.cpp" },
        }

group "rtx"

    namespace = "usdex_rtx"

    project "rtx_library"
        dependson { "core_library" }
        usdex_build.use_usd({ "arch", "gf", "sdf", "tf", "usd", "usdGeom", "usdShade", "usdUtils", "vt" })
        usdex_build.use_usdex_core()
        usdex_build.shared_library{
            library_name = namespace,
            headers = { "include/usdex/rtx/*.h" },
            sources = { "source/rtx/library/*.cpp", "source/rtx/library/*.h" },
        }

    if usdex_build.with_python() then
        project "rtx_python"
            dependson { "rtx_library" }
            usdex_build.use_usd({"gf", "sdf", "tf", "usd", "usdShade", "vt"})
            usdex_build.use_usdex_rtx()
            usdex_build.python_module{
                bindings_module_name = namespace,
                bindings_sources = "source/rtx/python/bindings/*.cpp",
                python_sources = "source/rtx/python/*.py",
            }
    end

group "test"

    namespace = "usdex_test"

    project "devtools"
        kind "Utility"
        repo_build.prebuild_link({
            { "source/test/python", target_build_dir.."/python/usdex/test" },
        })
