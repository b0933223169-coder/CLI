@echo off
setlocal
pushd "%~dp0desktop"
if not exist node_modules (
    echo Installing desktop app dependencies...
    call npm ci
    if errorlevel 1 (
        popd
        exit /b 1
    )
)
call npm run dev
set "exitCode=%errorlevel%"
popd
exit /b %exitCode%
