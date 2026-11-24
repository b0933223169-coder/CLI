// 被 backend.cpp 在檔尾 #include。這裡的函式取代原本呼叫 Python 的實作：
// 帳號/憑證(DPAPI)、報表直接請求、網路紀錄、登入、課程開啟、CLI 雙向同步。
#include "native.h"
#include <QFileSystemWatcher>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QNetworkProxyFactory>
#include <QRegularExpression>
#include <QSaveFile>
#include <QCoreApplication>

namespace {
const QString kBase = QStringLiteral("https://www.coolenglish.edu.tw");
const QString kReportUrl = kBase + QStringLiteral("/time/time_view_report.php");
const QString kUA = QStringLiteral("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36");

QString networkDir() { return filePath("network"); }
QString sessionLog(const QString &sid) { return networkDir() + "/" + sid + ".jsonl"; }

QJsonObject readCreds() { return readObject("credentials.json"); }
void writeCreds(const QJsonObject &o) {
    Native::atomicWrite(filePath("credentials.json"), QJsonDocument(o).toJson(QJsonDocument::Indented));
}
bool saveCredentialFor(const QString &email, const QString &password) {
    if (password.isEmpty()) return false;
    QString enc = Native::protectString(password);
    if (enc.isEmpty()) return false;
    QJsonObject c = readCreds();
    c[email.toLower()] = enc;
    writeCreds(c);
    return true;
}
bool getCredentialFor(const QString &email, QString *pw) {
    QString enc = readCreds().value(email.toLower()).toString();
    return !enc.isEmpty() && Native::unprotectString(enc, pw);
}
void removeCredentialFor(const QString &email) {
    QJsonObject c = readCreds();
    if (c.contains(email.toLower())) { c.remove(email.toLower()); writeCreds(c); }
}
QString isoNow() { return QDateTime::currentDateTime().toString("yyyy-MM-ddTHH:mm:ss"); }
QString isoUtcNow() { return QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs); }
bool underDir(const QString &dir, const QString &path) {
    QString d = QDir::cleanPath(QDir(dir).absolutePath()) + "/";
    return QDir::cleanPath(QFileInfo(path).absoluteFilePath()).startsWith(d, Qt::CaseInsensitive);
}
QString cookiePathFor(const QString &cookieFile) {
    return QDir::cleanPath(QDir(dataDir()).absoluteFilePath(cookieFile));
}
const char *kEncMarker = "#COOL_ENCRYPTED_V1\n";
} // namespace

// ============================================================ 路徑 / CLI 目錄
QString Backend::cliDir() const {
    QString env = qEnvironmentVariable("COOL_CLI_DIR");
    if (!env.isEmpty()) return QDir::cleanPath(env);
    QString bundled = QDir(rootDirPath()).filePath("cli");
    if (QFileInfo::exists(QDir(bundled).filePath("cool.py"))) return QDir::cleanPath(bundled);
    return projectRoot();
}

// ============================================================ 憑證 / Cookie
QList<Native::Cookie> Backend::loadCookies(const QString &email) {
    QList<Native::Cookie> out;
    QJsonArray raw = readArray("accounts.json");
    for (const auto &v : raw) {
        QJsonObject a = v.toObject();
        if (a.value("email").toString().compare(email, Qt::CaseInsensitive) != 0) continue;
        QString path = cookiePathFor(a.value("cookie_file").toString());
        if (a.value("cookie_file").toString().isEmpty() || !underDir(filePath("cookies"), path)) return out;
        QFile f(path);
        if (!f.open(QIODevice::ReadOnly)) return out;
        QString text = QString::fromUtf8(f.readAll());
        f.close();
        if (text.startsWith(QString::fromLatin1(kEncMarker))) {
            QString plain;
            QString b64 = text.mid(int(strlen(kEncMarker))).section('\n', 0, 0);
            if (!Native::unprotectString(b64, &plain)) return out;
            text = plain;
        } else {
            // 舊版明文 Cookie：讀取後立即升級為 DPAPI 加密
            text.remove(QChar(0xFEFF));
            QString enc = Native::protectString(text);
            if (!enc.isEmpty())
                Native::atomicWrite(path, (QString::fromLatin1(kEncMarker) + enc + "\n").toUtf8());
        }
        return Native::parseNetscape(text);
    }
    return out;
}

bool Backend::saveLogin(const QString &email, const QString &displayName, const QList<Native::Cookie> &cookies,
                        const QString &userId, QString *err) {
    QList<Native::Cookie> valid = Native::coolCookies(cookies);
    if (!Native::hasUsableMoodleSession(valid)) {
        if (err) *err = QStringLiteral("尚未取得有效的 MoodleSession，請先在登入視窗完成登入。");
        return false;
    }
    QString name = Native::emailCookieName(email);
    QString rel = "cookies/" + name;
    QString enc = Native::protectString(Native::serializeNetscape(valid));
    if (enc.isEmpty()) {
        if (err) *err = QStringLiteral("Windows 系統加密服務目前不可用，為保護 cookie 已取消儲存。");
        return false;
    }
    QDir().mkpath(filePath("cookies"));
    if (!Native::atomicWrite(filePath(rel), (QString::fromLatin1(kEncMarker) + enc + "\n").toUtf8())) {
        if (err) *err = QStringLiteral("無法寫入 Cookie 檔。");
        return false;
    }
    double minExp = 0;
    for (const auto &c : valid)
        if (c.name == "MoodleSession" && c.expires > QDateTime::currentSecsSinceEpoch() && (minExp == 0 || c.expires < minExp)) minExp = c.expires;
    QString expIso = minExp > 0 ? QDateTime::fromSecsSinceEpoch(qint64(minExp)).toUTC().toString(Qt::ISODate) : QString();
    QString nowIso = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
    QString now = isoNow();

    QJsonArray raw = readArray("accounts.json");
    int idx = -1;
    for (int i = 0; i < raw.size(); ++i)
        if (raw.at(i).toObject().value("email").toString().compare(email, Qt::CaseInsensitive) == 0) { idx = i; break; }
    QJsonObject o = idx >= 0 ? raw.at(idx).toObject() : QJsonObject();
    if (idx >= 0) {
        if (!displayName.trimmed().isEmpty()) o["name"] = displayName.trimmed();
    } else {
        QString base = displayName.trimmed().isEmpty() ? email.section('@', 0, 0) : displayName.trimmed();
        QString nm = base; int suffix = 2;
        auto taken = [&](const QString &n) {
            for (const auto &v : raw) if (v.toObject().value("name").toString().compare(n, Qt::CaseInsensitive) == 0) return true;
            return false;
        };
        while (taken(nm)) nm = base + QString::number(suffix++);
        o["name"] = nm; o["email"] = email; o["created_at"] = now;
    }
    o["cookie_file"] = rel;
    o["last_login"] = now;
    o["cookieObtainedAt"] = nowIso;
    o["cookieExpiresAt"] = expIso.isEmpty() ? QJsonValue(QJsonValue::Null) : QJsonValue(expIso);
    o["cookieStatus"] = "valid";
    o["cookieCheckedAt"] = nowIso;
    o.remove("cookieExpiredAt");
    o.remove("password_enc"); o.remove("password_len");
    if (!userId.isEmpty()) o["user_id"] = userId;
    if (idx >= 0) raw.replace(idx, o); else raw.append(o);
    saveRaw(raw);
    return true;
}

