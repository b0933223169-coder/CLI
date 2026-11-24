import QtQuick
import Cool 1.0
import "../components"

Item {
    id: root
    objectName: "networkPage"
    signal navigate(int page)
    signal notify(string text)

    property int view: 1              // 0 執行中 / 1 歷史（預設看歷史，執行中只在更新時出現）
    property string mode: "all"       // all | headed | headless | direct
    property string openId: ""
    property int detailTab: 0         // 0 排版 / 1 原始
    property var selected: []
    property string pendingStop: ""
    property string pendingDelete: ""
    property bool pendingBulk: false

    // 快取 Backend.sessions：QML 每次讀 Backend.sessions 都要做一次
    // Python→QML 的整份 list 轉換；切分頁時會讀上百次而卡死。這裡只在
    // sessionsChanged 時更新一次，其餘都用純 QML 的快取。
    property var sessions: Backend.sessions
    property var detailEvents: []
    property string rawCache: ""
    Connections {
        target: Backend
        function onSessionsChanged() {
            root.sessions = Backend.sessions
            if (root.openId !== "") root.loadDetail()
        }
        function onSessionOpened(sid, live) {
            // 停用紀錄時：直接切到「網路紀錄 › 正在運行」並展開該筆的即時進度
            if (live) { root.view = 0; root.mode = "all"; root.openId = sid; root.detailTab = 2 }
            root.navigate(4)
        }
    }
    onOpenIdChanged: loadDetail()
    Component.onCompleted: {
        // 從「停用紀錄」的課程開啟切進來時：直接顯示正在運行並展開第一筆
        for (var i = 0; i < sessions.length; i++)
            if (sessions[i].status === "active") { view = 0; openId = sessions[i].id; detailTab = sessions[i].lines !== "" ? 2 : 0; break }
    }
    function loadDetail() {
        if (openId === "") { detailEvents = []; rawCache = ""; return }
        detailEvents = Backend.sessionEvents(openId, 0, 400)
        rawCache = detailTab === 1 ? Backend.sessionRaw(openId, 300000) : rawCache
    }
    onDetailTabChanged: if (detailTab === 1 && openId !== "") rawCache = Backend.sessionRaw(openId, 300000)

    readonly property var modes: [
        { k: "all", n: "全部" }, { k: "headed", n: "有頭" },
        { k: "headless", n: "無頭" }, { k: "direct", n: "直接請求" }
    ]
    function isShown(s) {
        if (!s) return false
        if (view === 0 && s.status !== "active") return false
        if (view === 1 && s.status === "active") return false
        if (mode !== "all" && s.mode !== mode) return false
        return true
    }
    function countMode(k) {
        var n = 0
        for (var i = 0; i < root.sessions.length; i++) {
            var s = root.sessions[i]
            if (view === 0 && s.status !== "active") continue
            if (view === 1 && s.status === "active") continue
            if (k !== "all" && s.mode !== k) continue
            n++
        }
        return n
    }
    readonly property var shown: {
        var out = []
        for (var i = 0; i < root.sessions.length; i++) {
            var s = root.sessions[i]
            if (view === 0 && s.status !== "active") continue
            if (view === 1 && s.status === "active") continue
            if (mode !== "all" && s.mode !== mode) continue
            out.push(s)
        }
        return out
    }
    readonly property int running: countStatus("active")
    readonly property int history: root.sessions.length - running
    readonly property int totalEvents: {
        var n = 0
        for (var i = 0; i < root.sessions.length; i++) n += root.sessions[i].events_n
        return n
    }
    readonly property var openSession: {
        for (var i = 0; i < root.sessions.length; i++)
            if (root.sessions[i].id === openId) return root.sessions[i]
        return null
    }

    function countStatus(st) {
        var n = 0
        for (var i = 0; i < root.sessions.length; i++)
            if (root.sessions[i].status === st) n++
        return n
    }
    function modeName(m) { return m === "headed" ? "有頭" : m === "headless" ? "無頭" : "直接請求" }
    function modeIcon(m) { return m === "headed" ? "open_in_new" : m === "headless" ? "visibility_off" : "bolt" }
    function modeTone(m) { return m === "headed" ? M3.c.primaryContainer : m === "headless" ? M3.c.secondaryContainer : M3.c.tertiaryContainer }
    function modeOn(m) { return m === "headed" ? M3.c.onPrimaryContainer : m === "headless" ? M3.c.onSecondaryContainer : M3.c.onTertiaryContainer }
    function statusName(s) { return s === "active" ? "執行中" : s === "completed" ? "完成" : s === "stopped" ? "已停止" : "失敗" }
    function statusTone(s) { return s === "active" ? M3.c.successContainer : s === "completed" ? M3.c.secondaryContainer : s === "stopped" ? M3.c.warningContainer : M3.c.errorContainer }
    function statusOn(s) { return s === "active" ? M3.c.success : s === "completed" ? M3.c.onSecondaryContainer : s === "stopped" ? M3.c.warning : M3.c.onErrorContainer }
    function isSelected(id) { return selected.indexOf(id) >= 0 }
    function toggle(id) {
        var out = selected.slice()
        var i = out.indexOf(id)
        if (i >= 0) out.splice(i, 1); else out.push(id)
        selected = out
    }
    function selectAll() {
        if (selected.length === shown.length) { selected = []; return }
        var out = []
        for (var i = 0; i < shown.length; i++) out.push(shown[i].id)
        selected = out
    }
    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        contentHeight: col.height + 48
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: col
            x: 28; y: 6; width: scroll.width - 56; spacing: M3.gap

            // 摘要
            Row {
                width: parent.width; spacing: 12
                Stat {
                    width: (parent.width - 36) / 4
                    icon: "fiber_manual_record"; label: "執行中"; value: root.running + " 筆"
                    note: "正在更新的請求"; toneIndex: 0
                    trend: root.running > 0 ? "LIVE" : "閒置"; good: root.running > 0
                }
                Stat {
                    width: (parent.width - 36) / 4
                    icon: "history"; label: "歷史紀錄"; value: root.history + " 筆"; note: "已停止或完成"; toneIndex: 1
                }
                Stat {
                    width: (parent.width - 36) / 4
                    icon: "receipt_long"; label: "事件總數"; value: root.totalEvents + " 個"; note: "請求和回應"; toneIndex: 2
                }
                Stat {
                    width: (parent.width - 36) / 4
                    icon: "database"; label: "資料量"; value: Backend.networkSize; note: "實際請求與回應位元組"; toneIndex: 0
                }
            }

            // 視圖切換
            Row {
                width: parent.width; height: 44; spacing: 12
                Seg {
                    model: ["正在運行 " + root.running, "歷史紀錄 " + root.history]
                    currentIndex: root.view
                    anchors.verticalCenter: parent.verticalCenter
                    onPicked: function (i) { root.view = i; root.openId = ""; root.selected = [] }
                }
                Rectangle { width: 1; height: 24; color: M3.alpha(M3.c.outlineVariant, 0.6); anchors.verticalCenter: parent.verticalCenter }
                Repeater {
                    model: root.modes
                    delegate: Rectangle {
                        height: 34; width: mlbl.implicitWidth + 26; radius: 17
                        anchors.verticalCenter: parent.verticalCenter
                        color: root.mode === modelData.k ? M3.c.primary : M3.c.surfaceContainerHighest
                        Behavior on color { ColorAnimation { duration: 120 } }
                        Text {
                            id: mlbl; anchors.centerIn: parent
                            text: modelData.n + " " + root.countMode(modelData.k)
                            color: root.mode === modelData.k ? M3.c.onPrimary : M3.c.onSurfaceVariant
                            font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                        }
                        StateLayer { anchors.fill: parent; radius: 17; onClicked: { root.mode = modelData.k; root.openId = "" } }
                    }
                }
                FillSpacer {}
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.view === 1
                    text: "全選"; icon: root.selected.length === root.shown.length && root.shown.length > 0 ? "deselect" : "select_all"
                    kind: "text"; small: true
                    onClicked: root.selectAll()
                }
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.view === 1 && root.selected.length > 0
                    text: "刪除 " + root.selected.length; icon: "delete"; kind: "tonal"; small: true; danger: true
                    onClicked: {
                        if (Backend.settings.confirmDestructive === false) { Backend.deleteSessions(root.selected); root.selected = [] }
                        else { root.pendingBulk = true; bulkDlg.open() }
                    }
                }
                Btn {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: root.view === 1
                    text: "匯出全部"; icon: "download"; kind: "outlined"; small: true
                    onClicked: Backend.exportSessions()
                }
            }

            // 清單
            EmptyState {
                visible: root.shown.length === 0
                width: parent.width; height: 260
                icon: "lan"
                title: root.view === 0 ? "目前沒有執行中的工作階段" : "尚無連線紀錄"
                desc: root.view === 0 ? "開啟課程、登入或更新報表時，正在執行的工作階段會出現在這裡。" : "登入、開啟課程或更新報表時，這裡會記錄本程式實際發出的 Chromium 請求與回應。"
                actionText: root.view === 0 ? "看歷史紀錄" : "看全部歷史"
                onAction: { if (root.view === 0) root.view = 1; else { root.mode = "all" } }
            }

            Repeater {
                model: root.sessions
                delegate: Item {
                    width: col.width
                    visible: root.isShown(modelData)
                    height: visible ? (62 + (root.openId === modelData.id ? 332 : 0)) : 0
                    property var rowData: modelData

                    Rectangle {
                        width: parent.width; height: parent.height
                        radius: M3.rLg
                        color: M3.c.surfaceContainer
                        border.width: 1
                        border.color: root.openId === modelData.id ? M3.alpha(M3.c.primary, 0.5) : M3.alpha(M3.c.outlineVariant, 0.35)
                        clip: true
                        Behavior on border.color { ColorAnimation { duration: 150 } }

                        // 上列
                        Item {
                            id: rowTop
                            width: parent.width; height: 62

                            Check {
                                x: 16; anchors.verticalCenter: parent.verticalCenter
                                visible: root.view === 1
                                checked: root.isSelected(modelData.id)
                                onToggled: root.toggle(modelData.id)
                            }

                            Rectangle {
                                x: root.view === 1 ? 50 : 18
                                width: 8; height: 8; radius: 4
                                anchors.verticalCenter: parent.verticalCenter
                                color: modelData.status === "active" ? M3.c.success
                                     : modelData.status === "failed" ? M3.c.error
                                     : modelData.status === "stopped" ? M3.c.warning : M3.c.outline
                            }
                            Text {
                                x: root.view === 1 ? 68 : 36
                                anchors.verticalCenter: parent.verticalCenter
                                width: 250
                                text: modelData.label
                                color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.Medium
                                elide: Text.ElideRight
                            }
                            Chip {
                                x: parent.width * 0.34; anchors.verticalCenter: parent.verticalCenter
                                height: 24
                                text: root.modeName(modelData.mode)
                                icon: root.modeIcon(modelData.mode)
                                tone: root.modeTone(modelData.mode)
                                onTone: root.modeOn(modelData.mode)
                            }
                            Chip {
                                x: parent.width * 0.46; anchors.verticalCenter: parent.verticalCenter
                                height: 24
                                text: root.statusName(modelData.status)
                                tone: root.statusTone(modelData.status)
                                onTone: root.statusOn(modelData.status)
                            }
                            Text {
                                x: parent.width * 0.57; anchors.verticalCenter: parent.verticalCenter
                                text: modelData.time
                                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                            }
                            Text {
                                x: parent.width * 0.70; anchors.verticalCenter: parent.verticalCenter
                                text: modelData.events_n + " 事件"
                                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                            }
                            Text {
                                x: parent.width * 0.78; anchors.verticalCenter: parent.verticalCenter
                                text: modelData.size
                                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                            }

                            Row {
                                anchors.right: parent.right; anchors.rightMargin: 10
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 4
                                Btn {
                                    visible: modelData.status === "active" && modelData.label.indexOf("登入") !== 0
                                    text: "終止"; icon: "stop_circle"; kind: "outlined"; small: true; danger: true
                                    onClicked: { root.pendingStop = modelData.id; stopDlg.open() }
                                }
                                IconBtn {
                                    icon: "download"; tip: "匯出 JSON"; size: 32; iconSize: 16
                                    onClicked: Backend.exportSession(modelData.id)
                                }
                                IconBtn {
                                    visible: root.view === 1
                                    icon: "delete"; tip: "刪除紀錄"; size: 32; iconSize: 16; danger: true
                                    onClicked: {
                                        if (Backend.settings.confirmDestructive === false) Backend.deleteSession(modelData.id)
                                        else { root.pendingDelete = modelData.id; deleteDlg.open() }
                                    }
                                }
                                IconBtn {
                                    icon: root.openId === modelData.id ? "expand_less" : "expand_more"
                                    tip: root.openId === modelData.id ? "收合明細" : "查看明細"
                                    size: 32; iconSize: 18
                                    onClicked: { root.openId = root.openId === modelData.id ? "" : modelData.id; root.detailTab = 0 }
                                }
                            }
                        }

                        // 明細：只在展開的那一筆才建立（其餘不建，避免切換時全量重建卡頓）
                        Loader {
                            active: root.openId === modelData.id
                            sourceComponent: root.openId === modelData.id ? detailComp : undefined
                            y: 62; width: parent.width; height: parent.height - 62
                        }
                        Component {
                            id: detailComp
                            Item {
                            width: parent.width; height: parent.height

                            Rectangle {
                                x: 16; y: 0; width: parent.width - 32; height: 1
                                color: M3.alpha(M3.c.outlineVariant, 0.5)
                            }

                            Row {
                                x: 20; y: 12; width: parent.width - 40; spacing: 8
                                Repeater {
                                    model: ["排版檢視", "原始 JSONL", "CLI 畫面"]
                                    delegate: Rectangle {
                                        height: 30; width: dlbl.implicitWidth + 24; radius: 9
                                        color: root.detailTab === index ? M3.c.secondaryContainer : "transparent"
                                        Text {
                                            id: dlbl; anchors.centerIn: parent
                                            text: modelData
                                            color: root.detailTab === index ? M3.c.onSecondaryContainer : M3.c.onSurfaceVariant
                                            font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                                        }
                                        StateLayer { anchors.fill: parent; radius: 9; onClicked: root.detailTab = index }
                                    }
                                }
                                Chip {
                                    anchors.verticalCenter: parent.verticalCenter
                                    height: 22
                                    text: modelData.account
                                    icon: "person"
                                    tone: M3.c.surfaceContainerHighest
                                    onTone: M3.c.onSurfaceVariant
                                }
                                FillSpacer {}
                                Btn {
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: root.detailTab === 1
                                    text: "重新讀取"; icon: "refresh"; kind: "text"; small: true
                                    onClicked: {
                                        root.loadDetail()
                                        root.rawCache = Backend.sessionRaw(root.openId, 300000)
                                        root.notify(root.openSession ? "已重新讀取工作階段資料" : "尚未選擇工作階段")
                                    }
                                }
                                Btn {
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "複製"; icon: "content_copy"; kind: "text"; small: true
                                    onClicked: Backend.copyText(JSON.stringify(root.openSession ? root.openSession : {}, null, 2))
                                }
                            }

                            // 排版檢視
                            Item {
                                visible: root.detailTab === 0
                                x: 20; y: 50; width: parent.width - 40; height: parent.height - 58

                                Item {
                                    id: ehead
                                    width: parent.width; height: 26
                                    Text { text: "時間"; color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.weight: Font.Bold }
                                    Text { x: parent.width * 0.11; text: "類型"; color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.weight: Font.Bold }
                                    Text { x: parent.width * 0.22; text: "方法"; color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.weight: Font.Bold }
                                    Text { x: parent.width * 0.31; text: "路徑"; color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.weight: Font.Bold }
                                    Text { x: parent.width * 0.72; text: "狀態"; color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.weight: Font.Bold }
                                    Text { x: parent.width * 0.81; text: "耗時"; color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.weight: Font.Bold }
                                    Text { x: parent.width * 0.90; text: "大小"; color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.weight: Font.Bold }
                                }
                                Rectangle { y: 26; width: parent.width; height: 1; color: M3.alpha(M3.c.outlineVariant, 0.4) }

                                WheelGuard { target: evList }
                                ListView {
                                    id: evList
                                    y: 30; width: parent.width; height: parent.height - 58
                                    clip: true; boundsBehavior: Flickable.StopAtBounds
                                    model: root.detailEvents
                                    delegate: Rectangle {
                                            width: parent.width; height: 28; radius: 6
                                            property var e: modelData
                                            color: "transparent"
                                            Text { x: 0; anchors.verticalCenter: parent.verticalCenter; text: e ? e.time : ""; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.family: M3.mono }
                                            Text {
                                                x: parent.width * 0.11; anchors.verticalCenter: parent.verticalCenter
                                                text: e ? (e.kind === "request" ? "請求" : e.kind === "response" ? "回應" : "失敗") : ""
                                                color: e && e.kind === "failed" ? M3.c.error : M3.c.onSurfaceVariant
                                                font.pixelSize: 10
                                            }
                                            Text { x: parent.width * 0.22; anchors.verticalCenter: parent.verticalCenter; text: e ? e.method : ""; color: M3.c.onSurface; font.pixelSize: 10; font.family: M3.mono; font.weight: Font.Bold }
                                            Text {
                                                x: parent.width * 0.31; anchors.verticalCenter: parent.verticalCenter
                                                width: parent.width * 0.38
                                                text: e ? e.path : ""
                                                color: M3.c.onSurface; font.pixelSize: 10; font.family: M3.mono
                                                elide: Text.ElideMiddle
                                            }
                                            Text {
                                                x: parent.width * 0.72; anchors.verticalCenter: parent.verticalCenter
                                                text: e && e.status > 0 ? e.status : "—"
                                                color: !e || e.status === 0 ? M3.c.onSurfaceVariant : e.status >= 400 ? M3.c.error : M3.c.success
                                                font.pixelSize: 10; font.family: M3.mono
                                            }
                                            Text { x: parent.width * 0.81; anchors.verticalCenter: parent.verticalCenter; text: e && e.ms ? e.ms + " ms" : "—"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.family: M3.mono }
                                            Text { x: parent.width * 0.90; anchors.verticalCenter: parent.verticalCenter; text: e ? e.size : ""; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.family: M3.mono }
                                        }
                                }
                                WheelGuard { target: liveScroll; visible: liveScroll.visible }
                                Flickable {
                                    id: liveScroll
                                    visible: root.detailEvents.length === 0 && modelData.lines !== ""
                                    y: 30; width: parent.width; height: parent.height - 58
                                    contentHeight: liveText.implicitHeight; clip: true
                                    boundsBehavior: Flickable.StopAtBounds
                                    Text {
                                        id: liveText; width: parent.width
                                        textFormat: Text.RichText
                                        text: "<span style='color:" + M3.c.onSurfaceVariant + "'>即時進度（不保存為網路事件）</span>\n\n" + Backend.ansiToHtml(modelData.lines)
                                        color: M3.c.onSurface; font.family: M3.mono; font.pixelSize: 11
                                        wrapMode: Text.WrapAnywhere
                                    }
                                }
                                Text {
                                    visible: root.detailEvents.length === 0 && modelData.lines === ""
                                    anchors.centerIn: parent
                                    text: modelData.status === "active" ? "等待網路事件…" : "這筆工作階段沒有保留事件"
                                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
                                }
                                Text {
                                    visible: root.detailEvents.length > 0
                                    y: parent.height - 22
                                    text: "共 " + modelData.events_n + " 個事件" +
                                          (modelData.events_n > root.detailEvents.length ? " · 只顯示前 " + root.detailEvents.length + " 筆，完整內容請匯出" : "")
                                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                }
                            }

                            // CLI 畫面：cool.py 在終端機會看到的輸出（含顏色），登入、前往網站、報表等都在這裡
                            Rectangle {
                                visible: root.detailTab === 2
                                x: 20; y: 50; width: parent.width - 40; height: parent.height - 58
                                radius: 12; color: Backend.settings.terminalBg ? Backend.settings.terminalBg : "#101418"
                                border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.3)
                                clip: true
                                WheelGuard { target: cliScroll }
                                Flickable {
                                    id: cliScroll
                                    anchors.fill: parent; anchors.margins: 12
                                    contentHeight: cliText.implicitHeight
                                    clip: true
                                    boundsBehavior: Flickable.StopAtBounds
                                    property bool stick: true
                                    onMovementEnded: stick = (contentY + height >= contentHeight - 8)
                                    onContentHeightChanged: if (modelData.status === "active" && stick) contentY = Math.max(0, contentHeight - height)
                                    Text {
                                        id: cliText
                                        width: parent.width
                                        textFormat: Text.RichText
                                        text: modelData.lines !== "" ? Backend.ansiToHtml(modelData.lines)
                                              : "<span style='color:#8b949e'>這筆工作階段沒有 CLI 輸出（只有由 cool.py 執行的登入、開啟課程、報表等工作階段才有）。</span>"
                                        color: Backend.settings.terminalText ? Backend.settings.terminalText : "#d7dde5"
                                        font.family: M3.mono; font.pixelSize: 12
                                        wrapMode: Text.WrapAnywhere
                                    }
                                }
                            }

                            // 原始數據
                            Rectangle {
                                visible: root.detailTab === 1
                                x: 20; y: 50; width: parent.width - 40; height: parent.height - 58
                                radius: 12; color: M3.c.surfaceContainerLowest
                                border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.3)
                                clip: true
                                WheelGuard { target: rawScroll }
                                Flickable {
                                    id: rawScroll
                                    anchors.fill: parent; anchors.margins: 12
                                    contentHeight: raw.implicitHeight
                                    clip: true
                                    boundsBehavior: Flickable.StopAtBounds
                                    Text {
                                        id: raw
                                        width: parent.width
                                        text: root.rawCache
                                        color: M3.c.onSurface
                                        font.family: M3.mono; font.pixelSize: 10
                                        wrapMode: Text.WrapAnywhere
                                        lineHeight: 1.2
                                    }
                                }
                            }
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: stopDlg
        title: "終止工作階段？"
        subtitle: "只會關閉這筆工作階段所屬的瀏覽器；其他工作階段不受影響。"
        icon: "stop_circle"
        preferredWidth: 460
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: stopDlg.close() }
            FillSpacer {}
            Btn {
                text: "終止工作階段"; icon: "stop_circle"; danger: true
                onClicked: { Backend.stopSession(root.pendingStop); stopDlg.close() }
            }
        }
    }

    Dialog {
        id: deleteDlg
        title: "刪除這筆紀錄？"
        subtitle: "事件與原始數據會一起刪除，無法復原。"
        icon: "delete_forever"
        preferredWidth: 460
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: deleteDlg.close() }
            FillSpacer {}
            Btn {
                text: "刪除"; icon: "delete"; danger: true
                onClicked: { Backend.deleteSession(root.pendingDelete); deleteDlg.close() }
            }
        }
    }

    Dialog {
        id: bulkDlg
        title: "刪除選取的紀錄？"
        subtitle: "共 " + root.selected.length + " 筆，刪除後無法復原。"
        icon: "delete_sweep"
        preferredWidth: 460
        Row {
            width: parent.width; spacing: 8
            Btn { text: "取消"; kind: "text"; onClicked: bulkDlg.close() }
            FillSpacer {}
            Btn {
                text: "全部刪除"; icon: "delete_sweep"; danger: true
                onClicked: { Backend.deleteSessions(root.selected); root.selected = []; bulkDlg.close() }
            }
        }
    }

    function historySize() { return Backend.networkSize }
}



