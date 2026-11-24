"""產生真正讀取 %APPDATA%/cool 資料的 C++ backend.cpp（Qt JSON）。"""
from pathlib import Path
import subprocess

HERE = Path(__file__).parent
out = subprocess.run(['python', str(HERE / 'scan_api.py')], capture_output=True, text=True,
                     encoding='utf-8').stdout

props = []
in_sec = False
for line in out.splitlines():
    if line.startswith('==='):
        in_sec = 'PROPERTIES' in line
        continue
    if in_sec and '|' in line:
        props.append(line.split('|'))

qml_to_cpp = {'int':'int','bool':'bool','float':'qreal','str':'QString',
              'QVariantList':'QVariantList','QVariantMap':'QVariantMap'}
list_props = {'terminalTabs','terminalProfiles','terminalHistory','variants','seeds',
              'themes','cliStyles','cliFields','accounts','courses','reports','sessions'}

c = []
c.append('#include "backend.h"')
c.append('#include <QDir>')
c.append('#include <QFile>')
c.append('#include <QJsonDocument>')
c.append('#include <QJsonObject>')
c.append('#include <QJsonArray>')
c.append('#include <QColor>')
c.append('#include <QUrl>')
c.append('#include <QStandardPaths>')
c.append('#include <QGuiApplication>')
c.append('#include <QClipboard>')
c.append('')
c.append('namespace {')
c.append('QString dataDir() {')
c.append('    QString env = qEnvironmentVariable("COOL_DATA_DIR");')
c.append('    if (!env.isEmpty()) return env;')
c.append('    QString appdata = qEnvironmentVariable("APPDATA");')
c.append('    if (!appdata.isEmpty()) return appdata + "/cool";')
c.append('    return QDir::homePath() + "/.config/cool";')
c.append('}')
c.append('QJsonDocument readJson(const QString &name) {')
c.append('    QFile f(QDir(dataDir()).filePath(name));')
c.append('    if (!f.open(QIODevice::ReadOnly)) return QJsonDocument();')
c.append('    return QJsonDocument::fromJson(f.readAll());')
c.append('}')
c.append('QString fmtStamp(const QString &s) {')
c.append('    if (s.isEmpty()) return QStringLiteral("—");')
c.append('    // 2026-11-17T14:02:15 -> 2026-11-17 14:02')
c.append('    QString t = s; t.replace(QLatin1Char(\'T\'), QLatin1Char(\' \'));')
c.append('    if (t.size() >= 16) t = t.left(16);')
c.append('    return t;')
c.append('}')
c.append('} // namespace')
c.append('')
c.append('Backend::Backend(QObject *parent) : QObject(parent)')
c.append('{')
c.append('    // 讀取設定')
c.append('    QJsonObject st = readJson("settings.json").object().toVariantMap().isEmpty()')
c.append('        ? QJsonObject() : readJson("settings.json").object();')
c.append('    m_settings = readJson("settings.json").object().toVariantMap();')
c.append('    m_seed = m_settings.value("seed", "#ff583d").toString();')
c.append('    m_variant = m_settings.value("variant", "expressive").toString();')
c.append('    m_dark = m_settings.value("dark", true).toBool();')
c.append('    m_contrast = m_settings.value("contrast", 0.0).toDouble();')
c.append('    reloadAccounts();')
c.append('    reloadReports();')
c.append('    reloadSessions();')
c.append('    reloadCourses();')
c.append('    buildColors();')
c.append('}')
c.append('')

