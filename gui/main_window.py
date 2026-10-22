"""cool GUI — PyQt6 主視窗。
終端機面板 + 四個可切換側邊欄（LOG / AI / 瀏覽器 / FP）。
"""
from __future__ import annotations
import sys
import os
import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QTextEdit, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QGridLayout, QStackedWidget,
)
from PyQt6.QtCore import (
    Qt, QTimer,
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QTextCursor,
)
from .terminal import EmbeddedTerminal


# ── 顏色常數 ──────────────────────────────────────────────────────────────────
BG_DARK   = "#141414"
BG_PANEL  = "#1e1e1e"
BG_SIDE   = "#252526"
BG_TERM   = "#141414"
FG_MAIN   = "#cccccc"
FG_DIM    = "#555555"
FG_INFO   = "#4ec9b0"
FG_WARN   = "#dcdcaa"
FG_ERR    = "#f48771"
FG_OK     = "#6a9955"
FG_HI     = "#9cdcfe"
FG_URL    = "#ce9178"
FG_ACT    = "#c586c0"
FG_PING   = "#4fc1ff"
ACCENT    = "#0078d4"
ACCENT_BG = "#1a3a5c"
BTN_BG    = "#2d2d2d"
BTN_HOV   = "#3a3a3a"
BORDER    = "#3a3a3a"
STATUS_BG = "#0078d4"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:12]


# ── 終端機輸出面板 ────────────────────────────────────────────────────────────
class TerminalWidget(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {BG_TERM};
                color: {FG_MAIN};
                border: none;
                padding: 8px;
            }}
        """)

    COLORS = {
        "info": FG_MAIN,
        "ok":   FG_OK,
        "warn": FG_WARN,
        "err":  FG_ERR,
        "act":  FG_ACT,
        "ping": FG_PING,
        "url":  FG_URL,
        "dim":  FG_DIM,
    }

    def append_line(self, text: str, level: str = "info", ts: str = ""):
        color = self.COLORS.get(level, FG_MAIN)
        ts_html = f'<span style="color:{FG_DIM}">{ts or _ts()}</span> ' if ts != "_no_ts_" else ""
        html = f'{ts_html}<span style="color:{color}">{self._escape(text)}</span>'
        self.moveCursor(QTextCursor.MoveOperation.End)
        self.insertHtml(html + "<br>")
        self.moveCursor(QTextCursor.MoveOperation.End)

    @staticmethod
    def _escape(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def banner(self):
        self.append_line("cool v2.0 — 反偵測學習時數工具", "ok", "_no_ts_")
        self.append_line("─" * 52, "dim", "_no_ts_")


# ── 側邊欄按鈕 ───────────────────────────────────────────────────────────────
class SideButton(QPushButton):
    def __init__(self, icon_char: str, label: str):
        super().__init__()
        self._icon_char = icon_char
        self._label     = label
        self._active    = False
        self.setFixedSize(52, 52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh()

    def set_active(self, v: bool):
        self._active = v
        self._refresh()

    def _refresh(self):
        bg  = ACCENT_BG if self._active else BTN_BG
        fg  = "#ffffff"  if self._active else "#999999"
        brd = ACCENT     if self._active else BORDER
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                color: {fg};
                border: 1px solid {brd};
                border-radius: 6px;
                font-size: 9px;
            }}
            QPushButton:hover {{
                background: {BTN_HOV};
                color: #ffffff;
            }}
        """)
        self.setText(f"{self._icon_char}\n{self._label}")


