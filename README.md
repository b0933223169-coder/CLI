# Cool Desktop（Qt / QML）+ cool.py

> **這個儲存庫在 2026-11 整個換成了 Qt 版本。** 先前的 Python CLI + Electron 桌面版只存在於 git 歷史
> （最後一個舊版提交：`803c881`），**目前的檔案全部都是新專案，與舊版無關。**

Windows 桌面工作台，用來管理 [coolenglish.edu.tw](https://coolenglish.edu.tw) 的帳號、課程連結與學習時數。
由兩個部分組成，**桌面程式是 `cool.py` 的殼**：登入、報表、開課程、Cookie 都是呼叫 `cli/` 裡的 CLI 完成，不另外重寫邏輯。

| 部分 | 技術 | 位置 |
| --- | --- | --- |
| 桌面程式 | C++17、Qt 6.9（Qt Quick / QML、QtWebEngine）、MSVC 2022 | 根目錄 `*.cpp`、`qml/`、`xterm/` |
| 命令列工具 `cool.py` | Python 3、Playwright | `cli/` |

只支援 Windows（使用 ConPTY 與 DPAPI）。

## 桌面程式

- **頁面：** 工作台、帳號、課程、報表、網路紀錄、設定（`qml/pages/`）。
- **帳號：** 呼叫 `cool.py -l` 登入；帳號、Cookie、頭像與 CLI 雙向同步（`accounts.json`、`cookies/`、`avatars/`）。
- **報表：** 呼叫 `cool.py -t --raw` 取得學習時數，不開瀏覽器。
- **課程：** 連結組存在 `urls.txt`，與 CLI 雙向同步；開啟時呼叫 `cool.py -g`，可設定自動關閉與延遲開始。
- **內嵌終端機：** xterm.js（`xterm/`）透過 QWebChannel 連到 Windows ConPTY（`conpty.cpp`、`qml_pty_bridge.cpp`），
  支援多分頁、歷史重播、下方或右側停靠。附帶的 `conpty/conpty.dll` 與 `OpenConsole.exe` 來自 Windows Terminal（MIT）。
- **網路紀錄：** 把 CLI 執行時輸出的事件（`@@COOL_PLAYWRIGHT_LOG@@`）整理成工作階段，可看排版、原始 JSONL 與 CLI 畫面。
- **主題：** `color_engine.cpp` 以 OKLCH 產生色盤並檢查對比，24 組預設主題。
- **安全：** 密碼與 Cookie 使用 Windows DPAPI 加密保存（`native.cpp`）。

資料放在 `%APPDATA%\cool`（設定 `COOL_DATA_DIR` 可改）；`cool.py` 來源預設是 `cli/`（設定 `COOL_CLI_DIR` 可改）。

### 原始碼導覽

| 檔案 | 內容 |
| --- | --- |
| `main.cpp` | 程式進入點、QML 引擎、測試用環境變數 |
| `backend.h` / `backend.cpp` | 暴露給 QML 的 `Backend`（設定、主題、終端機分頁與偵測） |
| `backend_native.inc` | 帳號、憑證、工作階段與 JSONL、與 CLI 的檔案同步 |
| `backend_cli.inc` | 啟動 `cool.py` 子程序、解析輸出、自動回答提示 |
| `native.*` | DPAPI 加解密、Cookie 讀寫 |
| `color_engine.*` | OKLCH 色彩引擎 |
| `conpty.*`、`qml_pty_bridge.*` | ConPTY 包裝與 QML 橋接 |
| `qml/` | 介面（`Main.qml`、`pages/`、`components/`） |

### 建置

需要 Qt 6.9.3（MSVC 2022 64 位元）、Visual Studio Build Tools、Ninja、Python 3。

```bat
rebuild.bat          :: CMake + Ninja 建置到 build-main\
deploy_main.bat      :: windeployqt，並複製 WebEngine 資源與 conpty
build-main\coolqml.exe
```

`rebuild.bat` 內的 Qt 與 VS 路徑（`C:\Qt\6.9.3\...`、`C:\VSBT\...`）是寫死的，換機器要自行修改。
QML 與 `cli/` 是從磁碟載入，改了不必重新編譯。

## cool.py（`cli/`）

```bat
python cli\cool.py              :: 互動式 cool>
python cli\cool.py -g a         :: 單行執行
```

| 指令 | 說明 |
| --- | --- |
| `cool -l` | 登入帳號（Playwright） |
| `cool -a` / `cool -A` | 帳號狀態與選擇／完整帳號清單 |
| `cool -g` | 開啟課程連結組 |
| `cool -u`（`-u -w`） | 新增／刪除連結（批量貼上） |
| `cool -t` | 學習時數報表 |
| `cool -n` | 重新命名帳號／連結組 |
| `cool -c` | 自訂顏色（互動式調色） |
| `cool -h` | 說明；**任何指令後加 `-h` 都有詳細說明** |

**指令修飾符**用 `>` 附加給前面的指令，一次指令分三個階段：

```
① 開始前   /delay T   /at 時:分
② 執行中   /timer T（別名 /for）
③ 結束後   /clear   /exit        其他：/show（有頭瀏覽器）  /repeat N
```

```
cool -g a|b > /delay 10:00 /timer 1:00:00 /exit     10 分鐘後開、開 1 小時、關閉後離開
-h > (/show | /delay | /at | /repeat)               括號：一次對多個項目
cool -t && (cool -c | cool -a)                      && | ; 串接與括號分組
```

`cli/` 的程式分層：`lineedit.py`（輸入）→ `repl.py`（切行、括號展開、串接）→ `dispatch.py`（指令分派）→
`modifiers.py`（修飾符解析）→ `runner.py`（等待、重複、時限）→ `commands/`（各指令本體）。

## 開發小工具

| 檔案 | 用途 |
| --- | --- |
| `tools_subset_font.py` | 把 Material Symbols 字型縮成只含專案用到的圖示 |
| `fetch_xterm.py` | 下載 xterm.js 資源 |
| `shots.ps1`、`auditcli.ps1` | 截圖與 CLI 檢查 |
| `COOL_STALL_LOG=1` | 記錄介面卡頓與畫面更新率 |

個人資料（帳號、Cookie、頭像、課程網址）不會被提交，見 `.gitignore`。