void Backend::setCookieStatus(const QString &email, const QString &status) {
    QJsonArray raw = readArray("accounts.json");
    for (int i = 0; i < raw.size(); ++i) {
        QJsonObject o = raw.at(i).toObject();
        if (o.value("email").toString().compare(email, Qt::CaseInsensitive) != 0) continue;
        QString now = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
        o["cookieStatus"] = status; o["cookieCheckedAt"] = now;
        if (status == "expired") o["cookieExpiredAt"] = now; else if (status == "valid") o.remove("cookieExpiredAt");
        raw.replace(i, o);
        saveRaw(raw);
        break;
    }
    reloadAccounts();
    emit accountsChanged();
}

// ============================================================ 帳號（覆寫舊實作）
void Backend::reloadAccounts() {
    QVariantList out;
    QJsonArray arr = readArray("accounts.json");
    QJsonObject creds = readCreds();
    QJsonObject legacyStatus = readObject("cookie_status.json");
    int i = 0;
    for (const auto &v : arr) {
        QJsonObject a = v.toObject();
        QString email = a.value("email").toString();
        QVariantMap m;
        m["id"] = ++i;
        QString nm = a.value("name").toString();
        m["name"] = nm.isEmpty() ? email.section('@', 0, 0) : nm;
        m["email"] = email;
        m["last"] = fmtStamp(a.value("last_login").toString());
        QString st = a.value("cookieStatus").toString();
        if (st.isEmpty()) st = legacyStatus.value(email).toString();
        if (st != "valid" && st != "expired") st = "unknown";
        // 本機 Cookie 檔不存在就不可能有效
        QString ck = a.value("cookie_file").toString();
        if (ck.isEmpty() || !QFile::exists(cookiePathFor(ck))) st = (ck.isEmpty() ? "unknown" : "expired");
        m["cookie"] = st;
        QString expAt = a.value("cookieExpiresAt").toString();
        if (st == "expired") m["expires"] = QStringLiteral("已失效");
        else if (!expAt.isEmpty()) m["expires"] = fmtStamp(QDateTime::fromString(expAt, Qt::ISODate).toLocalTime().toString("yyyy-MM-ddTHH:mm"));
        else m["expires"] = QStringLiteral("工作階段 Cookie");
        QString obt = a.value("cookieObtainedAt").toString();
        m["obtained"] = obt.isEmpty() ? fmtStamp(a.value("created_at").toString())
                                      : fmtStamp(QDateTime::fromString(obt, Qt::ISODate).toLocalTime().toString("yyyy-MM-ddTHH:mm"));
        m["saved"] = creds.contains(email.toLower());
        m["synced"] = true;
        QString mode = a.value("login_mode").toString();
        m["note"] = (mode == "headed" || mode == "headless") ? QStringLiteral("以 Google 登入（Chromium）") : QString();
        m["mode"] = mode;
        m["userId"] = a.value("user_id").toString();
        QString stem = emailStem(email);
        QString av;
        for (const char *ext : {"png", "jpg", "jpeg", "webp", "gif"}) {
            QString p = filePath("avatars/" + stem + "." + QString::fromLatin1(ext));
            if (QFile::exists(p)) { av = QUrl::fromLocalFile(p).toString() + "?v=" + QString::number(QFileInfo(p).lastModified().toMSecsSinceEpoch()); break; }
        }
        m["avatar"] = av;
        out.append(m);
    }
    m_accounts = out;
    if (m_selected >= out.size()) m_selected = qMax(0, out.size() - 1);
}

void Backend::renameAccount(const QVariant &a0, const QVariant &a1) {
    int i = a0.toInt(); QString name = a1.toString().trimmed();
    QJsonArray raw = readArray("accounts.json");
    if (i < 0 || i >= raw.size()) return;
    static const QRegularExpression bad(QStringLiteral("[\\\\/*?:\"<>|\\n\\t]"));
    if (name.isEmpty() || name.size() > 64 || bad.match(name).hasMatch()) {
        emit toast(QStringLiteral("名稱不可為空、超過 64 字，或包含不合法字元。")); return;
    }
    for (int k = 0; k < raw.size(); ++k)
        if (k != i && raw.at(k).toObject().value("name").toString().compare(name, Qt::CaseInsensitive) == 0) {
            emit toast(QStringLiteral("此帳號名稱已被使用。")); return;
        }
    QJsonObject o = raw.at(i).toObject(); o["name"] = name; raw.replace(i, o);
    saveRaw(raw); reloadAccounts(); emit accountsChanged(); emit toast(QStringLiteral("已更新名稱"));
    syncToCli();
}

void Backend::removeAccount(const QVariant &a0) {
    int i = a0.toInt();
    QJsonArray raw = readArray("accounts.json");
    if (i < 0 || i >= raw.size()) return;
    QJsonObject o = raw.at(i).toObject();
    QString email = o.value("email").toString(), name = o.value("name").toString();
    QString ck = o.value("cookie_file").toString();
    if (!ck.isEmpty() && underDir(filePath("cookies"), cookiePathFor(ck))) QFile::remove(cookiePathFor(ck));
    QString stem = emailStem(email);
    for (const char *ext : {"png", "jpg", "jpeg", "webp", "gif"}) QFile::remove(filePath("avatars/" + stem + "." + QString::fromLatin1(ext)));
    removeCredentialFor(email);
    raw.removeAt(i);
    saveRaw(raw); reloadAccounts(); reloadReports();
    emit accountsChanged(); emit selectedChanged(); emit reportsChanged();
    removeCliAccount(email);
    emit toast(QStringLiteral("已移除 ") + name + QStringLiteral(" 與本機 Cookie"));
}

