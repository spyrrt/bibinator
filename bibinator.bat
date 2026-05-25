@echo off
setlocal

set SCRIPT_DIR=%~dp0
set VENV_DIR=%SCRIPT_DIR%.venv

where py >nul 2>&1
if %errorlevel% == 0 (
    set SYS_PYTHON=py
    goto found_python
)
where python >nul 2>&1
if %errorlevel% == 0 (
    set SYS_PYTHON=python
    goto found_python
)
echo Error: Python is not installed.
pause
exit /b 1

:found_python
for /f "tokens=*" %%i in ('%SYS_PYTHON% --version') do echo Using %%i

if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    %SYS_PYTHON% -m venv "%VENV_DIR%"
)

set PYTHON=%VENV_DIR%\Scripts\python.exe

echo Installing dependencies...
"%PYTHON%" -m pip install -q mysql-connector-python streamlit pandas numpy plotly

cd /d "%SCRIPT_DIR%src\app"
echo.
"%PYTHON%" main.py
pause
