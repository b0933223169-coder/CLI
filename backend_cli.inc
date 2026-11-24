// 以 cool.py 為邏輯核心：桌面只是外殼。所有登入／報表／Cookie 檢查／課程開啟都以隱藏的
// `python cool.py ...` 子行程執行；輸出的 @@COOL_PLAYWRIGHT_LOG@@ 事件轉成網路紀錄，
// 互動提示（選帳號、輸入帳密、安裝確認）由本檔自動回覆。帳號/Cookie 由 CLI 寫檔，再由檔案同步帶回桌面。
#include <QProcess>
#include <QProcessEnvironment>

struct CliRule { QRegularExpression re; QString send; int left; };
struct CliJob {
    QProcess *proc = nullptr;
    QString sid, mode, email, kind;       // kind: login / report / cookie / course
    QByteArray raw;                       // 尚未形成完整行的位元組
    QString tail;                         // 供提示比對
    QString all;                          // 完整輸出（解析報表用）
    QList<CliRule> rules;
    QHash<QString, qint64> reqAt;
    QElapsedTimer clock;
    bool stopped = false;
    std::function<void(int, const QString &)> done;
};

namespace {
QString stripAnsi(QString s) {
    static const QRegularExpression re(QStringLiteral("\x1b\\[[0-9;?]*[A-Za-z]"));
    s.remove(re);
    return s;
}
}

int Backend::cliAccountIndex(const QString &email) const {
    QFile f(QDir(cliDir()).filePath("accounts.json"));
    if (!f.open(QIODevice::ReadOnly)) return -1;
    const QJsonArray a = QJsonDocument::fromJson(f.readAll()).array();
    for (int i = 0; i < a.size(); ++i)
        if (a.at(i).toObject().value("email").toString().compare(email, Qt::CaseInsensitive) == 0) return i;
    return -1;
}

int Backend::cliAccountCount() const {
    QFile f(QDir(cliDir()).filePath("accounts.json"));
    if (!f.open(QIODevice::ReadOnly)) return 0;
    return QJsonDocument::fromJson(f.readAll()).array().size();
}

QString Backend::runCli(const QStringList &args, const QString &kind, const QString &mode, const QString &label,
                        const QString &email, const QList<QPair<QString, QString>> &rules,
                        std::function<void(int, const QString &)> done) {
    QString py = consolePython();
    QString script = QDir(cliDir()).filePath("cool.py");
    if (py.isEmpty() || !QFile::exists(script)) {
        emit toast(QStringLiteral("找不到 Python 或 cool.py，無法執行 CLI"));
        return QString();
    }
    syncToCli();                                   // 讓 CLI 看到桌面最新的帳號與 Cookie
    QString sid = QStringLiteral("c%1").arg(QDateTime::currentMSecsSinceEpoch());
    createSession(mode, label, email, sid);
    auto *job = new CliJob;
    job->sid = sid; job->mode = mode; job->email = email; job->kind = kind; job->done = done;
    for (const auto &r : rules) job->rules.append({ QRegularExpression(r.first), r.second, 0 });
    job->clock.start();
    job->proc = new QProcess(this);
    job->proc->setWorkingDirectory(cliDir());
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONUTF8", "1"); env.insert("PYTHONIOENCODING", "utf-8"); env.insert("COOL_GUI_LOG", "1");
    job->proc->setProcessEnvironment(env);
    job->proc->setProcessChannelMode(QProcess::MergedChannels);
    m_cliJobs.insert(sid, job);
    connect(job->proc, &QProcess::readyRead, this, [this, sid] { onCliOutput(sid); });
    connect(job->proc, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished), this, [this, sid](int code, QProcess::ExitStatus) {
        onCliOutput(sid);
        CliJob *j = m_cliJobs.take(sid);
        if (!j) return;
        if (!j->raw.isEmpty()) handleCliLine(j, QString::fromUtf8(j->raw));
        bool bad = code != 0 || ((j->kind == "report" || j->kind == "login") && (j->all.contains("[FAILED]") || j->all.contains("請重新 cool -l")));
        finishSession(sid, j->stopped ? "stopped" : (bad ? "failed" : "completed"), QString());
        auto cb = j->done; QString out = j->all;
        j->proc->deleteLater(); delete j;
        syncFromCli(); reloadAccounts(); emit accountsChanged();
        if (cb) cb(code, out);
    });
    job->proc->start(py, QStringList() << script << args);
    return sid;
}

