#include "pty_bridge.h"
#include <QWebSocket>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QHostAddress>

PtyBridge::PtyBridge(QObject *parent) : QObject(parent), m_socket(nullptr) {
    m_pty = new ConPty(this);
    m_wsServer = new QWebSocketServer(QStringLiteral("coolpty"),
                                      QWebSocketServer::NonSecureMode, this);
    connect(m_wsServer, &QWebSocketServer::newConnection, this, &PtyBridge::onNewConnection);
    connect(m_pty, &ConPty::output, this, [this](const QByteArray &data){
        if (!m_socket) return;
        QJsonObject o;
        o["type"] = "output";
        o["data"] = QString::fromLatin1(data.toBase64());
        m_socket->sendTextMessage(QString::fromUtf8(
            QJsonDocument(o).toJson(QJsonDocument::Compact)));
    });
}
PtyBridge::~PtyBridge() {}

void PtyBridge::log(const QString &msg) {
    QFile f("C:/Users/jusaper/Downloads/coolqml-rs/wv-status.log");
    if (f.open(QIODevice::Append)) f.write((msg+"\n").toUtf8());
}

bool PtyBridge::startServer(quint16 port) {
    if (!m_wsServer->listen(QHostAddress::LocalHost, port)) {
        log("WS listen failed: " + m_wsServer->errorString());
        return false;
    }
    log("WS server started on 18181");
    return true;
}

void PtyBridge::onNewConnection() {
    if (m_socket) { m_socket->close(); m_socket->deleteLater(); }
    m_socket = m_wsServer->nextPendingConnection();
    log("CLIENT CONNECTED");
    connect(m_socket, &QWebSocket::textMessageReceived, this, &PtyBridge::onTextMessage);
    connect(m_socket, &QWebSocket::disconnected, this, [this](){
        log("CLIENT DISCONNECTED");
        m_socket = nullptr;
    });
}

void PtyBridge::onTextMessage(const QString &msg) {
    QJsonParseError err;
    QJsonDocument doc = QJsonDocument::fromJson(msg.toUtf8(), &err);
    if (err.error != QJsonParseError::NoError) return;
    QJsonObject o = doc.object();
    QString type = o.value("type").toString();
    if (type == "input") {
        QByteArray data = QByteArray::fromBase64(o.value("data").toString().toLatin1());
        m_pty->writeInput(data);
    } else if (type == "resize") {
        int cols = o.value("cols").toInt(), rows = o.value("rows").toInt();
        log(QString("RESIZE %1x%2").arg(cols).arg(rows));
        m_pty->resize(cols, rows);
    }
}

void PtyBridge::startShell() {
    QStringList args;
    args << QStringLiteral("/k")
         << QStringLiteral("cd /d C:\\Users\\jusaper\\Downloads\\cool-qml-caelestia\\coolqml && python cool.py");
    m_pty->start(QStringLiteral("cmd.exe"), args, QString(), 100, 30);
}
