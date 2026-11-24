import QtQuick
import Cool 1.0
import "../../components"

Column {
    id: page
    signal notify(string text)
    width: parent ? parent.width : 0
    spacing: M3.gap

    property bool confirmWipe: false
    property bool confirmCookies: false

    // 長路徑在設定列放不下，改成 ~/ 相對顯示（完整路徑可用「複製路徑」取得）。
    function shortDataDir() {
        var dir = String(Backend.dataDir)
        var home = String(Backend.homeDir)
        if (home && dir.indexOf(home) === 0) dir = "~" + dir.slice(home.length)
        return dir + "  ·  cookies/  ·  exports/"
    }

    // 加密與保存
    Card {
        width: parent.width
        height: b1.height + 44
        Column {
            id: b1
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "ENCRYPTION"
                title: "加密與登入資料"
                desc: "密碼以系統帳戶金鑰加密；Cookie 只存在使用者資料夾"
            }

            Pref {
                width: parent.width
                title: "密碼加密保存"
                desc: "使用 DPAPI，只有這台裝置的 Windows 帳戶能解密"
                icon: "enhanced_encryption"
                Chip {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "已啟用"; icon: "lock"
                    tone: M3.c.successContainer
                    onTone: M3.c.success
                }
            }
            Pref {
                width: parent.width
                title: "Cookie 保存位置"
                desc: "個人資料夾，不會放進程式庫或 Git"
                icon: "cookie"
                Chip {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "本機"; icon: "folder"
                    tone: M3.c.successContainer
                    onTone: M3.c.success
                }
            }
            Pref {
                width: parent.width
                title: "自動鎖定"
                desc: "閒置一段時間後隱藏敏感資料"
                icon: "lock_clock"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.autoLock === true
                    onToggled: function (v) { Backend.updateSetting("autoLock", v) }
                }
            }
            Pref {
                width: parent.width
                title: "鎖定時間"
                desc: "閒置幾分鐘後鎖定"
                icon: "timer"
                Slider {
                    width: 240; anchors.verticalCenter: parent.verticalCenter
                    from: 1; to: 60; step: 1; suffix: " 分"
                    value: Backend.settings.lockMinutes ? Backend.settings.lockMinutes : 15
                    onMoved: function (v) { Backend.updateSetting("lockMinutes", Math.round(v)) }
                }
            }
            Pref {
                width: parent.width
                title: "遮蔽敏感資料"
                desc: "帳號列表與工作台的 Email 以 •••• 顯示"
                icon: "visibility_off"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.maskSensitive !== false
                    onToggled: function (v) { Backend.updateSetting("maskSensitive", v) }
                }
            }
        }
    }

    // 資料管理
    Card {
        width: parent.width
        height: b2.height + 44
        Column {
            id: b2
            x: 22; y: 22; width: parent.width - 44; spacing: 12

            SectionTitle {
                width: parent.width
                eyebrow: "DATA"
                title: "資料管理"
                desc: "匯出、清除或完全刪除本機資料"
            }

            Row {
                width: parent.width; spacing: 10
                Btn {
                    text: "匯出所有資料"; icon: "download"; kind: "tonal"; small: true
                    onClicked: Backend.exportData()
                }
                Btn {
                    text: "備份設定"; icon: "save"; kind: "outlined"; small: true
                    onClicked: Backend.backupSettings()
                }
                FillSpacer {}
                Btn {
                    text: "刪除全部資料"; icon: "delete_forever"; kind: "filled"; small: true; danger: true
                    onClicked: page.confirmWipe = true
                }
            }

            Rectangle {
                visible: page.confirmWipe
                width: parent.width; height: 58; radius: M3.rMd
                color: M3.c.errorContainer
                Row {
                    x: 16; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                    Icon { anchors.verticalCenter: parent.verticalCenter; name: "warning"; size: 18; fill: 1; color: M3.c.onErrorContainer }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "這會刪除 " + Backend.accounts.length + " 個帳號、" + Backend.courses.length + " 個課程與所有網路紀錄。"
                        color: M3.c.onErrorContainer; font.pixelSize: M3.tLabel
                    }
                }
                Row {
                    anchors.right: parent.right; anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6
                    Btn { text: "取消"; kind: "text"; small: true; onClicked: page.confirmWipe = false }
                    Btn {
                        text: "確定刪除"; icon: "delete_forever"; danger: true; small: true
                        onClicked: { Backend.wipeAll(); page.confirmWipe = false }
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: M3.alpha(M3.c.outlineVariant, 0.5) }

            Item {
                width: parent.width; height: 34
                Text { anchors.verticalCenter: parent.verticalCenter; text: "Cookie 與登入狀態"; color: M3.c.onSurface; font.pixelSize: M3.tLabel }
                Row {
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6
                    Btn {
                        text: "重新檢查全部"; icon: "sync"; kind: "text"; small: true
                        onClicked: Backend.refresh()
                    }
                    Btn {
                        text: "清除 Cookie"; icon: "cookie"; kind: "outlined"; small: true; danger: true
                        onClicked: page.confirmCookies = true
                    }
                }
            }
            Row {
                visible: page.confirmCookies
                spacing: 8
                Text { anchors.verticalCenter: parent.verticalCenter; text: "清除後所有帳號都需要重新登入。"; color: M3.c.error; font.pixelSize: M3.tMicro }
                Btn { text: "取消"; kind: "text"; small: true; onClicked: page.confirmCookies = false }
                Btn {
                    text: "確認清除"; icon: "cookie"; danger: true; small: true
                    onClicked: { Backend.clearCookies(); page.confirmCookies = false }
                }
            }

            Item {
                width: parent.width; height: 34
                Text { anchors.verticalCenter: parent.verticalCenter; text: "暫存與快取"; color: M3.c.onSurface; font.pixelSize: M3.tLabel }
                Row {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    spacing: 6
                    Text { anchors.verticalCenter: parent.verticalCenter; text: Backend.cacheSize; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                    Btn {
                        text: "清除暫存"; icon: "cleaning_services"; kind: "text"; small: true
                        onClicked: Backend.clearCache()
                    }
                }
            }
        }
    }

    // 連線與隱私
    Card {
        width: parent.width
        height: b3.height + 44
        Column {
            id: b3
            x: 22; y: 22; width: parent.width - 44; spacing: 4

            SectionTitle {
                width: parent.width
                eyebrow: "PRIVACY"
                title: "連線與隱私"
                desc: "本機不收集任何遙測資料"
            }

            Pref {
                width: parent.width
                title: "只在需要時連線"
                desc: "只有更新報表或登入時才會連到 Cool English"
                icon: "wifi_tethering"
                Chip {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "隨選連線"; icon: "bolt"
                    tone: M3.c.secondaryContainer
                    onTone: M3.c.onSecondaryContainer
                }
            }
            Pref {
                width: parent.width
                title: "使用系統代理"
                desc: "沿用 Windows 的 Proxy 設定"
                icon: "vpn_lock"
                Toggle {
                    anchors.verticalCenter: parent.verticalCenter
                    checked: Backend.settings.systemProxy === true
                    onToggled: function (v) { Backend.updateSetting("systemProxy", v) }
                }
            }
            Pref {
                width: parent.width
                title: "匿名使用統計"
                desc: "固定關閉，也不會預設開啟"
                icon: "analytics"
                Chip {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "已關閉"; icon: "block"
                    tone: M3.c.surfaceContainerHighest
                    onTone: M3.c.onSurfaceVariant
                }
            }
            Pref {
                width: parent.width
                title: "資料存放位置"
                desc: page.shortDataDir()
                icon: "folder"
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "複製路徑"; icon: "content_copy"; kind: "text"; small: true
                    onClicked: Backend.copyText(Backend.dataDir)
                }
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "開啟資料夾"; icon: "folder_open"; kind: "text"; small: true
                    onClicked: Backend.openFolder()
                }
            }
        }
    }

    // 關於
    Rectangle {
        width: parent.width; height: 96
        radius: M3.rLg
        color: M3.alpha(M3.c.surfaceContainerHigh, 0.6)
        border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)
        Row {
            x: 20; anchors.verticalCenter: parent.verticalCenter; spacing: 12
            Rectangle {
                width: 42; height: 42; radius: 14; color: M3.c.primaryContainer
                Icon { anchors.centerIn: parent; name: "bolt"; size: 22; fill: 1; color: M3.c.onPrimaryContainer }
            }
            Column {
                anchors.verticalCenter: parent.verticalCenter; spacing: 2
                Text { text: "cool · 學習工作台"; color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.Medium }
                Text { text: "PySide6 + Qt Quick · Material 3 · 版本 0.4.0"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
            }
        }
        Text {
            anchors.right: parent.right; anchors.rightMargin: 20
            anchors.verticalCenter: parent.verticalCenter
            text: "原始原型：Cool Desktop（Electron）"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
        }
    }
}
