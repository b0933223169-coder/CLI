#include "term_buffer.h"
#include <QHash>

TermBuffer::TermBuffer(QObject *parent) : QObject(parent) {
    setSize(m_cols, m_rows);
}

void TermBuffer::setSize(int cols, int rows) {
    QMutexLocker l(&m_mutex);
    if (cols < 1 || rows < 1) return;
    m_cols = cols; m_rows = rows;
    // 調整每行的寬度
    for (auto &line : m_screen) line.resize(cols, Cell());
    while (m_screen.size() < rows) m_screen.append(QVector<Cell>(cols, Cell()));
    while (m_screen.size() > rows) {
        m_history.append(m_screen.takeFirst());
        if (m_history.size() > MAX_HISTORY) m_history.removeFirst();
    }
    if (m_curX >= cols) m_curX = cols - 1;
    if (m_curY >= rows) m_curY = rows - 1;
    emit changed();
}

void TermBuffer::feed(const QByteArray &data) {
    QMutexLocker l(&m_mutex);
    bool dirty = false;
    QByteArray pending;  // 收集可列印位元組（含 UTF-8 多位元組），一次解碼
    auto flushPending = [&]() {
        if (pending.isEmpty()) return;
        QString text = QString::fromUtf8(pending);
        for (int j = 0; j < text.size(); ++j) { putChar(text.at(j)); }
        pending.clear();
        dirty = true;
    };
    for (int i = 0; i < data.size(); ++i) {
        unsigned char c = (unsigned char)data.at(i);
        if (m_state == Normal) {
            if (c == 0x1b) { flushPending(); m_state = Esc; m_escBuf.clear(); }
            else if (c == '\r') { flushPending(); carriageReturn(); dirty = true; }
            else if (c == '\n') { flushPending(); lineFeed(); dirty = true; }
            else if (c == '\b') { flushPending(); if (m_curX > 0) --m_curX; dirty = true; }
            else if (c == '\t') {
                flushPending();
                int nx = (m_curX / 8 + 1) * 8;
                if (nx >= m_cols) nx = m_cols - 1;
                while (m_curX < nx) { putChar(QChar(' ')); }
                dirty = true;
            }
            else if (c >= 0x20) { pending.append((char)c); }
            else { flushPending(); }  // 其他控制碼略過
        } else if (m_state == Esc) {
            m_escBuf.append((char)c);
            if (c == '[') { m_state = Csi; m_escBuf.clear(); }
            else if (c == ']') { m_state = Osc; m_escBuf.clear(); }
            else { m_state = Normal; m_escBuf.clear(); }  // 略過其他 ESC
        } else if (m_state == Csi) {
            m_escBuf.append((char)c);
            if (c >= 0x40 && c <= 0x7e) {  // 最終位元組
                applyCSI(m_escBuf);
                m_escBuf.clear(); m_state = Normal; dirty = true;
            }
        } else if (m_state == Osc) {
            if (c == 0x07) { m_escBuf.clear(); m_state = Normal; }
            else if (c == 0x1b) { m_oscEsc = true; }
            else if (c == 0x5c && m_oscEsc) { m_escBuf.clear(); m_oscEsc=false; m_state = Normal; }
            else { m_oscEsc = false; }
        }
    }
    flushPending();  // 處理結尾殘留的可列印位元組
    if (dirty) emit changed();
}

void TermBuffer::putChar(QChar c) {
    if (m_curY >= 0 && m_curY < m_screen.size()) {
        Cell cell(c, m_fg ? m_fg : m_defaultFg, m_bg, m_bold);
        m_screen[m_curY][m_curX] = cell;
    }
    ++m_curX;
    if (m_curX >= m_cols) { m_curX = 0; lineFeed(); }
}

void TermBuffer::lineFeed() {
    ++m_curY;
    if (m_curY >= m_rows) { m_curY = m_rows - 1; scrollUp(); }
}
void TermBuffer::carriageReturn() { m_curX = 0; }
void TermBuffer::scrollUp() {
    if (m_screen.isEmpty()) return;
    m_history.append(m_screen.takeFirst());
    if (m_history.size() > MAX_HISTORY) m_history.removeFirst();
    m_screen.append(QVector<Cell>(m_cols, Cell()));
}

