@echo off
call "C:\VSBT\VC\Auxiliary\Build\vcvars64.bat"
set PATH=C:\Qt\6.9.3\msvc2022_64\bin;%PATH%
cd /d C:\Users\jusaper\Downloads\coolqml-rs
C:\Qt\6.9.3\msvc2022_64\bin\windeployqt.exe --no-translations build\we_test.exe
echo done
