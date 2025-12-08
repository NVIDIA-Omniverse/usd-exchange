# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
"""
`usdex.core <https://docs.omniverse.nvidia.com/usd/code-docs/usd-exchange-sdk/latest/docs/python-usdex-core.html>`_ provides higher-level convenience
functions top of lower-level `OpenUSD <https://openusd.org/release/index.html>`_ concepts, so developers can quickly adopt OpenUSD best practices
when mapping their native data sources to OpenUSD-legible data models.
"""

__all__ = [
    # core
    "version",
    "buildVersion",
    "deprecated",
    # settings
    "enableTranscodingSetting",
    # diagnostics
    "DiagnosticsLevel",
    "DiagnosticsOutputStream",
    "isDiagnosticsDelegateActive",
    "activateDiagnosticsDelegate",
    "deactivateDiagnosticsDelegate",
    "setDiagnosticsLevel",
    "getDiagnosticsLevel",
    "getDiagnosticLevel",
    "setDiagnosticsOutputStream",
    "getDiagnosticsOutputStream",
    # layers
    "hasLayerAuthoringMetadata",
    "setLayerAuthoringMetadata",
    "getLayerAuthoringMetadata",
    "saveLayer",
    "exportLayer",
    "getUsdLayerEncoding",
    # stage
    "createStage",
    "configureStage",
    "saveStage",
    "isEditablePrimLocation",
    # asset structure
    "getAssetToken",
    "getContentsToken",
    "getGeometryToken",
    "getLibraryToken",
    "getMaterialsToken",
    "getPayloadToken",
    "getPhysicsToken",
    "getTexturesToken",
    "definePayload",
    "defineReference",
    "defineScope",
    "createAssetPayload",
    "addAssetContent",
    "addAssetLibrary",
    "addAssetInterface",
    "configureAssemblyHierarchy",
    "configureComponentHierarchy",
    # names
    "getValidPrimName",
    "getValidPrimNames",
    "getValidChildName",
    "getValidChildNames",
    "NameCache",
    "ValidChildNameCache",
    "getValidPropertyName",
    "getValidPropertyNames",
    "getDisplayName",
    "setDisplayName",
    "clearDisplayName",
    "blockDisplayName",
    "computeEffectiveDisplayName",
    # xform
    "defineXform",
    "RotationOrder",
    "getLocalTransform",
    "getLocalTransformMatrix",
    "getLocalTransformComponents",
    "getLocalTransformComponentsQuat",
    "setLocalTransform",
    # geometry
    "definePointCloud",
    "definePolyMesh",
    "defineLinearBasisCurves",
    "defineCubicBasisCurves",
    "definePlane",
    "defineSphere",
    "defineCube",
    "defineCone",
    "defineCylinder",
    "defineCapsule",
    "computeMeshNormals",
    # camera
    "defineCamera",
    # primvars
    "FloatPrimvarData",
    "IntPrimvarData",
    "Int64PrimvarData",
    "Vec3fPrimvarData",
    "Vec2fPrimvarData",
    "StringPrimvarData",
    "TokenPrimvarData",
    # lights
    "isLight",
    "getLightAttr",
    "defineDomeLight",
    "defineRectLight",
    # materials
    "createMaterial",
    "bindMaterial",
    "computeEffectivePreviewSurfaceShader",
    "definePreviewMaterial",
    "addDiffuseTextureToPreviewMaterial",
    "addNormalTextureToPreviewMaterial",
    "addOrmTextureToPreviewMaterial",
    "addRoughnessTextureToPreviewMaterial",
    "addMetallicTextureToPreviewMaterial",
    "addOpacityTextureToPreviewMaterial",
    "addPrimvarShaderToPreviewMaterial",
    "connectPrimvarShader",
    "addPreviewMaterialInterface",
    "removeMaterialInterface",
    "ColorSpace",
    "getColorSpaceToken",
    "sRgbToLinear",
    "linearToSrgb",
    # physicsJoint
    "JointFrame",
    "definePhysicsFixedJoint",
    "definePhysicsRevoluteJoint",
    "definePhysicsPrismaticJoint",
    "definePhysicsSphericalJoint",
    "alignPhysicsJoint",
    "connectPhysicsJoint",
    # physicsMaterial
    "definePhysicsMaterial",
    "addPhysicsToMaterial",
    "bindPhysicsMaterial",
]

import os

# we must force import any USD module which defines types used as default values in usdex.core bindings
# in order for the expected pxr_python symbols to be registered before the usdex function loads
__import__("pxr.Gf")

if hasattr(os, "add_dll_directory"):
    __scriptdir = os.path.dirname(os.path.realpath(__file__))
    __dlldir = os.path.abspath(os.path.join(__scriptdir, "../../../lib"))
    __whl_libdir = os.path.abspath(os.path.join(__scriptdir, "../../usd_exchange.libs"))
    if os.path.exists(__dlldir):
        with os.add_dll_directory(__dlldir):
            from ._usdex_core import *  # noqa
    elif os.path.exists(__whl_libdir):
        with os.add_dll_directory(__whl_libdir):
            from ._usdex_core import *  # noqa
    else:
        # fallback to requiring the client to setup the dll directory
        from ._usdex_core import *  # noqa
else:
    from ._usdex_core import *  # noqa

# Import hand rolled python bindings
from ._AssetStructureBindings import *  # noqa
from ._StageAlgoBindings import *  # noqa


def deprecated(version: str, message: str):
    """
    Decorator used to deprecate public functions

    Example:

    .. code-block:: python

        @deprecated("0.5", "Use `baz` instead")
        def foo(bar: str) -> str:
            return baz(bar)

    Args:
        version: The major.minor version in which the function was first deprecated
        message: A user facing message about the deprecation, ideally with a suggested alternative function.
            Do not include the version in this message, it will be prefixed automatically.
    """

    def _wrap(func):

        # For init functions report the name of the class
        func_name = func.__name__
        if func_name == "__init__":
            func_name, _, _ = func.__qualname__.partition(".")

        warning = f"`{func_name}` was deprecated in v{version} and will be removed in the future. {message}"

        def deprecation(*args, **kwargs):
            from pxr import Tf

            Tf.Warn(warning)
            return func(*args, **kwargs)

        deprecation.__name__ = func.__name__
        deprecation.__doc__ = warning
        return deprecation

    return _wrap


class ValidChildNameCache(_usdex_core.ValidChildNameCache):

    @deprecated("1.1", "Use the NameCache class instead")
    def __init__(self) -> None:
        super().__init__()
