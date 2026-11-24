
// ============ Slots：登入 ============
void Backend::startLogin(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3) {
    QString email = a0.toString().trimmed();
    QString password = a1.toString();
    QString name = a2.toString();
    QString mode = a3.toString();
    if (email.isEmpty()) { emit toast(QStringLiteral("請先選擇或輸入帳號")); return; }
    if (m_loginBusy) { emit toast(QStringLiteral("已有登入程序在執行，請稍候")); return; }
    QString helper = "C:/Users/jusaper/Downloads/cool-qml-caelestia/coolqml/login_helper.py";
    if (!QFile::exists(helper)) { emit toast(QStringLiteral("找不到 login_helper.py，無法登入")); return; }
    m_loginBusy = true;
    m_loginStatus = mode == "headed" ? QStringLiteral("正在開啟瀏覽器，請完成 Google 登入…") : QStringLiteral("正在背景登入…");
    emit loginChanged();
    QProcess *proc = new QProcess(this);
    QProcessEnvironment env = QProcessEnvironment::systemEnvironment();
    env.insert("PYTHONUTF8", "1");
    proc->setProcessEnvironment(env);
    QJsonObject payload;
    payload["email"] = email; payload["password"] = password;
    payload["name"] = name; payload["mode"] = mode;
    proc->start(pythonExe(), QStringList() << helper);
    proc->write(QJsonDocument(payload).toJson(QJsonDocument::Compact) + "\n");
    proc->closeWriteChannel();
    connect(proc, &QProcess::readyReadStandardOutput, this, [this, proc]() {
        QString out = QString::fromUtf8(proc->readAllStandardOutput());
        // 抓 __COOL_LOGIN__ 行
        for (const QString &line : out.split('\n')) {
            if (line.startsWith("__COOL_LOGIN__")) {
                QJsonDocument d = QJsonDocument::fromJson(line.mid(14).toUtf8());
                QJsonObject o = d.object();
                m_loginStatus = o.value("ok").toBool() ? QStringLiteral("登入成功") : (QStringLiteral("登入失敗：") + o.value("error").toString());
                reloadAccounts(); reloadReports();
                emit accountsChanged(); emit reportsChanged(); emit loginChanged();
            }
        }
    });
    connect(proc, QOverload<int,QProcess::ExitStatus>::of(&QProcess::finished), this,
            [this, proc](int code, QProcess::ExitStatus) {
                proc->deleteLater(); m_loginBusy = false; emit loginChanged();
            });
}
void Backend::loginAccount(const QVariant &a0, const QVariant &a1) {
    int i = a0.toInt(); QString mode = a1.toString();
    QJsonArray raw = readArray("accounts.json");
    if (i < 0 || i >= raw.size()) { emit toast(QStringLiteral("請先選擇帳號")); return; }
    QJsonObject o = raw.at(i).toObject();
    QString email = o.value("email").toString();
    QString label = o.value("name").toString(); if (label.isEmpty()) label = email;
    // 解密密碼
    QString enc = o.value("password_enc").toString();
    if (enc.isEmpty()) { emit toast(label + QStringLiteral(" 沒有儲存密碼，請重新輸入 Email 與密碼後按「連結帳號」")); return; }
    QProcess proc;
    QString code = QString("import sys;sys.path.insert(0,r'C:/Users/jusaper/Downloads/cool-qml-caelestia/coolqml');"
        "from cool_cli.security import decrypt_password;print(decrypt_password(%1))").arg("'" + enc + "'");
    proc.start(pythonExe(), QStringList() << "-c" << code);
    proc.waitForFinished(5000);
    QString pwd = QString::fromUtf8(proc.readAllStandardOutput()).trimmed();
    if (pwd.isEmpty()) { emit toast(label + QStringLiteral(" 無法解密密碼，請重新連結帳號")); return; }
    startLogin(email, pwd, label, mode);
}
void Backend::loginSelected(const QVariant &a0) { loginAccount(m_selected, a0.toString()); }
void Backend::clearLoginStatus() { m_loginStatus.clear(); emit loginChanged(); }

