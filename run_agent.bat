@echo off
title Knowledge Review Agent
echo Starting Knowledge Review Agent...

:: Change to the script's directory
cd /d "%~dp0"

:: Check if streamlit is installed
where streamlit >nul 2>nul
if %errorlevel% neq 0 (
    echo Streamlit not found in PATH.
    echo Please ensure you have installed the requirements: pip install -r requirements.txt
    pause
    exit /b
)

:: Run the app
echo Launching Streamlit...
streamlit run app.py

if %errorlevel% neq 0 (
    echo.
    echo An error occurred. Press any key to exit.
    pause >nul
)
