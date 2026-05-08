# Authoring USD Data

The OpenUSD Exchange SDK helps developers implement their own USD I/O solutions that produce consistent and correct USD assets across diverse 3D ecosystems.

It provides higher-level convenience functions on top of lower-level USD concepts, so developers can quickly adopt OpenUSD best practices when mapping their native data sources to OpenUSD-legible data models.

The goal is not to abstract the USD authoring process, but instead to simplify it, by providing convenience functions that cover common use cases and avoid common stumbling blocks.

Each of the subsections below describes a common challenge with OpenUSD and links to the relevant functions and classes in OpenUSD Exchange that aim simplify these problems.

## Layers and Stages

Whenever you are authoring OpenUSD data, ultimately, your data will need to be stored in a [SdfLayer](https://openusd.org/release/api/class_sdf_layer.html), whether it is in-memory, in a local or shared filesystem, or in cloud storage.

While you can author data directly via OpenUSD's [Sdf library](https://openusd.org/release/api/sdf_page_front.html), it is often more intuitive and convenient to author the layer via a [UsdStage](https://openusd.org/release/api/class_usd_stage.html) instead, so you can make use of higher level [schemas](https://openusd.org/release/api/class_usd_schema_base.html#details).

In either approach, your Layers should contain particular metadata to ensure they will load correctly across diverse 3D ecosystems. It is very common to forget (or misconfigure) this metadata. We provide [SdfLayer authoring](../api/group__layers.rebreather_rst) and [UsdStage Configuration](../api/group__stage__metadata.rebreather_rst) functions to assist & prevent common mistakes.

When authoring [UsdPrims](https://openusd.org/release/api/class_usd_prim.html) to a Stage, you will need to specify an [SdfPath](https://openusd.org/release/api/class_sdf_path.html) that identifies a unique location for the Prim. The nature of OpenUSD's [composition algorithm](https://openusd.org/release/glossary.html#composition) (know as "LIVERPS") makes it fairly complex to determine whether your chosen location is valid for authoring. We provide [UsdStage Prim Hierarchy](../api/group__stage__hierarchy.rebreather_rst) functions to assist.

### Binary vs Text Layers

`SdfLayers` can be written in several formats, the most common of which is `.usd`. However, any `.usd` file could be either USDA encoded (human-readable text) or USDC encoded (a binary [Crate](https://openusd.org/release/glossary.html#crate-file-format) encoding). Both encodings are also available as their own dedicated file extensions (`.usda` and `.usdc`), which help clarify the intent of content & prevent encoding mistakes. To ease introspection of USD layers, we provide a `getUsdLayerEncoding` function in our [SdfLayer authoring](../api/group__layers.rebreather_rst) module.

It is important to consider your content when choosing the encoding for your `SdfLayer`. A good default is to always prefer USDC encoding, but for lightweight "interface" layers or quick debugging layers it may be preferable to choose USDA encoding. Further guidance can be found [here](https://openusd.org/release/maxperf.html#use-binary-usd-files-for-geometry-and-shading-caches).

### USD Layer Versions

Both USDC and USDA file formats have their own associated version that is separate from the USD runtime version, as it impacts serialized content that may be loaded in newer or older runtimes. As the default versions differs across USD runtimes, this has implications on which USD Ecosystem products will be able to load each layer.

In a given USD runtime, these versions are hardcoded on the `UsdcFileFormat` and `UsdaFileFormat` objects. However, both formats provide [TfEnvSetting](https://openusd.org/release/api/env_setting_8h.html#details) to downgrade & target an older format, with auto-upgrade processes if necessary to support the authored features in the layer.

```{eval-rst}
.. note::
  In OpenUSD v25.11 and beyond, all of these objects were moved from the `usd` to the `sdf` module. In older runtimes, use e.g. `UsdUsdaFileFormat` and in newer runtimes use `SdfUsdaFileFormat`.
```

Accessing the version information is different for each file format. See [USDC Version Info](#usdc-version-info) and [USDA Version Info](#usda-version-info) respectively.

#### USDC Version Info

[CrateInfo](https://openusd.org/release/api/class_usd_crate_info.html) is a useful class to help determine your software's USDC capabilities.

```{eval-rst}
.. note::
  In OpenUSD v25.11 and beyond, `CrateInfo` was moved from the `usd` to the `sdf` module. In older runtimes, use `Usd.CrateInfo` and in newer runtimes use `Sdf.CrateInfo`.
```

- Use `CrateInfo::GetSoftwareVersion` to determine the newest possible Crate Version that your runtime could read.
- Use `CrateInfo::GetFileVersion` to determine the Crate Version with which a given `SdfLayer` was serialized.
- To determine your current default Crate Version, serialize a new layer and check `CrateInfo::GetFileVersion`.
  - Note this will not necessarily match `GetSoftwareVersion`; it is common for a runtime to serialize an older Crate Version than it can read, to maximize portability to other runtimes.
- If you need to target older runtimes than your default allows, be sure to set the [TfEnvSetting](https://openusd.org/release/api/env_setting_8h.html#details) `USD_WRITE_NEW_USDC_FILES_AS_VERSION` _before starting the process_.

#### USDA Version Info

Unlike USDC, there is no public function to programmatically query USDA version on an existing layer. However, as these files are plain text, it is trivial to parse the first line of the file to determine the version.

Rather than providing a standalone class like `CrateInfo`, the [UsdaFileFormat](https://openusd.org/release/api/class_sdf_usda_file_format.html#pub-static-methods) object provides direct methods for querying the min/max input & output versions.

```{eval-rst}
.. note::
  The USDA version inspection functions are *not* bound to python.
```

If you need to target older runtimes than your default allows, be sure to set the [TfEnvSetting](https://openusd.org/release/api/env_setting_8h.html#details) `USD_WRITE_NEW_USDA_FILES_AS_VERSION` _before starting the process_.

## Valid and Unique Names

OpenUsd has strict requirements on what names are valid for a `UsdObject`, which includes both `UsdPrim` and `UsdProperty` objects.

An [identifier is valid](https://openusd.org/release/api/group__group__tf___string.html#gaa129b294af3f68d01477d430b70d40c8) if it follows
the C/Python identifier convention; that is, it must be at least one character long, must start with a letter or underscore, and must contain
only letters, underscores, and numerals.

Additionally the names of sibling Objects must be unique so that the `SdfPath` that identifies them is unique within the `UsdStage`.

### Ascii and UTF-8 Support

In some current OpenUSD runtimes, valid characters within identifiers are restricted to the minimal ascii characters `[A-Za-z0-9_]`. The name of a `UsdProperty` can contain `:` delimiters for namespaces, however the values within each namespace must be a valid identifier.

```{eval-rst}
.. note::
  In OpenUSD v24.03 and beyond, XID identifiers are natively supported, but some reserved characters remain illegal (e.g. `/`, `@`).
```

For many data sources, native items will not conform to these requirements and the names will need to be made valid in order to be used in USD.

The [Prim and Property Names](../api/group__names.rebreather_rst) functions can be used to produce valid `UsdObject` names for any OpenUSD runtime
that we support.

## Defining Prims

OpenUsd provides Schema classes for authoring typed Prims, however in order to author a complete and correct Prim it is often necessary to call
multiple functions. It is common for some of these functions to be over looked, or have mismatched data supplied.

The OpenUSD Exchange SDK provides "define" functions to address this problem. The "define" functions are the primary entry point for authoring 3D data to USD.

The role of a "define" function is to:
- Ensure that a complete Prim definition is authored via a single function call
- Perform validation on the supplied data _before authoring the Prim_.
  - If any of the supplied data is invalid, then the Prim will not be authored. This up front validation avoids partial authoring of Prims.
- Ensure all opinions that contribute to the Prim's definition will be explicitly authored in a single Layer.

To learn about each of the "define" functions in more detail, see the specific documentation:
- [Xforms](../api/group__xform.rebreather_rst) (placement prims; the typical default prim of a placeable asset)
- [Polygon Meshes](../api/group__mesh.rebreather_rst)
- [Point Clouds / Particles](../api/group__points.rebreather_rst)
- [Lines and Curves](../api/group__curves.rebreather_rst)
- [Cameras](../api/group__cameras.rebreather_rst)
- [Lights](../api/group__lights.rebreather_rst)
- [Physics Joints](../api/group__physicsjoints.rebreather_rst)
- [Physics Materials](../api/group__physicsmaterials.rebreather_rst)
- [Preview Materials and Shaders](../api/group__materials.rebreather_rst)
- [RTX Materials and Shaders](../api/group__rtx__materials.rebreather_rst) (optionally included via `usdex_rtx`)

### Defining Primvars

All [UsdGeomPointBased](https://openusd.org/release/api/class_usd_geom_point_based.html) prims can optionally have geometric surface varying variables called [UsdGeomPrimvars](https://openusd.org/release/api/class_usd_geom_primvar.html) (primitive variables or simply "primvars") which interpolate across a primitive's topology, and can override shader inputs. In addition, any `UsdPrim` can have constant primvars, which are inherited down prim hierarchy to provide a convenient set-once-affect-many workflow within a hierarchy.

`UsdGeomPrimvars` are often used when authoring `UsdGeomPointBased` prims (e.g meshes, curves, and point clouds) to describe surface varying
properties such as normals, widths, displayColor, and displayOpacity. They can also be used to describe completely bespoke user properties that can affect how a prim is rendered, or to drive a surface deformation.

However, `UsdGeomPrimvar` data can be quite intricate to use, especially with respect to indexed vs non-indexed primvars, element size, the
complexities of `VtArray` detach (copy-on-write) semantics, and the ambiguity of "native" attributes vs primvar attributes (e.g. mesh normals).

We provide a templated [`PrimvarData` class](../api/group__primvars.rebreather_rst) to encapsulate all this data as a single object without risk of detaching (copying) arrays, and to provide simpler entry points to avoid common mistakes with respect to `UsdGeomPrimvar` data handling.

All of our USD authoring "define" functions for `UsdGeomPointBased` prims accept optional `PrimvarData` to define e.g normals, display colors, etc.

The `PrimvarData` class also supports reading from (and authoring to) any existing `UsdGeomPrimvar`, which may have been created via OpenUSD's [UsdGeomPrimvarsAPI](https://openusd.org/release/api/class_usd_geom_primvars_a_p_i.html), as well as self-validation and automated values indexing.

## Working with 3D Transformation

The [UsdGeomXformable](https://openusd.org/release/api/usd_geom_page_front.html#UsdGeom_Xformable) schema supports a rich set of transform operations
from which a resulting matrix can be computed.

The flexibility of this system adds complexity to the code required for authoring and retrieving transform information. The `usdex_core` library provides the [3D Transformation](../api/group__xformable.rebreather_rst) functions to help with this.

## Physics

[UsdPhysics](https://openusd.org/release/api/usd_physics_page_front.html) defines the physics-related prim and property schemas that together form a physics simulation representation. It is primarily designed around rigid body simulators, which take as input a list of rigid bodies and a list of constraints.

Many concepts in UsdPhysics are fairly straightforward and don't merit higher level authoring functions. For example:
- To make any [UsdGeomXformable](https://openusd.org/release/api/usd_geom_page_front.html#UsdGeom_Xformable) prim a rigid body use `UsdPhysicsRigidBodyAPI::Apply(prim)`
- To make any [UsdGeomGPrim](https://openusd.org/release/api/class_usd_geom_gprim.html) a collision object use `UsdPhysicsCollisionAPI::Apply(prim)`

```{eval-rst}
.. tip::
  Use the `Asset Validator <./devtools.html#asset-validator>`_ to ensure the ``UsdPhysics`` schemas have been used correctly.
```

However, some other UsdPhysics concepts are more intricate to author correctly, especially given often divergent approaches in the source data specifications across maximal coordinate (free-body) and reduced coordinate solvers.

Properly defining `PhysicsJoints` relative to both bodies can be arduous. The `usdex_core` library provides several [Physics Joints](../api/group__physicsjoints.rebreather_rst) functions to simplify the authoring process and ensure `PhysicsJoints` are aligned to both bodies, regardless of the source data specification.

Another complex aspect of UsdPhysics is specifying friction and other material properties via [PhysicsMaterialAPI](https://openusd.org/release/api/usd_physics_page_front.html#usdPhysics_physics_materials), which needs to be bound to the collision geometry similarly to how visual materials are bound to the render geometry. The `usdex_core` library provides [Physics Material](../api/group__physicsmaterials.rebreather_rst) functions to define, apply, and bind physics material properties like friction.

## Asset Structure

An asset is a named, versioned, and structured container of one or more resources which may include composable OpenUSD layers, textures, volumetric data, and more. There are many approaches to structuring assets, and no one structure is ideal for all use cases.

NVIDIA's [Principles of Scalable Asset Structure](https://docs.omniverse.nvidia.com/usd/latest/learn-openusd/independent/asset-structure-principles.html) article proposes four key principles that should always be considered: **legibility**, **modularity**, **performance**, and **navigability**.

It goes further, to discuss pros and cons of various production proven asset structures, and makes some explicit recommendations in the form of example assets towards the end of the article.

The `usdex_core` library provides an [Asset Structure](../api/group__assetstructure.rebreather_rst) module which aims to codify authoring of asset structures that have been proven scalable and have broad import compatibility across a wide range of OpenUSD enabled applications, while guiding and simplifying the development process for new OpenUSD Exporters.

In particular, we provide functions for:
- Static `Tokens` (strings) which can be used for Layer or Scope names, to ensure consistency across assets
- Defining relative References/Payloads whenever possible, and absolute References/Payloads only when necessary
- Creating the Atomic Component structure proposed in the article
  - Creating and organizing Content Layers and Library Layers in a consistent manner
  - Configuring an Asset Interface Layer, which payload's the content for deferred loading, while still exposing key metadata to the consumer

When you convert a source asset (an OBJ, STL, FBX, URDF, CAD file, etc.) into USD, the result is meant to be *placed* into larger scenes -- referenced into assemblies, instanced into synthetic-data layouts, posed by simulators, transformed by users. The asset's default prim therefore needs to be **placeable**: an [Xformable](https://openusd.org/release/api/class_usd_geom_xformable.html#details) prim that can accept a transform when it is referenced or payloaded into a parent stage. The simplest placeable default prim is an `Xform`, defined via `usdex::core::defineXform`, with geometry, materials, lights, and physics authored beneath it.

For reusable assets, also classify the default prim with [Kind](https://openusd.org/release/glossary.html#usdglossary-kind) -- typically [Component](https://openusd.org/release/glossary.html#usdglossary-component) for atomic models or [Assembly](https://openusd.org/release/glossary.html#usdglossary-assembly) for compositions of components. This is what lets DCCs, simulators, and asset browsers treat the conversion output as a first-class model rather than an opaque grouping. The `usdex_core` library provides `configureComponentHierarchy` and `configureAssemblyHierarchy` to set this up correctly across the prim and its descendants.

## Diagnostic Logs

OpenUSD's [Tf library](https://openusd.org/release/api/tf_page_front.html) provides various [diagnostic logging facilities](https://openusd.org/release/api/page_tf__diagnostic.html) which are useful for communicating errors, warnings, and status information to end users or system logs.

However, the default diagnostic output is somewhat engineer-centric. Fortunately, it provides the ability to override the default message handler, with one or more custom diagnostic delegates.

We provide one such [diagnostic delegate](../api/group__diagnostics.rebreather_rst) with some more controllable options (like level filtering), which you are welcome to use directly, or to use as inspiration for your own diagnostic delegate implementation.

Debug logs are emitted via OpenUSD's `TfDebug` mechanism, which is separate from the other diagnostics. See our [Debugging guide](./testing-debugging.md#debugging) for more information.

## Runtime Settings

Some OpenUSD Exchange behaviors (such as name transcoding) are controllable via global static [runtime settings](../api/group__settings.rebreather_rst), using OpenUSD’s `TfEnvSetting` mechanism, which relies on setting Environment Variables before the USD libraries are loaded into an application.

## Python Interoperability

Many projects use `pybind11` for python bindings, but OpenUSD 24.08 and older uses `boost::python`, while OpenUSD 24.11 and newer
uses a fork of `boost::python` called `pxr_python`.

We often need to pass the python objects in and out of c++ between a mix of bound functions. OpenUSD Exchange provides [`usdex/pybind` C++ headers](../api/group__pybind.rebreather_rst) to enable pybind11 to consume & to produce OpenUSD bound objects.
