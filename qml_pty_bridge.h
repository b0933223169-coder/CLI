#pragma once
#include <QObject>
#include <QElapsedTimer>
#include <QByteArray>
#include "conpty.h"

class QTimer;

// 給 QML WebChannel 註冊的 ConPTY 橋（JS 用 channel.objects.pty）。
// 每一個終端分頁都有自己獨立的一個實例 + 自己的 ConPty。
class QmlPtyBridge : public QObject {
    Q_OBJECT
public:
    explicit QmlPtyBridge(QObject *parent = nullptr);
    ~QmlPtyBridge();

    Q_INVOKABLE bool startShell(const QString &program, const QStringList &args,
                                const QString &boot = QString(), const QString &cwd = QString());
    Q_INVOKABLE bool running() const;
    Q_INVOKABLE void stop();
    QByteArray buffer() const { return m_buffer; }

public slots:
    void sendInput(const QString &b64);
    void resize(int cols, int rows);
    // JS 連上後呼叫，立刻把目前累積的輸出送出（避免 connect 前的資料遺失）
    void flush();
    void detach();      // 畫面離開（切換分頁）時呼叫，暫停推送

signals:
    void outputReady(const QString &b64);
    void historyReady(const QString &b64);   // 畫面（重新）載入後的完整歷史；空字串 = 沒有歷史
    void exitRequested();            // 使用者在終端輸入 /exit

private:
    void flushBuffer();
    ConPty *m_pty;
    QString m_line;
    bool m_connected = false;
    QByteArray m_buffer;     // 尚未推送的新輸出
    bool m_everConnected = false, m_repliedDA = false, m_repliedCPR = false;
    QByteArray m_history;    // 完整輸出歷史：切換分頁後 xterm 重新載入時整段重播
    QTimer *m_flushTimer;
};
