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
FROM python:3.10-slim

# Install Python dependencies
RUN python3 -m venv usdex-env && \
    . usdex-env/bin/activate && \
    pip install usd-exchange

CMD . usdex-env/bin/activate && python3 -c 'import pxr.Usd, usdex.core; print(f"OpenUSD: {pxr.Usd.GetVersion()}\nOpenUSD Exchange: {usdex.core.version()}")'
```

Build and run with these commands:
```bash
docker build -t usdex_image .
docker run usdex_image
```

Output:
```
OpenUSD: (0, 25, 5)
OpenUSD Exchange: ${repo_docs_version}
```

```{eval-rst}
.. note::
  The example above is a specific base image with Python 3.10, but neither of these are strict requirements. The precompiled OpenUSD Exchange SDK binaries are ``manylinux_2_35`` compatible and available for multiple python versions.
```

```{eval-rst}
.. important::
  You must ensure that the OpenUSD libraries and plugins from the ``usd-exchange`` wheel are the **only** OpenUSD binaries configured in the container.

  If, for example, you had previously run ``pip install usd-core`` in your container, you will almost certainly have two copies of the OpenUSD binaries configured, and they are very likely to conflict with each other in unpredictable ways.
```

## Plugin to a DCC

This approach generally takes the form of a dynamic library and/or python module that is loaded into the DCC via a native plugin mechanism. Sometimes, they can be built into the DCC directly, if a single 3rd Party is developing both the DCC and integrating OpenUSD Exchange libraries and modules. For the purposes of this article we will consider both as "Plugins".

When integrating OpenUSD Exchange libraries and modules into an existing DCC Application, making your own library that links `usdex_core` (or module that imports `usdex.core`) is recommended.

See our [example runtime file layouts](./runtime-requirements.md#example-runtime-file-layouts) for a listing of dynamic libraries, python modules, and OpenUSD Plugins (`plugInfo.json`) that you will need to distribute along with your DCC Plugin.

You will also need to determine a few important details about your target DCC:

### Does it provide its own OpenUSD runtime?

If it does, you will likely want to match the exact OpenUSD binaries. You _might_ be able to use the prebuilt binaries from [`install_usdex`](./devtools.md#install_usdex) if they were built with compatible [dependencies and options](https://github.com/PixarAnimationStudios/OpenUSD/blob/release/BUILDING.md).

However, the more likely outcome is that you should re-compile the OpenUSD Exchange SDK from source code, making sure to compile & link against your application's USD distribution.

Once you have a USD distro assembled, you can "source link" it into a local clone of OpenUSD Exchange SDK:

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
git clone https://github.com/NVIDIA-Omniverse/usd-exchange.git
cd usd-exchange
./repo.sh source link usd_release ../path/to/your/usd
./repo.sh build
```
````
````{tab-item} Windows
:sync: windows

```bat
git clone https://github.com/NVIDIA-Omniverse/usd-exchange.git
cd usd-exchange
.\repo.bat source link usd_release ..\path\to\your\usd
.\repo.bat build
```
````
`````
``````

If you encounter missing file errors, it likely indicates a difference between your USD distro file layout and the ones NVIDIA produces internally. Inspect the two folder structures and try to align them.

```{eval-rst}
.. note::
  The ``repo source link`` command will generate a ``deps/usd-deps.packman.xml.user`` file with the relative filesystem path to your USD distro. The ``repo build`` command will respect this. If you want to alter the path later, you can hand edit this file. If you want to revert to using the pre-built USD distros, just remove this file entirely or call ``repo source unlink usd_release``.
```

See [CONTRIBUTING.md](https://github.com/NVIDIA-Omniverse/usd-exchange/blob/main/CONTRIBUTING.md#building) for more information on the OpenUSD Exchange SDK build process.

### Does it use TBB or Boost?

[TBB](https://oneapi-src.github.io/oneTBB) and [Boost](https://www.boost.org) are open source software that OpenUSD requires. While OpenUSD Exchange does not use them directly, several critical OpenUSD libraries do link & require them.

```{eval-rst}
.. note::
  In OpenUSD 24.11 the use of Boost was eliminated from many modules. It is still required for OpenVDB and OpenImageIO, but none of the modules used by OpenUSD Exchange SDK require Boost as of this version. If you want to avoid Boost, consider using 24.11 flavors (or newer).
```

If your application ships its own TBB or Boost, you _might_ be able to use the prebuilt binaries from [`install_usdex`](./devtools.md#install_usdex), it works out more often than not.

However, some applications use an older TBB or Boost library that is incompatible. There isn't any great way to detect this, other than to try & see if you hit issues. If you do, you should re-compile OpenUSD against your application's TBB and/or Boost libraries, then re-compile the OpenUSD Exchange SDK from source code, making sure to compile & link against your new USD distribution.

### Does it provide its own Python runtime?

If you want to use the OpenUSD or OpenUSD Exchange python modules, you will need a python interpreter at runtime. If your application has one natively, you will need to match at least the Python major.minor version to be able to import the precompiled python modules from [`install_usdex`](./devtools.md#install_usdex).

We support a range of python versions, but if yours is unsupported, you will need to re-compile both OpenUSD and the OpenUSD Exchange SDK modules from source code, making sure to compile & link against your application's Python distribution.

```{eval-rst}
.. warning::
  Even if you don't require python in your application, you may still require ``libpython.so/python3.dll`` as the OpenUSD C++ libraries do link python by default unless you are using a flavor of the OpenUSD binaries without the python dependency or have explicitly built OpenUSD without python. See `install_usdex <./devtools.html#install_usdex>`_ if you want to automatically install the necessary python library.
```
