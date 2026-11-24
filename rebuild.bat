@echo off
call "C:\VSBT\VC\Auxiliary\Build\vcvars64.bat" >nul
set PATH=C:\Users\jusaper\AppData\Local\Programs\Python\Python312\Scripts;C:\Qt\6.9.3\msvc2022_64\bin;%PATH%
cd /d "%~dp0"
if not exist build-main mkdir build-main
cd build-main
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="C:/Qt/6.9.3/msvc2022_64" > cmake.log 2>&1
if errorlevel 1 ( type cmake.log & echo CMAKE FAILED & exit /b 1 )
ninja 2>&1
if errorlevel 1 ( echo BUILD FAILED & exit /b 1 )
echo BUILD OK