void Backend::onCliOutput(const QString &sid) {
    CliJob *j = m_cliJobs.value(sid);
    if (!j) return;
    QByteArray chunk = j->proc->readAll();
    if (!qEnvironmentVariableIsEmpty("COOL_CLI_LOG")) {
        QFile lf(qEnvironmentVariable("COOL_CLI_LOG")); if (lf.open(QIODevice::Append)) { lf.write(chunk); lf.write("\n<<chunk>>\n"); }
    }
    j->raw += chunk;
    int nl;
    while ((nl = j->raw.indexOf('\n')) >= 0) {
        QString line = QString::fromUtf8(j->raw.left(nl)); j->raw.remove(0, nl + 1);
        if (line.endsWith('\r')) line.chop(1);
        handleCliLine(j, line);
        j->tail.clear();
    }
    // 尚未換行的尾端 = 可能是提示
    j->tail += stripAnsi(QString::fromUtf8(j->raw));
    for (auto &r : j->rules) {
        if (r.left == 0 && r.re.match(j->tail).hasMatch()) {
            j->proc->write((r.send + "\n").toUtf8());
            j->raw.clear(); j->tail.clear();
            break;
        }
    }
    // 結束時的 Enter 提示（課程工作階段）與人工驗證提示
    if (j->tail.contains(QStringLiteral("完成後按 Enter")) && !j->all.contains(QStringLiteral("@@MANUAL@@"))) {
        j->all += QStringLiteral("@@MANUAL@@\n");
        emit toast(QStringLiteral("CLI 需要你在瀏覽器完成驗證（MFA／通行密鑰／CAPTCHA）；完成後到「網路紀錄 › 正在運行」按終止，或在終端機執行 cool -l。"));
    }
}

void Backend::handleCliLine(CliJob *j, const QString &rawLine) {
    static const QString marker = QStringLiteral("@@COOL_PLAYWRIGHT_LOG@@");
    QString line = stripAnsi(rawLine);
    int mi = line.indexOf(marker);
    if (mi >= 0) {
        QJsonObject o = QJsonDocument::fromJson(line.mid(mi + marker.size()).toUtf8()).object();
        QString ev = o.value("event").toString(), url = o.value("url").toString();
        QString key = o.value("method").toString() + " " + url;
        QVariantMap e; e["url"] = url; e["path"] = QUrl(url).path();
        e["headers"] = o.value("headers").toObject().toVariantMap();
        if (ev == "request") {
            j->reqAt[url] = j->clock.elapsed();
            e["kind"] = "request"; e["method"] = o.value("method").toString(); e["status"] = 0; e["ms"] = 0; e["bytes"] = 0; e["size"] = "—";
        } else if (ev == "response") {
            qint64 bytes = o.value("headers").toObject().value("content-length").toString().toLongLong();
            e["kind"] = "response"; e["method"] = "GET"; e["status"] = o.value("status").toInt();
            e["ms"] = int(j->clock.elapsed() - j->reqAt.take(url)); e["bytes"] = bytes; e["size"] = bytes ? Native::humanSize(bytes) : QStringLiteral("—");
            if (!o.value("body").isNull() && m_settings.value("captureRaw", false).toBool()) {
                const QString dir = filePath("network") + "/bodies/" + j->sid; QDir().mkpath(dir);
                QString id = QStringLiteral("r%1").arg(++m_bodySeq);
                QFile f(dir + "/" + id + ".bin");
                if (f.open(QIODevice::WriteOnly)) { f.write(o.value("body").toString().toUtf8()); f.close(); e["bodyAttachmentId"] = id; e["bodyBytes"] = int(f.size()); e["bodySource"] = "response"; }
            }
        } else if (ev == "requestfailed") {
            e["kind"] = "failed"; e["method"] = o.value("method").toString(); e["status"] = 0; e["ms"] = 0; e["bytes"] = 0; e["size"] = "—";
            e["message"] = o.value("failure").toString();
        } else return;
        recordEvent(j->sid, e);
        return;
    }
    static const QRegularExpression envLine(QStringLiteral("^(標準庫|本地模組|第三方套件) .*\\[ +(OK|SKIP|DEPEND) +\\]$"));
    if (envLine.match(line.trimmed()).hasMatch()) return;          // 環境檢查的逐行輸出不顯示
    j->all += line + "\n";
    int i = sessionIndex(j->sid);
    if (i >= 0 && !line.trimmed().isEmpty()) {
        QVariantMap s = m_sessions.at(i).toMap();
        QString raw = rawLine; if (raw.endsWith('\r')) raw.chop(1);
        QString lines = s.value("lines").toString() + raw + "\n";       // 保留 ANSI 顏色，顯示時才轉成 HTML
        if (lines.size() > 20000) lines = lines.right(20000);
        s["lines"] = lines; m_sessions[i] = s; markSessionsDirty();
    }
}

