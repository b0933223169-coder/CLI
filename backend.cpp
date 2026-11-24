#include "backend.h"
#include "color_engine.h"
#include "paths.h"
#include "native.h"
#include <memory>
#include <QDirIterator>
#include <QSet>
#include <QFileSystemWatcher>
#include <QNetworkAccessManager>
#include <QNetworkProxyFactory>
#include <QDir>
#include <QPointer>
#include <thread>
#include <QFile>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QColor>
#include <QUrl>
#include <QGuiApplication>
#include <QClipboard>
#include <QDesktopServices>
#include <QStandardPaths>
#include <QDateTime>
#include <QProcess>
#include <QTimer>
#include <QFontMetrics>
#include <QElapsedTimer>
#include <QDebug>
#include <algorithm>
#include <QTimer>
#include <QEvent>
#include <QQmlWebChannel>
#include "qml_pty_bridge.h"
#ifdef Q_OS_WIN
#include <windows.h>
#endif

namespace {
QString DATA;

QString dataDir() {
    if (!DATA.isEmpty()) return DATA;
    QString env = qEnvironmentVariable("COOL_DATA_DIR");
    if (!env.isEmpty()) { DATA = env; return DATA; }
    QString appdata = qEnvironmentVariable("APPDATA");
    if (!appdata.isEmpty()) { DATA = appdata + "/cool"; return DATA; }
    DATA = QDir::homePath() + "/.config/cool";
    return DATA;
}
QString filePath(const QString &name) { return QDir(dataDir()).filePath(name); }
QString resolvePath(const QString &p) {
    QFileInfo fi(p);
    if (fi.isAbsolute()) return p;
    return QDir(dataDir()).filePath(p);
}
QJsonDocument readJson(const QString &name) {
    QFile f(filePath(name));
    if (!f.open(QIODevice::ReadOnly)) return QJsonDocument();
    return QJsonDocument::fromJson(f.readAll());
}
bool writeJson(const QString &name, const QJsonDocument &doc) {
    return Native::atomicWrite(filePath(name), doc.toJson(QJsonDocument::Indented));
}
QJsonArray readArray(const QString &name) {
    QJsonDocument d = readJson(name);
    return d.isArray() ? d.array() : QJsonArray();
}
QJsonObject readObject(const QString &name) {
    QJsonDocument d = readJson(name);
    return d.isObject() ? d.object() : QJsonObject();
}
QString fmtStamp(const QString &s) {
    if (s.isEmpty()) return QStringLiteral("-");
    QString t = s; t.replace(QLatin1Char('T'), QLatin1Char(' '));
    if (t.size() >= 16) t = t.left(16);
    return t;
}
QString nowStamp() {
    return QDateTime::currentDateTime().toString("yyyy-MM-ddTHH:mm:ss");
}
QString exportPath(const QString &name) {
    QDir dir(QDir::currentPath());
    // 匯出到使用者資料夾的 exports/
    QString ex = filePath("exports");
    QDir().mkpath(ex);
    return ex + "/" + name + "-" + QDateTime::currentDateTime().toString("yyyyMMdd-HHmmss");
}
QString emailStem(const QString &email) {
    // 與 Python _sanitize_filename 一致：[^a-zA-Z0-9._-] → _，保留點號
    QString s = email.trimmed();
    for (int i = 0; i < s.size(); ++i) {
        QChar c = s.at(i);
        if (!(c.isLetterOrNumber() || c=='.' || c=='_' || c=='-')) s[i] = QLatin1Char('_');
    }
    return s;
}
} // namespace

Backend::Backend(QObject *parent) : QObject(parent)
{
    m_settings = readObject("settings.json").toVariantMap();
    applyDefaults();       // 全新安裝：套用與桌面版相同的預設（霓虹街景主題、保留紀錄、無頭登入…）
    m_seed = m_settings.value("seed", "#ff583d").toString();
    m_variant = m_settings.value("variant", "expressive").toString();
    m_dark = m_settings.value("dark", false).toBool();
    m_contrast = m_settings.value("contrast", 0.0).toDouble();
    m_termCfg = new TermConfig(this);
    m_nam = new QNetworkAccessManager(this);
    QNetworkProxyFactory::setUseSystemConfiguration(m_settings.value("systemProxy", true).toBool());
    m_sessionsTimer = new QTimer(this);
    m_sessionsTimer->setSingleShot(true); m_sessionsTimer->setInterval(400);
    connect(m_sessionsTimer, &QTimer::timeout, this, &Backend::flushSessions);
    m_retainTimer = new QTimer(this);
    m_retainTimer->setInterval(60000);
    connect(m_retainTimer, &QTimer::timeout, this, &Backend::applyRetention);
    m_retainTimer->start();
    {   // 報表自動更新：依「更新間隔」（分鐘）定時呼叫 cool.py -t
        auto lastAuto = std::make_shared<qint64>(QDateTime::currentMSecsSinceEpoch());
        auto *autoTimer = new QTimer(this);
        autoTimer->setInterval(60000);
        connect(autoTimer, &QTimer::timeout, this, [this, lastAuto] {
            if (!m_settings.value("reportAutoRefresh", false).toBool() || m_reportBusy || m_accounts.isEmpty()) return;
            const qint64 mins = qMax(5, m_settings.value("reportInterval", 60).toInt());
            const qint64 now = QDateTime::currentMSecsSinceEpoch();
            if (now - *lastAuto < mins * 60000) return;
            *lastAuto = now;
            refreshReports();
        });
        autoTimer->start();
    }
    initCliSync();
    reloadAccounts();
    {   // 預設帳號
        QString def = m_settings.value("defaultAccount").toString();
        for (int i = 0; i < m_accounts.size() && !def.isEmpty(); ++i)
            if (m_accounts.at(i).toMap().value("email").toString().compare(def, Qt::CaseInsensitive) == 0) { m_selected = i; break; }
    }
    reloadReports();
    reloadSessions();
    reloadCourses();
    buildPresets();
    buildColors();
    pushTermConfig();
    applyFontFamily();
    applyRetention();
    // 自動鎖定計時器
    m_idleTimer = new QTimer(this);
    m_idleTimer->setSingleShot(true);
    connect(m_idleTimer, &QTimer::timeout, this, &Backend::onIdleTimeout);
    syncIdle();
}

void Backend::applyDefaults() {
    auto def = [this](const char *k, const QVariant &v) { if (!m_settings.contains(QString::fromLatin1(k))) m_settings[QString::fromLatin1(k)] = v; };
    def("seed", "#00e6c3"); def("variant", "tonalSpot"); def("dark", true); def("contrast", 0.0);
    def("themeId", "neon");
    def("defaultLoginMode", "headless"); def("launchTimer", ""); def("launchDelay", ""); def("networkMode", "keep"); def("retention", 1440);
    def("captureRaw", false); def("confirmDestructive", true); def("reportIncludeVideo", true);
    def("terminalCursor", "#52ffe1"); def("terminalText", "#ddfff8"); def("terminalBg", "#06231f");
    def("systemProxy", true); def("sidebarMode", "click"); def("fontSize", 14); def("terminalFontSize", 13);
    def("invertText", false); def("restoreSession", true); def("reportAutoRefresh", false); def("reportInterval", 60); def("uiScale", 100); def("startPage", 0); def("terminalDock", "bottom"); def("reportThreshold", 720); def("showThreshold", true); def("showPractice", true);
    def("showStatusBar", true); def("showNavLabels", true); def("exportFormat", "csv"); def("reportSort", "oldest");
    def("lockMinutes", 10); def("autoLock", false); def("trayOnClose", false); def("terminalFont", "Cascadia Mono");
    def("settingsOrder", QVariantList{ "appearance", "terminal", "workspace", "reports", "cli", "network", "privacy" });
    if (!m_settings.contains("cliColors")) {
        QVariantMap cc{ { "title", "MAGENTA" }, { "titleText", "WHITE" }, { "header", "CYAN" }, { "current", "REVERSE" },
                        { "below", "RED_BG_WHITE" }, { "url", "DIM" }, { "sep", "DIM" } };
        m_settings["cliColors"] = cc;
    }
    // 舊版 networkMode 只有 keep/drop：drop 視為「停用新紀錄」
    if (m_settings.value("networkMode").toString() == "drop") m_settings["networkMode"] = "disabled";
}

