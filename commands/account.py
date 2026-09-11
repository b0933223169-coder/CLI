"""Account, login, status, and deletion commands."""
from __future__ import annotations
from .._compat import *
from ..paths import *
from ..colors import *
from ..security import *
from ..accounts import *
from ..ui import *
from .urls import load_urls

def _looks_like_profile_verification(html: str, url: str) -> bool:
    """Detect a profile-completion page instead of treating it as a login success."""
    if "user/profile.php" not in url.lower():
        return False
    text = html.lower()
    if "logout.php" in text or "登出" in text or "個人檔案" in text:
        return False
    form_markers = (
        "firstname", "lastname", 'input type="text"',
        "gender", "birthday", "phone", "mobile", "email",
        "請填寫", "verify", "verification", "確認資料",
        "complete profile", "profile form",
    )
    return "<form" in text and any(marker in text for marker in form_markers)

def _has_valid_moodle_session(cookies: list[dict]) -> bool:
    """Require a live MoodleSession cookie for a successful login."""
    now = time.time()
    for cookie in cookies:
        if str(cookie.get("name", "")).strip() != "MoodleSession":
            continue
        domain = str(cookie.get("domain", "")).lower()
        if "coolenglish.edu.tw" not in domain:
            continue
        expires = cookie.get("expires")
        if not isinstance(expires, (int, float)) or expires <= 0 or expires > now:
            return True
    return False