void Backend::removeAllAccounts() {
    QJsonArray raw = readArray("accounts.json");
    QStringList emails;
    for (const auto &v : raw) {
        QJsonObject o = v.toObject();
        QString ck = o.value("cookie_file").toString();
        if (!ck.isEmpty() && underDir(filePath("cookies"), cookiePathFor(ck))) QFile::remove(cookiePathFor(ck));
        emails << o.value("email").toString();
        removeCredentialFor(o.value("email").toString());
    }
    saveRaw(QJsonArray());
    reloadAccounts(); reloadReports();
    emit accountsChanged(); emit selectedChanged(); emit reportsChanged();
    for (const QString &e : emails) removeCliAccount(e);
    emit toast(QStringLiteral("已移除全部帳號"));
}

void Backend::clearCookies() {
    QJsonArray raw = readArray("accounts.json");
    for (int i = 0; i < raw.size(); ++i) {
        QJsonObject o = raw.at(i).toObject();
        QString ck = o.value("cookie_file").toString();
        if (!ck.isEmpty() && underDir(filePath("cookies"), cookiePathFor(ck))) QFile::remove(cookiePathFor(ck));
        o["cookieStatus"] = "expired"; o["cookieExpiredAt"] = QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs);
        raw.replace(i, o);
    }
    saveRaw(raw); reloadAccounts(); emit accountsChanged(); emit toast(QStringLiteral("已清除本機 Cookie"));
}

bool Backend::hasUnlockPassword() { return !readCreds().isEmpty(); }
bool Backend::verifyUnlock(const QVariant &a0) {
    QString pw = a0.toString();
    if (pw.isEmpty()) return false;
    const QJsonObject creds = readCreds();
    for (auto it = creds.begin(); it != creds.end(); ++it) {
        QString plain;
        if (Native::unprotectString(it.value().toString(), &plain) && plain == pw) return true;
    }
    return false;
}

// ============================================================ 登入（原生 CDP）
// ============================================================ 報表（直接請求，不啟動瀏覽器）
// ============================================================ 網路紀錄
bool Backend::historyEnabled() const { return m_settings.value("networkMode", "keep").toString() != "disabled"; }

QString Backend::createSession(const QString &mode, const QString &label, const QString &account, const QString &forcedId) {
    QString sid = forcedId.isEmpty() ? QStringLiteral("r%1").arg(QDateTime::currentMSecsSinceEpoch()) : forcedId;
    QVariantMap m;
    m["id"] = sid; m["label"] = label; m["mode"] = mode; m["status"] = "active";
    m["time"] = QDateTime::currentDateTime().toString("MM-dd HH:mm");
    m["startedAt"] = isoNow(); m["endedAt"] = QString();
    m["events"] = QVariantList(); m["events_n"] = 0; m["bytes"] = 0; m["size"] = "0 B";
    m["account"] = account; m["note"] = QString(); m["lines"] = QString();
    m["ephemeral"] = !historyEnabled();
    m_sessions.prepend(m);
    markSessionsDirty();
    return sid;
}

int Backend::sessionIndex(const QString &sid) const {
    for (int i = 0; i < m_sessions.size(); ++i) if (m_sessions.at(i).toMap().value("id").toString() == sid) return i;
    return -1;
}

void Backend::recordEvent(const QString &sid, const QVariantMap &ev) {
    if (!historyEnabled()) return;
    if (m_settings.value("onlyFailures", false).toBool() && ev.value("kind").toString() != "failed"
        && ev.value("status").toInt() < 400) return;          // 只記錄失敗請求（含 HTTP 4xx/5xx）
    int i = sessionIndex(sid);
    if (i < 0) return;
    QFile *f = m_logs.value(sid);
    if (!f) {
        QDir().mkpath(networkDir());
        f = new QFile(sessionLog(sid), this);
        if (!f->open(QIODevice::Append | QIODevice::WriteOnly)) { delete f; return; }
        m_logs.insert(sid, f);
    }
    QVariantMap e = ev;
    if (!e.contains("time")) e["time"] = QDateTime::currentDateTime().toString("HH:mm:ss");
    if (!e.contains("iso")) e["iso"] = QDateTime::currentDateTime().toString(Qt::ISODateWithMs);
    f->write(QJsonDocument(QJsonObject::fromVariantMap(e)).toJson(QJsonDocument::Compact) + "\n");
    f->flush();
    QVariantMap s = m_sessions.at(i).toMap();
    s["events_n"] = s.value("events_n").toInt() + 1;
    qint64 bytes = s.value("bytes").toLongLong() + e.value("bytes").toLongLong();
    s["bytes"] = bytes; s["size"] = Native::humanSize(bytes);
    m_sessions[i] = s;
    markSessionsDirty();
}

void Backend::finishSession(const QString &sid, const QString &status, const QString &note) {
    int i = sessionIndex(sid);
    if (i < 0) return;
    if (QFile *f = m_logs.take(sid)) { f->close(); f->deleteLater(); }
    QVariantMap s = m_sessions.at(i).toMap();
    if (s.value("status").toString() != "active") return;
    s["status"] = status; s["endedAt"] = isoNow();
    if (!note.isEmpty()) s["note"] = note;
    if (s.value("ephemeral").toBool()) { m_sessions.removeAt(i); }
    else m_sessions[i] = s;
    saveSessionsJson();
    markSessionsDirty();
}

void Backend::markSessionsDirty() {
    if (m_sessionsTimer && !m_sessionsTimer->isActive()) m_sessionsTimer->start();
}

void Backend::flushSessions() {
    emit sessionsChanged();
    // 活動中的工作階段每次最多每 400 ms 通知一次；落盤改為每 5 秒一次
    static QElapsedTimer last; if (!last.isValid()) last.start();
    if (last.elapsed() > 5000) { saveSessionsJson(); last.restart(); }
}