// ---------------------------------------------------------------- 對外 API
static QList<QPair<QString, QString>> commonRules() {
    return { { QStringLiteral("\\[y/n/a\\][^\\n]*$"), QStringLiteral("y") } };
}

void Backend::startLogin(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3) {
    QString email = a0.toString().trimmed(), password = a1.toString(), name = a2.toString().trimmed(), mode = a3.toString();
    if (mode != "headed" && mode != "headless") mode = m_settings.value("defaultLoginMode", "headless").toString();
    if (!email.contains('@') || password.isEmpty()) { emit toast(QStringLiteral("請輸入有效的 Email 與密碼。")); return; }
    if (m_loginBusy) { emit toast(QStringLiteral("已有登入程序在執行，請稍候")); return; }
    int idx = cliAccountIndex(email);
    int count = cliAccountCount();
    QList<QPair<QString, QString>> rules = commonRules();
    if (count > 0) rules.append({ QStringLiteral("輸入編號: ?$"), QString::number(idx >= 0 ? idx + 1 : count + 1) });
    rules.append({ QStringLiteral("帳號 \\(Google Email\\): ?$"), email });
    rules.append({ QStringLiteral("密碼[^\\n]*: ?$"), password });
    rules.append({ QStringLiteral("帳號名稱 \\(預設[^\\n]*: ?$"), name });
    QStringList args{ "-l" }; if (mode == "headed") args << "/show";
    QJsonArray raw = readArray("accounts.json");
    m_loginBusy = true;
    m_loginStatus = mode == "headed" ? QStringLiteral("正在以 cool.py 開啟瀏覽器，請完成 Google 登入…") : QStringLiteral("cool.py 正在背景登入…");
    emit loginChanged();
    QString sid = runCli(args, "login", mode, QStringLiteral("登入 ") + email, email, rules, [this, email, password](int code, const QString &out) {
        m_loginBusy = false;
        bool ok = cliAccountIndex(email) >= 0 && (out.contains(QStringLiteral("登入成功")) || out.contains(QStringLiteral("已儲存")) || code == 0)
                  && !out.contains(QStringLiteral("登入失敗")) && !out.contains(QStringLiteral("[ FAILED"));
        if (ok) saveCredentialFor(email, password);
        QString last;
        for (const QString &l : out.split('\n')) if (!l.trimmed().isEmpty()) last = l.trimmed();
        QString avatarNote;
        if (ok) {
            if (out.contains(QStringLiteral("已儲存 Google 頭像"))) avatarNote = QStringLiteral("，已更新頭像");
            else if (out.contains(QStringLiteral("找不到頭像")) || out.contains(QStringLiteral("頭像下載失敗")) || out.contains(QStringLiteral("取得頭像時發生錯誤")))
                avatarNote = QStringLiteral("，但沒有取得頭像（看網路紀錄裡的 cool.py 輸出）");
        }
        m_loginStatus = ok ? QStringLiteral("登入成功") + avatarNote : QStringLiteral("登入失敗：") + last;
        reloadAccounts(); reloadReports();
        emit accountsChanged(); emit loginChanged();
        emit toast(m_loginStatus);
        if (ok) syncToCli();
    });
    if (sid.isEmpty()) { m_loginBusy = false; m_loginStatus.clear(); emit loginChanged(); }
}

