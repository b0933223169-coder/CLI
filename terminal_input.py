"""Terminal input handling for the interactive cool CLI."""
from __future__ import annotations

from ._compat import *
from .colors import DIM, RESET

try:
    import readline

    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set editing-mode emacs")
except ImportError:
    readline = None


def _strip_control_sequences(text: str) -> str:
    """Remove terminal escape sequences and legacy shortcut markers."""
    text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z~]", "", text)
    text = re.sub(r"\x1bO[A-Za-z]", "", text)
    text = re.sub(r"(;\d+){1,2}~", "", text)
    text = re.sub(r"[A-Za-z_]*(?:COOL_KEY|OL_KEY|EY)_[0-9_~:-]*", "", text)
    return text.strip()


__all__ = [name for name in globals() if not name.startswith("__")]
