#pragma once
#include <QString>
#include <QObject>
#include <QMutex>
#include <QByteArray>
#ifdef Q_OS_WIN
typedef unsigned long DWORD;
#else
typedef unsigned long DWORD;
#endif

// Win32 ConPTY 封裝：在背景執行緒啟動真終端、讀 output、寫 input、resize。
// 完全不依賴 Python / pywinpty。
class ConPty : public QObject {
    Q_OBJECT
public:
    explicit ConPty(QObject *parent = nullptr);
    ~ConPty();

    // 啟動一個真正的 shell（program 例如 powershell.exe / cmd.exe）
    bool start(const QString &program, const QStringList &args,
               const QString &cwd, int cols, int rows);
    void writeInput(const QByteArray &data);
    void resize(int cols, int rows);
    void kill();
    bool running() const;

signals:
    void output(const QByteArray &data);   // ConPTY 原始輸出（ANSI bytes）
    void finished(int exitCode);

private:
    struct Private;
    Private *d;
};
