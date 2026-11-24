import QtQuick
import Cool 1.0
import "../components"

Flickable {
    id: root
    signal navigate(int page)
    signal notify(string text)
    signal openTerminal()
    clip: true
    contentHeight: col.height + 56
    boundsBehavior: Flickable.StopAtBounds
    topMargin: 0


    readonly property var acc: Backend.accounts.length > 0 ? Backend.accounts[Backend.selected] : null
    readonly property var latest: Backend.reports.length > 0 ? Backend.reports[Backend.reports.length - 1] : null
    readonly property bool hasReports: Backend.reports.length > 0
    readonly property int totalOpens: {
        var n = 0
        for (var i = 0; i < Backend.courses.length; i++) n += Backend.courses[i].opens
        return n
    }
    readonly property var recentCourses: {
        var arr = Backend.courses.slice()
        arr.sort(function (a, b) {
            var aa = a.openedAt || "", bb = b.openedAt || ""
            if (aa === bb) return b.opens - a.opens
            return aa < bb ? 1 : -1
        })
        return arr
    }
    readonly property int validCount: {
        var n = 0
        for (var i = 0; i < Backend.accounts.length; i++)
            if (Backend.accounts[i].cookie === "valid") n++
        return n
    }
    readonly property int expiredCount: {
        var n = 0
        for (var i = 0; i < Backend.accounts.length; i++)
            if (Backend.accounts[i].cookie === "expired") n++
        return n
    }
    readonly property int eventCount: {
        var n = 0
        for (var i = 0; i < Backend.sessions.length; i++) n += Backend.sessions[i].events.length
        return n
    }
    readonly property int running: {
        var n = 0
        for (var i = 0; i < Backend.sessions.length; i++)
            if (Backend.sessions[i].status === "active") n++
        return n
    }
    readonly property int threshold: Backend.settings.reportThreshold
    readonly property int chartMax: Backend.reports.length === 0
        ? Math.max(600, (Backend.settings.reportThreshold || 720) + 120)
        : Math.max(600, Math.ceil((maxMonth + 60) / 60) * 60)
    readonly property real maxMonth: {
        var m = 1
        for (var i = 0; i < Backend.reports.length; i++) {
            var t = Backend.reports[i].platform + Backend.reports[i].video
            if (t > m) m = t
        }
        return m
    }
    property int hoverBar: -1
    property string nowText: root.clockText()
    readonly property string dateText: (Backend.settings.dateFormat === "short"
        ? Qt.formatDate(new Date(), "M/d")
        : Qt.formatDate(new Date(), "yyyy 年 M 月 d 日")) + " · " + ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"][new Date().getDay()]
    readonly property string greeting: {
        var h = new Date().getHours()
        if (h < 5) return "夜深了"
        if (h < 11) return "早安"
        if (h < 14) return "午安"
        if (h < 18) return "下午好"
        return "晚安"
    }
    // 內嵌多句文案，依日期輪換
    readonly property var taglines: [
        "管理 Cool English 帳號、課程與學習進度，所有資料都保存在這台裝置。",
        "每天一點點，月底就是一大步。",
        "先整理課程連結，再一次開啟整組，省下來回點選的時間。",
        "Cookie 與密碼只用 Windows 系統加密保存，不會離開這台電腦。",
        "報表一鍵更新，未達門檻的月份會用警示色標出來。",
        "終端與桌面共用同一份帳號、網址與配色，兩邊改動即時同步。",
        "用無頭模式在背景開課程，需要時再到網路紀錄終止。",
        "穩定比衝刺更重要：固定時段、固定份量。"
    ]
    readonly property string tagline: {
        var d = new Date()
        var day = Math.floor((d - new Date(d.getFullYear(), 0, 0)) / 86400000)
        return taglines[day % taglines.length]
    }
    readonly property int monthTotal: latest ? latest.platform + latest.video : 0

    // 主視覺文字：暗色主題改用 onSurface，避免與深色漸層糊在一起
    readonly property color heroFg: Backend.dark ? M3.c.onSurface : M3.c.onPrimaryContainer
    readonly property color heroFgDim: Backend.dark ? M3.c.onSurfaceVariant : M3.alpha(M3.c.onPrimaryContainer, 0.78)

    Timer {
        interval: 20000; running: true; repeat: true
        onTriggered: root.nowText = root.clockText()
    }

    function clockText() {
        return Backend.settings.hour24 === false
            ? Qt.formatTime(new Date(), "hh:mm AP")
            : Qt.formatTime(new Date(), "hh:mm")
    }
    function totalOf(r) { return r.platform + r.video }
    function monthLabel(m) { return m.substring(5) + "月" }
    function shownEmail(value) {
        var email = String(value || "")
        if (Backend.settings.maskSensitive !== true) return email
        var at = email.indexOf("@")
        return at > 0 ? "••••" + email.substring(at) : "••••"
    }

    Column {
        id: col
        x: 28; width: root.width - 56; spacing: M3.gapLg
        y: 6

        // ── 主視覺 ──
        Rectangle {
            width: parent.width; height: 190
            radius: M3.rXl
            clip: true
            color: M3.c.surfaceContainer

            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: Backend.dark ? M3.alpha(M3.c.primaryContainer, 0.18) : M3.alpha(M3.c.primaryContainer, 0.85) }
                    GradientStop { position: 0.55; color: Backend.dark ? M3.alpha(M3.c.secondaryContainer, 0.55) : M3.alpha(M3.c.secondaryContainer, 0.55) }
                    GradientStop { position: 1.0; color: Backend.dark ? M3.alpha(M3.c.tertiaryContainer, 0.22) : M3.alpha(M3.c.tertiaryContainer, 0.35) }
                }
            }
            // 裝飾圓
            Rectangle {
                x: parent.width - 260; y: -70
                width: 300; height: 300; radius: 150
                color: M3.alpha(M3.c.surface, 0.10)
            }
            Rectangle {
                x: parent.width - 190; y: 90
                width: 160; height: 160; radius: 80
                color: M3.alpha(M3.c.surface, 0.12)
            }

            Column {
                x: 26; y: 22
                spacing: 4
                Text {
                    text: root.dateText.toUpperCase()
                    color: root.heroFg
                    font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.5
                }
                Row {
                    spacing: 14
                    Text {
                        text: root.greeting + "，" + (root.acc ? root.acc.name.split(" ")[0] : "朋友")
                        color: root.heroFg
                        font.pixelSize: 30; font.weight: Font.Medium
                    }
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        height: 26; width: 82; radius: 13
                        color: M3.alpha(M3.c.surface, 0.45)
                        Row {
                            anchors.centerIn: parent; spacing: 4
                            Icon { anchors.verticalCenter: parent.verticalCenter; name: "schedule"; size: 15; color: root.heroFg }
                            Text { anchors.verticalCenter: parent.verticalCenter; text: root.nowText; color: root.heroFg; font.pixelSize: M3.tBody; font.weight: Font.Bold }
                        }
                    }
                }
                Text {
                    width: 560
                    text: root.tagline
                    color: root.heroFgDim
                    font.pixelSize: M3.tBody
                    wrapMode: Text.WordWrap
                }
                Row {
                    y: 14; spacing: 10
                    Btn {
                        text: "取得本月報表"; icon: "download"; kind: "filled"; small: true
                        onClicked: { root.navigate(3); Backend.refreshReports() }
                    }
                    Btn {
                        text: "新增課程"; icon: "add_link"; kind: "tonal"; small: true
                        onClicked: root.navigate(2)
                    }
                    Btn {
                        text: "終端機"; icon: "terminal"; kind: "text"; small: true
                        onClicked: root.openTerminal()
                    }
                }
            }

            // 右側：本月門檻環
            Row {
                anchors.right: parent.right; anchors.rightMargin: 26
                anchors.verticalCenter: parent.verticalCenter
                spacing: 22
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 6
                    Text { text: "本月累積"; color: root.heroFgDim; font.pixelSize: M3.tLabel; font.weight: Font.DemiBold }
                    Row {
                        spacing: 4
                        Text { text: (root.monthTotal / 60).toFixed(1); color: root.heroFg; font.pixelSize: 34; font.weight: Font.DemiBold }
                        Text { anchors.bottom: parent.bottom; anchors.bottomMargin: 6; text: "小時"; color: root.heroFgDim; font.pixelSize: M3.tLabel }
                    }
                    Text {
                        text: "門檻 " + (root.threshold / 60).toFixed(0) + " 小時 · 還差 " + Math.max(0, ((root.threshold - root.monthTotal) / 60)).toFixed(1) + " 小時"
                        color: root.heroFgDim; font.pixelSize: M3.tMicro
                    }
                }
                Ring {
                    width: 116; height: 116
                    value: Math.min(1, root.monthTotal / root.threshold)
                    thickness: 11
                    track: M3.alpha(root.heroFg, 0.18)
                    fill: root.heroFg
                    label: Math.round(Math.min(1, root.monthTotal / root.threshold) * 100) + "%"
                    caption: "門檻達成"
                }
            }
        }

        // ── KPI ──
        Row {
            width: parent.width
            spacing: 12
            Stat {
                width: (parent.width - 36) / 4
                icon: "group"; label: "已連結帳號"; toneIndex: 0
                value: Backend.accounts.length + " 個"
                note: root.validCount + " 個有效 · " + root.expiredCount + " 個過期"
                trend: root.expiredCount > 0 ? root.expiredCount + " 待處理" : "全部有效"
                good: root.expiredCount === 0
                interactive: true
                onClicked: root.navigate(1)
            }
            Stat {
                width: (parent.width - 36) / 4
                icon: "menu_book"; label: "課程網址"; toneIndex: 1
                value: Backend.courses.length + " 個"
                note: "分為 " + root.categoryCount() + " 個分類"
                trend: root.totalOpens + " 次開啟"; good: true
                interactive: true
                onClicked: root.navigate(2)
            }
            Stat {
                width: (parent.width - 36) / 4
                icon: "monitoring"; label: "本月時數"; toneIndex: 2
                value: (root.monthTotal / 60).toFixed(1) + " h"
                note: "平台 " + (root.latest ? (root.latest.platform / 60).toFixed(1) : 0) + "h · 影片 " + (root.latest ? (root.latest.video / 60).toFixed(1) : 0) + "h"
                trend: root.monthTotal >= root.threshold ? "已達標" : "未達標"
                good: root.monthTotal >= root.threshold
                interactive: true
                onClicked: root.navigate(3)
            }
            Stat {
                width: (parent.width - 36) / 4
                icon: "lan"; label: "網路工作階段"; toneIndex: 3
                value: Backend.sessions.length + " 筆"
                note: root.eventCount + " 個事件 · " + (Backend.sessions.length > 0 ? "最近 " + Backend.sessions[0].time : "尚無紀錄")
                trend: root.running + " 執行中"; good: root.running > 0
                interactive: true
                onClicked: root.navigate(4)
            }
        }

        // ── 12 個月趨勢 ──
        Card {
            width: parent.width; height: 296

            Item {
                x: 24; y: 20; width: parent.width - 48; height: 44
                Column {
                    spacing: 2
                    Text { text: Backend.reports.length + " 個月學習時間"; color: M3.c.onSurface; font.pixelSize: M3.tBodyLg; font.weight: Font.DemiBold }
                    Text {
                        text: root.hasReports
                              ? "平台 " + (Backend.reports.reduce(function (s, r) { return s + r.platform }, 0) / 60).toFixed(1) + "h · 影片 " +
                                (Backend.reports.reduce(function (s, r) { return s + r.video }, 0) / 60).toFixed(1) + "h · 合計 " +
                                (Backend.reports.reduce(function (s, r) { return s + r.platform + r.video }, 0) / 60).toFixed(1) + "h"
                              : "尚無資料，請到「報表」頁按更新報表"
                        color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
                    }
                }
                Row {
                    anchors.right: parent.right; anchors.top: parent.top; spacing: 14
                    Row {
                        spacing: 6; anchors.verticalCenter: parent.verticalCenter
                        Rectangle { width: 9; height: 9; radius: 3; color: M3.c.primary; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "平台"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; anchors.verticalCenter: parent.verticalCenter }
                    }
                    Row {
                        spacing: 6; anchors.verticalCenter: parent.verticalCenter
                        Rectangle { width: 9; height: 9; radius: 3; color: M3.c.tertiary; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "影片"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; anchors.verticalCenter: parent.verticalCenter }
                    }
                    Row {
                        spacing: 6; anchors.verticalCenter: parent.verticalCenter
                        Rectangle { width: 14; height: 2; color: M3.c.error; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: "門檻"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }

            Item {
                id: plot
                x: 44; y: 78; width: parent.width - 76; height: 176
                readonly property real unit: (height - 18) / root.chartMax

                // 水平格線
                Repeater {
                    model: 5
                    delegate: Item {
                        readonly property real tick: root.chartMax * (4 - index) / 4
                        width: plot.width; y: plot.height - 18 - tick * plot.unit
                        Rectangle { width: parent.width; height: 1; color: M3.alpha(M3.c.outlineVariant, index === 4 ? 0.7 : 0.3) }
                        Text {
                            x: -34; y: -7; width: 30
                            horizontalAlignment: Text.AlignRight
                            text: tick === 0 ? "0" : (tick / 60).toFixed(tick % 60 === 0 ? 0 : 1) + "h"
                            color: M3.c.onSurfaceVariant; font.pixelSize: 9
                        }
                    }
                }
                // 門檻線
                Rectangle {
                    visible: Backend.settings.showThreshold !== false
                    width: plot.width; height: 1
                    y: plot.height - 18 - Math.min(root.chartMax, root.threshold) * plot.unit
                    color: Backend.settings.reportWarning ? Backend.settings.reportWarning : M3.c.error
                    opacity: 0.85
                }
                Text {
                    visible: !root.hasReports
                    anchors.centerIn: parent
                    text: "尚無學習時數，請到「報表」頁更新"
                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
                }

                Row {
                    width: parent.width
                    height: parent.height
                    Repeater {
                        model: Backend.reports
                        delegate: Item {
                            width: plot.width / Math.max(1, Backend.reports.length); height: plot.height
                            Rectangle {
                                visible: root.hoverBar === index
                                anchors.fill: parent
                                color: M3.alpha(M3.c.primary, 0.05)
                                radius: 8
                            }
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.horizontalCenterOffset: -6
                                y: parent.height - 18 - Math.min(root.chartMax, modelData.platform) * plot.unit
                                width: parent.width * 0.26
                                height: Math.min(root.chartMax, modelData.platform) * plot.unit
                                radius: 4
                                color: index === Backend.reports.length - 1 ? M3.c.primary : M3.alpha(M3.c.primary, 0.75)
                                Behavior on height { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.emphasized } }
                            }
                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.horizontalCenterOffset: 6
                                y: parent.height - 18 - Math.min(root.chartMax, modelData.video) * plot.unit
                                width: parent.width * 0.26
                                height: Math.min(root.chartMax, modelData.video) * plot.unit
                                radius: 4
                                color: index === Backend.reports.length - 1 ? M3.c.tertiary : M3.alpha(M3.c.tertiary, 0.75)
                                Behavior on height { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.emphasized } }
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                y: parent.height - 14
                                text: root.monthLabel(modelData.month)
                                color: root.totalOf(modelData) < root.threshold ? M3.c.error
                                     : index === Backend.reports.length - 1 ? M3.c.primary : M3.c.onSurfaceVariant
                                font.pixelSize: 9
                                font.weight: index === Backend.reports.length - 1 ? Font.Bold : Font.Normal
                            }
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                onEntered: root.hoverBar = index
                                onExited: root.hoverBar = -1
                            }
                            // 提示
                            Rectangle {
                                visible: root.hoverBar === index
                                z: 5
                                width: tipCol.width + 20; height: tipCol.height + 12
                                radius: 10
                                x: Math.max(-10, Math.min(parent.width - width + 10, (parent.width - width) / 2))
                                y: Math.max(0, parent.height - Math.min(root.chartMax, Math.max(modelData.platform, modelData.video)) * plot.unit - height - 6)
                                color: M3.c.inverseSurface
                                Column {
                                    id: tipCol
                                    x: 10; y: 6
                                    spacing: 1
                                    Text { text: modelData.month; color: M3.c.inverseOnSurface; font.pixelSize: 9; font.weight: Font.Bold }
                                    Text { text: "平台 " + (modelData.platform / 60).toFixed(1) + "h"; color: M3.c.inverseOnSurface; font.pixelSize: 9 }
                                    Text { text: "影片 " + (modelData.video / 60).toFixed(1) + "h"; color: M3.c.inverseOnSurface; font.pixelSize: 9 }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── 課程 + 帳號 ──
        Row {
            width: parent.width; spacing: 16

            Card {
                width: (parent.width - 16) * 0.58; height: 306
                SectionTitle {
                    x: 22; y: 18; width: parent.width - 44
                    title: "最近開啟的課程"; desc: "依最後開啟時間排序"
                    Btn { text: "全部課程"; kind: "text"; small: true; onClicked: root.navigate(2) }
                }
                Column {
                    x: 12; y: 70; width: parent.width - 24
                    Repeater {
                        model: root.recentCourses.slice(0, 4)
                        delegate: Rectangle {
                            width: parent.width; height: 52; radius: 14
                            color: hover.containsMouse ? M3.c.surfaceContainerHighest : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Rectangle {
                                x: 10; width: 34; height: 34; radius: 11; anchors.verticalCenter: parent.verticalCenter
                                color: M3.tone(index)
                                Icon { anchors.centerIn: parent; name: ["headphones", "auto_stories", "movie", "assignment"][index % 4]; size: 17; fill: 1; color: M3.onTone(index) }
                            }
                            Column {
                                x: 54; anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 150
                                spacing: 1
                                Text {
                                    text: modelData.alias
                                    color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.Medium
                                    width: parent.width; elide: Text.ElideRight
                                }
                                Text {
                                    text: modelData.category + " · 開啟 " + modelData.opens + " 次 · " + modelData.opened
                                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                    width: parent.width; elide: Text.ElideRight
                                }
                            }
                            Row {
                                anchors.right: parent.right; anchors.rightMargin: 8
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 4
                                IconBtn {
                                    icon: "open_in_new"; tip: "在瀏覽器開啟"; size: 30; iconSize: 15
                                    onClicked: Backend.openUrl(modelData.url)
                                }
                                IconBtn {
                                    icon: "content_copy"; tip: "複製網址"; size: 30; iconSize: 15
                                    onClicked: Backend.copyText(modelData.url)
                                }
                            }
                            MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        }
                    }
                    Text {
                        visible: root.recentCourses.length === 0
                        y: 40; width: parent.width
                        horizontalAlignment: Text.AlignHCenter
                        text: "尚無課程，請到「課程」頁新增網址"
                        color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
                    }
                }
            }

            Card {
                width: (parent.width - 16) * 0.42; height: 306
                SectionTitle {
                    x: 22; y: 18; width: parent.width - 44
                    title: "帳號狀態"; desc: root.validCount + " / " + Backend.accounts.length + " 個 Cookie 有效"
                    Btn { text: "管理"; kind: "text"; small: true; onClicked: root.navigate(1) }
                }
                Column {
                    x: 12; y: 70; width: parent.width - 24
                    Repeater {
                        model: Math.min(4, Backend.accounts.length)
                        delegate: Rectangle {
                            width: parent.width; height: 48; radius: 14
                            color: Backend.selected === index ? M3.c.secondaryContainer : (ahover.containsMouse ? M3.c.surfaceContainerHighest : "transparent")
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Rectangle {
                                x: 8; width: 30; height: 30; radius: 15; anchors.verticalCenter: parent.verticalCenter
                                color: Backend.selected === index ? M3.c.onSecondaryContainer : M3.c.surfaceContainerHighest
                                Text {
                                    anchors.centerIn: parent
                                    text: Backend.accounts[index].name.charAt(0)
                                    color: Backend.selected === index ? M3.c.secondaryContainer : M3.c.onSurfaceVariant
                                    font.pixelSize: 12; font.weight: Font.Bold
                                }
                            }
                            Column {
                                x: 46; anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 140
                                spacing: 0
                                Text {
                                    text: Backend.accounts[index].name
                                    color: Backend.selected === index ? M3.c.onSecondaryContainer : M3.c.onSurface
                                    font.pixelSize: M3.tLabel; font.weight: Font.Medium
                                    width: parent.width; elide: Text.ElideRight
                                }
                                Text {
                                    text: root.shownEmail(Backend.accounts[index].email)
                                    color: M3.c.onSurfaceVariant; font.pixelSize: 10
                                    width: parent.width; elide: Text.ElideRight
                                }
                            }
                            Chip {
                                anchors.right: parent.right; anchors.rightMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                height: 22
                text: Backend.accounts[index].cookie === "valid" ? "有效" : Backend.accounts[index].cookie === "expired" ? "過期" : "待檢查"
                                tone: Backend.accounts[index].cookie === "valid" ? M3.c.successContainer : Backend.accounts[index].cookie === "expired" ? M3.c.errorContainer : M3.c.warningContainer
                                onTone: Backend.accounts[index].cookie === "valid" ? M3.c.success : Backend.accounts[index].cookie === "expired" ? M3.c.onErrorContainer : M3.c.warning
                            }
                            MouseArea { id: ahover; anchors.fill: parent; hoverEnabled: true; onClicked: { Backend.select(index); root.notify("已切換到 " + Backend.accounts[index].name) } }
                        }
                    }
                }
                Text {
                    x: 22; y: parent.height - 32
                    text: root.expiredCount > 0 ? "有 " + root.expiredCount + " 個帳號需要重新登入" : "所有 Cookie 都在有效期內"
                    color: root.expiredCount > 0 ? M3.c.error : M3.c.onSurfaceVariant
                    font.pixelSize: M3.tMicro
                }
            }
        }

        // ── 工作階段 + 快速動作 ──
        Row {
            width: parent.width; spacing: 16

            Card {
                width: (parent.width - 16) * 0.58; height: 268
                SectionTitle {
                    x: 22; y: 18; width: parent.width - 44
                    title: "最近網路工作階段"; desc: root.running + " 個執行中 · " + root.eventCount + " 個事件"
                    Btn { text: "查看全部"; kind: "text"; small: true; onClicked: root.navigate(4) }
                }
                Column {
                    x: 12; y: 70; width: parent.width - 24
                    Repeater {
                        model: 4
                        delegate: Rectangle {
                            visible: index < Backend.sessions.length
                            width: parent.width; height: 44; radius: 12
                            color: shover.containsMouse ? M3.c.surfaceContainerHighest : "transparent"
                            Behavior on color { ColorAnimation { duration: 120 } }
                            Rectangle {
                                x: 10; width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter
                                color: !Backend.sessions[index] ? M3.c.outline
                                     : Backend.sessions[index].status === "active" ? M3.c.success
                                     : Backend.sessions[index].status === "failed" ? M3.c.error
                                     : Backend.sessions[index].status === "stopped" ? M3.c.warning : M3.c.outline
                            }
                            Text {
                                x: 28; anchors.verticalCenter: parent.verticalCenter
                                width: parent.width - 240
                                text: Backend.sessions[index] ? Backend.sessions[index].label : ""
                                color: M3.c.onSurface; font.pixelSize: M3.tLabel; font.weight: Font.Medium
                                elide: Text.ElideRight
                            }
                            Text {
                                anchors.right: parent.right; anchors.rightMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                text: Backend.sessions[index] ? Backend.sessions[index].time + " · " + Backend.sessions[index].events_n + " 事件" : ""
                                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                            }
                            MouseArea { id: shover; anchors.fill: parent; hoverEnabled: true; onClicked: root.navigate(4) }
                        }
                    }
                }
            }

            Card {
                width: (parent.width - 16) * 0.42; height: 268
                SectionTitle { x: 22; y: 18; width: parent.width - 44; title: "快速動作"; desc: "常用操作的捷徑" }
                Column {
                    x: 16; y: 70; width: parent.width - 32; spacing: 6
                    Repeater {
                        model: [
                            { t: "新增帳號", i: "person_add", p: 1 },
                            { t: "新增課程網址", i: "add_link", p: 2 },
                            { t: "匯出學習報表", i: "download", p: 3 },
                            { t: "開啟終端機", i: "terminal", p: -1 }
                        ]
                        delegate: Rectangle {
                            width: parent.width; height: 40; radius: 12
                            color: qhover.containsMouse ? M3.c.surfaceContainerHighest : M3.c.surfaceContainerLow
                            Row {
                                x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                                Icon { anchors.verticalCenter: parent.verticalCenter; name: modelData.i; size: 17; color: M3.c.primary }
                                Text { anchors.verticalCenter: parent.verticalCenter; text: modelData.t; color: M3.c.onSurface; font.pixelSize: M3.tLabel; font.weight: Font.Medium }
                            }
                            Icon { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; name: "chevron_right"; size: 16; color: M3.c.onSurfaceVariant }
                            MouseArea {
                                id: qhover; anchors.fill: parent; hoverEnabled: true
                                onClicked: {
                                    if (modelData.p >= 0) { root.navigate(modelData.p); root.notify("已前往 " + ["工作台", "帳號", "課程", "報表"][modelData.p]) }
                                    else root.openTerminal()
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    function categoryCount() {
        var seen = {}, n = 0
        for (var i = 0; i < Backend.courses.length; i++)
            if (!seen[Backend.courses[i].category]) { seen[Backend.courses[i].category] = true; n++ }
        return n
    }
}





