
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
void Backend::refreshReports() {
    if (m_reportBusy) { emit toast(QStringLiteral("報表正在更新，請稍候")); return; }
    QJsonArray raw = readArray("accounts.json");
    if (m_selected < 0 || m_selected >= raw.size()) {
        emit toast(QStringLiteral("請先新增並登入一個帳號")); return;
    }
    QJsonObject entry = raw.at(m_selected).toObject();
    QString cookie = entry.value("cookie_file").toString();
    if (cookie.isEmpty()) { emit toast(QStringLiteral("這個帳號還沒有 Cookie，請先登入")); return; }
    if (!QFile::exists(resolvePath(cookie))) { emit toast(QStringLiteral("找不到 Cookie 檔，請重新登入")); return; }
    // 抓取目前選擇帳號的報表並寫回 reports.json（多帳號各自獨立）
    emit toast(QStringLiteral("正在向 Cool English 取得學習時數…"));
    QProcess *proc = new QProcess(this);
    QString script = "C:/Users/jusaper/Downloads/coolqml-rs/fetch_report.py";
    proc->start(pythonExe(), QStringList() << script << entry.value("email").toString());
    connect(proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this, proc](int, QProcess::ExitStatus) {
                QString out = QString::fromUtf8(proc->readAllStandardOutput());
                proc->deleteLater();
                // 解析 __COOL_REPORT__{...}
                QString line;
                for (const QString &l : out.split('\n'))
                    if (l.startsWith("__COOL_REPORT__")) line = l.mid(15);
                QJsonObject r = QJsonDocument::fromJson(line.toUtf8()).object();
                reloadReports(); reloadSessions(); reloadAccounts();
                emit reportsChanged(); emit sessionsChanged(); emit reportStateChanged(); emit accountsChanged();
                if (r.value("ok").toBool())
                    emit toast(QStringLiteral("報表已更新（%1 筆）").arg(r.value("rows").toInt()));
                else
                    emit toast(QStringLiteral("報表更新失敗：") + r.value("error").toString());
            });
}

// ============ Slots：帳號 ============
void Backend::addAccount(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3) {
    QString email = a0.toString().trimmed();
    QString password = a1.toString();
    QString name = a2.toString().trimmed();
    QString mode = a3.toString();
    if (email.isEmpty()) { emit toast(QStringLiteral("請輸入 Cool English 帳號（Email）")); return; }
    if (password.isEmpty()) { emit toast(QStringLiteral("請輸入密碼")); return; }
    QJsonArray raw = readArray("accounts.json");
    QString label = name.isEmpty() ? email.section('@',0,0) : name;
    int idx = -1;
    for (int i = 0; i < raw.size(); ++i) {
        if (raw.at(i).toObject().value("email").toString().compare(email, Qt::CaseInsensitive) == 0) { idx = i; break; }
    }
    QJsonObject obj = idx >= 0 ? raw.at(idx).toObject() : QJsonObject();
    obj["name"] = label;
    obj["email"] = email;
    obj["login_mode"] = mode;
    if (idx < 0) {
        obj["created_at"] = nowStamp();
        obj["cookie_file"] = QString("cookies/") + emailStem(email) + ".txt";
    }
    // 密碼加密：呼叫 helper（此處先記錄明文长度的 flag，實際加密在 login 時由 helper 处理）
    if (!password.isEmpty()) {
        obj["password_len"] = password.size();
        QProcess proc;
        QString enc = "C:/Users/jusaper/Downloads/cool-qml-caelestia/coolqml/cool_cli/security.py";
        if (QFile::exists(enc)) {
            proc.start(pythonExe(), QStringList() << "-c"
                << QString("import sys;sys.path.insert(0,r'C:/Users/jusaper/Downloads/cool-qml-caelestia/coolqml');from cool_cli.security import encrypt_password;print(encrypt_password(%1))").arg("'" + password + "'"));
            proc.waitForFinished(5000);
            QString out = QString::fromUtf8(proc.readAllStandardOutput()).trimmed();
            if (!out.isEmpty()) obj["password_enc"] = out;
        }
    }
    if (idx >= 0) raw.replace(idx, obj); else raw.append(obj);
    saveRaw(raw);
    reloadAccounts();
    emit accountsChanged();
    emit toast(idx >= 0 ? QStringLiteral("已更新帳號資料") : QStringLiteral("已新增帳號"));
}
void Backend::renameAccount(const QVariant &a0, const QVariant &a1) {
    int i = a0.toInt(); QString name = a1.toString().trimmed();
    QJsonArray raw = readArray("accounts.json");
    if (i >= 0 && i < raw.size() && !name.isEmpty()) {
        QJsonObject o = raw.at(i).toObject(); o["name"] = name; raw.replace(i, o);
        saveRaw(raw); reloadAccounts(); emit accountsChanged(); emit toast(QStringLiteral("已更新名稱"));
    }
}
void Backend::removeAccount(const QVariant &a0) {
    int i = a0.toInt();
    QJsonArray raw = readArray("accounts.json");
    if (i >= 0 && i < raw.size()) {
        QJsonObject o = raw.at(i).toObject();
        QString ck = o.value("cookie_file").toString();
        if (!ck.isEmpty()) QFile::remove(resolvePath(ck));
        QString stem = emailStem(o.value("email").toString());
        // 移除 avatar
        for (const char *ext : {"png","jpg","jpeg","webp","gif"}) QFile::remove(filePath("avatars/"+stem+"."+QString::fromLatin1(ext)));
        QString name = o.value("name").toString();
        raw.removeAt(i);
        saveRaw(raw); reloadAccounts(); reloadReports();
        emit accountsChanged(); emit selectedChanged(); emit reportsChanged();
        emit toast(QStringLiteral("已移除 ") + name + QStringLiteral(" 與本機 Cookie"));
    }
}
void Backend::removeAllAccounts() {
    QJsonArray raw = readArray("accounts.json");
    for (const auto &v : raw) {
        QJsonObject o = v.toObject();
        QString ck = o.value("cookie_file").toString();
        if (!ck.isEmpty()) QFile::remove(resolvePath(ck));
    }
    saveRaw(QJsonArray());
    reloadAccounts(); reloadReports();
    emit accountsChanged(); emit selectedChanged(); emit reportsChanged();
    emit toast(QStringLiteral("已移除全部帳號"));
}
void Backend::checkCookie(const QVariant &a0) {
    int i = a0.toInt();
    QJsonArray raw = readArray("accounts.json");
    if (i < 0 || i >= raw.size()) { emit toast(QStringLiteral("找不到這個帳號")); return; }
    QJsonObject o = raw.at(i).toObject();
    QString email = o.value("email").toString();
    QString ck = o.value("cookie_file").toString();
    if (ck.isEmpty()) { emit toast(email + QStringLiteral(" 沒有 Cookie，請先登入")); return; }
    if (!QFile::exists(resolvePath(ck))) { emit toast(email + QStringLiteral(" 的 Cookie 檔不存在，請重新登入")); return; }
    emit toast(QStringLiteral("正在向 Cool English 確認 ") + email + QStringLiteral(" 的 Cookie…"));
    QProcess *proc = new QProcess(this);
    QString script = "C:/Users/jusaper/Downloads/coolqml-rs/check_cookie.py";
    proc->start(pythonExe(), QStringList() << script << email);
    connect(proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this, proc, email](int, QProcess::ExitStatus) {
                QString out = QString::fromUtf8(proc->readAllStandardOutput());
                proc->deleteLater();
                QString line;
                for (const QString &l : out.split('\n'))
                    if (l.startsWith("__COOL_COOKIE__")) line = l.mid(15);
                QJsonObject r = QJsonDocument::fromJson(line.toUtf8()).object();
                QString state = r.value("state").toString();
                // 寫到獨立狀態檔，不污染 reports.json 的報表錯誤欄
                QJsonObject cs = readObject("cookie_status.json");
                cs[email] = state;
                writeJson("cookie_status.json", QJsonDocument(cs));
                reloadAccounts(); emit accountsChanged();
                if (state == "valid") emit toast(email + QStringLiteral("：Cookie 在伺服器端有效"));
                else if (state == "expired") emit toast(email + QStringLiteral("：Cookie 已失效，請重新登入"));
                else emit toast(email + QStringLiteral("：無法連線確認，請稍後重試"));
            });
}

