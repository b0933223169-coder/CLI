"""解析 app.py 的 Backend，列出所有 Property/Signal/Slot 签名。"""
import pathlib, re

APP = pathlib.Path(r'C:\Users\jusaper\Downloads\cool-qml-caelestia\coolqml\app.py')
src = APP.read_text(encoding='utf-8').splitlines()

print('=== PROPERTIES ===')
for i, line in enumerate(src):
    m = re.search(r'@Property\(\s*([^,)]+)', line)
    if m:
        qtype = m.group(1).strip().strip("'\"")
        for j in range(i+1, min(i+5, len(src))):
            d = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', src[j])
            if d:
                print(f'{d.group(1)}|{qtype}')
                break

print('=== SIGNALS ===')
for line in src:
    m = re.match(r'\s{4}(\w+)\s*=\s*Signal', line)
    if m:
        print(m.group(1))

print('=== SLOTS ===')
for i, line in enumerate(src):
    if not re.search(r'@Slot\(', line):
        continue
    for j in range(i+1, min(i+5, len(src))):
        d = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', src[j])
        if d:
            args = d.group(2) or ''
            params = [p.strip().split('=')[0].strip()
                      for p in args.split(',') if p.strip() and p.strip() != 'self']
            print(f'{d.group(1)}|{len(params)}')
            break
