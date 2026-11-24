"""向 Cool English 確認單一帳號的 Cookie 是否仍有效。

由 coolqml-rs 的 C++ host 呼叫。用法：python check_cookie.py <email>
輸出：最後一行 __COOL_COOKIE__{"valid": true/false}
"""
import sys, json, os
from pathlib import Path

ROOT = Path(r'C:\Users\jusaper\Downloads\cool-qml-caelestia\coolqml')
sys.path.insert(0, str(ROOT))
from cool_cli.commands.time_report import fetch_time_rows

DATA = Path(os.environ.get('COOL_DATA_DIR') or (Path(os.environ.get('APPDATA', '')) / 'cool'))


def load_cookies(path):
    out = []
    try:
        for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
            if not line.strip() or line.startswith('#'):
                continue
            segs = line.split('\t')
            if len(segs) >= 7:
                out.append({'name': segs[5], 'value': segs[6], 'domain': segs[0]})
    except Exception:
        pass
    return out


def main():
    email = sys.argv[1].strip() if len(sys.argv) > 1 else ''
    state = 'unknown'
    try:
        accs = json.loads((DATA / 'accounts.json').read_text(encoding='utf-8'))
        acc = next((a for a in accs if str(a.get('email', '')).lower() == email.lower()), None)
        if acc and acc.get('cookie_file'):
            ck = Path(acc['cookie_file'])
            if not ck.is_absolute():
                ck = DATA / ck
            # 最可靠：直接抓報表，抓得到就一定是有效 Cookie（不看登出文字，避免誤判）
            rows, url, events, err = fetch_time_rows(ck, acc, system_proxy=True)
            if rows:
                state = 'valid'
            elif err and ('Cookie' in err or '登入' in err or '303' in err or '302' in err or 'login' in err.lower()):
                state = 'expired'
            else:
                # 抓不到但原因不明（網路/網站問題）→ 不輕易說過期
                state = 'unknown'
    except Exception:
        state = 'unknown'
    print('__COOL_COOKIE__' + json.dumps({'state': state}, ensure_ascii=False))


if __name__ == '__main__':
    main()