// ============ 終端機種類偵測（對應原 Python app 的 _detect_terminals / _terminal_command）============
QString Backend::projectRoot() const {
    QString env = qEnvironmentVariable("COOL_PY_ROOT");
    if (!env.isEmpty() && QFileInfo::exists(QDir(env).filePath("cool.py")))
        return QDir::cleanPath(env);
    QString exeDir = QCoreApplication::applicationDirPath();
    QString proj = QDir(exeDir).filePath("..");   // coolqml-rs 根目錄
    QStringList cands = {
        QDir(proj).filePath("cli"),                          // 隨附的 CLI 原始碼
        QDir(proj).filePath("../cool-qml-caelestia/coolqml"), // 原始位置
        QDir(proj).filePath(".."),                           // 移植到原專案後的父子關係
        exeDir
    };
    for (const QString &c : cands)
        if (QFileInfo::exists(QDir(c).filePath("cool.py"))) return QDir::cleanPath(c);
    return QDir::cleanPath(cands.first());
}

QString Backend::consolePython() const {
    QString p = QStandardPaths::findExecutable(QStringLiteral("python.exe"));
    if (p.isEmpty()) p = QStandardPaths::findExecutable(QStringLiteral("python"));
    return p;
}

void Backend::detectTerminalProfiles() {
    QVariantList found;
    auto add = [&](const QString &id, const QString &label, const QString &icon,
                   const QString &exe, const QString &kind, const QString &distro = QString()) {
        if (exe.isEmpty() || !QFileInfo::exists(exe)) return;
        for (const auto &v : found)
            if (v.toMap().value("path").toString().compare(exe, Qt::CaseInsensitive) == 0) return;
        QVariantMap m;
        m["id"] = id; m["label"] = label; m["icon"] = icon; m["path"] = exe;
        m["kind"] = kind; m["distro"] = distro; m["about"] = QStringLiteral("開啟後自動執行 cool.py");
        found.append(m);
    };

    add(QStringLiteral("pwsh"), QStringLiteral("PowerShell 7"), QStringLiteral("terminal"),
        QStandardPaths::findExecutable(QStringLiteral("pwsh.exe")), QStringLiteral("pwsh"));

    QString root = qEnvironmentVariable("SystemRoot");
    if (root.isEmpty()) root = QStringLiteral("C:/Windows");
    QString ps = QDir(root).filePath(QStringLiteral("System32/WindowsPowerShell/v1.0/powershell.exe"));
    if (!QFileInfo::exists(ps)) ps = QStandardPaths::findExecutable(QStringLiteral("powershell.exe"));
    add(QStringLiteral("powershell"), QStringLiteral("Windows PowerShell"), QStringLiteral("terminal"),
        ps, QStringLiteral("pwsh"));

    QString comspec = qEnvironmentVariable("COMSPEC");
    if (comspec.isEmpty()) comspec = QStandardPaths::findExecutable(QStringLiteral("cmd.exe"));
    add(QStringLiteral("cmd"), QStringLiteral("命令提示字元"), QStringLiteral("code"),
        comspec, QStringLiteral("cmd"));

    QString bash;
    const char *bashPaths[] = {
        "C:/Program Files/Git/bin/bash.exe",
        "C:/Program Files/Git/usr/bin/bash.exe",
        "C:/Program Files (x86)/Git/bin/bash.exe"
    };
    for (const char *bp : bashPaths) if (QFileInfo::exists(QString::fromLatin1(bp))) {
        bash = QString::fromLatin1(bp); break;
    }
    if (bash.isEmpty()) bash = QStandardPaths::findExecutable(QStringLiteral("bash.exe"));
    add(QStringLiteral("gitbash"), QStringLiteral("Git Bash"), QStringLiteral("terminal"),
        bash, QStringLiteral("bash"));

    // 先用偵測得到的快速項目讓「＋」選單立刻可用；WSL 與 Visual Studio 的偵測要啟動外部程式
    // （wsl -l 與 vswhere 各可能等好幾秒），放到背景執行緒做，做完再補進清單。
    m_terminalProfiles = found;

    const QString wsl = QStandardPaths::findExecutable(QStringLiteral("wsl.exe"));
    const QString vswhere = QDir(qEnvironmentVariable("ProgramFiles(x86)", "C:/Program Files (x86)"))
                                .filePath("Microsoft Visual Studio/Installer/vswhere.exe");
    const QString envVs = qEnvironmentVariable("VSINSTALLDIR");
    QPointer<Backend> self(this);
    std::thread([self, wsl, vswhere, envVs, comspec, ps]() {
        QVariantList extra;
        if (!wsl.isEmpty()) {
            QProcess proc;
            proc.start(wsl, QStringList() << QStringLiteral("-l") << QStringLiteral("-q"));
            proc.waitForFinished(3000);
            const QStringList lines = QString::fromLocal8Bit(proc.readAllStandardOutput()).split('\n', Qt::SkipEmptyParts);
            for (QString l : lines) {
                l = l.trimmed(); l.remove('\r');
                // wsl 在 Windows 上常輸出 UTF-16，含空字元：去掉
                l.remove(QChar(0));
                if (l.isEmpty()) continue;
                QVariantMap m;
                m["id"] = "wsl"; m["label"] = QStringLiteral("WSL · ") + l; m["icon"] = "terminal"; m["path"] = wsl;
                m["kind"] = "wsl"; m["distro"] = l; m["about"] = QStringLiteral("開啟後自動執行 cool.py");
                extra.append(m);
                break;
            }
        }
        QString vsInst;
        if (QFileInfo::exists(vswhere)) {
            QProcess vp;
            vp.start(vswhere, QStringList() << "-latest" << "-products" << "*" << "-property" << "installationPath");
            vp.waitForFinished(4000);
            vsInst = QString::fromLocal8Bit(vp.readAllStandardOutput()).trimmed().section('\n', 0, 0).trimmed();
        }
        if (vsInst.isEmpty()) vsInst = envVs;
        while (vsInst.endsWith('\\') || vsInst.endsWith('/')) vsInst.chop(1);
        if (!vsInst.isEmpty() && QFileInfo::exists(vsInst + "/Common7/Tools/VsDevCmd.bat")) {
            QVariantMap c;
            c["id"] = "vs-cmd"; c["label"] = QStringLiteral("Developer Command Prompt for VS"); c["icon"] = "code";
            c["path"] = comspec; c["kind"] = "cmd"; c["distro"] = QString(); c["vsdev"] = vsInst;
            c["about"] = QStringLiteral("載入 Visual Studio 開發環境後自動執行 cool.py");
            extra.append(c);
            QString psExe = QStandardPaths::findExecutable(QStringLiteral("pwsh.exe"));
            if (psExe.isEmpty()) psExe = ps;
            QVariantMap d;
            d["id"] = "vs-ps"; d["label"] = QStringLiteral("Developer PowerShell for VS"); d["icon"] = "terminal";
            d["path"] = psExe; d["kind"] = "pwsh"; d["distro"] = QString(); d["vsdev"] = vsInst;
            d["about"] = QStringLiteral("載入 Visual Studio 開發環境後自動執行 cool.py");
            extra.append(d);
        }
        if (extra.isEmpty() || !self) return;
        QMetaObject::invokeMethod(self.data(), [self, extra]() {
            if (!self) return;
            for (const auto &v : extra) {
                bool dup = false;
                for (const auto &e : self->m_terminalProfiles)
                    if (e.toMap().value("id").toString() == v.toMap().value("id").toString()) { dup = true; break; }
                if (!dup) self->m_terminalProfiles.append(v);
            }
            emit self->terminalProfilesChanged();
        }, Qt::QueuedConnection);
    }).detach();
}

