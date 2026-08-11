<!-- SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved. -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Getting Started

The OpenUSD Exchange SDK is available as Python wheels on [PyPI](https://pypi.org/project/usd-exchange/) and [PyPI NVIDIA](https://pypi.nvidia.com/usd-exchange/), making it easy to get started without having to build.

Many USD authoring workflows can be accomplished entirely in Python with the wheels, offering significant simplification in deployment and dependency management.

```{important}
  Each OpenUSD Exchange SDK release supports many OpenUSD versions and python versions. When using wheels, the python version is automatically determined based on the interpreter. However, the version of OpenUSD is currently locked in the python wheels. If you need to control OpenUSD version use the [install_usdex CLI](./devtools.md#install_usdex) instead of the python wheels.
```

## Installation

The recommended way to install the OpenUSD Exchange SDK for Python development is using a virtual environment:

``````{card}

`````{tab-set}

````{tab-item} Linux
:sync: linux

```bash
# Create a virtual environment
python -m venv usdex-env

# Activate the virtual environment
source usdex-env/bin/activate

# Install the OpenUSD Exchange modules
pip install usd-exchange
```
````

````{tab-item} Windows
:sync: windows

```powershell
# Create a virtual environment
python -m venv usdex-env

# Activate the virtual environment
usdex-env\Scripts\activate

# Install the OpenUSD Exchange modules
pip install usd-exchange
```
````

`````

``````

## Your First USD Stage

Create a simple Python script to test your installation:

```python
# hello_usdex.py
import pathlib
import usdex.core
from pxr import Gf, Usd, UsdGeom

# Create a new USD stage
identifier = "hello_world.usda"
stage = usdex.core.createStage(identifier, "Scene", UsdGeom.Tokens.y, 0.01, "OpenUSD Exchange SDK Example")

# Create and Xform and set the transform on it
xform = usdex.core.defineXform(stage, "/Scene")
cube = UsdGeom.Cube.Define(stage, xform.GetPrim().GetPath().AppendChild("Cube"))
usdex.core.setLocalTransform(
    prim=cube.GetPrim(),
    translation=Gf.Vec3d(10.459, 49.592, 17.792),
    pivot=Gf.Vec3d(0.0),
    rotation=Gf.Vec3f(-0.379, 56.203, 0.565),
    rotationOrder=usdex.core.RotationOrder.eXyz,
    scale=Gf.Vec3f(1),
)

# Save the stage
stage.Save()

print(f"Created USD stage '{pathlib.Path('./'+identifier).absolute()}' using:")
print(f"\tOpenUSD version: {Usd.GetVersion()}")
print(f"\tOpenUSD Exchange SDK version: {usdex.core.version()}")
```

Run your script within your virtual environment:

```bash
python hello_usdex.py
```

This will create a `hello_world.usda` file containing a rotated cube primitive.

## Try the Samples

[Try the OpenUSD Exchange Samples](./try-samples.md) to experiment further with the OpenUSD Exchange SDK.
