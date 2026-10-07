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

where mysqldump >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: mysqldump not found in PATH. Database backup will fail.
    echo Add MySQL bin directory to PATH.
    pause
)

if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    %SYS_PYTHON% -m venv "%VENV_DIR%"
)

set PYTHON=%VENV_DIR%\Scripts\python.exe

echo Installing dependencies...
"%PYTHON%" -m pip install -q mysql-connector-python rapidfuzz pandas openpyxl

cd /d "%SCRIPT_DIR%src\setup"
echo.
"%PYTHON%" main.py
pause
