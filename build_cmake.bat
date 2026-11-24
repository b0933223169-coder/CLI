@echo off
call "C:\VSBT\VC\Auxiliary\Build\vcvars64.bat"
set PATH=C:\Users\jusaper\AppData\Local\Programs\Python\Python312\Scripts;C:\Qt\6.9.3\msvc2022_64\bin;%PATH%
cd /d C:\Users\jusaper\Downloads\coolqml-rs
if exist build rmdir /S /Q build
mkdir build
cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="C:/Qt/6.9.3/msvc2022_64"
if errorlevel 1 goto fail
ninja
if errorlevel 1 goto fail
echo BUILD OK
exit /b 0
:fail
echo BUILD FAILED
exit /b 1
