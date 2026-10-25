"""Help text for interactive and command-line usage."""
from __future__ import annotations
from ._compat import *
from .colors import *

# ============================== help：說明文字 ==============================
HELP_TEXT = f"""{CYAN}cool.py — coolenglish.edu.tw 終端機工具{RESET}
{DIM}可用指令列表（在 cool> 提示符下輸入）：{RESET}

  {GREEN}cool -l{RESET}, {GREEN}--login{RESET}             登入新帳號（支援密碼加密）
  {GREEN}cool -a{RESET}, {GREEN}--account{RESET}           顯示帳號狀態並開啟帳號選擇
  {GREEN}cool -g{RESET}, {GREEN}--go{RESET}                選擇一組或多組課程連結並執行
  {GREEN}cool -u{RESET}, {GREEN}--url{RESET}               新增或刪除已儲存課程連結
  {GREEN}cool -s{RESET}, {GREEN}--show{RESET}              搭配 -l 或 -g 使用有頭瀏覽器
  {GREEN}cool -t{RESET}, {GREEN}--time{RESET}             使用已儲存的 Cookie 取得學習時數（不開瀏覽器）
  {GREEN}cool -n{RESET}, {GREEN}--name{RESET}             選擇重新命名帳號或連結組
  {GREEN}cool -c{RESET}, {GREEN}--color{RESET}             自訂介面顯示顏色選單
  {GREEN}cool -v{RESET}, {GREEN}--version{RESET}            顯示目前版本
  {GREEN}cool -h{RESET}, {GREEN}--help{RESET}              顯示此說明列表
  {GREEN}sudo{RESET}                      取得超級使用者權限；可放在指令前
  {GREEN}&&{RESET}                        依序執行多個 cool 指令
  {GREEN}|{RESET}                         在 -g 選單中多選連結組

  {DIM}/clear 清空畫面  |  /passwd 設定密碼  |  /exit 離開程式{RESET}
"""

CMD_HELP = {
    "login": f"{CYAN}cool -l / cool --login{RESET}\n  登入新帳號或切換帳號，支援加密儲存密碼。\n  範例：cool -l",
    "account": f"{CYAN}cool -a / cool --account{RESET}\n  顯示所有帳號的即時 Cookie 狀態，然後開啟帳號選擇。\n  範例：cool -a",
    "go": f"{CYAN}cool -g / cool --go [-s]{RESET}\n  選擇已儲存連結組；可輸入 a|b 同時執行多組。\n  加 -s 以有頭瀏覽器執行，預設使用無頭模式。\n  範例：cool -g / cool -g -s",
    "show": f"{CYAN}cool -s / cool --show{RESET}\n  顯示 Playwright 瀏覽器；請搭配 cool -l 或 cool -g 使用。\n  範例：cool -l -s / cool -g -s",
    "url": f"{CYAN}cool -u / cool --url{RESET}\n  開啟課程連結管理選單，可新增或刪除連結。\n  刪除時輸入連結編號刪除單筆，或輸入分類名稱／分類:<名稱> 刪除整個分類。\n  分類與連結組名稱會與桌面應用程式同步。\n  新增時可輸入群組名稱；留空會依有效 Cookie 的課程頁標題自動分類，否則以 URL 中第一個數字命名。\n  範例：cool -u",
    "write": f"{CYAN}cool -u -w{RESET}\n  批量貼上多個連結，逐筆輸入群組名稱；輸入已存在名稱可歸入同組。\n  範例：cool -u -w",
    "time": f"{CYAN}cool -t / cool --time{RESET}\n  使用已儲存的 Cookie 直接取得並解析時數 HTML，不開啟 Playwright 瀏覽器。\n  範例：cool -t",
    "name": f"{CYAN}cool -n / cool --name{RESET}\n  選擇重新命名帳號或連結組。\n  範例：cool -n",
    "color": f"{CYAN}cool -c / cool --color{RESET}\n  調整報表色彩，以及與桌面設定同步的終端游標、文字、背景顏色。\n  可開選單或用 set <項目> <顏色>；色彩即時儲存。\n  範例：cool -c / cool -c set terminal_background_color #101f20",
    "passwd": f"{CYAN}/passwd{RESET}\n  設定 CLI 內部管理密碼（用於保護解密帳號密碼）。\n  範例：/passwd",
    "sudo": f"{CYAN}sudo cool <指令>{RESET}\n  取得 CLI 超級使用者權限；可放在受保護指令前使用。\n  範例：sudo cool -l",
    "clear": f"{CYAN}/clear{RESET}\n  清空目前終端機畫面。\n  範例：/clear",
    "exit": f"{CYAN}/exit / /quit / /q{RESET}\n  離開 cool.py 互動式終端機。\n  範例：/exit",
    "help": f"{CYAN}cool -h / cool --help{RESET}\n  顯示說明清單。\n  範例：cool -h",
}


__all__ = [name for name in globals() if not name.startswith("__")]