void Backend::loginAccount(const QVariant &a0, const QVariant &a1) {
    int i = a0.toInt();
    QJsonArray raw = readArray("accounts.json");
    if (i < 0 || i >= raw.size()) { emit toast(QStringLiteral("請先選擇帳號")); return; }
    QJsonObject o = raw.at(i).toObject();
    QString email = o.value("email").toString(), pwd;
    if (!getCredentialFor(email, &pwd)) {
        emit toast(o.value("name").toString() + QStringLiteral(" 沒有已保存的密碼，請在上方輸入 Email 與密碼後按「連結帳號」")); return;
    }
    startLogin(email, pwd, o.value("name").toString(), a1);
}

void Backend::addAccount(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3) { startLogin(a0, a1, a2, a3); }

void Backend::refreshReports() {
    if (m_reportBusy) { emit toast(QStringLiteral("報表正在更新，請稍候")); return; }
    QJsonArray raw = readArray("accounts.json");
    if (m_selected < 0 || m_selected >= raw.size()) { emit toast(QStringLiteral("請先新增並登入一個帳號")); return; }
    QString email = raw.at(m_selected).toObject().value("email").toString();
    QString label = raw.at(m_selected).toObject().value("name").toString();
    runReportCli(email, label, true);
}

void Backend::runReportCli(const QString &email, const QString &label, bool store) {
    syncToCli();
    int idx = cliAccountIndex(email);
    if (idx < 0) { emit toast(QStringLiteral("CLI 找不到這個帳號，請先登入")); return; }
    m_reportBusy = true; m_reportError.clear();
    emit reportBusyChanged(); emit reportStateChanged();
    emit toast(QStringLiteral("cool.py 正在取得學習時數…"));
    QList<QPair<QString, QString>> rules;
    if (cliAccountCount() > 1) rules.append({ QStringLiteral("輸入編號[^\\n]*: ?$"), QString::number(idx + 1) });
    runCli(QStringList{ "-t", "--raw" }, "report", "direct",
           (store ? QStringLiteral("學習報表 · ") : QStringLiteral("Cookie 有效性檢查 ")) + (label.isEmpty() ? email : label), email, rules,
           [this, email, store](int, const QString &out) {
        int cut = out.indexOf(QStringLiteral("----------------------------------------"));
        QString html = cut >= 0 ? out.mid(cut) : out;
        QString state = Native::classifyTimeReport(QStringLiteral("https://www.coolenglish.edu.tw/time/x"), 200, html);
        QString url;
        for (const QString &l : out.split('\n')) if (l.contains(QStringLiteral("目標網址："))) url = l.section(QStringLiteral("目標網址："), 1).trimmed();
        QList<Native::ReportRow> rows = state == "valid" ? Native::parseTimeReport(html) : QList<Native::ReportRow>();
        bool expired = out.contains(QStringLiteral("已過期")) || out.contains(QStringLiteral("cookie 無效")) || out.contains(QStringLiteral("請重新 cool -l"));
        QString err;
        if (rows.isEmpty()) {
            err = expired ? QStringLiteral("Cookie 已失效，請重新登入。") : QStringLiteral("無法取得學習時間資料（請看網路紀錄中的 cool.py 輸出）。");
        }
        if (!rows.isEmpty() && store) {
            QJsonObject cache = readObject("reports.json"); QJsonObject accounts = cache.value("accounts").toObject();
            QJsonObject rec = accounts.value(email).toObject();
            QJsonArray arr; QList<Native::ReportRow> sorted = rows;
            std::sort(sorted.begin(), sorted.end(), [](const auto &a, const auto &b) { return a.month < b.month; });
            for (const auto &r : sorted) arr.append(QJsonObject{ { "month", r.month }, { "platform", r.platform }, { "video", r.video }, { "practice", r.practice } });
            rec["reports"] = arr; rec["url"] = url; rec["fetchedAt"] = isoNow(); rec["fetchedTs"] = double(QDateTime::currentSecsSinceEpoch()); rec["error"] = QString();
            accounts[email] = rec; cache["accounts"] = accounts; writeJson("reports.json", QJsonDocument(cache));
        } else if (store) {
            QJsonObject cache = readObject("reports.json"); QJsonObject accounts = cache.value("accounts").toObject();
            QJsonObject rec = accounts.value(email).toObject(); rec["error"] = err; accounts[email] = rec; cache["accounts"] = accounts;
            writeJson("reports.json", QJsonDocument(cache));
        }
        setCookieStatus(email, !rows.isEmpty() ? "valid" : (expired ? "expired" : "unknown"));
        m_reportBusy = false; m_reportError = err;
        reloadReports();
        emit reportBusyChanged(); emit reportsChanged(); emit reportStateChanged(); emit reportErrorChanged(); emit reportDone(QVariant(!rows.isEmpty()));
        if (!rows.isEmpty()) emit toast(store ? QStringLiteral("報表已更新（%1 筆）").arg(rows.size()) : email + QStringLiteral("：Cookie 在伺服器端有效"));
        else emit toast(err);
        emit cookieChecked();
    });
}

