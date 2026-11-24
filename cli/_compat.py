"""Shared standard-library imports for the cool application package."""
from __future__ import annotations

import base64
import getpass
import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

# getpass 在 Windows 上一律直接讀主控台，stdin 是管線（例如桌面程式、腳本）時會永遠卡住；
# 非互動 stdin 時改為從 stdin 讀一行。互動終端機行為不變（仍隱藏輸入）。
_orig_getpass = getpass.getpass

def _stdin_aware_getpass(prompt="Password: ", stream=None):
    if sys.stdin is not None and not sys.stdin.isatty():
        sys.stdout.write(prompt)
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            raise EOFError
        return line.rstrip("\r\n")
    return _orig_getpass(prompt, stream)

getpass.getpass = _stdin_aware_getpass

__all__ = [name for name in globals() if not name.startswith("__")]
