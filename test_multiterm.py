"""自動化測試：開兩個不同終端分頁，確認各自獨立 + 擷取畫面。"""
import subprocess, time, pathlib, ctypes, os
from PIL import ImageGrab

root = pathlib.Path(r'C:\Users\jusaper\Downloads\coolqml-rs\build-main')
env = dict(os.environ)
p = subprocess.Popen([str(root/'coolqml.exe')], cwd=str(root), env=env)
time.sleep(6)

u = ctypes.windll.user32
# 找 app 視窗提到前景
Proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
wins = []
def cb(hwnd, l):
    n = u.GetWindowTextLengthW(hwnd)
    if n > 0:
        b = ctypes.create_unicode_buffer(n+1)
        u.GetWindowTextW(hwnd, b, n+1)
        if b.value.startswith('cool') and 'opencode' not in b.value.lower():
            wins.append(hwnd)
    return True
u.EnumWindows(Proc(cb), 0)
for h in wins: u.ShowWindow(h, 3)
time.sleep(1)
# 按 Ctrl+` 開終端
VK_OEM_3 = 0xC0
def key(vk, ctrl=False):
    if ctrl: u.keybd_event(0x11, 0, 0, 0)
    u.keybd_event(vk, 0, 0, 0); u.keybd_event(vk, 0, 2, 0)
    if ctrl: u.keybd_event(0x11, 0, 2, 0)
key(VK_OEM_3, ctrl=True)
time.sleep(4)
img = ImageGrab.grab()
out = pathlib.Path(r'C:\Users\jusaper\Downloads\coolqml-rs\multiterm-shot.png')
img.save(out)
print('saved', img.size, 'windows', len(wins))
p.terminate()