// ============ Slots：終端（ConPTY 由 QProcess + shell 近似）============
bool Backend::startTerminalWithArgs(const QStringList &args, const QString &label) {
    if (m_termTabs.size() >= 8) { emit toast(QStringLiteral("最多開啟 8 個終端分頁")); return false; }
    int sid = ++m_termSeq;
    QString profileId = defaultTerminal();
    QVariantMap tab;
    tab["id"] = sid; tab["profile"] = profileId;
    tab["label"] = label.isEmpty() ? QStringLiteral("終端機") : label;
    tab["icon"] = "terminal"; tab["status"] = QStringLiteral("執行中");
    tab["running"] = true; tab["active"] = true;
    for (auto &v : m_termTabs) { QVariantMap m = v.toMap(); m["active"] = false; v = m; }
    m_termTabs.append(tab);
    m_termActive = sid;
    m_termRunning = true;
    m_termStatus = QStringLiteral("執行中");
    // 真正的 ConPTY shell 由 QML 的 TerminalView (sessionId 改變時) 啟動，
    // 後端只管理分頁狀態，不再用 QProcess 起重複的 shell。
    emit terminalTabsChanged();
    emit terminalChanged();
    return true;
}
void Backend::startTerminal(const QVariant &a0) { startTerminalWithArgs(QStringList(), QString()); }
void Backend::launchTerminal(const QVariant &a0) { startTerminalWithArgs(QStringList(), QString()); }
void Backend::selectTerminalTab(const QVariant &a0) {
    int sid = a0.toInt();
    for (const auto &v : m_termTabs) if (v.toMap().value("id").toInt() == sid) {
        m_termActive = sid;
        for (auto &t : m_termTabs) { QVariantMap m = t.toMap(); m["active"] = (m["id"].toInt()==sid); t = m; }
        emit terminalTabsChanged(); return;
    }
}
void Backend::closeTerminalTab(const QVariant &a0) {
    int sid = a0.toInt();
    if (m_termProcs.contains(sid)) { QProcess *p = m_termProcs.take(sid); p->kill(); p->deleteLater(); }
    QVariantList keep;
    for (const auto &v : m_termTabs) if (v.toMap().value("id").toInt() != sid) keep.append(v);
    m_termTabs = keep;
    if (m_termActive == sid) m_termActive = m_termTabs.isEmpty() ? 0 : m_termTabs.last().toMap().value("id").toInt();
    m_termRunning = !m_termTabs.isEmpty();
    emit terminalTabsChanged(); emit terminalChanged();
}
void Backend::writeTerminal(const QVariant &a0) {
    QProcess *p = m_termProcs.value(m_termActive, nullptr);
    if (!p || p->state() != QProcess::Running) { emit toast(QStringLiteral("這個分頁的終端機沒有在執行")); return; }
    QString text = a0.toString(); text.remove('\r'); text.remove('\n');
    p->write((text + "\r").toUtf8());
}
void Backend::pasteTerminal(const QVariant &a0) {
    QString text = QGuiApplication::clipboard()->text();
    if (text.isEmpty()) { emit toast(QStringLiteral("剪貼簿是空的")); return; }
    text.replace("\r\n", "\r"); text.replace('\n', '\r');
    int sid = a0.toInt();
    QProcess *p = m_termProcs.value(sid, nullptr);
    if (p && p->state() == QProcess::Running) {
        p->write(text.toUtf8());
        emit toast(QStringLiteral("已貼上 ") + QString::number(text.size()) + QStringLiteral(" 個字元"));
    }
}
void Backend::copyTerminalSelection(const QVariant &a0) {
    if (m_termText.isEmpty()) return;
    QGuiApplication::clipboard()->setText(m_termText);
    emit toast(QStringLiteral("已複製目前終端機畫面"));
}
void Backend::stopTerminal() {
    QProcess *p = m_termProcs.value(m_termActive, nullptr);
    if (!p || p->state() != QProcess::Running) { emit toast(QStringLiteral("終端機沒有在執行")); return; }
    p->kill();
    for (auto &v : m_termTabs) { QVariantMap m = v.toMap(); if (m["id"].toInt() == m_termActive) { m["status"]="已停止"; m["running"]=false; } v = m; }
    m_termRunning = false; emit terminalTabsChanged(); emit terminalChanged();
}
void Backend::shutdownTerminal() {
    for (auto it = m_termProcs.begin(); it != m_termProcs.end(); ++it) { it.value()->kill(); it.value()->deleteLater(); }
    m_termProcs.clear(); m_termTabs.clear(); m_termActive = 0; m_termRunning = false; m_termText.clear();
    emit terminalTabsChanged(); emit terminalChanged();
}
void Backend::restartTerminal() {
    if (m_termTabs.isEmpty()) { startTerminalWithArgs(QStringList(), QString()); return; }
    closeTerminalTab(m_termActive);
    startTerminalWithArgs(QStringList(), QString());
}
void Backend::clearTerminal() { m_termText.clear(); emit terminalChanged(); }
void Backend::clearTerminalHistory() { m_termHistory.clear(); emit terminalChanged(); }
void Backend::toggleCursor() { /* 游標閃爍由 QML 處理 */ }
QString Backend::selectionText() { return QString(); }
void Backend::refresh() { reloadReports(); reloadSessions(); emit reportsChanged(); emit sessionsChanged(); }