# ── LOG 面板（Playwright network / page events）───────────────────────────────
class LogPanel(QWidget):
    def __init__(self, main_win):
        super().__init__()
        self._mw = main_win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = self._header("Playwright 網路 I/O")
        lay.addWidget(hdr)

        self._out = TerminalWidget()
        self._out.append_line("── 等待 Playwright 瀏覽器網路事件 ──", "dim", "_no_ts_")
        lay.addWidget(self._out)

    def _header(self, title: str) -> QWidget:
        w = QFrame()
        w.setStyleSheet(f"background:{BG_SIDE};border-bottom:1px solid {BORDER};")
        w.setFixedHeight(32)
        hl = QHBoxLayout(w)
        hl.setContentsMargins(10, 0, 6, 0)
        lbl = QLabel(title.upper())
        lbl.setStyleSheet(f"color:#888;font-size:10px;letter-spacing:1px;")
        hl.addWidget(lbl)
        hl.addStretch()
        return w

    def append(self, text: str, level: str = "info"):
        self._out.append_line(text, level)


# ── AI 面板 ──────────────────────────────────────────────────────────────────
class AiPanel(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QFrame()
        hdr.setStyleSheet(f"background:{BG_SIDE};border-bottom:1px solid {BORDER};")
        hdr.setFixedHeight(32)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 0, 6, 0)
        lbl = QLabel("AI 動態修正".upper())
        lbl.setStyleSheet("color:#888;font-size:10px;letter-spacing:1px;")
        hl.addWidget(lbl)
        hl.addStretch()
        lay.addWidget(hdr)

        self._msgs = TerminalWidget()
        self._msgs.append_line("AI 監控中，偵測到 fingerprint 異常時自動提示。", "info", "_no_ts_")
        lay.addWidget(self._msgs)

        inp_row = QWidget()
        inp_row.setStyleSheet(f"background:{BG_PANEL};border-top:1px solid {BORDER};")
        inp_row.setFixedHeight(44)
        il = QHBoxLayout(inp_row)
        il.setContentsMargins(8, 6, 8, 6)
        self._inp = QLineEdit()
        self._inp.setPlaceholderText("問 AI 或指示修正...")
        self._inp.setStyleSheet(f"""
            QLineEdit {{
                background:{BG_DARK};color:{FG_MAIN};
                border:1px solid {BORDER};border-radius:4px;
                padding:4px 8px;font-size:12px;
            }}
        """)
        self._inp.returnPressed.connect(self._send)
        il.addWidget(self._inp)
        btn = QPushButton("送出")
        btn.setFixedWidth(48)
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{ACCENT};color:#fff;
                border:none;border-radius:4px;font-size:12px;
            }}
            QPushButton:hover {{ background:#005fa3; }}
        """)
        btn.clicked.connect(self._send)
        il.addWidget(btn)
        lay.addWidget(inp_row)

    def _send(self):
        text = self._inp.text().strip()
        if not text:
            return
        self._msgs.append_line(f"你：{text}", "hi", "_no_ts_")
        self._inp.clear()
        self._msgs.append_line("AI：分析中...", "dim", "_no_ts_")

    def notify(self, msg: str, level: str = "warn"):
        self._msgs.append_line(msg, level)


# ── 瀏覽器面板 ──────────────────────────────────────────────────────────────
class BrowserPanel(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QFrame()
        hdr.setStyleSheet(f"background:{BG_SIDE};border-bottom:1px solid {BORDER};")
        hdr.setFixedHeight(32)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 0, 6, 0)
        lbl = QLabel("瀏覽器視圖".upper())
        lbl.setStyleSheet("color:#888;font-size:10px;letter-spacing:1px;")
        hl.addWidget(lbl)
        hl.addStretch()
        lay.addWidget(hdr)

        self._url_bar = QFrame()
        self._url_bar.setStyleSheet(f"background:{BG_PANEL};border-bottom:1px solid {BORDER};")
        self._url_bar.setFixedHeight(34)
        ul = QHBoxLayout(self._url_bar)
        ul.setContentsMargins(8, 4, 8, 4)
        self._url_lbl = QLabel("—")
        self._url_lbl.setStyleSheet(f"color:{FG_URL};font-size:11px;font-family:Consolas;")
        ul.addWidget(self._url_lbl)
        lay.addWidget(self._url_bar)

        self._msg = QLabel("無頭模式中\n加 -s 啟動有頭模式才可見瀏覽器視窗")
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg.setStyleSheet(f"color:{FG_DIM};font-size:12px;")
        lay.addWidget(self._msg, 1)

    def set_url(self, url: str):
        self._url_lbl.setText(url[:80] + ("..." if len(url) > 80 else ""))

    def set_headless(self, is_headless: bool):
        if is_headless:
            self._msg.setText("無頭模式中\n加 -s 啟動有頭模式才可見瀏覽器視窗")
        else:
            self._msg.setText("有頭模式 — 瀏覽器視窗已開啟")


# ── FP 面板 ──────────────────────────────────────────────────────────────────
class FpPanel(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QFrame()
        hdr.setStyleSheet(f"background:{BG_SIDE};border-bottom:1px solid {BORDER};")
        hdr.setFixedHeight(32)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(10, 0, 6, 0)
        lbl = QLabel("Fingerprint 數據".upper())
        lbl.setStyleSheet("color:#888;font-size:10px;letter-spacing:1px;")
        hl.addWidget(lbl)
        hl.addStretch()
        lay.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea{{border:none;background:{BG_PANEL};}}")

        inner = QWidget()
        inner.setStyleSheet(f"background:{BG_PANEL};")
        self._grid = QGridLayout(inner)
        self._grid.setContentsMargins(10, 10, 10, 10)
        self._grid.setSpacing(6)
        self._cells: dict[str, QLabel] = {}

        FP_KEYS = [
            ("navigator.webdriver", "?"),
            ("navigator.plugins",   "?"),
            ("navigator.platform",  "?"),
            ("navigator.languages", "?"),
            ("hardwareConcurrency", "?"),
            ("deviceMemory",        "?"),
            ("window.chrome",       "?"),
            ("viewport",            "?"),
            ("sec-ch-ua",           "?"),
            ("timezone",            "?"),
            ("canvas FP",           "?"),
            ("WebGL renderer",      "?"),
        ]
        for i, (k, v) in enumerate(FP_KEYS):
            row, col = divmod(i, 2)
            cell = QFrame()
            cell.setStyleSheet(f"""
                QFrame {{
                    background:{BG_SIDE};
                    border:1px solid {BORDER};
                    border-radius:4px;
                }}
            """)
            cl = QVBoxLayout(cell)
            cl.setContentsMargins(8, 6, 8, 6)
            cl.setSpacing(2)
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet(f"color:{FG_DIM};font-size:10px;")
            val   = QLabel(v)
            val.setStyleSheet(f"color:{FG_MAIN};font-size:11px;font-family:Consolas;font-weight:bold;")
            cl.addWidget(lbl_k)
            cl.addWidget(val)
            self._grid.addWidget(cell, row, col)
            self._cells[k] = val

        scroll.setWidget(inner)
        lay.addWidget(scroll)

    def update_fp(self, data: dict):
        """接收 dict {key: (value, status)} status: ok/bad/neu"""
        for k, (v, status) in data.items():
            if k not in self._cells:
                continue
            lbl = self._cells[k]
            color = FG_OK if status == "ok" else FG_ERR if status == "bad" else FG_MAIN
            suffix = " ✓" if status == "ok" else " ✗" if status == "bad" else ""
            lbl.setText(v + suffix)
            lbl.setStyleSheet(f"color:{color};font-size:11px;font-family:Consolas;font-weight:bold;")


# ── 狀態列 ───────────────────────────────────────────────────────────────────
class StatusBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(26)
        self.setStyleSheet(f"background:{STATUS_BG};")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(20)

        self._conn  = self._item("● 待機")
        self._time  = self._item("累積 00:00:00")
        self._ping  = self._item("ping —")
        lay.addWidget(self._conn)
        lay.addWidget(self._time)
        lay.addWidget(self._ping)
        lay.addStretch()
        self._stlth = self._item("◈ stealth 啟用")
        lay.addWidget(self._stlth)

        self._elapsed = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def _item(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#fff;font-size:11px;")
        return lbl

    def set_connected(self, v: bool):
        self._conn.setText("● 已連線" if v else "● 待機")

    def start_timer(self):
        self._timer.start(1000)

    def stop_timer(self):
        self._timer.stop()

    def _tick(self):
        self._elapsed += 1
        h, r = divmod(self._elapsed, 3600)
        m, s = divmod(r, 60)
        self._time.setText(f"累積 {h:02d}:{m:02d}:{s:02d}")

    def set_ping(self, status: str):
        self._ping.setText(f"ping {status}")


# ── 主視窗 ───────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("cool v2")
        self.resize(1200, 680)
        self._current_panel: str | None = "log"
        self._panel_widths: dict[str, int] = {
            "log": 320, "ai": 320, "browser": 320, "fp": 300,
        }
        self._terminal_log_buffer = ""
        self._setup_ui()
        self._apply_palette()
        self._term.output_received.connect(self._handle_terminal_output)
        self._term.process_exited.connect(self._terminal_process_exited)
        QTimer.singleShot(0, self._start_terminal)

    def _apply_palette(self):
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window,     QColor(BG_DARK))
        p.setColor(QPalette.ColorRole.WindowText, QColor(FG_MAIN))
        QApplication.setPalette(p)
        self.setStyleSheet(f"QMainWindow{{background:{BG_DARK};}}")

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Titlebar ──────────────────────────────────────────────────────
        tb = QFrame()
        tb.setFixedHeight(30)
        tb.setStyleSheet(f"background:{BG_SIDE};border-bottom:1px solid {BORDER};")
        tbl = QHBoxLayout(tb)
        tbl.setContentsMargins(12, 0, 12, 0)
        for color in ("#FF5F57", "#FEBC2E", "#28C840"):
            dot = QFrame()
            dot.setFixedSize(11, 11)
            dot.setStyleSheet(f"background:{color};border-radius:5px;")
            tbl.addWidget(dot)
        tbl.addSpacing(8)
        title_lbl = QLabel("cool v2 — 反偵測學習時數工具")
        title_lbl.setStyleSheet(f"color:{FG_DIM};font-size:12px;")
        tbl.addStretch()
        tbl.addWidget(title_lbl)
        tbl.addStretch()
        root.addWidget(tb)

        # ── Body ──────────────────────────────────────────────────────────
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setFixedWidth(52)
        sidebar.setStyleSheet(f"background:{BG_SIDE};border-right:1px solid {BORDER};")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(7, 10, 7, 10)
        sl.setSpacing(4)
        sl.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._btns: dict[str, SideButton] = {}
        panels_def = [
            ("log",     "▦",  "LOG"),
            ("ai",      "◈",  "AI"),
            ("browser", "◻",  "瀏覽"),
            ("fp",      "⊕",  "FP"),
        ]
        for key, icon, label in panels_def:
            btn = SideButton(icon, label)
            btn.clicked.connect(lambda _, k=key: self._toggle_panel(k))
            self._btns[key] = btn
            sl.addWidget(btn)

        sl.addStretch()
        settings_btn = SideButton("⚙", "設定")
        settings_btn.clicked.connect(self._open_settings)
        sl.addWidget(settings_btn)
        body.addWidget(sidebar)

        # Main area: terminal + splitter + panel
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(3)
        self._splitter.setStyleSheet(f"""
            QSplitter::handle {{ background: {BORDER}; }}
            QSplitter::handle:hover {{ background: {ACCENT}; }}
        """)

        # Terminal
        term_wrap = QWidget()
        term_wrap.setStyleSheet(f"background:{BG_TERM};")
        twl = QVBoxLayout(term_wrap)
        twl.setContentsMargins(0, 0, 0, 0)
        twl.setSpacing(0)
        self._term = EmbeddedTerminal()
        twl.addWidget(self._term)

        self._splitter.addWidget(term_wrap)

        # Side panel stack
        self._panel_stack = QStackedWidget()
        self._panel_stack.setStyleSheet(f"background:{BG_PANEL};")
        self._panel_stack.setMinimumWidth(200)
        self._panel_stack.setMaximumWidth(600)

        self._log_panel     = LogPanel(self)
        self._ai_panel      = AiPanel()
        self._browser_panel = BrowserPanel()
        self._fp_panel      = FpPanel()

        self._panel_stack.addWidget(self._log_panel)      # 0
        self._panel_stack.addWidget(self._ai_panel)       # 1
        self._panel_stack.addWidget(self._browser_panel)  # 2
        self._panel_stack.addWidget(self._fp_panel)       # 3

        self._panel_idx = {"log": 0, "ai": 1, "browser": 2, "fp": 3}
        self._splitter.addWidget(self._panel_stack)
        self._splitter.setSizes([860, 340])

        body.addWidget(self._splitter)
        root.addLayout(body, 1)

        # Status bar
        self._status = StatusBar()
        root.addWidget(self._status)

        # Start with log panel open
        self._btns["log"].set_active(True)

    # ── Panel toggle ─────────────────────────────────────────────────────────
    def _toggle_panel(self, key: str):
        if self._current_panel == key:
            # 收起
            self._panel_stack.setVisible(False)
            self._btns[key].set_active(False)
            self._current_panel = None
        else:
            # 儲存舊寬度
            if self._current_panel:
                w = self._splitter.sizes()[1]
                self._panel_widths[self._current_panel] = w
                self._btns[self._current_panel].set_active(False)
            # 切換
            self._panel_stack.setCurrentIndex(self._panel_idx[key])
            self._panel_stack.setVisible(True)
            new_w = self._panel_widths.get(key, 320)
            total = sum(self._splitter.sizes())
            self._splitter.setSizes([total - new_w, new_w])
            self._btns[key].set_active(True)
            self._current_panel = key

    # ── Embedded terminal and Playwright event routing ───────────────────────
    def _start_terminal(self):
        cool_py = str(Path(__file__).resolve().parents[1] / "cool.py")
        if getattr(sys, "frozen", False):
            command = [sys.executable, "--gui-repl"]
        else:
            command = [sys.executable, "-X", "utf8", "-u", cool_py, "--gui-repl"]
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["TERM"] = "xterm-256color"
        try:
            self._term.start_process(command, str(Path(cool_py).parent), env)
        except Exception as exc:
            self._term.feed(f"\r\n[無法啟動嵌入式終端：{exc}]\r\n")
            self._status.set_connected(False)
            return
        self._status.set_connected(True)
        self._status.start_timer()

    def _handle_terminal_output(self, text: str):
        marker = "@@COOL_PLAYWRIGHT_LOG@@"
        self._terminal_log_buffer += text
        while "\n" in self._terminal_log_buffer:
            line, self._terminal_log_buffer = self._terminal_log_buffer.split("\n", 1)
            line = line.rstrip("\r")
            if marker in line:
                before, payload = line.split(marker, 1)
                if before:
                    self._term.feed(before)
                self._append_network_event(payload)
            else:
                self._term.feed(line + "\r\n")

        pending = self._terminal_log_buffer
        if pending and not marker.startswith(pending.lstrip("\r")):
            self._term.feed(pending)
            self._terminal_log_buffer = ""

    def _append_network_event(self, payload: str):
        try:
            record = json.loads(payload)
            event = record.get("event", "network")
            status = record.get("status")
            level = "err" if event == "requestfailed" else (
                "warn" if isinstance(status, int) and status >= 400 else "info"
            )
            for line in json.dumps(record, ensure_ascii=False, indent=2).splitlines():
                self._log_panel.append(line, level)
        except json.JSONDecodeError:
            self._log_panel.append(payload, "err")

    def _terminal_process_exited(self, exit_code: int):
        self._term.feed(f"\r\n[REPL 結束，exit {exit_code}]\r\n")
        self._status.set_connected(False)
        self._status.stop_timer()

    def _open_settings(self):
        self._term.feed("\r\n設定功能開發中...\r\n")

    def closeEvent(self, event):
        self._term.terminate()
        event.accept()


# ── 入口 ─────────────────────────────────────────────────────────────────────
def launch():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch()
