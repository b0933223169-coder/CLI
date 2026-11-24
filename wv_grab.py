import subprocess, pathlib, time, os
from PIL import ImageGrab

env = dict(os.environ)
env['PATH'] = "C:\\Qt\\6.9.3\\mingw_64\\bin;C:\\Qt\\Tools\\mingw1310_64\\bin;" + env['PATH']
env.pop('QT_QPA_PLATFORM', None)
root = pathlib.Path(r'C:\Users\jusaper\Downloads\coolqml-rs')
p = subprocess.Popen([str(root/'wv_host.exe')], cwd=str(root), env=env,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                     text=True, encoding='utf-8', errors='replace')
# 讓 host 自己跑（它 6 秒後 quit 並存 wv-shot.png）；但 grabWindow 抓不到 WebView
# 改：直接用 ImageGrab 在 4 秒時抓螢幕
time.sleep(4)
img = ImageGrab.grab()
out = root/'wv-screen.png'
img.save(out)
print('saved', out, img.size)
try:
    o,_ = p.communicate(timeout=10)
    print(o[:300])
except Exception:
    p.kill()
