## `usd-core` compatibility

`usd-exchange` already includes its required OpenUSD runtime and `pxr` modules. Do not install `usd-core` in the same environment. Installing both packages can overwrite shared files and cause import or runtime failures.

If both packages are installed, remove `usd-core` from any requirements or lock files. Then run:

```bash
pip uninstall usd-core
pip install --force-reinstall usd-exchange
```
