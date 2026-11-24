import QtQuick
import Cool 1.0
import "../components"

Item {
    id: root
    signal navigate(int page)
    signal notify(string text)

    readonly property int threshold: Backend.settings.reportThreshold
    readonly property var acc: Backend.accounts.length > 0 ? Backend.accounts[Backend.selected] : null
    readonly property int totalMinutes: {
        var n = 0
        for (var i = 0; i < Backend.reports.length; i++) n += Backend.reports[i].platform
        return n
    }
    readonly property int metCount: {
        var n = 0
        for (var i = 0; i < Backend.reports.length; i++)
            if (Backend.reports[i].platform >= threshold) n++
        return n
    }
    readonly property var best: {
        if (Backend.reports.length === 0) return null
        var b = Backend.reports[0]
        for (var i = 1; i < Backend.reports.length; i++)
            if (Backend.reports[i].platform > b.platform) b = Backend.reports[i]
        return b
    }
    readonly property var current: Backend.reports.length > 0 ? Backend.reports[Backend.reports.length - 1] : null
    // 依設定排序後的顯示順序（表格與 CLI 預覽共用）
    readonly property var displayReports: {
        var arr = Backend.reports.slice()
        return Backend.settings.reportSort === "oldest" ? arr : arr.reverse()
    }
    property int exportFormat: Backend.settings.exportFormat === "json" ? 1
                               : Backend.settings.exportFormat === "csv" ? 2 : 0
    readonly property int chartMax: Backend.reports.length === 0
        ? Math.max(600, (Backend.settings.reportThreshold || 720) + 120)
        : Math.max(600, root.maxReport() + 100)

    // 網站的原始資料：platform 已是「總時數」(影片+學習)，video 是影片，practice 是學習。
    // 不再把 platform + video 重複相加（那會多算一次影片）。
    function total(r) { return r.platform }
    function maxReport() {
        var m = 0
        for (var i = 0; i < Backend.reports.length; i++) m = Math.max(m, total(Backend.reports[i]))
        return m
    }
    function styleOf(key) { return Backend.cliStyle(key) }
    function cli(key) { return Backend.settings.cliColors[key] }
    function fgOf(key) { return styleOf(cli(key)).fg }
    function bgOf(key) { return styleOf(cli(key)).bg }

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentHeight: col.height + 48
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: col
            x: 28; y: 6; width: scroll.width - 56; spacing: M3.gap

            // 帳號選擇列
            Row {
                width: parent.width; height: 44; spacing: 10
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "帳號"; color: M3.c.onSurfaceVariant
                    font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                }
                Repeater {
                    model: Backend.accounts
                    delegate: Rectangle {
                        height: 36; width: albl.implicitWidth + 34; radius: 18
                        anchors.verticalCenter: parent.verticalCenter
                        color: Backend.selected === index ? M3.c.primary : M3.c.surfaceContainerHighest
                        Behavior on color { ColorAnimation { duration: 120 } }
                        Row {
                            anchors.centerIn: parent; spacing: 6
                            Rectangle {
                                width: 18; height: 18; radius: 9
                                anchors.verticalCenter: parent.verticalCenter
                                color: Backend.selected === index ? M3.alpha(M3.c.onPrimary, 0.2) : M3.c.surfaceContainer
                                Text {
                                    anchors.centerIn: parent
                                    text: modelData.name.charAt(0)
                                    color: Backend.selected === index ? M3.c.onPrimary : M3.c.onSurfaceVariant
                                    font.pixelSize: 10; font.weight: Font.Bold
                                }
                            }
                            Text {
                                id: albl
                                anchors.verticalCenter: parent.verticalCenter
                                text: modelData.name
                                color: Backend.selected === index ? M3.c.onPrimary : M3.c.onSurfaceVariant
                                font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                            }
                        }
                        StateLayer { anchors.fill: parent; radius: 18; onClicked: Backend.select(index) }
                    }
                }
                FillSpacer {}
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Backend.reportBusy ? "更新中…" : "更新報表"; icon: "refresh"; small: true
                    enabled: !Backend.reportBusy
                    onClicked: Backend.refreshReports()
                }
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "用 CLI 取得"; icon: "terminal"; kind: "outlined"; small: true
                    onClicked: Backend.openReportCli()
                }
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "匯出"; icon: "download"; kind: "outlined"; small: true
                    enabled: Backend.reports.length > 0
                    onClicked: exportDlg.open()
                }
            }

            // 資料來源與錯誤（真實抓取結果）
            Row {
                width: parent.width; height: 22; spacing: 8
                Icon {
                    anchors.verticalCenter: parent.verticalCenter
                    name: Backend.reportError !== "" ? "error" : "cloud_sync"; size: 15
                    color: Backend.reportError !== "" ? M3.c.error : M3.c.onSurfaceVariant
                }
                Text {
                    width: parent.width - 20
                    anchors.verticalCenter: parent.verticalCenter
                    text: Backend.reportError !== ""
                          ? "更新失敗：" + Backend.reportError + "（目前顯示上次成功的資料）"
                          : (Backend.reports.length > 0
                             ? "來源 " + (Backend.reportSource || "Cool English") + " · 更新 " + Backend.reportUpdated
                             : "尚未取得報表：請先選擇帳號，再按「更新報表」從 Cool English 下載學習時數")
                    color: Backend.reportError !== "" ? M3.c.error : M3.c.onSurfaceVariant
                    font.pixelSize: M3.tMicro
                    elide: Text.ElideMiddle
                }
            }

            // 摘要
            Row {
                width: parent.width; spacing: 14

                Rectangle {
                    width: (parent.width - 42) * 0.46; height: 190
                    radius: M3.rXl
                    color: M3.c.surfaceContainer
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)

                    Column {
                        x: 22; y: 20; spacing: 2
                        Text { text: "目前帳號"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text {
                            text: root.acc ? root.acc.name : "未選擇"
                            color: M3.c.onSurface; font.pixelSize: M3.tTitle; font.weight: Font.Medium
                        }
                        Text {
                            text: root.acc ? root.acc.email : ""
                            color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                        }
                    }
                    Row {
                        x: 22; y: 92; spacing: 26
                        Column {
                            spacing: 1
                            Text { text: (root.totalMinutes / 60).toFixed(1) + " h"; color: M3.c.onSurface; font.pixelSize: 26; font.weight: Font.DemiBold }
                            Text { text: Backend.reports.length + " 個月總時數"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                        }
                        Column {
                            spacing: 1
                            Text { text: root.metCount + " / " + Backend.reports.length; color: M3.c.onSurface; font.pixelSize: 26; font.weight: Font.DemiBold }
                            Text { text: "達標月份"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                        }
                        Column {
                            spacing: 1
                            Text { text: (root.best ? (root.total(root.best) / 60).toFixed(1) : "0") + " h"; color: M3.c.onSurface; font.pixelSize: 26; font.weight: Font.DemiBold }
                            Text { text: "最佳 " + (root.best ? root.best.month : ""); color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                        }
                    }
                    Chip {
                        x: 22; y: 156
                        text: root.current && root.total(root.current) >= root.threshold ? "本期已達門檻" : "本期未達門檻"
                        icon: root.current && root.total(root.current) >= root.threshold ? "verified" : "pending"
                        tone: root.current && root.total(root.current) >= root.threshold ? M3.c.successContainer : M3.c.errorContainer
                        onTone: root.current && root.total(root.current) >= root.threshold ? M3.c.success : M3.c.onErrorContainer
                    }
                }

                Rectangle {
                    width: (parent.width - 42) * 0.27; height: 190
                    radius: M3.rXl
                    color: M3.c.primaryContainer
                    Column {
                        x: 22; y: 20; spacing: 4
                        Text { text: "本期進度"; color: M3.alpha(M3.c.onPrimaryContainer, 0.75); font.pixelSize: M3.tMicro; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { id: monthTotalText; text: root.current ? (root.total(root.current) / 60).toFixed(1) + " h" : "—"; color: M3.c.onPrimaryContainer; font.pixelSize: 34; font.weight: Font.DemiBold }
                        Text {
                            text: root.current ? root.current.month + " · 門檻 " + (root.threshold / 60).toFixed(0) + " h" : ""
                            color: M3.alpha(M3.c.onPrimaryContainer, 0.78); font.pixelSize: M3.tMicro
                        }
                    }
                    ProgressBar {
                        x: 22; y: 120; width: parent.width - 44; thickness: 10
                        visible: root.current !== null
                        value: root.current ? Math.min(1, root.total(root.current) / root.threshold) : 0
                        tone: M3.c.onPrimaryContainer
                        track: M3.alpha(M3.c.onPrimaryContainer, 0.2)
                    }
                    Text {
                        x: 22; y: 142
                        visible: root.current !== null
                        text: root.current ? Math.round(Math.min(1, root.total(root.current) / root.threshold) * 100) + "% 已達成" : ""
                        color: M3.alpha(M3.c.onPrimaryContainer, 0.85); font.pixelSize: M3.tMicro; font.weight: Font.DemiBold
                    }
                    Text {
                        x: 22; y: 162
                        visible: root.current !== null
                        text: root.current ? "還差 " + Math.max(0, (root.threshold - root.total(root.current)) / 60).toFixed(1) + " 小時" : ""
                        color: M3.alpha(M3.c.onPrimaryContainer, 0.7); font.pixelSize: M3.tMicro
                    }
                    Text {
                        x: 22; y: 122
                        visible: root.current === null
                        text: "尚無報表資料，按「更新報表」取得"
                        color: M3.alpha(M3.c.onPrimaryContainer, 0.8); font.pixelSize: M3.tMicro
                        width: parent.width - 44; wrapMode: Text.WordWrap
                    }
                }

                Rectangle {
                    width: (parent.width - 42) * 0.27; height: 190
                    radius: M3.rXl
                    color: M3.c.surfaceContainer
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)
                    Column {
                        x: 22; y: 20; spacing: 2
                        Text { text: "組成分佈"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { text: "平台與影片"; color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.Medium }
                    }
                    Column {
                        x: 22; y: 70; width: parent.width - 44; spacing: 14
                        Repeater {
                            model: [
                                { l: "總時數", v: root.sumPlatform(), c: M3.c.primary },
                                { l: "影片", v: root.sumVideo(), c: M3.c.tertiary },
                                { l: "學習", v: root.sumPractice(), c: M3.c.secondary }
                            ]
                            delegate: Column {
                                width: parent.width; spacing: 5
                                Row {
                                    width: parent.width
                                    Text { text: modelData.l; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                                    FillSpacer {}
                                    Text { text: (modelData.v / 60).toFixed(1) + " h"; color: M3.c.onSurface; font.pixelSize: M3.tMicro; font.weight: Font.DemiBold }
                                }
                                Rectangle {
                                    width: parent.width; height: 6; radius: 3; color: M3.c.surfaceContainerHighest
                                    Rectangle {
                                        width: parent.width * Math.max(0, Math.min(1, modelData.v / Math.max(1, root.totalMinutes)))
                                        height: parent.height; radius: 3; color: modelData.c
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // 趨勢圖
            Card {
                width: parent.width; height: 272
                Item {
                    x: 24; y: 18; width: parent.width - 48; height: 40
                    Column {
                        spacing: 2
                        Text { text: "每月學習時間"; color: M3.c.onSurface; font.pixelSize: M3.tBodyLg; font.weight: Font.DemiBold }
                        Text { text: "紅色線為 " + (root.threshold / 60).toFixed(0) + " 小時門檻；點長條可看明細"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                    }
                    Row {
                        anchors.right: parent.right; anchors.top: parent.top; spacing: 14
                        Row {
                            spacing: 6
                            Rectangle { width: 9; height: 9; radius: 3; color: M3.c.primary; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "學習"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; anchors.verticalCenter: parent.verticalCenter }
                        }
                        Row {
                            spacing: 6
                            Rectangle { width: 9; height: 9; radius: 3; color: M3.c.tertiary; anchors.verticalCenter: parent.verticalCenter }
                            Text { text: "影片"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; anchors.verticalCenter: parent.verticalCenter }
                        }
                    }
                }
                Item {
                    id: plot2
                    x: 46; y: 74; width: parent.width - 78; height: 156
                    readonly property real unit: height / root.chartMax

                    Repeater {
                        model: 4
                        delegate: Item {
                            readonly property real tick: root.chartMax * (3 - index) / 3
                            width: plot2.width; y: plot2.height - tick * plot2.unit
                            Rectangle { width: parent.width; height: 1; color: M3.alpha(M3.c.outlineVariant, 0.3) }
                            Text { x: -36; y: -7; width: 32; horizontalAlignment: Text.AlignRight; text: (tick / 60).toFixed(tick % 60 === 0 ? 0 : 1) + "h"; color: M3.c.onSurfaceVariant; font.pixelSize: 9 }
                        }
                    }
                    Rectangle {
                        visible: Backend.settings.showThreshold !== false
                        width: plot2.width; height: 1
                        y: plot2.height - root.threshold * plot2.unit
                        color: Backend.settings.reportWarning ? Backend.settings.reportWarning : M3.c.error
                        opacity: 0.8
                    }
                    Text {
                        visible: Backend.reports.length === 0
                        anchors.centerIn: parent
                        text: "尚無報表資料"
                        color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
                    }

                    Row {
                        width: parent.width; height: parent.height
                        Repeater {
                            model: Backend.reports
                            delegate: Item {
                                width: plot2.width / Math.max(1, Backend.reports.length); height: plot2.height
                                // platform 已是總時數(= 學習 practice + 影片 video)。
                                // 下方藍色畫學習(practice)，上方紫色畫影片(video)，兩者堆疊=總時數。
                                Rectangle {
                                    anchors.bottom: parent.bottom
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: parent.width * 0.52
                                    height: Math.min(root.chartMax, modelData.practice) * plot2.unit
                                    radius: 4
                                    color: index === Backend.reports.length - 1 ? M3.c.primary : M3.alpha(M3.c.primary, 0.62)
                                }
                                Rectangle {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    width: parent.width * 0.52
                                    // 紫色底部對齊藍色顶部：y = 底部 - (practice + video) * unit
                                    y: parent.height - (Math.min(root.chartMax, modelData.practice) + modelData.video) * plot2.unit
                                    height: modelData.video * plot2.unit
                                    radius: 4
                                    color: index === Backend.reports.length - 1 ? M3.c.tertiary : M3.alpha(M3.c.tertiary, 0.62)
                                }
                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    y: parent.height + 5
                                    text: modelData.month.substring(5) + "月"
                                    color: index === Backend.reports.length - 1 ? M3.c.primary : M3.c.onSurfaceVariant
                                    font.pixelSize: 9; font.weight: index === Backend.reports.length - 1 ? Font.Bold : Font.Normal
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onClicked: root.notify(modelData.month + "：" + (root.total(modelData) / 60).toFixed(1) + " 小時")
                                }
                            }
                        }
                    }
                }
            }

            // 表格 + 匯出預覽
            Row {
                width: parent.width; spacing: 16

                Rectangle {
                    width: (parent.width - 16) * 0.56; height: 552
                    radius: M3.rXl
                    color: M3.c.surfaceContainer
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)
                    clip: true

                    Item {
                        id: thead
                        x: 20; y: 16; width: parent.width - 40; height: 32
                        Text { text: "月份"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { x: parent.width * 0.22; text: "平台"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { x: parent.width * 0.39; text: "影片"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { x: parent.width * 0.55; visible: Backend.settings.showPractice !== false; text: "學習"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { x: parent.width * 0.70; text: "總時數"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                        Text { x: parent.width * 0.85; text: "狀態"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1 }
                    }

                    WheelGuard { target: tscroll }
                    Flickable {
                        id: tscroll
                        objectName: "tableScroll"
                        x: 12; y: 52; width: parent.width - 24; height: parent.height - 64
                        contentHeight: tcol.height
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds

                        Column {
                            id: tcol
                            width: tscroll.width
                            Repeater {
                                model: root.displayReports
                                delegate: Rectangle {
                                    property bool isCurrent: modelData.month === (root.current ? root.current.month : "")
                                    width: parent.width; height: 38; radius: 10
                                    color: rowHover.containsMouse ? M3.c.surfaceContainerHighest
                                         : isCurrent ? M3.alpha(M3.c.primary, 0.08) : "transparent"
                                    Behavior on color { ColorAnimation { duration: 120 } }
                                    Text {
                                        x: 8; anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.month
                                        color: isCurrent ? M3.c.primary : M3.c.onSurface
                                        font.pixelSize: M3.tLabel; font.weight: isCurrent ? Font.Bold : Font.Medium
                                    }
                                    Text { x: parent.width * 0.22; anchors.verticalCenter: parent.verticalCenter; text: (modelData.platform / 60).toFixed(1) + " h"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel }
                                    Text { x: parent.width * 0.39; anchors.verticalCenter: parent.verticalCenter; text: (modelData.video / 60).toFixed(1) + " h"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel }
                                    Text { x: parent.width * 0.55; visible: Backend.settings.showPractice !== false; anchors.verticalCenter: parent.verticalCenter; text: (modelData.practice / 60).toFixed(1) + " h"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel }
                                    Text {
                                        x: parent.width * 0.70; anchors.verticalCenter: parent.verticalCenter
                                        text: (root.total(modelData) / 60).toFixed(1) + " h"
                                        color: M3.c.onSurface; font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                                    }
                                    Chip {
                                        x: parent.width * 0.85; anchors.verticalCenter: parent.verticalCenter
                                        height: 22
                                        text: root.total(modelData) >= root.threshold ? "達標" : (root.total(modelData) >= root.threshold * 0.9 ? "接近" : "未達")
                                        tone: root.total(modelData) >= root.threshold ? M3.c.successContainer
                                            : root.total(modelData) >= root.threshold * 0.9 ? M3.c.warningContainer : M3.c.errorContainer
                                        onTone: root.total(modelData) >= root.threshold ? M3.c.success
                                            : root.total(modelData) >= root.threshold * 0.9 ? M3.c.warning : M3.c.onErrorContainer
                                    }
                                    MouseArea { id: rowHover; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                                }
                            }
                        }
                    }

                    // 表格捲軸
                    Rectangle {
                        visible: tscroll.contentHeight > tscroll.height + 2
                        width: 4; radius: 2
                        x: parent.width - 9
                        height: Math.max(28, tscroll.height * tscroll.height / Math.max(1, tscroll.contentHeight))
                        y: 52 + (tscroll.contentY / Math.max(1, tscroll.contentHeight - tscroll.height)) * (tscroll.height - height)
                        color: M3.alpha(M3.c.onSurfaceVariant, 0.35)
                    }
                    Text {
                        visible: Backend.reports.length === 0
                        anchors.centerIn: parent
                        anchors.verticalCenterOffset: 20
                        text: "尚無資料，請按上方「更新報表」"
                        color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
                    }
                }

                // CLI 報表預覽
                Rectangle {
                    width: (parent.width - 16) * 0.44; height: 552
                    radius: M3.rXl
                    color: M3.c.surfaceContainer
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.35)

                    Row {
                        x: 20; y: 16; spacing: 8
                        Icon { anchors.verticalCenter: parent.verticalCenter; name: "terminal"; size: 18; color: M3.c.primary }
                        Text { anchors.verticalCenter: parent.verticalCenter; text: "CLI 報表預覽"; color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.DemiBold }
                        Item { width: 1; height: 1 }
                    }
                    Btn {
                        anchors.right: parent.right; anchors.rightMargin: 16; y: 10
                        text: "配色設定"; kind: "text"; small: true
                        onClicked: root.navigate(5)
                    }

                    Rectangle {
                        x: 16; y: 52; width: parent.width - 32; height: parent.height - 68
                        radius: 14; color: M3.c.surfaceContainerLowest
                        border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.3)
                        clip: true

                        Item {
                            x: 14; y: 10; width: parent.width - 28; height: parent.height - 20

                            Text {
                                text: "═══ 學習時間 · " + (root.acc ? root.acc.name : "") + " ═══"
                                color: root.fgOf("titleText")
                                font.family: M3.mono; font.pixelSize: 10; font.weight: Font.Bold
                            }
                            Text {
                                y: 18
                                text: "──────────────────────────────────────────"
                                color: root.fgOf("title"); font.family: M3.mono; font.pixelSize: 10
                            }
                            Item {
                                y: 38; width: parent.width; height: 13
                                Text { x: 0; text: "月份"; color: root.fgOf("header"); font.family: M3.mono; font.pixelSize: 9; font.weight: Font.Bold }
                                Text { x: 78; text: "停留"; color: root.fgOf("header"); font.family: M3.mono; font.pixelSize: 9; font.weight: Font.Bold }
                                Text { x: 138; text: "影片"; color: root.fgOf("header"); font.family: M3.mono; font.pixelSize: 9; font.weight: Font.Bold }
                                Text { x: 198; text: "學習"; color: root.fgOf("header"); font.family: M3.mono; font.pixelSize: 9; font.weight: Font.Bold }
                                Text { x: 258; text: "總時數"; color: root.fgOf("header"); font.family: M3.mono; font.pixelSize: 9; font.weight: Font.Bold }
                                Text { x: parent.width - 40; text: "狀態"; color: root.fgOf("header"); font.family: M3.mono; font.pixelSize: 9; font.weight: Font.Bold }
                            }
                            Rectangle { y: 54; width: parent.width; height: 1; color: root.fgOf("sep"); opacity: 0.5 }

                            // 所有月份都在這裡，可用滑鼠滾輪或拖曳捲動
                            WheelGuard { target: pscroll }
                            Flickable {
                                id: pscroll
                                objectName: "previewScroll"
                                y: 58; width: parent.width
                                height: parent.height - 58 - 46
                                contentHeight: pcol.height
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds

                                Column {
                                    id: pcol
                                    width: pscroll.width
                                    Repeater {
                                        model: root.displayReports
                                        delegate: Rectangle {
                                            property var r: modelData
                                            property bool below: root.total(r) < root.threshold
                                            property bool cur: r.month === (root.current ? root.current.month : "")
                                            property var st: cur ? root.styleOf(root.cli("current"))
                                                                 : (below ? root.styleOf(root.cli("below")) : null)
                                            property bool tinted: st !== null && st.bg !== null
                                            width: parent.width; height: 25
                                            radius: 3
                                            color: tinted ? st.bg : "transparent"

                                            Text { x: 4; text: r.month; color: parent.tinted ? parent.st.fg : M3.c.onSurfaceVariant; font.family: M3.mono; font.pixelSize: 10 }
                                            Text { x: 78; text: (r.platform / 60).toFixed(1) + "h"; color: parent.tinted ? parent.st.fg : M3.c.onSurface; font.family: M3.mono; font.pixelSize: 10 }
                                            Text { x: 138; text: (r.video / 60).toFixed(1) + "h"; color: parent.tinted ? parent.st.fg : M3.c.onSurface; font.family: M3.mono; font.pixelSize: 10 }
                                            Text { x: 198; text: (r.practice / 60).toFixed(1) + "h"; color: parent.tinted ? parent.st.fg : M3.c.onSurface; font.family: M3.mono; font.pixelSize: 10 }
                                            Text {
                                                x: 258
                                                text: (root.total(r) / 60).toFixed(1) + "h"
                                                color: parent.tinted ? parent.st.fg : (root.total(r) >= root.threshold ? M3.c.success : M3.c.onSurface)
                                                font.family: M3.mono; font.pixelSize: 10; font.weight: Font.Bold
                                            }
                                            Text {
                                                x: parent.width - 40
                                                text: root.total(r) >= root.threshold ? "OK" : "!!"
                                                color: parent.tinted ? parent.st.fg : (root.total(r) >= root.threshold ? M3.c.success : M3.c.error)
                                                font.family: M3.mono; font.pixelSize: 10; font.weight: Font.Bold
                                            }
                                        }
                                    }
                                }
                            }

                            // 預覽捲軸
                            Rectangle {
                                visible: pscroll.contentHeight > pscroll.height + 2
                                width: 3; radius: 2
                                x: parent.width - 3
                                y: 58 + (pscroll.contentY / Math.max(1, pscroll.contentHeight - pscroll.height)) * (pscroll.height - height)
                                height: Math.max(24, pscroll.height * pscroll.height / Math.max(1, pscroll.contentHeight))
                                color: M3.alpha(M3.c.onSurfaceVariant, 0.35)
                            }

                            Rectangle {
                                y: parent.height - 46
                                width: parent.width; height: 1
                                color: root.fgOf("sep"); opacity: 0.5
                            }
                            Text {
                                y: parent.height - 38
                                width: parent.width
                                elide: Text.ElideRight
                                text: "合計 " + (root.totalMinutes / 60).toFixed(1) + "h · 達標 " + root.metCount + "/" + Backend.reports.length + " · 門檻 " + (root.threshold / 60).toFixed(0) + "h"
                                color: root.fgOf("header")
                                font.family: M3.mono; font.pixelSize: 9; font.weight: Font.Bold
                            }
                            Text {
                                y: parent.height - 18
                                width: parent.width
                                text: Backend.reportSource !== "" ? Backend.reportSource : "尚未取得報表來源網址"
                                color: root.fgOf("url"); font.family: M3.mono; font.pixelSize: 8
                                elide: Text.ElideMiddle
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: exportDlg
        title: "匯出學習報表"
        subtitle: "會寫入專案內的 exports/ 資料夾。"
        icon: "download"
        preferredWidth: 520

        Seg {
            model: ["CLI 文字", "JSON", "CSV"]
            currentIndex: root.exportFormat
            onPicked: function (i) { root.exportFormat = i }
        }
        Pref {
            title: "包含影片時間"
            desc: "匯出時一併計入影片課程"
            Toggle { checked: true; anchors.verticalCenter: parent.verticalCenter }
        }
        Pref {
            title: "保留 ANSI 色彩"
            desc: "僅 CLI 文字格式有效"
            Toggle { checked: true; anchors.verticalCenter: parent.verticalCenter }
        }
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: exportDlg.close() }
            FillSpacer {}
            Btn {
                text: "匯出"; icon: "download"
                onClicked: {
                    exportDlg.close()
                    Backend.updateSetting("exportFormat", ["cli", "json", "csv"][root.exportFormat])
                    Backend.exportReport(["txt", "json", "csv"][root.exportFormat])
                }
            }
        }
    }

    function sumPlatform() { var n = 0; for (var i = 0; i < Backend.reports.length; i++) n += Backend.reports[i].platform; return n }
    function sumVideo() { var n = 0; for (var i = 0; i < Backend.reports.length; i++) n += Backend.reports[i].video; return n }
    function sumPractice() { var n = 0; for (var i = 0; i < Backend.reports.length; i++) n += Backend.reports[i].practice; return n }
}





