@echo off
setlocal
chcp 65001 >nul
cls

echo.
echo ===================================================
echo   Cool Desktop — 建置 Windows 安裝程式
echo ===================================================
echo.

pushd "%~dp0desktop"
if not exist node_modules (
    echo [1/2] Installing desktop app dependencies...
    call npm ci
    if errorlevel 1 (
        echo [FAILED] npm ci failed.
        popd
        pause
        exit /b 1
    )
)
echo [2/2] Building the Windows installer...
call npm run build:win
if errorlevel 1 (
    echo.
    echo [FAILED] Build failed. See the error output above.
    popd
    pause
    exit /b 1
)
popd

echo.
echo ===================================================
echo   [SUCCESS] Build complete!
echo   Installer output: desktop\dist
echo ===================================================
echo.
pause