void Backend::checkCookie(const QVariant &a0) {
    int i = a0.toInt();
    QJsonArray raw = readArray("accounts.json");
    if (i < 0 || i >= raw.size()) { emit toast(QStringLiteral("找不到這個帳號")); return; }
    QJsonObject o = raw.at(i).toObject();
    runReportCli(o.value("email").toString(), o.value("name").toString(), false);
}

// 連結組：以 cool -g 開啟。labels = CLI 的連結組字母（a、b…）
void Backend::openGroups(const QStringList &labels, const QString &mode, const QString &label) {
    if (labels.isEmpty()) { emit toast(QStringLiteral("沒有可開啟的連結組")); return; }
    if (m_accounts.isEmpty() || m_selected < 0 || m_selected >= m_accounts.size()) { emit toast(QStringLiteral("請先選擇已登入的帳號")); return; }
    QString email = m_accounts.at(m_selected).toMap().value("email").toString();
    int idx = cliAccountIndex(email);
    if (idx < 0) { syncToCli(); idx = cliAccountIndex(email); }
    if (idx < 0) { emit toast(QStringLiteral("CLI 找不到這個帳號，請先登入")); return; }
    QList<QPair<QString, QString>> rules = commonRules();
    if (cliAccountCount() > 1) rules.append({ QStringLiteral("輸入編號[^\\n]*: ?$"), QString::number(idx + 1) });
    // 與 CLI 的時間軸修飾符一致：cool -g a|b > /show /delay T /timer T
    const QString tm = m_settings.value("launchTimer").toString().trimmed();
    const QString dl = m_settings.value("launchDelay").toString().trimmed();
    QStringList args{ "-g", labels.join('|') };
    if (mode == "headed" || !tm.isEmpty() || !dl.isEmpty()) {
        args << ">";
        if (mode == "headed") args << "/show";
        if (!dl.isEmpty()) args << "/delay" << dl;
        if (!tm.isEmpty()) args << "/timer" << tm;
    }
    QString m = mode == "headed" ? "headed" : "headless";
    QString sid = runCli(args, "course", m, label, email, rules, nullptr);
    if (sid.isEmpty()) return;
    QString note = m == "headed" ? QStringLiteral("cool.py 已用有頭瀏覽器開啟") : QStringLiteral("cool.py 已在背景開啟；可到「網路紀錄 › 正在運行」終止");
    if (!dl.isEmpty()) note += QStringLiteral("，%1 後開始").arg(dl);
    if (!tm.isEmpty()) note += QStringLiteral("，開啟 %1 後自動關閉").arg(tm);
    emit toast(note);
    emit sessionOpened(sid, !historyEnabled());
}

