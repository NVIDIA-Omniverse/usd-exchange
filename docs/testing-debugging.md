# Testing and Debugging

When developing an application using OpenUSD Exchange SDK it is important to understand how to test your results & debug any issues you may run into.

## Testing the Results

It is a good idea to author test data in your source format which you can use during development and for regression testing.

Once your data is converted to USD, it is recommended to test it for correctness & compliance with OpenUSD, using a tool like [USD Validation](./devtools.md#asset-validator). It is a Python module & CLI which you can use to run a suite of validation rules that check for common USD authoring mistakes.

```{eval-rst}
.. note::
  While the Asset Validator was developed as a part of Omniverse, Kit is not required to use it. You can see example uses in the `OpenUSD Exchange Samples <https://github.com/NVIDIA-Omniverse/usd-exchange-samples>`__.
```

If you are using Python's [unittest framework](https://docs.python.org/3/library/unittest.html) for your regression testing, consider trying the [`usdex.test` python module](./python-usdex-test.rst) in your test suite. It includes a few `unittest.TestCase` derived classes to simplify some common OpenUSD testing scenarios, including the Asset Validator mentioned above (e.g `self.assertIsValidUsd()`), as well as context managers for asserting OpenUSD and OpenUSD Exchange Diagnostic logs. See [Python Wheel Optional Test Dependencies](./devtools.md#python-wheel-optional-test-dependencies) for installation instructions.

If you require C++ testing, consider using [doctest](https://github.com/doctest/doctest) and the [`usdex/test` headers](../api/namespace_usdex__test.rebreather_rst), which provide similar diagnostic log assertions for the doctest framework.

## Debugging

### Diagnostic Logs

OpenUSD provides [diagnostics facilities](https://openusd.org/release/api/page_tf__diagnostic.html) to issue coding errors, runtime errors, warnings and status messages. The OpenUSD Exchange SDK also uses these `TfDiagnostic` messages to relay detailed status, warning, and error conditions the user.

There are functions to activate and configure a specialized "diagnostics delegate" within the SDK detailed in the [Diagnostic Messages group](../api/group__diagnostics.rebreather_rst).

Users may immediately notice that the OpenUSD Exchange SDK function, `usdex::core::createStage()` emits a Status message to `stdout` like:

```text
Status: in saveStage at line 254 of ...\source\core\library\StageAlgo.cpp -- Saving "stage with rootLayer @.../AppData/Local/Temp/usdex/sample.usdc@, sessionLayer @anon:000001927295CA60:sample-session.usda@"
```

One way to filter out these messages is to activate the SDK's diagnostic delegate using `usdex::core::activateDiagnosticsDelegate()`. Once this diagnostics delegate is engaged, the default diagnostics level emitted is "warning", so the "status" messages will be hidden.

### TF_DEBUG Logs

OpenUSD ships with a debug logging feature that prints to `stdout`. You can configure OpenUSD logging using the `TF_DEBUG` environment variable or the `TfDebug` interface. All of the debug message types are available using the [`TfDebug::GetDebugSymbolDescriptions()`](https://openusd.org/release/api/class_tf_debug.html#ac31e63c4d474fd7297df4d1cdac10937) method.

Here are some useful examples that are present in recent USD releases:

```text
AR_RESOLVER_INIT         : Print debug output during asset resolver initialization
PLUG_LOAD                : Plugin loading
PLUG_REGISTRATION        : Plugin registration
USD_CHANGES              : USD change processing
USD_STAGE_LIFETIMES      : USD stage ctor/dtor messages
```

Additionally, OpenUSD Exchange SDK adds its own TF_DEBUG settings:

```text
USDEX_TRANSCODING_ERROR  : Indicates when UsdPrim or UsdProperty name string encoding fails
```

The debug variables can be combined using wildcards to enable multiple symbol messages:

```text
TF_DEBUG=*               : Enable all debug symbols
TF_DEBUG='PLUG_* AR_*'   : Enable debug symbols for all ``PLUG_*`` and ``AR_*`` messages
TF_DEBUG=USDEX_*         : Enable only the debug symbols for OpenUSD Exchange SDK messages
```

### Attaching a Debugger

`TF_DEBUG` can be set to cause a debug break in a debugger when a warning, error, or fatal diagnostic message is emitted.

```text
TF_ATTACH_DEBUGGER_ON_ERROR         : attach/stop in a debugger for all errors
TF_ATTACH_DEBUGGER_ON_FATAL_ERROR   : attach/stop in a debugger for fatal errors
TF_ATTACH_DEBUGGER_ON_WARNING       : attach/stop in a debugger for all warnings
```

To debug break in any of these while a debugger is attached to the process:

```text
TF_DEBUG=TF_ATTACH_DEBUGGER*
```

[ARCH_DEBUGGER_TRAP/ArchDebuggerTrap()](https://openusd.org/release/api/debugger_8h.html#ad9fc0e50dd7ec1d9636c7e1222a321be) is a direct way to break if a debugger is attached from within application code.
