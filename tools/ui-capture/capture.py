#!/usr/bin/env python3
"""Baseline UI capture for the cool desktop app (Electron + React).

Launches the already-built Electron app with an isolated, empty
--user-data-dir, drives it over the Chrome DevTools Protocol using the
system-installed Python Playwright (no new project dependency), takes baseline
screenshots and records layout measurements as JSON.

Outputs go to C:/work/baseline (override with COOL_BASELINE_DIR).
Nothing in the repository is modified: the script only creates the git-ignored
runtime files the app itself insists on writing, and removes them again if they
did not exist before the run.

Usage:  python tools/ui-capture/capture.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "desktop"
ELECTRON = DESKTOP / "node_modules" / "electron" / "dist" / "electron.exe"
OUT = Path(os.environ.get("COOL_BASELINE_DIR", "C:/work/baseline"))

# Runtime files the app creates in the repository root (git-ignored).
REPO_RUNTIME_FILES = ("accounts.json", "cookies", "urls.txt", "colors.json")

# (file slug, sidebar label)
PAGES = [
    ("工作台", "工作台"),
    ("帳號", "帳號"),
    ("課程", "課程網址"),
    ("報表", "學習報表"),
    ("網路", "網路紀錄"),
    ("設定", "設定"),
]

DEFAULT = {"fontSize": 13, "splitRatio": 0.68}

# One Electron launch per settings combination (settings are read from disk at
# startup, so changing fontSize / splitRatio requires a restart).
LEGS = [
    {"settings": {"fontSize": 13, "splitRatio": 0.68}, "port": 9311},
    {"settings": {"fontSize": 24, "splitRatio": 0.68}, "port": 9312},
    {"settings": {"fontSize": 13, "splitRatio": 0.8}, "port": 9313},
]

VIEW_1360 = (1360, 900)
VIEW_1000 = (1000, 680)


def log(message: str) -> None:
    print(message, flush=True)


def fail(message: str) -> "NoReturn":  # type: ignore[valid-type]
    print(f"FAILED: {message}", file=sys.stderr, flush=True)
    sys.exit(1)


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def guard_no_real_accounts() -> None:
    """Rule: screenshots must never contain real personal data."""
    repo_accounts = ROOT / "accounts.json"
    if repo_accounts.exists():
        data = read_json(repo_accounts)
        if isinstance(data, list) and len(data) > 0:
            fail(
                f"{repo_accounts} contains {len(data)} account record(s); "
                "refusing to capture screenshots that could show personal data."
            )


def wait_for_cdp(port: int, timeout: float = 60.0) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/json/version"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            time.sleep(0.5)
    fail(f"CDP endpoint on port {port} never came up")


def launch_electron(port: int, user_data_dir: Path, log_file: Path) -> subprocess.Popen:
    if not ELECTRON.exists():
        fail(f"electron binary missing: {ELECTRON}")
    args = [
        str(ELECTRON),
        ".",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
    ]
    handle = log_file.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        args,
        cwd=str(DESKTOP),
        stdout=handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    )
    return proc


def stop_electron(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    try:
        proc.wait(timeout=15)
    except Exception:
        pass


def wait_for_app_page(browser, timeout: float = 60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for context in browser.contexts:
            for page in context.pages:
                if not page.url.startswith("file:"):
                    continue
                try:
                    if page.locator(".app-shell").count() > 0:
                        return page
                except Exception:
                    continue
        time.sleep(0.5)
    fail("renderer page with .app-shell never appeared")


def set_viewport(page, width: int, height: int) -> None:
    session = page.context.new_cdp_session(page)
    session.send(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": False,
            "screenWidth": width,
            "screenHeight": height,
        },
    )
    session.detach()


def ensure_terminal_open(page) -> None:
    toggle = page.locator('.titlebar button[title="顯示終端"]')
    if toggle.count() > 0:
        toggle.first.click()
        page.wait_for_selector(".main-layout:not(.terminal-hidden)", timeout=15000)
        page.wait_for_timeout(600)


def ensure_sidebar_open(page) -> None:
    """The sidebar starts collapsed to a 56px rail; nav items are display:none.

    Expand it so the pages are reachable and the shell matches the 236px / 205px
    sidebar width assumed by the layout spec.
    """
    if page.locator(".workbench[data-sidebar-open='true']").count() > 0:
        return
    toggle = page.locator(".sidebar-brand-toggle")
    if toggle.count() == 0:
        fail("sidebar toggle not found")
    toggle.first.click()
    page.wait_for_selector(".workbench[data-sidebar-open='true']", timeout=10000)
    page.wait_for_timeout(500)


def goto_page(page, slug: str, label: str) -> None:
    item = page.locator(".sidebar .nav-item").filter(has_text=label)
    if item.count() == 0:
        fail(f"sidebar entry not found: {label}")
    item.first.click()
    # The breadcrumb in the page top bar mirrors the current page state for all
    # six pages (the settings nav item never receives .active - App.tsx:978).
    page.wait_for_function(
        """(label) => {
            const el = document.querySelector('.page-topbar .breadcrumbs strong')
            return !!el && el.textContent.trim() === label
        }""",
        arg=label,
        timeout=15000,
    )
    page.wait_for_timeout(500)


def shot(page, name: str) -> Path:
    path = OUT / name
    page.screenshot(path=str(path))
    log(f"  shot -> {path.name}")
    return path


def measure_a(page):
    """1000x680 + splitRatio 0.8: is the terminal dock clipped?"""
    return page.evaluate(
        """() => {
          const rect = (sel) => {
            const el = document.querySelector(sel)
            if (!el) return null
            const b = el.getBoundingClientRect()
            return { top: b.top, bottom: b.bottom, height: b.height, width: b.width }
          }
          const de = document.documentElement
          const ml = document.querySelector('.main-layout')
          const dock = document.querySelector('.terminal-dock')
          const dockRect = dock ? dock.getBoundingClientRect() : null
          const round = (n) => Math.round(n * 100) / 100
          return {
            viewport: { innerWidth: innerWidth, innerHeight: innerHeight, devicePixelRatio: devicePixelRatio },
            documentVisibleHeight: de.clientHeight,
            documentVisibleWidth: de.clientWidth,
            pageContent: rect('.page-content'),
            terminalDock: rect('.terminal-dock'),
            terminalDockBottomOverflowsDocument: dockRect ? dockRect.bottom > de.clientHeight : null,
            terminalDockBottomOverflowPx: dockRect ? round(Math.max(0, dockRect.bottom - de.clientHeight)) : null,
            mainLayoutScrollHeight: ml ? ml.scrollHeight : null,
            mainLayoutClientHeight: ml ? ml.clientHeight : null,
            mainLayoutOverflowsY: ml ? ml.scrollHeight > ml.clientHeight : null,
            documentScrollHeight: de.scrollHeight,
            documentOverflowsY: de.scrollHeight > de.clientHeight,
            bodyScrollHeight: document.body.scrollHeight,
            statusBar: rect('.statusbar'),
            splitRatioStyle: getComputedStyle(document.querySelector('.page-content')).flexBasis
          }
        }"""
    )


def measure_overflow(page, selectors):
    """Horizontal overflow of document + the given scroll containers."""
    return page.evaluate(
        """(selectors) => {
          const out = {}
          const round = (n) => Math.round(n * 100) / 100
          for (const sel of selectors) {
            const nodes = [...document.querySelectorAll(sel)]
            nodes.forEach((el, i) => {
              const key = nodes.length > 1 ? sel + '[' + i + ']' : sel
              if (el.scrollWidth > el.clientWidth) {
                out[key] = {
                  scrollWidth: el.scrollWidth,
                  clientWidth: el.clientWidth,
                  overflowPx: round(el.scrollWidth - el.clientWidth)
                }
              }
            })
          }
          const de = document.documentElement
          out['document'] = {
            scrollWidth: de.scrollWidth,
            clientWidth: de.clientWidth,
            overflowPx: round(de.scrollWidth - de.clientWidth),
            overflowsX: de.scrollWidth > de.clientWidth
          }
          return out
        }""",
        selectors,
    )


SCROLL_SELECTORS = [
    ".page-content",
    ".content-wrap",
    ".main-layout",
    ".main-column",
    ".app-shell",
    ".account-table",
    ".report-table",
    ".network-list",
    ".course-list",
    ".table-head",
    ".table-row",
]


def main() -> int:
    if not DESKTOP.exists():
        fail(f"desktop/ not found at {DESKTOP}")
    if not (DESKTOP / "out" / "main" / "index.js").exists():
        fail("desktop/out is missing - run `npm run build` in desktop/ first")

    guard_no_real_accounts()

    OUT.mkdir(parents=True, exist_ok=True)
    user_data = Path(tempfile.mkdtemp(prefix="cool-ui-capture-"))
    log(f"isolated userData (empty temp dir): {user_data.name}")

    pre_existing = {name for name in REPO_RUNTIME_FILES if (ROOT / name).exists()}

    measurements: dict = {
        "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "app": "cool-desktop (Electron + React)",
        "notes": [
            "Viewport is forced with CDP Emulation.setDeviceMetricsOverride, so "
            "document.documentElement.clientWidth/clientHeight equal the requested "
            "window size exactly (the native window keeps its default size).",
            "fontSize / splitRatio are written to <userData>/data/settings.json "
            "before launch; the app reads them at startup.",
            "Terminal panel starts closed in the app (App.tsx useState(false)) and "
            "is opened by clicking the title-bar toggle for every capture.",
            "userData is an empty temp folder, so no account/cookie data exists.",
        ],
        "legs": [],
    }

    try:
        with sync_playwright() as pw:
            for index, leg in enumerate(LEGS, start=1):
                settings = dict(DEFAULT)
                settings.update(leg["settings"])
                port = leg["port"]
                log(f"--- leg {index}: settings={settings} port={port}")

                data_dir = user_data / "data"
                data_dir.mkdir(parents=True, exist_ok=True)
                (data_dir / "settings.json").write_text(
                    json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
                )

                log_path = OUT / f"electron-leg{index}.log"
                proc = launch_electron(port, user_data, log_path)
                page = None
                browser = None
                try:
                    wait_for_cdp(port)
                    browser = pw.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                    page = wait_for_app_page(browser)
                    ensure_sidebar_open(page)
                    ensure_terminal_open(page)

                    font = settings["fontSize"]
                    split = settings["splitRatio"]
                    leg_record = {
                        "settings": settings,
                        "screenshots": [],
                        "measurements": {},
                    }

                    # ---- 1360x900: all six pages, screenshots -------------
                    if abs(split - 0.68) < 1e-9:
                        set_viewport(page, *VIEW_1360)
                        page.wait_for_timeout(400)
                        for slug, label in PAGES:
                            goto_page(page, slug, label)
                            name = f"{slug}_{font}_{VIEW_1360[0]}x{VIEW_1360[1]}_{split}.png"
                            shot(page, name)
                            leg_record["screenshots"].append(name)

                    # ---- 1000x680: accounts page -------------------------
                    set_viewport(page, *VIEW_1000)
                    page.wait_for_timeout(400)
                    goto_page(page, "帳號", "帳號")
                    name = f"帳號_{font}_{VIEW_1000[0]}x{VIEW_1000[1]}_{split}.png"
                    shot(page, name)
                    leg_record["screenshots"].append(name)

                    # ---- measurements ------------------------------------
                    if font == 13 and split == 0.68:
                        leg_record["measurements"][
                            "b_accounts_horizontal_overflow_1000x680_font13"
                        ] = {
                            "viewport": list(VIEW_1000),
                            "page": "帳號",
                            "scrollWidthVsClientWidth": page.evaluate(
                                """() => {
                                  const m = (sel) => {
                                    const el = document.querySelector(sel)
                                    if (!el) return null
                                    return { scrollWidth: el.scrollWidth,
                                             clientWidth: el.clientWidth,
                                             overflowsX: el.scrollWidth > el.clientWidth }
                                  }
                                  const de = document.documentElement
                                  return {
                                    document: { scrollWidth: de.scrollWidth,
                                                clientWidth: de.clientWidth,
                                                overflowsX: de.scrollWidth > de.clientWidth },
                                    accountTable: m('.account-table'),
                                    accountTableHead: m('.account-table .table-head'),
                                    pageContent: m('.page-content'),
                                    contentWrap: m('.content-wrap')
                                  }
                                }"""
                            ),
                            "accountTableDetail": page.evaluate(
                                """() => {
                                  const table = document.querySelector('.account-table')
                                  const head = document.querySelector('.account-table .table-head')
                                  if (!table || !head) return null
                                  const cs = getComputedStyle(head)
                                  const tracks = cs.gridTemplateColumns === 'none' ? [] :
                                    cs.gridTemplateColumns.split(' ').map(v => parseFloat(v))
                                  const gap = parseFloat(cs.columnGap) || 0
                                  const pad = parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight)
                                  const gridWidth = tracks.reduce((a, b) => a + b, 0) + gap * Math.max(0, tracks.length - 1)
                                  const contentBox = head.clientWidth - pad
                                  return {
                                    headExists: true,
                                    rowCount: document.querySelectorAll('.account-table .table-row').length,
                                    gridTemplateColumns: cs.gridTemplateColumns,
                                    columnGap: cs.columnGap,
                                    padding: cs.paddingLeft + ' ' + cs.paddingRight,
                                    gridTracksSumPx: Math.round(gridWidth * 100) / 100,
                                    headContentBoxPx: contentBox,
                                    gridOverflowsHeadByPx: Math.round((gridWidth - contentBox) * 100) / 100,
                                    accountTableOverflowX: cs ? getComputedStyle(table).overflowX : null
                                  }
                                }"""
                            ),
                            "caveat": (
                                "Measured on an EMPTY accounts table (fresh userData, no login). "
                                "Row-level overflow cannot occur with zero rows."
                            ),
                        }

                    if font == 24:
                        per_page = {}
                        for slug, label in PAGES:
                            goto_page(page, slug, label)
                            per_page[slug] = measure_overflow(page, SCROLL_SELECTORS)
                        leg_record["measurements"][
                            "c_font24_horizontal_overflow_1000x680"
                        ] = {
                            "viewport": list(VIEW_1000),
                            "fontSize": font,
                            "perPage": per_page,
                        }

                    if abs(split - 0.8) < 1e-9:
                        leg_record["measurements"][
                            "a_terminal_clip_1000x680_split0.8"
                        ] = {"viewport": list(VIEW_1000), "page": "帳號", **measure_a(page)}

                    measurements["legs"].append(leg_record)
                finally:
                    if browser is not None:
                        try:
                            browser.close()
                        except Exception:
                            pass
                    stop_electron(proc)
                time.sleep(1.0)
    finally:
        # remove runtime files the app created in the repo that were not there
        removed = []
        for name in REPO_RUNTIME_FILES:
            path = ROOT / name
            if name in pre_existing or not path.exists():
                continue
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
            removed.append(name)
            log(f"cleaned up app-created {name}")

        measurements["repoRuntimeFilesRemoved"] = removed
        measurements["repoRuntimeFilesPreExisting"] = sorted(pre_existing)

    (OUT / "measurements.json").write_text(
        json.dumps(measurements, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    log(f"wrote {OUT / 'measurements.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