// ============ Slots：課程 ============
void Backend::courseChanged() {
    saveCourses();
    for (int i = 0; i < m_courses.size(); ++i) {
        QVariantMap m = m_courses.at(i).toMap(); m["id"] = i+1; m_courses[i] = m;
    }
    emit coursesChanged();
}
void Backend::addCourse(const QVariant &a0, const QVariant &a1, const QVariant &a2) {
    QString url = a0.toString().trimmed(), cat = a1.toString().trimmed(), alias = a2.toString().trimmed();
    if (!url.startsWith("http")) { emit toast(QStringLiteral("網址需要以 http 或 https 開頭")); return; }
    if (cat.isEmpty()) cat = QStringLiteral("未分類");
    for (const auto &v : m_courses) if (v.toMap().value("url").toString() == url) { emit toast(QStringLiteral("這個網址已經在清單裡")); return; }
    QVariantMap m; m["id"]=m_courses.size()+1; m["url"]=url; m["category"]=cat;
    m["alias"]=alias.isEmpty()?cat:alias; m["opens"]=0; m["opened"]=QStringLiteral("尚未開啟"); m["openedAt"]=QString();
    m_courses.append(m);
    courseChanged();
    emit toast(QStringLiteral("已儲存 1 個網址到 urls.txt"));
}
void Backend::removeCourse(const QVariant &a0) {
    int i = a0.toInt();
    if (i >= 0 && i < m_courses.size()) { m_courses.removeAt(i); courseChanged(); emit toast(QStringLiteral("已移除網址")); }
}
void Backend::setCourseCategory(const QVariant &a0, const QVariant &a1) {
    int i = a0.toInt(); QString cat = a1.toString().trimmed();
    if (i >= 0 && i < m_courses.size() && !cat.isEmpty()) {
        QVariantMap m = m_courses.at(i).toMap(); m["category"] = cat; m_courses[i] = m;
        courseChanged(); emit toast(QStringLiteral("分類已更新"));
    }
}
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
void Backend::openCourseMenu() { emit toast(startTerminalWithArgs(QStringList() << "-u", QStringLiteral("課程")) ? QStringLiteral("已在內嵌終端機開啟 cool.py 課程選單") : QStringLiteral("無法啟動內嵌終端機")); }
void Backend::openReportCli() { emit toast(startTerminalWithArgs(QStringList() << "-t", QStringLiteral("學習時間")) ? QStringLiteral("已在內嵌終端機用 cool.py 取得學習時間") : QStringLiteral("無法啟動內嵌終端機")); }