QStringList Backend::groupLabels(const QStringList &urls) const {
    QList<QPair<QString, QString>> order; QStringList out;
    QHash<QString, QString> urlGroup;
    for (const auto &v : m_courses) {
        QVariantMap c = v.toMap();
        QString al = c.value("alias").toString().trimmed(), cat = c.value("category").toString();
        if (al.isEmpty()) al = cat;
        QPair<QString, QString> k(al, cat);
        if (!order.contains(k)) order.append(k);
        int idx = order.indexOf(k);
        urlGroup[c.value("url").toString()] = idx < 26 ? QString(QChar('a' + idx)) : QString::number(idx + 1);
    }
    for (const QString &u : urls) { QString l = urlGroup.value(u); if (!l.isEmpty() && !out.contains(l)) out << l; }
    return out;
}

void Backend::openCourses(const QVariant &a0, const QVariant &a1, const QVariant &a2) {
    QStringList urls;
    for (const auto &v : a0.toList()) urls << v.toString();
    if (a0.typeId() == QMetaType::QString) urls << a0.toString();
    QString mode = a1.toString();
    if (mode != "headed" && mode != "headless") mode = m_settings.value("defaultLoginMode", "headless").toString();
    QString label = a2.toString();
    if (label.isEmpty()) label = QStringLiteral("開啟課程");
    for (const QString &u : urls) noteCourseOpen(u);
    openGroups(groupLabels(urls), mode, label);
}

void Backend::openAlias(const QVariant &a0, const QVariant &a1) {
    QStringList urls;
    for (const auto &v : m_courses) { QVariantMap c = v.toMap(); if (c.value("alias").toString() == a0.toString()) urls << c.value("url").toString(); }
    for (const QString &u : urls) noteCourseOpen(u);
    openGroups(groupLabels(urls), a1.toString(), QStringLiteral("連結組「%1」").arg(a0.toString()));
}

void Backend::openUrl(const QVariant &a0) {
    QString url = a0.toString();
    if (!url.startsWith("http://", Qt::CaseInsensitive) && !url.startsWith("https://", Qt::CaseInsensitive)) { emit toast(QStringLiteral("不是有效的網址")); return; }
    openCourses(QVariantList{ url }, QVariant(), QString());
}

void Backend::stopSession(const QVariant &a0) {
    QString sid = a0.toString();
    if (CliJob *j = m_cliJobs.value(sid)) {
        j->stopped = true;
        j->proc->write("\n");                      // 課程工作階段：Enter = 結束並關閉瀏覽器
        QPointer<QProcess> p(j->proc);
        QTimer::singleShot(4000, this, [p] { if (p && p->state() != QProcess::NotRunning) p->kill(); });
        emit toast(QStringLiteral("已終止工作階段"));
        return;
    }
    int i = sessionIndex(sid);
    if (i >= 0 && m_sessions.at(i).toMap().value("status").toString() == "active") { finishSession(sid, "stopped", QString()); emit toast(QStringLiteral("已終止工作階段")); }
}


