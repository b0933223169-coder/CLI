
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
void Backend::exportSessions() {
    if (m_sessions.isEmpty()) { emit toast(QStringLiteral("目前沒有網路紀錄可匯出")); return; }
    QString path = exportPath("sessions") + ".json";
    QFile f(path);
    if (f.open(QIODevice::WriteOnly)) {
        QJsonArray arr;
        for (const auto &v : m_sessions) arr.append(QJsonObject::fromVariantMap(v.toMap()));
        f.write(QJsonDocument(arr).toJson(QJsonDocument::Indented));
        f.close(); emit toast(QStringLiteral("已匯出網路紀錄：") + QFileInfo(path).fileName());
    } else emit toast(QStringLiteral("匯出失敗"));
}
void Backend::exportSession(const QVariant &a0) {
    QString sid = a0.toString();
    for (const auto &v : m_sessions) {
        QVariantMap m = v.toMap();
        if (m.value("id").toString() == sid) {
            QString path = exportPath("session-" + sid) + ".json";
            QFile f(path);
            if (f.open(QIODevice::WriteOnly)) {
                f.write(QJsonDocument(QJsonObject::fromVariantMap(m)).toJson(QJsonDocument::Indented));
                f.close(); emit toast(QStringLiteral("已匯出 ") + QFileInfo(path).fileName());
            }
            return;
        }
    }
    emit toast(QStringLiteral("找不到工作階段"));
}
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
void Backend::openUrl(const QVariant &a0) {
    QString url = a0.toString();
    if (!url.startsWith("http://", Qt::CaseInsensitive) && !url.startsWith("https://", Qt::CaseInsensitive)) {
        emit toast(QStringLiteral("不是有效的網址")); return;
    }
    QDesktopServices::openUrl(QUrl(url));
    noteCourseOpen(url);
    emit toast(QStringLiteral("已在瀏覽器開啟，並記錄開啟次數"));
}
void Backend::openFolder(const QVariant &a0) {
    QString p = a0.toString();
    if (p.isEmpty()) p = dataDir();
    QDir().mkpath(p);
    QDesktopServices::openUrl(QUrl::fromLocalFile(p));
    emit toast(QStringLiteral("已開啟資料夾"));
}

// ============ Slots：清除 ============
void Backend::clearCookies() {
    QJsonArray raw = readArray("accounts.json");
    for (int i = 0; i < raw.size(); ++i) {
        QJsonObject o = raw.at(i).toObject();
        QString ck = o.value("cookie_file").toString();
        if (!ck.isEmpty()) QFile::remove(resolvePath(ck));
        o["cookie_file"] = "";
        raw.replace(i, o);
    }
    saveRaw(raw); reloadAccounts(); emit accountsChanged(); emit toast(QStringLiteral("已清除本機 Cookie"));
}
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