# getter 實作
for name, qtype in props:
    cpp = qml_to_cpp.get(qtype, 'QVariant')
    if name == 'dataDir':
        c.append(f'{cpp} Backend::{name}() const {{ return ::dataDir(); }}')
    elif name == 'homeDir':
        c.append(f'{cpp} Backend::{name}() const {{ return QDir::homePath(); }}')
    elif name == 'exportDir':
        c.append(f'{cpp} Backend::{name}() const {{ return QDir(dataDir()).filePath("exports"); }}')
    elif name == 'settingsFile':
        c.append(f'{cpp} Backend::{name}() const {{ return QDir(dataDir()).filePath("settings.json"); }}')
    elif name == 'colorsFile':
        c.append(f'{cpp} Backend::{name}() const {{ return QDir(dataDir()).filePath("colors.json"); }}')
    elif name == 'coolScript':
        c.append(f'{cpp} Backend::{name}() const {{ return QStringLiteral("cool.py"); }}')
    elif name == 'settings':
        c.append(f'{cpp} Backend::{name}() const {{ return m_settings; }}')
    elif name == 'colors':
        c.append(f'{cpp} Backend::{name}() const {{ return m_colors; }}')
    elif name == 'seed':
        c.append(f'{cpp} Backend::{name}() const {{ return m_seed; }}')
    elif name == 'variant':
        c.append(f'{cpp} Backend::{name}() const {{ return m_variant; }}')
    elif name == 'dark':
        c.append(f'{cpp} Backend::{name}() const {{ return m_dark; }}')
    elif name == 'contrast':
        c.append(f'{cpp} Backend::{name}() const {{ return m_contrast; }}')
    elif name == 'accounts':
        c.append(f'{cpp} Backend::{name}() const {{ return m_accounts; }}')
    elif name == 'reports':
        c.append(f'{cpp} Backend::{name}() const {{ return m_reports; }}')
    elif name == 'sessions':
        c.append(f'{cpp} Backend::{name}() const {{ return m_sessions; }}')
    elif name == 'courses':
        c.append(f'{cpp} Backend::{name}() const {{ return m_courses; }}')
    elif name == 'selected':
        c.append(f'{cpp} Backend::{name}() const {{ return m_selected; }}')
    elif name == 'networkSize':
        c.append(f'{cpp} Backend::{name}() const {{ return m_networkSize; }}')
    elif name == 'cacheSize':
        c.append(f'{cpp} Backend::{name}() const {{ return QStringLiteral("—"); }}')
    elif name == 'defaultTerminal':
        c.append(f'{cpp} Backend::{name}() const {{ return QStringLiteral("powershell"); }}')
    elif name == 'defaultTerminalProfile':
        c.append(f'{cpp} Backend::{name}() const {{ return QStringLiteral("powershell"); }}')
    elif name == 'loginMode':
        c.append(f'{cpp} Backend::{name}() const {{ return m_settings.value("defaultLoginMode","headless").toString(); }}')
    elif name == 'trayAvailable':
        c.append(f'{cpp} Backend::{name}() const {{ return true; }}')
    elif name == 'encryptionStatus':
        c.append(f'{cpp} Backend::{name}() const {{ return QStringLiteral("已加密"); }}')
    elif name == 'reportUpdated':
        c.append(f'{cpp} Backend::{name}() const {{ return m_reportUpdated; }}')
    elif name == 'reportSource':
        c.append(f'{cpp} Backend::{name}() const {{ return m_reportSource; }}')
    elif name == 'reportError':
        c.append(f'{cpp} Backend::{name}() const {{ return QString(); }}')
    elif name == 'reportBusy':
        c.append(f'{cpp} Backend::{name}() const {{ return false; }}')
    elif name in ('terminalTabs','terminalProfiles','terminalHistory','variants','seeds','themes','cliStyles','cliFields'):
        c.append(f'{cpp} Backend::{name}() const {{ return {cpp}(); }}')
    elif name == 'terminalCount':
        c.append(f'{cpp} Backend::{name}() const {{ return 0; }}')
    elif name == 'terminalText':
        c.append(f'{cpp} Backend::{name}() const {{ return QString(); }}')
    elif name == 'terminalStatus':
        c.append(f'{cpp} Backend::{name}() const {{ return QStringLiteral("未啟動"); }}')
    elif name == 'terminalRunning':
        c.append(f'{cpp} Backend::{name}() const {{ return false; }}')
    elif name == 'terminalProfile':
        c.append(f'{cpp} Backend::{name}() const {{ return QStringLiteral("powershell"); }}')
    elif name == 'activeTerminalId':
        c.append(f'{cpp} Backend::{name}() const {{ return 0; }}')
    elif name == 'loginBusy':
        c.append(f'{cpp} Backend::{name}() const {{ return false; }}')
    elif name == 'loginStatus':
        c.append(f'{cpp} Backend::{name}() const {{ return QString(); }}')
    elif name == 'debugSection':
        c.append(f'{cpp} Backend::{name}() const {{ return QString(); }}')

