import subprocess, time, pathlib, ctypes, os
from PIL import ImageGrab

root = pathlib.Path(r'C:\Users\jusaper\Downloads\coolqml-rs\build-main')
env = dict(os.environ)
env['COOL_SHOT'] = '1'
env['COOL_SHOT_TERM'] = '1'
if os.environ.get('COOL_SHOT_TERM2'):
    env['COOL_SHOT_TERM2'] = '1'
env['COOL_SHOT_OUT'] = r'C:\Users\jusaper\Downloads\coolqml-rs\_unused.png'
p = subprocess.Popen([str(root/'coolqml.exe')], cwd=str(root), env=env)
time.sleep(9)

u = ctypes.windll.user32
Proc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
app_wins, browsers = [], []
def cb(hwnd, l):
    n = u.GetWindowTextLengthW(hwnd)
    if n > 0:
        b = ctypes.create_unicode_buffer(n+1)
        u.GetWindowTextW(hwnd, b, n+1)
        t = b.value
        low = t.lower()
        if low.startswith('cool') and 'opencode' not in low and 'caelestia' not in low:
            if u.IsWindowVisible(hwnd):
                app_wins.append(hwnd)
        elif 'opencode' in low or 'caelestia' in low or 'smartmate' in low:
            if u.IsWindowVisible(hwnd):
                browsers.append(hwnd)
    return True
u.EnumWindows(Proc(cb), 0)
print('app:', app_wins, 'browsers:', browsers)
# 暫時最小化瀏覽器
for h in browsers:
    u.ShowWindow(h, 6)  # SW_MINIMIZE
time.sleep(1)
if app_wins:
    u.ShowWindow(app_wins[-1], 3)  # SW_MAXIMIZE
time.sleep(2)
img = ImageGrab.grab()
out = pathlib.Path(r'C:\Users\jusaper\Downloads\coolqml-rs\real-screen.png')
img.save(out)
print('saved', img.size)
# 還原瀏覽器
for h in browsers:
    u.ShowWindow(h, 9)  # SW_RESTORE
p.terminate()
