# -*- mode: python ; coding: utf-8 -*-
# cool GUI — PyInstaller 打包設定
# 執行方式：pyinstaller cool.spec

from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

block_cipher = None
root_modules = [
    (str(path), ".")
    for path in Path(".").glob("*.py")
    if path.name != "cool.py"
]

hidden = (
    collect_submodules("playwright") +
    collect_submodules("PyQt6") +
    collect_submodules("pyte") +
    collect_submodules("winpty") +
    ["playwright.sync_api", "playwright.async_api"]
)

a = Analysis(
    ["cool.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("gui",      "gui"),
        ("commands", "commands"),
        *root_modules,
    ],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="cool",
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 環境檢查階段需要終端，檢查完用 ShowWindow 藏起來
    icon=None,
)