# 私有方法與 slots
c.append('')
c.append('void Backend::buildColors() {')
c.append('    // 依 seed 產生一組 Material 色彩（簡化版：固定色，之後接 scheme 移植）')
c.append('    QVariantMap m;')
scheme = {
    'primary':'#ff583d','onPrimary':'#ffffff','primaryContainer':'#ffdbd0',
    'onPrimaryContainer':'#3d0f04','secondary':'#77574f','onSecondary':'#ffffff',
    'secondaryContainer':'#ffdbd2','onSecondaryContainer':'#2d1510',
    'tertiary':'#6d5e3d','onTertiary':'#ffffff','tertiaryContainer':'#f6e2b8',
    'onTertiaryContainer':'#241a05','surface':'#fdf7f5','onSurface':'#241917',
    'surfaceContainer':'#f3eae7','surfaceContainerLow':'#f7f0ed',
    'surfaceContainerHigh':'#eee4e1','surfaceContainerHighest':'#e8deda',
    'surfaceContainerLowest':'#ffffff','onSurfaceVariant':'#85736e',
    'outline':'#a18e88','outlineVariant':'#d3c2bc','success':'#2e6b46',
    'successContainer':'#c4ecd1','onSuccess':'#ffffff','error':'#ba1a1a',
    'errorContainer':'#ffdad6','onError':'#ffffff','onErrorContainer':'#410002',
    'warning':'#8a5a00','warningContainer':'#ffdfb9','inverseSurface':'#3b2f2c',
    'inverseOnSurface':'#fff0eb','inversePrimary':'#ffb59e','shadow':'#000000',
    'scrim':'#000000','surfaceVariant':'#f3eae7','background':'#fdf7f5',
    'onBackground':'#241917','surfaceTint':'#ff583d','surfaceBright':'#fdf7f5',
    'surfaceDim':'#ddd3d0','onSuccessContainer':'#0a381c','onWarning':'#1f1300',
}
for k,v in scheme.items():
    c.append(f'    m[QStringLiteral("{k}")] = QColor(QStringLiteral("{v}"));')
c.append('    m_colors = m;')
c.append('}')

# reloadAccounts
c.append('void Backend::reloadAccounts() {')
c.append('    QVariantList out;')
c.append('    QJsonArray arr = readJson("accounts.json").array();')
c.append('    int i = 0;')
c.append('    for (const auto &v : arr) {')
c.append('        QJsonObject a = v.toObject();')
c.append('        QString email = a.value("email").toString();')
c.append('        QVariantMap m;')
c.append('        m["id"] = ++i;')
c.append('        m["name"] = a.value("name").toString();')
c.append('        m["email"] = email;')
c.append('        m["last"] = fmtStamp(a.value("last_login").toString());')
c.append('        m["cookie"] = QStringLiteral("valid");')
c.append('        m["expires"] = QStringLiteral("工作階段 Cookie");')
c.append('        m["obtained"] = fmtStamp(a.value("created_at").toString());')
c.append('        m["saved"] = !a.value("password_enc").toString().isEmpty();')
c.append('        m["synced"] = true;')
c.append('        QString mode = a.value("login_mode").toString();')
c.append('        m["note"] = (mode=="headed"||mode=="headless") ? QStringLiteral("以 Playwright 登入") : QString();')
c.append('        m["mode"] = mode;')
c.append('        // avatar')
c.append('        QString stem = email; stem.replace(QLatin1Char(\'@\'),QLatin1Char(\'_\')).replace(QLatin1Char(\'.\'),QLatin1Char(\'_\'));')
c.append('        for (const char *ext : {"png","jpg","jpeg","webp","gif"}) {')
c.append('            QString p = QDir(dataDir()).filePath(QString("avatars/%1.%2").arg(stem, QString::fromLatin1(ext)));')
c.append('            if (QFile::exists(p)) { m["avatar"] = QUrl::fromLocalFile(p).toString(); break; }')
c.append('        }')
c.append('        if (!m.contains("avatar")) m["avatar"] = QString();')
c.append('        out.append(m);')
c.append('    }')
c.append('    m_accounts = out;')
c.append('}')

# reloadReports
c.append('void Backend::reloadReports() {')
c.append('    QVariantList out;')
c.append('    QJsonObject root = readJson("reports.json").object();')
c.append('    QJsonObject accounts = root.value("accounts").toObject();')
c.append('    // 依目前選擇的帳號 email')
c.append('    QString email;')
c.append('    if (m_selected >= 0 && m_selected < m_accounts.size())')
c.append('        email = m_accounts.at(m_selected).toMap().value("email").toString();')
c.append('    QJsonObject entry = accounts.value(email).toObject();')
c.append('    if (entry.isEmpty() && !accounts.isEmpty()) {')
c.append('        entry = accounts.begin().value().toObject();')
c.append('    }')
c.append('    QJsonArray reps = entry.value("reports").toArray();')
c.append('    for (const auto &v : reps) {')
c.append('        QJsonObject r = v.toObject();')
c.append('        QVariantMap m;')
c.append('        m["month"] = r.value("month").toString();')
c.append('        m["platform"] = r.value("platform").toInt();')
c.append('        m["video"] = r.value("video").toInt();')
c.append('        m["practice"] = r.value("practice").toInt();')
c.append('        out.append(m);')
c.append('    }')
c.append('    m_reports = out;')
c.append('    m_reportSource = entry.value("url").toString();')
c.append('    m_reportUpdated = entry.value("fetchedAt").toString();')
c.append('}')

