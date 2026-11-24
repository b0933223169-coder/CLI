@echo off
call "C:\VSBT\VC\Auxiliary\Build\vcvars64.bat"
set PATH=C:\Qt\6.9.3\msvc2022_64\bin;%PATH%
cd /d "%~dp0"
C:\Qt\6.9.3\msvc2022_64\bin\windeployqt.exe --no-translations --qmldir "%~dp0qml" build-main\coolqml.exe
echo --- ensure WebEngine resources ---
if not exist build-main\resources mkdir build-main\resources
copy /Y "C:\Qt\6.9.3\msvc2022_64\resources\qtwebengine_resources.pak" build-main\resources\ >nul
copy /Y "C:\Qt\6.9.3\msvc2022_64\resources\qtwebengine_resources_100p.pak" build-main\resources\ >nul
copy /Y "C:\Qt\6.9.3\msvc2022_64\resources\qtwebengine_resources_200p.pak" build-main\resources\ >nul
copy /Y "C:\Qt\6.9.3\msvc2022_64\resources\qtwebengine_devtools_resources.pak" build-main\resources\ >nul
copy /Y "C:\Qt\6.9.3\msvc2022_64\resources\icudtl.dat" build-main\resources\ >nul
copy /Y "C:\Qt\6.9.3\msvc2022_64\resources\v8_context_snapshot.bin" build-main\resources\ >nul
echo --- copy conpty runtime ---
if not exist build-main\conpty mkdir build-main\conpty
copy /Y conpty\conpty.dll build-main\conpty\conpty.dll
copy /Y conpty\OpenConsole.exe build-main\conpty\OpenConsole.exe
echo DEPLOY DONE
