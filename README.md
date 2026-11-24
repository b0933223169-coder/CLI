# Cool Desktop（Qt / QML 原生版）

以 **C++ + Qt Quick** 重寫的 Cool English 桌面工作台，功能對齊 `CLI-main`（Electron + Python）專案，
但不需要 Node/Electron，也不再需要 Python 來驅動 UI、登入、報表或瀏覽器；閒置記憶體約 **200 MB**（原 Electron 版通常 > 400 MB）。
Python 只剩「內嵌終端裡執行的 `cool.py` CLI」（隨附於 `cli/`），桌面程式本身零 Python 相依。

## 功能（與 CLI-main 桌面版對照）

| 功能 | 實作 |
| --- | --- |
| Google OAuth 登入（有頭／無頭） | `browser.cpp`：直接用 Chrome DevTools Protocol 驅動系統 Edge/Chrome（找不到時用 Playwright 的 Chromium）。只點 `oauth2/login.php?id=2`，依序處理帳號／密碼，監看 `accounts.google.com(.tw)` 與跨頁導向；遇 reCAPTCHA／MFA／通行密鑰時無頭會帶 Cookie 切到可見瀏覽器等使用者完成；以 MoodleSession + 渲染頁面 + `/my/` 驗證成功後才保存，逾時（無頭 60 秒／有頭 15 分鐘）會回報最近診斷 |
| Cookie／密碼保存 | Windows DPAPI（`native.cpp`）；`cookies/*.txt` 為 `#COOL_ENCRYPTED_V1`；密碼在 `credentials.json` |
| 學習報表 | 不開瀏覽器，用已保存 Cookie 直接 HTTP 取得時數頁並解析表格，記為「直接請求」工作階段；明確導向登入才標為過期，暫時性錯誤標為待檢查 |
| Cookie 有效性檢查 | 同上，直接請求 |
| 開啟課程（有頭／無頭／整個連結組） | 同一批次記為單一工作階段；無頭持續執行，可在「網路紀錄 › 正在運行」終止；停用紀錄時逐筆顯示 `[ OK ]／[ WARN ]` 即時進度 |
| 網路紀錄 | 以 CDP 記錄 request／response／failed（URL 與 Header 已遮蔽）；每個工作階段是獨立 JSONL（不整份載入記憶體）；永久保留／自動刪除／停用；可選記錄原始本文；多選刪除、匯出含本文的單一 JSON、排版檢視／原始 JSONL |
| 帳號與 CLI 雙向同步 | 帳號、Cookie、密碼（CLI 的 XOR 格式自動轉 DPAPI）、`colors.json` 雙向；課程直接共用 `urls.txt`（`# group:` / `# category:`）；檔案監看即時反映 |
| 課程別名／分類 | 別名跟隨分類、舊資料自動校正；CLI 新增／改名／刪除即時同步 |
| 內嵌終端 | ConPTY + xterm.js；PowerShell／命令提示字元／Visual Studio 開發者 shell／Git Bash／WSL；每個終端從 `cli/` 執行 `python cool.py`；右鍵選單、Ctrl+Shift+C/V；輸入 `/exit` 關閉整個工作臺；終端色與字級同步設定 |
| 外觀 | 24 組高辨識主題（暖／冷／自然／鮮明，介面背景與卡片色各不相同）、介面字體、反轉文字色、字級、圓角、動態 |
| 設定 | 7 個分類可雙擊排序；CLI 報表七色（37 種預設樣式 + 自訂 HEX，與 `cool -c` 即時同步） |
| 其他 | 每日輪換問候語、側邊欄點擊／懸停模式、閒置自動鎖定、匯出（CSV/JSON/TXT） |

## 建置

需求：Windows、Qt 6.9.3 (MSVC 2022 64-bit)、VS Build Tools、CMake + Ninja。

```powershell
.\rebuild.bat        # 增量編譯（build-main\coolqml.exe）
.\deploy_main.bat    # windeployqt + WebEngine 資源 + ConPTY
```

`build_main.bat` 會清掉 `build-main` 後完整重建。

## 開發小工具

- `cooltest.exe native|open <url> [headed|headless]|login|seedcli <dir>`：不含 UI 的原生模組自我測試
- `shots.ps1`：以隔離資料夾啟動並截圖各頁（不碰真實資料）
- `tools_subset_font.py`：把 15 MB 的 Material Symbols 縮成只含用到的圖示（`MaterialSymbolsRounded.full.ttf` 是完整備份；新增圖示後重跑）

## 資料位置

- 桌面資料：`%APPDATA%\cool`（可用 `COOL_DATA_DIR` 覆寫）
- CLI 目錄：`<專案>\cli`（可用 `COOL_CLI_DIR` 覆寫）；請勿把 `accounts.json`、`cookies/`、`colors.json`、`urls.txt` 上傳到版本控制
- 瀏覽器：優先 Edge，其次 Chrome，最後 Playwright 的 Chromium；可用 `COOL_BROWSER` 指定

舊的 `fetch_report.py`、`check_cookie.py` 等輔助腳本已不再被程式使用。
