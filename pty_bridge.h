#pragma once
#include <QObject>
#include <QWebSocketServer>
#include "conpty.h"

class QWebSocket;

// 把 ConPTY 透過原生 WebSocket(JSON) 橋接給 xterm.js
// 協定：C++→JS {"type":"output","data":"<base64>"}
//       JS→C++ {"type":"input","data":"<base64>"} / {"type":"resize","cols":n,"rows":m}
class PtyBridge : public QObject {
    Q_OBJECT
public:
    explicit PtyBridge(QObject *parent = nullptr);
    ~PtyBridge();
    bool startServer(quint16 port);
    void startShell();

private slots:
    void onNewConnection();
    void onTextMessage(const QString &msg);

private:
    void log(const QString &msg);
    ConPty *m_pty;
    QWebSocketServer *m_wsServer;
    QWebSocket *m_socket;
};
