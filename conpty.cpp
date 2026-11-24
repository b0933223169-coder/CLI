#include "conpty.h"
#include <QFileInfo>
#include <QDebug>
#include <QFile>
#include <iomanip>

#ifdef Q_OS_WIN
#include <windows.h>

// MinGW 舊 headers 缺的定義
typedef void* HPCON;
#ifndef PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE
#define PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE 0x00020016
#endif
typedef HRESULT(WINAPI *PFN_CreatePseudoConsole)(COORD, HANDLE, HANDLE, DWORD, HPCON*);
typedef HRESULT(WINAPI *PFN_ResizePseudoConsole)(HPCON, COORD);
typedef void(WINAPI *PFN_ClosePseudoConsole)(HPCON);

struct ConPty::Private {
    HPCON hpc = nullptr;
    HANDLE inWrite = INVALID_HANDLE_VALUE;   // 我們寫 input 給 console
    HANDLE outRead = INVALID_HANDLE_VALUE;   // 我們讀 console 的 output
    HANDLE hProcess = INVALID_HANDLE_VALUE;
    HANDLE hThread = INVALID_HANDLE_VALUE;
    HANDLE hStop = INVALID_HANDLE_VALUE;     // 停止 reader 的事件
    HANDLE hReader = INVALID_HANDLE_VALUE;   // reader thread
    bool running = false;
    QMutex mutex;
    int cols = 80, rows = 24;

    struct ReaderCtx { ConPty *self; Private *d; };
    static DWORD WINAPI reader(LPVOID p) {
        ReaderCtx *ctx = (ReaderCtx*)p;
        char buf[8192];
        DWORD n = 0;
        while (ctx->d->running) {
            BOOL ok = ReadFile(ctx->d->outRead, buf, sizeof(buf), &n, nullptr);
            if (!ok || n == 0) break;
            emit ctx->self->output(QByteArray(buf, n));
        }
        delete ctx;
        return 0;
    }
};

namespace {
PFN_CreatePseudoConsole pCreate = nullptr;
PFN_ResizePseudoConsole pResize = nullptr;
PFN_ClosePseudoConsole pClose = nullptr;
bool loadApi() {
    if (pCreate) return true;
    // 優先載入修正版 conpty.dll（herdr 同款，不吞 escape sequences）；
    // 沒有才退回系統 kernel32 的 ConPTY。
    HMODULE k = nullptr;
    wchar_t dllPath[MAX_PATH] = {};
    GetModuleFileNameW(nullptr, dllPath, MAX_PATH);
    std::wstring p(dllPath);
    size_t slash = p.find_last_of(L"\\/");
    if (slash != std::wstring::npos) p = p.substr(0, slash);
    p += L"\\conpty\\conpty.dll";
    k = LoadLibraryW(p.c_str());
    if (!k) k = GetModuleHandleW(L"kernel32.dll");
    pCreate = (PFN_CreatePseudoConsole)GetProcAddress(k, "CreatePseudoConsole");
    pResize = (PFN_ResizePseudoConsole)GetProcAddress(k, "ResizePseudoConsole");
    pClose = (PFN_ClosePseudoConsole)GetProcAddress(k, "ClosePseudoConsole");
    return pCreate && pResize && pClose;
}
QString toWide(const QString &s) { return s; }

}

ConPty::ConPty(QObject *parent) : QObject(parent), d(new Private) {}
ConPty::~ConPty() { kill(); delete d; }

