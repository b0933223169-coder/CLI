# 第三方元件聲明 / Third-party notices

本專案的原始碼與下列第三方元件一起發行。各元件的版權與授權屬於原作者，以下僅列出來源與授權類型。

| 元件 | 用途 | 授權 | 位置 |
| --- | --- | --- | --- |
| [xterm.js](https://github.com/xtermjs/xterm.js) 與其附加元件（fit / web-links / webgl） | 內嵌終端機的畫面 | MIT — Copyright (c) 2014 The xterm.js authors；部分程式碼 Copyright (c) 2012-2013 Christopher Jeffrey（MIT） | `xterm/` |
| Windows Terminal 的 `conpty.dll`、`OpenConsole.exe`（版本 1.24.2607.10001） | 偽終端機（ConPTY） | MIT — Copyright (c) Microsoft Corporation，來源 [microsoft/terminal](https://github.com/microsoft/terminal) | `conpty/` |
| [Material Symbols Rounded](https://fonts.google.com/icons) | 介面圖示字型（`MaterialSymbolsRounded.ttf` 為只含用到圖示的子集，`.full.ttf` 為完整檔） | Apache License 2.0 — Copyright Google LLC | `assets/fonts/` |
| [Qt 6.9](https://www.qt.io/)（Core、Gui、Qml、Quick、QuickControls2、Network、WebChannel、WebEngine…） | 桌面程式的框架；**只出現在發行包（Release）的 DLL**，儲存庫本身不含 | LGPL v3 / GPL（動態連結）；QtWebEngine 內含 Chromium，另有 BSD 等授權 | Release 的 `app/` |
| [Playwright for Python](https://playwright.dev/python/) | `cool.py` 登入與開啟課程連結 | Apache License 2.0；**不隨本專案發行**，由使用者以 `pip install playwright` 安裝 | — |

## 取得 Qt 原始碼

Release 內的 Qt 函式庫為官方預先編譯版（動態連結，可自行替換）。原始碼與授權文字見 <https://www.qt.io/download-open-source> 與 <https://code.qt.io/>。

## 本專案自己的授權

本專案的原始碼以 [MIT License](LICENSE) 授權。上表的第三方元件不在此授權範圍內，各自維持原本的授權。
