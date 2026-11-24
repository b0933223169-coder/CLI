// coolqml-rs — 桌面 host：純 C++ + Qt QML/WebEngine，完全不載入 Python 作為 UI。
// 載入 coolqml-rs 自己的 qml/Main.qml；終端用 xterm.js + QWebEngineView。
#include <QApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QUrl>
#include <QQuickPaintedItem>
#include <QPainter>
#include <QDebug>
#include <QFile>
#include <QTextStream>
#include <QQmlError>
#include <QJsonDocument>
#include <QQuickWindow>
#include <QImage>
#include <QPainterPath>
#include <QUrl>
#include <QTimer>
#include <QQmlWebChannel>
#include "backend.h"
#include "conpty.h"
#include "qml_pty_bridge.h"
#include "paths.h"
#include <QElapsedTimer>

// 除錯 log（寫入 host.log）；重載 const char* 避免與 C math logf(float) 混淆
static QElapsedTimer g_up;
static void logf(const QString &msg) {
    QFile f(QDir(appDirPath()).filePath(QStringLiteral("host.log")));
    if (f.open(QIODevice::Append | QIODevice::WriteOnly))
        f.write((QStringLiteral("[%1ms] ").arg(g_up.isValid() ? g_up.elapsed() : 0) + msg + QStringLiteral("\n")).toUtf8());
}
static inline void logf(const char *msg) { logf(QString::fromUtf8(msg)); }

// AvatarView：有圖片就畫圖片（圓形裁切），沒有才畫名稱縮寫
class AvatarView : public QQuickPaintedItem
{
    Q_OBJECT
    Q_PROPERTY(QString source READ source WRITE setSource NOTIFY changed)
    Q_PROPERTY(QString name READ name WRITE setName NOTIFY changed)
    Q_PROPERTY(QColor tint READ tint WRITE setTint NOTIFY changed)
    Q_PROPERTY(QColor onTint READ onTint WRITE setOnTint NOTIFY changed)
    Q_PROPERTY(qreal radius READ radius WRITE setRadius NOTIFY changed)
public:
    using QQuickPaintedItem::QQuickPaintedItem;
    void paint(QPainter *p) override {
        if (width() < 1 || height() < 1) return;
        p->setRenderHint(QPainter::Antialiasing, true);
        qreal r = m_radius > 0 ? m_radius : qMin(width(), height()) / 2.0;
        QRectF rect(0, 0, width(), height());
        QPainterPath path;
        path.addRoundedRect(rect, r, r);
        p->setClipPath(path);
        QColor c = m_tint.isValid() ? m_tint : QColor("#6750a4");
        p->fillRect(rect, c);

        if (!m_image.isNull()) {
            // 等比放大填滿（KeepAspectRatioByExpanding），置中裁切
            QImage scaled = m_image.scaled(QSize(int(width()), int(height())),
                                           Qt::KeepAspectRatioByExpanding, Qt::SmoothTransformation);
            QPointF pos((width() - scaled.width()) / 2.0, (height() - scaled.height()) / 2.0);
            p->drawImage(pos, scaled);
            return;
        }
        if (!m_name.isEmpty()) {
            p->setPen(m_onTint.isValid() ? m_onTint : QColor("#ffffff"));
            QFont f; f.setPixelSize(qMax(10, int(qMin(width(), height()) * 0.42))); f.setBold(true);
            p->setFont(f);
            p->drawText(rect, Qt::AlignCenter, m_name.left(1).toUpper());
        }
    }
    QString source() const { return m_source; }
    void setSource(const QString &v) {
        if (v == m_source) return;
        m_source = v;
        m_image = QImage();
        // 支援 file:// URL 與 ?v= 快取參數
        QString local = v;
        if (local.startsWith("file:")) local = QUrl(local).toLocalFile();
        int q = local.indexOf('?');
        if (q >= 0) local = local.left(q);
        if (!local.isEmpty()) {
            QImage img(local);
            if (!img.isNull()) m_image = img;
        }
        emit changed(); update();
    }
    QString name() const { return m_name; } void setName(const QString &v) { m_name=v; emit changed(); update(); }
    QColor tint() const { return m_tint; } void setTint(const QColor &v) { m_tint=v; emit changed(); update(); }
    QColor onTint() const { return m_onTint; } void setOnTint(const QColor &v) { m_onTint=v; emit changed(); update(); }
    qreal radius() const { return m_radius; } void setRadius(qreal v) { m_radius=v; emit changed(); update(); }
signals:
    void changed();
private:
    QString m_source, m_name; QColor m_tint, m_onTint; qreal m_radius = 0;
    QImage m_image;
};

