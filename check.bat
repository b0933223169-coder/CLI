@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
cls

echo.
echo ===================================================
echo             Python Auto Installer (3.14)
echo ===================================================
echo.
echo Installing Python 3.14 via winget...
echo.

winget install --id Python.Python.3.14 -e --accept-package-agreements --accept-source-agreements

set "EXIT_CODE=%errorlevel%"

if "!EXIT_CODE!" equ "0" (
    echo.
    echo ===================================================
    echo   [SUCCESS] Python 3.14 installation completed!
    echo.
    echo   Please restart your terminal to update environment.
    echo ===================================================
) else (
    echo.
    echo ===================================================
    echo   [FAILED] Error code: !EXIT_CODE!
    echo.
    echo   Please download manually from:
    echo   https://python.org
    echo ===================================================
)

echo.
endlocal
pause
