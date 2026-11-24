#pragma once
#include <QObject>
#include <QVector>
#include <QColor>
#include <QMutex>

// 輕量 ANSI 終端畫面緩衝區：解析 ConPTY 輸出，維護可見畫面 + 捲動歷史。
// 支援：可列印字元、CR/LF/BS、游標移動 (CSI H/f/A/B/C/D)、
//       清除 (CSI J/K)、SGR 顏色 (16/256/true color)、游標顯隐 (CSI ?25)。
struct Cell {
    QChar ch = QChar(' ');
    QRgb fg = 0xFFFFFFFF;   // 預設前景
    QRgb bg = 0x00000000;   // 透明=用背景
    bool bold = false;
    Cell() {}
    Cell(QChar c, QRgb f, QRgb b, bool bo):ch(c),fg(f),bg(b),bold(bo){}
};

class TermBuffer : public QObject {
    Q_OBJECT
public:
    explicit TermBuffer(QObject *parent = nullptr);

    void feed(const QByteArray &data);
    void setSize(int cols, int rows);
    int cols() const { return m_cols; }
    int rows() const { return m_rows; }

    // 取得可見畫面某一行的 cells
    QVector<Cell> line(int row) const;
    int cursorRow() const { return m_curY; }
    int cursorCol() const { return m_curX; }
    bool cursorVisible() const { return m_cursorVisible; }
    QRgb defaultFg() const { return m_defaultFg; }
    QRgb defaultBg() const { return m_defaultBg; }

    // _history.top 之前的捲動行（供捲輪回溯）
    const QVector<QVector<Cell>> &history() const { return m_history; }
    int displayStart() const;  // 畫面在 (history + screen) 中的起始 index

signals:
    void changed();

private:
    void putChar(QChar c);
    void lineFeed();
    void carriageReturn();
    void scrollUp();
    void applyCSI(const QByteArray &seq);
    void applySGR(const QVector<int> &params);
    QRgb ansiColor(int code, bool bright) const;
    QRgb xterm256(int n) const;

    int m_cols = 80, m_rows = 24;
    QVector<QVector<Cell>> m_screen;   // 可見畫面
    QVector<QVector<Cell>> m_history;  // 捲出的行
    int m_curX = 0, m_curY = 0;
    bool m_cursorVisible = true;
    QRgb m_defaultFg = 0xFFD0D0D0, m_defaultBg = 0xFF1A1030;
    QRgb m_fg = 0, m_bg = 0;
    bool m_bold = false;
    QByteArray m_escBuf;
    bool m_oscEsc = false;
    enum State { Normal, Esc, Csi, Osc } m_state = Normal;
    mutable QMutex m_mutex;

    static const int MAX_HISTORY = 2000;
};