def cmd_login(mgr: AccountManager, args: list[str] | None = None):
    from playwright.sync_api import sync_playwright

    username = None
    display_name = None
    password = None
    if mgr.list_accounts():
        choice = _choose_login_target(mgr)
        if choice == "cancel":
            note("INFO", "已返回上一部")
            return
        elif choice is None:
            pass
        else:
            if choice["email"].startswith("unknown"):
                note("WARN", "該帳號為舊版遷移，無 Email，請重新輸入新帳號")
            else:
                username = choice["email"]
                display_name = choice["name"]
                note("INFO", f"將為已登入帳號 {display_name} ({username}) 重新登入")
                stored = get_stored_password(choice)
                if stored:
                    password = stored
                    note("INFO", "已透過 sudo 解密並自動帶入密碼，無需再次輸入")
                else:
                    password = getpass.getpass(f"密碼（{username}）: ")
                    if not password:
                        note("WARN", "已取消")
                        return

    if username is None:
        username = input("帳號 (Google Email): ").strip()
        if not username:
            note("WARN", "帳號不可為空")
            return
        if len(username) > 254:
            note("WARN", "帳號過長，已截斷")
            username = username[:254]
        if "\n" in username or "\t" in username or " " in username:
            if " " in username:
                note("WARN", "帳號包含空白，已去除")
                username = username.replace(" ", "")
        password = getpass.getpass("密碼: ")
        if not password:
            note("WARN", "密碼不可為空，已取消")
            return
        if len(password) > 512:
            note("WARN", "密碼過長")
            return
        default_name = username.split("@")[0] if "@" in username else username
        custom_name = input(f"帳號名稱 (預設: {default_name}) 直接 Enter 使用預設，或輸入新名稱: ").strip()
        display_name = custom_name if custom_name else default_name
        if mgr.find(display_name):
            note("WARN", f"名稱 '{display_name}' 已存在，將自動處理重複命名")
        if mgr.find(username):
            note("NOTICE", f"帳號 {username} 已存在，登入後將更新 cookie")

    pwd_for_save = password

    status_line("啟動瀏覽器", "WORK")
    with sync_playwright() as p:
        try:
            show_browser = args is not None and any(a in ("-s", "--show") for a in args)
            browser = p.chromium.launch(headless=not show_browser)
        except Exception as e:
            note("WARN", f"Playwright 瀏覽器啟動失敗（{e}），改用 headless=True")
            browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        status_line("啟動瀏覽器", "OK")

        def show_browser_for_interaction(reason: str) -> bool:
            nonlocal browser, context, page, show_browser
            if show_browser:
                return True
            note("NOTICE", f"{reason}，切換為可見瀏覽器供你完成操作")
            try:
                state = context.storage_state()
                current_url = page.url
                browser.close()
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(storage_state=state)
                page = context.new_page()
                page.goto(current_url, wait_until="domcontentloaded", timeout=20000)
                show_browser = True
                status_line("切換可見瀏覽器", "OK")
                return True
            except Exception as exc:
                status_line("切換可見瀏覽器", "FAILED")
                note("ERR", f"無法顯示瀏覽器：{exc}")
                return False

        status_line("前往登入頁", "WORK")
        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
        except Exception as e:
            status_line("前往登入頁", "FAILED")
            note("ERR", f"無法載入登入頁：{e}")
            try:
                browser.close()
            except Exception:
                pass
            return
        status_line("前往登入頁", "OK")

        status_line("確認頁面結構", "WORK")
        google_link = page.locator('a[href*="oauth2/login.php?id=2"]')
        if google_link.count() == 0:
            status_line("確認頁面結構", "FAILED")
            note("ERR", "找不到 Google 登入按鈕，網站結構可能已變更")
            try:
                browser.close()
            except Exception:
                pass
            return
        status_line("確認頁面結構", "OK")

        status_line("點擊 Google 登入", "WORK")
        try:
            google_link.first.click()
            page.wait_for_load_state("domcontentloaded")
        except Exception as e:
            status_line("點擊 Google 登入", "FAILED")
            note("ERR", f"點擊後導頁失敗：{e}")
            try:
                browser.close()
            except Exception:
                pass
            return
        status_line("點擊 Google 登入", "OK")

        status_line("輸入 Google 帳號", "WORK")
        try:
            email_input = page.locator("#identifierId")
            email_input.wait_for(state="visible", timeout=15000)
            email_input.wait_for(state="visible", timeout=5000)
            for _ in range(5):
                if email_input.is_enabled() and email_input.is_editable():
                    break
                page.wait_for_timeout(400)
            email_input.click(timeout=5000)
            email_input.fill(username)
            for _ in range(3):
                try:
                    if email_input.input_value(timeout=2000) == username:
                        break
                except Exception:
                    pass
                page.wait_for_timeout(300)
                email_input.fill(username)
            if email_input.input_value(timeout=2000) != username:
                raise RuntimeError("帳號欄位驗證失敗，可能是頁面尚未就緒")
            page.locator("#identifierNext").click()
        except Exception as e:
            status_line("輸入 Google 帳號", "FAILED")
            note("ERR", f"找不到帳號輸入框或填入失敗：{e}")
            try:
                browser.close()
            except Exception:
                pass
            return
        status_line("輸入 Google 帳號", "OK")

        status_line("等待密碼輸入框", "WORK")
        try:
            password_input = page.locator('input[name="Passwd"][type="password"]')
            password_input.wait_for(state="visible", timeout=20000)
            for _ in range(10):
                try:
                    if password_input.is_visible() and password_input.is_enabled() and password_input.is_editable():
                        break
                except Exception:
                    pass
                page.wait_for_timeout(500)
            page.wait_for_timeout(800)
            password_input.click(timeout=5000)
        except Exception as e:
            status_line("等待密碼輸入框", "FAILED")
            if show_browser_for_interaction("偵測到額外登入驗證"):
                note("INFO", "請在瀏覽器完成驗證後，再重新執行 cool -l")
            else:
                note("ERR", f"沒有出現密碼欄位（可能需 2FA 或帳號不存在）：{e}")
            try:
                browser.close()
            except Exception:
                pass
            return
        status_line("等待密碼輸入框", "OK")

        status_line("輸入密碼", "WORK")
        _fill_ok = False
        try:
            for attempt in range(1, 4):
                try:
                    password_input.click(timeout=3000)
                except Exception:
                    pass
                try:
                    password_input.fill("")
                except Exception:
                    pass
                page.wait_for_timeout(200)
                try:
                    password_input.fill(password)
                except Exception as e:
                    try:
                        password_input.press("Control+A")
                        password_input.press("Backspace")
                        password_input.type(password, delay=30)
                    except Exception:
                        raise e
                page.wait_for_timeout(400)
                try:
                    actual = password_input.input_value(timeout=2000)
                    if actual == password:
                        _fill_ok = True
                        break
                    else:
                        note("WARN", f"密碼欄位驗證失敗 (嘗試 {attempt}/3)：實際長度 {len(actual)} ≠ 預期 {len(password)}，重試...")
                        continue
                except Exception as ve:
                    note("WARN", f"讀取密碼欄位失敗 (嘗試 {attempt}/3)：{ve}")
                    continue
            if not _fill_ok:
                raise RuntimeError("密碼欄位多次填入後仍為空或不符，可能是頁面未就緒或被遮擋")
        except Exception as e:
            status_line("輸入密碼", "FAILED")
            note("ERR", f"填入密碼失敗：{e}")
            try:
                del password
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
            return
        finally:
            pass
        status_line("輸入密碼", "OK")

        status_line("送出密碼", "WORK")
        try:
            try:
                _v = password_input.input_value(timeout=1000)
                if not _v:
                    raise RuntimeError("送出前偵測到密碼欄位仍為空，已阻擋送出，請重試")
            except RuntimeError:
                raise
            except Exception:
                pass
            password_input.press("Enter")
            page.wait_for_load_state("domcontentloaded")
        except Exception as e:
            status_line("送出密碼", "FAILED")
            note("ERR", f"送出後發生問題：{e}")
            try:
                del password
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass
            return
        finally:
            try:
                del password
            except Exception:
                pass
        status_line("送出密碼", "OK")

        status_line("檢查登入後導向", "WORK")
        _reached = False
        for _ in range(20):
            cur_url = page.url
            try:
                html_snip = page.content()[:8000]
                challenge_text = html_snip.lower()
                has_challenge = any(
                    marker in challenge_text
                    for marker in (
                        "2-step verification", "two-step verification",
                        "two factor", "雙重驗證", "驗證碼",
                        "verification code", "security key",
                        "choose how you want to verify",
                    )
                )
                if has_challenge and not _reached:
                    show_browser_for_interaction("偵測到雙重驗證或額外安全確認")
                has_logout = (
                    "logout.php" in html_snip
                    or "登出" in html_snip
                    or "個人檔案" in html_snip
                    or "time_view_detail" in html_snip
                    or page.locator("a[href*='logout.php']").count() > 0
                )
                if not has_logout:
                    try:
                        page.wait_for_selector("a[href*='logout.php']", timeout=400)
                        has_logout = True
                    except Exception:
                        pass
            except Exception:
                has_logout = False
            if "coolenglish.edu.tw" in cur_url and has_logout:
                _reached = True
                break
            if "coolenglish.edu.tw" in cur_url:
                try:
                    cont = page.locator('a:has-text("繼續"), button:has-text("繼續"), a:has-text("Continue"), button:has-text("Continue"), a:has-text("綁定"), button:has-text("綁定"), a:has-text("確認")')
                    if cont.count() > 0 and cont.first.is_visible():
                        cont.first.click()
                        page.wait_for_load_state("domcontentloaded")
                        page.wait_for_timeout(400)
                        continue
                except Exception:
                    pass
                try:
                    acc_choice = page.locator('div:has-text("選擇帳號") a, div.account a')
                    if acc_choice.count() > 0 and acc_choice.first.is_visible():
                        acc_choice.first.click()
                        page.wait_for_load_state("domcontentloaded")
                except Exception:
                    pass
            else:
                try:
                    cont2 = page.locator('a:has-text("繼續"), button:has-text("繼續")')
                    if cont2.count() > 0 and cont2.first.is_visible():
                        cont2.first.click()
                except Exception:
                    pass
            page.wait_for_timeout(300)
        if not _reached:
            show_browser_for_interaction("偵測到額外頁面（雙重綁定／帳號選擇／2FA）")
            note("NOTICE", "請在瀏覽器視窗手動完成選擇、綁定或驗證")
            note("INFO", f"當前連結：{page.url}")
            try:
                if sys.stdin.isatty():
                    input("完成後按 Enter 繼續... ")
                else:
                    note("INFO", "非互動終端，跳過等待 3 秒")
                    time.sleep(3)
            except (EOFError, KeyboardInterrupt):
                print()
                pass
            for _ in range(15):
                try:
                    html2 = page.content()[:8000]
                    if "logout.php" in html2 or "登出" in html2 or "個人檔案" in html2 or page.locator("a[href*='logout.php']").count() > 0:
                        _reached = True
                        break
                except Exception:
                    pass
                if "coolenglish.edu.tw" in page.url:
                    try:
                        page.wait_for_selector("a[href*='logout.php']", timeout=400)
                        _reached = True
                        break
                    except Exception:
                        pass
                page.wait_for_timeout(300)
        try:
            final_html = page.content()
            final_has_logout = "logout.php" in final_html or "登出" in final_html[:8000]
            final_is_profile_gate = _looks_like_profile_verification(
                final_html, page.url
            )
        except Exception:
            final_html = ""
            final_has_logout = False
            final_is_profile_gate = False
        if final_is_profile_gate:
            show_browser_for_interaction("偵測到需要填寫的帳號驗證資料")
            note("NOTICE", "請在 Playwright 瀏覽器完成驗證或補填資料；程式會自動等待")
            completed = False
            for _ in range(600):
                try:
                    current_html = page.content()
                    current_cookies = context.cookies()
                    still_profile_gate = _looks_like_profile_verification(
                        current_html, page.url
                    )
                    if not still_profile_gate and (
                        "logout.php" in current_html
                        or "登出" in current_html
                        or _has_valid_moodle_session(current_cookies)
                    ):
                        completed = True
                        break
                except Exception:
                    pass
                page.wait_for_timeout(500)
            if not completed:
                note("ERR", "驗證資料尚未完成，未儲存 cookie；請完成後重新執行 cool -l")
                return
        if not final_has_logout:
            note("WARN", f"當前頁面仍未偵測到登入特徵（{page.url}），將仍嘗試擷取 cookie，若失敗請重試並手動完成中間頁")
        status_line("檢查登入後導向", "OK")

        _detected_uid = None
        try:
            html_for_id = page.content()
            m = re.search(r'time_view_detail_by_people\.php\?id=(\d+)', html_for_id)
            if m:
                _detected_uid = m.group(1)
            else:
                m2 = re.search(r'"userId"\s*:\s*(\d+)', html_for_id)
                if m2 and m2.group(1) not in ("0","1"):
                    _detected_uid = m2.group(1)
        except Exception:
            _detected_uid = None
        try:
            cookies = context.cookies()
        finally:
            try:
                browser.close()
            except Exception:
                pass

    coolenglish_cookies = [c for c in cookies if "coolenglish.edu.tw" in c["domain"]]
    if not coolenglish_cookies:
        status_line("擷取登入 cookie", "FAILED")
        note("ERR", "沒有抓到 cookie，登入可能未成功，請重試 login")
        return
    if not _has_valid_moodle_session(coolenglish_cookies):
        status_line("擷取登入 cookie", "FAILED")
        note("ERR", "未偵測到有效的 MoodleSession cookie；目前可能停在驗證或補填頁，請完成後重試")
        return

    status_line("擷取登入 cookie", "OK")

    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    safe_email = _sanitize_filename(username)
    cookie_file = COOKIE_DIR / f"{safe_email}.txt"
    try:
        cookie_file.resolve().relative_to(COOKIE_DIR.resolve())
    except Exception:
        safe_email = "user_" + hashlib.sha256(username.encode()).hexdigest()[:12]
        cookie_file = COOKIE_DIR / f"{safe_email}.txt"
    save_netscape_cookies(coolenglish_cookies, cookie_file)
    acc = mgr.add_or_update(username, cookie_file, display_name, password=pwd_for_save, user_id=_detected_uid)
    if _detected_uid:
        note("INFO", f"已記錄 userId：{_detected_uid}，供 cool -t 直接使用")
    try:
        mgr.path.chmod(0o600)
    except Exception:
        pass
    try:
        PASSWD_FILE.chmod(0o600)
    except Exception:
        pass
    try:
        cookie_file.chmod(0o600)
    except Exception:
        pass
    try:
        del pwd_for_save
    except Exception:
        pass
    status_line("儲存帳號資訊", "DONE")
    note("INFO", f"已儲存帳號：{acc['name']} ({acc['email']}) -> {cookie_file} ({len(coolenglish_cookies)} 筆 cookie)")
    note("NOTICE", "可用 cool -s 查看所有帳號，cool -t 顯示時數")
    status_line("全部完成", "OK")

