"""Help text for interactive and command-line usage.

HELP_TEXT   = cool -h 的簡短介紹（只列指令，不寫細節）
CMD_HELP    = 在任何指令後加 -h 看到的詳細說明；每一段固定是：用法 / 說明 / 運作方式 / 選項 / 範例 / 相關
              鍵名對照見 dispatch.py 的 help_key_for()（指令、slash 指令、修飾符都各有一段）
"""
from __future__ import annotations
from ._compat import *
from .colors import *

# ============================== help：簡短介紹 ==============================
HELP_TEXT = f"""{CYAN}cool.py — coolenglish.edu.tw 終端機工具{RESET}
{DIM}可用指令列表（在 cool> 提示符下輸入）：{RESET}

  {GREEN}cool -l{RESET}, {GREEN}--login{RESET}     登入帳號
  {GREEN}cool -a{RESET}, {GREEN}--account{RESET}   帳號狀態與選擇
  {GREEN}cool -g{RESET}, {GREEN}--go{RESET}        開啟課程連結組
  {GREEN}cool -u{RESET}, {GREEN}--url{RESET}       新增／刪除課程連結
  {GREEN}cool -t{RESET}, {GREEN}--time{RESET}      取得學習時數
  {GREEN}cool -n{RESET}, {GREEN}--name{RESET}      重新命名帳號／連結組
  {GREEN}cool -c{RESET}, {GREEN}--color{RESET}     自訂顏色
  {GREEN}cool -v{RESET}, {GREEN}--version{RESET}   顯示版本
  {GREEN}cool -h{RESET}, {GREEN}--help{RESET}      顯示說明
  {GREEN}sudo{RESET}                   取得管理權限，可放在指令前
  {GREEN}>{RESET}                      附加設定給前面的指令：/show /timer /delay /at /repeat /clear /exit
  {GREEN}( ){RESET}                    括號群組：一次對多個東西附值，例：-h > (/show | /at)
  {GREEN}&&{RESET}                     依序執行，前一個失敗就停止
  {GREEN}|{RESET}                      依序執行，不論成敗

  {DIM}在任何指令後加 -h 看詳細說明（含 /clear、/exit、/timer 等 slash 指令），例：cool -g -h、/clear -h{RESET}
  {DIM}例：cool -g > /timer 1:30:00（90 分鐘後自動關閉）  cool -c > /timer 30（最多開 30 秒）{RESET}
  {DIM}/clear 清空畫面  |  /passwd 設定密碼  |  /exit 離開程式{RESET}
"""

