#pragma once
#include <QObject>
#include <QVariant>
#include <QJsonArray>
#include <QMap>
#include <QPair>
#include <QStringList>
#include <QSet>
#include <QHash>
#include <functional>
#include "native.h"

class QProcess;
class QTimer;
class QEvent;
class QmlPtyBridge;
class QQmlWebChannel;
struct CliJob;
class QFileSystemWatcher;
class QNetworkAccessManager;
class QFile;

// 一個終端分頁 = 一組獨立的 ConPTY + WebChannel 橋 + WebChannel
struct TermSession {
    int id = 0;
    QString profile;
    QString label;
    QStringList argv;
    QString boot;
    QmlPtyBridge *bridge = nullptr;
    QQmlWebChannel *channel = nullptr;
};

// 提供 xterm 頁面讀取的終端設定（配色 / 字型）與剪貼簿存取
class TermConfig : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QString json READ json NOTIFY changed)
public:
    explicit TermConfig(QObject *p = nullptr) : QObject(p) {}
    QString json() const { return m_json; }
    void setJson(const QString &j) { if (j == m_json) return; m_json = j; emit changed(); }
    Q_INVOKABLE void copyText(const QString &t);
    Q_INVOKABLE QString pasteText();
signals:
    void changed();
private:
    QString m_json;
};

