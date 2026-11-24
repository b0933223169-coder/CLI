#include <QDebug>
#include <QFile>
#include "qml_pty_bridge.h"
#include <QTimer>

QmlPtyBridge::QmlPtyBridge(QObject *parent) : QObject(parent) {
    m_pty = new ConPty(this);
    connect(m_pty, &ConPty::output, this, [this](const QByteArray &data){
        // ConPTY 啟動時會先查詢終端機（裝置屬性 ESC[c、游標位置 ESC[6n），沒人回應就乾等約 3 秒才繼續。
        // 這些查詢在 xterm 頁面載入完成前就送出，頁面連上時又會清掉先前累積的輸出，所以永遠沒人回應。
        // 因此在還沒有畫面連上之前，由這裡直接回應（連上之後由 xterm 自己回應）。
        if (!m_everConnected) {
            if (!m_repliedDA && data.contains("\x1b[c")) {
                m_repliedDA = true;
                m_pty->writeInput(QByteArray("\x1b[?1;0c"));
            }
            if (!m_repliedCPR && data.contains("\x1b[6n")) {
                m_repliedCPR = true;
                m_pty->writeInput(QByteArray("\x1b[1;1R"));
            }
        }
        m_buffer.append(data);
        if (m_buffer.size() > 1024 * 1024) m_buffer = m_buffer.right(1024 * 1024);
        // 歷史上限 2 MB；超過時從最舊處砍掉一半，並對齊到下一個換行，避免從跳脫序列中間開始重播
        m_history.append(data);
        if (m_history.size() > 2 * 1024 * 1024) {
            int cut = m_history.size() / 2;
            int nl = m_history.indexOf('\n', cut);
            m_history = m_history.mid(nl >= 0 ? nl + 1 : cut);
        }
    });
    // 定期推送：不依賴 ConPTY reader thread → JS 的 signal 跨執行緒時序
    m_flushTimer = new QTimer(this);
    m_flushTimer->setInterval(100);
    connect(m_flushTimer, &QTimer::timeout, this, &QmlPtyBridge::flushBuffer);
    m_flushTimer->start();
}
QmlPtyBridge::~QmlPtyBridge() {}

void QmlPtyBridge::flushBuffer() {
    if (m_buffer.isEmpty()) return;
    if (!m_connected) return;               // 沒有畫面在看（切到別的分頁）時先不推送，內容已保存在歷史裡
    QByteArray out = m_buffer;
    m_buffer.clear();
    emit outputReady(QString::fromLatin1(out.toBase64()));
}

bool QmlPtyBridge::startShell(const QString &program, const QStringList &args,
                              const QString &boot, const QString &cwd) {
    if (m_pty->running()) return true;
    bool ok = m_pty->start(program, args, cwd, 100, 30);
    if (ok && !boot.isEmpty()) m_pty->writeInput(boot.toUtf8());
    return ok;
}
bool QmlPtyBridge::running() const { return m_pty->running(); }
void QmlPtyBridge::stop() { if (m_pty->running()) m_pty->kill(); }
void QmlPtyBridge::sendInput(const QString &b64) {
    const QByteArray data = QByteArray::fromBase64(b64.toLatin1());
    m_pty->writeInput(data);
    // 追蹤使用者目前輸入的整行：輸入 /exit 並按 Enter 會關閉整個工作臺
    const QString text = QString::fromUtf8(data);
    for (const QChar ch : text) {
        if (ch == QLatin1Char('\r') || ch == QLatin1Char('\n')) {
            const bool quit = m_line == QLatin1String("/exit");
            m_line.clear();
            if (quit) { emit exitRequested(); return; }
        } else if (ch == QChar(0x7f) || ch == QChar(0x08)) {
            m_line.chop(1);
        } else if (ch == QChar(0x1b) || ch == QChar(0x03) || ch == QChar(0x15)) {
            m_line.clear();
        } else if (ch.unicode() >= 0x20) {
            m_line.append(ch);
        }
    }
}
void QmlPtyBridge::resize(int cols, int rows) {
    m_pty->resize(cols, rows);
}
void QmlPtyBridge::flush() {
    // xterm 頁面（重新）載入完成：把完整歷史重播給它，之後只推增量。
    // 切換分頁時網頁會重新載入，若只送增量，原本畫面上的文字就會不見。
    m_connected = true;
    m_everConnected = true;
    m_buffer.clear();
    emit historyReady(m_history.isEmpty() ? QString() : QString::fromLatin1(m_history.toBase64()));
}
void QmlPtyBridge::detach() { m_connected = false; }
