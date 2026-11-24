@echo off
call "C:\VSBT\VC\Auxiliary\Build\vcvars64.bat"
set QMAKE_MSC_VER=1944
echo QMAKE_MSC_VER=%QMAKE_MSC_VER%
set PATH=C:\Qt\6.9.3\msvc2022_64\bin;%PATH%
cd /d C:\Users\jusaper\Downloads\coolqml-rs
del /Q Makefile Makefile.Debug Makefile.Release 2>nul
C:\Qt\6.9.3\msvc2022_64\bin\qmake.exe -set QMAKE_MSC_VER 1944
C:\Qt\6.9.3\msvc2022_64\bin\qmake.exe we_test.pro -spec win32-msvc "CONFIG+=release"
if errorlevel 1 goto fail
nmake
if errorlevel 1 goto fail
echo BUILD OK
exit /b 0
:fail
echo BUILD FAILED
exit /b 1
