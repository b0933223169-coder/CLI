"""Help text for interactive and command-line usage."""
from __future__ import annotations
from ._compat import *
from .colors import *

# ============================== help：說明文字 ==============================
HELP_TEXT = f"""{CYAN}cool.py — coolenglish.edu.tw 終端機工具{RESET}
{DIM}可用指令列表（在 cool> 提示符下輸入）：{RESET}

  {GREEN}cool -l{RESET}, {GREEN}--login{RESET}             登入新帳號（支援密碼加密）
  {GREEN}cool -a{RESET}, {GREEN}--account{RESET}           顯示帳號狀態並開啟帳號選擇
  {GREEN}cool -A{RESET}, {GREEN}--ALL{RESET}               顯示所有帳號完整資料
  {GREEN}cool -u -s{RESET}, {GREEN}--show{RESET}            顯示課程 Playwright 瀏覽器
  {GREEN}cool -l -s{RESET}                                顯示登入 Playwright 瀏覽器
  {GREEN}cool -u{RESET}, {GREEN}--url{RESET}               載入已儲存課程網址（支援選取/刪除）
  {GREEN}cool -t{RESET}, {GREEN}--time{RESET}             查詢學習時數報表（開啟帳號選單）
  {GREEN}cool -n{RESET}, {GREEN}--name{RESET}             重新命名帳號（開啟帳號選單）
  {GREEN}cool -d{RESET}, {GREEN}--delete{RESET}          刪除指定帳號（開啟帳號選單）
  {GREEN}cool -c{RESET}, {GREEN}--color{RESET}             自訂介面顯示顏色選單
  {GREEN}cool -v{RESET}, {GREEN}--version{RESET}            顯示目前版本
  {GREEN}cool -h{RESET}, {GREEN}--help{RESET}              顯示此說明列表
  {GREEN}sudo{RESET}                      解鎖 sudo 權限以檢視密碼明文

  {DIM}/clear 清空畫面  |  /passwd 設定密碼  |  /exit 離開程式{RESET}
"""

CMD_HELP = {
    "login": f"{CYAN}cool -l / cool --login{RESET}\n  登入新帳號或切換帳號，支援加密儲存密碼。\n  範例：cool -l",
    "account": f"{CYAN}cool -a / cool --account{RESET}\n  顯示所有帳號的即時 Cookie 狀態，然後開啟帳號選擇。\n  範例：cool -a",
    "show": f"{CYAN}cool -A / cool --ALL{RESET}\n  顯示所有帳號完整資料。\n  Playwright 顯示旗標：cool -u -s、cool -l -s。",
    "url": f"{CYAN}cool -u / cool --url [-w] [-s]{RESET}\n  課程網址管理；清單中的 Delete / d 鍵會先跳出 [y/N] 確認對話框。\n    • cool -u -s ➡️ 顯示 Playwright 瀏覽器\n    • cool -u -w ➡️ 批量貼上並排版儲存新網址\n  範例：cool -u / cool -u -s / cool -u -w",
    "write": f"{CYAN}cool -u -w / cool -w{RESET}\n  批量寫入/貼上多個課程網址，自動去除重複與排版儲存。\n  範例：cool -u -w / cool -w",
    "time": f"{CYAN}cool -t / cool --time{RESET}\n  開啟帳號選單並顯示所選帳號的時數報表。\n  範例：cool -t",
    "name": f"{CYAN}cool -n / cool --name{RESET}\n  開啟帳號選單並重新命名所選帳號。\n  範例：cool -n",
    "delete": f"{CYAN}cool -d / cool --delete{RESET}\n  開啟帳號選單並刪除所選帳號與對應 Cookie 檔案。\n  範例：cool -d",
    "color": f"{CYAN}cool -c / cool --color{RESET}\n  自訂終端顏色，可開選單或用 set <項目> <顏色>。\n  範例：cool -c / cool -c set title #ff00aa",
    "passwd": f"{CYAN}/passwd{RESET}\n  設定 CLI 內部管理密碼（用於保護解密帳號密碼）。\n  範例：/passwd",
    "sudo": f"{CYAN}sudo / sudo cool -s{RESET}\n  取得管理權限，解鎖密碼明文顯示。\n  範例：sudo",
    "clear": f"{CYAN}/clear{RESET}\n  清空目前終端機畫面。\n  範例：/clear",
    "exit": f"{CYAN}/exit / /quit / /q{RESET}\n  離開 cool.py 互動式終端機。\n  範例：/exit",
    "help": f"{CYAN}cool -h / cool --help{RESET}\n  顯示說明清單。\n  範例：cool -h",
}


__all__ = [name for name in globals() if not name.startswith("__")]
