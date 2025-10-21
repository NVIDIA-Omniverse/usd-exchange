# Try the Samples

The best way to learn about OpenUSD Exchange functionality is to try out the OpenUSD Exchange Samples. These are simple applications that showcase many features and key concepts of the SDK.

You can execute the samples to try them out, learn from their source code, and modify them to experiment with OpenUSD and the OpenUSD Exchange SDK for yourself.

## Get the Samples

The OpenUSD Exchange Samples are available on [GitHub](https://github.com/NVIDIA-Omniverse/usd-exchange-samples). You can clone the repository or download the source as a zip file.

The [Samples README](https://github.com/NVIDIA-Omniverse/usd-exchange-samples/blob/main/README.md) provides detailed descriptions and documentation about the individual samples.

Each sample provides equivalent C++ and Python implementations. Before they can be used, you must first [build the Samples](#build-the-samples).


## Build the Samples

To try the Samples you will need to build them from source. The included build scripts make it easy.

``````{card}

`````{tab-set}

````{tab-item} Linux
:sync: linux

This project requires "make" and "g++".

1. Open a terminal.
2. To obtain "make" type `sudo apt install make` (Ubuntu/Debian), or `yum install make` (CentOS/RHEL).
3. For "g++" type `sudo apt install g++` (Ubuntu/Debian), or `yum install gcc-c++` (CentOS/RHEL).
4. Use the provided build script to download all other dependencies (e.g OpenUSD), create the Makefiles, and compile the code:
    ```bash
    ./repo.sh build
    ```
````

````{tab-item} Windows
:sync: windows

This project requires Microsoft Visual Studio 2019 or newer.

1. Download & install [Visual Studio with C++](https://visualstudio.microsoft.com/vs/features/cplusplus).
2. Use the provided build script to download all dependencies (e.g OpenUSD), create the projects, and compile the code:
```bash
.\repo.bat build
```
````

`````

``````

## Run the C++ Samples

Once you have built the samples, you can run their executables to try them. All of the compiled samples are executed with a `run` script with the program name as the first argument. There are many samples under the `source` folder, like `createStage`, `createLights`, `createTransforms`, etc.

``````{card}
`````{tab-set}

````{tab-item} Linux
:sync: linux

Use the `run.sh` script (e.g. `./run.sh createStage`) to execute each program with a pre-configured environment.

For command line argument help, use `--help`
```bash
./run.sh createStage --help
```
````

````{tab-item} Windows
:sync: windows

Use the `run.bat` script (e.g. `.\run.bat createStage`) to execute each program with a pre-configured environment.

For command line argument help, use `--help`
```batch
.\run.bat createStage --help
```
````
`````
``````

## Run the Python Samples

Setup and activate a virtual environment for USD Exchange as suggested in [Getting Started](./getting-started.md#installation). Run the samples within the virtual environment:

``````{card}

`````{tab-set}

````{tab-item} Linux
:sync: linux

For command line argument help, use `--help`
```bash
python source/python/createStage.py
```
````

````{tab-item} Windows
:sync: windows

For command line argument help, use `--help`

```powershell
python source\python\createStage.py
```
````

`````
``````

## Experiment

Once you have oriented yourself with the samples that interest you, try modifying the source code in the `source/` directory of the repository to experiment with the SDK. Once you've made your change, just repeat the **Build** and **Run** steps in this guide and test out your change.

When you're ready, see [Create a Native Application](./native-application.md) to learn how to start building your own application or simply continue using the Python wheels in your own scripts & modules.
