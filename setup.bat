@echo off
setlocal
echo ===================================================
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH. Please install Python 3.12+ from python.org.
    pause
    exit /b 1
)
python --version

echo ===================================================
echo [2/5] Checking Android Platform Tools (ADB)...
if exist "platform-tools\adb.exe" (
    echo [OK] Local platform-tools/adb.exe found.
) else (
    adb version >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [INFO] Extracting platform-tools-latest-windows.zip...
        tar -xf platform-tools-latest-windows.zip
    )
)

echo ===================================================
echo [3/5] Setting up Python Virtual Environment (.venv)...
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
) else (
    echo [OK] Virtual environment already exists.
)

echo ===================================================
echo [4/5] Installing dependencies from requirements.txt...
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo ===================================================
echo [5/5] Creating data directories and .env...
if not exist "data\screenshots" mkdir "data\screenshots"
if not exist "data\history" mkdir "data\history"
if not exist "logs" mkdir "logs"

if not exist ".env" (
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [INFO] Created .env from .env.example.
    )
) else (
    echo [OK] .env already exists.
)

echo ===================================================
echo SETUP COMPLETED SUCCESSFULLY!
echo Remember to configure your GEMINI_API_KEY in the .env file.
echo You can now run run.bat or check_device.bat.
pause