void Backend::reloadSessions() {
    QVariantList out;
    QJsonArray arr = readArray("network.json");
    qint64 total = 0;
    for (const auto &v : arr) {
        QJsonObject s = v.toObject();
        QVariantMap m = s.toVariantMap();
        if (m["status"] == "active") { m["status"] = "stopped"; if (m.value("endedAt").toString().isEmpty()) m["endedAt"] = isoNow(); }
        // 舊版把事件內嵌在 network.json：搬到獨立的 JSONL，避免整份載入記憶體
        QVariantList emb = m.value("events").toList();
        if (!emb.isEmpty() && !QFile::exists(sessionLog(m.value("id").toString()))) {
            QDir().mkpath(networkDir());
            QFile f(sessionLog(m.value("id").toString()));
            if (f.open(QIODevice::WriteOnly)) {
                for (const auto &ev : emb) f.write(QJsonDocument(QJsonObject::fromVariantMap(ev.toMap())).toJson(QJsonDocument::Compact) + "\n");
            }
        }
        m["events"] = QVariantList();
        if (!m.contains("events_n") || !emb.isEmpty()) m["events_n"] = emb.isEmpty() ? m.value("events_n", 0).toInt() : emb.size();
        if (!m.contains("lines")) m["lines"] = QString();
        out.append(m);
        total += m.value("bytes").toLongLong();
    }
    m_sessions = out;
    qint64 disk = 0;
    QDirIterator it(networkDir(), QDir::Files, QDirIterator::Subdirectories);
    while (it.hasNext()) { it.next(); disk += it.fileInfo().size(); }
    m_networkSize = Native::humanSize(disk ? disk : total);
}

void Backend::saveSessionsJson() {
    QJsonArray arr;
    for (const auto &v : m_sessions) {
        QVariantMap m = v.toMap();
        if (m.value("ephemeral").toBool()) continue;
        m["events"] = QVariantList();
        arr.append(QJsonObject::fromVariantMap(m));
    }
    writeJson("network.json", QJsonDocument(arr));
    qint64 disk = 0;
    QDirIterator it(networkDir(), QDir::Files, QDirIterator::Subdirectories);
    while (it.hasNext()) { it.next(); disk += it.fileInfo().size(); }
    m_networkSize = Native::humanSize(disk);
}

QVariantList Backend::sessionEvents(const QVariant &a0, const QVariant &a1, const QVariant &a2) {
    QVariantList out;
    QString sid = a0.toString(); int offset = qMax(0, a1.toInt()), limit = qBound(1, a2.toInt(), 5000);
    QFile f(sessionLog(sid));
    if (!f.open(QIODevice::ReadOnly)) return out;
    int n = 0;
    while (!f.atEnd()) {
        QByteArray line = f.readLine();
        if (n++ < offset) continue;
        QJsonObject o = QJsonDocument::fromJson(line).object();
        if (!o.isEmpty()) out.append(o.toVariantMap());
        if (out.size() >= limit) break;
    }
    return out;
}

QString Backend::sessionRaw(const QVariant &a0, const QVariant &a1) {
    QFile f(sessionLog(a0.toString()));
    if (!f.open(QIODevice::ReadOnly)) return QString();
    int cap = qBound(1024, a1.toInt(), 8 * 1024 * 1024);
    QByteArray data = f.read(cap);
    QString s = QString::fromUtf8(data);
    if (f.size() > cap) s += QStringLiteral("\n… 已截斷，僅顯示前 %1 KB；完整內容請匯出").arg(cap / 1024);
    return s;
}

void Backend::removeSessionFiles(const QString &sid) {
    if (QFile *f = m_logs.take(sid)) { f->close(); f->deleteLater(); }
    QFile::remove(sessionLog(sid));
    QDir(networkDir() + "/bodies/" + sid).removeRecursively();
}

void Backend::deleteSession(const QVariant &a0) {
    QString sid = a0.toString();
    int i = sessionIndex(sid);
    if (i < 0 || m_sessions.at(i).toMap().value("status").toString() == "active") { emit toast(QStringLiteral("進行中的工作階段不可刪除")); return; }
    removeSessionFiles(sid);
    m_sessions.removeAt(i); saveSessionsJson(); emit sessionsChanged(); emit toast(QStringLiteral("已刪除工作階段"));
}
void Backend::deleteSessions(const QVariant &a0) {
    QVariantList ids = a0.toList();
    QVariantList keep; int removed = 0;
    for (const auto &v : m_sessions) {
        QVariantMap m = v.toMap();
        if (ids.contains(m.value("id")) && m.value("status").toString() != "active") { removeSessionFiles(m.value("id").toString()); ++removed; }
        else keep.append(v);
    }
    m_sessions = keep; saveSessionsJson(); emit sessionsChanged();
    emit toast(QStringLiteral("已刪除 ") + QString::number(removed) + QStringLiteral(" 筆紀錄"));
}
void Backend::clearSessions() {
    QVariantList keep;
    for (const auto &v : m_sessions) {
        QVariantMap m = v.toMap();
        if (m.value("status").toString() == "active") keep.append(v); else removeSessionFiles(m.value("id").toString());
    }
    m_sessions = keep; saveSessionsJson(); emit sessionsChanged(); emit toast(QStringLiteral("已清除全部網路紀錄"));
}

void Backend::applyRetention() {
    if (m_settings.value("networkMode", "keep").toString() != "expire") return;
    qint64 mins = qMax<qint64>(1, m_settings.value("retention", 1440).toLongLong());
    QDateTime cutoff = QDateTime::currentDateTime().addSecs(-mins * 60);
    QVariantList keep; bool changed = false;
    for (const auto &v : m_sessions) {
        QVariantMap m = v.toMap();
        QDateTime end = QDateTime::fromString(m.value("endedAt").toString(), "yyyy-MM-ddTHH:mm:ss");
        if (m.value("status").toString() != "active" && end.isValid() && end < cutoff) { removeSessionFiles(m.value("id").toString()); changed = true; }
        else keep.append(v);
    }
    if (changed) { m_sessions = keep; saveSessionsJson(); emit sessionsChanged(); }
}

void Backend::exportSessions() {
    if (m_sessions.isEmpty()) { emit toast(QStringLiteral("目前沒有網路紀錄可匯出")); return; }
    QString path = exportPath("sessions") + ".json";
    QFile f(path);
    if (!f.open(QIODevice::WriteOnly)) { emit toast(QStringLiteral("匯出失敗")); return; }
    QJsonArray arr;
    for (const auto &v : m_sessions) { QVariantMap m = v.toMap(); m.remove("events"); arr.append(QJsonObject::fromVariantMap(m)); }
    f.write(QJsonDocument(arr).toJson(QJsonDocument::Indented)); f.close();
    emit toast(QStringLiteral("已匯出網路紀錄：") + QFileInfo(path).fileName());
}

