"""Windows pseudo-terminal widget with VT screen emulation."""
from __future__ import annotations

import html
import os
import queue
import signal
import subprocess
import threading

import pyte
from winpty import PTY, WinptyError

from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QPalette, QTextCursor
from PyQt6.QtWidgets import QTextEdit


_COLORS = {
    "default": "#cccccc",
    "black": "#000000",
    "red": "#cd3131",
    "green": "#0dbc79",
    "brown": "#e5e510",
    "blue": "#2472c8",
    "magenta": "#bc3fbc",
    "cyan": "#11a8cd",
    "white": "#e5e5e5",
    "brightblack": "#666666",
    "brightred": "#f14c4c",
    "brightgreen": "#23d18b",
    "brightbrown": "#f5f543",
    "brightblue": "#3b8eea",
    "brightmagenta": "#d670d6",
    "brightcyan": "#29b8db",
    "brightwhite": "#e5e5e5",
}


class PtyReader(QThread):
    output_received = pyqtSignal(str)
    process_exited = pyqtSignal(int)

    def __init__(
        self,
        command: list[str],
        cwd: str,
        env: dict[str, str],
        dimensions: tuple[int, int],
        parent=None,
    ):
        super().__init__(parent)
        self._command = command
        self._cwd = cwd
        self._env = env
        self._dimensions = dimensions
        self._events: queue.SimpleQueue[tuple[str, str | tuple[int, int]]] = queue.SimpleQueue()
        self._stop_requested = threading.Event()
        self._termination_sent = threading.Event()
        self._process_id: int | None = None

    def write(self, text: str):
        self._events.put(("input", text))

    def resize(self, rows: int, columns: int):
        self._events.put(("resize", (rows, columns)))

    def stop(self):
        self._stop_requested.set()
        self._terminate_process()

    def _terminate_process(self):
        process_id = self._process_id
        if process_id is not None and not self._termination_sent.is_set():
            self._termination_sent.set()
            self._terminate(process_id)

    @staticmethod
    def _terminate(process_id: int):
        try:
            os.kill(process_id, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def run(self):
        process = None
        exit_code = 1
        try:
            rows, columns = self._dimensions
            process = PTY(columns, rows, backend=1)
            env = "\0".join(f"{key}={value}" for key, value in self._env.items()) + "\0"
            cmdline = " " + subprocess.list2cmdline(self._command[1:])
            process.spawn(self._command[0], cmdline, cwd=self._cwd, env=env)
            self._process_id = process.pid
            if self._stop_requested.is_set():
                self._terminate_process()

            while True:
                if self._stop_requested.is_set():
                    self._terminate_process()
                while True:
                    try:
                        event, value = self._events.get_nowait()
                    except queue.Empty:
                        break
                    if process.isalive():
                        if event == "input" and isinstance(value, str):
                            process.write(value)
                        elif event == "resize" and isinstance(value, tuple):
                            rows, columns = value
                            process.set_size(columns, rows)

                try:
                    text = process.read(blocking=False)
                except (OSError, WinptyError):
                    if not process.isalive():
                        break
                    raise
                if text:
                    self.output_received.emit(text)
                else:
                    self.msleep(10)

            exit_code = process.get_exitstatus()
        except (OSError, WinptyError) as exc:
            self.output_received.emit(f"\r\n[終端錯誤：{exc}]\r\n")
        finally:
            if process and process.isalive():
                self._terminate(process.pid)
            self._process_id = None
            self.process_exited.emit(exit_code if exit_code is not None else 0)


class EmbeddedTerminal(QTextEdit):
    """Interactive terminal view backed by a real Windows pseudo-terminal."""

    process_exited = pyqtSignal(int)
    output_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setUndoRedoEnabled(False)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet(
            "QTextEdit{background:#141414;color:#cccccc;border:none;padding:8px;"
            "selection-background-color:#264f78;selection-color:#ffffff;}"
        )
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Highlight, QColor("#264f78"))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._screen = pyte.HistoryScreen(100, 32, history=2000)
        self._stream = pyte.Stream(self._screen)
        self._reader: PtyReader | None = None
        self._render_pending = False
        self._show_banner()

    def _show_banner(self):
        self._stream.feed("cool v2.0 — 反偵測學習時數工具\r\n")
        self._stream.feed("─" * 52 + "\r\n")
        self._render()

    def start_process(self, command: list[str], cwd: str, env: dict[str, str]):
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self.moveCursor(QTextCursor.MoveOperation.End)
        dimensions = self._terminal_size()
        self._reader = PtyReader(
            command,
            cwd,
            env,
            dimensions,
            self,
        )
        self._reader.output_received.connect(self.output_received)
        self._reader.process_exited.connect(self._reader_finished)
        self._reader.finished.connect(self._reader.deleteLater)
        self._reader.start()
        self.setFocus()

    def _reader_finished(self, exit_code: int):
        self._reader = None
        self.process_exited.emit(exit_code)

    def write_input(self, text: str):
        if self._reader and self._reader.isRunning():
            self._reader.write(text)

    def terminate(self):
        reader = self._reader
        if reader:
            reader.stop()
            reader.wait(3000)
        self._reader = None

    def feed(self, text: str):
        self._stream.feed(text)
        if not self._render_pending:
            self._render_pending = True
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(0, self._render)

    def _terminal_size(self) -> tuple[int, int]:
        metrics = self.fontMetrics()
        columns = max(40, (self.viewport().width() - 16) // max(1, metrics.horizontalAdvance("M")))
        rows = max(10, (self.viewport().height() - 16) // max(1, metrics.lineSpacing()))
        return rows, columns

    def resizeEvent(self, event):
        super().resizeEvent(event)
        rows, columns = self._terminal_size()
        self._screen.resize(lines=rows, columns=columns)
        if self._reader and self._reader.isRunning():
            self._reader.resize(rows, columns)
        self._render()

    @staticmethod
    def _css_color(color: str, default: str) -> str:
        return color if color.startswith("#") else _COLORS.get(color, default)

    def _render_line(self, line: dict[int, object]) -> str:
        cells = list(line.values())
        while cells and cells[-1].data == " ":
            cells.pop()
        spans = []
        previous_style = None
        text = []
        for cell in cells:
            fg = self._css_color(cell.fg, "#cccccc")
            bg = self._css_color(cell.bg, "#141414")
            if cell.reverse:
                fg, bg = bg, fg
            style = (
                fg,
                bg,
                cell.bold,
                cell.italics,
                cell.underscore,
                cell.strikethrough,
            )
            if previous_style is not None and style != previous_style:
                spans.append(self._span("".join(text), previous_style))
                text = []
            previous_style = style
            text.append(cell.data)
        if text and previous_style is not None:
            spans.append(self._span("".join(text), previous_style))
        return "".join(spans)

    @staticmethod
    def _span(text: str, style: tuple) -> str:
        fg, bg, bold, italics, underscore, strikethrough = style
        decorations = []
        if underscore:
            decorations.append("underline")
        if strikethrough:
            decorations.append("line-through")
        css = f"color:{fg};background-color:{bg};"
        if bold:
            css += "font-weight:bold;"
        if italics:
            css += "font-style:italic;"
        if decorations:
            css += "text-decoration:" + " ".join(decorations) + ";"
        return f'<span style="{css}">{html.escape(text)}</span>'

    def _render(self):
        self._render_pending = False
        history = list(self._screen.history.top)
        rows = [self._render_line(row) for row in history]
        rows.extend(
            self._render_line(self._screen.buffer[index])
            for index in range(self._screen.lines)
        )
        scrollbar = self.verticalScrollBar()
        follow_output = scrollbar.value() >= scrollbar.maximum() - 2
        cursor = self.textCursor()
        preserve = cursor.hasSelection()
        selection_start, selection_end = cursor.selectionStart(), cursor.selectionEnd()
        self.setHtml("<br>".join(rows))
        if preserve:
            cursor = self.textCursor()
            cursor.setPosition(min(selection_start, len(self.toPlainText())))
            cursor.setPosition(min(selection_end, len(self.toPlainText())), QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
        elif follow_output:
            self.moveCursor(QTextCursor.MoveOperation.End)
            scrollbar.setValue(scrollbar.maximum())

    def keyPressEvent(self, event: QKeyEvent):
        modifiers = event.modifiers()
        key = event.key()
        if modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_C:
            if self.textCursor().hasSelection():
                self.copy()
            else:
                self.write_input("\x03")
            return
        if modifiers & Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_V:
            self.write_input(self._clipboard_text())
            return
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
                self.write_input(chr(key - Qt.Key.Key_A + 1))
                return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.write_input("\r")
        elif key == Qt.Key.Key_Backspace:
            self.write_input("\x7f")
        elif key == Qt.Key.Key_Tab:
            self.write_input("\t")
        elif key == Qt.Key.Key_Escape:
            self.write_input("\x1b")
        elif key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Right, Qt.Key.Key_Left):
            self.write_input({
                Qt.Key.Key_Up: "\x1b[A",
                Qt.Key.Key_Down: "\x1b[B",
                Qt.Key.Key_Right: "\x1b[C",
                Qt.Key.Key_Left: "\x1b[D",
            }[key])
        elif key == Qt.Key.Key_Home:
            self.write_input("\x1b[H")
        elif key == Qt.Key.Key_End:
            self.write_input("\x1b[F")
        elif key == Qt.Key.Key_Delete:
            self.write_input("\x1b[3~")
        elif key == Qt.Key.Key_PageUp:
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - self.viewport().height()
            )
        elif key == Qt.Key.Key_PageDown:
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() + self.viewport().height()
            )
        elif event.text():
            self.write_input(event.text())
        else:
            super().keyPressEvent(event)

    @staticmethod
    def _clipboard_text() -> str:
        from PyQt6.QtWidgets import QApplication

        return QApplication.clipboard().text()
