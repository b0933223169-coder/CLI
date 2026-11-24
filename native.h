#pragma once
// 原生核心：取代原本呼叫 Python 的部分（DPAPI 加密、Cookie 檔、報表解析、CLI 密碼相容）。
#include <QString>
#include <QStringList>
#include <QList>
#include <QByteArray>
#include <QVariantMap>
#include <QJsonObject>

namespace Native {

struct Cookie {
    QString name, value, domain, path = QStringLiteral("/");
    bool secure = false, httpOnly = false;
    double expires = -1;            // epoch 秒；<=0 代表工作階段 Cookie
};

// ---- Windows DPAPI（與 Electron safeStorage 同一類保護：只有目前 Windows 使用者能解密）----
QString protectString(const QString &plain);                       // → base64
bool unprotectString(const QString &b64, QString *plain);

// ---- Cookie ----
QList<Cookie> parseNetscape(const QString &text);
QString serializeNetscape(const QList<Cookie> &cookies, const QString &header = QString());
QList<Cookie> coolCookies(const QList<Cookie> &all);
bool hasUsableMoodleSession(const QList<Cookie> &cookies);
QString cookieHeader(const QList<Cookie> &cookies);
QString emailCookieName(const QString &email);                     // base64url(email).left(48)+".txt"

// ---- Cool English 網站判斷 ----
bool isCoolUrl(const QString &url);
bool isGoogleAccountsUrl(const QString &url);
bool isGoogleRecaptchaUrl(const QString &url);
bool isGoogleOAuthProviderHref(const QString &href);
bool isAuthenticatedDashboard(const QString &url, int status, const QString &html);
QString classifyTimeReport(const QString &url, int status, const QString &html);   // valid/expired/unknown

struct ReportRow { QString month; int platform = 0, video = 0, practice = 0; };
QList<ReportRow> parseTimeReport(const QString &html);
int durationMinutes(const QString &text);
QString detectUserId(const QString &html);

// ---- CLI（Python）相容 ----
QStringList cliMachineIds();
bool decryptCliPassword(const QString &enc, int length, QString *out);
QString encryptCliPassword(const QString &plain);                  // 讓 CLI 也能讀

// ---- 網路紀錄用 ----
QString redactUrl(const QString &raw);
QJsonObject redactHeaders(const QJsonObject &h);
QString humanSize(qint64 bytes);

// ---- 檔案 ----
bool atomicWrite(const QString &path, const QByteArray &data);
QString sha256Hex(const QByteArray &b);

} // namespace Native
