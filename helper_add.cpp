
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
