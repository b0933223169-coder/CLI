#pragma once
#include <QString>
#include <QDir>
#include <QFileInfo>
#include <QCoreApplication>

// 所有路徑以執行檔位置為基準，方便整個資料夾搬家/移植。
// 配置：exe 在 <root>/build-main/，資源(qml、xterm、helper scripts)在 <root>/，
//       Python 原專案在 <root>/../
inline QString appDirPath() {
    return QCoreApplication::applicationDirPath();
}
inline QString rootDirPath() {
    return QDir::cleanPath(QDir(appDirPath()).filePath(QStringLiteral("..")));
}
inline QString pyRootPath() {
    // 移植到 cooler 原專案後：<root>/.. 就是 coolqml（有 cool.py）
    QString up = QDir::cleanPath(QDir(rootDirPath()).filePath(QStringLiteral("..")));
    if (QFileInfo::exists(QDir(up).filePath(QStringLiteral("cool.py")))) return up;
    // 開發中：<root>/../cool-qml-caelestia/coolqml
    QString dev = QDir::cleanPath(QDir(rootDirPath()).filePath(
        QStringLiteral("../cool-qml-caelestia/coolqml")));
    if (QFileInfo::exists(QDir(dev).filePath(QStringLiteral("cool.py")))) return dev;
    return up;
}
inline QString pyExePath() {
    return QDir(pyRootPath()).filePath(QStringLiteral(".venv/Scripts/python.exe"));
}