class Backend : public QObject
{
    Q_OBJECT
    Q_PROPERTY(int activeTerminalId READ activeTerminalId NOTIFY terminalTabsChanged)
    Q_PROPERTY(QVariantList terminalTabs READ terminalTabs NOTIFY terminalTabsChanged)
    Q_PROPERTY(int terminalCount READ terminalCount NOTIFY terminalTabsChanged)
    Q_PROPERTY(QString terminalText READ terminalText)
    Q_PROPERTY(QString terminalStatus READ terminalStatus)
    Q_PROPERTY(bool terminalRunning READ terminalRunning)
    Q_PROPERTY(QString terminalProfile READ terminalProfile)
    Q_PROPERTY(QVariantList terminalProfiles READ terminalProfiles NOTIFY terminalProfilesChanged)
    Q_PROPERTY(QVariantList terminalHistory READ terminalHistory)
    Q_PROPERTY(QString coolScript READ coolScript)
    Q_PROPERTY(QString dataDir READ dataDir)
    Q_PROPERTY(QString exportDir READ exportDir)
    Q_PROPERTY(QString homeDir READ homeDir)
    Q_PROPERTY(QString defaultTerminal READ defaultTerminal)
    Q_PROPERTY(QString defaultTerminalProfile READ defaultTerminalProfile)
    Q_PROPERTY(bool loginBusy READ loginBusy)
    Q_PROPERTY(QString loginStatus READ loginStatus)
    Q_PROPERTY(QString loginMode READ loginMode)
    Q_PROPERTY(QVariantMap colors READ colors NOTIFY colorsChanged)
    Q_PROPERTY(QString seed READ seed NOTIFY schemeChanged)
    Q_PROPERTY(QString variant READ variant NOTIFY schemeChanged)
    Q_PROPERTY(bool dark READ dark NOTIFY schemeChanged)
    Q_PROPERTY(qreal contrast READ contrast NOTIFY schemeChanged)
    Q_PROPERTY(QVariantList variants READ variants)
    Q_PROPERTY(QVariantList seeds READ seeds)
    Q_PROPERTY(QVariantList themes READ themes)
    Q_PROPERTY(QVariantList cliStyles READ cliStyles)
    Q_PROPERTY(QVariantList cliFields READ cliFields)
    Q_PROPERTY(QString debugSection READ debugSection)
    Q_PROPERTY(QString cliInfo READ cliInfo NOTIFY debugSectionChanged)
    Q_PROPERTY(bool trayAvailable READ trayAvailable)
    Q_PROPERTY(QString colorsFile READ colorsFile)
    Q_PROPERTY(QVariantMap settings READ settings NOTIFY settingsChanged)
    Q_PROPERTY(QString settingsFile READ settingsFile)
    Q_PROPERTY(QString encryptionStatus READ encryptionStatus)
    Q_PROPERTY(QVariantList accounts READ accounts NOTIFY accountsChanged)
    Q_PROPERTY(QVariantList courses READ courses NOTIFY coursesChanged)
    Q_PROPERTY(QVariantList reports READ reports NOTIFY reportsChanged)
    Q_PROPERTY(bool reportBusy READ reportBusy)
    Q_PROPERTY(QString reportError READ reportError)
    Q_PROPERTY(QString reportUpdated READ reportUpdated)
    Q_PROPERTY(QString reportSource READ reportSource)
    Q_PROPERTY(QVariantList sessions READ sessions NOTIFY sessionsChanged)
    Q_PROPERTY(QString networkSize READ networkSize)
    Q_PROPERTY(int selected READ selected NOTIFY selectedChanged)
    Q_PROPERTY(QString cacheSize READ cacheSize)
    Q_PROPERTY(QString cliDir READ cliDir CONSTANT)

public:
    explicit Backend(QObject *parent = nullptr);
    ~Backend() override;
    // QML 用 activeTerminalId 取得該分頁專屬的 WebChannel
    Q_INVOKABLE QObject *terminalChannel(int sid);
    int activeTerminalId() const;
    QVariantList terminalTabs() const;
    int terminalCount() const;
    QString terminalText() const;
    QString terminalStatus() const;
    bool terminalRunning() const;
    QString terminalProfile() const;
    QVariantList terminalProfiles() const;
    QVariantList terminalHistory() const;
    QString coolScript() const;
    QString dataDir() const;
    QString exportDir() const;
    QString homeDir() const;
    QString defaultTerminal() const;
    QString defaultTerminalProfile() const;
    bool loginBusy() const;
    QString loginStatus() const;
    QString loginMode() const;
    QVariantMap colors() const;
    QString seed() const;
    QString variant() const;
    bool dark() const;
    qreal contrast() const;
    QVariantList variants() const;
    QVariantList seeds() const;
    QVariantList themes() const;
    QVariantList cliStyles() const;
    QVariantList cliFields() const;
    QString debugSection() const;
    QString cliInfo() const;
    bool trayAvailable() const;
    QString colorsFile() const;
    QVariantMap settings() const;
    QString settingsFile() const;
    QString encryptionStatus() const;
    QVariantList accounts() const;
    QVariantList courses() const;
    QVariantList reports() const;
    bool reportBusy() const;
    QString reportError() const;
    QString reportUpdated() const;
    QString reportSource() const;
    QVariantList sessions() const;
    QString networkSize() const;
    int selected() const;
    QString cacheSize() const;
    QString cliDir() const;

signals:
    void accountsChanged();
    void sessionOpened(const QString &sid, bool live);
    void active();
    void activeTerminalIdChanged();
    void avatarChecked();
    void cacheChanged();
    void cacheSizeChanged();
    void cliFieldsChanged();
    void cliStylesChanged();
    void colorsChanged();
    void colorsFileChanged();
    void contrastChanged();
    void cookieChecked();
    void coolScriptChanged();
    void coursesChanged();
    void darkChanged();
    void dataDirChanged();
    void debugSectionChanged();
    void defaultTerminalChanged();
    void defaultTerminalProfileChanged();
    void encryptionStatusChanged();
    void exportDirChanged();
    void homeDirChanged();
    void lockRequested(int v);
    void loginBusyChanged();
    void loginChanged();
    void loginModeChanged();
    void loginStatusChanged();
    void networkSizeChanged();
    void reportBusyChanged();
    void reportDone(const QVariant &v);
    void reportErrorChanged();
    void reportSourceChanged();
    void reportStateChanged();
    void reportUpdatedChanged();
    void reportsChanged();
    void schemeChanged();
    void seedChanged();
    void seedsChanged();
    void selectedChanged();
    void sessionIdChanged();
    void sessionsChanged();
    void settingsChanged();
    void settingsFileChanged();
    void terminalChanged();
    void terminalCountChanged();
    void terminalHistoryChanged();
    void terminalProfileChanged();
    void terminalProfilesChanged();
    void terminalRequested();
    void terminalRunningChanged();
    void terminalStatusChanged();
    void terminalTabsChanged();
    void terminalTextChanged();
    void themesChanged();
    void toast(const QString &msg);
    void trayAvailableChanged();
    void variantChanged();
    void variantsChanged();

public slots:
    void refresh();
    void toggleCursor();
    QString selectionText();
    void refreshAvatar(const QVariant &a0);
    void refreshAvatarFromChrome(const QVariant &a0);
    void setAvatarFromFile(const QVariant &a0, const QVariant &a1);
    void clearAvatar(const QVariant &a0);
    void startTerminal(const QVariant &a0);
    void launchTerminal(const QVariant &a0);
    void selectTerminalTab(const QVariant &a0);
    void closeTerminalTab(const QVariant &a0);
    void writeTerminal(const QVariant &a0);
    void pasteTerminal(const QVariant &a0);
    void copyTerminalSelection(const QVariant &a0);
    void stopTerminal();
    void shutdownTerminal();
    void restartTerminal();
    void clearTerminal();
    void startLogin(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3);
    void loginAccount(const QVariant &a0, const QVariant &a1);
    void loginSelected(const QVariant &a0);
    void clearLoginStatus();
    void clearTerminalHistory();
    void setScheme(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3);
    QString seedFromImage(const QVariant &a0);
    QVariantList preview(const QVariant &a0, const QVariant &a1, const QVariant &a2);
    void resetIdle();
    bool hasUnlockPassword();
    bool verifyUnlock(const QVariant &a0);
    void updateSetting(const QVariant &a0, const QVariant &a1);
    void applyTheme(const QVariant &a0, const QVariant &a1, const QVariant &a2);
    void saveWindowGeometry(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3);
    void select(const QVariant &a0);
    void refreshReports();
    void addAccount(const QVariant &a0, const QVariant &a1, const QVariant &a2, const QVariant &a3);
    void renameAccount(const QVariant &a0, const QVariant &a1);
    void removeAccount(const QVariant &a0);
    void removeAllAccounts();
    void checkCookie(const QVariant &a0);
    void addCourse(const QVariant &a0, const QVariant &a1, const QVariant &a2);
    void removeCourse(const QVariant &a0);
    void setCourseCategory(const QVariant &a0, const QVariant &a1);
    void removeCategory(const QVariant &a0);
    void renameCategory(const QVariant &a0, const QVariant &a1);
    void openCourseMenu();
    void openReportCli();
    void copyText(const QVariant &a0);
    void openUrl(const QVariant &a0);
    void openFolder(const QVariant &a0);
    void exportReport(const QVariant &a0);
    void exportSessions();
    void exportSession(const QVariant &a0);
    void stopSession(const QVariant &a0);
    void deleteSession(const QVariant &a0);
    void deleteSessions(const QVariant &a0);
    void clearSessions();
    void clearCookies();
    void exportData();
    void backupSettings();
    void clearCache();
    void wipeAll();
    void openCourses(const QVariant &a0, const QVariant &a1, const QVariant &a2);
    void openAlias(const QVariant &a0, const QVariant &a1);
    QVariantList sessionEvents(const QVariant &a0, const QVariant &a1, const QVariant &a2);
    QString sessionRaw(const QVariant &a0, const QVariant &a1);
    void quitApp();
    QVariantMap cliStyle(const QVariant &a0);
    QString ansiToHtml(const QVariant &a0);

protected:
    bool eventFilter(QObject *obj, QEvent *event) override;
private slots:
    void onIdleTimeout();

private:
    QTimer *m_idleTimer = nullptr;
    void syncIdle();
    void buildColors();
    void buildPresets();
    void reloadAccounts();
    void reloadReports();
    void reloadSessions();
    void reloadCourses();
    void saveSettings();
    void saveRaw(const QJsonArray &arr);
    void saveCourses();
    void saveSessionsJson();
    void courseChanged();
    void noteCourseOpen(const QString &url);
    bool startTerminalWithArgs(const QString &profileId, const QStringList &args,
                               const QString &label = QString());
    void detectTerminalProfiles();
    // 回傳 profile 的 argv + 開機寫入 PTY 的字串
    QPair<QStringList, QString> terminalCommand(const QString &profileId,
                                                const QStringList &extra);
    QString consolePython() const;
    QString projectRoot() const;
    // ---- 原生實作（backend_native.inc）----
    QList<Native::Cookie> loadCookies(const QString &email);
    bool saveLogin(const QString &email, const QString &displayName, const QList<Native::Cookie> &cookies,
                   const QString &userId, QString *err);
    void setCookieStatus(const QString &email, const QString &status);
    bool historyEnabled() const;
    QString createSession(const QString &mode, const QString &label, const QString &account, const QString &forcedId = QString());
    int sessionIndex(const QString &sid) const;
    void recordEvent(const QString &sid, const QVariantMap &ev);
    void finishSession(const QString &sid, const QString &status, const QString &note);
    void markSessionsDirty();
    void flushSessions();
    void removeSessionFiles(const QString &sid);
    void applyRetention();
    void initCliSync();
    void onCliChanged();
    bool syncFromCli();
    void syncToCli();
    void removeCliAccount(const QString &email);
    bool syncCliColors(bool initial);
    void writeCliColors();
    QString defaultCliColor(const QString &key) const;
    void applyDefaults();
    void pushTermConfig();
    void applyFontFamily();
    int cliAccountIndex(const QString &email) const;
    int cliAccountCount() const;
    QString runCli(const QStringList &args, const QString &kind, const QString &mode, const QString &label,
                   const QString &email, const QList<QPair<QString, QString>> &rules,
                   std::function<void(int, const QString &)> done);
    void onCliOutput(const QString &sid);
    void handleCliLine(CliJob *j, const QString &line);
    void runReportCli(const QString &email, const QString &label, bool store);
    void openGroups(const QStringList &labels, const QString &mode, const QString &label);
    QStringList groupLabels(const QStringList &urls) const;
    QHash<QString, CliJob *> m_cliJobs;
    TermConfig *m_termCfg = nullptr;
    QFileSystemWatcher *m_cliWatch = nullptr;
    QTimer *m_syncTimer = nullptr;
    QTimer *m_sessionsTimer = nullptr;
    QTimer *m_retainTimer = nullptr;
    QNetworkAccessManager *m_nam = nullptr;
    QHash<QString, QFile *> m_logs;
    int m_bodySeq = 0;
    QString m_urlsPath;
    QByteArray m_selfWriteUrls, m_lastUrlsSeen;
    QString m_pendingLoginMode;
    QMap<int, TermSession> m_termSessions;
    QMap<int, QProcess *> m_termProcs;
    int m_termSeq = 0;
    QVariantMap m_settings;
    QVariantMap m_colors;
    QVariantList m_accounts;
    QVariantList m_reports;
    QVariantList m_sessions;
    QVariantList m_courses;
    QVariantList m_variants;
    QVariantList m_seeds;
    QVariantList m_themes;
    QVariantList m_terminalProfiles;
    QVariantList m_cliStyles;
    QVariantList m_cliFields;
    QVariantList m_preview;
    QString m_previewKey;
    QString m_seed;
    QString m_variant;
    bool m_dark = true;
    qreal m_contrast = 0.0;
    int m_selected = 0;
    QString m_networkSize;
    QString m_reportSource;
    QString m_reportUpdated;
    QString m_reportError;
    bool m_reportBusy = false;
    // 終端狀態
    int m_termActive = 0;
    QVariantList m_termTabs;
    QString m_termText;
    QString m_termStatus;
    bool m_termRunning = false;
    QString m_termProfile;
    QVariantList m_termHistory;
    // 登入狀態
    bool m_loginBusy = false;
    QString m_loginStatus;
};