int main(int argc, char *argv[])
{
    // 內嵌終端機（xterm.js）完全用不到 GPU：關掉 Chromium 的 GPU 程序，
    // 避免 GPU 初始化失敗時 Chromium 直接中止整個程式（Qt6WebEngineCore 內部的 0x80000003 當機），也省記憶體。
    // Chromium 的紀錄寫到資料夾的 chromium.log，萬一還是當機可以看到真正原因。
    if (qEnvironmentVariableIsEmpty("QTWEBENGINE_CHROMIUM_FLAGS")) {
        QString dir = qEnvironmentVariable("COOL_DATA_DIR");
        if (dir.isEmpty()) dir = qEnvironmentVariable("APPDATA") + QStringLiteral("/cool");
        qputenv("QTWEBENGINE_CHROMIUM_FLAGS",
                QStringLiteral("--disable-gpu --disable-gpu-compositing --enable-logging --log-file=\"%1/chromium.log\" --v=0")
                    .arg(dir).toLocal8Bit());
    }
    g_up.start();
    QApplication app(argc, argv);
    if (!qEnvironmentVariable("COOL_QML_LOG").isEmpty())
        qInstallMessageHandler([](QtMsgType, const QMessageLogContext &, const QString &msg) { logf("MSG: " + msg); });
    logf("MAIN enter");
    if (!qEnvironmentVariable("COOL_STALL_LOG").isEmpty()) {
        auto *heartbeat = new QTimer(&app);
        auto *last = new QElapsedTimer; last->start();
        heartbeat->setInterval(10);
        QObject::connect(heartbeat, &QTimer::timeout, [last]() {
            const qint64 gap = last->restart();
            if (gap > 80) logf(QString("STALL %1ms（介面執行緒被卡住）").arg(gap));
        });
        heartbeat->start();
    }
    logf("app constructed");
    app.setApplicationName("coolqml");
    logf("Backend ctor begin");
    Backend *backend = new Backend(&app);
    logf("Backend ctor end");
    app.installEventFilter(backend);
    if (!qEnvironmentVariable("COOL_PROBE").isEmpty()) {
        logf("PROBE begin");
        QString mode = qEnvironmentVariable("COOL_PROBE_MODE");
        QString rep;
        if (mode == "addAccount") {
            backend->addAccount("test@example.com", "pass123", "測試帳號", "headless");
            rep = QString("AFTER_ADD=%1\n").arg(backend->accounts().size());
        } else if (mode == "renameAccount") {
            backend->renameAccount(0, "新名稱");
            rep = "NAME=" + backend->accounts().at(0).toMap().value("name").toString() + "\n";
        } else if (mode == "removeAccount") {
            backend->removeAccount(0);
            rep = QString("AFTER_REMOVE=%1\n").arg(backend->accounts().size());
        } else if (mode == "addCourse") {
            backend->addCourse("https://example.com/course", "測試分類", "測試課程");
            rep = QString("COURSES=%1\n").arg(backend->courses().size());
        } else if (mode == "removeCourse") {
            backend->removeCourse(0);
            rep = QString("COURSES=%1\n").arg(backend->courses().size());
        } else if (mode == "renameCategory") {
            backend->renameCategory("test", "newtest");
            rep = "OK\n";
        } else if (mode == "deleteSession") {
            if (backend->sessions().size() > 0)
                backend->deleteSession(backend->sessions().at(0).toMap().value("id").toString());
            rep = QString("SESSIONS=%1\n").arg(backend->sessions().size());
        } else if (mode == "clearSessions") {
            backend->clearSessions();
            rep = QString("SESSIONS=%1\n").arg(backend->sessions().size());
        } else if (mode == "updateSetting") {
            backend->updateSetting("fontSize", 20);
            rep = "FONT=" + backend->settings().value("fontSize").toString() + "\n";
        } else if (mode == "exportReport") {
            backend->exportReport("csv");
            rep = "OK\n";
        } else if (mode == "cookieStates") {
            rep = "";
            for (const auto &v : backend->accounts()) {
                QVariantMap m = v.toMap();
                rep += m.value("email").toString() + " = " + m.value("cookie").toString() + "\n";
            }
        } else if (mode == "switchAccount") {
            rep = "ACCOUNTS=" + QString::number(backend->accounts().size()) + "\n";
            for (int i = 0; i < backend->accounts().size(); ++i) {
                backend->select(i);
                rep += QString("sel%1: email=%2 reports=%3 source=%4\n")
                    .arg(i)
                    .arg(backend->accounts().at(i).toMap().value("email").toString())
                    .arg(backend->reports().size())
                    .arg(backend->reportSource().isEmpty() ? QString("(none)") : backend->reportSource().right(20));
            }
        } else if (mode == "terminals") {
            rep = "N=" + QString::number(backend->terminalProfiles().size()) + "\n";
            for (const auto &v : backend->terminalProfiles()) {
                QVariantMap m = v.toMap();
                rep += m.value("id").toString() + " | " + m.value("label").toString()
                     + " | " + m.value("kind").toString() + " | " + m.value("path").toString()
                     + " | distro=" + m.value("distro").toString() + "\n";
            }
        } else if (mode == "multiterm") {
            backend->startTerminal(QStringLiteral("powershell"));
            backend->startTerminal(QStringLiteral("cmd"));
            rep = "tabs=" + QString::number(backend->terminalCount()) + "\n";
            for (const auto &v : backend->terminalTabs()) {
                QVariantMap m = v.toMap();
                rep += QStringLiteral("tab %1: profile=%2 label=%3\n")
                    .arg(m.value("id").toInt()).arg(m.value("profile").toString())
                    .arg(m.value("label").toString());
            }
            QObject *c1 = backend->terminalChannel(1);
            QObject *c2 = backend->terminalChannel(2);
            rep += QStringLiteral("channel1=%2 channel2=%3 distinct=%4\n")
                .arg(c1 ? "yes" : "no", c2 ? "yes" : "no",
                     (c1 && c2 && c1 != c2) ? "true" : "false");
        } else if (mode == "colors") {
            QVariantMap c = backend->colors();
            rep = "primary=" + c.value("primary").toString() + "\n"
                + "secondary=" + c.value("secondary").toString() + "\n"
                + "tertiary=" + c.value("tertiary").toString() + "\n"
                + "surface=" + c.value("surface").toString() + "\n"
                + "primaryContainer=" + c.value("primaryContainer").toString() + "\n";
        } else if (mode == "setSeed") {
            backend->setScheme("#0066ff", "ocean", false, 0.0);
            QVariantMap c = backend->colors();
            rep = "AFTER_SEED primary=" + c.value("primary").toString() + "\n"
                + "secondary=" + c.value("secondary").toString() + "\n"
                + "surface=" + c.value("surface").toString() + "\n";
        } else if (mode == "preview") {
            QVariantList p = backend->preview("#ff583d", "expressive", false);
            QStringList cols;
            for (const auto &v : p) cols << v.toString();
            rep = "PREVIEW_N=" + QString::number(p.size()) + " COLORS=" + cols.join(",") + "\n";
        } else if (mode == "avatars") {
            for (const auto &v : backend->accounts()) {
                QVariantMap a = v.toMap();
                QString av = a.value("avatar").toString();
                QString local = QUrl(av.left(av.indexOf('?') >= 0 ? av.indexOf('?') : av.size())).toLocalFile();
                QImage img(local);
                rep += a.value("email").toString() + " | avatar=" + av + " | exists=" + (QFile::exists(local) ? "yes" : "no")
                     + " | loads=" + (img.isNull() ? "NO" : QString("%1x%2").arg(img.width()).arg(img.height())) + "\n";
            }
        } else if (mode == "scheme") {
            auto snap = [&]() { QVariantMap c = backend->colors(); return c.value("primary").toString() + "|" + c.value("onSurface").toString() + "|" + c.value("surfaceContainer").toString() + "|" + c.value("outline").toString(); };
            backend->applyTheme("ember", "#ff583d", true);
            QString base = snap();
            rep += "ember        " + base + " theme=" + backend->settings().value("themeId").toString() + "\n";
            backend->setScheme("#ff583d", "tonalSpot", true, 0.8);
            rep += "contrast .8  " + snap() + " theme=" + backend->settings().value("themeId").toString() + "\n";
            backend->setScheme("#ff583d", "tonalSpot", true, 0.0);
            rep += "contrast 0   " + snap() + " theme=" + backend->settings().value("themeId").toString() + (snap() == base ? "  RESTORED" : "  DIFFERENT") + "\n";
            backend->setScheme("#ff583d", "tonalSpot", false, 0.0);
            rep += "light        theme=" + backend->settings().value("themeId").toString() + "\n";
            backend->setScheme("#ff583d", "tonalSpot", true, 0.0);
            rep += "dark again   " + snap() + " theme=" + backend->settings().value("themeId").toString() + (snap() == base ? "  RESTORED" : "  DIFFERENT") + "\n";
            backend->setScheme("#0066ff", "tonalSpot", true, 0.0);
            rep += "other seed   theme=" + backend->settings().value("themeId").toString() + "\n";
        } else if (mode == "themes") {
            const QStringList keys = { "surface", "surfaceContainer", "surfaceContainerHigh", "onSurface", "onSurfaceVariant", "primary", "onPrimary",
                                       "primaryContainer", "onPrimaryContainer", "secondaryContainer", "onSecondaryContainer",
                                       "tertiaryContainer", "onTertiaryContainer", "error", "errorContainer", "onErrorContainer",
                                       "success", "successContainer", "warning", "warningContainer", "outline", "outlineVariant" };
            for (const auto &tv : backend->themes()) {
                QVariantMap t = tv.toMap();
                backend->applyTheme(t.value("id"), t.value("seed"), t.value("dark"));
                QVariantMap c = backend->colors();
                rep += "THEME " + t.value("id").toString() + " dark=" + (t.value("dark").toBool() ? "1" : "0");
                for (const QString &k : keys) rep += " " + k + "=" + c.value(k).toString();
                rep += "\n";
            }
        } else if (mode == "hasUnlock") {
            rep = QString("HAS_UNLOCK=%1\n").arg(backend->hasUnlockPassword() ? "true" : "false");
        } else {
            rep += QString("ACCOUNTS_N=%1\n").arg(backend->accounts().size());
            if (backend->accounts().size() > 0)
            {
                QVariantMap a0 = backend->accounts().at(0).toMap();
                rep += "ACCOUNT0_EMAIL=" + a0.value("email").toString() + "\n";
                rep += "ACCOUNT0_COOKIE=" + a0.value("cookie").toString() + " SAVED=" + QString(a0.value("saved").toBool() ? "yes" : "no")
                     + " USERID=" + a0.value("userId").toString() + " EXP=" + a0.value("expires").toString() + "\n";
            }
            rep += QString("REPORTS_N=%1\n").arg(backend->reports().size());
            rep += QString("SESSIONS_N=%1\n").arg(backend->sessions().size());
            rep += QString("COURSES_N=%1\n").arg(backend->courses().size());
            rep += "DATA_DIR=" + backend->dataDir() + "\n";
            rep += "SEED=" + backend->seed() + "\n";
            rep += "REPORT_SOURCE=" + backend->reportSource() + "\n";
        }
        QFile pf(QDir(appDirPath()).filePath(QStringLiteral("probe.out")));
        if (pf.open(QIODevice::WriteOnly)) { pf.write(rep.toUtf8()); pf.close(); }
        return 0;
    }
    qmlRegisterSingletonInstance<Backend>("Cool", 1, 0, "Backend", backend);
    qmlRegisterType<AvatarView>("Cool", 1, 0, "AvatarView");
    // TerminalView 已改用 xterm.js (WebEngineView)，不再註冊 QPainter 版

    // 每個終端分頁的 ConPTY + WebChannel 由 Backend 建立與管理；
    // QML 透過 Backend.terminalChannel(activeTerminalId) 取得該分頁專屬的 channel。
    QQmlApplicationEngine engine;

    engine.addImportPath(QDir(rootDirPath()).filePath(QStringLiteral("qml")));
    engine.addImportPath(QStringLiteral("C:/Qt/6.9.3/msvc2022_64/qml"));
    QString qmlFile = QDir(rootDirPath()).filePath(QStringLiteral("qml/Main.qml"));
    if (!qEnvironmentVariable("COOL_PROBE").isEmpty())
        qmlFile = QDir(rootDirPath()).filePath(QStringLiteral("probe.qml"));
    const QUrl url = QUrl::fromLocalFile(qmlFile);
    logf("start, importPaths=" + engine.importPathList().join(";"));
    QObject::connect(&engine, &QQmlApplicationEngine::objectCreationFailed, &app,
                     []() { logf("objectCreationFailed"); }, Qt::QueuedConnection);
    QObject::connect(&engine, &QQmlApplicationEngine::warnings, &app,
                     [](const QList<QQmlError> &errs) {
                         for (const auto &e : errs) logf("QML warn: " + e.toString());
                     });
    logf("engine.load begin");
    engine.load(url);
    logf("engine.load end");
    if (!qEnvironmentVariable("COOL_STALL_LOG").isEmpty() && !engine.rootObjects().isEmpty()) {
        // 畫面更新率：每秒記錄一次（拖曳、抽屜動畫時掉幀就是「卡」）
        if (auto *w = qobject_cast<QQuickWindow *>(engine.rootObjects().first())) {
            auto *frames = new int(0);
            QObject::connect(w, &QQuickWindow::frameSwapped, w, [frames]() { ++*frames; });
            auto *fpsTimer = new QTimer(w);
            fpsTimer->setInterval(1000);
            QObject::connect(fpsTimer, &QTimer::timeout, [frames]() { logf(QString("FPS %1").arg(*frames)); *frames = 0; });
            fpsTimer->start();
        }
    }
    logf("rootObjects=" + QString::number(engine.rootObjects().size()));
    if (engine.rootObjects().isEmpty()) {
        return -1;
    }
    // 內建截圖模式：載入完成後抓窗口存圖
    if (!qEnvironmentVariable("COOL_SHOT").isEmpty()) {
        int shotPage = qEnvironmentVariable("COOL_SHOT_PAGE", "0").toInt();
        QString shotOut = qEnvironmentVariable("COOL_SHOT_OUT",
                            QDir(appDirPath()).filePath(QStringLiteral("app-shot.png")));
        bool shotTerm = !qEnvironmentVariable("COOL_SHOT_TERM").isEmpty();
        QTimer::singleShot(1200, [&, shotPage, shotOut, shotTerm]() {
            QObject *root = engine.rootObjects().isEmpty() ? nullptr : engine.rootObjects().first();
            if (root && shotPage > 0) root->setProperty("page", shotPage);
            if (root && !qEnvironmentVariable("COOL_SHOT_ACCT").isEmpty())
                if (QObject *menu = root->findChild<QObject *>("acctMenu")) QMetaObject::invokeMethod(menu, "open");
            if (root && shotTerm) {
                // setProperty("termOpen", true) 會觸發 onTermOpenChanged 開第一個分頁（預設 pwsh）
                root->setProperty("termOpen", true);
                // 測試用：再開一個不同種類的分頁，驗證每個分頁獨立
                if (!qEnvironmentVariable("COOL_SHOT_TERM2").isEmpty())
                    QMetaObject::invokeMethod(backend, "startTerminal",
                                              Q_ARG(QVariant, QVariant(QStringLiteral("cmd"))));
            }
            QTimer::singleShot(shotTerm ? 12000 : 1500, [&, shotOut]() {
                QObject *r = engine.rootObjects().isEmpty() ? nullptr : engine.rootObjects().first();
                QQuickWindow *win = qobject_cast<QQuickWindow *>(r);
                if (win) {
                    QImage img = win->grabWindow();
                    img.save(shotOut);
                    logf("shot saved: " + shotOut);
                } else logf("no window for shot");
                qApp->quit();
            });
        });
    }
    // 自動測試：COOL_AUTOTEST=report|cookie|go → 觸發對應的 CLI 綁定動作，25 秒後輸出工作階段摘要
    if (!qEnvironmentVariable("COOL_AUTOTEST").isEmpty()) {
        const QString what = qEnvironmentVariable("COOL_AUTOTEST");
        QTimer::singleShot(1500, [backend, what]() {
            if (what == "report") backend->refreshReports();
            else if (what == "cookie") backend->checkCookie(0);
            else if (what == "go") backend->openAlias(QStringLiteral("a"), QStringLiteral("headless"));
            else if (what == "tabs") {
                // 多分頁切換測試：分頁 1 輸入標記 → 開分頁 2 → 切回分頁 1 → 截圖
                QObject *root = qApp->property("coolRoot").value<QObject *>();
                Q_UNUSED(root);
                QMetaObject::invokeMethod(backend, "startTerminal", Q_ARG(QVariant, QVariant(QStringLiteral("cmd"))));
                QTimer::singleShot(3500, [backend]() {
                    backend->writeTerminal(QStringLiteral("echo FIRSTTAB_MARK_12345"));
                    QTimer::singleShot(1500, [backend]() {
                        QMetaObject::invokeMethod(backend, "startTerminal", Q_ARG(QVariant, QVariant(QStringLiteral("powershell"))));
                        QTimer::singleShot(3500, [backend]() {
                            backend->selectTerminalTab(2);
                        });
                    });
                });
            }
            else if (what == "login")
                backend->startLogin(qEnvironmentVariable("COOL_TEST_EMAIL"), qEnvironmentVariable("COOL_TEST_PASS"),
                                    QString(), qEnvironmentVariable("COOL_TEST_MODE", "headed"));
        });
        if (what == "termcmd") {
            // COOL_TEST_CMDS="指令1||指令2"：打開抽屜、依序送進終端機，每個指令後 COOL_TEST_STEP 秒（預設 14）截圖到 COOL_TEST_SHOTOUT-<序號>.png
            const QStringList cmds = qEnvironmentVariable("COOL_TEST_CMDS").split(QStringLiteral("||"));
            const int step = qEnvironmentVariable("COOL_TEST_STEP", "14").toInt() * 1000;
            auto grab = [&engine](const QString &suffix) {
                if (engine.rootObjects().isEmpty()) return;
                if (auto *win = qobject_cast<QQuickWindow *>(engine.rootObjects().first()))
                    win->grabWindow().save(qEnvironmentVariable("COOL_TEST_SHOTOUT") + suffix + ".png");
            };
            QTimer::singleShot(1500, [&engine]() { if (!engine.rootObjects().isEmpty()) engine.rootObjects().first()->setProperty("termOpen", true); });
            int t = 16000;                                   // 等環境檢查跑完、出現 cool>
            QTimer::singleShot(t - 500, [grab]() { grab(QStringLiteral("-start")); });
            for (int i = 0; i < cmds.size(); ++i) {
                const QString c = cmds.at(i);
                QTimer::singleShot(t, [backend, c, i]() { logf(QString("send %1: %2").arg(i).arg(c)); backend->writeTerminal(c); });
                QTimer::singleShot(t + 2000, [grab, i]() { grab(QString("-%1a").arg(i)); });
                t += step;
                QTimer::singleShot(t - 500, [grab, i]() { grab(QString("-%1b").arg(i)); });
            }
        }
        if (what == "termtabs") {
            auto root = [&engine]() -> QObject * { return engine.rootObjects().isEmpty() ? nullptr : engine.rootObjects().first(); };
            QTimer::singleShot(2000, [root]() { root()->setProperty("termOpen", true); logf("T open"); });
            QTimer::singleShot(6000, [backend]() { logf("T start 2nd"); backend->startTerminal(QVariant(QStringLiteral("cmd"))); });
            QTimer::singleShot(9000, [backend]() { logf("T start 3rd (default)"); backend->launchTerminal(QVariant()); });
            QTimer::singleShot(12000, [backend]() { logf("T close active"); backend->closeTerminalTab(QVariant(backend->activeTerminalId())); });
            QTimer::singleShot(15000, [backend]() { logf("T close active"); backend->closeTerminalTab(QVariant(backend->activeTerminalId())); });
            QTimer::singleShot(18000, [backend]() { logf("T close last"); backend->closeTerminalTab(QVariant(backend->activeTerminalId())); });
            QTimer::singleShot(21000, [root, backend]() { logf("T reopen"); backend->startTerminal(QVariant()); root()->setProperty("termOpen", true); });
        }
        if (what == "termtoggle")
            for (int i = 0; i < 6; ++i)
                QTimer::singleShot(3000 + i * 3500, [&engine, i]() {
                    if (!engine.rootObjects().isEmpty()) {
                        engine.rootObjects().first()->setProperty("termOpen", i % 2 == 0);
                        logf(QString("termOpen=%1").arg(i % 2 == 0));
                    }
                });
        if (!qEnvironmentVariable("COOL_TEST_SHOTPAGE").isEmpty())
            QTimer::singleShot(qEnvironmentVariable("COOL_TEST_SHOTDELAY", "1500").toInt(), [&engine]() {
                if (!engine.rootObjects().isEmpty())
                    engine.rootObjects().first()->setProperty("page", qEnvironmentVariable("COOL_TEST_SHOTPAGE").toInt());
            });
        if (!qEnvironmentVariable("COOL_TEST_DETAILTAB").isEmpty())
            QTimer::singleShot(9000, [&engine]() {
                if (engine.rootObjects().isEmpty()) return;
                if (QObject *np = engine.rootObjects().first()->findChild<QObject *>("networkPage")) {
                    np->setProperty("view", 0);
                    np->setProperty("detailTab", qEnvironmentVariable("COOL_TEST_DETAILTAB").toInt());
                }
            });
        QTimer::singleShot(qEnvironmentVariable("COOL_TEST_WAIT", "30000").toInt(), [backend, &engine]() {
            if (!qEnvironmentVariable("COOL_TEST_SHOTOUT").isEmpty() && !engine.rootObjects().isEmpty())
                if (auto *win = qobject_cast<QQuickWindow *>(engine.rootObjects().first()))
                    win->grabWindow().save(qEnvironmentVariable("COOL_TEST_SHOTOUT"));
            QString rep;
            for (const auto &v : backend->sessions()) {
                QVariantMap m = v.toMap();
                rep += m.value("label").toString() + " | " + m.value("mode").toString() + " | " + m.value("status").toString()
                     + " | events=" + QString::number(m.value("events_n").toInt()) + "\n" + m.value("lines").toString() + "\n";
            }
            rep += "toastlog end\n";
            QFile pf(QDir(appDirPath()).filePath(QStringLiteral("autotest.out")));
            if (pf.open(QIODevice::WriteOnly)) { pf.write(rep.toUtf8()); pf.close(); }
            qApp->quit();
        });
    }
    logf("exec");
    return app.exec();
}
#include "main.moc"
