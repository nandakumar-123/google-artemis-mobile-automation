@echo off
setlocal
echo ===================================================
echo STOPPING ANDROID AI ASSISTANT SERVER (Port 8000)
echo ===================================================

set FOUND=0
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr /r ":8000[ ]" ^| findstr LISTENING') do (
    set FOUND=1
    echo Found process listening on port 8000 with PID: %%a
    echo Terminating PID: %%a ...
    taskkill /F /PID %%a
)

if "%FOUND%"=="0" (
    echo [OK] No process is currently listening on port 8000.
) else (
    echo [OK] Server process terminated.
)
pause