QPair<QStringList, QString> Backend::terminalCommand(const QString &profileId,
                                                     const QStringList &extra) {
    QString path, kind, distro, vsdev;
    for (const auto &v : m_terminalProfiles) {
        QVariantMap m = v.toMap();
        if (m.value("id").toString() == profileId) {
            path = m.value("path").toString();
            kind = m.value("kind").toString();
            distro = m.value("distro").toString();
            vsdev = m.value("vsdev").toString();
            break;
        }
    }
    if (path.isEmpty() && !m_terminalProfiles.isEmpty()) {
        QVariantMap m = m_terminalProfiles.first().toMap();
        path = m.value("path").toString();
        kind = m.value("kind").toString();
        distro = m.value("distro").toString();
    }
    QString py = consolePython();
    QString cool = QDir(projectRoot()).filePath(QStringLiteral("cool.py"));
    QString tail;
    for (const QString &a : extra) tail += QStringLiteral(" '") + a + QStringLiteral("'");

    QStringList argv;
    QString boot;
    if (kind == QStringLiteral("cmd")) {
        // 直接把指令放 cmdline（boot 寫入會被修正版 ConPTY 吞掉輸出）
        QString inner = QStringLiteral("chcp 65001>nul && \"%1\" \"%2\"%3").arg(py, cool, tail);
        if (!vsdev.isEmpty())
            inner = QStringLiteral("call \"%1/Common7/Tools/VsDevCmd.bat\" -arch=x64 -host_arch=x64 >nul && ").arg(QDir::toNativeSeparators(vsdev)) + inner;
        argv << QStringLiteral("/k") << inner;
    } else if (kind == QStringLiteral("bash")) {
        QString p = py; p.replace('\\', '/');
        QString c = cool; c.replace('\\', '/');
        QString inner = QStringLiteral("\"%1\" \"%2\"%3; exec bash -i").arg(p, c, tail);
        argv << QStringLiteral("--login") << QStringLiteral("-i") << QStringLiteral("-c") << inner;
    } else if (kind == QStringLiteral("wsl")) {
        auto wslPath = [](const QString &in) {
            QString s = in; s.replace('\\', '/');
            if (s.size() > 2 && s[1] == ':')
                return QStringLiteral("/mnt/") + s[0].toLower() + s.mid(2);
            return s;
        };
        QString inner = QStringLiteral("\"%1\" \"%2\"%3; exec bash -i")
                            .arg(wslPath(py), wslPath(cool), tail);
        argv << QStringLiteral("-d") << distro << QStringLiteral("--cd") << projectRoot()
             << QStringLiteral("--") << QStringLiteral("bash") << QStringLiteral("-lic") << inner;
    } else { // pwsh / powershell
        QString cmd = QStringLiteral("& '%1' '%2'%3").arg(py, cool, tail);
        if (!vsdev.isEmpty()) {
            QString vp = QDir::toNativeSeparators(vsdev);
            cmd = QStringLiteral("Import-Module '%1\\Common7\\Tools\\Microsoft.VisualStudio.DevShell.dll'; "
                                 "Enter-VsDevShell -VsInstallPath '%1' -SkipAutomaticLocation -DevCmdArguments '-arch=x64'; ").arg(vp) + cmd;
        }
        argv << QStringLiteral("-NoLogo") << QStringLiteral("-NoExit") << QStringLiteral("-Command") << cmd;
    }
    QStringList full; full << path << argv;
    return qMakePair(full, boot);
}

// ============ 資料載入 ============
void Backend::buildPresets() {
    // variants
    QVariantList vars;
    const char *vk[][2] = {
        {"tonalSpot","Tonal Spot"},{"vibrant","Vibrant"},{"expressive","Expressive"},
        {"neutral","Neutral"},{"monochrome","Monochrome"},{"fidelity","Fidelity"},
        {"content","Content"},{"rainbow","Rainbow"},{"fruitSalad","Fruit Salad"}
    };
    for (auto &v : vk) { QVariantMap m; m["key"]=QString::fromLatin1(v[0]); m["name"]=QString::fromLatin1(v[1]); vars.append(m); }
    m_variants = vars;
    // seeds
    QVariantList seeds;
    const char *seedArr[] = {"#ff583d","#6750a4","#00639b","#3f6212","#9c4146","#7d5260","#415f91","#006a6a"};
    for (auto &s : seedArr) seeds.append(QString::fromLatin1(s));
    m_seeds = seeds;
    // themes：24 組（與桌面版 colorThemes.ts 相同）
    QVariantList themes;
    struct TP { const char *id, *name, *group; bool dark; const char *bg, *surface, *accent, *text, *tCursor, *tText, *tBg; };
    static const TP tp[] = {
        {u8"ember",u8"熔岩赤焰",u8"暖色",true,"#24100f","#51231b","#ff583d","#fff0e8","#ff795b","#ffe5dc","#2b100e"},
        {u8"terracotta",u8"陶土夕陽",u8"暖色",false,"#f2d0c2","#fbe8df","#b74421","#37170d","#ff906b","#fff0e8","#32150f"},
        {u8"honey",u8"金箔蜂蜜",u8"暖色",true,"#241d0b","#51400f","#ffc928","#fff7d6","#ffdc58","#fff3c4","#241b08"},
        {u8"rosewood",u8"莓紅酒窖",u8"暖色",false,"#f0cad8","#f9e2eb","#b51f55","#35101e","#ff6b9a","#ffe7ee","#2b101c"},
        {u8"saffron",u8"藏紅花金",u8"暖色",true,"#261a08","#503008","#ff9e00","#fff0d1","#ffc04d","#fff0cf","#241605"},
        {u8"peach",u8"珊瑚蜜桃",u8"暖色",false,"#ffd8cf","#ffebe6","#e84b78","#3b1020","#ff89a9","#fff0f4","#2c101a"},
        {u8"ocean",u8"深洋藍",u8"冷色",true,"#071b2a","#123f5b","#20b8f0","#e5f8ff","#64d5ff","#dff7ff","#071b2a"},
        {u8"arctic",u8"冰川青",u8"冷色",false,"#c5e8ed","#e2f4f5","#007f91","#082b31","#27d3df","#ddffff","#082328"},
        {u8"lavender",u8"紫水晶",u8"冷色",true,"#1a1030","#39265d","#b88cff","#f4eaff","#d0afff","#f2e8ff","#1a1030"},
        {u8"indigo",u8"靛藍電波",u8"冷色",false,"#cdd5ff","#e7eaff","#354fce","#111c4a","#8297ff","#e9edff","#111936"},
        {u8"silverblue",u8"鋼鐵銀藍",u8"冷色",true,"#101a27","#2b4665","#a9c8e8","#e9f2fb","#c4e0ff","#e5f0ff","#101a27"},
        {u8"glacier",u8"薄荷極光",u8"冷色",false,"#c5eee2","#e1f7ef","#00a982","#07352b","#50f0bd","#ddfff1","#09271f"},
        {u8"forest",u8"松林深處",u8"自然",true,"#0b2113","#1c4b2d","#47c76f","#e6ffe9","#7bea91","#e4ffe8","#0d2113"},
        {u8"sage",u8"鼠尾草灰綠",u8"自然",false,"#dfe8c8","#eff4df","#627d35","#202d12","#badb71","#f0f7dc","#202719"},
        {u8"moss",u8"青苔螢光",u8"自然",true,"#1c2409","#40520e","#b5d92b","#f5ffd9","#d5f56b","#f1ffd1","#1a2108"},
        {u8"bamboo",u8"竹影墨青",u8"自然",false,"#c5e9dc","#e2f5ec","#007d63","#082c25","#47d6aa","#dffff3","#09251e"},
        {u8"wildflower",u8"野花紫羅蘭",u8"自然",true,"#28102d","#56245d","#df70e8","#ffebff","#f2a3f4","#ffebff","#28112b"},
        {u8"earth",u8"赤陶大地",u8"自然",false,"#e9d2b6","#f6e8d5","#80552f","#30200f","#d7a667","#fff0d8","#2b2016"},
        {u8"candy",u8"糖果霓彩",u8"鮮明",true,"#2d0b28","#5b1950","#ff36bd","#ffe9fa","#ff78d6","#ffe8f8","#2a0c27"},
        {u8"coral",u8"亮珊瑚",u8"鮮明",false,"#ffd2cb","#ffebe7","#ed382e","#3d0d0b","#ff8276","#fff0eb","#2c100f"},
        {u8"citrus",u8"青檸氣泡",u8"鮮明",true,"#1b2306","#48560b","#9de600","#f4ffd9","#c9ff53","#f0ffd7","#182005"},
        {u8"electric",u8"電光藍紫",u8"鮮明",false,"#d8ccff","#ede7ff","#6e36e8","#1e1044","#aa83ff","#f0e8ff","#1b1035"},
        {u8"neon",u8"霓虹街景",u8"鮮明",true,"#06231f","#0f5145","#00e6c3","#ddfff8","#52ffe1","#ddfff8","#06231f"},
        {u8"monochrome",u8"黑白鉻影",u8"鮮明",false,"#d9dee4","#eef0f3","#313943","#171b20","#e1e8f0","#f1f4f8","#171b20"}
    };
    for (const auto &t : tp) {
        QVariantMap m;
        m["id"] = QString::fromUtf8(reinterpret_cast<const char *>(t.id));
        m["name"] = QString::fromUtf8(reinterpret_cast<const char *>(t.name));
        m["group"] = QString::fromUtf8(reinterpret_cast<const char *>(t.group));
        m["seed"] = QString::fromLatin1(t.accent); m["dark"] = t.dark; m["variant"] = "tonalSpot";
        m["bg"] = QString::fromLatin1(t.bg); m["surface"] = QString::fromLatin1(t.surface);
        m["text"] = QString::fromLatin1(t.text);
        m["termCursor"] = QString::fromLatin1(t.tCursor); m["termText"] = QString::fromLatin1(t.tText); m["termBg"] = QString::fromLatin1(t.tBg);
        themes.append(m);
    }
    m_themes = themes;
    // terminal profiles：動態偵測本機實際存在的終端機（与原 Python app 一致）
    detectTerminalProfiles();
    // CLI 報表配色：與 CLI colors.py 相同的 37 種預設樣式（fg/bg 僅用於預覽）
    QVariantList styles;
    struct CS { const char *key, *name, *fg, *bg; };
    static const CS cs[] = {
        {"GREEN","綠","#23d18b",nullptr},{"RED","紅","#f14c4c",nullptr},{"YELLOW","黃","#f5f543",nullptr},
        {"BLUE","藍","#3b8eea",nullptr},{"CYAN","青","#29b8db",nullptr},{"MAGENTA","洋紅","#d670d6",nullptr},
        {"WHITE","白","#ffffff",nullptr},{"DIM","暗","#8b949e",nullptr},{"RESET","預設","#d7dde5",nullptr},
        {"RED_BG","紅底","#d7dde5","#cd3131"},{"RED_BG_WHITE","紅底白字","#ffffff","#cd3131"},
        {"YELLOW_BG_WHITE","黃底白字","#ffffff","#b58900"},{"BLUE_BG_WHITE","藍底白字","#ffffff","#2472c8"},
        {"MAGENTA_BG_WHITE","洋紅底白字","#ffffff","#bc3fbc"},{"CYAN_BG_WHITE","青底白字","#ffffff","#11a8cd"},
        {"GREEN_BG_WHITE","綠底白字","#ffffff","#0dbc79"},
        {"ORANGE","橘","#ff8700",nullptr},{"ORANGE_BG","橘底","#101418","#ff8700"},
        {"PURPLE","紫","#af5fff",nullptr},{"PURPLE_BG","紫底","#101418","#af5fff"},
        {"PINK","粉","#ff87ff",nullptr},{"PINK_BG","粉底","#101418","#ff87ff"},
        {"LIME","萊姆","#afd700",nullptr},{"LIME_BG","萊姆底","#101418","#afd700"},
        {"TEAL","水鴨","#00afaf",nullptr},{"TEAL_BG","水鴨底","#101418","#00afaf"},
        {"GOLD","金","#ffd700",nullptr},{"GOLD_BG","金底","#101418","#ffd700"},
        {"SKY","天藍","#87d7ff",nullptr},{"SKY_BG","天藍底","#101418","#87d7ff"},
        {"BROWN","棕","#af5f00",nullptr},{"BROWN_BG","棕底","#ffffff","#af5f00"},
        {"GRAY","灰","#8a8a8a",nullptr},{"GRAY_BG","灰底","#101418","#8a8a8a"},
        {"BLACK","黑","#2b2b2b",nullptr},{"BLACK_BG","黑底","#ffffff","#000000"},
        {"REVERSE","終端反色","#101418","#d7dde5"}
    };
    for (const auto &s : cs) {
        QVariantMap m; m["key"] = QString::fromLatin1(s.key); m["name"] = QString::fromUtf8(s.name);
        m["fg"] = QString::fromLatin1(s.fg); m["bg"] = s.bg ? QVariant(QString::fromLatin1(s.bg)) : QVariant();
        styles.append(m);
    }
    m_cliStyles = styles;
    QVariantList fields;
    struct CF { const char *key, *label, *desc, *def; };
    static const CF cf[] = {
        {"title","標題外框","「學習時間」標題框線與裝飾","MAGENTA"},
        {"titleText","標題文字","標題及帳號名稱","WHITE"},
        {"header","表頭","月份、停留、影片與練習欄位名稱","CYAN"},
        {"current","當月列","本月已達標的整列重點標示","REVERSE"},
        {"below","未達標列","未達門檻月份的警示文字","RED_BG_WHITE"},
        {"url","網址列","報表來源網址與帳號提示","DIM"},
        {"sep","分隔線","報表表格的水平分隔線","DIM"}
    };
    for (const auto &f : cf) {
        QVariantMap m; m["key"] = QString::fromLatin1(f.key); m["label"] = QString::fromUtf8(f.label);
        m["desc"] = QString::fromUtf8(f.desc); m["default"] = QString::fromLatin1(f.def);
        fields.append(m);
    }
    m_cliFields = fields;
}

