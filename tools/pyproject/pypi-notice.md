## Do not install `usd-core` in the same environment

The `usd-exchange` wheel bundles the OpenUSD runtime it was compiled against & installs the top-level `pxr` python modules alongside `usdex`. The `usd-core` wheel installs many of those same file paths, so installing one over the other silently overwrites files belonging to the first. Python packaging cannot declare this conflict, so `pip` reports success while leaving a `pxr` package that mixes two OpenUSD builds, which can load two different OpenUSD runtimes into a single process.

Install one or the other, never both. If you need the OpenUSD python modules, use the ones this wheel provides, as they match the OpenUSD version that `usdex.core` was compiled against.

Repairing an environment that already has both takes the same two steps with any package manager: remove `usd-core`, then reinstall `usd-exchange` so the shared files that removal deleted are restored. If a lockfile or dependency list describes the environment, drop `usd-core` from it first, or the next sync reintroduces the conflict. With `pip`, or `uv pip`, which accepts the same flags:

```
pip uninstall usd-core
pip install --force-reinstall usd-exchange
```

Importing `usdex.core` warns when it detects a `usd-core` distribution in the same environment.