void Backend::exportSession(const QVariant &a0) {
    QString sid = a0.toString();
    int i = sessionIndex(sid);
    if (i < 0) { emit toast(QStringLiteral("找不到工作階段")); return; }
    QVariantMap meta = m_sessions.at(i).toMap(); meta.remove("events");
    QString path = exportPath("session-" + sid) + ".json";
    QFile out(path);
    if (!out.open(QIODevice::WriteOnly)) { emit toast(QStringLiteral("匯出失敗")); return; }
    // 串流寫出：{ ...meta, "events":[ ... ] }，本文以 Base64 無損承載
    QByteArray head = QJsonDocument(QJsonObject::fromVariantMap(meta)).toJson(QJsonDocument::Compact);
    head.chop(1);
    out.write(head); out.write(",\"events\":[");
    QFile in(sessionLog(sid));
    bool first = true;
    if (in.open(QIODevice::ReadOnly)) {
        while (!in.atEnd()) {
            QJsonObject o = QJsonDocument::fromJson(in.readLine()).object();
            if (o.isEmpty()) continue;
            QString att = o.value("bodyAttachmentId").toString();
            if (!att.isEmpty()) {
                QFile b(networkDir() + "/bodies/" + sid + "/" + att + ".bin");
                if (b.open(QIODevice::ReadOnly)) { o["bodyBase64"] = QString::fromLatin1(b.readAll().toBase64()); o["bodyEncoding"] = "base64"; }
            }
            if (!first) out.write(",");
            first = false;
            out.write(QJsonDocument(o).toJson(QJsonDocument::Compact));
        }
    }
    out.write("]}\n"); out.close();
    emit toast(QStringLiteral("已匯出 ") + QFileInfo(path).fileName());
}

// Automation 的訊號
// ============================================================ 課程開啟（原生 CDP）
// ============================================================ 課程（與 CLI 共用 urls.txt）
void Backend::reloadCourses() {
    QVariantList out;
    QFile f(m_urlsPath.isEmpty() ? filePath("urls.txt") : m_urlsPath);
    QJsonObject usage = readObject("course_usage.json");
    if (!f.open(QIODevice::ReadOnly)) { m_courses = out; return; }
    QString group = QStringLiteral("未分類"), category;
    int id = 0;
    QSet<QString> seen;
    auto dec = [](const QString &s) { QString d = QUrl::fromPercentEncoding(s.toUtf8()); return d.isEmpty() ? s : d; };
    static const QRegularExpression gr(QStringLiteral("^#\\s*group:\\s*(.*)$"), QRegularExpression::CaseInsensitiveOption);
    static const QRegularExpression cr(QStringLiteral("^#\\s*category:\\s*(.*)$"), QRegularExpression::CaseInsensitiveOption);
    while (!f.atEnd()) {
        QString line = QString::fromUtf8(f.readLine()).trimmed();
        auto gm = gr.match(line), cm = cr.match(line);
        if (gm.hasMatch()) { group = dec(gm.captured(1).trimmed()); if (group.isEmpty()) group = QStringLiteral("未分類"); category.clear(); continue; }
        if (cm.hasMatch()) { category = dec(cm.captured(1).trimmed()); continue; }
        if (!line.startsWith("http", Qt::CaseInsensitive)) continue;
        if (seen.contains(line)) continue;
        seen.insert(line);
        QVariantMap m;
        QString cat = category.isEmpty() ? group : category;
        // 別名沿用 normalizeCourseAlias：舊資料別名為「未分類」但分類已更新時跟隨分類
        QString alias = group;
        if (alias == QStringLiteral("未分類") && cat != QStringLiteral("未分類")) alias = cat;
        QJsonObject u = usage.value(line).toObject();
        m["id"] = ++id; m["url"] = line; m["category"] = cat; m["alias"] = alias;
        m["opens"] = u.value("opens").toInt();
        m["openedAt"] = u.value("last").toString();
        m["opened"] = u.contains("last") ? fmtStamp(u.value("last").toString()) : QStringLiteral("尚未開啟");
        out.append(m);
    }
    m_courses = out;
}

void Backend::saveCourses() {
    // 依 (別名, 分類) 分組，輸出 CLI 相容的 urls.txt（# group: / # category: 以 URL 編碼）
    QList<QPair<QPair<QString, QString>, QStringList>> groups;
    for (const auto &v : m_courses) {
        QVariantMap c = v.toMap();
        QString alias = c.value("alias").toString().trimmed(), cat = c.value("category").toString();
        if (alias.isEmpty()) alias = cat;
        QPair<QString, QString> key(alias, cat);
        bool found = false;
        for (auto &g : groups) if (g.first == key) { g.second << c.value("url").toString(); found = true; break; }
        if (!found) groups.append({ key, QStringList{ c.value("url").toString() } });
    }
    QStringList lines;
    lines << "# Cool English 課程網址清單"
          << "# 最後更新時間: " + QDateTime::currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
          << "# 每行一個網址，支援 cool -u 快速選取或依序瀏覽" << "";
    auto enc = [](const QString &s) { return QString::fromLatin1(QUrl::toPercentEncoding(s, QByteArray(), QByteArray())); };
    for (const auto &g : groups) {
        lines << "# group: " + enc(g.first.first) << "# category: " + enc(g.first.second);
        lines << g.second << "";
    }
    QString path = m_urlsPath.isEmpty() ? filePath("urls.txt") : m_urlsPath;
    QByteArray data = (lines.join("\n") + "\n").toUtf8();
    m_selfWriteUrls = data;
    Native::atomicWrite(path, data);
}