def cmd_show(mgr: AccountManager, mode: str = "account"):
    accounts = mgr.list_accounts()
    if not accounts:
        status_line("帳號清單", "WARN")
        note("INFO", "尚未登入任何帳號，請執行： -l / --login")
        if LEGACY_COOKIE.exists():
            note("INFO", f"發現舊版 {LEGACY_COOKIE}，將於下次 login 時自動遷移")
        return

    if mode == "url":
        saved_urls = load_urls()
        print(f"\n{CYAN}=== 已儲存的課程網址清單 (cool -u -s) ==={RESET}\n")
        if saved_urls:
            print(f"{CYAN}共 {len(saved_urls)} 筆課程網址：{RESET}\n")
            for idx, u in enumerate(saved_urls, 1):
                print(f"  {YELLOW}[{idx:2d}]{RESET} {u}")
            print(f"\n{DIM}提示：使用 cool -u 進入訪問選單，或 cool -u -w 批量新增網址{RESET}\n")
        else:
            print(f"  {YELLOW}(目前清單為空){RESET}")
            print(f"  {DIM}請使用 cool -u -w 貼上並批量儲存課程網址。{RESET}\n")
        return

    # mode == "account" (預設帳號管理模式)
    print(f"\n{CYAN}=== 帳號管理清單 (cool -A / cool --ALL) ==={RESET}\n")
    print(f"{CYAN}共 {len(accounts)} 個已儲存帳號：{RESET}\n")
    for idx, acc in enumerate(accounts, 1):
        try:
            cookie_path = (PROJECT_DIR / acc["cookie_file"]).resolve()
            _allowed = [PROJECT_DIR.resolve(), _BASE.resolve()]
            if not any(str(cookie_path).startswith(str(a)) for a in _allowed):
                note("WARN", f"帳號 {acc['name']} 的 cookie 路徑異常，已略過")
                continue
        except Exception:
            cookie_path = PROJECT_DIR / acc.get("cookie_file","")
        exists = cookie_path.exists()
        expiry_info = ""
        if exists:
            try:
                mtime = datetime.fromtimestamp(cookie_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                expiry_info = f"{DIM}更新: {mtime}{RESET}"
            except Exception:
                pass
            status = f"{GREEN}● 正常{RESET}"
        else:
            status = f"{RED}● 缺少 cookie 檔{RESET}"
            expiry_info = f"{RED}{acc['cookie_file']} 不存在{RESET}"

        print(f"  {YELLOW}[{idx}]{RESET} {MAGENTA}{acc['name']}{RESET}  {status}  {expiry_info}")
        print(f"      {DIM}帳號:{RESET} {acc['email']}")
        if acc.get("password_enc"):
            pwd_len = acc.get("password_len")
            if pwd_len is None:
                try:
                    pwd_len = len(decrypt_password(acc["password_enc"]))
                except Exception:
                    pwd_len = 3
            masked = "*" * pwd_len
            if has_sudo_cached():
                try:
                    pwd_plain = decrypt_password(acc["password_enc"])
                    print(f"      {DIM}密碼:{RESET} {pwd_plain} {DIM}(sudo 解密){RESET}")
                except Exception:
                    print(f"      {DIM}密碼:{RESET} {masked} {DIM}(解密失敗){RESET}")
            else:
                print(f"      {DIM}密碼:{RESET} {masked} {DIM}(需 sudo 才顯示){RESET}")
        else:
            print(f"      {DIM}密碼:{RESET} {DIM}未儲存（舊帳號請 cool -l 重登）{RESET}")
        print(f"      {DIM}檔案:{RESET} {acc['cookie_file']}")
        if acc.get("created_at"):
            print(f"      {DIM}建立:{RESET} {acc['created_at']}")
        print()
    print(f"{DIM}提示：cool -n 可重新命名，cool -t 顯示時數{RESET}\n")

def cmd_account(mgr: AccountManager, args: list[str] = None):
    """帳號管理與切換選單 (-a)，保留原本的帳號操作流程。"""
    if args:
        note("WARN", f"cool -a 不接受額外參數：{' '.join(args)}")
        return

    accounts = mgr.list_accounts()
    if not accounts:
        status_line("帳號清單", "WARN")
        note("INFO", "尚未登入任何帳號，請先執行： cool -l")
        return

    chosen = _choose_account_interactive(mgr, "已儲存的帳號列表 (選擇以切換/檢視)")
    if not chosen:
        return

    cmd_status(mgr, [chosen])
    print(f"\n{CYAN}目前選定帳號：{RESET}{MAGENTA}{chosen['name']}{RESET} ({chosen['email']})")
    note("INFO", f"Cookie 檔案：{chosen['cookie_file']}")

def cmd_name(mgr: AccountManager, args: list[str]):
    if args:
        note("WARN", "cool -n 不接受帳號或名稱參數，請直接使用 cool -n 並從選單選擇帳號")
        return

    if not mgr.list_accounts():
        status_line("重新命名", "WARN")
        note("INFO", "尚未登入任何帳號，請先 cool -l")
        return
    acc = _choose_account_interactive(mgr, "請選擇要重新命名的帳號")
    if not acc:
        return
    print(f"已選擇：{MAGENTA}{acc['name']}{RESET} ({acc['email']})")
    try:
        new_name = input(f"請輸入新名稱 (原: {acc['name']} 直接 Enter 取消): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        note("INFO", "已取消")
        return
    if not new_name:
        note("INFO", "已取消")
        return
    acc2, old = mgr.rename(acc["name"], new_name)
    if acc2 is None:
        status_line("重新命名", "FAILED")
        note("ERR", old)
        return
    status_line("重新命名", "DONE")
    note("INFO", f"已將 '{old}' -> '{acc2['name']}' ({acc2['email']})")

def cmd_status(mgr: AccountManager, selected=None):
    """Check every stored cookie against the live website."""
    import urllib.error
    import urllib.request

    accounts = mgr.list_accounts()
    if not accounts:
        status_line("整體狀態", "WARN")
        note("INFO", "無帳號，請 -l 登入")
        return
    if selected is not None:
        accounts = selected
    for acc in accounts:
        raw = acc.get("cookie_file","")
        p = None
        for base in [_BASE, PROJECT_DIR]:
            try:
                cand = base / raw
                if cand.exists():
                    p = cand
                    break
            except Exception:
                continue
        if p is None:
            try:
                p = Path(raw)
            except Exception:
                p = PROJECT_DIR / raw
        if not p.exists():
            status_line(f"帳號 {acc['name']}", "FAILED")
            note("ERR", f"  遺失檔案: {acc['cookie_file']}")
            continue

        try:
            cookie_pairs = []
            for line in p.read_text(encoding="utf-8").splitlines():
                if not line or line.startswith("#"):
                    continue
                fields = line.split("\t")
                if len(fields) >= 7:
                    cookie_pairs.append(f"{fields[5]}={fields[6]}")
            if not cookie_pairs:
                raise ValueError("cookie 檔案沒有可用內容")

            target_url = f"{BASE_URL}/user/profile.php"
            stored_uid = acc.get("user_id")
            if stored_uid and str(stored_uid) not in ("0", "1"):
                target_url = f"{BASE_URL}/time/time_view_detail_by_people.php?id={stored_uid}"
            request = urllib.request.Request(
                target_url,
                headers={"User-Agent": UA, "Cookie": "; ".join(cookie_pairs)},
            )
            class _NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            context = ssl._create_unverified_context()
            opener = urllib.request.build_opener(
                urllib.request.HTTPSHandler(context=context),
                _NoRedirect,
            )
            try:
                response = opener.open(request, timeout=10)
                final_url = response.geturl()
                body = response.read(4096).decode("utf-8", errors="replace")
                valid = "login" not in final_url.lower() and "logintoken" not in body[:3000]
                reason = "網站接受 cookie" if valid else "網站要求重新登入"
            except urllib.error.HTTPError as error:
                location = error.headers.get("Location", "") if error.headers else ""
                valid = error.code not in (301, 302, 303, 307, 308)
                reason = f"HTTP {error.code}" if valid else f"導向登入頁：{location or 'login'}"
        except Exception as error:
            valid = False
            reason = str(error)

        status_line(
            f"帳號 {acc['name']} ({acc['email']})",
            "OK" if valid else "FAILED",
        )
        note("INFO" if valid else "WARN", f"  cookie：{reason}")

def cmd_delete(mgr: AccountManager, args: list[str]):
    if args:
        note("WARN", "cool -d 不接受帳號參數，請直接使用 cool -d 並從選單選擇帳號")
        return
    if not mgr.list_accounts():
        status_line("刪除帳號", "WARN")
        note("INFO", "無帳號可刪")
        return
    chosen = _choose_account_interactive(mgr, "請選擇要刪除的帳號")
    if not chosen:
        note("INFO", "已返回上一部")
        return
    identifier = chosen["name"]
    try:
        confirm = input(f"確定刪除 {chosen['name']} ({chosen['email']})？ [y/n]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        note("INFO", "已取消")
        return
    if confirm.lower() not in ("y", "yes"):
        note("INFO", "已取消")
        return
    ok, info = mgr.remove(identifier)
    if not ok:
        status_line("刪除帳號", "FAILED")
        note("ERR", info)
        return
    status_line("刪除帳號", "DONE")
    note("INFO", f"已刪除 {info['name']} ({info['email']})")

__all__ = [name for name in globals() if not name.startswith("__")]
