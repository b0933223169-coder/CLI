import QtQuick
import QtQuick.Window
import Cool 1.0
import "../components"

Item {
    id: root
    signal navigate(int page)
    signal notify(string text)

    property string section: Backend.debugSection

    Connections {
        target: Window.window
        function onSettingsSectionChanged() {
            if (Window.window.settingsSection !== undefined && Window.window.settingsSection !== "")
                root.section = Window.window.settingsSection
        }
    }
    Component.onCompleted: {
        if (Window.window && Window.window.settingsSection !== undefined && Window.window.settingsSection !== "")
            root.section = Window.window.settingsSection
    }

    readonly property var cats: [
        { id: "appearance", name: "外觀", icon: "palette", desc: "24 組主題、種子色、介面字級與對比", meta: "主題庫 · 變體 · 字級", file: "Appearance.qml" },
        { id: "terminal", name: "終端機", icon: "terminal", desc: "預覽字型、游標與背景色（配色同步 CLI）", meta: "字級 · 配色 · 同步", file: "Terminal.qml" },
        { id: "workspace", name: "工作區", icon: "space_dashboard", desc: "側邊欄行為、啟動頁面與預設登入模式", meta: "導覽 · 啟動 · 視窗", file: "Workspace.qml" },
        { id: "reports", name: "報表", icon: "monitoring", desc: "學習門檻、警示色與自動更新", meta: "門檻 · 匯出 · 更新", file: "ReportSettings.qml" },
        { id: "cli", name: "CLI 報表配色", icon: "format_color_text", desc: "終端機報表的 ANSI 樣式（與 cool -c 雙向同步）", meta: "7 個欄位 · 37 種樣式 · 自訂 HEX", file: "CliColors.qml" },
        { id: "network", name: "網路紀錄", icon: "lan", desc: "永久保留／自動刪除／停用、原始本文與容量", meta: "保留 · 擷取 · 清除", file: "NetworkHistory.qml" },
        { id: "privacy", name: "隱私與安全", icon: "shield", desc: "加密保存、自動鎖定與資料清除", meta: "DPAPI · Cookie · 匯出", file: "Privacy.qml" }
    ]
    property bool sorting: false
    readonly property var orderedCats: {
        var order = Backend.settings.settingsOrder || [], out = [], seen = {}
        for (var i = 0; i < order.length; i++)
            for (var j = 0; j < cats.length; j++)
                if (cats[j].id === order[i] && !seen[cats[j].id]) { out.push(cats[j]); seen[cats[j].id] = 1 }
        for (var k = 0; k < cats.length; k++) if (!seen[cats[k].id]) out.push(cats[k])
        return out
    }
    function moveCat(id, dir) {
        var ids = []
        for (var i = 0; i < orderedCats.length; i++) ids.push(orderedCats[i].id)
        var a = ids.indexOf(id), b = a + dir
        if (a < 0 || b < 0 || b >= ids.length) return
        var t = ids[a]; ids[a] = ids[b]; ids[b] = t
        Backend.updateSetting("settingsOrder", ids)
    }
    function catById(id) {
        for (var i = 0; i < cats.length; i++) if (cats[i].id === id) return cats[i]
        return cats[0]
    }
    function open(id) { section = id; landingFlick.contentY = 0 }
    function back() { section = "" }

    // ── 設定首頁 ──
    Flickable {
        id: landingFlick
        anchors.fill: parent
        visible: root.section === ""
        clip: true
        contentHeight: landingCol.height + 48
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: landingCol
            x: 28; y: 6; width: landingFlick.width - 56; spacing: 14

            // 目前主題
            Rectangle {
                width: parent.width; height: 168
                radius: M3.rXl
                color: M3.c.surfaceContainer
                clip: true

                Rectangle {
                    anchors.fill: parent; radius: parent.radius
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0; color: M3.c.primaryContainer }
                        GradientStop { position: 0.5; color: M3.alpha(M3.c.primaryContainer, 0.55) }
                        GradientStop { position: 1; color: M3.alpha(M3.c.tertiaryContainer, 0.75) }
                    }
                }
                Row {
                    x: 26; y: 24; spacing: 18
                    Column {
                        spacing: 4
                        Text { text: "目前主題"; color: M3.alpha(M3.c.onPrimaryContainer, 0.82); font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.4 }
                        Text {
                            text: {
                                var t = Backend.themes
                                for (var i = 0; i < t.length; i++) if (t[i].id === Backend.settings.themeId) return t[i].name
                                return "自訂"
                            }
                            color: M3.c.onPrimaryContainer; font.pixelSize: 26; font.weight: Font.Medium
                        }
                        Text {
                            text: Backend.settings.variant + " · " + (Backend.dark ? "暗色" : "亮色") + " · 對比 " + Math.round(Backend.contrast * 100) + "%"
                            color: M3.alpha(M3.c.onPrimaryContainer, 0.78); font.pixelSize: M3.tLabel
                        }
                    }
                    Row {
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        Repeater {
                            model: [M3.c.primary, M3.c.secondary, M3.c.tertiary, M3.c.primaryContainer, M3.c.surface, M3.c.surfaceContainerHighest]
                            delegate: Rectangle {
                                width: 40; height: 40; radius: 13
                                color: modelData
                                border.width: 1; border.color: M3.alpha(M3.c.onPrimaryContainer, 0.2)
                            }
                        }
                    }
                }
                Row {
                    x: 26; y: 118; spacing: 8
                    Btn {
                        text: "主題與色彩"; icon: "palette"; kind: "filled"; small: true
                        onClicked: root.open("appearance")
                    }
                    Btn {
                        text: "切換深淺色"; icon: "contrast"; kind: "tonal"; small: true
                        onClicked: Backend.setScheme(Backend.seed, Backend.variant, !Backend.dark, Backend.contrast)
                    }
                    Rectangle {
                        width: fontLbl.implicitWidth + 30; height: 32; radius: 16
                        color: M3.alpha(M3.c.onPrimaryContainer, 0.14)
                        Row {
                            anchors.centerIn: parent; spacing: 6
                            Icon { anchors.verticalCenter: parent.verticalCenter; name: "text_fields"; size: 15; color: M3.c.onPrimaryContainer }
                            Text {
                                id: fontLbl
                                anchors.verticalCenter: parent.verticalCenter
                                text: "字級與動畫"; color: M3.c.onPrimaryContainer
                                font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                            }
                        }
                        StateLayer { anchors.fill: parent; radius: 16; onClicked: root.open("appearance") }
                    }
                }
            }

            // 分類
            Row {
                width: parent.width
                height: 30
                Text { anchors.verticalCenter: parent.verticalCenter; text: "設定分類"; color: M3.c.onSurface; font.pixelSize: M3.tBodyLg; font.weight: Font.DemiBold }
                FillSpacer {}
                Text { anchors.verticalCenter: parent.verticalCenter; visible: !root.sorting; text: "7 個分類 · 雙擊卡片可調整順序"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.sorting
                    text: "完成排序"; icon: "check"; kind: "tonal"; small: true
                    onClicked: root.sorting = false
                }
            }

            Grid {
                width: parent.width
                columns: 3
                spacing: M3.gap
                Repeater {
                    model: root.orderedCats
                    delegate: Rectangle {
                        width: (parent.width - M3.gap * 2) / 3; height: 148
                        radius: M3.rXl
                        color: cardHover.containsMouse ? M3.c.surfaceContainerHigh : M3.c.surfaceContainer
                        border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)
                        Behavior on color { ColorAnimation { duration: 120 } }
                        scale: cardHover.pressed ? 0.99 : 1
                        Behavior on scale { NumberAnimation { duration: 120 } }

                        Rectangle {
                            x: 20; y: 18; width: 42; height: 42; radius: 14
                            color: M3.tone(index)
                            Icon { anchors.centerIn: parent; name: modelData.icon; size: 21; fill: 1; color: M3.onTone(index) }
                        }
                        Text {
                            x: 20; y: 72
                            text: modelData.name; color: M3.c.onSurface
                            font.pixelSize: M3.tBodyLg; font.weight: Font.DemiBold
                        }
                        Text {
                            x: 20; y: 96; width: parent.width - 70
                            text: modelData.desc; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                            wrapMode: Text.WordWrap; lineHeight: 1.2
                        }
                        Row {
                            x: 20; y: 122; spacing: 6
                            Icon { anchors.verticalCenter: parent.verticalCenter; name: "tune"; size: 12; color: M3.c.primary }
                            Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.meta; color: M3.c.primary; font.pixelSize: 9; font.weight: Font.DemiBold }
                        }
                        Icon {
                            visible: !root.sorting
                            anchors.right: parent.right; anchors.rightMargin: 16
                            anchors.verticalCenter: parent.verticalCenter
                            name: "chevron_right"; size: 20; color: M3.c.onSurfaceVariant
                        }
                        MouseArea {
                            id: cardHover
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: { if (!root.sorting) root.open(modelData.id) }
                            onDoubleClicked: root.sorting = true
                        }
                        Row {
                            visible: root.sorting
                            anchors.right: parent.right; anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 4
                            IconBtn { icon: "arrow_back"; tip: "往前移"; size: 34; enabled: index > 0; onClicked: root.moveCat(modelData.id, -1) }
                            IconBtn { icon: "arrow_forward"; tip: "往後移"; size: 34; enabled: index < root.orderedCats.length - 1; onClicked: root.moveCat(modelData.id, 1) }
                        }
                    }
                }
            }

            // 資料與儲存
            Row {
                width: parent.width; height: 132; spacing: 14
                Repeater {
                    model: [
                        { t: "本機資料", v: Backend.dataDir, i: "folder", d: "帳號、Cookie、報表與設定" },
                        { t: "加密狀態", v: Backend.encryptionStatus, i: "enhanced_encryption", d: "密碼以系統帳戶金鑰加密" },
                        { t: "資料匯出", v: "JSON / CSV", i: "download", d: "匯出帳號、課程、學習報表與連線紀錄" }
                    ]
                    delegate: Rectangle {
                        width: (parent.width - 28) / 3; height: parent.height
                        radius: M3.rLg; color: M3.c.surfaceContainer
                        border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)
                        Icon { x: 18; y: 16; name: modelData.i; size: 20; color: M3.c.primary }
                        Text { x: 18; y: 46; text: modelData.t; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; font.weight: Font.DemiBold }
                        Text { x: 18; y: 64; text: modelData.v; color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.Medium; width: parent.width - 36; elide: Text.ElideRight }
                        Text { x: 18; y: 88; width: parent.width - 36; text: modelData.d; color: M3.c.onSurfaceVariant; font.pixelSize: 9; wrapMode: Text.WordWrap }
                    }
                }
            }

            Text {
                text: "設定會即時套用，並寫入 " + Backend.settingsFile
                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                width: parent.width; elide: Text.ElideMiddle
            }
        }
    }

    // ── 分類內容 ──
    Flickable {
        id: detailFlick
        anchors.fill: parent
        visible: root.section !== ""
        clip: true
        contentHeight: detailCol.height + 48
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: detailCol
            x: 28; y: 6; width: detailFlick.width - 56; spacing: 14

            Row {
                width: parent.width; height: 52; spacing: 12
                IconBtn {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "arrow_back"; tip: "回到設定"; size: 40
                    onClicked: root.back()
                }
                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    width: 38; height: 38; radius: 13
                    color: M3.c.primaryContainer
                    Icon {
                        anchors.centerIn: parent
                        name: root.catById(root.section).icon; size: 19; fill: 1; color: M3.c.onPrimaryContainer
                    }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 0
                    Text { text: root.catById(root.section).name; color: M3.c.onSurface; font.pixelSize: M3.tTitle; font.weight: Font.Medium }
                    Text { text: root.catById(root.section).desc; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                }
                FillSpacer {}
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "完成"; icon: "check"; kind: "tonal"; small: true
                    onClicked: root.back()
                }
            }

            Loader {
                id: sub
                width: detailCol.width
                height: item ? item.implicitHeight : 0
                source: root.section === "" ? "" : "settings/" + root.catById(root.section).file
                onLoaded: {
                    item.width = Qt.binding(function () { return sub.width })
                    if (item.notify) item.notify.connect(root.notify)
                }
            }
        }
    }

    function settingCount() {
        var s = Backend.settings, n = 0
        for (var k in s) n++
        return n
    }
}