void Backend::addCourse(const QVariant &a0, const QVariant &a1, const QVariant &a2) {
    QString url = a0.toString().trimmed(), cat = a1.toString().trimmed(), alias = a2.toString().trimmed();
    QUrl q(url);
    if (!q.isValid() || (q.scheme() != "http" && q.scheme() != "https")) { emit toast(QStringLiteral("只接受 http 或 https 網址。")); return; }
    if (cat.isEmpty()) cat = QStringLiteral("未分類");
    if (cat.size() > 64 || alias.size() > 64) { emit toast(QStringLiteral("課程分類／別名不得超過 64 個字元。")); return; }
    auto norm = [](QString u) {
        QUrl q(u.trimmed()); q.setFragment(QString());
        QString t = q.toString(QUrl::FullyEncoded).toLower().left(8) + q.toString(QUrl::FullyEncoded).mid(8);
        while (t.endsWith('/')) t.chop(1);
        return t;
    };
    for (const auto &v : m_courses) {
        QVariantMap c = v.toMap();
        if (norm(c.value("url").toString()) == norm(url)) {
            emit toast(QStringLiteral("重複網址，已拒絕加入：已存在於「%1」").arg(c.value("alias").toString())); return;
        }
    }
    QVariantMap m; m["id"] = m_courses.size() + 1; m["url"] = url; m["category"] = cat;
    m["alias"] = alias.isEmpty() ? cat : alias; m["opens"] = 0; m["opened"] = QStringLiteral("尚未開啟"); m["openedAt"] = QString();
    m_courses.append(m);
    courseChanged();
    emit toast(QStringLiteral("已儲存 1 個網址（與 cool -u 同步）"));
}

void Backend::setCourseCategory(const QVariant &a0, const QVariant &a1) {
    int i = a0.toInt(); QString cat = a1.toString().trimmed();
    if (cat.isEmpty() || cat.size() > 64) { emit toast(QStringLiteral("課程分類不可空白，且不得超過 64 個字元。")); return; }
    if (i >= 0 && i < m_courses.size()) {
        QVariantMap m = m_courses.at(i).toMap();
        QString prev = m.value("category").toString();
        m["category"] = cat;
        if (m.value("alias").toString() == prev) m["alias"] = cat;       // 預設別名跟隨分類
        m_courses[i] = m;
        courseChanged(); emit toast(QStringLiteral("分類已更新"));
    }
}

// ============================================================ CLI 雙向同步
void Backend::initCliSync() {
    QString dir = cliDir();
    QDir().mkpath(dir);
    m_urlsPath = QDir(dir).filePath("urls.txt");
    // 首次：若桌面資料夾有舊的 urls.txt 而 CLI 沒有，搬過去
    if (!QFile::exists(m_urlsPath) && QFile::exists(filePath("urls.txt"))) QFile::copy(filePath("urls.txt"), m_urlsPath);
    // 舊版 password_enc（CLI 的 XOR）→ 桌面 DPAPI 憑證，並從桌面 accounts.json 移除明文可逆欄位
    QJsonArray raw = readArray("accounts.json");
    bool dirty = false;
    for (int i = 0; i < raw.size(); ++i) {
        QJsonObject o = raw.at(i).toObject();
        QString enc = o.value("password_enc").toString();
        if (enc.isEmpty()) continue;
        QString email = o.value("email").toString(), pw;
        if (!readCreds().contains(email.toLower()) && Native::decryptCliPassword(enc, o.value("password_len").toInt(), &pw)) saveCredentialFor(email, pw);
        o.remove("password_enc"); o.remove("password_len"); raw.replace(i, o); dirty = true;
    }
    if (dirty) saveRaw(raw);
    syncFromCli();
    syncCliColors(true);
    syncToCli();
    reloadCourses();
    m_cliWatch = new QFileSystemWatcher(this);
    m_syncTimer = new QTimer(this);
    m_syncTimer->setSingleShot(true); m_syncTimer->setInterval(450);
    connect(m_syncTimer, &QTimer::timeout, this, &Backend::onCliChanged);
    auto rewatch = [this, dir] {
        for (const char *n : { "accounts.json", "colors.json", "urls.txt" }) {
            QString p = QDir(dir).filePath(QString::fromLatin1(n));
            if (QFile::exists(p) && !m_cliWatch->files().contains(p)) m_cliWatch->addPath(p);
        }
        if (!m_cliWatch->directories().contains(dir)) m_cliWatch->addPath(dir);
    };
    rewatch();
    connect(m_cliWatch, &QFileSystemWatcher::fileChanged, this, [this, rewatch](const QString &) { rewatch(); m_syncTimer->start(); });
    connect(m_cliWatch, &QFileSystemWatcher::directoryChanged, this, [this, rewatch](const QString &) { rewatch(); m_syncTimer->start(); });
}

void Backend::onCliChanged() {
    bool acc = syncFromCli();
    bool col = syncCliColors(false);
    QByteArray cur;
    { QFile f(m_urlsPath); if (f.open(QIODevice::ReadOnly)) cur = f.readAll(); }
    if (cur != m_selfWriteUrls && cur != m_lastUrlsSeen) { m_lastUrlsSeen = cur; reloadCourses(); emit coursesChanged(); }
    if (acc) { reloadAccounts(); emit accountsChanged(); emit reportsChanged(); }
    if (col) { pushTermConfig(); emit settingsChanged(); }
}