void Backend::buildColors() {
    // 由 seed（主色）推導整套配色；預設主題另外指定介面背景／卡片／文字色，讓每組風格的底色都明顯不同
    m_colors = ColorEngine::generate(m_seed, m_variant, m_dark);
    const QString tid = m_settings.value("themeId").toString();
    for (const auto &v : m_themes) {
        QVariantMap t = v.toMap();
        if (t.value("id").toString() != tid) continue;
        if (QColor(t.value("seed").toString()) != QColor(m_seed)) break;     // 使用者已改主色 → 視為自訂
        QColor bg(t.value("bg").toString()), sf(t.value("surface").toString()), tx(t.value("text").toString());
        auto mix = [](const QColor &a, const QColor &b, qreal k) {
            return QColor::fromRgbF(a.redF() * (1 - k) + b.redF() * k, a.greenF() * (1 - k) + b.greenF() * k, a.blueF() * (1 - k) + b.blueF() * k);
        };
        bool dark = t.value("dark").toBool();
        QColor lowest = dark ? bg.darker(115) : mix(bg, QColor("#ffffff"), 0.25);
        m_colors["background"] = bg.name(); m_colors["surface"] = bg.name(); m_colors["surfaceDim"] = bg.name();
        m_colors["surfaceBright"] = mix(bg, sf, 0.9).name();
        m_colors["surfaceContainerLowest"] = lowest.name();
        m_colors["surfaceContainerLow"] = mix(bg, sf, 0.30).name();
        m_colors["surfaceContainer"] = mix(bg, sf, 0.55).name();
        m_colors["surfaceContainerHigh"] = mix(bg, sf, 0.80).name();
        m_colors["surfaceContainerHighest"] = sf.name();
        m_colors["surfaceVariant"] = mix(bg, sf, 0.80).name();
        m_colors["onSurface"] = tx.name(); m_colors["onBackground"] = tx.name();
        m_colors["onSurfaceVariant"] = mix(tx, bg, 0.28).name();
        m_colors["outlineVariant"] = mix(bg, tx, 0.20).name();
        m_colors["outline"] = mix(bg, tx, 0.45).name();
        m_colors["inverseSurface"] = tx.name(); m_colors["inverseOnSurface"] = bg.name();
        // 主色直接取自主題強調色，只在對比不足時微調明度（保留主題個性，同時保證按鈕／圖示看得清楚）
        QColor acc(t.value("seed").toString());
        QColor prim = ColorEngine::ensureContrast(ColorEngine::ensureContrast(acc, bg, 3.2), sf, 3.2);
        m_colors["primary"] = prim.name(); m_colors["surfaceTint"] = prim.name();
        m_colors["onPrimary"] = ColorEngine::ensureContrast(ColorEngine::onFor(prim), prim, 4.5).name();
        QColor pc = mix(bg, acc, dark ? 0.42 : 0.26);
        m_colors["primaryContainer"] = pc.name();
        m_colors["onPrimaryContainer"] = ColorEngine::ensureContrast(tx, pc, 7.0).name();
        m_colors["inversePrimary"] = ColorEngine::ensureContrast(acc, tx, 3.0).name();
        break;
    }
    // 反轉介面文字色：文字改用「互補色相」（色相轉 180°、彩度略增），明度自動調到與所有表面至少 7:1，
    // 所以一定看得清楚；背景、卡片與終端配色完全不變。關掉就回到原本文字色。
    if (m_settings.value("invertText", false).toBool()) {
        double L, C, h;
        ColorEngine::toOklch(QColor(m_colors.value("onSurface").toString()), L, C, h);
        const double hue = std::fmod(h + 180.0, 360.0);
        const double chroma = std::clamp(C * 1.6 + 0.04, 0.05, 0.11);
        QColor txt = ColorEngine::oklch(m_dark ? 0.92 : 0.25, chroma, hue);
        const QColor surf(m_colors.value("surface").toString()), hi(m_colors.value("surfaceContainerHighest").toString());
        txt = ColorEngine::ensureContrast(ColorEngine::ensureContrast(txt, surf, 7.0), hi, 7.0);
        QColor soft = ColorEngine::ensureContrast(ColorEngine::oklch(m_dark ? 0.80 : 0.40, chroma * 0.8, hue), hi, 4.6);
        m_colors["onSurface"] = txt.name(); m_colors["onBackground"] = txt.name();
        m_colors["onSurfaceVariant"] = soft.name();
    }
    // 統一收尾（自訂與預設主題一致）：對比等級 → 拉回 0 就完全還原
    ColorEngine::applyContrast(m_colors, m_contrast, m_dark);
}

