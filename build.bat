@echo off
REM 用 MinGW 版 Qt 編譯 coolqml host（完全不依賴 Python / Visual Studio）
set QT_DIR=C:\Qt\6.9.3\mingw_64
set MINGW_DIR=C:\Qt\Tools\mingw1310_64
set PATH=%QT_DIR%\bin;%MINGW_DIR%\bin;%PATH%

cd /d C:\Users\jusaper\Downloads\coolqml-rs

echo === qmake ===
%QT_DIR%\bin\qmake.exe coolqml.pro -spec win32-g++ "CONFIG+=release"
if errorlevel 1 goto fail

echo === make ===
%MINGW_DIR%\bin\mingw32-make.exe -j4
if errorlevel 1 goto fail

echo === 完成 ===
dir release\coolqml.exe
goto end

:fail
echo 編譯失敗
exit /b 1
:end
