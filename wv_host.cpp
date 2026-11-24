#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQuickWindow>
#include <QTimer>
#include <QFile>
#include <QDebug>
#include "pty_bridge.h"

int main(int argc, char *argv[]){
    QGuiApplication app(argc, argv);
    app.setApplicationName("xterm-webview-test");

    // 啟動 WebSocket 橋 + ConPTY
    PtyBridge bridge;
    if(!bridge.startServer(18181)){ qWarning()<<"WS server failed"; return -1; }
    bridge.startShell();
    { QFile lf("C:/Users/jusaper/Downloads/coolqml-rs/wv-status.log");
      if(lf.open(QIODevice::WriteOnly)) lf.write("WS server started on 18181\n"); }

    QQmlApplicationEngine engine;
    engine.addImportPath("C:/Qt/6.9.3/mingw_64/qml");
    engine.load(QUrl::fromLocalFile("C:/Users/jusaper/Downloads/coolqml-rs/webview_test.qml"));
    if(engine.rootObjects().isEmpty()){ qWarning()<<"load fail"; return -1; }

    // webview_test.qml 載入 xterm/index.html（WebSocket 版）
    // 讓 PtyBridge 在有連線時寫 log（在 pty_bridge 內做），這裡定時檢查
    QTimer::singleShot(15000, [&](){ qApp->quit(); });
    return app.exec();
}