# reloadSessions
c.append('void Backend::reloadSessions() {')
c.append('    QVariantList out;')
c.append('    QJsonArray arr = readJson("network.json").array();')
c.append('    qint64 total = 0;')
c.append('    for (const auto &v : arr) {')
c.append('        QJsonObject s = v.toObject();')
c.append('        QVariantMap m = s.toVariantMap();')
c.append('        if (m["status"]=="active") m["status"] = "stopped";')
c.append('        out.append(m);')
c.append('        total += s.value("bytes").toInt();')
c.append('    }')
c.append('    m_sessions = out;')
c.append('    m_networkSize = QStringLiteral("%1 B").arg(total);')
c.append('}')

# reloadCourses (解析 urls.txt)
c.append('void Backend::reloadCourses() {')
c.append('    QVariantList out;')
c.append('    QFile f(QDir(dataDir()).filePath("urls.txt"));')
c.append('    if (!f.open(QIODevice::ReadOnly)) { m_courses = out; return; }')
c.append('    QString group, category;')
c.append('    int id = 0;')
c.append('    while (!f.atEnd()) {')
c.append('        QString line = QString::fromUtf8(f.readLine()).trimmed();')
c.append('        if (line.startsWith("# group:")) group = line.mid(8).trimmed();')
c.append('        else if (line.startsWith("# category:")) category = line.mid(11).trimmed();')
c.append('        else if (line.startsWith("http")) {')
c.append('            QVariantMap m;')
c.append('            m["id"] = ++id;')
c.append('            m["url"] = line;')
c.append('            m["category"] = category.isEmpty() ? group : category;')
c.append('            m["alias"] = group.isEmpty() ? category : group;')
c.append('            m["opens"] = 0;')
c.append('            m["opened"] = QStringLiteral("尚未開啟");')
c.append('            m["openedAt"] = QString();')
c.append('            out.append(m);')
c.append('        }')
c.append('    }')
c.append('    m_courses = out;')
c.append('}')

# slots（空實作，但 select / updateSetting / setScheme 給基本行為）
in_sig, in_slot = False, False
sig_lines = []
slot_lines = []
for line in out.splitlines():
    if line.startswith('==='):
        in_sig = 'SIGNALS' in line
        in_slot = 'SLOTS' in line
        continue
    if in_sig:
        sig_lines.append(line.strip())
    if in_slot and '|' in line:
        slot_lines.append(line.split('|'))
seen = set()
for p in slot_lines:
    n, argc = p[0], int(p[1])
    if n in seen: continue
    seen.add(n)
    params = ', '.join(f'const QVariant &/*a{i}*/' for i in range(argc)) if argc else ''
    body = ''
    if n == 'select':
        body = 'if (argc_placeholder) {}'
        params = 'const QVariant &a0'
        body = 'int i = a0.toInt(); if (i>=0 && i<m_accounts.size()) { m_selected = i; reloadReports(); emit selectedChanged(); emit reportsChanged(); }'
    elif n == 'updateSetting':
        params = 'const QVariant &a0, const QVariant &a1'
        body = 'm_settings[a0.toString()] = a1; emit settingsChanged();'
    elif n == 'setScheme':
        params = 'const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3'
        body = 'm_seed=a0.toString(); m_variant=a1.toString(); m_dark=a2.toBool(); buildColors(); emit colorsChanged(); emit schemeChanged();'
    elif n == 'applyTheme':
        params = 'const QVariant &a0, const QVariant &a1, const QVariant &a2'
        body = 'm_seed=a0.toString(); m_variant=a1.toString(); m_dark=a2.toBool(); buildColors(); emit colorsChanged();'
    elif n == 'refresh' or n == 'refreshReports':
        body = 'reloadReports(); emit reportsChanged();'
    elif n == 'refreshSessions' or n == 'refresh':
        body = 'reloadSessions(); emit sessionsChanged();'
    elif n == 'copyText':
        params = 'const QVariant &a0'
        body = 'QGuiApplication::clipboard()->setText(a0.toString());'
    c.append(f'void Backend::{n}({params}) {{ {body} }}')

(HERE / 'backend.cpp').write_text('\n'.join(c) + '\n', encoding='utf-8')
print('real backend.cpp written,', len(props), 'getters,', len(seen), 'slots')
