"""下載 xterm.js（VS Code 同款終端模擬器）的核心 + addons 到 xterm/ 目錄。"""
import urllib.request, pathlib

BASE = 'https://cdn.jsdelivr.net/npm/'
FILES = {
    # @xterm/xterm 核心 (UMD 版本，可直接在瀏覽器 <script> 用)
    '@xterm/xterm@5.5.0/lib/xterm.js': 'xterm/xterm.js',
    '@xterm/xterm@5.5.0/css/xterm.css': 'xterm/xterm.css',
    # addons (UMD)
    '@xterm/addon-fit@0.10.0/lib/addon-fit.js': 'xterm/addon-fit.js',
    '@xterm/addon-webgl@0.18.0/lib/addon-webgl.js': 'xterm/addon-webgl.js',
    '@xterm/addon-web-links@0.11.0/lib/addon-web-links.js': 'xterm/addon-web-links.js',
}
root = pathlib.Path(r'C:\Users\jusaper\Downloads\coolqml-rs')
for src, dst in FILES.items():
    out = root / dst
    out.parent.mkdir(parents=True, exist_ok=True)
    url = BASE + src
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        out.write_bytes(data)
        print('OK', dst, len(data), 'bytes')
    except Exception as e:
        print('FAIL', src, e)