CMD_HELP = {
    # ───────────────────────── 指令 ─────────────────────────
    "login": f"""{CYAN}cool -l / cool --login{RESET}  登入帳號
{YELLOW}用法{RESET}
  cool -l [> /show]
{YELLOW}說明{RESET}
  用 Playwright 瀏覽器登入 Cool English（Google 帳號），把登入後的 Cookie 存起來，
  之後 cool -t（查時數）、cool -g（開課程連結）都靠這份 Cookie，不必每次輸入密碼。
{YELLOW}運作方式{RESET}
  1. 已有帳號時先選「重新登入哪個帳號」或「輸入新帳號」（Esc / 直接 Enter 返回）。
  2. 新帳號要輸入 Email、密碼、顯示名稱（名稱留空使用預設）。同一個 Email 會更新 Cookie，不會重複新增。
  3. 預設在背景（無頭）自動填寫登入；遇到雙重驗證、帳號選擇或要補填資料的頁面，
     會自動改成顯示瀏覽器視窗，讓你自己完成後程式再繼續。
  4. 成功後儲存 Cookie，並抓取該帳號的 Google 頭像（沒有自訂照片也會存預設圖），給桌面程式顯示。
  5. 密碼可加密保存；之後 sudo cool -l 重新登入時會自動帶入，不必再輸入。
{YELLOW}選項（接在 > 之後）{RESET}
  /show        一開始就顯示瀏覽器視窗（取代舊的 -s）
  /timer T     登入超過時間就中止      /delay T、/at 時:分  延後開始      /repeat N  重複
{YELLOW}範例{RESET}
  {GREEN}cool -l{RESET}                      背景登入
  {GREEN}cool -l > /show{RESET}              看得到瀏覽器的登入
  {GREEN}sudo cool -l{RESET}                 重新登入並自動帶入已儲存的密碼
{YELLOW}相關{RESET}  cool -a 看帳號與 Cookie 狀態｜cool -A 完整帳號清單｜cool -n 改帳號名稱｜cool passwd 設定 sudo 密碼""",

    "account": f"""{CYAN}cool -a / cool --account{RESET}  帳號狀態與選擇
{YELLOW}用法{RESET}
  cool -a
{YELLOW}說明{RESET}
  檢查所有已儲存帳號的 Cookie 是否還有效，再用上下鍵選一個帳號切換／檢視。
{YELLOW}運作方式{RESET}
  1. 逐一向網站確認每個帳號的 Cookie 狀態（有效／過期／缺少檔案）。
  2. 顯示帳號列表；↑↓ 移動、Enter 選擇、Esc 離開。
  3. 選定後顯示該帳號的名稱、Email 與 Cookie 檔案位置，並成為目前使用的帳號。
{YELLOW}注意{RESET}
  cool -a 不接受額外參數。Cookie 過期請用 cool -l 重新登入。
{YELLOW}範例{RESET}
  {GREEN}cool -a{RESET}
  {GREEN}cool -a > /timer 30{RESET}          選單最多停 30 秒，沒操作就自動離開
{YELLOW}相關{RESET}  cool -l 登入／重新登入｜cool -A 不經選單直接列出全部帳號｜cool -n 改名""",

    "go": f"""{CYAN}cool -g / cool --go{RESET}  開啟課程連結組
{YELLOW}用法{RESET}
  cool -g [選擇] [> /show] [/delay T] [/timer T] [/exit]
{YELLOW}說明{RESET}
  把 cool -u 存好的連結組，用你登入過的 Cookie 一次全部開啟（預設無頭瀏覽器，不跳出視窗）。
{YELLOW}運作方式{RESET}
  1. 列出連結組：a. [分類] 名稱 (N 個連結)、b. … 。
  2. 選擇：a|b（也可 a,b 或 a b）同時開多組；all 全部；留空 Enter 取消。
     寫在指令後面可省略詢問：cool -g a|b
  3. 有多個帳號時選要用哪個帳號的 Cookie；Cookie 失效的連結會被略過並提示。
  4. 逐一開啟連結，顯示每個頁面標題。全部開完後等你按 Enter 結束（或等 /timer 時間到）。
{YELLOW}選項（接在 > 之後）{RESET}
  /show        顯示瀏覽器視窗（預設背景無頭）
  /timer T     瀏覽器開啟 T 之後自動關閉，不必手動關；倒數中按 Enter 可提前結束
  /delay T     等 T 之後才開始      /at 21:30  到指定時刻才開始      /repeat N  連續執行 N 次
  /exit        結束後離開 cool      /clear  結束後清畫面
{YELLOW}範例{RESET}
  {GREEN}cool -g{RESET}                       互動選擇連結組
  {GREEN}cool -g a|b > /timer 1:30:00{RESET}  開 a、b 兩組，90 分鐘後自動關閉
  {GREEN}cool -g all > /show{RESET}           全部連結組，顯示瀏覽器
  {GREEN}cool -g a > /at 21:30 /timer 1:00:00 /exit{RESET}   9:30 開始、開 1 小時、關閉後離開 cool
{YELLOW}相關{RESET}  cool -u 新增／刪除連結｜cool -n 重新命名連結組｜cool -h /timer 計時細節""",

    "url": f"""{CYAN}cool -u / cool --url{RESET}  新增／刪除課程連結
{YELLOW}用法{RESET}
  cool -u            開啟選單
  cool -u -w         批量貼上（見 cool -u -w -h）
{YELLOW}說明{RESET}
  管理 cool -g 要開啟的課程連結。連結存在 urls.txt，用「# group: 名稱」分組，
  與桌面程式的「課程」頁雙向同步。
{YELLOW}運作方式{RESET}
  選單用 ↑↓ 選擇：
  1. 新增連結：可一次貼上多個連結（含雜訊文字也行，會自動抓出 http/https 網址）。
     網址已存在會提醒並拒絕加入；輸入群組名稱可歸入同組，留空則依有效 Cookie 的課程頁標題自動分類，
     否則以網址中第一個數字命名。
  2. 刪除：先選分類（可多選，空白鍵勾選），Tab 進入分類後可再刪單一連結。
{YELLOW}注意{RESET}
  cool -u 不接受網址參數，請從選單操作。
{YELLOW}範例{RESET}
  {GREEN}cool -u{RESET}
  {GREEN}cool -u -w{RESET}                   批量貼上多個連結
{YELLOW}相關{RESET}  cool -g 開啟連結組｜cool -n 重新命名連結組｜cool -A 列出全部連結組""",

    "write": f"""{CYAN}cool -u -w / cool -u --write{RESET}  批量貼上課程連結
{YELLOW}用法{RESET}
  cool -u -w
{YELLOW}說明{RESET}
  一次貼上一大段文字（聊天紀錄、文件內容都可以），自動抓出所有網址並排版儲存。
{YELLOW}運作方式{RESET}
  1. 直接貼上文字，可多行、可含雜訊；完成後按兩次 Enter（或輸入空白行）送出。
  2. 程式抓出所有 http/https 網址並去除重複，已存在的連結會略過。
  3. 逐筆詢問群組名稱；輸入已存在的名稱會歸入同一組。
{YELLOW}範例{RESET}
  {GREEN}cool -u -w{RESET}
{YELLOW}相關{RESET}  cool -u 單筆新增／刪除｜cool -g 開啟連結組""",

    "time": f"""{CYAN}cool -t / cool --time{RESET}  取得學習時數
{YELLOW}用法{RESET}
  cool -t [> /timer T] [/clear]
{YELLOW}說明{RESET}
  用已儲存的 Cookie 直接向網站取得「學習時間報表」並解析成表格，不開啟瀏覽器，所以很快。
{YELLOW}運作方式{RESET}
  1. 只有一個帳號時自動使用；多個帳號會用 ↑↓ 選擇要查哪一個。
  2. 下載報表頁面並解析，列出每個月的「平台停留時間」與「影片時間」。
  3. 與門檻比較：當月已達標用反白高亮，未達標用紅底；顏色可用 cool -c 調整。
  4. 結果同時是桌面程式「報表」頁的資料來源。
{YELLOW}注意{RESET}
  cool -t 不接受帳號參數；Cookie 失效時請先 cool -l。
{YELLOW}範例{RESET}
  {GREEN}cool -t{RESET}
  {GREEN}cool -t > /timer 10 /clear{RESET}    顯示 10 秒後清畫面
  {GREEN}cool -t && cool -g a{RESET}          先查時數，成功再開連結組
{YELLOW}相關{RESET}  cool -c 調色｜cool -a 檢查 Cookie 是否過期""",

    "name": f"""{CYAN}cool -n / cool --name{RESET}  重新命名帳號／連結組
{YELLOW}用法{RESET}
  cool -n
{YELLOW}說明{RESET}
  修改帳號的顯示名稱，或連結組（分類）的名稱；名稱會與桌面程式同步。
{YELLOW}運作方式{RESET}
  1. ↑↓ 選「帳號」或「連結組」（Esc 取消）。
  2. 再選要改的是哪一個。
  3. 輸入新名稱後 Enter 套用；直接 Enter 取消。名稱重複時會提示。
{YELLOW}注意{RESET}
  cool -n 不接受額外參數。
{YELLOW}範例{RESET}
  {GREEN}cool -n{RESET}
{YELLOW}相關{RESET}  cool -l 登入｜cool -u 管理連結""",

    "color": f"""{CYAN}cool -c / cool --color{RESET}  自訂顏色
{YELLOW}用法{RESET}
  cool -c                       開啟互動調色選單
  cool -c list                  列出目前所有顏色設定
  cool -c set <項目> <顏色>     直接設定
  cool -c reset [項目…]         還原預設（不指定項目 = 全部）
{YELLOW}說明{RESET}
  調整 cool -t 報表的色彩，以及與桌面程式同步的終端機游標／文字／背景色；設定即時儲存到 colors.json。
{YELLOW}項目{RESET}
  title 標題外框｜title_text 標題文字｜header 表頭｜cur 當月已達標｜low 未達標
  url 網址列｜sep 分隔線｜terminal_cursor_color 終端游標｜terminal_text_color 終端文字｜terminal_background_color 終端背景
{YELLOW}顏色寫法{RESET}
  名稱（GREEN、CYAN、REVERSE…）、256 色編號，或 #rrggbb（背景用 bg:#rrggbb），不分大小寫。
{YELLOW}互動選單{RESET}
  ↑↓ 選項目、Enter 進入色盤；色盤 ←→↑↓ 移動、Tab 切換分類、PgUp/PgDn 翻頁、Esc 返回。
{YELLOW}範例{RESET}
  {GREEN}cool -c{RESET}
  {GREEN}cool -c set title GREEN{RESET}
  {GREEN}cool -c set terminal_background_color #101f20{RESET}
  {GREEN}cool -c reset title{RESET}
  {GREEN}cool -c > /timer 30 && /clear{RESET}   選單最多開 30 秒，然後清畫面
{YELLOW}相關{RESET}  桌面程式「設定 › CLI 報表配色」與終端機設定會雙向同步""",

    "all": f"""{CYAN}cool -A / cool --ALL{RESET}  完整帳號清單
{YELLOW}用法{RESET}
  cool -A
{YELLOW}說明{RESET}
  不經選單，一次列出所有已儲存的帳號（含 Cookie 狀態、到期資訊、Email），
  已用 sudo 取得權限時也會顯示解密後的密碼。
{YELLOW}運作方式{RESET}
  1. 標題顯示共有幾個已儲存帳號。
  2. 每個帳號一行：[編號] 名稱 ● 狀態（正常／缺少 cookie 檔）與到期資訊，下一行是 Email。
  3. 沒有帳號時提示先執行 cool -l。
{YELLOW}範例{RESET}
  {GREEN}cool -A{RESET}
  {GREEN}sudo cool -A{RESET}                  連同加密保存的密碼一起顯示
{YELLOW}相關{RESET}  cool -a 互動選擇帳號｜cool -g 開啟連結組""",

    "hidden": f"""{CYAN}cool -H{RESET}  隱藏說明
{YELLOW}用法{RESET}
  cool -H
{YELLOW}說明{RESET}
  列出不在一般說明裡的 slash 指令。
{YELLOW}內容{RESET}
  /IG          顯示製作者 IG 名稱與主頁面
  /INEEDLINK   顯示所有課程連結的收藏文件
{YELLOW}範例{RESET}
  {GREEN}cool -H{RESET}    {GREEN}/IG{RESET}    {GREEN}/INEEDLINK{RESET}
{YELLOW}相關{RESET}  /IG -h、/INEEDLINK -h 看各自說明""",

    "version": f"""{CYAN}cool -v / cool --version{RESET}  顯示版本
{YELLOW}用法{RESET}
  cool -v
{YELLOW}說明{RESET}
  印出 cool.py 的版本號碼，回報問題或確認桌面程式用的是哪一版時使用。
{YELLOW}範例{RESET}
  {GREEN}cool -v{RESET}
  {GREEN}cool -v > /timer 5{RESET}           顯示後保留 5 秒倒數
{YELLOW}相關{RESET}  桌面程式「設定 › 工作區 › cool.py 來源」會顯示實際載入的版本、更新時間與資料夾""",

    "help": f"""{CYAN}cool -h / cool --help  ·  /help{RESET}  顯示說明
{YELLOW}用法{RESET}
  cool -h                  指令列表（簡短）
  cool <指令> -h           該指令的詳細說明，例：cool -g -h
  /<指令> -h               slash 指令的詳細說明，例：/clear -h
  cool -h /timer           修飾符的詳細說明（/show /timer /delay /at /repeat /clear /exit）
{YELLOW}說明{RESET}
  -h 可以加在任何指令、slash 指令、修飾符後面；也可以寫成 --help 或 /help。
  詳細說明固定包含：用法、說明、運作方式、選項、範例、相關指令。
{YELLOW}範例{RESET}
  {GREEN}cool -h{RESET}    {GREEN}cool -l -h{RESET}    {GREEN}cool -u -w -h{RESET}    {GREEN}/passwd -h{RESET}    {GREEN}cool -h /timer{RESET}    {GREEN}cool -h > /timer 5 /clear{RESET}""",

    "passwd": f"""{CYAN}/passwd  ·  cool passwd{RESET}  設定 sudo 密碼
{YELLOW}用法{RESET}
  /passwd        （在 cool> 內）
{YELLOW}說明{RESET}
  設定 cool 自己的「管理密碼」。它用來保護儲存在本機的帳號密碼：
  只有輸入這個密碼取得 sudo 後，才能解密並自動帶入登入密碼或在 cool -A 顯示密碼。
{YELLOW}運作方式{RESET}
  1. 已設定過時先要求輸入舊密碼（直接 Enter 可跳過驗證）。
  2. 輸入新密碼、再確認一次；兩次不一致或空白會取消。
  3. 之後要用到解密時，輸入 sudo 會要求這個密碼；每一行指令結束後權限就會收回。
{YELLOW}注意{RESET}
  忘記密碼無法復原，已加密的帳號密碼需要重新登入才能再存。
{YELLOW}範例{RESET}
  {GREEN}/passwd{RESET}
  {GREEN}sudo cool -l{RESET}          設定好之後，用 sudo 重新登入會自動帶入密碼
{YELLOW}相關{RESET}  sudo -h""",

    "sudo": f"""{CYAN}sudo{RESET}  取得管理權限
{YELLOW}用法{RESET}
  sudo                      只取得權限（顯示「已取得 cool sudo 權限」）
  sudo cool <指令>          取得權限並執行該指令，例：sudo cool -l
  sudo /passwd              取得權限後執行 slash 指令
{YELLOW}說明{RESET}
  輸入 /passwd 設定的 cool 密碼後，這一行指令才能解密帳號密碼（自動帶入登入、cool -A 顯示密碼）。
{YELLOW}運作方式{RESET}
  1. 尚未設定密碼時提示先執行 /passwd。
  2. 密碼輸入時不會顯示字元；錯誤會拒絕。
  3. 權限只在這一行有效，下一行自動收回；可放在 && / | 串接的每一段前面。
{YELLOW}範例{RESET}
  {GREEN}sudo cool -l{RESET}
  {GREEN}sudo cool -A{RESET}
  {GREEN}sudo cool -t && sudo cool -g a{RESET}
{YELLOW}相關{RESET}  /passwd -h""",

    # ───────────────────────── slash 指令 ─────────────────────────
    "clear": f"""{CYAN}/clear{RESET}（別名 /cls、/c）  清空畫面
{YELLOW}用法{RESET}
  /clear                    直接清畫面
  <指令> > /clear           指令結束後清畫面（修飾符寫法）
  <指令> && /clear          前一個成功才清
{YELLOW}說明{RESET}
  只清除目前終端機的畫面，不會中斷任何程序，也不會刪掉資料。
{YELLOW}當修飾符使用{RESET}
  接在 > 後面時是「結束後」階段的動作。搭配 /timer 時，指令即使提早結束（例如 cool -h），
  畫面也會保留到時間到才清，倒數中 Ctrl+C 可取消。
  /clear 也可以單獨帶設定：/clear > /timer 5 表示 5 秒後清畫面。
{YELLOW}範例{RESET}
  {GREEN}/clear{RESET}
  {GREEN}cool -h > /timer 5 /clear{RESET}      說明顯示 5 秒後清掉
  {GREEN}cool -c > /timer 30 && /clear{RESET}
{YELLOW}相關{RESET}  cool -h /timer""",

    "exit": f"""{CYAN}/exit{RESET}（別名 /quit、/q）  離開 cool
{YELLOW}用法{RESET}
  /exit                     離開 cool>
  <指令> > /exit            指令結束後離開（修飾符寫法）
{YELLOW}說明{RESET}
  結束 cool.py 的互動模式；在桌面程式的內嵌終端機裡只是結束 cool，終端機分頁仍在。
{YELLOW}當修飾符使用{RESET}
  屬於「結束後」階段，在 /timer 等其他設定都做完之後才離開。
  `cool -g > /timer 1:00:00 /exit` = 開瀏覽器 1 小時，關閉後自動離開 cool。
{YELLOW}範例{RESET}
  {GREEN}/exit{RESET}
  {GREEN}cool -t > /exit{RESET}               查完時數就離開
  {GREEN}cool -g a > /delay 10:00 /timer 1:00:00 /exit{RESET}
{YELLOW}相關{RESET}  cool -h /timer""",

    "ig": f"""{CYAN}/IG{RESET}  製作者 IG
{YELLOW}用法{RESET}
  /IG
{YELLOW}說明{RESET}
  顯示製作者的 IG 名稱與主頁面網址。不需要登入，不接受參數。
{YELLOW}範例{RESET}
  {GREEN}/IG{RESET}
{YELLOW}相關{RESET}  cool -H 列出隱藏指令｜/INEEDLINK""",

    "ineedlink": f"""{CYAN}/INEEDLINK{RESET}  課程連結收藏
{YELLOW}用法{RESET}
  /INEEDLINK
{YELLOW}說明{RESET}
  顯示所有課程連結的收藏文件網址（Google 文件），可複製後用 cool -u -w 批量貼入。
{YELLOW}範例{RESET}
  {GREEN}/INEEDLINK{RESET}
{YELLOW}相關{RESET}  cool -u -w 批量貼上連結｜/IG｜cool -H""",

    # ───────────────────────── 修飾符與串接 ─────────────────────────
    "mod": f"""{CYAN}>  指令修飾符（時間軸）{RESET}
{YELLOW}用法{RESET}
  <指令> > /修飾符 [值] [/修飾符 [值] …]
{YELLOW}說明{RESET}
  `>` 把設定附加給前面的指令，可搭配任何 cool 指令與 slash 指令，也可與 && / | 串接。
  一次指令分三個階段，每個關鍵字只管一個階段：
    ① 開始前   /delay T 延遲後才執行    /at 時:分 到指定時刻才執行
    ② 執行中   /timer T 倒數（別名 /for），時間到結束指令
    ③ 結束後   /clear 清畫面    /exit 離開 cool
  其他：/show 顯示瀏覽器（cool -l / -g）    /repeat N 連續執行 N 次
  一次附加給多個指令或對多個項目：用括號 ( )，見 cool -h group。
  內部固定依 ① → ② → ③ 的順序執行，與你寫的順序無關。
{YELLOW}範例{RESET}
  {GREEN}cool -h > /timer 5 /clear{RESET}
  {GREEN}cool -g a|b > /delay 10:00 /timer 1:00:00 /exit{RESET}
  {GREEN}cool -t > /at 07:05{RESET}
{YELLOW}寫法很寬鬆{RESET}
  全形＞｜：、少打空白（/timer5）、中文單位（5分、30秒）、| 接在修飾符前，都可以。
{YELLOW}提醒{RESET}
  在 cmd / PowerShell 直接輸入時 > 會被當成輸出導向，請在 cool> 內輸入或加引號。
{YELLOW}詳細{RESET}  cool -h /show、/timer、/delay、/at、/repeat、/clear、/exit""",

    "show": f"""{CYAN}/show{RESET}  顯示瀏覽器視窗
{YELLOW}用法{RESET}
  cool -l > /show        cool -g > /show        （也可省略 >：cool -l /show）
{YELLOW}說明{RESET}
  讓 Playwright 瀏覽器以可見視窗執行，取代舊的 -s / --show。預設是背景（無頭）。
{YELLOW}適用{RESET}
  只有 cool -l 與 cool -g；其他指令不開瀏覽器，加了會提示不支援。
  cool -l 遇到雙重驗證時即使沒加 /show 也會自動顯示視窗。
{YELLOW}範例{RESET}
  {GREEN}cool -l > /show{RESET}
  {GREEN}cool -g a > /show /timer 30:00{RESET}
{YELLOW}相關{RESET}  cool -l -h、cool -g -h""",

    "timer": f"""{CYAN}> /timer 時:分:秒{RESET}（別名 /for）  執行中的倒數
{YELLOW}用法{RESET}
  <指令> > /timer T
{YELLOW}說明{RESET}
  「執行中」階段的倒數：從指令開始算起，時間到就結束這個指令。逾時算正常結束，後面的 && 會繼續。
{YELLOW}時間到時的行為{RESET}
  cool -g                  關閉瀏覽器（倒數中按 Enter 可提前結束）
  cool -l -a -u -n -c      中止並回到 cool>（包含停在等你輸入的時候）
  cool -h -v -t -A         這些一瞬間就做完，改成畫面保留到時間到並顯示倒數
  後面可接 /clear 清畫面、/exit 離開 cool。
{YELLOW}時間寫法{RESET}
  1:30:00、45:00（分:秒）、90（秒）、1h30m、5分、30秒；上限 7 天。
{YELLOW}注意{RESET}
  想「延遲後才執行」請用 /delay 或 /at，不是 /timer。
{YELLOW}範例{RESET}
  {GREEN}cool -h > /timer 0:0:2{RESET}              顯示說明，倒數 2 秒後結束
  {GREEN}cool -g a|b > /timer 1:30:00{RESET}        開瀏覽器 90 分鐘後自動關閉
  {GREEN}cool -c > /timer 30 && /clear{RESET}
{YELLOW}相關{RESET}  cool -h /delay、cool -h /at、cool -h /clear""",

    "delay": f"""{CYAN}> /delay 時:分:秒{RESET}  延遲後才開始
{YELLOW}用法{RESET}
  <指令> > /delay T
{YELLOW}說明{RESET}
  「開始前」階段：先等 T 再執行指令；等待時顯示倒數，Ctrl+C 取消（指令不會執行）。
  不能與 /at 同時使用；可與 /timer 合用（/timer 從開始執行那一刻才算）。
{YELLOW}範例{RESET}
  {GREEN}cool -t > /delay 10:00{RESET}                  10 分鐘後查時數
  {GREEN}cool -g a > /delay 1:00:00 /timer 2:00:00{RESET}  1 小時後開、開 2 小時
{YELLOW}相關{RESET}  cool -h /at、cool -h /timer""",

    "at": f"""{CYAN}> /at 時:分[:秒]{RESET}  到指定時刻才開始
{YELLOW}用法{RESET}
  <指令> > /at 21:30
{YELLOW}說明{RESET}
  「開始前」階段：等到指定時刻（24 小時制）才執行；時刻已過就排到明天。
  等待時顯示倒數，Ctrl+C 取消。不能與 /delay 同時使用。
{YELLOW}範例{RESET}
  {GREEN}cool -t > /at 07:05{RESET}
  {GREEN}cool -g a > /at 21:30 /timer 1:00:00{RESET}
{YELLOW}相關{RESET}  cool -h /delay、cool -h /timer""",

    "repeat": f"""{CYAN}> /repeat 次數{RESET}  連續執行
{YELLOW}用法{RESET}
  <指令> > /repeat N
{YELLOW}說明{RESET}
  把指令連續執行 N 次（1～50），每次之間顯示「第 i/N 次」；其中一次失敗就停止。
  搭配 /timer 時每次各自計時；/delay、/at 只在第一次之前等待。
{YELLOW}範例{RESET}
  {GREEN}cool -t > /repeat 3{RESET}
  {GREEN}cool -t > /repeat 4 /timer 5{RESET}
{YELLOW}相關{RESET}  cool -h /timer""",

    "group": f"""{CYAN}( )  括號群組{RESET}  一次對多個東西附值
{YELLOW}用法{RESET}
  X > (A | B | C)          把同一個 X 對 A、B、C 各做一次
  (A | B | C) > V          把同一個設定 V 附加給 A、B、C 各一個指令
  (A | B) > (V1 | V2)      兩邊相乘，全部組合各執行一次
  (A && B) | C             單獨的括號：把括號內當成一個單位（決定執行的先後與失敗時要不要繼續）
{YELLOW}說明{RESET}
  括號裡用 | 或 ; 分隔項目，展開後依序執行，每項不論成敗都會做（等同 |）。
  `>` 的每一側要嘛是一個完整的括號群組，要嘛是一般文字；展開後一次最多 50 個指令。
  可以省略 cool：-h > (/show | /at) 等於 cool -h > (/show | /at)。
{YELLOW}說明（-h）的特別處理{RESET}
  `-h > (...)` 括號裡是「說明主題」：-h > (/show | /delay) = 看 /show 和 /delay 的說明。
{YELLOW}分開 vs 同時{RESET}
  cool -g a > (/timer 1:00:00 | /timer 2:00:00)      用 |：分成兩次執行，各用一個時間
  cool -g a > (/timer 1:00:00 /show)                 用空白：同一次執行同時套用兩個設定
{YELLOW}範例{RESET}
  {GREEN}-h > (/show | /delay | /at | /repeat){RESET}      一次看四個修飾符的說明
  {GREEN}(cool -t | cool -a) > /timer 5{RESET}             兩個指令都限時 5 秒
  {GREEN}cool -t && (cool -c | cool -a){RESET}             查時數成功後，依序開調色與帳號選單
  {GREEN}(cool -t | cool -a) > (/timer 5 | /timer 9){RESET}   4 種組合各一次
{YELLOW}注意{RESET}
  只有出現在行首，或 > | ; & ( 後面的 ( 才算群組，所以 cool -n 名稱(備註) 這種參數裡的括號不受影響。
  括號沒有成對、或內容是空的，整行都不會執行。""",

    "chain": f"""{CYAN}串接指令  &&  |  ;{RESET}
{YELLOW}用法{RESET}
  A && B        依序執行，A 失敗就不執行 B（逾時依 /timer 結束算成功）
  A | B         依序執行，不論 A 成敗
  A ; B         同 |
{YELLOW}說明{RESET}
  可以串很多段，每段可以是 cool 指令、sudo cool 指令或 slash 指令（/clear、/passwd …），
  每段都能各自帶 > 修飾符。`|` 只有後面接 cool / sudo / slash 指令時才算串接，
  所以 cool -g a|b 的多選語法不受影響。
  串接符號旁邊缺少指令（例如 cool -t &&）時，整行都不執行並說明原因。
{YELLOW}範例{RESET}
  {GREEN}cool -t && cool -g a|b{RESET}
  {GREEN}cool -t | cool -g{RESET}
  {GREEN}cool -c > /timer 3 && /clear{RESET}
{YELLOW}相關{RESET}  cool -h >""",
}

__all__ = [name for name in globals() if not name.startswith("__")]
