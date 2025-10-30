# OpenUSD Exchange Dev Tools

Most users of OpenUSD Exchange SDK will have their own build systems & CI/CD processes, and our custom dev tools may be of limited use outside of the `usd-exchange` and `usd-exchange-samples` repositories.

However, there are three tools that we highly recommend using:

- The [Omniverse Asset Validator](#asset-validator) is a python module & command line interface for validating OpenUSD Stage/Layer data.
- The `usd-exchange` [python wheels](getting-started.md#installation) include an [optional test module](#python-wheel-optional-test-dependencies), which we recommend for integrating into CI/CD processes to ensure valid output of data converters.
- For C++ or mixed language developers, the [repo install_usdex](#install_usdex) tool can be used to acquire all of the OpenUSD Exchange build & runtime requirements, including the public headers for all relevant compiled libraries.


## Asset Validator

The Omniverse Asset Validator provides both a python module & command line interface for validating OpenUSD Stage/Layer data.

It includes a suite of validation rules that check for common USD authoring mistakes:
- All rules from OpenUSD's [usdchecker](https://openusd.org/release/toolset.html#usdchecker) CLI.
- Many additional rules, developed by NVIDIA, which are applicable to all OpenUSD Ecosystem products.
- It is easily extended & configured with your own custom python rules specific to your data or workflows.

It can be used in several ways:
- Interactively, to validate data on import into your application.
- As a runtime component in data exchange workflows, for validating at each hand-off gate in your pipeline.
- Integrated into CI/CD processes to test for correctness & compliance of OpenUSD data models.

See [Python Wheel Optional Test Dependencies](#python-wheel-optional-test-dependencies) for the simplest installation instructions.

To use the validator from python, with the default rules enabled, simply provide any layer URI (or composed `Usd.Stage` object) and validate:

```
import omni.asset_validator

# validate an existing layer file
engine = omni.asset_validator.ValidationEngine()
print(engine.validate("foo.usd"))

# validate a stage in memory
stage = Usd.Stage.CreateAnonymous()
# define prims
engine = omni.asset_validator.ValidationEngine()
print(engine.validate(stage))
```

There are also [CLI examples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples/blob/main/source/assetValidator/README.md) of the Asset Validator in [OpenUSD Exchange Samples](https://github.com/NVIDIA-Omniverse/usd-exchange-samples).

If you are using Python's [unittest framework](https://docs.python.org/3/library/unittest.html) for your regression testing, consider trying the [`usdex.test` python module](./python-usdex-test.rst) in your test suite. It includes a few `unittest.TestCase` derived classes to simplify some common OpenUSD testing scenarios, including the Asset Validator (e.g `self.assertIsValidUsd()`).

Unfortunately, the Omniverse Asset Validator is not yet available for pure C++ testing, but recent OpenUSD versions now include a [UsdValidatorSuite](https://openusd.org/release/api/class_usd_validator_suite.html#details) that is implemented in C++. Over time these two frameworks will align & validation should be possible from either C++ or Python.

## Python Wheel Optional Test Dependencies

If you would like to use the [`usdex.test` python module](./python-usdex-test.rst) that comes with the `usd-exchange` wheels, you will need to opt-in to the optional `test` dependencies as well. This pulls an additional wheel for the [Omniverse Asset Validator](#asset-validator).

```{important}
  Each OpenUSD Exchange SDK release supports many OpenUSD versions and python versions. When using wheels, the python version is automatically determined based on the interpreter. However, the version of OpenUSD is currently locked in the python wheels. If you need to control OpenUSD version use the [install_usdex CLI](./devtools.md#python-test-helpers) instead of the python wheels.
```

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
# Create a virtual environment
python -m venv usdex-env

# Activate the virtual environment
source usdex-env/bin/activate

# Install the OpenUSD Exchange modules with test dependency
pip install usd-exchange[test]
````
````{tab-item} Windows
:sync: windows

```powershell
# Create a virtual environment
python -m venv usdex-env

# Activate the virtual environment
usdex-env\Scripts\activate

# Install the OpenUSD Exchange modules with test dependency
pip install usd-exchange[test]
````
`````
``````

## install_usdex

If you want to build a native application or plugin, or if you need more flexibility than the [python wheels](#python-wheel-optional-test-dependencies) provide, we include a CLI to install the OpenUsd Exchange SDK.

Assembling the minimal runtime requirements of the SDK can be arduous. The `install_usdex` tool can be used to download precompiled binary artifacts for any flavor of the SDK, including all runtime dependencies, and assemble them into a single file tree on your local disk.

```{eval-rst}
.. important::
  Be sure to configure the ``--usd-flavor``, ``--usd-version``, ``--python-version``, and ``--version`` arguments appropriately to download your preferred flavor of OpenUSD Exchange SDK. See ``repo install_usdex -h`` for available options.
```

This tool can be invoked from a clone of the [GitHub repository](https://github.com/NVIDIA-Omniverse/usd-exchange) or from a source archive downloaded from an [official release](https://github.com/NVIDIA-Omniverse/usd-exchange/releases).

### Install usdex_core

By default, the tool will install the core library and module from OpenUSD Exchange SDK. For example, to download & assemble a USD 24.05 & Python 3.11 compatible binaries for OpenUSD Exchange v${repo_docs_version} call:

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
./repo.sh install_usdex --usd-version 24.05 --python-version 3.11 --version ${repo_docs_version}
```
````
````{tab-item} Windows
:sync: windows

```bat
.\repo.bat install_usdex --usd-version 24.05 --python-version 3.11 --version ${repo_docs_version}
```
````
`````
``````

Similarly, to download & assemble a minimal monolithic USD 24.11, with no python support, for OpenUSD Exchange v${repo_docs_version} call:

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
./repo.sh install_usdex --usd-flavor usd-minimal --usd-version 24.11 --python-version 0 --version ${repo_docs_version}
```
````
````{tab-item} Windows
:sync: windows

```bat
.\repo.bat install_usdex --usd-flavor usd-minimal --usd-version 24.11 --python-version 0 --version ${repo_docs_version}
```
````
`````
``````

### Extra OpenUSD plugins

If you need more OpenUSD modules than the strict minimal requirements of OpenUSD Exchange SDK, you can install them using `--install-extra-plugins`.

For example, to add on `usdSkel` and `usdVol` call:

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
./repo.sh install_usdex --version ${repo_docs_version} --install-extra-plugins usdSkel usdVol
```
````
````{tab-item} Windows
:sync: windows

```bat
.\repo.bat install_usdex --version ${repo_docs_version} --install-extra-plugins usdSkel usdVol
```
````
`````
``````

### Install usdex_rtx

If you are interested in RTX Rendering via NVIDIA Omniverse, you may want to use `usdex_rtx` to assist with [MDL Shader](https://www.nvidia.com/en-us/design-visualization/technologies/material-definition-language) authoring. Use the `--install-rtx` argument to install the [usdex_rtx library](../api/group__rtx__materials.rebreather_rst) and [`usdex.rtx` python module](./python-usdex-rtx.rst).

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
./repo.sh install_usdex --version ${repo_docs_version} --install-rtx
```
````
````{tab-item} Windows
:sync: windows

```bat
.\repo.bat install_usdex --version ${repo_docs_version} --install-rtx
```
````
`````
``````

### Python Test Helpers

If you would like to use our [`usdex.test` python module](./python-usdex-test.rst), or the [Omniverse Asset Validator](#asset-validator), you can use `--install-test` to install them both.

``````{card}
`````{tab-set}
````{tab-item} Linux
:sync: linux

```bash
./repo.sh install_usdex --version ${repo_docs_version} --install-test
```
````
````{tab-item} Windows
:sync: windows

```bat
.\repo.bat install_usdex --version ${repo_docs_version} --install-test
```
````
`````
``````

### repo_tools configuration

If you do use `repo_tools` in your project, you can configure `install_usdex` by adding the following to your `repo.toml` along with any tool configuration overrides from the default values:

```
[repo]
extra_tool_paths."++" = [
    "_build/target-deps/usd-exchange/release/dev/tools/repoman/repo_tools.toml",
]

[repo_install_usdex]
enabled = true
```

If you would like to run this process automatically during a build, add it to the post build commands:

```
[repo_build.post_build]
commands = [
    ["$root/repo${shell_ext}", "install_usdex", "-c", "$config"],
]
```

```{eval-rst}
.. repotools-file:: ../tools/repoman/repo_tools.toml
```

```{eval-rst}
.. repotools-confval:: staging_dir
.. repotools-confval:: install_dir
.. repotools-confval:: usd_flavor
.. repotools-confval:: usd_ver
.. repotools-confval:: python_ver
```
