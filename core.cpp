#include "backend.h"
#include "color_engine.h"
#include <QDir>
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
    QDir(dataDir()).mkpath(".");
    QFile f(filePath(name));
    if (!f.open(QIODevice::WriteOnly)) return false;
    f.write(doc.toJson(QJsonDocument::Indented));
    return true;
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
QString pythonExe() {
    // 用專案 venv 的 python（有 materialyoucolor / playwright / cryptography）
    QString p = "C:/Users/jusaper/Downloads/cool-qml-caelestia/coolqml/.venv/Scripts/python.exe";
    if (QFile::exists(p)) return p;
    return "python";
}
} // namespace

Backend::Backend(QObject *parent) : QObject(parent)
{
    m_settings = readObject("settings.json").toVariantMap();
    if (m_settings.isEmpty()) {
        // 合理預設
        m_settings["seed"] = "#ff583d";
        m_settings["variant"] = "expressive";
        m_settings["dark"] = false;
        m_settings["contrast"] = 0.0;
        m_settings["defaultLoginMode"] = "headless";
        m_settings["networkMode"] = "keep";
        m_settings["retention"] = 1440;
        m_settings["maxSessions"] = 80;
        m_settings["captureRaw"] = false;
        m_settings["confirmDestructive"] = true;
        m_settings["reportIncludeVideo"] = true;
    }
    m_seed = m_settings.value("seed", "#ff583d").toString();
    m_variant = m_settings.value("variant", "expressive").toString();
    m_dark = m_settings.value("dark", false).toBool();
    m_contrast = m_settings.value("contrast", 0.0).toDouble();
    reloadAccounts();
    reloadReports();
    reloadSessions();
    reloadCourses();
    buildPresets();
    buildColors();
    // 自動鎖定計時器
    m_idleTimer = new QTimer(this);
    m_idleTimer->setSingleShot(true);
    connect(m_idleTimer, &QTimer::timeout, this, &Backend::onIdleTimeout);
    syncIdle();
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
    // themes
    QVariantList themes;
    const char *th[][6] = {
        {"ember","Ember","暖色","#ff583d","false","expressive"},
        {"lavender","Lavender","冷色","#6750a4","true","tonalSpot"},
        {"ocean","Ocean","冷色","#00639b","true","vibrant"},
        {"forest","Forest","自然","#3f6212","false","tonalSpot"},
        {"mono","Mono","中性","#767676","true","monochrome"}
    };
    for (auto &t : th) {
        QVariantMap m; m["id"]=QString::fromLatin1(t[0]); m["name"]=QString::fromLatin1(t[1]);
        m["group"]=QString::fromLatin1(t[2]); m["seed"]=QString::fromLatin1(t[3]);
        m["dark"]=(QString::fromLatin1(t[4])=="true"); m["variant"]=QString::fromLatin1(t[5]);
        themes.append(m);
    }
    m_themes = themes;
    // terminal profiles
    QVariantList profs;
    QVariantMap p1; p1["id"]="powershell"; p1["label"]="Windows PowerShell"; p1["icon"]="terminal"; profs.append(p1);
    QVariantMap p2; p2["id"]="cmd"; p2["label"]="命令提示字元"; p2["icon"]="terminal"; profs.append(p2);
    m_terminalProfiles = profs;
    // cli styles / fields 基本
    QVariantList styles;
    const char *cs[][2] = {{"title","GREEN"},{"text","WHITE"},{"error","RED"},{"success","GREEN"}};
    for (auto &c : cs) { QVariantMap m; m["field"]=QString::fromLatin1(c[0]); m["style"]=QString::fromLatin1(c[1]); styles.append(m); }
    m_cliStyles = styles;
}

void Backend::buildColors() {
    // 全新色彩風格：從 seed 用 HSV 色相協調推導整套配色，不依賴 scheme.py
    m_colors = ColorEngine::generate(m_seed, m_variant, m_dark);
}

