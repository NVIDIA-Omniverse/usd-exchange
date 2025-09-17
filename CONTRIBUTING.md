# Contributing to OpenUSD Exchange SDK

If you are interested in contributing to OpenUSD Exchange SDK, your contributions will fall
into three categories:
1. You want to report a bug, feature request, or documentation issue
2. You want to implement a feature or bug-fix for an outstanding issue
3. You want to propose a new Feature and implement it

In all cases, first search the existing [GitHub Issues](https://github.com/NVIDIA-Omniverse/usd-exchange/issues) to see if anyone has reported something similar.

If not, create a new [GitHub Issue](https://github.com/NVIDIA-Omniverse/usd-exchange/issues/new/choose) describing what you encountered or what you want to see changed. If you have feedback that is best explained in code, feel free to fork the repository on GitHub, create a branch demonstrating your intent, and either link it to the GitHub Issue or open a Pull Request back upstream. See [Code Contributions](#code-contributions) for more details.

Whether adding details to an existing issue or creating a new one, please let us know what companies are impacted.

## Code contributions

If you want to implement a feature, or change the logic of existing features, you are welcome to modify the code on a personal clone/mirror/fork & re-build the libraries from source. See [Building](#building) for more details.

If you want to contribute your changes back upstream, please first start a GitHub Issue as described above.

If you intend to submit a Pull Request:
- First, ensure alignment with the Code Owners on the associated Issue, to avoid redundant work or wasted iterations.
- Develop your changes on a well named [development branch](#development-branches) within your personal clone/mirror/fork.
- Run all test suites locally & ensure passing results in your dev environment.
- Ensure all commits have a sign-off (see [Developer Certificate of Origin](#developer-certificate-of-origin))

Please note that in some cases, we may not merge GitHub Pull Requests directly. We will take suggestions under advisement and discuss internally. We may rebase your commits to provide alignment with internal development branches.

### Developer Certificate of Origin

Rather than requiring a formal Contributor License Agreement (CLA), we use the [Developer Certificate of Origin](https://developercertificate.org/) to ensure contributors have the right to submit their contributions to this project.

Please ensure that all commits have a [sign-off](https://git-scm.com/docs/git-commit#Documentation/git-commit.txt-code--signoffcode) added with an email address that matches the commit author to agree to the DCO terms for each particular contribution.

```text
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

### Branches and Versions

The default branch is named `main` and it is a protected branch. Our internal CI Pipeline automatically builds & tests all changes from this branch across a large suite of OpenUSD & Python runtimes on both Windows and Linux (x86 and arm). However, all new features target the `main` branch, and we may merge code changes to this branch at any time; it is not guaranteed to be stable/usable and may break API/ABI regularly.

We advise to use an official tagged version of the OpenUSD Exchange SDK to ensure stability. Tagged releases are named e.g. `v1.2.3` following a [SemVer 2.0](https://semver.org) naming scheme. We guarantee API/ABI stability (for both C++ and Python) within any given major version series of releases, as well as support for all OpenUSD runtimes that the initial major version release was supporting.

Once a tagged release has passed internal QA processes, we push the tag to [OpenUSD Exchange SDK on GitHub](https://github.com/NVIDIA-Omniverse/usd-exchange) and author a corresponding [GitHub Release](https://github.com/NVIDIA-Omniverse/usd-exchange/releases). Official artifacts from tagged releases are deployed for both Linux (x86 and arm) and Windows, and the Windows flavors will be codesigned by NVIDIA Corporation.

> Note: We will occasionally provide pre-release alphas, betas, or release candidates prior to an official release. The API/ABI of these pre-releases is not guaranteed, and they should not be used in final runtime deployments. Consider these pre-releases ephemeral & unstable. They can be identified by the version suffix which will be in the form `(a|b|rc)[0-9]`

Long term support of any existing releases is done using a maintenance branch. The naming pattern for maintenance branches is e.g. `production/1.x` for the v1.0+ series of releases. Only hotfixes should target release branches. Hotfix tags also run through the usual CI/CD process, for testing, deployment, and codesigning.

### Development Branches

For all development, changes are pushed into a branch in personal development forks of usd-exchange, and code is submitted upstream for code review and CI verification before being merged into `main` or the target release branch.

We do not enforce any particular naming convention for development branches, other than avoiding the reserved branch patterns `main` and `production/*`. We recommend using legible branch names that imply the feature or fix being developed.

All code changes must contain either new unittests, or updates to existing tests, and we won't merge any code changes that have failing CI pipelines or sub-standard code coverage.

## Building

To build OpenUSD Exchange SDK yourself, use `repo.bat build` or `repo.sh build`, depending on your local platform.

The `repo build` command accepts additional arguments (e.g. `-config release`), see `repo build --help` for more information. Internally, `repo build` is using [Premake](https://premake.github.io) to perform cross-platform builds. See the `premake5.lua` file a the root of the repository to learn how the libraries are compiled.

### Build Flavors & Features

OpenUSD Exchange SDK can be compiled for many flavors of OpenUSD and Python. It is important to build using the dependencies required by your client application or other deployment. Additionally, some features of OpenUSD Exchange SDK are compile-time optional. For example, the libraries can be built with or without Python functionality.

To build OpenUSD Exchange SDK for different flavors of the upstream dependencies, we provide the following tokens that can be overridden on the commandline:
- `$usd_flavor`: either 'usd' or 'usd-minimal'
- `$usd_ver`: many options, see details below
- `$python_ver`: 3.12, 3.11, 3.10, 0 (disable python)

For example, to build with USD 24.11 and Python 3.10, call `repo --set-token usd_flavor:usd --set-token usd_ver:24.11 --set-token python_ver:3.10 build`.

Similarly, for a minimal monothlicic build of USD 24.05 with no python support, call `repo --set-token usd_flavor:usd-minimal --set-token usd_ver:24.05 --set-token python_ver:0 build`.

> Important : When building multiple flavors using the same working directories, you need to rebuild using `-x/--clean` to force premake to re-create all artifacts.

If you attempt a build and it is not successful, it may be because the upstream dependencies do not exist in this particular combination on your current platform. Validate that the packages for OpenUSD and Python all exist and are able to be downloaded successfully.

If your dependencies do exist and you are hitting a compiler or linker issue, you may have found an edge case in the build system that we have not accounted for yet. Feel free to file a GitHub Issue or ask in the appropriate forum.

### Requesting new Build Flavors

If none of the existing flavors meet the requirements of your application, you have two options:
1. Build OpenUSD Exchange SDK from source as and when you need to & manage the build artifacts yourself
2. Submit an Feature Request to add a new flavor to our matrix

## Testing

To run all the unittest suites, use `repo.bat test` or `repo.sh test`, depending on your local platform. We currently have 3 suites, `main`, `cpp`, and `whl`. Only the `main` suite runs by default, but a special `--suite all` argument will run them all. Any failure in any suite will fail the test process.

> Note: `repo test` uses the same `$usd_flavor`, `$usd_ver`, and `$python_ver` tokens as `repo build`. If you are building for a non-default flavor it is critical to supply the same token values to `repo test`. For example, `repo --set-token usd_ver:24.05 --set-token python_ver:3.11 test -s main`

### Main Test Suite

The `main` suite is a python [unittest](https://docs.python.org/3/library/unittest.html) suite and exercises the vast majority of OpenUSD Exchange SDK, as most public symbols are bound to python.

To run the `main` suite use `repo test -s main`.

If you want to isolate the `main` tests even further, `repo test -s main -f <pattern>` will filter down to a single test file or test pattern. See `repo test -h` for more information.

### Cpp Test Suite

The `cpp` suite is a [doctest](https://github.com/doctest/doctest) suite, and is only used to exercise those functions in OpenUSD Exchange SDK which cannot be bound to python, or those for which performance or multithreading requires using C++ entry points.

To run the `cpp` suite use `repo test -s cpp`.

### Wheel Test Suite

The `whl` suite is the same set of python unittests as in the `main` suite, but it is run from an isolated virtual environment using pip to install the .whl package.

To run the `whl` suite you must first build the wheel using `repo py_package` and then run the tests with `repo test -s whl`.

## Internal release instructions for Code Owners

This workflow requires tag names to be consistent, using the pattern "v" plus the semver at the top of [`CHANGELOG.md`](./CHANGELOG.md?plain=1#L1) (eg "v1.2.3"). Be sure to bump this version appropriately when updating CHANGELOG.md prior to tagging.

Once your Changelog updates are committed locally, submit the code changes for review targeting `main` or the relevant `production/X.x` maintenance branch.

> Note: If a maintenance branch does not exist for the release yet you should create one by checking out the appropriate tag (eg `git checkout v1.0.0; git switch -c production/1.x; git push upstream production/1.x`). Once it exists on the upstream remote, you are able to submit patches and author releases against this branch just as if it were `main`.

Next, author a "New Release" internally. This form will allow you to create the tag, name the release, set the tag message, and copy/paste the relevant changes into the release notes.

> Note: Typically the tag message can be the same as the tag name, e.g. "v1.0.0"

Finally, press "Create Release" at the bottom of the page. The tag will be added to the repository and shortly afterwards a CI job will start the associated CI/CD run automatically.

> Note: For tagged builds, we generate 2 copies of the package, one with the full build version string and one with a simple SEMVER version. These are identical packages, in fact its just a copy/link operation on the server side. In release announcements we should advertise the simple SEMVER package rather than the more complex version, as this is the package that will be made publicly available.

Wait for the publishing to finish, give the artifacts a brief manual QA test, and announce the release in the appropriate internal forums.