bool ConPty::start(const QString &program, const QStringList &args,
                   const QString &cwd, int cols, int rows) {
    if (!loadApi()) { qWarning() << "ConPTY API unavailable"; return false; }
    d->cols = cols; d->rows = rows;

    HANDLE inRead, inWrite, outRead, outWrite;
    SECURITY_ATTRIBUTES sa = {}; sa.nLength = sizeof(sa); sa.bInheritHandle = TRUE;
    if (!CreatePipe(&inRead, &inWrite, &sa, 0)) return false;
    if (!CreatePipe(&outRead, &outWrite, &sa, 0)) { CloseHandle(inRead); CloseHandle(inWrite); return false; }

    HPCON hpc = nullptr;
    COORD size = {(short)cols, (short)rows};
    HRESULT hr = pCreate(size, inRead, outWrite, 0, &hpc);
    if (FAILED(hr)) {
        qWarning() << "CreatePseudoConsole failed" << QString::number((int)hr, 16);
        CloseHandle(inRead); CloseHandle(inWrite); CloseHandle(outRead); CloseHandle(outWrite);
        return false;
    }
    d->hpc = hpc;

    SIZE_T attrSize = 0;
    InitializeProcThreadAttributeList(nullptr, 1, 0, &attrSize);
    auto attrs = (PPROC_THREAD_ATTRIBUTE_LIST)HeapAlloc(GetProcessHeap(), 0, attrSize);
    InitializeProcThreadAttributeList(attrs, 1, 0, &attrSize);
    UpdateProcThreadAttribute(attrs, 0, PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
                              hpc, sizeof(hpc), nullptr, nullptr);

    STARTUPINFOEXW si = {};
    si.lpAttributeList = attrs;
    si.StartupInfo.cb = sizeof(si);
    si.StartupInfo.dwFlags = STARTF_USESTDHANDLES;
    si.StartupInfo.hStdInput = INVALID_HANDLE_VALUE;
    si.StartupInfo.hStdOutput = INVALID_HANDLE_VALUE;
    si.StartupInfo.hStdError = INVALID_HANDLE_VALUE;

    // 組 command line：依 Windows 規則為含空白/引號的參數加上雙引號並轉義，
    // 否則 PowerShell 的 -Command "& 'python' 'cool.py'" 會被拆壞。
    auto quoteArg = [](const QString &a) -> QString {
        if (!a.isEmpty() && !a.contains(QChar(' ')) && !a.contains(QChar('\t'))
            && !a.contains(QChar('"')) && !a.contains(QChar('\'')))
            return a;
        QString q = QStringLiteral("\"");
        int backslashes = 0;
        for (int i = 0; i < a.size(); ++i) {
            QChar c = a.at(i);
            if (c == QChar('\\')) { ++backslashes; continue; }
            if (c == QChar('"')) {
                q += QString(backslashes * 2 + 1, QChar('\\'));
                q += QChar('"');
                backslashes = 0;
            } else {
                q += QString(backslashes, QChar('\\'));
                q += c;
                backslashes = 0;
            }
        }
        q += QString(backslashes * 2, QChar('\\'));
        q += QChar('"');
        return q;
    };
    QString cmdline = quoteArg(program);
    const bool isCmd = QFileInfo(program).fileName().compare(QStringLiteral("cmd.exe"), Qt::CaseInsensitive) == 0;
    if (isCmd && args.size() == 2 && (args[0].compare(QStringLiteral("/k"), Qt::CaseInsensitive) == 0
                                      || args[0].compare(QStringLiteral("/c"), Qt::CaseInsensitive) == 0)) {
        // cmd 的規則：/k 後面若以雙引號開頭，會去掉最前與最後一個引號，其餘原樣執行；
        // 所以內層的引號不能用 \" 轉義（cmd 不認得，會變成 '\"python.exe\"' 找不到命令）。
        cmdline += QChar(' ') + args[0] + QStringLiteral(" \"") + args[1] + QStringLiteral("\"");
    } else {
        for (const QString &a : args) cmdline += QChar(' ') + quoteArg(a);
    }
    std::wstring wcmd = cmdline.toStdWString();
    std::wstring wcwd = cwd.isEmpty() ? std::wstring() : cwd.toStdWString();

    PROCESS_INFORMATION pi = {};
    BOOL ok = CreateProcessW(nullptr, (LPWSTR)wcmd.c_str(), nullptr, nullptr, FALSE,
                             EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT,
                             nullptr, wcwd.empty() ? nullptr : (LPWSTR)wcwd.c_str(),
                             &si.StartupInfo, &pi);
    DeleteProcThreadAttributeList(attrs);
    HeapFree(GetProcessHeap(), 0, attrs);
    CloseHandle(inRead);   // console 持有
    CloseHandle(outWrite); // console 持有
    if (!ok) {
        qWarning() << "CreateProcess failed" << GetLastError();
        pClose(hpc); d->hpc = nullptr;
        CloseHandle(inWrite); CloseHandle(outRead);
        return false;
    }
    d->inWrite = inWrite;
    d->outRead = outRead;
    d->hProcess = pi.hProcess;
    d->hThread = pi.hThread;
    d->running = true;
    d->hStop = CreateEventW(nullptr, TRUE, FALSE, nullptr);

    auto *ctx = new Private::ReaderCtx{this, d};
    d->hReader = CreateThread(nullptr, 0, Private::reader, ctx, 0, nullptr);
    return true;
}

void ConPty::writeInput(const QByteArray &data) {
    QMutexLocker l(&d->mutex);
    if (d->inWrite == INVALID_HANDLE_VALUE || data.isEmpty()) return;
    DWORD written = 0;
    WriteFile(d->inWrite, data.constData(), data.size(), &written, nullptr);
}

void ConPty::resize(int cols, int rows) {
    QMutexLocker l(&d->mutex);
    if (d->hpc && pResize) pResize(d->hpc, COORD{(short)cols, (short)rows});
    d->cols = cols; d->rows = rows;
}

void ConPty::kill() {
    QMutexLocker l(&d->mutex);
    if (!d->running && d->hpc == nullptr) return;
    d->running = false;
    if (d->hStop != INVALID_HANDLE_VALUE) SetEvent(d->hStop);
    if (d->hProcess != INVALID_HANDLE_VALUE) {
        TerminateProcess(d->hProcess, 1);
        CloseHandle(d->hProcess); d->hProcess = INVALID_HANDLE_VALUE;
    }
    if (d->hThread != INVALID_HANDLE_VALUE) { CloseHandle(d->hThread); d->hThread = INVALID_HANDLE_VALUE; }
    if (d->inWrite != INVALID_HANDLE_VALUE) { CloseHandle(d->inWrite); d->inWrite = INVALID_HANDLE_VALUE; }
    if (d->hpc) { pClose(d->hpc); d->hpc = nullptr; }
    if (d->outRead != INVALID_HANDLE_VALUE) { CloseHandle(d->outRead); d->outRead = INVALID_HANDLE_VALUE; }
    if (d->hReader != INVALID_HANDLE_VALUE) { CloseHandle(d->hReader); d->hReader = INVALID_HANDLE_VALUE; }
    if (d->hStop != INVALID_HANDLE_VALUE) { CloseHandle(d->hStop); d->hStop = INVALID_HANDLE_VALUE; }
}

bool ConPty::running() const { return d->running; }

#else
struct ConPty::Private {};
ConPty::ConPty(QObject *p):QObject(p),d(new Private){}
ConPty::~ConPty(){delete d;}
bool ConPty::start(const QString&,const QStringList&,const QString&,int,int){return false;}
void ConPty::writeInput(const QByteArray&){}
void ConPty::resize(int,int){}
void ConPty::kill(){}
bool ConPty::running() const {return false;}
#endif
