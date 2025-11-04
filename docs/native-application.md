# Create a Native Application

The next step to familiarize yourself with the OpenUSD Exchange SDK is to create a simple standalone application.

```{eval-rst}
.. note::
  This section specifically does not use Python wheels. It instead installs the SDK dependencies within a project structure of a native application, which may or may not include python runtime.
```

This section will teach you how to create an application that opens a `UsdStage`, reports basic stage configuration details, and lists all of the `UsdPrim` paths.

This walkthrough will use these tokens:
- `$project_root` - the base directory where the project application is located
  - To keep things clean, it is recommended that this is completely separate from either the OpenUSD Exchange SDK or Exchange Samples repo folders
- `$config` - the build configuration (`debug` or `release`)
- `$platform` - the platform (`linux-x86_64` or `windows-x86_64`)

## Install the SDK

Assembling the minimal requirements for the OpenUSD Exchange SDK can be complicated, so there is an [install_usdex](devtools.md#install_usdex) script that developers run to gather everything into one `_install` folder. This folder can then be copied into the project structure of the developer's application.

Running these commands from either the [Samples](./try-samples.md) root folder, or the `usd-exchange` repository itself, will generate the `_install` folder for both debug and release configurations and deep copy them to your project root.

```{eval-rst}
.. tab-set::

    .. tab-item:: Linux
      :sync: linux

        .. code-block:: bash

          # only fetch first when running from usd-exchange-samples
          ./repo.sh build --fetch-only

          ./repo.sh install_usdex --config release --install-python-libs
          ./repo.sh install_usdex --config debug --install-python-libs

          cp -Lr _install $project_root/usdex

    .. tab-item:: Windows
      :sync: windows

        .. code-block:: batch

          # only fetch first when running from usd-exchange-samples
          .\repo.bat build --fetch-only

          .\repo.bat install_usdex --config release --install-python-libs
          .\repo.bat install_usdex --config debug --install-python-libs

          robocopy /s _install $project_root\usdex > NUL
```

```{eval-rst}
.. note::
  The ``install_usdex`` script may be run from either the Exchange Samples or the Exchange SDK root directory, it is provided with both repositories.  If ``repo.bat|sh install_usdex`` is run from within the usd-exchange repository root, there is no need to run ``repo.bat|sh build`` first. The version of OpenUSD Exchange that is downloaded will match the top line of the USD Exchange repository's CHANGELOG.md if no ``--version`` argument is provided.
```

This tree describes the proposed file layout for the project:

```text
$project_root
│   Makefile or UsdTraverse.sln|vsproj
│   UsdTraverse.cpp
│   ...
└───usdex
    ├───target-deps            <----- build dependencies
    │   ├───python
    │   ├───usd
    │   └───usd-exchange
    └───$platform/$config      <----- runtime dependencies
        ├───lib
        └───python
            ├───pxr
            └───usdex
```

This `_install` folder will be copied into `$project_root/usdex` for this walkthrough.  Note that the `target-deps` folder contains soft links on Linux and junctions on Windows, so any time it is copied, it requires deep copy commands or options.

For more details on choosing build flavors & features, or different versions of the SDK, see the [install_usdex](devtools.md#install_usdex) documentation.

### Runtime Dependencies

The `install_usdex` tool will assemble the exact runtime requirements based on the build flavor you have selected, so the easiest approach is to copy the file tree that it generated.

There is some flexibility however. For more thorough details about how to deploy the runtime dependencies for an application or plugin using the OpenUSD Exchange SDK, see the [detailed runtime requirements](./runtime-requirements.md).

## Sample Program

The application performs a few simple things with OpenUSD and the OpenUSD Exchange SDK:

- Expects one argument, the path to a USD stage
  - Acceptable forms:
    - `C:/USD/helloworld.usd` or `/tmp/USD/helloworld.usd` - an absolute path
    - A relative path based on the CWD of the program (`sample.usda`)
  - Open the USD stage
  - Print the stage's up-axis
  - Print the stage's linear units, or "meters per unit" setting
  - Traverse the stage prims and print the path of each one
  - If the prim is `xformable` then print its position

It is included here to copy into a `UsdTraverse.cpp` file within `$project_root`

```cpp
// SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: MIT
//

#include <usdex/core/XformAlgo.h>

#include <pxr/usd/usd/primRange.h>
#include <pxr/usd/usd/stage.h>
#include <pxr/usd/usdGeom/metrics.h>
#include <pxr/usd/usdGeom/xformable.h>

#include <iostream>


// The program expects one argument, a path to a USD file
int main(int argc, char* argv[])
{
    if (argc != 2)
    {
        std::cout << "Please provide a local file path to a USD stage to read." << std::endl;
        return -1;
    }

    std::cout << "OpenUSD Stage Traversal: " << argv[1] << std::endl;

    pxr::UsdStageRefPtr stage = pxr::UsdStage::Open(argv[1]);
    if (!stage)
    {
        std::cout << "Failure to open stage.  Exiting." << std::endl;
        return -2;
    }

    // Print the stage metadata metrics
    std::cout << "Stage up-axis: " << pxr::UsdGeomGetStageUpAxis(stage) << std::endl;
    std::cout << "Meters per unit: " << pxr::UsdGeomGetStageMetersPerUnit(stage) << std::endl;

    // Traverse the stage, print all prim names, print transformable prim positions
    pxr::UsdPrimRange range = stage->Traverse();
    for (const auto& prim : range)
    {
        std::cout << prim.GetPath();

        if (pxr::UsdGeomXformable(prim))
        {
            pxr::GfTransform xform = usdex::core::getLocalTransform(prim);
            std::cout << ":" << xform.GetTranslation();
        }
        std::cout << std::endl;
    }
}
```

## Build Configuration

The build configurations below apply to the default flavor of OpenUSD Exchange SDK. Certain settings will vary for different flavors (e.g. python version).

```{eval-rst}
.. note::
  In OpenUSD 24.11 the use of Boost was eliminated from many modules. It is still required for OpenVDB and OpenImageIO, but none of the modules used by OpenUSD Exchange SDK require Boost as of this version. If you use the 24.11 flavors (or newer) all of the Boost configuration below can be removed.
```

### Linux

For Linux, all of the build configuration settings are described in the Makefile included here:

```makefile
# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: MIT

# This makefile is a simple example for an application, or converter for including, linking, and executing with
# OpenUSD and the OpenUSD Exchange SDK
#
# By default it will build against the release version of OpenUSD, to build against the debug version run `make CONFIG=debug`.

# The expectation is that OpenUSD, the OpenUSD Exchange SDK, and other dependencies are present in the `$project_root/usdex/target-deps` directory
DEPSDIR = $(CURDIR)/usdex/target-deps
PYTHONVER = python3.10
PROGRAMNAME = UsdTraverse

ifndef CONFIG
	CONFIG=release
endif

ifndef TARGETDIR
	TARGETDIR = $(CURDIR)/$(CONFIG)
endif

# Debug vs. Release differences
ifeq ($(CONFIG),debug)
	CONFIG_DEFINES += -g -DDEBUG -O0 -DTBB_USE_DEBUG=1
else ifeq ($(CONFIG),release)
	CONFIG_DEFINES += -DNDEBUG -O2
endif

# ABI Settings
ifndef ABI_DEFINES
	ABI_DEFINES = -D_GLIBCXX_USE_CXX11_ABI=1 -std=c++17
endif

# Ignored Warnings
ifndef IGNORED_WARNINGS
	IGNORED_WARNINGS = -Wno-deprecated -DTBB_SUPPRESS_DEPRECATED_MESSAGES
endif

# Include search directories
USDEX_INCLUDE_DIRS = \
 -isystem $(DEPSDIR)/usd-exchange/$(CONFIG)/include \
 -isystem $(DEPSDIR)/usd/$(CONFIG)/include

# USD libs (most of these not required, but this is a proper set for a fully featured converter)
USD_LIBS = \
 -lusd_ar \
 -lusd_arch \
 -lusd_gf \
 -lusd_js \
 -lusd_kind \
 -lusd_pcp \
 -lusd_plug \
 -lusd_sdf \
 -lusd_tf \
 -lusd_trace \
 -lusd_usd \
 -lusd_usdGeom \
 -lusd_usdLux \
 -lusd_usdPhysics \
 -lusd_usdShade \
 -lusd_usdUtils \
 -lusd_vt \
 -lusd_work

# For USD 24.11 and newer
USD_LIBS += \
 -lusd_python \
 -lusd_ts

ifeq ($(CONFIG),debug)
	USD_LIBS += -ltbb_debug
endif

# For USD 24.08 and older, uncomment and remove the block above.
# USDEX_INCLUDE_DIRS += \
#  -isystem $(DEPSDIR)/usd/$(CONFIG)/include/boost-1_78
# USD_LIBS += \
#  -lboost_python310

USDEX_LIBS = \
 -lusdex_core

# Library dependency directories
USDEX_LIB_DIRS = \
 -L$(DEPSDIR)/usd-exchange/$(CONFIG)/lib \
 -L$(DEPSDIR)/usd/$(CONFIG)/lib

# Python specifics
ifndef PYTHON_INCLUDE_DIR
	PYTHON_INCLUDE_DIR = -isystem $(DEPSDIR)/python/include/$(PYTHONVER)
endif

ifndef PYTHON_LIB
	PYTHON_LIB = -l$(PYTHONVER)
endif

ifndef PYTHON_LIB_DIR
	PYTHON_LIB_DIR = -L$(DEPSDIR)/python/lib
endif

# Common flags
CXXFLAGS += $(CONFIG_DEFINES) $(ABI_DEFINES) $(IGNORED_WARNINGS) -m64
INCLUDES += $(USDEX_INCLUDE_DIRS) $(PYTHON_INCLUDE_DIR)
LIBS += $(USD_LIBS) $(USDEX_LIBS) $(PYTHON_LIB)
LDFLAGS += $(USDEX_LIB_DIRS) $(PYTHON_LIB_DIR)

OBJS = $(TARGETDIR)/$(PROGRAMNAME).o

# Build Targets

all: $(TARGETDIR)/$(PROGRAMNAME)

# $@ matches the target; $< matches the first dependent
$(TARGETDIR)/$(PROGRAMNAME): $(OBJS)
	echo Linking $(PROGRAMNAME)
	g++ -o $@ $< $(LDFLAGS) $(LIBS)

$(OBJS): $(PROGRAMNAME).cpp | $(TARGETDIR)
	g++ $(INCLUDES) $(CXXFLAGS) -c $< -o $@

$(TARGETDIR):
	@echo Creating $(TARGETDIR)
	@mkdir -p $(TARGETDIR)

clean:
	rm -rf $(TARGETDIR)
```

### Windows

Create a new Visual Studio 2019 or 2022 project based on the `C++ Console App`, `Empty Project` template and call it `UsdTraverse`.  Make sure that the solution and project files live in `$project_root`.  Add the CPP source that traverses the USD file to the project. All of the settings specified in this section are found by right clicking on the created project and selecting `Properties` from within Visual Studio.

```{eval-rst}
.. note::
  The OpenUSD Exchange Samples include `Visual Studio solution and project files <https://github.com/NVIDIA-Omniverse/usd-exchange-samples/tree/main/source/usdTraverse>`_ with all of the below build configuration settings setup.  Because Visual Studio solutions aren't as portable as Makefiles, your mileage may vary with them and you may need to start from scratch with a new solution.
```

#### Header Include Paths

`VC++ Directories > External Include Directories`
```
usdex/target-deps/usd-exchange/$(CONFIGURATION)/include
usdex/target-deps/python/include
usdex/target-deps/usd/$(CONFIGURATION)/include
```

#### Library Include Paths

`VC++ Directories > Library Directories`
```
usdex/target-deps/usd-exchange/$(CONFIGURATION)/lib
usdex/target-deps/python/libs
usdex/target-deps/usd/$(CONFIGURATION)/lib
```

#### Compiler Flags from Settings
- Windows requires the `/std:c++17` flag, this can be enabled by setting the `C/C++ > Language > C++ Language Standard` to `ISO C++17 Standard`.
- The OpenUSD C++ headers generate many compiler warnings, the `/external:W0` flag will quiet them. Set `C/C++ > External Includes > External Header Warning Level` to `Turn Off All Warnings` (if the include folders were put into the `External Include Directories` list).

#### Preprocessor Definitions

`C/C++ > Preprocessor > Preprocessor Definitions` (all configurations)
```text
NOMINMAX
TBB_SUPPRESS_DEPRECATED_MESSAGES
```

The debug configuration will also need to use explicitly enable the debug build of TBB:
```text
TBB_USE_DEBUG=1
```

#### Libraries

`Linker > Input > Additional Dependencies` (All configurations)
```text
usdex_core.lib
usd_ar.lib
usd_arch.lib
usd_gf.lib
usd_kind.lib
usd_pcp.lib
usd_plug.lib
usd_sdf.lib
usd_tf.lib
usd_usd.lib
usd_usdGeom.lib
usd_usdLux.lib
usd_usdPhysics.lib
usd_usdShade.lib
usd_usdUtils.lib
usd_vt.lib
usd_work.lib
```

For USD 24.11 and newer:
```text
usd_python.lib
usd_ts.lib
```

For the release configuration of USD 24.08 and older:
```text
boost_python310-vc142-mt-x64-1_78.lib
```

For the debug configuration of USD 24.08 and older:
```text
boost_python310-vc142-mt-gd-x64-1_78.lib
```

Each OpenUSD module must be linked by the application separately.  The list above is a subset of all of them, but actually more than what the example requires.  For instance, `usd_usdLux.lib` includes the [UsdLux : USD Lighting Schema](https://openusd.org/release/api/usd_lux_page_front.html), but the example doesn't actually use any of the UsdLux interface.  The developer can trim this library list according to the needs of their application.


#### Debugger Environment

If you want to launch or debug the sample from within Visual Studio, the `PATH` environment variable must be set in the settings:

`Configuration Properties > Debugging` (All configurations)
```
PATH=usdex/windows-x86_64/$(CONFIGURATION)/lib
```

## Runtime Environment

The application must be able to find the shared libraries located in `usdex/$platform/$config/lib`.  These variables should be setup from a launching script, Visual Studio debugger settings, or from within the application itself before using the OpenUSD Exchange Core module.

```{eval-rst}
.. tab-set::

    .. tab-item:: Linux
      :sync: linux

        ``run_usdex_app.sh``

        .. code-block:: bash

            #!/bin/bash

            set -e

            export RUNTIME_PATH=./usdex/linux-x86_64/release
            export LD_LIBRARY_PATH=${RUNTIME_PATH}/lib:${LD_LIBRARY_PATH}

            ./release/UsdTraverse "$@"

    .. tab-item:: Windows
      :sync: windows

        ``run_usdex_app.bat``

        .. code-block:: batch

            @echo off
            setlocal

            set RUNTIME_PATH=usdex/windows-x86_64/release
            set PATH=%RUNTIME_PATH%/lib;%PATH%
            x64\release\UsdTraverse.exe %*
```

```{eval-rst}
.. warning::
  If OpenUSD is installed on your system and its paths are in your ``PATH`` environment variable, the samples may not run correctly.
```

## Debugging

For more information on debugging you application, see [Testing and Debugging](./testing-debugging.md).