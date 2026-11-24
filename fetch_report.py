"""抓單一帳號的學習報表並寫回 reports.json / network.json。

由 coolqml-rs 的 C++ host 以 QProcess 呼叫（功能沿用 Python，桌面 App 本體零 Python）。
用法：python fetch_report.py <email>
輸出：最後一行 __COOL_REPORT__{json}（ok / rows / url / fetchedAt / error）
"""
import sys, json, os, time
from pathlib import Path

ROOT = Path(r'C:\Users\jusaper\Downloads\cool-qml-caelestia\coolqml')
sys.path.insert(0, str(ROOT))

from cool_cli.paths import BASE_URL, COOKIE_DIR, _sanitize_filename
from cool_cli.commands.time_report import fetch_time_rows, _duration_minutes

DATA = Path(os.environ.get('COOL_DATA_DIR') or (Path(os.environ.get('APPDATA', '')) / 'cool'))
REPORT_FILE = DATA / 'reports.json'
NETWORK_FILE = DATA / 'network.json'
ACCOUNTS_FILE = DATA / 'accounts.json'


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception:
        return default


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def normalize_events(events):
    out = []
    for e in events or []:
        if not isinstance(e, dict):
            continue
        out.append({
            'time': str(e.get('time') or ''),
            'kind': str(e.get('kind') or ''),
            'method': str(e.get('method') or ''),
            'path': str(e.get('path') or ''),
            'status': int(e.get('status') or 0),
            'ms': int(e.get('ms') or 0),
            'size': str(e.get('size') or ''),
            'bytes': int(e.get('bytes') or 0),
        })
    return out


def main():
    if len(sys.argv) < 2:
        print('__COOL_REPORT__' + json.dumps({'ok': False, 'error': '缺少 email'}, ensure_ascii=False))
        return
    email = sys.argv[1].strip()

    # 找帳號的 cookie 路徑
    raw = read_json(ACCOUNTS_FILE, [])
    entry = None
    for a in raw:
        if str(a.get('email', '')).lower() == email.lower():
            entry = a
            break
    if not entry:
        print('__COOL_REPORT__' + json.dumps({'ok': False, 'error': '找不到帳號'}, ensure_ascii=False))
        return
    ck = entry.get('cookie_file')
    if not ck:
        print('__COOL_REPORT__' + json.dumps({'ok': False, 'error': '沒有 Cookie'}, ensure_ascii=False))
        return
    ck_path = Path(ck)
    if not ck_path.is_absolute():
        ck_path = DATA / ck
    if not ck_path.is_file():
        print('__COOL_REPORT__' + json.dumps({'ok': False, 'error': 'Cookie 檔不存在'}, ensure_ascii=False))
        return

    # 抓報表（用 venv 的 python，功能沿用）
    now = time.time()
    dt = time.strftime('%Y-%m-%dT%H:%M:%S')
    try:
        rows, url, events, error = fetch_time_rows(ck_path, entry, system_proxy=True)
        parsed = []
        for row in rows or []:
            if len(row) < 4:
                continue
            parsed.append({
                'month': str(row[0]).replace('/', '-'),
                'platform': _duration_minutes(row[1]),
                'video': _duration_minutes(row[2]),
                'practice': _duration_minutes(row[3]),
            })
        rows = parsed
    except Exception as exc:
        rows, url, events, error = None, None, [], str(exc)

    events = normalize_events(events)
    # onlyFailures 設定
    settings = read_json(DATA / 'settings.json', {})
    if settings.get('onlyFailures'):
        events = [e for e in events if e['kind'] == 'failed']

    ok = bool(rows)
    # 寫入 reports.json 的 accounts[email]
    cache = read_json(REPORT_FILE, {'accounts': {}})
    accounts = cache.setdefault('accounts', {})
    rec = accounts.get(email) or {}
    if ok:
        rec['reports'] = sorted(rows, key=lambda r: str(r.get('month') or ''))
        rec['url'] = url or BASE_URL
        rec['fetchedAt'] = dt
        rec['fetchedTs'] = now
        rec['error'] = ''
    else:
        rec['error'] = str(error or '無法取得報表')
    accounts[email] = rec
    write_json(REPORT_FILE, cache)

    # 寫入 network.json 一筆 session
    sessions = read_json(NETWORK_FILE, [])
    sessions.insert(0, {
        'id': 'r%d' % int(now * 1000),
        'label': '學習報表 · ' + str(entry.get('name') or email),
        'mode': 'direct',
        'status': 'completed' if ok else 'failed',
        'time': time.strftime('%m-%d %H:%M'),
        'startedAt': dt,
        'events': events,
        'events_n': len(events),
        'bytes': sum(int(e.get('bytes') or 0) for e in events),
        'size': '—',
        'account': email,
        'note': '' if ok else str(error),
    })
    # 保留筆數上限
    limit = max(10, int(settings.get('maxSessions') or 80))
    del sessions[limit:]
    write_json(NETWORK_FILE, sessions)

    print('__COOL_REPORT__' + json.dumps({
        'ok': ok, 'email': email,
        'rows': len(rows) if rows else 0,
        'url': url or '', 'fetchedAt': dt,
        'error': '' if ok else str(error),
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