void TermBuffer::applyCSI(const QByteArray &seq) {
    char final = seq.isEmpty() ? 0 : seq.at(seq.size()-1);
    QByteArray nums = seq.mid(0, seq.size()-1);
    // 去掉前導 '?' 和 '>'
    bool privateMode = false;
    if (nums.startsWith('?') || nums.startsWith('>')) { privateMode = true; nums.remove(0,1); }
    QList<QByteArray> parts = nums.split(';');
    QVector<int> p;
    for (const auto &s : parts) {
        bool ok=false; int v=s.toInt(&ok);
        p.append(ok ? v : 0);
    }
    int a = p.value(0, 0);

    if (privateMode && final == 'h') {
        if (a == 25) m_cursorVisible = true;   // DECTCEM show
        return;
    }
    if (privateMode && final == 'l') {
        if (a == 25) m_cursorVisible = false;  // hide
        return;
    }

    switch (final) {
    case 'H': case 'f': {
        int row = p.value(0,1) - 1, col = p.value(1,1) - 1;
        m_curY = qBound(0, row, m_rows-1);
        m_curX = qBound(0, col, m_cols-1);
        break;
    }
    case 'A': m_curY = qBound(0, m_curY - qMax(1,a), m_rows-1); break; // up
    case 'B': m_curY = qBound(0, m_curY + qMax(1,a), m_rows-1); break; // down
    case 'C': m_curX = qBound(0, m_curX + qMax(1,a), m_cols-1); break; // forward
    case 'D': m_curX = qBound(0, m_curX - qMax(1,a), m_cols-1); break; // back
    case 'G': m_curX = qBound(0, a-1, m_cols-1); break;               // CHA
    case 'J': { // erase in display
        int mode = p.value(0,0);
        if (mode == 2) { // clear all
            for (auto &line : m_screen) line.fill(Cell());
            m_curX = 0; m_curY = 0;
        } else if (mode == 0) { // from cursor to end
            if (m_curY >= 0 && m_curY < m_screen.size())
                for (int x = m_curX; x < m_cols; ++x) m_screen[m_curY][x] = Cell();
            for (int y = m_curY+1; y < m_screen.size(); ++y) m_screen[y].fill(Cell());
        }
        break;
    }
    case 'K': { // erase in line
        int mode = p.value(0,0);
        if (m_curY >= 0 && m_curY < m_screen.size()) {
            if (mode == 0) for (int x=m_curX;x<m_cols;++x) m_screen[m_curY][x]=Cell();
            else if (mode == 1) for (int x=0;x<=m_curX && x<m_cols;++x) m_screen[m_curY][x]=Cell();
            else if (mode == 2) m_screen[m_curY].fill(Cell());
        }
        break;
    }
    case 'm': applySGR(p); break;
    default: break;
    }
}

void TermBuffer::applySGR(const QVector<int> &params) {
    if (params.isEmpty()) { m_fg=0; m_bg=0; m_bold=false; return; }
    for (int i=0;i<params.size();++i) {
        int v = params[i];
        if (v == 0) { m_fg=0; m_bg=0; m_bold=false; }
        else if (v == 1) m_bold = true;
        else if (v == 22) m_bold = false;
        else if (v >= 30 && v <= 37) m_fg = ansiColor(v-30, false);
        else if (v >= 90 && v <= 97) m_fg = ansiColor(v-90, true);
        else if (v >= 40 && v <= 47) m_bg = ansiColor(v-40, false);
        else if (v >= 100 && v <= 107) m_bg = ansiColor(v-100, true);
        else if (v == 38 || v == 48) { // extended color
            bool fg = (v==38);
            if (i+1 < params.size() && params[i+1]==5 && i+2 < params.size()) {
                QRgb c = xterm256(params[i+2]); if (fg) m_fg=c; else m_bg=c; i+=2;
            } else if (i+1 < params.size() && params[i+1]==2 && i+4 < params.size()) {
                QRgb c = qRgb(params[i+2],params[i+3],params[i+4]); if(fg)m_fg=c;else m_bg=c; i+=4;
            }
        }
        else if (v == 39) m_fg = 0;
        else if (v == 49) m_bg = 0;
    }
}

QRgb TermBuffer::ansiColor(int code, bool bright) const {
    static const QRgb normal[8] = {
        qRgb(0x1a,0x10,0x30), qRgb(0xc0,0x39,0x2b), qRgb(0x4e,0x9a,0x42), qRgb(0xc2,0xa4,0x3a),
        qRgb(0x3b,0x6b,0xb8), qRgb(0x8a,0x3c,0xa0), qRgb(0x2a,0x9a,0x9e), qRgb(0xd0,0xd0,0xd0)
    };
    static const QRgb brightC[8] = {
        qRgb(0x60,0x60,0x70), qRgb(0xff,0x6b,0x5a), qRgb(0x7c,0xd0,0x6e), qRgb(0xff,0xd8,0x5a),
        qRgb(0x6a,0xa8,0xff), qRgb(0xc9,0x7a,0xe0), qRgb(0x5a,0xd8,0xda), qRgb(0xff,0xff,0xff)
    };
    if (code<0||code>7) return 0;
    return bright ? brightC[code] : normal[code];
}

QRgb TermBuffer::xterm256(int n) const {
    if (n < 16) return ansiColor(n % 8, n >= 8);
    if (n < 232) {
        n -= 16;
        int r = (n/36)*51, g = ((n%36)/6)*51, b = (n%6)*51;
        return qRgb(r,g,b);
    }
    int gray = 8 + (n-232)*10;
    return qRgb(gray,gray,gray);
}

QVector<Cell> TermBuffer::line(int row) const {
    QMutexLocker l(&m_mutex);
    if (row < 0 || row >= m_screen.size()) return QVector<Cell>(m_cols, Cell());
    return m_screen[row];
}

int TermBuffer::displayStart() const { return m_history.size(); }
