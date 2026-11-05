@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo STARTING ANDROID AI ASSISTANT
echo ===================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo [WARNING] .env file not found. Copying from .env.example...
    copy .env.example .env >nul
)

findstr /C:"GEMINI_API_KEY=YOUR_GEMINI_API_KEY" .env >nul
if %ERRORLEVEL% EQU 0 (
    echo [NOTE] GEMINI_API_KEY is not configured yet in .env.
    echo The assistant will run using local rule-based planning for standard tasks.
    echo To enable full Gemini AI, enter your API key in .env.
    echo.
)

:: Check if port 8000 is already in use
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr /r ":8000[ ]" ^| findstr LISTENING') do (
    echo [INFO] Port 8000 is already in use by Process ID %%a.
    echo The FastAPI server appears to already be running.
    echo Opening browser at http://127.0.0.1:8000 ...
    start "" "http://127.0.0.1:8000"
    echo.
    echo If you need to restart the server with new code changes:
    echo Run stop.bat first to close the running instance, then run run.bat again.
    pause
    exit /b 0
)

echo Starting FastAPI server at http://127.0.0.1:8000 ...
start "" "http://127.0.0.1:8000"

.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