// (已改為原生實作，見 backend_native.inc: reloadAccounts)
void Backend::reloadReports() {
    QVariantList out;
    QJsonObject accounts = readObject("reports.json").value("accounts").toObject();
    QString email;
    if (m_selected >= 0 && m_selected < m_accounts.size())
        email = m_accounts.at(m_selected).toMap().value("email").toString();
    QJsonObject entry = accounts.value(email).toObject();
    // 這個帳號還沒抓過報表 → 顯示空，絕對不能拿別人的帳號資料
    QJsonArray reps = entry.value("reports").toArray();
    for (const auto &v : reps) {
        QJsonObject r = v.toObject();
        QVariantMap m;
        m["month"] = r.value("month").toString();
        m["platform"] = r.value("platform").toInt();
        m["video"] = r.value("video").toInt();
        m["practice"] = r.value("practice").toInt();
        out.append(m);
    }
    m_reports = out;
    m_reportSource = entry.value("url").toString();
    m_reportUpdated = entry.value("fetchedAt").toString();
    const QString &sortKey = m_settings.value("reportSort").toString();
    if (sortKey == "newest") std::reverse(out.begin(), out.end());
    m_reports = out;
}

// (已改為原生實作，見 backend_native.inc: reloadSessions)
// (已改為原生實作，見 backend_native.inc: reloadCourses)
void Backend::saveSettings() {
    QJsonObject obj = QJsonObject::fromVariantMap(m_settings);
    writeJson("settings.json", QJsonDocument(obj));
}

void Backend::saveRaw(const QJsonArray &arr) {
    writeJson("accounts.json", QJsonDocument(arr));
}

// (已改為原生實作，見 backend_native.inc: saveCourses)
// (已改為原生實作，見 backend_native.inc: saveSessionsJson)
// ============ Getter ============
QString Backend::dataDir() const { return ::dataDir(); }
QString Backend::homeDir() const { return QDir::homePath(); }
QString Backend::exportDir() const { return filePath("exports"); }
QString Backend::settingsFile() const { return filePath("settings.json"); }
QString Backend::colorsFile() const { return filePath("colors.json"); }
QString Backend::coolScript() const { return QStringLiteral("cool.py"); }
QVariantMap Backend::settings() const { return m_settings; }
QVariantMap Backend::colors() const { return m_colors; }
QString Backend::seed() const { return m_seed; }
QString Backend::variant() const { return m_variant; }
bool Backend::dark() const { return m_dark; }
qreal Backend::contrast() const { return m_contrast; }
QVariantList Backend::accounts() const { return m_accounts; }
QVariantList Backend::reports() const { return m_reports; }
QVariantList Backend::sessions() const { return m_sessions; }
QVariantList Backend::courses() const { return m_courses; }
int Backend::selected() const { return m_selected; }
QString Backend::networkSize() const { return m_networkSize; }
QString Backend::cacheSize() const { return QStringLiteral("-"); }
QString Backend::defaultTerminal() const { return m_settings.value("defaultTerminal","powershell").toString(); }
QString Backend::defaultTerminalProfile() const { return defaultTerminal(); }
QString Backend::loginMode() const { return m_settings.value("defaultLoginMode","headless").toString(); }
bool Backend::trayAvailable() const { return true; }
QString Backend::encryptionStatus() const { return QStringLiteral("Windows DPAPI 已啟用"); }
QString Backend::reportUpdated() const { return m_reportUpdated; }
QString Backend::reportSource() const { return m_reportSource; }
QString Backend::reportError() const { return m_reportError; }
bool Backend::reportBusy() const { return m_reportBusy; }
QVariantList Backend::variants() const { return m_variants; }
QVariantList Backend::seeds() const { return m_seeds; }
QVariantList Backend::themes() const { return m_themes; }
QVariantList Backend::terminalProfiles() const { return m_terminalProfiles; }
QVariantList Backend::cliStyles() const { return m_cliStyles; }
QVariantList Backend::cliFields() const { return m_cliFields; }
int Backend::activeTerminalId() const { return m_termActive; }
QVariantList Backend::terminalTabs() const { return m_termTabs; }
int Backend::terminalCount() const { return m_termTabs.size(); }
QString Backend::terminalText() const { return m_termText; }
QString Backend::terminalStatus() const { return m_termStatus; }
bool Backend::terminalRunning() const { return m_termRunning; }
QString Backend::terminalProfile() const { return m_termProfile; }
QVariantList Backend::terminalHistory() const { return m_termHistory; }
bool Backend::loginBusy() const { return m_loginBusy; }
QString Backend::loginStatus() const { return m_loginStatus; }
QString Backend::debugSection() const { return qEnvironmentVariable("COOL_DEBUG_SECTION"); }

// 桌面程式實際使用的 cool.py 來源：路徑、版本、CLI 原始碼的最後更新時間（確認有沒有套用最新版）
QString Backend::cliInfo() const {
    const QString dir = cliDir();
    const QString root = projectRoot();
    QDateTime newest;
    const auto files = QDir(root).entryInfoList({ QStringLiteral("*.py") }, QDir::Files);
    for (const QFileInfo &f : files) if (!newest.isValid() || f.lastModified() > newest) newest = f.lastModified();
    const auto cmds = QDir(root + QStringLiteral("/commands")).entryInfoList({ QStringLiteral("*.py") }, QDir::Files);
    for (const QFileInfo &f : cmds) if (!newest.isValid() || f.lastModified() > newest) newest = f.lastModified();
    QString ver;
    QFile vf(root + QStringLiteral("/version.py"));
    if (vf.open(QIODevice::ReadOnly)) {
        const QString t = QString::fromUtf8(vf.readAll());
        const int i = t.indexOf(QStringLiteral("VERSION = \""));
        if (i >= 0) ver = t.mid(i + 11, t.indexOf(QLatin1Char('"'), i + 11) - i - 11);
    }
    Q_UNUSED(dir);
    return QStringLiteral("v%1 · 更新於 %2 · %3").arg(ver.isEmpty() ? QStringLiteral("?") : ver,
        newest.isValid() ? newest.toString(QStringLiteral("MM-dd HH:mm")) : QStringLiteral("?"), QDir::toNativeSeparators(root));
}


// ============ Slots：選擇 / 報表 ============
void Backend::select(const QVariant &a0) {
    int i = a0.toInt();
    if (i >= 0 && i < m_accounts.size()) {
        m_selected = i;
        emit selectedChanged();
        reloadReports();
        emit reportsChanged();
        emit reportStateChanged();
    }
}
// (已改為原生實作，見 backend_native.inc: refreshReports)
// ============ Slots：帳號 ============
// (已改為原生實作，見 backend_native.inc: addAccount)
// (已改為原生實作，見 backend_native.inc: renameAccount)
// (已改為原生實作，見 backend_native.inc: removeAccount)
// (已改為原生實作，見 backend_native.inc: removeAllAccounts)
// (已改為原生實作，見 backend_native.inc: checkCookie)
// ============ Slots：課程 ============
void Backend::courseChanged() {
    saveCourses();
    for (int i = 0; i < m_courses.size(); ++i) {
        QVariantMap m = m_courses.at(i).toMap(); m["id"] = i+1; m_courses[i] = m;
    }
    emit coursesChanged();
}
// (已改為原生實作，見 backend_native.inc: addCourse)
void Backend::removeCourse(const QVariant &a0) {
    int i = a0.toInt();
    if (i >= 0 && i < m_courses.size()) { m_courses.removeAt(i); courseChanged(); emit toast(QStringLiteral("已移除網址")); }
}
// (已改為原生實作，見 backend_native.inc: setCourseCategory)
void Backend::removeCategory(const QVariant &a0) {
    QString cat = a0.toString();
    QVariantList keep;
    int removed = 0;
    for (const auto &v : m_courses) {
        if (v.toMap().value("category").toString() == cat) ++removed; else keep.append(v);
    }
    m_courses = keep; courseChanged();
    emit toast(QStringLiteral("已刪除分類「") + cat + QStringLiteral("」與 ") + QString::number(removed) + QStringLiteral(" 個連結"));
}
void Backend::renameCategory(const QVariant &a0, const QVariant &a1) {
    QString old = a0.toString(), nw = a1.toString().trimmed();
    if (nw.isEmpty() || nw == old) return;
    for (auto &v : m_courses) {
        QVariantMap m = v.toMap();
        if (m.value("category").toString() == old) {
            m["category"] = nw;
            if (m.value("alias").toString() == old) m["alias"] = nw;
            v = m;
        }
    }
    courseChanged(); emit toast(QStringLiteral("分類已改名為「") + nw + QStringLiteral("」"));
}
void Backend::openCourseMenu() { emit toast(startTerminalWithArgs(defaultTerminal(), QStringList() << QStringLiteral("-u"), QStringLiteral("課程")) ? QStringLiteral("已在內嵌終端機開啟 cool.py 課程選單") : QStringLiteral("無法啟動內嵌終端機")); }
void Backend::openReportCli() { emit toast(startTerminalWithArgs(defaultTerminal(), QStringList() << QStringLiteral("-t"), QStringLiteral("學習時間")) ? QStringLiteral("已在內嵌終端機用 cool.py 取得學習時間") : QStringLiteral("無法啟動內嵌終端機")); }

