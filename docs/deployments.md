<!-- SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Deployment Options

While there are certainly a large range of deployment options & styles, the most common cases for OpenUSD Exchange SDK customers fall into a few main categories:

- A Python application, module, or command line interface using [pip-installed wheels](#python-wheels)
- A standalone C++ [Executable](#standalone-executable) application.
- Deployed [in a Container](#docker-containers) (e.g. via [Docker](https://www.docker.com))
- A [plugin or extension](#plugin-to-a-dcc) to an existing Digital Content Creation (DCC) Application.

The sections below briefly discuss each of these options and list some common intricacies.

## Python Wheels

**Recommended for Python-only development**

The simplest way to deploy the OpenUSD Exchange SDK is using Python wheels, which handle all dependencies automatically.

This approach is ideal for several common use cases:
- Python-only applications and scripts
- Data processing pipelines
- Prototyping and experimentation
- Web services and APIs
- Jupyter notebooks and data science workflows
- CI/CD automation

### Virtual Environment Deployment

For development and testing:

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
# Create and activate virtual environment
python -m venv usdex-env
source usdex-env/bin/activate

# Install the SDK
pip install usd-exchange

# Your application can now import and use the SDK
python
>> import usdex.core
>> from pxr import Usd
>> print(usdex.core.version())
>> print(Usd.GetVersion())

```
````
````{tab-item} Windows
:sync: windows

```powershell
# Create and activate virtual environment
python -m venv usdex-env
usdex-env\Scripts\activate

# Install the SDK
pip install usd-exchange

# Your application can now import and use the SDK
python
>> import usdex.core
>> from pxr import Usd
>> print(usdex.core.version())
>> print(Usd.GetVersion())

```
````
`````
``````

```{eval-rst}
.. important::
  Ensure the OpenUSD libraries and plugins from ``usd-exchange`` are the **only** OpenUSD binaries configured in the virtual environment.

  If ``usd-core`` is in your venv, you will have conflicting copies of the OpenUSD binaries configured.

  To repair, ``pip uninstall usd-core`` and ``pip install --force-reinstall usd-exchange``
```

### Production Deployment

For production environments, pin specific versions:

```bash
# requirements.txt
usd-exchange==${repo_docs_version}
```

```bash
# Install exact versions
pip install -r requirements.txt
```

```{important}
  Each OpenUSD Exchange SDK release supports many OpenUSD versions and python versions. When using wheels, the python version is automatically determined based on the interpreter. However, the version of OpenUSD is currently locked in the python wheels. If you need to control OpenUSD version use the [install_usdex CLI](./devtools.md#install_usdex) instead of the python wheels.
```

### Container Deployment with Wheels

See the [docker section](#docker-containers) for container deployment with Python wheels.

## Standalone Executable

The most common use case for OpenUSD Exchange integrated standalone applications is for a headless data converter executable. Another common use case is for unit testing (and integration testing). Often, we write tests as standalone executables. Each of these apps must be able to bootstrap OpenUSD and OpenUSD Exchange libraries.

If your application can dynamically load C++ libraries, you should be able to use the prebuilt binaries from [`install_usdex`](./devtools.md#install_usdex) directly.

See our [example runtime file layouts](./runtime-requirements.md#example-runtime-file-layouts) for a listing of dynamic libraries, python modules, and OpenUSD Plugins (`plugInfo.json`) that you will need to distribute along with your executable program. You will need to ensure that the dynamic libraries are on the appropriate system path.

If you need command line arguments for your program, we recommend using [cxxopts](https://github.com/jarro2783/cxxopts), which is a header-only C++ command line option parser. The headers are available in the `--staging-dir` when you use [`install_usdex`](./devtools.md#install_usdex).

You can see many examples of standalone executables in the [OpenUSD Exchange Samples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples).

## Docker Containers

When integrating OpenUSD Exchange libraries and modules into a microservice or other containerized process, you will likely want to install from within your `Dockerfile`. The easiest way to use the OpenUSD Exchange SDK in a dockerfile is with the Python wheels.

Below is an example `Dockerfile` for a microservice that uses the [`usdex.core`](./python-usdex-core.rst) python module:

```dockerfile
FROM python:3.12-slim

# Install Python dependencies
RUN python3 -m venv usdex-env && \
    . usdex-env/bin/activate && \
    pip install usd-exchange

CMD ["usdex-env/bin/python3", "-c", "import pxr.Usd, usdex.core; print(f'OpenUSD: {pxr.Usd.GetVersion()}\\nOpenUSD Exchange: {usdex.core.version()}')"]
```

Build and run with these commands:
```bash
docker build -t usdex_image .
docker run usdex_image
```

Output:
```
OpenUSD: (0, 26, 8)
OpenUSD Exchange: ${repo_docs_version}
```

```{eval-rst}
.. note::
  The example above is a specific base image with Python 3.12, but neither of these are strict requirements. The precompiled OpenUSD Exchange SDK binaries are ``manylinux_2_35`` compatible and available for multiple python versions.
```

```{eval-rst}
.. important::
  Ensure the OpenUSD libraries and plugins from ``usd-exchange`` are the **only** OpenUSD binaries configured in the container.

  If ``usd-core`` is in your container, you will have conflicting copies of the OpenUSD binaries configured.

  To repair, uninstall ``usd-core`` and reinstall ``usd-exchange``
```

## Plugin to a DCC

This approach generally takes the form of a dynamic library and/or python module that is loaded into the DCC via a native plugin mechanism. Sometimes, they can be built into the DCC directly, if a single 3rd Party is developing both the DCC and integrating OpenUSD Exchange libraries and modules. For the purposes of this article we will consider both as "Plugins".

When integrating OpenUSD Exchange libraries and modules into an existing DCC Application, making your own library that links `usdex_core` (or module that imports `usdex.core`) is recommended.

See our [example runtime file layouts](./runtime-requirements.md#example-runtime-file-layouts) for a listing of dynamic libraries, python modules, and OpenUSD Plugins (`plugInfo.json`) that you will need to distribute along with your DCC Plugin.

You will also need to determine a few important details about your target DCC:

### Does it provide its own OpenUSD runtime?

If it does, you will likely want to match the exact OpenUSD binaries. You _might_ be able to use the prebuilt binaries from [`install_usdex`](./devtools.md#install_usdex) if they were built with compatible [dependencies and options](https://github.com/PixarAnimationStudios/OpenUSD/blob/release/BUILDING.md).

However, the more likely outcome is that you should re-compile the OpenUSD Exchange SDK from source code, making sure to compile & link against your application's USD distribution.

Once you have a USD distro assembled, build the OpenUSD Exchange SDK against it. The SDK is a single, standard CMake project, so any recent CMake works. Point it at your USD distro via `USDEX_USD_ROOT`. Because some OpenUSD public headers inline TBB symbols, oneTBB must also be discoverable. Put oneTBB on `CMAKE_PREFIX_PATH` (the SDK calls `find_package(TBB)`) or pass `USDEX_TBB_ROOT`. Pass `USDEX_MATERIALX_ROOT` for a separate MaterialX distribution. For Python bindings, select the Python version that matches OpenUSD and make its development installation discoverable. Also provide the pybind11 headers. The following example uses explicit roots for OpenUSD, TBB, MaterialX, and pybind11. It uses `CMAKE_PREFIX_PATH` for Python:

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
git clone https://github.com/NVIDIA-Omniverse/usd-exchange.git
cd usd-exchange
cmake -S . -B build \
  -DCMAKE_PREFIX_PATH=/path/to/your/python \
  -DUSDEX_USD_ROOT=/path/to/your/usd \
  -DUSDEX_TBB_ROOT=/path/to/your/tbb \
  -DUSDEX_MATERIALX_ROOT=/path/to/your/materialx \
  -DUSDEX_PYTHON_VERSION=3.12 \
  -DUSDEX_PYBIND11_INCLUDE_DIR=/path/to/pybind11/include
cmake --build build --config Release
```
````
````{tab-item} Windows
:sync: windows

```bat
git clone https://github.com/NVIDIA-Omniverse/usd-exchange.git
cd usd-exchange
cmake -S . -B build ^
  -DCMAKE_PREFIX_PATH=C:\path\to\your\python ^
  -DUSDEX_USD_ROOT=C:\path\to\your\usd ^
  -DUSDEX_TBB_ROOT=C:\path\to\your\tbb ^
  -DUSDEX_MATERIALX_ROOT=C:\path\to\your\materialx ^
  -DUSDEX_PYTHON_VERSION=3.12 ^
  -DUSDEX_PYBIND11_INCLUDE_DIR=C:\path\to\pybind11\include
cmake --build build --config Release
```
````
`````
``````

The build tree contains generator-specific compiler outputs. Run `cmake --install build --prefix <dir>` to assemble
the relocatable SDK tree that your own project should consume, including `lib/`, `bin/`, `python/`, and `include/`.

Consume the installed tree through `find_package(usd-exchange)`. Link the imported targets, then list each OpenUSD module that the application calls directly:

```cmake
find_package(usd-exchange REQUIRED)
add_executable(my_app main.cpp)
target_link_libraries(my_app PRIVATE usdex::core usdex::rtx)
usdex_target_link_usd(my_app usd usdGeom sdf)
```

Add the installed SDK to `CMAKE_PREFIX_PATH`. Provide the dependencies required by the OpenUSD distribution.

A Python-enabled OpenUSD distribution requires `Python.h`, because its public headers reach it through `VtValue`. The SDK detects this from the distribution itself and its imported targets supply the Python include path, whether or not the SDK ships bindings. The `usdex_target_link_usd` function also links `usd_python` and the Python runtime library for applications that use the OpenUSD APIs directly; extension modules receive the include path without the runtime library, which they resolve from the interpreter that loads them.

Set `USDEX_PYTHON_ROOT` to a Python development installation when the matching one is not already discoverable, or to override which one is used. The SDK package records the Python major and minor version it was built with and requires that exact version.

The OpenUSD Exchange Samples provide a complete [CMake project](https://github.com/NVIDIA-Omniverse/usd-exchange-samples/blob/main/CMakeLists.txt). The [Linux](https://github.com/NVIDIA-Omniverse/usd-exchange-samples/blob/main/build.sh) and [Windows](https://github.com/NVIDIA-Omniverse/usd-exchange-samples/blob/main/build.bat) scripts show the dependency roots and configure commands.

`usdex::core` / `usdex::rtx` propagate the OpenUSD include paths and the C++ compatibility settings (language standard, ABI, and platform defines) required to compile against the SDK's public headers. Only call `usdex_target_link_usd(my_app <modules...>)` for the OpenUSD modules your own code calls directly (e.g. `usd usdGeom sdf`). The SDK's build-time hygiene (strict warnings, hidden visibility) is *not* imposed on your project.

```{eval-rst}
.. note::
  Besides your USD distro, the default build enables the Python bindings and so needs Python (with development headers/libs) and pybind11. Provide pybind11 the same way you point the build at OpenUSD: pass ``-DUSDEX_PYBIND11_INCLUDE_DIR`` or add it to ``CMAKE_PREFIX_PATH``. Set ``-DUSDEX_PYTHON_VERSION`` to match your USD distro's Python (e.g. ``3.11``), or ``-DUSDEX_BUILD_PYTHON_BINDINGS=OFF`` to build without them. Note that a Python-enabled USD distro still requires Python either way, because its public headers include ``Python.h``; only pybind11 becomes unnecessary. The C++ test suite is opt-in via ``-DUSDEX_BUILD_TESTS=ON``, as it additionally requires cxxopts and doctest, supplied via ``-DUSDEX_CXXOPTS_INCLUDE_DIR`` / ``-DUSDEX_DOCTEST_INCLUDE_DIR``.
```

If you encounter missing file errors, it likely indicates a difference between your USD distro file layout and the ones NVIDIA produces internally — ``USDEX_USD_ROOT`` must contain ``include/`` (with ``pxr/``) and ``lib/``. Inspect the two folder structures and try to align them.

```{eval-rst}
.. note::
  NVIDIA developers building the internal flavor matrix (or source-linking a local USD via ``repo source link``) should use the ``repo build`` workflow described in `CONTRIBUTING.md <https://github.com/NVIDIA-Omniverse/usd-exchange/blob/main/CONTRIBUTING.md#building>`_ instead.
```

### Does it use TBB?

[TBB](https://oneapi-src.github.io/oneTBB) is open source software that OpenUSD requires. While OpenUSD Exchange does not use TBB directly, several critical OpenUSD libraries do link & require it, and some of OpenUSD's public headers directly include inlined tbb symbols.

If your application ships its own TBB, you _might_ be able to use the prebuilt binaries from [`install_usdex`](./devtools.md#install_usdex), it works out more often than not.

However, some applications use an older TBB library that is incompatible. There isn't any great way to detect this, other than to try & see if you hit issues. If you do, you should re-compile OpenUSD against your application's TBB libraries, then re-compile the OpenUSD Exchange SDK from source code, making sure to compile & link against your new USD distribution. It is common to locate TBB via a distinct distro rather than part of the USD distro, so when building the SDK from source you must make it discoverable. In cmake you can use `find_package(TBB)` (assuming your oneTBB distro is on `CMAKE_PREFIX_PATH`) or `USDEX_TBB_ROOT`, as covered in the build steps above.

### Does it provide its own Python runtime?

If you want to use the OpenUSD or OpenUSD Exchange python modules, you will need a python interpreter at runtime. If your application has one natively, you will need to match at least the Python major.minor version to be able to import the precompiled python modules from [`install_usdex`](./devtools.md#install_usdex).

We support a range of python versions, but if yours is unsupported, you will need to re-compile both OpenUSD and the OpenUSD Exchange SDK modules from source code, making sure to compile & link against your application's Python distribution.

```{eval-rst}
.. warning::
  Even if you don't require python in your application, you may still require ``libpython.so/python3.dll`` as the OpenUSD C++ libraries do link python by default unless you are using a flavor of the OpenUSD binaries without the python dependency or have explicitly built OpenUSD without python. See `install_usdex <./devtools.html#install_usdex>`_ if you want to automatically install the necessary python library.
```
