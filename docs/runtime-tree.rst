.. SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
.. SPDX-License-Identifier: Apache-2.0

.. tab-set::

    .. tab-item:: Linux Default
        :sync: linux

        .. code-block:: bash

            ├── lib
            │   ├── libusdex_core.so
            │   ├── libusdex_rtx.so                                         <-- optional
            │   ├── libpython3.12.so -> libpython3.12.so.1.0
            │   ├── libpython3.12.so.1.0
            │   ├── libpython3.so
            │   ├── libtbb.so.12
            │   ├── libusd_ar.so
            │   ├── libusd_arch.so
            │   ├── libusd_gf.so
            │   ├── libusd_js.so
            │   ├── libusd_kind.so
            │   ├── libusd_ndr.so                                           <-- USD 25.05 & older
            │   ├── libusd_pcp.so
            │   ├── libusd_plug.so
            │   ├── libusd_python.so
            │   ├── libusd_sdf.so
            │   ├── libusd_sdr.so
            │   ├── libusd_tf.so
            │   ├── libusd_trace.so
            │   ├── libusd_ts.so
            │   ├── libusd_usd.so
            │   ├── libusd_usdGeom.so
            │   ├── libusd_usdLux.so
            │   ├── libusd_usdPhysics.so
            │   ├── libusd_usdShade.so
            │   ├── libusd_usdUI.so
            │   ├── libusd_usdUtils.so
            │   ├── libusd_vt.so
            │   ├── libusd_work.so
            │   ├── libusd_usdLod.so                                        <-- optional (USD 26.08+)
            │   ├── libusd_usdMedia.so                                      <-- optional
            │   ├── libusd_usdMtlx.so                                       <-- optional
            │   ├── libusd_usdProc.so                                       <-- optional
            │   ├── libusd_usdProfiles.so                                   <-- optional (USD 26.08+)
            │   ├── libusd_usdRender.so                                     <-- optional
            │   ├── libusd_usdSemantics.so                                  <-- optional
            │   ├── libusd_usdSkel.so                                       <-- optional
            │   ├── libusd_usdVol.so                                        <-- optional
            │   ├── libMaterialXCore.so                                     <-- optional (ships with usdMtlx)
            │   ├── libMaterialXFormat.so                                   <-- optional (ships with usdMtlx)
            │   ├── libusd_usdGeomValidators.so                             <-- [test] only
            │   ├── libusd_usdLuxValidators.so                              <-- [test] only (USD 26.08+)
            │   ├── libusd_usdPhysicsValidators.so                          <-- [test] only
            │   ├── libusd_usdShadeValidators.so                            <-- [test] only
            │   ├── libusd_usdSkelValidators.so                             <-- [test] only
            │   ├── libusd_usdUtilsValidators.so                            <-- [test] only
            │   ├── libusd_usdValidation.so                                 <-- [test] only
            |   └── usd
            |       ├── plugInfo.json
            |       └── ...
            |           └── resources
            |               └── plugInfo.json
            ├── python                                                      <-- optional
            |   ├── pxr
            │   |   └── ...
            |   └── usdex
            |       ├── core
            |       │   ├── __init__.py
            |       │   ├── _AssetStructureBindings.py
            |       │   ├── _StageAlgoBindings.py
            |       │   ├── _usdex_core.cpython-310-x86_64-linux-gnu.so
            |       │   └── _usdex_core.pyi
            |       └── rtx                                                 <-- optional
            |           ├── __init__.py
            |           ├── _usdex_rtx.cpython-310-x86_64-linux-gnu.so
            |           └── _usdex_rtx.pyi
            └── python-runtime                                              <-- optional
                ├── bin
                ├── lib
                └── ...

    .. tab-item:: Linux `usd-minimal`

        .. code-block:: bash
            :caption:
                OpenUSD is a minimal build with compact dependencies.

            └── lib
                ├── libusdex_core.so
                ├── libusdex_rtx.so                                         <-- optional
                ├── libtbb.so.12
                ├── libusd_ms.so
                ├── libMaterialXCore.so
                ├── libMaterialXFormat.so
                └── usd
                    ├── plugInfo.json
                    └── ...
                        └── resources
                            └── plugInfo.json

    .. tab-item:: Windows Default
        :sync: windows

        .. code-block:: bash

            ├── bin
            │   ├── usdex_core.dll
            │   ├── usdex_rtx.dll                           <-- optional
            │   ├── python3.dll
            │   ├── python312.dll
            │   ├── tbb12.dll
            │   ├── usd_ar.dll
            │   ├── usd_arch.dll
            │   ├── usd_gf.dll
            │   ├── usd_js.dll
            │   ├── usd_kind.dll
            │   ├── usd_ndr.dll                             <-- USD 25.05 & older
            │   ├── usd_pcp.dll
            │   ├── usd_plug.dll
            │   ├── usd_python.dll
            │   ├── usd_sdf.dll
            │   ├── usd_sdr.dll
            │   ├── usd_tf.dll
            │   ├── usd_trace.dll
            │   ├── usd_ts.dll
            │   ├── usd_usd.dll
            │   ├── usd_usdGeom.dll
            │   ├── usd_usdLux.dll
            │   ├── usd_usdPhysics.dll
            │   ├── usd_usdShade.dll
            │   ├── usd_usdUI.dll
            │   ├── usd_usdUtils.dll
            │   ├── usd_vt.dll
            │   ├── usd_work.dll
            │   ├── usd_usdLod.dll                          <-- optional (USD 26.08+)
            │   ├── usd_usdMedia.dll                        <-- optional
            │   ├── usd_usdMtlx.dll                         <-- optional
            │   ├── usd_usdProc.dll                         <-- optional
            │   ├── usd_usdProfiles.dll                     <-- optional (USD 26.08+)
            │   ├── usd_usdRender.dll                       <-- optional
            │   ├── usd_usdSemantics.dll                    <-- optional
            │   ├── usd_usdSkel.dll                         <-- optional
            │   ├── usd_usdVol.dll                          <-- optional
            │   ├── MaterialXCore.dll                       <-- optional (ships with usdMtlx)
            │   ├── MaterialXFormat.dll                     <-- optional (ships with usdMtlx)
            │   ├── usd_usdGeomValidators.dll               <-- [test] only
            │   ├── usd_usdLuxValidators.dll                <-- [test] only (USD 26.08+)
            │   ├── usd_usdPhysicsValidators.dll            <-- [test] only
            │   ├── usd_usdShadeValidators.dll              <-- [test] only
            │   ├── usd_usdSkelValidators.dll               <-- [test] only
            │   ├── usd_usdUtilsValidators.dll              <-- [test] only
            │   ├── usd_usdValidation.dll                   <-- [test] only
            │   └── usd
            |       ├── plugInfo.json
            |       └── ...
            |           └── resources
            |               └── plugInfo.json
            ├── python                                      <-- optional
            |   ├── pxr
            │   |   └── ...
            |   └── usdex
            |       ├── core
            |       │   ├── __init__.py
            |       │   ├── _StageAlgoBindings.py
            |       |   ├── _usdex_core.cp312-win_amd64.pyd
            |       │   └── _usdex_core.pyi
            |       └── rtx                                 <-- optional
            |           ├── __init__.py
            |           ├── _usdex_rtx.cp312-win_amd64.pyd
            |           └── _usdex_rtx.pyi
            └── python-runtime                              <-- optional
                ├── bin
                ├── lib
                └── ...

    .. tab-item:: Windows `usd-minimal`

        .. code-block:: bash
            :caption:
                OpenUSD is a minimal build with compact dependencies.

            └── bin
                ├── usdex_core.dll
                ├── usdex_rtx.dll                           <-- optional
                ├── tbb12.dll
                ├── usd_ms.dll
                ├── MaterialXCore.dll
                ├── MaterialXFormat.dll
                └── usd
                    ├── plugInfo.json
                    └── ...
                        └── resources
                            └── plugInfo.json