#include "color_engine.h"

// ============ Slots：網路紀錄 ============
// (已改為原生實作，見 backend_native.inc: stopSession)
// (已改為原生實作，見 backend_native.inc: deleteSession)
// (已改為原生實作，見 backend_native.inc: deleteSessions)
// (已改為原生實作，見 backend_native.inc: clearSessions)
// ============ Slots：設定 ============
void Backend::updateSetting(const QVariant &a0, const QVariant &a1) {
    QString key = a0.toString();
    m_settings[key] = a1;
    saveSettings();
    if (key == "terminalCursor" || key == "terminalText" || key == "terminalBg" || key == "cliColors") writeCliColors();
    if (key == "networkMode" || key == "retention") applyRetention();
    if (key == "systemProxy") QNetworkProxyFactory::setUseSystemConfiguration(a1.toBool());
    if (key == "invertText") { buildColors(); emit colorsChanged(); }
    if (key == "fontFamily") applyFontFamily();
    pushTermConfig();
    if (key == "seed" || key == "variant" || key == "dark" || key == "contrast") {
        m_seed = m_settings.value("seed").toString();
        m_variant = m_settings.value("variant").toString();
        m_dark = m_settings.value("dark").toBool();
        m_contrast = m_settings.value("contrast").toDouble();
        buildColors(); emit colorsChanged(); emit schemeChanged();
    }
    if (key == "autoLock" || key == "lockMinutes") syncIdle();
    if (key == "defaultAccount" && !a1.toString().isEmpty()) {
        for (int i = 0; i < m_accounts.size(); ++i) {
            if (m_accounts.at(i).toMap().value("email").toString().compare(a1.toString(), Qt::CaseInsensitive) == 0) {
                m_selected = i; emit selectedChanged(); reloadReports(); emit reportsChanged(); emit reportStateChanged(); break;
            }
        }
    }
    emit settingsChanged();
}
void Backend::applyTheme(const QVariant &a0, const QVariant &a1, const QVariant &a2) {
    QString id = a0.toString(), seed = a1.toString(); bool dark = a2.toBool();
    m_settings["themeId"] = id; m_settings["presetBase"] = id; m_settings["seed"] = seed; m_settings["dark"] = dark;
    for (const auto &v : m_themes) {
        QVariantMap t = v.toMap();
        if (t.value("id").toString() == id) {
            m_settings["variant"] = t.value("variant");
            // 套用主題同步更新終端配色（並寫入 CLI 的 colors.json）
            m_settings["terminalCursor"] = t.value("termCursor"); m_settings["terminalText"] = t.value("termText");
            m_settings["terminalBg"] = t.value("termBg");
            break;
        }
    }
    m_seed = seed; m_dark = dark;
    m_variant = m_settings.value("variant", m_variant).toString();
    buildColors(); saveSettings(); writeCliColors(); pushTermConfig();
    emit colorsChanged(); emit schemeChanged(); emit settingsChanged();
}
void Backend::setScheme(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3) {
    const QString seed = a0.toString(), variant = a1.toString();
    const bool dark = a2.toBool();
    const bool sameLook = QColor(seed) == QColor(m_seed) && variant == m_variant && dark == m_dark;   // 只動了對比
    m_seed = seed; m_variant = variant; m_dark = dark; m_contrast = a3.toDouble();
    m_settings["seed"] = m_seed; m_settings["variant"] = m_variant;
    m_settings["dark"] = m_dark; m_settings["contrast"] = m_contrast;
    if (!sameLook) {
        // 離開預設主題時記住它；日後把種子色／變體／深淺調回原樣，就自動回到該預設主題
        const QString cur = m_settings.value("themeId").toString();
        if (!cur.isEmpty() && cur != "custom") m_settings["presetBase"] = cur;
        const QString base = m_settings.value("presetBase").toString();
        QString restore;
        for (const auto &v : m_themes) {
            QVariantMap t = v.toMap();
            if (t.value("id").toString() == base && QColor(t.value("seed").toString()) == QColor(seed)
                && t.value("variant").toString() == variant && t.value("dark").toBool() == dark) { restore = base; break; }
        }
        m_settings["themeId"] = restore.isEmpty() ? QStringLiteral("custom") : restore;
        if (!restore.isEmpty()) {              // 還原預設主題時終端配色也一併還原
            for (const auto &v : m_themes) {
                QVariantMap t = v.toMap();
                if (t.value("id").toString() == restore) {
                    m_settings["terminalCursor"] = t.value("termCursor"); m_settings["terminalText"] = t.value("termText");
                    m_settings["terminalBg"] = t.value("termBg");
                }
            }
            writeCliColors(); pushTermConfig();
        }
    }
    buildColors(); saveSettings(); emit colorsChanged(); emit schemeChanged(); emit settingsChanged();
}
void Backend::saveWindowGeometry(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3) {
    if (m_settings.value("rememberWindow", true).toBool() == false) return;
    m_settings["windowWidth"] = a0.toInt(); m_settings["windowHeight"] = a1.toInt();
    m_settings["windowX"] = a2.toInt(); m_settings["windowY"] = a3.toInt();
    saveSettings();
}

// ============ Slots：色彩 ============
QString Backend::seedFromImage(const QVariant &a0) {
    QString path = a0.toString();
    path.remove("file://");
    if (path.isEmpty() || !QFile::exists(path)) { emit toast(QStringLiteral("找不到圖片")); return QString(); }
    QString seed = ColorEngine::seedFromImage(path);
    if (!seed.isEmpty()) { emit toast(QStringLiteral("已從圖片取色：") + seed); return seed; }
    emit toast(QStringLiteral("無法從圖片取色"));
    return QString();
}

QVariantList Backend::preview(const QVariant &a0, const QVariant &a1, const QVariant &a2) {
    QString seed = a0.toString(), variant = a1.toString(); bool dark = a2.toBool();
    QString key = seed + "|" + variant + "|" + (dark ? "1" : "0");
    if (m_previewKey == key) return m_preview;
    m_preview = ColorEngine::preview(seed, variant, dark);
    m_previewKey = key;
    return m_preview;
}

// ============ Slots：鎖定 ============
void Backend::resetIdle() {
    if (m_settings.value("autoLock", false).toBool() && m_idleTimer) {
        m_idleTimer->start();
    }
}
// (已改為原生實作，見 backend_native.inc: hasUnlockPassword)
// (已改為原生實作，見 backend_native.inc: verifyUnlock)
// ============ Slots：頭像 ============
void Backend::refreshAvatar(const QVariant &a0) {
    // Google 頭像只能在登入當下取得（CLI 登入完成後瀏覽器仍帶著 Google 登入狀態）；
    // 所以這個按鈕會用已保存的密碼重新登入一次，登入時 cool.py 會順便下載頭像。
    emit toast(QStringLiteral("正在登入以取得 Google 頭像，約需 30–60 秒，完成後會自動更新…"));
    loginAccount(a0, QStringLiteral("headless"));
}
void Backend::refreshAvatarFromChrome(const QVariant &a0) {
    // Google 頭像只能在登入當下取得（CLI 登入完成後瀏覽器仍帶著 Google 登入狀態）；
    // 所以這個按鈕會用已保存的密碼重新登入一次，登入時 cool.py 會順便下載頭像。
    emit toast(QStringLiteral("將重新登入以取得 Google 頭像…"));
    loginAccount(a0, QStringLiteral("headless"));
}
void Backend::setAvatarFromFile(const QVariant &a0, const QVariant &a1) {
    int i = a0.toInt();
    QString fileUrl = a1.toString();
    if (i < 0 || i >= m_accounts.size()) { emit toast(QStringLiteral("請先選擇帳號")); return; }
    QString email = m_accounts.at(i).toMap().value("email").toString();
    QString path = QUrl(fileUrl).toLocalFile();
    if (path.isEmpty()) path = fileUrl;
    QString stem = emailStem(email);
    QDir().mkpath(filePath("avatars"));
    // 判斷副檔名
    QString ext = QFileInfo(path).suffix().toLower();
    if (ext.isEmpty()) ext = "png";
    QString dest = filePath("avatars/" + stem + "." + ext);
    if (QFile::exists(dest)) QFile::remove(dest);
    if (QFile::copy(path, dest)) {
        for (const char *e : {"png","jpg","jpeg","webp","gif"}) {
            QString other = filePath("avatars/" + stem + "." + QString::fromLatin1(e));
            if (other != dest) QFile::remove(other);
        }
        reloadAccounts(); emit accountsChanged(); emit toast(QStringLiteral("已更新大頭貼"));
    } else emit toast(QStringLiteral("無法使用這張圖片"));
}
void Backend::clearAvatar(const QVariant &a0) {
    int i = a0.toInt();
    if (i < 0 || i >= m_accounts.size()) return;
    QString email = m_accounts.at(i).toMap().value("email").toString();
    QString stem = emailStem(email);
    for (const char *e : {"png","jpg","jpeg","webp","gif"}) QFile::remove(filePath("avatars/" + stem + "." + QString::fromLatin1(e)));
    reloadAccounts(); emit accountsChanged(); emit toast(QStringLiteral("已移除大頭貼，改回顯示名稱縮寫"));
}


