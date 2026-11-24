"""產生 backend.h：完整 property/signal/slot + 私有狀態。"""
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
signals = []
in_sig = False
for line in out.splitlines():
    if line.startswith('==='):
        in_sig = 'SIGNALS' in line
        continue
    if in_sig and line.strip():
        signals.append(line.strip())
slots = []
in_slot = False
for line in out.splitlines():
    if line.startswith('==='):
        in_slot = 'SLOTS' in line
        continue
    if in_slot and '|' in line:
        slots.append(line.split('|'))

qml_to_cpp = {'int':'int','bool':'bool','float':'qreal','str':'QString',
              'QVariantList':'QVariantList','QVariantMap':'QVariantMap'}

h = ['#pragma once','#include <QObject>','#include <QVariant>','#include <QJsonArray>','#include <QMap>','#include <QStringList>','',
     'class QProcess;','class QTimer;','class QEvent;',
     'class Backend : public QObject','{','    Q_OBJECT']
existing = set(signals)
for name, qtype in props:
    cpp = qml_to_cpp.get(qtype, 'QVariant')
    notify = name + 'Changed'
    if notify in existing:
        h.append(f'    Q_PROPERTY({cpp} {name} READ {name} NOTIFY {notify})')
    elif name in ('activeTerminalId', 'terminalCount'):
        h.append(f'    Q_PROPERTY({cpp} {name} READ {name} NOTIFY terminalTabsChanged)')
    else:
        h.append(f'    Q_PROPERTY({cpp} {name} READ {name})')
h += ['','public:','    explicit Backend(QObject *parent = nullptr);']
for name, qtype in props:
    cpp = qml_to_cpp.get(qtype, 'QVariant')
    h.append(f'    {cpp} {name}() const;')
h += ['','signals:']
sig_names = {n+'Changed' for n,_ in props} | set(signals)
# toast 需要 str 參數
for s in sorted(sig_names):
    if s == 'toast':
        h.append('    void toast(const QString &msg);')
    elif s == 'lockRequested':
        h.append('    void lockRequested(int v);')
    elif s == 'reportDone':
        h.append('    void reportDone(const QVariant &v);')
    else:
        h.append(f'    void {s}();')
h += ['','public slots:']
seen = set()
ret_slots = {'hasUnlockPassword':'bool', 'verifyUnlock':'bool', 'selectionText':'QString',
             'seedFromImage':'QString', 'preview':'QVariantList'}
for n, argc in slots:
    if n in seen: continue
    seen.add(n)
    params = ', '.join(f'const QVariant &a{i}' for i in range(int(argc))) if int(argc) else ''
    rt = ret_slots.get(n, 'void')
    h.append(f'    {rt} {n}({params});')
h += ['','protected:',
      '    bool eventFilter(QObject *obj, QEvent *event) override;',
      'private slots:',
      '    void onIdleTimeout();',
      '',
      'private:',
      '    QTimer *m_idleTimer = nullptr;',
      '    void syncIdle();',
      '    void buildColors();','    void buildPresets();','    void reloadAccounts();',
      '    void reloadReports();','    void reloadSessions();','    void reloadCourses();',
      '    void saveSettings();','    void saveRaw(const QJsonArray &arr);',
      '    void saveCourses();','    void saveSessionsJson();',
      '    void courseChanged();','    void noteCourseOpen(const QString &url);',
      '    bool startTerminalWithArgs(const QStringList &args, const QString &label = QString());',
      '    QMap<int, QProcess *> m_termProcs;','    int m_termSeq = 0;',
      '    QVariantMap m_settings;','    QVariantMap m_colors;',
      '    QVariantList m_accounts;','    QVariantList m_reports;',
      '    QVariantList m_sessions;','    QVariantList m_courses;',
      '    QVariantList m_variants;','    QVariantList m_seeds;','    QVariantList m_themes;',
      '    QVariantList m_terminalProfiles;','    QVariantList m_cliStyles;','    QVariantList m_cliFields;',
      '    QVariantList m_preview;','    QString m_previewKey;',
      '    QString m_seed;','    QString m_variant;','    bool m_dark = true;',
      '    qreal m_contrast = 0.0;','    int m_selected = 0;',
      '    QString m_networkSize;','    QString m_reportSource;','    QString m_reportUpdated;',
      '    QString m_reportError;','    bool m_reportBusy = false;',
      '    // 終端狀態','    int m_termActive = 0;','    QVariantList m_termTabs;',
      '    QString m_termText;','    QString m_termStatus;','    bool m_termRunning = false;',
      '    QString m_termProfile;','    QVariantList m_termHistory;',
      '    // 登入狀態','    bool m_loginBusy = false;','    QString m_loginStatus;',
      '};']
(HERE / 'backend.h').write_text('\n'.join(h) + '\n', encoding='utf-8')
print('backend.h written:', len(props), 'props,', len(sig_names), 'signals,', len(seen), 'slots')