bool Backend::syncFromCli() {
    QString dir = cliDir();
    QFile f(QDir(dir).filePath("accounts.json"));
    if (!f.open(QIODevice::ReadOnly)) return false;
    QJsonDocument d = QJsonDocument::fromJson(f.readAll());
    f.close();
    if (!d.isArray()) return false;
    bool anyChange = false;
    QJsonArray desk = readArray("accounts.json");
    for (const auto &item : d.array()) {
        QJsonObject s = item.toObject();
        QString name = s.value("name").toString(), email = s.value("email").toString(), ck = s.value("cookie_file").toString();
        if (name.isEmpty() || email.isEmpty() || ck.isEmpty()) continue;
        QString cpath = QDir::cleanPath(QDir(dir).absoluteFilePath(ck));
        if (!underDir(dir, cpath) || !QFile::exists(cpath)) continue;
        QJsonObject existing;
        for (const auto &v : desk) if (v.toObject().value("email").toString().compare(email, Qt::CaseInsensitive) == 0) existing = v.toObject();
        qint64 saved = existing.isEmpty() ? 0 : QDateTime::fromString(existing.value("last_login").toString(), Qt::ISODate).toMSecsSinceEpoch();
        QDateTime srcLogin = QDateTime::fromString(s.value("last_login").toString(), Qt::ISODate);
        bool newer = srcLogin.isValid() && srcLogin.toMSecsSinceEpoch() > saved;
        bool changed = false;
        if (existing.isEmpty() || newer) {
            QFile cf(cpath);
            if (!cf.open(QIODevice::ReadOnly)) continue;
            QString text = QString::fromUtf8(cf.readAll());
            if (text.startsWith("#COOL_ENCRYPTED_V1")) continue;
            QList<Native::Cookie> cookies = Native::parseNetscape(text);
            QString err;
            if (!saveLogin(email, name, cookies, s.value("user_id").toString(), &err)) continue;
            // 保留 CLI 帳號紀錄的登入時間，避免來回同步反覆覆寫
            QJsonArray cur = readArray("accounts.json");
            for (int i = 0; i < cur.size(); ++i) {
                QJsonObject o = cur.at(i).toObject();
                if (o.value("email").toString().compare(email, Qt::CaseInsensitive) == 0 && srcLogin.isValid()) {
                    o["last_login"] = s.value("last_login").toString(); cur.replace(i, o);
                }
            }
            saveRaw(cur);
            desk = cur;
            changed = true;
        }
        QString enc = s.value("password_enc").toString();
        if (!enc.isEmpty()) {
            int len = s.value("password_len").toInt();
            QJsonObject cr = readCreds();
            if (!cr.contains(email.toLower()) || newer) {
                QString pw;
                if (Native::decryptCliPassword(enc, len, &pw)) { saveCredentialFor(email, pw); changed = true; }
            }
        }
        // Google 頭像：CLI 登入時下載到 <cli>/avatars，這裡複製成桌面使用的頭像
        const QString avRel = s.value("avatar_file").toString();
        if (!avRel.isEmpty()) {
            const QString src = QDir::cleanPath(QDir(dir).absoluteFilePath(avRel));
            if (underDir(dir, src) && QFile::exists(src)) {
                const QString ext = QFileInfo(src).suffix().toLower();
                const QString stem = emailStem(email);
                const QString dest = filePath("avatars/" + stem + "." + ext);
                if (!QFile::exists(dest) || QFileInfo(src).lastModified() > QFileInfo(dest).lastModified()) {
                    QDir().mkpath(filePath("avatars"));
                    for (const char *e : { "png", "jpg", "jpeg", "webp", "gif" }) QFile::remove(filePath("avatars/" + stem + "." + QString::fromLatin1(e)));
                    if (QFile::copy(src, dest)) changed = true;
                }
            }
        }
        anyChange = anyChange || changed;
    }
    return anyChange;
}

void Backend::syncToCli() {
    QString dir = cliDir();
    QDir().mkpath(dir + "/cookies");
    QFile f(QDir(dir).filePath("accounts.json"));
    QJsonArray cli;
    if (f.open(QIODevice::ReadOnly)) { QJsonDocument d = QJsonDocument::fromJson(f.readAll()); if (d.isArray()) cli = d.array(); f.close(); }
    QJsonArray orig = cli;
    for (const auto &v : readArray("accounts.json")) {
        QJsonObject a = v.toObject();
        QString email = a.value("email").toString();
        if (a.value("cookie_file").toString().isEmpty()) continue;
        QString cpath = cookiePathFor(a.value("cookie_file").toString());
        if (!QFile::exists(cpath)) continue;
        QList<Native::Cookie> cookies = loadCookies(email);
        if (cookies.isEmpty()) continue;
        int mi = -1;
        for (int i = 0; i < cli.size(); ++i) if (cli.at(i).toObject().value("email").toString().compare(email, Qt::CaseInsensitive) == 0) { mi = i; break; }
        QJsonObject existing = mi >= 0 ? cli.at(mi).toObject() : QJsonObject();
        QString ckRel = existing.value("cookie_file").toString();
        if (ckRel.isEmpty() || !underDir(dir + "/cookies", QDir(dir).absoluteFilePath(ckRel)))
            ckRel = "cookies/desktop-" + Native::emailCookieName(email);
        QString text = Native::serializeNetscape(cookies);
        QString full = QDir(dir).absoluteFilePath(ckRel);
        QFile cf(full);
        QString cur; if (cf.open(QIODevice::ReadOnly)) { cur = QString::fromUtf8(cf.readAll()); cf.close(); }
        if (cur != text) Native::atomicWrite(full, text.toUtf8());
        existing["name"] = a.value("name"); existing["email"] = email; existing["cookie_file"] = ckRel;
        if (a.contains("created_at")) existing["created_at"] = a.value("created_at");
        if (a.contains("last_login")) existing["last_login"] = a.value("last_login");
        if (a.contains("user_id")) existing["user_id"] = a.value("user_id");
        if (mi >= 0) cli.replace(mi, existing); else cli.append(existing);
    }
    if (cli != orig) Native::atomicWrite(QDir(dir).filePath("accounts.json"), QJsonDocument(cli).toJson(QJsonDocument::Indented));
}

void Backend::removeCliAccount(const QString &email) {
    QString dir = cliDir();
    QFile f(QDir(dir).filePath("accounts.json"));
    if (!f.open(QIODevice::ReadOnly)) return;
    QJsonDocument d = QJsonDocument::fromJson(f.readAll()); f.close();
    if (!d.isArray()) return;
    QJsonArray rest; QStringList kill;
    for (const auto &v : d.array()) {
        QJsonObject o = v.toObject();
        if (o.value("email").toString().compare(email, Qt::CaseInsensitive) == 0) kill << o.value("cookie_file").toString(); else rest.append(o);
    }
    for (const QString &k : kill) {
        QString p = QDir::cleanPath(QDir(dir).absoluteFilePath(k));
        bool referenced = false;
        for (const auto &v : rest) if (QDir::cleanPath(QDir(dir).absoluteFilePath(v.toObject().value("cookie_file").toString())) == p) referenced = true;
        if (!k.isEmpty() && underDir(dir + "/cookies", p) && !referenced) QFile::remove(p);
    }
    Native::atomicWrite(QDir(dir).filePath("accounts.json"), QJsonDocument(rest).toJson(QJsonDocument::Indented));
}

// colors.json ↔ 設定：終端三色 + CLI 報表七色
struct CliKey { const char *qml, *cli; };
static const CliKey kCliKeys[] = { {"title","title"}, {"titleText","title_text"}, {"header","header"}, {"current","cur"}, {"below","low"}, {"url","url"}, {"sep","sep"} };