// ============ Slots：匯出 ============
void Backend::exportReport(const QVariant &a0) {
    if (m_reports.isEmpty()) { emit toast(QStringLiteral("目前沒有報表資料，請先按「更新報表」")); return; }
    QString fmt = a0.toString().toLower();
    if (fmt.isEmpty()) fmt = "txt";
    QString suffix = fmt == "csv" ? ".csv" : fmt == "json" ? ".json" : ".txt";
    QString path = exportPath("report") + suffix;
    QFile f(path);
    if (!f.open(QIODevice::WriteOnly)) { emit toast(QStringLiteral("匯出失敗")); return; }
    bool incVideo = m_settings.value("reportIncludeVideo", true).toBool();
    if (fmt == "json") {
        QJsonArray arr;
        for (const auto &v : m_reports) arr.append(QJsonObject::fromVariantMap(v.toMap()));
        f.write(QJsonDocument(arr).toJson(QJsonDocument::Indented));
    } else if (fmt == "csv") {
        QStringList rows; rows << "month,platform,video,practice,total";
        for (const auto &v : m_reports) {
            QVariantMap r = v.toMap();
            int platform = r.value("platform").toInt(), video = incVideo ? r.value("video").toInt() : 0, practice = r.value("practice").toInt();
            rows << QString("%1,%2,%3,%4,%5").arg(r.value("month").toString()).arg(platform).arg(video).arg(practice).arg(platform + video);
        }
        f.write((rows.join("\n")+"\n").toUtf8());
    } else {
        QString name = m_accounts.isEmpty() ? QString() : m_accounts.at(qMax(0,m_selected)).toMap().value("name").toString();
        QStringList lines; lines << QStringLiteral("學習時間 · ")+name << QString(34, QChar('='));
        for (const auto &v : m_reports) {
            QVariantMap r = v.toMap();
            lines << QString("%1  平台 %2  影片 %3  練習 %4")
                     .arg(r.value("month").toString()).arg(r.value("platform").toInt())
                     .arg(r.value("video").toInt()).arg(r.value("practice").toInt());
        }
        if (!m_reportSource.isEmpty()) lines << "" << QStringLiteral("來源：")+m_reportSource << QStringLiteral("更新：")+m_reportUpdated;
        f.write((lines.join("\n")+"\n").toUtf8());
    }
    f.close();
    emit toast(QStringLiteral("已匯出：") + QFileInfo(path).fileName());
}
// (已改為原生實作，見 backend_native.inc: exportSessions)
// (已改為原生實作，見 backend_native.inc: exportSession)
void Backend::exportData() {
    QString path = exportPath("cool-data") + ".json";
    QFile f(path);
    if (!f.open(QIODevice::WriteOnly)) { emit toast(QStringLiteral("匯出失敗")); return; }
    QJsonObject root;
    QJsonArray acc; for (const auto &v : m_accounts) acc.append(QJsonObject::fromVariantMap(v.toMap()));
    QJsonArray ses; for (const auto &v : m_sessions) ses.append(QJsonObject::fromVariantMap(v.toMap()));
    QJsonArray crs; for (const auto &v : m_courses) crs.append(QJsonObject::fromVariantMap(v.toMap()));
    root["accounts"] = acc; root["settings"] = QJsonObject::fromVariantMap(m_settings);
    root["courses"] = crs; root["sessions"] = ses;
    f.write(QJsonDocument(root).toJson(QJsonDocument::Indented)); f.close();
    emit toast(QStringLiteral("已匯出全部資料"));
}
void Backend::backupSettings() {
    QString path = exportPath("settings") + ".json";
    QFile f(path);
    if (f.open(QIODevice::WriteOnly)) {
        f.write(QJsonDocument(QJsonObject::fromVariantMap(m_settings)).toJson(QJsonDocument::Indented));
        f.close(); emit toast(QStringLiteral("已備份設定"));
    }
}

// ============ Slots：系統整合 ============
void Backend::copyText(const QVariant &a0) {
    QString text = a0.toString();
    if (text.trimmed().isEmpty()) { emit toast(QStringLiteral("目前沒有可複製的內容")); return; }
    QGuiApplication::clipboard()->setText(text);
    emit toast(QStringLiteral("已複製到剪貼簿"));
}
// (已改為原生實作，見 backend_native.inc: openUrl)
void Backend::openFolder(const QVariant &a0) {
    QString p = a0.toString();
    if (p.isEmpty()) p = dataDir();
    QDir().mkpath(p);
    QDesktopServices::openUrl(QUrl::fromLocalFile(p));
    emit toast(QStringLiteral("已開啟資料夾"));
}

// ============ Slots：清除 ============
// (已改為原生實作，見 backend_native.inc: clearCookies)
void Backend::clearCache() {
    // 清除 reports cache / 暫存
    QStringList filters; filters << "*.tmp" << "*.cache";
    QDir dir(dataDir());
    for (const auto &f : dir.entryList(filters, QDir::Files)) QFile::remove(dir.filePath(f));
    emit cacheChanged(); emit toast(QStringLiteral("已清除快取"));
}
void Backend::wipeAll() {
    QStringList files = {"accounts.json","reports.json","network.json","settings.json","urls.txt","colors.json"};
    for (const auto &f : files) QFile::remove(filePath(f));
    // 只刪 cookies/avatars 內的檔案，不刪資料夾本身
    for (const auto &sub : {QString("cookies"), QString("avatars")}) {
        QDir d(filePath(sub));
        for (const auto &f : d.entryList(QDir::Files)) QFile::remove(d.filePath(f));
    }
    reloadAccounts(); reloadReports(); reloadSessions(); reloadCourses();
    emit accountsChanged(); emit reportsChanged(); emit sessionsChanged(); emit coursesChanged();
    emit toast(QStringLiteral("已清除全部資料"));
}


// ============ Slots：登入 ============
// (已改為原生實作，見 backend_native.inc: startLogin)
// (已改為原生實作，見 backend_native.inc: loginAccount)
void Backend::loginSelected(const QVariant &a0) { loginAccount(m_selected, a0.toString()); }
void Backend::clearLoginStatus() { m_loginStatus.clear(); emit loginChanged(); }

// ============ Slots：終端（每個分頁一個獨立 ConPTY + WebChannel）============
Backend::~Backend() {
    for (auto it = m_termSessions.begin(); it != m_termSessions.end(); ++it) {
        if (it->bridge) it->bridge->stop();
        if (it->channel) it->channel->deleteLater();
    }
    m_termSessions.clear();
}