// ---------------------------------------------------------------- ANSI → HTML（網路頁的「CLI 畫面」）
QString Backend::ansiToHtml(const QVariant &a0) {
    const QString text = a0.toString();
    static const char *pal[16] = { "#0c0c0c", "#c50f1f", "#13a10e", "#c19c00", "#0037da", "#881798", "#3a96dd", "#cccccc",
                                   "#767676", "#e74856", "#16c60c", "#f9f1a5", "#3b78ff", "#b4009e", "#61d6d6", "#f2f2f2" };
    const QString defFg = m_settings.value("terminalText", "#d7dde5").toString();
    const QString defBg = m_settings.value("terminalBg", "#101418").toString();
    QString fg, bg; bool bold = false, dim = false, rev = false;
    QString out, seg;
    auto esc = [](const QString &t) { QString r = t.toHtmlEscaped(); r.replace('\r', QString()); return r; };
    auto color256 = [&](int n) { return n < 16 ? QString::fromLatin1(pal[n]) : xterm256(n); };
    auto flush = [&]() {
        if (seg.isEmpty()) return;
        QString f = fg.isEmpty() ? defFg : fg, b = bg;
        if (rev) { const QString realBg = b.isEmpty() ? defBg : b; b = f; f = realBg; }
        if (dim && fg.isEmpty() && !rev) f = QStringLiteral("#8b949e");
        QString style = QStringLiteral("color:%1;").arg(f);
        if (!b.isEmpty()) style += QStringLiteral("background-color:%1;").arg(b);
        if (bold) style += QStringLiteral("font-weight:bold;");
        out += QStringLiteral("<span style=\"%1\">%2</span>").arg(style, esc(seg));
        seg.clear();
    };
    for (int i = 0; i < text.size(); ++i) {
        const QChar ch = text.at(i);
        if (ch == QChar(0x1b) && i + 1 < text.size() && text.at(i + 1) == '[') {
            int j = i + 2;
            while (j < text.size() && !(text.at(j).isLetter())) ++j;
            if (j >= text.size()) break;
            const QChar cmd = text.at(j);
            if (cmd == 'm') {
                flush();
                const QStringList parts = text.mid(i + 2, j - i - 2).split(';');
                QList<int> p; for (const QString &x : parts) p << (x.isEmpty() ? 0 : x.toInt());
                for (int k = 0; k < p.size(); ++k) {
                    int v = p[k];
                    if (v == 0) { fg.clear(); bg.clear(); bold = dim = rev = false; }
                    else if (v == 1) bold = true;
                    else if (v == 2) dim = true;
                    else if (v == 7) rev = true;
                    else if (v == 22) { bold = false; dim = false; }
                    else if (v == 27) rev = false;
                    else if (v >= 30 && v <= 37) fg = QString::fromLatin1(pal[bold ? v - 30 + 8 : v - 30]);
                    else if (v >= 90 && v <= 97) fg = QString::fromLatin1(pal[v - 90 + 8]);
                    else if (v == 39) fg.clear();
                    else if (v >= 40 && v <= 47) bg = QString::fromLatin1(pal[v - 40]);
                    else if (v >= 100 && v <= 107) bg = QString::fromLatin1(pal[v - 100 + 8]);
                    else if (v == 49) bg.clear();
                    else if ((v == 38 || v == 48) && k + 1 < p.size()) {
                        QString col;
                        if (p[k + 1] == 5 && k + 2 < p.size()) { col = color256(p[k + 2]); k += 2; }
                        else if (p[k + 1] == 2 && k + 4 < p.size()) { col = QColor(p[k + 2], p[k + 3], p[k + 4]).name(); k += 4; }
                        if (v == 38) fg = col; else bg = col;
                    }
                }
            }
            i = j;                     // 其他控制序列（游標移動、清行）直接略過
            continue;
        }
        seg += ch;
    }
    flush();
    return QStringLiteral("<pre style=\"margin:0\">") + out + QStringLiteral("</pre>");
}
