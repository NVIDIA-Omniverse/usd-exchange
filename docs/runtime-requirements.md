<!-- SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Runtime Requirements

If you are using the Python wheels, simply install the wheel using your preferred package manager. All runtime requirements are precompiled & self-contained within the wheel setup.

If you are building a compiled application or plugin that uses OpenUSD Exchange libraries and modules, there are a few considerations:

- The shared libraries can be placed anywhere, so long as they can be dynamically loaded at runtime using standard procedures on your operating system (e.g on the `PATH` or `LD_LIBRARY_PATH` environment variables).
- The OpenUSD Plugins (i.e. `plugInfo.json` files) **must** be placed within a subdirectory beneath the OpenUSD shared libraries.
- If you are using python, the `pxr` and `usdex` python modules can be placed anywhere, so long as they are configured appropriately for `sys.path` at runtime.

## Example runtime file layouts

For clarity, below are some suggested file layouts for our both default and "minimal" builds on Linux and Windows.

```{eval-rst}
.. note::
  As suggested above, if you need to use alternate paths for some or all of the normal shared libraries or python modules, that is fine. These are just default suggestions, which match the `install_usdex` defaults. The Python Wheels have a quite different file layout.
```

```{eval-rst}
.. include::
  runtime-tree.rst
```