QObject *Backend::terminalChannel(int sid) {
    auto it = m_termSessions.find(sid);
    return it != m_termSessions.end() ? it->channel : nullptr;
}
bool Backend::startTerminalWithArgs(const QString &profileId, const QStringList &args,
                                    const QString &label) {
    if (m_termTabs.size() >= 8) { emit toast(QStringLiteral("最多開啟 8 個終端分頁")); return false; }
    if (m_terminalProfiles.isEmpty()) { emit toast(QStringLiteral("找不到可用的終端機")); return false; }

    QString pid = profileId.isEmpty() ? defaultTerminal() : profileId;
    bool found = false;
    QString profileLabel;
    for (const auto &v : m_terminalProfiles) {
        QVariantMap m = v.toMap();
        if (m.value("id").toString() == pid) { found = true; profileLabel = m.value("label").toString(); break; }
    }
    if (!found) {
        QVariantMap m = m_terminalProfiles.first().toMap();
        pid = m.value("id").toString();
        profileLabel = m.value("label").toString();
    }

    int sid = ++m_termSeq;
    TermSession sess;
    sess.id = sid; sess.profile = pid;
    auto cmd = terminalCommand(pid, args);
    sess.argv = cmd.first; sess.boot = cmd.second;

    // 每個分頁：獨立 bridge + 獨立 WebChannel（JS 端 channel.objects.pty 各自隔離）
    sess.bridge = new QmlPtyBridge(this);
    connect(sess.bridge, &QmlPtyBridge::exitRequested, this, &Backend::quitApp, Qt::QueuedConnection);
    sess.channel = new QQmlWebChannel(this);
    sess.channel->registerObjects(
        QVariantMap{{QStringLiteral("pty"), QVariant::fromValue<QObject *>(sess.bridge)},
                    {QStringLiteral("cfg"), QVariant::fromValue<QObject *>(m_termCfg)}});
    m_termSessions.insert(sid, sess);

    // 這個分頁的 shell 立刻啟動，不依賴 QML 載入完成
    if (!sess.argv.isEmpty())
        sess.bridge->startShell(sess.argv.first(), sess.argv.mid(1), sess.boot, projectRoot());

    int same = 0;
    for (const auto &v : m_termTabs)
        if (v.toMap().value("profile").toString() == pid) ++same;

    QVariantMap tab;
    tab["id"] = sid; tab["profile"] = pid;
    tab["label"] = label.isEmpty()
        ? (same == 0 ? profileLabel : QStringLiteral("%1 %2").arg(profileLabel).arg(same + 1))
        : label;
    tab["icon"] = QStringLiteral("terminal"); tab["status"] = QStringLiteral("執行中");
    tab["running"] = true; tab["active"] = true;
    for (auto &v : m_termTabs) { QVariantMap m = v.toMap(); m["active"] = false; v = m; }
    m_termTabs.append(tab);
    for (auto it = m_termSessions.begin(); it != m_termSessions.end(); ++it)
        if (it.key() != sid && it->bridge) it->bridge->detach();
    m_termActive = sid;
    m_termRunning = true;
    m_termStatus = QStringLiteral("執行中");
    emit terminalTabsChanged();
    emit terminalChanged();
    return true;
}
void Backend::startTerminal(const QVariant &a0) {
    startTerminalWithArgs(a0.toString(), QStringList(), QString());
}
void Backend::launchTerminal(const QVariant &a0) {
    startTerminalWithArgs(a0.toString(), QStringList(), QString());
}
void Backend::selectTerminalTab(const QVariant &a0) {
    int sid = a0.toInt();
    if (!m_termSessions.contains(sid)) return;
    // 其他分頁的輸出先存進各自的歷史；切回來時由 xterm 載入後整段重播
    for (auto it = m_termSessions.begin(); it != m_termSessions.end(); ++it)
        if (it.key() != sid && it->bridge) it->bridge->detach();
    m_termActive = sid;
    for (auto &t : m_termTabs) { QVariantMap m = t.toMap(); m["active"] = (m["id"].toInt()==sid); t = m; }
    emit terminalTabsChanged();
}
void Backend::closeTerminalTab(const QVariant &a0) {
    int sid = a0.toInt();
    auto it = m_termSessions.find(sid);
    if (it != m_termSessions.end()) {
        if (it->bridge) it->bridge->stop();
        if (it->channel) it->channel->deleteLater();
        m_termSessions.erase(it);
    }
    QVariantList keep;
    for (const auto &v : m_termTabs) if (v.toMap().value("id").toInt() != sid) keep.append(v);
    m_termTabs = keep;
    if (m_termActive == sid) m_termActive = m_termTabs.isEmpty() ? 0 : m_termTabs.last().toMap().value("id").toInt();
    m_termRunning = !m_termTabs.isEmpty();
    emit terminalTabsChanged(); emit terminalChanged();
}
void Backend::writeTerminal(const QVariant &a0) {
    auto it = m_termSessions.find(m_termActive);
    if (it == m_termSessions.end() || !it->bridge || !it->bridge->running()) {
        emit toast(QStringLiteral("這個分頁的終端機沒有在執行")); return;
    }
    QString text = a0.toString(); text.remove('\r'); text.remove('\n');
    it->bridge->sendInput(QString::fromLatin1((text + "\r").toUtf8().toBase64()));
}
void Backend::pasteTerminal(const QVariant &a0) {
    QString text = QGuiApplication::clipboard()->text();
    if (text.isEmpty()) { emit toast(QStringLiteral("剪貼簿是空的")); return; }
    text.replace("\r\n", "\r"); text.replace('\n', '\r');
    auto it = m_termSessions.find(a0.toInt());
    if (it != m_termSessions.end() && it->bridge && it->bridge->running()) {
        it->bridge->sendInput(QString::fromLatin1(text.toUtf8().toBase64()));
        emit toast(QStringLiteral("已貼上 ") + QString::number(text.size()) + QStringLiteral(" 個字元"));
    }
}
void Backend::copyTerminalSelection(const QVariant &a0) {
    if (m_termText.isEmpty()) return;
    QGuiApplication::clipboard()->setText(m_termText);
    emit toast(QStringLiteral("已複製目前終端機畫面"));
}
void Backend::stopTerminal() {
    auto it = m_termSessions.find(m_termActive);
    if (it == m_termSessions.end() || !it->bridge || !it->bridge->running()) {
        emit toast(QStringLiteral("終端機沒有在執行")); return;
    }
    it->bridge->stop();
    for (auto &v : m_termTabs) { QVariantMap m = v.toMap(); if (m["id"].toInt() == m_termActive) { m["status"]="已停止"; m["running"]=false; } v = m; }
    m_termRunning = false; emit terminalTabsChanged(); emit terminalChanged();
}
void Backend::shutdownTerminal() {
    for (auto it = m_termSessions.begin(); it != m_termSessions.end(); ++it) {
        if (it->bridge) it->bridge->stop();
        if (it->channel) it->channel->deleteLater();
    }
    m_termSessions.clear(); m_termProcs.clear();
    m_termTabs.clear(); m_termActive = 0; m_termRunning = false; m_termText.clear();
    emit terminalTabsChanged(); emit terminalChanged();
}
void Backend::restartTerminal() {
    if (m_termTabs.isEmpty()) { startTerminalWithArgs(QString(), QStringList(), QString()); return; }
    auto it = m_termSessions.find(m_termActive);
    QString pid = (it != m_termSessions.end()) ? it->profile : defaultTerminal();
    QStringList ar = (it != m_termSessions.end()) ? it->argv.mid(1) : QStringList();
    closeTerminalTab(m_termActive);
    startTerminalWithArgs(pid, ar, QString());
}
void Backend::clearTerminal() { m_termText.clear(); emit terminalChanged(); }
void Backend::clearTerminalHistory() { m_termHistory.clear(); emit terminalChanged(); }
void Backend::toggleCursor() { /* 游標閃爍由 QML 處理 */ }
QString Backend::selectionText() { return QString(); }
void Backend::refresh() { reloadReports(); reloadSessions(); emit reportsChanged(); emit sessionsChanged(); }


void Backend::syncIdle() {
    if (!m_idleTimer) return;
    if (m_settings.value("autoLock", false).toBool()) {
        int minutes = qMax(1, m_settings.value("lockMinutes", 10).toInt());
        m_idleTimer->setInterval(minutes * 60 * 1000);
        m_idleTimer->start();
    } else {
        m_idleTimer->stop();
    }
}
void Backend::onIdleTimeout() {
    if (m_settings.value("autoLock", false).toBool()) {
        int minutes = qMax(1, m_settings.value("lockMinutes", 10).toInt());
        emit lockRequested(minutes);
    }
}
bool Backend::eventFilter(QObject *obj, QEvent *event) {
    // 任何滑鼠/鍵盤活動就重設計時
    if (m_idleTimer && m_idleTimer->isActive()) {
        QEvent::Type t = event->type();
        if (t == QEvent::MouseMove || t == QEvent::MouseButtonPress ||
            t == QEvent::KeyPress || t == QEvent::Wheel || t == QEvent::TouchBegin) {
            m_idleTimer->start();
        }
    }
    return QObject::eventFilter(obj, event);
}

void Backend::noteCourseOpen(const QString &url) {
    QString path = filePath("course_usage.json");
    QJsonObject usage = readObject("course_usage.json");
    QJsonObject item = usage.value(url).toObject();
    item["opens"] = item.value("opens").toInt() + 1;
    item["last"] = nowStamp();
    usage[url] = item;
    writeJson("course_usage.json", QJsonDocument(usage));
    // 更新 m_courses
    for (auto &v : m_courses) {
        QVariantMap m = v.toMap();
        if (m.value("url").toString() == url) {
            m["opens"] = item["opens"].toInt();
            m["opened"] = fmtStamp(item["last"].toString());
            m["openedAt"] = item["last"].toString();
            v = m;
        }
    }
    emit coursesChanged();
}

#include "backend_native.inc"

void Backend::applyFontFamily() {
    const QString f = m_settings.value("fontFamily", "system").toString();
    QString fam = f == "segoe" ? "Segoe UI" : f == "arial" ? "Arial" : f == "consolas" ? "Consolas" : "Segoe UI Variable";
    QFont font = QGuiApplication::font();
    font.setFamilies(QStringList{ fam, "Segoe UI", "Microsoft JhengHei UI", "Microsoft JhengHei" });
    QGuiApplication::setFont(font);
}
#include "backend_cli.inc"
