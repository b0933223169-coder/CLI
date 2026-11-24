// 最小驗證：Qt WebEngine + xterm.js + QWebChannel + ConPTY
#include <QApplication>
#include <QWebEngineView>
#include <QWebEnginePage>
#include <QWebChannel>
#include <QWebChannelAbstractTransport>
#include <QFile>
#include <QDebug>
#include "conpty.h"

// PtyBridge：暴露給 JS 的物件
class PtyBridge : public QObject {
    Q_OBJECT
public:
    explicit PtyBridge(ConPty *pty, QObject *parent=nullptr) : QObject(parent), m_pty(pty) {}
public slots:
    void sendInput(const QString &b64) { m_pty->writeInput(QByteArray::fromBase64(b64.toLatin1())); }
    void resize(int c, int r) { m_pty->resize(c, r);
        QFile f("C:/Users/jusaper/Downloads/coolqml-rs/we-status.log");
        if(f.open(QIODevice::Append)) f.write(QString("RESIZE %1x%2\n").arg(c).arg(r).toUtf8()); }
signals:
    void outputReady(const QString &b64);
private:
    ConPty *m_pty;
};

int main(int argc, char *argv[]){
    QApplication app(argc, argv);
    { QFile f("C:/Users/jusaper/Downloads/coolqml-rs/we-status.log");
      if(f.open(QIODevice::WriteOnly)) f.write("start\n"); }

    ConPty pty;
    QStringList args;
    args << "/k" << "cd /d C:\\Users\\jusaper\\Downloads\\cool-qml-caelestia\\coolqml && python cool.py";
    bool ok = pty.start("cmd.exe", args, QString(), 100, 30);
    { QFile f("C:/Users/jusaper/Downloads/coolqml-rs/we-status.log");
      if(f.open(QIODevice::Append)) f.write(QString("pty start=%1\n").arg(ok).toUtf8()); }

    PtyBridge bridge(&pty);
    QObject::connect(&pty, &ConPty::output, &bridge, [&](const QByteArray &d){
        emit bridge.outputReady(QString::fromLatin1(d.toBase64()));
    });

    QWebEngineView view;
    view.resize(900, 500);
    QWebChannel channel;
    channel.registerObject("pty", &bridge);
    view.page()->setWebChannel(&channel);
    view.setUrl(QUrl::fromLocalFile("C:/Users/jusaper/Downloads/coolqml-rs/xterm/index.html"));
    view.show();

    return app.exec();
}
#include "we_host.moc"
