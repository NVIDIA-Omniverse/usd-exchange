@echo off
setlocal

REM Setup the build environment
set VENV=.\_build\tests\venv
echo Building: %VENV%
if exist "%VENV%" (
    rd /s /q "%VENV%"
)

.\_build\target-deps\python\python.exe -m venv "%VENV%"
if %errorlevel% neq 0 ( exit /b %errorlevel% )

call "%VENV%\Scripts\activate.bat"
if %errorlevel% neq 0 ( exit /b %errorlevel% )

for %%f in ("_build\packages\*.whl") do (
    python.exe -m pip install "%%f[test]"
    if %errorlevel% neq 0 ( exit /b %errorlevel% )
)

REM Run the tests
python.exe -m unittest discover -v -s source\core\tests\unittest
if %errorlevel% neq 0 ( exit /b %errorlevel% )

python.exe -m unittest discover -v -s source\rtx\tests\unittest
if %errorlevel% neq 0 ( exit /b %errorlevel% )

endlocal