void Backend::reloadAccounts() {
    QVariantList out;
    QJsonArray arr = readArray("accounts.json");
    int i = 0;
    for (const auto &v : arr) {
        QJsonObject a = v.toObject();
        QString email = a.value("email").toString();
        QVariantMap m;
        m["id"] = ++i;
        m["name"] = a.value("name").toString();
        if (m["name"].toString().isEmpty()) m["name"] = email.section('@',0,0);
        m["email"] = email;
        m["last"] = fmtStamp(a.value("last_login").toString());
        // Cookie 狀態：優先信任「檢查 Cookie」存的獨立狀態，其次依報表抓取結果
        QString cookieStatus;
        QJsonObject cookieStates = readObject("cookie_status.json");
        if (cookieStates.contains(email)) {
            cookieStatus = cookieStates.value(email).toString();  // valid / expired / unknown
        } else {
            QJsonObject repEntry = readObject("reports.json").value("accounts").toObject().value(email).toObject();
            QString repErr = repEntry.value("error").toString();
            if (repEntry.contains("reports") && !repEntry.value("reports").toArray().isEmpty())
                cookieStatus = "valid";           // 抓過報表 → 有效
            else if (repErr.contains("Cookie") || repErr.contains("登入") || repErr.contains("Session") || repErr.contains("session"))
                cookieStatus = "expired";          // 報表抓取明確說 Cookie 問題 → 過期
            else
                cookieStatus = "unknown";          // 沒抓過也沒錯誤 → 未檢查（不假設有效）
        }
        m["cookie"] = cookieStatus;
        m["expires"] = cookieStatus == "expired" ? QStringLiteral("已失效") : QStringLiteral("工作階段 Cookie");
        m["obtained"] = fmtStamp(a.value("created_at").toString());
        m["saved"] = !a.value("password_enc").toString().isEmpty();
        m["synced"] = true;
        QString mode = a.value("login_mode").toString();
        m["note"] = (mode=="headed"||mode=="headless") ? QStringLiteral("以 Playwright 登入") : QString();
        m["mode"] = mode;
        QString stem = emailStem(email);
        QString av;
        for (const char *ext : {"png","jpg","jpeg","webp","gif"}) {
            QString p = filePath("avatars/" + stem + "." + QString::fromLatin1(ext));
            if (QFile::exists(p)) { av = QUrl::fromLocalFile(p).toString() + "?v=" + QString::number(QFileInfo(p).lastModified().toMSecsSinceEpoch()); break; }
        }
        m["avatar"] = av;
        out.append(m);
    }
    m_accounts = out;
    if (m_selected >= out.size()) m_selected = qMax(0, out.size()-1);
}

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

void Backend::reloadSessions() {
    QVariantList out;
    QJsonArray arr = readArray("network.json");
    qint64 total = 0;
    for (const auto &v : arr) {
        QJsonObject s = v.toObject();
        QVariantMap m = s.toVariantMap();
        if (m["status"]=="active") m["status"]="stopped";
        out.append(m);
        total += s.value("bytes").toInt();
    }
    m_sessions = out;
    m_networkSize = QStringLiteral("%1 B").arg(total);
}

void Backend::reloadCourses() {
    QVariantList out;
    QFile f(filePath("urls.txt"));
    if (!f.open(QIODevice::ReadOnly)) { m_courses = out; return; }
    QString group, category;
    int id = 0;
    while (!f.atEnd()) {
        QString line = QString::fromUtf8(f.readLine()).trimmed();
        if (line.startsWith("# group:")) group = line.mid(8).trimmed();
        else if (line.startsWith("# category:")) category = line.mid(11).trimmed();
        else if (line.startsWith("http")) {
            QVariantMap m;
            m["id"]=++id; m["url"]=line;
            m["category"]=category.isEmpty()?group:category;
            m["alias"]=group.isEmpty()?category:group;
            m["opens"]=0; m["opened"]=QStringLiteral("尚未開啟"); m["openedAt"]=QString();
            out.append(m);
        }
    }
    m_courses = out;
}

void Backend::saveSettings() {
    QJsonObject obj = QJsonObject::fromVariantMap(m_settings);
    writeJson("settings.json", QJsonDocument(obj));
}

void Backend::saveRaw(const QJsonArray &arr) {
    writeJson("accounts.json", QJsonDocument(arr));
}

void Backend::saveCourses() {
    QStringList lines;
    lines << "# Cool English 課程連結組" << "# 最近更新: " + QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss") << "";
    QString lastGroup, lastCat;
    for (const auto &v : m_courses) {
        QVariantMap c = v.toMap();
        QString g = c["category"].toString();
        if (g != lastGroup) { lines << "" << "# group: " + g << "# category: " + g; lastGroup = g; }
        lines << c["url"].toString();
    }
    QFile f(filePath("urls.txt"));
    if (f.open(QIODevice::WriteOnly)) f.write((lines.join("\n")+"\n").toUtf8());
}

void Backend::saveSessionsJson() {
    QJsonArray arr;
    for (const auto &v : m_sessions) arr.append(QJsonObject::fromVariantMap(v.toMap()));
    writeJson("network.json", QJsonDocument(arr));
}

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
QString Backend::debugSection() const { return QString(); }
