@echo off
chcp 65001 >nul
cls

echo.
echo ===================================================
echo             Python Auto Installer (3.14)
echo ===================================================
echo.
echo 正在透過 winget 安裝 Python 3.14...
echo.

winget install --id Python.Python.3.14 -e --accept-package-agreements --accept-source-agreements

if %errorlevel% equ 0 (
    echo.
    echo ===================================================
    echo   [成功] Python 3.14 安裝完成！
    echo.
    echo   提示: 請關閉並重新開啟終端機視窗以更新環境變數，
    echo   即可正常使用 python 與 cool.py。
    echo ===================================================
) else (
    echo.
    echo ===================================================
    echo   [失敗] 安裝過程出現問題，錯誤代碼: %errorlevel%
    echo.
    echo   請確認網路連線，或手動前往以下網址下載：
    echo   https://www.python.org/
    echo ===================================================
)

echo.
pause
