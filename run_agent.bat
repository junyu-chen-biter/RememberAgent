@echo off
title Knowledge Review Agent
echo Starting Knowledge Review Agent...

REM Change to the script's directory
cd /d "%~dp0"

set "CONDA_ENV_NAME=langchain-env"

REM Ensure conda exists
where conda >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: conda command not found in PATH.
    echo Please run this script from "Anaconda Prompt", or add conda to PATH.
    echo Manual command:
    echo   conda run -n %CONDA_ENV_NAME% python -m streamlit run app.py
    echo.
    pause
    exit /b 1
)

echo Launching Streamlit in conda env: %CONDA_ENV_NAME% ...
conda run -n %CONDA_ENV_NAME% python -m streamlit run app.py

if %errorlevel% neq 0 (
    echo.
    echo An error occurred. Press any key to exit.
    pause >nul
)