bool Backend::syncCliColors(bool initial) {
    QString path = QDir(cliDir()).filePath("colors.json");
    QJsonObject colors;
    { QFile f(path); if (f.open(QIODevice::ReadOnly)) { QJsonDocument d = QJsonDocument::fromJson(f.readAll()); if (d.isObject()) colors = d.object(); } }
    bool changed = false;
    auto hex = [](const QString &s) { static const QRegularExpression re("^#[0-9a-fA-F]{6}$"); return re.match(s).hasMatch(); };
    struct Map { const char *cli; const char *key; } tmap[] = { { "terminal_cursor_color", "terminalCursor" }, { "terminal_text_color", "terminalText" }, { "terminal_background_color", "terminalBg" } };
    for (auto &m : tmap) {
        QString v = colors.value(QString::fromLatin1(m.cli)).toString().toLower();
        if (hex(v) && m_settings.value(QString::fromLatin1(m.key)).toString().toLower() != v) { m_settings[QString::fromLatin1(m.key)] = v; changed = true; }
    }
    QVariantMap cc = m_settings.value("cliColors").toMap();
    for (const auto &k : kCliKeys) {
        QString v = colors.value(QString::fromLatin1(k.cli)).toString();
        if (!v.isEmpty() && cc.value(QString::fromLatin1(k.qml)).toString() != v) { cc[QString::fromLatin1(k.qml)] = v; changed = true; }
    }
    if (changed) { m_settings["cliColors"] = cc; saveSettings(); }
    if (initial) writeCliColors();
    return changed;
}

void Backend::writeCliColors() {
    QString path = QDir(cliDir()).filePath("colors.json");
    QJsonObject colors;
    { QFile f(path); if (f.open(QIODevice::ReadOnly)) { QJsonDocument d = QJsonDocument::fromJson(f.readAll()); if (d.isObject()) colors = d.object(); } }
    QJsonObject before = colors;
    colors["terminal_cursor_color"] = m_settings.value("terminalCursor", "#d0afff").toString();
    colors["terminal_text_color"] = m_settings.value("terminalText", "#f2e8ff").toString();
    colors["terminal_background_color"] = m_settings.value("terminalBg", "#1a1030").toString();
    QVariantMap cc = m_settings.value("cliColors").toMap();
    for (const auto &k : kCliKeys) {
        QString v = cc.value(QString::fromLatin1(k.qml)).toString();
        if (v.isEmpty()) v = defaultCliColor(QString::fromLatin1(k.qml));
        colors[QString::fromLatin1(k.cli)] = v;
    }
    if (colors != before) Native::atomicWrite(path, QJsonDocument(colors).toJson(QJsonDocument::Indented));
}

QString Backend::defaultCliColor(const QString &key) const {
    if (key == "title") return "MAGENTA"; if (key == "titleText") return "WHITE"; if (key == "header") return "CYAN";
    if (key == "current") return "REVERSE"; if (key == "below") return "RED_BG_WHITE"; return "DIM";
}

void Backend::quitApp() {
    shutdownTerminal();
    QCoreApplication::quit();
}

// xterm 256 色 → #rrggbb
static QString xterm256(int n) {
    static const int base16[16][3] = { {0,0,0},{205,49,49},{13,188,121},{229,229,16},{36,114,200},{188,63,188},{17,168,205},{229,229,229},
                                       {102,102,102},{241,76,76},{35,209,139},{245,245,67},{59,142,234},{214,112,214},{41,184,219},{255,255,255} };
    n = qBound(0, n, 255);
    int r, g, b;
    if (n < 16) { r = base16[n][0]; g = base16[n][1]; b = base16[n][2]; }
    else if (n < 232) {
        int i = n - 16; int lv[6] = { 0, 95, 135, 175, 215, 255 };
        r = lv[i / 36]; g = lv[(i / 6) % 6]; b = lv[i % 6];
    } else { r = g = b = 8 + (n - 232) * 10; }
    return QColor(r, g, b).name();
}

QVariantMap Backend::cliStyle(const QVariant &a0) {
    const QString key = a0.toString();
    for (const auto &v : m_cliStyles) {
        QVariantMap m = v.toMap();
        if (m.value("key").toString() == key) return m;
    }
    QVariantMap out; out["key"] = key; out["name"] = QStringLiteral("自訂"); out["fg"] = "#d7dde5"; out["bg"] = QVariant();
    static const QRegularExpression hexRe(QStringLiteral("^#[0-9a-fA-F]{6}$")), fgRe(QStringLiteral("^COLOR_(\\d{3})$")), bgRe(QStringLiteral("^BG_(\\d{3})$"));
    if (hexRe.match(key).hasMatch()) { out["name"] = key; out["fg"] = key; }
    else if (key.startsWith(QLatin1String("bg:#"), Qt::CaseInsensitive) && hexRe.match(key.mid(3)).hasMatch()) {
        out["name"] = key; out["fg"] = "#101418"; out["bg"] = key.mid(3);     // CLI 的自訂背景色 bg:#rrggbb
    }
    else if (auto m = fgRe.match(key); m.hasMatch()) { out["name"] = key; out["fg"] = xterm256(m.captured(1).toInt()); }
    else if (auto m2 = bgRe.match(key); m2.hasMatch()) { out["name"] = key; out["fg"] = "#101418"; out["bg"] = xterm256(m2.captured(1).toInt()); }
    return out;
}

// ============================================================ 終端設定 / 剪貼簿（給 xterm.js 用）
void TermConfig::copyText(const QString &t) { if (!t.isEmpty()) QGuiApplication::clipboard()->setText(t); }
QString TermConfig::pasteText() { return QGuiApplication::clipboard()->text(); }

void Backend::pushTermConfig() {
    if (!m_termCfg) return;
    QJsonObject o;
    o["background"] = m_settings.value("terminalBg", "#1e1e1e").toString();
    o["foreground"] = m_settings.value("terminalText", "#d4d4d4").toString();
    o["cursor"] = m_settings.value("terminalCursor", "#aeafad").toString();
    o["fontSize"] = qBound(10, m_settings.value("terminalFontSize", 13).toInt(), 24);
    o["fontFamily"] = m_settings.value("terminalFont", "Cascadia Mono").toString();
    m_termCfg->setJson(QString::fromUtf8(QJsonDocument(o).toJson(QJsonDocument::Compact)));
}
