# OpenUSD Exchange License Notices

## Apache 2.0 License

The NVIDIA OpenUSD Exchange SDK is provided under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).

## Runtime License Notices

The NVIDIA OpenUSD Exchange SDK makes direct use of several 3rd Party Open Source Software (OSS). Each of these 3rd Party OSS may use other OSS internally.

Some of the runtime dependencies are compile-time optional, and some only apply to individual modules.

Detailed below are the licenses of all runtime dependencies of each OpenUSD Exchange library & module. Each dependency listed links to the relevant [individual licenses](#individual-licenses).

```{eval-rst}
.. note::
  OpenUSD uses many 3rd Party OSS to build and at runtime. Most of these are isolated to individual modules (USD plugins). Many are only relevant to a rendering context (e.g via Hydra) and do not apply to a 3D scene description authoring context. Some *do apply to 3D authoring*, but are not utilized by any OpenUSD Exchange SDK modules.

  The listings below do not include dependencies required to re-build (compile) the OpenUSD Exchange libraries. Similarly, they exclude licenses for OpenUSD modules that OpenUSD Exchange SDK does not leverage.

  This listing represents the technologies in-use for a shipping runtime that uses each OpenUSD Exchange module. If you ship a complete OpenUSD runtime as well (as opposed to our intentionally limited subset) you will need to gather the appropriate licenses manually. They can be found in `_install/target-deps/usd/release/PACKAGE-LICENSES` if you used `repo install_usdex` with default arguments.
```

The versions of some dependencies can vary across each build flavor of OpenUSD Exchange:
- Many are static/common to all flavors and are listed in the source code [target-deps xml file](https://github.com/NVIDIA-Omniverse/usd-exchange/blob/main/deps/target-deps.packman.xml).
- OpenUSD and Python versions vary per flavor, with all official flavors listed in [usd_flavors.json](https://github.com/NVIDIA-Omniverse/usd-exchange/blob/main/deps/usd_flavors.json).
- Additionally, as OpenUSD Exchange is open source, it can be recompiled against newer, older, or customized versions of any of its dependencies.

### Core C++ Shared Library

These licenses pertain to the `usdex_core` shared library.

**Mandatory Runtime Dependencies**

```{eval-rst}
- OpenUSD Exchange :ref:`(jump to license) <usdexlicense>`
- OpenUSD `(jump to license) <usd LICENSE_>`_
- TBB :ref:`(jump to license) <tbblicense>`
- hwloc :ref:`(jump to license) <hwloclicense>`
- zlib :ref:`(jump to license) <zliblicense>`
```

**Optional Runtime Dependencies**

These licenses are optional in that the python-less flavors of `usdex_core` do not use them.

```{eval-rst}
.. important::
  If you are using a `WITH_PYTHON` flavor, then these licenses become mandatory.
```

```{eval-rst}
- Python `(jump to license) <python LICENSE_>`_
- Boost :ref:`(jump to license) <boostlicense>`
```

### Core Python Module

These licenses pertain to the `usdex.core` python module, its compiled bindings library, and its use of the `usdex_core` shared library.

```{eval-rst}
- OpenUSD Exchange :ref:`(jump to license) <usdexlicense>`
- OpenUSD `(jump to license) <usd LICENSE_>`_
- TBB :ref:`(jump to license) <tbblicense>`
- hwloc :ref:`(jump to license) <hwloclicense>`
- zlib :ref:`(jump to license) <zliblicense>`
- Python `(jump to license) <python LICENSE_>`_
- Boost :ref:`(jump to license) <boostlicense>`
- pybind11 `(jump to license) <pybind11 LICENSE_>`_
- pyboost11 `(jump to license) <pyboost11 LICENSE_>`_
```

### C++ Python Binding Helpers

These licenses pertain to the `usdex/pybind` c++ headers and any compiled library or executable in which they are used (e.g. the `usdex.core` python binding library).

```{eval-rst}
- OpenUSD Exchange :ref:`(jump to license) <usdexlicense>`
- OpenUSD `(jump to license) <usd LICENSE_>`_
- Python `(jump to license) <python LICENSE_>`_
- Boost :ref:`(jump to license) <boostlicense>`
- pybind11 `(jump to license) <pybind11 LICENSE_>`_
- pyboost11 `(jump to license) <pyboost11 LICENSE_>`_
```

### C++ Test Helpers

These licenses pertain to the `usdex/test` c++ headers and any compiled library or executable in which they are used (i.e. [doctest](https://github.com/doctest/doctest) executable binaries).

```{eval-rst}
- OpenUSD Exchange :ref:`(jump to license) <usdexlicense>`
- OpenUSD `(jump to license) <usd LICENSE_>`_
- cxxopts `(jump to license) <cxxopts LICENSE_>`_
- doctest `(jump to license) <doctest LICENSE_>`_
```

### Python Test Module

These licenses pertain to the `usdex.test` python module, which is based on python's `unittest` framework.

```{eval-rst}
- OpenUSD Exchange :ref:`(jump to license) <usdexlicense>`
- OpenUSD `(jump to license) <usd LICENSE_>`_
- Omni Asset Validator `(jump to license) <omni.asset_validator LICENSE_>`_
- TBB :ref:`(jump to license) <tbblicense>`
- hwloc :ref:`(jump to license) <hwloclicense>`
- zlib :ref:`(jump to license) <zliblicense>`
- Python `(jump to license) <python LICENSE_>`_
- Boost :ref:`(jump to license) <boostlicense>`
- pybind11 `(jump to license) <pybind11 LICENSE_>`_
- pyboost11 `(jump to license) <pyboost11 LICENSE_>`_
```

### Source Code Inspiration

Some design patterns used in OpenUSD Exchange SDK source code may resemble those found in the following products. These licenses are relevant as inspiration only. There is no common implementation nor shipping binary that is relevant, neither at compile, link, nor runtime.

```{eval-rst}
- Cortex `(jump to license) <cortex LICENSE_>`_
- Gaffer `(jump to license) <gaffer LICENSE_>`_
```

## Individual Licenses

```{eval-rst}
.. _usdexlicense:

usd-exchange License
--------------------

.. dropdown:: usd-exchange License

   .. literalinclude:: /LICENSE.md
      :language: text
```

```{eval-rst}
.. include-licenses:: /_build/target-deps/usd/release/PACKAGE-LICENSES/usd-license.txt

.. include-licenses:: /_build/target-deps/omni_asset_validator/PACKAGE-LICENSES/omni.asset_validator-LICENSE.txt

.. Workaround for TBB as the name of the license file varies between packages

.. _tbblicense:

.. include-licenses:: /_build/target-deps/usd/release/PACKAGE-LICENSES/*tbb-LICENSE*

.. Workaround for hwloc as the license file only applies to oneTBB packages, but our docs build with older TBB

.. _hwloclicense:

.. include-licenses:: /tools/extra-licenses/hwloc-COPYING.txt

.. Workaround for zlib as the name of the license file varies between packages

.. _zliblicense:

.. include-licenses:: /_build/target-deps/usd/release/PACKAGE-LICENSES/zlib-LICENSE

.. include-licenses:: /_build/target-deps/cxxopts/PACKAGE-LICENSES/cxxopts-LICENSE.txt

.. include-licenses:: /_build/target-deps/doctest/PACKAGE-LICENSES/doctest-LICENSE.txt

.. include-licenses:: /_build/target-deps/usd/release/PACKAGE-LICENSES/python-LICENSE.txt

.. Workaround for Boost as the name of the license file varies between packages

.. _boostlicense:

.. include-licenses:: /_build/target-deps/usd/release/PACKAGE-LICENSES/boost-LICENSE*.txt

.. include-licenses:: /_build/target-deps/pybind11/PACKAGE-LICENSES/pybind11-LICENSE.txt

.. include-licenses:: /tools/internal-licenses/pyboost11-LICENSE.txt

.. include-licenses:: /tools/internal-licenses/cortex-LICENSE.txt

.. include-licenses:: /tools/internal-licenses/gaffer-LICENSE.txt
```
