#include "color_engine.h"

// ============ Slots：網路紀錄 ============
void Backend::stopSession(const QVariant &a0) {
    QString sid = a0.toString();
    for (auto &v : m_sessions) {
        QVariantMap m = v.toMap();
        if (m.value("id").toString() == sid && m.value("status").toString() == "active") {
            m["status"] = "stopped"; v = m; emit toast(QStringLiteral("已終止 ") + m.value("label").toString());
        }
    }
    saveSessionsJson(); emit sessionsChanged();
}
void Backend::deleteSession(const QVariant &a0) {
    QString sid = a0.toString();
    QVariantList keep;
    for (const auto &v : m_sessions) if (v.toMap().value("id").toString() != sid) keep.append(v);
    m_sessions = keep; saveSessionsJson(); emit sessionsChanged(); emit toast(QStringLiteral("已刪除工作階段"));
}
void Backend::deleteSessions(const QVariant &a0) {
    QVariantList ids = a0.toList();
    QVariantList keep;
    for (const auto &v : m_sessions) if (!ids.contains(v.toMap().value("id"))) keep.append(v);
    m_sessions = keep; saveSessionsJson(); emit sessionsChanged();
    emit toast(QStringLiteral("已刪除 ") + QString::number(ids.size()) + QStringLiteral(" 筆紀錄"));
}
void Backend::clearSessions() {
    m_sessions.clear(); saveSessionsJson(); emit sessionsChanged(); emit toast(QStringLiteral("已清除全部網路紀錄"));
}

// ============ Slots：設定 ============
void Backend::updateSetting(const QVariant &a0, const QVariant &a1) {
    QString key = a0.toString();
    if (!m_settings.contains(key)) return;
    m_settings[key] = a1;
    saveSettings();
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
    m_settings["themeId"] = id; m_settings["seed"] = seed; m_settings["dark"] = dark;
    for (const auto &v : m_themes) {
        QVariantMap t = v.toMap();
        if (t.value("id").toString() == id) { m_settings["variant"] = t.value("variant"); break; }
    }
    m_seed = seed; m_dark = dark;
    m_variant = m_settings.value("variant", m_variant).toString();
    buildColors(); saveSettings();
    emit colorsChanged(); emit schemeChanged(); emit settingsChanged();
}
void Backend::setScheme(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3) {
    m_seed = a0.toString(); m_variant = a1.toString(); m_dark = a2.toBool(); m_contrast = a3.toDouble();
    m_settings["seed"] = m_seed; m_settings["variant"] = m_variant;
    m_settings["dark"] = m_dark; m_settings["contrast"] = m_contrast;
    buildColors(); saveSettings(); emit colorsChanged(); emit schemeChanged();
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
bool Backend::hasUnlockPassword() {
    QJsonArray raw = readArray("accounts.json");
    for (const auto &v : raw) if (!v.toObject().value("password_enc").toString().isEmpty()) return true;
    return false;
}
bool Backend::verifyUnlock(const QVariant &a0) {
    QString pw = a0.toString();
    if (pw.isEmpty()) return false;
    QProcess proc;
    QString code = QString("import sys;sys.path.insert(0,r'C:/Users/jusaper/Downloads/cool-qml-caelestia/coolqml');"
        "from cool_cli.security import decrypt_password;import json,os;"
        "raw=json.load(open(os.path.join(os.environ['APPDATA'],'cool','accounts.json'),encoding='utf-8'));"
        "print(any(decrypt_password(a.get('password_enc',''))==%1 for a in raw if a.get('password_enc')))").arg("'" + pw + "'");
    proc.start(pythonExe(), QStringList() << "-c" << code);
    proc.waitForFinished(5000);
    return QString::fromUtf8(proc.readAllStandardOutput()).trimmed() == "True";
}

// ============ Slots：頭像 ============
void Backend::refreshAvatar(const QVariant &a0) {
    int i = a0.toInt();
    if (i < 0 || i >= m_accounts.size()) { emit toast(QStringLiteral("請先選擇帳號")); return; }
    QString email = m_accounts.at(i).toMap().value("email").toString();
    emit toast(QStringLiteral("正在從 Google 讀取頭像…"));
    QProcess *proc = new QProcess(this);
    QString code = QString("import sys;sys.path.insert(0,r'C:/Users/jusaper/Downloads/cool-qml-caelestia/coolqml');"
        "from cool_cli.avatar import fetch_avatar;p,m=fetch_avatar(%1);print(m)").arg("'" + email + "'");
    proc->start(pythonExe(), QStringList() << "-c" << code);
    connect(proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this, proc](int, QProcess::ExitStatus) {
                proc->deleteLater(); reloadAccounts(); emit accountsChanged();
            });
}
void Backend::refreshAvatarFromChrome(const QVariant &a0) {
    int i = a0.toInt();
    if (i < 0 || i >= m_accounts.size()) { emit toast(QStringLiteral("請先選擇帳號")); return; }
    QString email = m_accounts.at(i).toMap().value("email").toString();
    emit toast(QStringLiteral("正在從 Chrome 讀取 Google 頭像…"));
    QProcess *proc = new QProcess(this);
    QString code = QString("import sys;sys.path.insert(0,r'C:/Users/jusaper/Downloads/cool-qml-caelestia/coolqml');"
        "from cool_cli.avatar import fetch_avatar_from_chrome;p,m=fetch_avatar_from_chrome(%1);print(m)").arg("'" + email + "'");
    proc->start(pythonExe(), QStringList() << "-c" << code);
    connect(proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this, proc](int, QProcess::ExitStatus) {
                proc->deleteLater(); reloadAccounts(); emit accountsChanged();
            });
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
