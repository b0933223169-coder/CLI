@echo off
call "C:\VSBT\VC\Auxiliary\Build\vcvars64.bat"
set PATH=C:\Users\jusaper\AppData\Local\Programs\Python\Python312\Scripts;C:\Qt\6.9.3\msvc2022_64\bin;%PATH%
cd /d "%~dp0"
if exist build-main rmdir /S /Q build-main
mkdir build-main
cd build-main
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="C:/Qt/6.9.3/msvc2022_64"
if errorlevel 1 goto fail
ninja
if errorlevel 1 goto fail
echo BUILD OK
cd /d "%~dp0"
call deploy_main.bat
exit /b 0
:fail
echo BUILD FAILED
exit /b 1
