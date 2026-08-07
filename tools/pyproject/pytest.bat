@echo off
setlocal

REM Run from the repo root so relative paths match the rest of the tooling
cd /d "%~dp0..\.."

set VENV=.\_build\tests\venv

REM Isolate the wheel under test: ensure the native build tree is not imported over the pip-installed wheel.
set PYTHONPATH=

REM (Re)create a clean venv with repo_man's vendored uv, then install the built wheel(s) with the test extras.
if exist "%VENV%" (
    rd /s /q "%VENV%"
)

call .\repo.bat uv -- venv --python .\_build\target-deps\python\python.exe "%VENV%"
if %errorlevel% neq 0 ( exit /b %errorlevel% )

REM Add our token's index to uv's native UV_EXTRA_INDEX_URL when set, appending to any the environment already provides
if not "%USDEX_UV_EXTRA_INDEX_URL%"=="" (
    if defined UV_EXTRA_INDEX_URL (
        set "UV_EXTRA_INDEX_URL=%UV_EXTRA_INDEX_URL% %USDEX_UV_EXTRA_INDEX_URL%"
    ) else (
        set "UV_EXTRA_INDEX_URL=%USDEX_UV_EXTRA_INDEX_URL%"
    )
)

for %%f in ("_build\packages\*.whl") do (
    call .\repo.bat uv -- pip install --python "%VENV%\Scripts\python.exe" "%%f[test]"
    if %errorlevel% neq 0 ( exit /b %errorlevel% )
)

REM Verify the usd-exchange modules import from the installed wheel, not a build-tree leak that could mask a broken wheel binary.
"%VENV%\Scripts\python.exe" tools\pyproject\check_wheel_imports.py
if %errorlevel% neq 0 ( exit /b %errorlevel% )

REM Run the tests with the venv interpreter
"%VENV%\Scripts\python.exe" -m unittest discover -v -s source\core\tests\unittest
if %errorlevel% neq 0 ( exit /b %errorlevel% )

"%VENV%\Scripts\python.exe" -m unittest discover -v -s source\rtx\tests\unittest
if %errorlevel% neq 0 ( exit /b %errorlevel% )

endlocal
