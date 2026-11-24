"""最終 UI 驗證：開 app、開終端、最大化、抓真實螢幕。"""
import subprocess, time, pathlib, ctypes, os
from PIL import ImageGrab

root = pathlib.Path(r'C:\Users\jusaper\Downloads\cool-qml-caelestia\coolqml\coolqml-rs\build-main')
env = dict(os.environ)
env['COOL_SHOT'] = '1'
env['COOL_SHOT_TERM'] = '1'
env['COOL_SHOT_TERM2'] = '1'   # 開兩個不同分頁
env['COOL_SHOT_OUT'] = str(root/'_unused.png')
p = subprocess.Popen([str(root/'coolqml.exe')], cwd=str(root), env=env)
time.sleep(12)

u = ctypes.windll.user32
Proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
app_wins, browsers = [], []
def cb(hwnd, l):
    n = u.GetWindowTextLengthW(hwnd)
    if n > 0:
        b = ctypes.create_unicode_buffer(n+1)
        u.GetWindowTextW(hwnd, b, n+1)
        t = b.value; low = t.lower()
        if low.startswith('cool') and 'opencode' not in low and 'caelestia' not in low and 'claude' not in low:
            if u.IsWindowVisible(hwnd): app_wins.append(hwnd)
        elif 'opencode' in low or 'claude' in low:
            if u.IsWindowVisible(hwnd): browsers.append(hwnd)
    return True
u.EnumWindows(Proc(cb), 0)
print('app:', app_wins, 'browsers:', len(browsers))
for h in browsers: u.ShowWindow(h, 6)
time.sleep(1)
if app_wins:
    u.ShowWindow(app_wins[-1], 3)
    u.SetForegroundWindow(app_wins[-1])
time.sleep(2)
img = ImageGrab.grab()
out = root/'ui-final.png'
img.save(out)
print('saved', img.size)
for h in browsers: u.ShowWindow(h, 9)
p.terminate()
