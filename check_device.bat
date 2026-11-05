@echo off
setlocal
echo ===================================================
echo CHECKING ANDROID DEVICE CONNECTION
echo ===================================================

set ADB_CMD=platform-tools\adb.exe
if not exist "%ADB_CMD%" (
    set ADB_CMD=adb
)

echo [ADB Version]
"%ADB_CMD%" version
echo.

echo [Connected Devices]
"%ADB_CMD%" devices
echo.

echo [Device Model]
"%ADB_CMD%" shell getprop ro.product.model
echo.

echo ===================================================
echo If no device is listed:
echo 1. Connect your phone using a USB data cable.
echo 2. Go to Settings - About Phone - Tap Build Number 7 times.
echo 3. Open Developer Options - Enable 'USB Debugging'.
echo 4. Unlock your phone and tap 'Allow USB debugging' when prompted.
echo ===================================================
pause

