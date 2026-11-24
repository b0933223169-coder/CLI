import QtQuick
import QtQuick.Window
import QtQuick.Controls
import Cool 1.0
import "components"
import "pages"

Window {
    id: win
    width: 1440; height: 900; minimumWidth: 1060; minimumHeight: 700
    visible: true
    title: "cool · 學習工作台"
    color: M3.c.surface
    Behavior on color { ColorAnimation { duration: M3.dLong } }

    // 啟動頁面只在啟動時決定一次（不能做成綁定：換頁會寫入 lastPage → 設定變動 → 綁定重算，形成迴圈）
    property int page: 0
    function initialPage() {
        var s = Backend.settings
        if (s.restoreSession !== false && (s.lastPage || 0) > 0)
            return Math.min(5, Math.max(0, s.lastPage))
        return Math.max(0, Math.min(5, s.startPage || 0))
    }
    property string settingsSection: ""
    property bool termOpen: Backend.settings.terminalAutoOpen === true
    property bool launcherOpen: false
    property string toastText: ""
    property string toastIcon: "check_circle"
    property int termHeight: 340
    property int termWidth: 520
    readonly property bool termSide: Backend.settings.terminalDock === "right"

    // 內嵌終端：抽屜打開時若還沒有任何分頁，直接在裡面開一個真正的 shell（並自動執行 cool.py）
    onTermOpenChanged: if (termOpen && Backend.terminalCount === 0) Backend.startTerminal(Backend.defaultTerminal)
    Component.onCompleted: {
        page = initialPage()
        if (termOpen && Backend.terminalCount === 0) Backend.startTerminal(Backend.defaultTerminal)
    }
    Connections {
        target: Backend
        function onTerminalRequested() { win.termOpen = true }
    }

    // 側邊欄：滑過展開（設定頁可切換）
    readonly property bool railExpanded: Backend.settings.sidebarMode === "hover"
                                        && Backend.settings.showNavLabels !== false
                                        && railHover.hovered && !win.launcherOpen
    readonly property int railWidth: railExpanded ? 212 : 84

    onPageChanged: if (Backend.settings.restoreSession !== false) Backend.updateSetting("lastPage", page)

    readonly property var nav: [
        { label: "工作台", icon: "space_dashboard", sub: "今天的學習狀態、12 個月趨勢與最近活動" },
        { label: "帳號", icon: "group", sub: "管理 Cool English 帳號、Cookie 與登入方式" },
        { label: "課程", icon: "menu_book", sub: "整理課程網址，用指定帳號開啟" },
        { label: "報表", icon: "monitoring", sub: "每月學習時間、門檻與匯出" },
        { label: "網路", icon: "lan", sub: "本程式實際發出的請求、事件與原始數據" },
        { label: "設定", icon: "tune", sub: "外觀、終端、工作區、報表、隱私" }
    ]
    readonly property int expiredCount: {
        var n = 0
        for (var i = 0; i < Backend.accounts.length; i++)
            if (Backend.accounts[i].cookie === "expired") n++
        return n
    }
    readonly property int runningCount: {
        var n = 0
        for (var i = 0; i < Backend.sessions.length; i++)
            if (Backend.sessions[i].status === "active") n++
        return n
    }

    onClosing: function (close) {
        Backend.saveWindowGeometry(width, height, x, y)
        if (Backend.settings.trayOnClose === true && Backend.trayAvailable) {
            close.accepted = false
            win.hide()
        }
    }

    // 閒置自動鎖定
    property bool locked: false
    property int lockAfter: 10
    property string unlockError: ""

    function unlockNow() {
        if (Backend.hasUnlockPassword() && !Backend.verifyUnlock(unlockField.text)) {
            win.unlockError = "密碼不正確，請再試一次"
            unlockField.text = ""
            unlockField.forceInput()
            return
        }
        win.locked = false
        win.unlockError = ""
        unlockField.text = ""
        Backend.resetIdle()
        win.toast("已解除鎖定")
    }

    Connections {
        target: Backend
        function onToast(text) {
            // 圖示依訊息性質：進行中（…）用沙漏、失敗類用警示，其餘才是打勾——避免「還在登入」看起來像「已完成」
            var icon = "check_circle"
            if (text.indexOf("…") >= 0 || text.indexOf("...") >= 0) icon = "hourglass_top"
            else if (/失敗|無法|找不到|錯誤|沒有取得|不可|請先/.test(text)) icon = "error"
            win.toastWith(text, icon)
        }
        function onSessionOpened(sid, live) { if (live) win.go(4) }
        function onLockRequested(minutes) {
            win.lockAfter = minutes
            win.unlockError = ""
            win.locked = true
        }
    }

    function go(i) { page = i; launcherOpen = false }
    function toast(t) { toastText = t; toastTimer.restart() }
    function toastWith(t, icon) { toastIcon = icon; toast(t) }

    FontLoader { source: "../assets/fonts/MaterialSymbolsRounded.ttf" }
    Shortcut { sequence: "Ctrl+K"; onActivated: win.launcherOpen = !win.launcherOpen }
    Shortcut { sequence: "Ctrl+`"; onActivated: win.termOpen = !win.termOpen }
    Shortcut { sequence: "Escape"; enabled: win.launcherOpen; onActivated: { win.launcherOpen = false } }
    Timer { id: toastTimer; interval: 2800; onTriggered: win.toastText = "" }

    // ───────── 左側邊框（導覽列）─────────
    Item {
        id: rail
        x: 0; y: 0; width: win.railWidth; height: parent.height
        z: 2  // 讓收合時的滑過提示能蓋在內容區上
        Behavior on width { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.standard } }

        HoverHandler { id: railHover }

        Rectangle {
            id: brand
            x: 18; y: 22; width: 48; height: 48; radius: win.launcherOpen ? 16 : 24
            color: M3.c.primaryContainer
            Behavior on radius { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
            Icon { anchors.centerIn: parent; name: "bolt"; fill: 1; size: 26; color: M3.c.onPrimaryContainer }
            StateLayer { anchors.fill: parent; radius: parent.radius; color: M3.c.onPrimaryContainer; onClicked: win.launcherOpen = !win.launcherOpen }
        }

        // 目前頁面指示膠囊
        Rectangle {
            id: pill
            x: 18; width: 48; height: 48; radius: 16
            y: 94 + win.page * 54
            color: M3.c.secondaryContainer
            Behavior on y { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
            Behavior on color { ColorAnimation { duration: M3.dMed } }
        }

        Repeater {
            model: win.nav.length
            delegate: Item {
                x: 18; y: 94 + index * 54; width: 48; height: 48
                Icon {
                    anchors.centerIn: parent
                    name: win.nav[index].icon
                    fill: win.page === index ? 1 : 0
                    size: 24
                    color: win.page === index ? M3.c.onSecondaryContainer : M3.c.onSurfaceVariant
                }
                // 頁碼小點：顯示未讀狀態
                Rectangle {
                    visible: (index === 1 && win.expiredCount > 0) || (index === 4 && win.runningCount > 0)
                    x: 37; y: 6; width: 8; height: 8; radius: 4
                    color: index === 1 ? M3.c.error : M3.c.success
                    border.width: 1.5; border.color: M3.c.surface
                }
                StateLayer { id: navHit; anchors.fill: parent; radius: 16; onClicked: win.go(index) }
                Text {
                    x: 56; anchors.verticalCenter: parent.verticalCenter
                    text: win.nav[index].label
                    color: win.page === index ? M3.c.onSecondaryContainer : M3.c.onSurfaceVariant
                    font.pixelSize: M3.tLabel; font.weight: win.page === index ? Font.DemiBold : Font.Medium
                    opacity: win.railExpanded ? 1 : 0
                    visible: opacity > 0.01
                    Behavior on opacity { NumberAnimation { duration: M3.dMed } }
                }
                Rectangle {
                    x: 56; anchors.verticalCenter: parent.verticalCenter
                    height: 32; width: tip.implicitWidth + 24; radius: 10
                    color: M3.c.inverseSurface
                    opacity: navHit.containsMouse && !win.railExpanded ? 1 : 0; visible: opacity > 0.01
                    scale: navHit.containsMouse ? 1 : 0.8; transformOrigin: Item.Left
                    z: 20
                    Behavior on opacity { NumberAnimation { duration: M3.dShort } }
                    Behavior on scale { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
                    Text { id: tip; anchors.centerIn: parent; text: win.nav[index].label; color: M3.c.inverseOnSurface; font.pixelSize: M3.tLabel; font.weight: Font.DemiBold }
                }
            }
        }

        Column {
            x: 18; anchors.bottom: parent.bottom; anchors.bottomMargin: 18; spacing: 10
            Rectangle {
                width: 48; height: 48; radius: 16; color: win.termOpen ? M3.c.tertiaryContainer : "transparent"
                Behavior on color { ColorAnimation { duration: M3.dMed } }
                Icon { anchors.centerIn: parent; name: "terminal"; size: 23; color: win.termOpen ? M3.c.onTertiaryContainer : M3.c.onSurfaceVariant }
                StateLayer { anchors.fill: parent; radius: 16; onClicked: win.termOpen = !win.termOpen }
            }
            Rectangle {
                width: 48; height: 48; radius: 24; color: M3.c.surfaceContainerHigh
                Icon { anchors.centerIn: parent; name: Backend.dark ? "dark_mode" : "light_mode"; fill: 1; size: 21; color: M3.c.primary }
                StateLayer { anchors.fill: parent; radius: 24; onClicked: Backend.setScheme(Backend.seed, Backend.variant, !Backend.dark, Backend.contrast) }
            }
            AvatarView {
                width: 48; height: 48; radius: 24
                source: Backend.accounts.length > 0
                        ? (Backend.accounts[Backend.selected] || Backend.accounts[0]).avatar : ""
                name: Backend.accounts.length > 0
                      ? (Backend.accounts[Backend.selected] || Backend.accounts[0]).name : "?"
                tint: M3.c.primaryContainer
                onTint: M3.c.onPrimaryContainer
                StateLayer { anchors.fill: parent; radius: 24; onClicked: win.go(1) }
            }
        }
    }

    // ───────── 內容「螢幕」─────────
    Rectangle {
        id: screen
        x: win.railWidth; y: 10; width: parent.width - win.railWidth - 10; height: parent.height - 20
        Behavior on x { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.standard } }
        Behavior on width { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.standard } }
        radius: 30
        color: M3.c.surfaceContainerLow
        Behavior on color { ColorAnimation { duration: M3.dLong } }
        clip: true

        Rectangle {
            anchors.fill: parent; radius: parent.radius
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: M3.alpha(M3.c.primaryContainer, 0.42) }
                GradientStop { position: 0.32; color: M3.alpha(M3.c.primaryContainer, 0) }
            }
        }

        // 頂部：頁面標題 + 狀態 + 指令列
        Item {
            id: top
            x: 32; y: 16; width: parent.width - 64; height: 68

            Column {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 2
                Row {
                    spacing: 8
                    Text {
                        text: "COOL"; color: M3.c.primary
                        font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 2
                    }
                    Rectangle { width: 4; height: 4; radius: 2; color: M3.c.outline; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                        text: win.page === 0 ? "YOUR LEARNING WORKSPACE" : win.nav[win.page].label.toUpperCase()
                        color: M3.c.onSurfaceVariant
                        font.pixelSize: 10; font.weight: Font.DemiBold; font.letterSpacing: 1.4
                    }
                }
                Row {
                    spacing: 10
                    Text {
                        text: win.nav[win.page].label; color: M3.c.onSurface
                        font.pixelSize: 27; font.weight: Font.Medium
                    }
                    Rectangle {
                        anchors.verticalCenter: parent.verticalCenter
                        visible: win.page === 4 && win.runningCount > 0
                        height: 22; width: runLbl.implicitWidth + 16; radius: 11
                        color: M3.c.successContainer
                        Text { id: runLbl; anchors.centerIn: parent; text: win.runningCount + " 執行中"; color: M3.c.success; font.pixelSize: M3.tMicro; font.weight: Font.Bold }
                    }
                }
                Text {
                    text: win.nav[win.page].sub; color: M3.c.onSurfaceVariant
                    font.pixelSize: M3.tLabel
                }
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8

                Rectangle {
                    width: 252; height: 42; radius: 21; color: M3.c.surfaceContainerHighest
                    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.4)
                    Icon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: "search"; size: 19; color: M3.c.onSurfaceVariant }
                    Text { x: 42; anchors.verticalCenter: parent.verticalCenter; text: "搜尋頁面、帳號、課程…"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel }
                    Rectangle {
                        anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                        width: 44; height: 24; radius: 7; color: M3.alpha(M3.c.surface, 0.55)
                        Text { anchors.centerIn: parent; text: "Ctrl K"; color: M3.c.onSurfaceVariant; font.pixelSize: 10; font.weight: Font.DemiBold }
                    }
                    StateLayer { anchors.fill: parent; radius: 21; onClicked: win.launcherOpen = true }
                }

                IconBtn {
                    icon: "refresh"; tip: "重新讀取 accounts.json"; size: 42
                    onClicked: Backend.refresh()
                }
                IconBtn {
                    icon: "notifications"; tip: win.expiredCount > 0 ? win.expiredCount + " 個帳號需要重新登入" : "沒有通知"
                    size: 42; active: win.expiredCount > 0; danger: win.expiredCount > 0
                    onClicked: { win.go(1); if (win.expiredCount > 0) win.toast(win.expiredCount + " 個帳號的 Cookie 已過期") }
                }
                Item { width: 4; height: 1 }
                Rectangle {
                    id: acctChip
                    width: 172; height: 42; radius: 21; color: M3.c.surfaceContainerHigh
                    Row {
                        anchors.centerIn: parent; spacing: 8
                        AvatarView {
                            width: 26; height: 26; radius: 13
                            source: Backend.accounts.length > 0 && Backend.accounts[Backend.selected]
                                    ? Backend.accounts[Backend.selected].avatar : ""
                            name: Backend.accounts.length > 0 && Backend.accounts[Backend.selected]
                                  ? Backend.accounts[Backend.selected].name : "?"
                            tint: M3.c.secondaryContainer
                            onTint: M3.c.onSecondaryContainer
                        }
                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: Backend.accounts.length > 0 && Backend.accounts[Backend.selected] ? Backend.accounts[Backend.selected].name : "未選擇"
                            color: M3.c.onSurface; font.pixelSize: M3.tLabel; font.weight: Font.Medium
                            width: 78; elide: Text.ElideRight
                        }
                        Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            name: acctMenu.opened ? "expand_less" : "expand_more"; size: 18; color: M3.c.onSurfaceVariant
                        }
                    }
                    StateLayer { anchors.fill: parent; radius: 21; onClicked: { if (acctMenu.opened) acctMenu.close(); else acctMenu.open() } }

                    // 帳號切換選單：不用特地跑到帳號頁
                    Popup {
                        id: acctMenu
                        objectName: "acctMenu"
                        parent: acctChip
                        x: acctChip.width - width
                        y: acctChip.height + 8
                        width: 320
                        padding: 8
                        modal: false
                        focus: true
                        closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
                        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: M3.dShort } }
                        background: Rectangle {
                            radius: 18; color: M3.c.surfaceContainerHigh
                            border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.6)
                        }
                        contentItem: Column {
                            spacing: 2
                            Text {
                                x: 8; width: parent.width - 16; height: 24
                                text: "切換帳號"; color: M3.c.onSurfaceVariant
                                font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1
                                verticalAlignment: Text.AlignVCenter
                            }
                            Text {
                                visible: Backend.accounts.length === 0
                                x: 8; width: parent.width - 16; height: 44
                                text: "尚未連結帳號"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
                                verticalAlignment: Text.AlignVCenter
                            }
                            Repeater {
                                model: Backend.accounts
                                delegate: Rectangle {
                                    width: parent.width; height: 52; radius: 12
                                    color: Backend.selected === index ? M3.c.secondaryContainer
                                         : (rowArea.containsMouse ? M3.c.surfaceContainerHighest : "transparent")
                                    AvatarView {
                                        x: 8; width: 34; height: 34; radius: 17
                                        anchors.verticalCenter: parent.verticalCenter
                                        source: modelData.avatar; name: modelData.name
                                        tint: M3.c.surfaceContainerHighest; onTint: M3.c.onSurfaceVariant
                                    }
                                    Column {
                                        x: 52; anchors.verticalCenter: parent.verticalCenter
                                        width: parent.width - 52 - 52; spacing: 1
                                        Text {
                                            text: modelData.name; width: parent.width; elide: Text.ElideRight
                                            color: Backend.selected === index ? M3.c.onSecondaryContainer : M3.c.onSurface
                                            font.pixelSize: M3.tBody; font.weight: Font.Medium
                                        }
                                        Text {
                                            text: modelData.email; width: parent.width; elide: Text.ElideRight
                                            color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                                        }
                                    }
                                    Rectangle {
                                        anchors.right: parent.right; anchors.rightMargin: 38
                                        anchors.verticalCenter: parent.verticalCenter
                                        width: 8; height: 8; radius: 4
                                        color: modelData.cookie === "valid" ? M3.c.success : modelData.cookie === "expired" ? M3.c.error : M3.c.warning
                                    }
                                    Icon {
                                        visible: Backend.selected === index
                                        anchors.right: parent.right; anchors.rightMargin: 10
                                        anchors.verticalCenter: parent.verticalCenter
                                        name: "check"; size: 18; color: M3.c.onSecondaryContainer
                                    }
                                    MouseArea {
                                        id: rowArea
                                        anchors.fill: parent; hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: { Backend.select(index); acctMenu.close() }
                                    }
                                }
                            }
                            Rectangle { width: parent.width; height: 1; color: M3.alpha(M3.c.outlineVariant, 0.5) }
                            Rectangle {
                                width: parent.width; height: 40; radius: 12
                                color: manageArea.containsMouse ? M3.c.surfaceContainerHighest : "transparent"
                                Row {
                                    x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                                    Icon { name: "manage_accounts"; size: 18; color: M3.c.primary; anchors.verticalCenter: parent.verticalCenter }
                                    Text { text: "管理帳號／新增帳號"; color: M3.c.primary; font.pixelSize: M3.tLabel; font.weight: Font.Medium; anchors.verticalCenter: parent.verticalCenter }
                                }
                                MouseArea {
                                    id: manageArea
                                    anchors.fill: parent; hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: { acctMenu.close(); win.go(1) }
                                }
                            }
                        }
                    }
                }
            }
        }

        // 頁面舞台
        Item {
            id: stage
            x: 0; y: 86
            width: parent.width - (win.termSide && win.termOpen ? drawer.width + 12 : 0)
            Behavior on width { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.standard } }
            height: parent.height - 86 - (Backend.settings.showStatusBar !== false ? 36 : 10)
            Repeater {
                model: ["pages/Dash.qml", "pages/Accounts.qml", "pages/Courses.qml", "pages/Reports.qml", "pages/Network.qml", "pages/Settings.qml"]
                delegate: Loader {
                    property bool seen: false
                    readonly property bool current: win.page === index
                    onCurrentChanged: if (current) seen = true
                    onLoaded: {
                        if (item.navigate) item.navigate.connect(win.go)
                        if (item.notify) item.notify.connect(win.toast)
                        if (item.toastWith) item.toastWith.connect(win.toastWith)
                        if (item.openTerminal) item.openTerminal.connect(function () { win.termOpen = true })
                    }
                    Component.onCompleted: if (current) seen = true
                    source: seen ? modelData : ""
                    width: stage.width; height: stage.height
                    opacity: current ? 1 : 0
                    visible: opacity > 0.01
                    y: current ? 0 : 22
                    Behavior on opacity { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.standard } }
                    Behavior on y { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.emphasized } }
                }
            }
        }

        // 底部狀態列
        Rectangle {
            id: status
            x: 16; width: parent.width - 32
            height: 30; radius: 10
            anchors.bottom: parent.bottom; anchors.bottomMargin: 8
            visible: Backend.settings.showStatusBar !== false
            color: M3.alpha(M3.c.surfaceContainerHighest, 0.55)
            Row {
                anchors.left: parent.left; anchors.leftMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Rectangle {
                    width: 7; height: 7; radius: 4
                    anchors.verticalCenter: parent.verticalCenter
                    color: Backend.accounts.length > 0 && Backend.accounts[Backend.selected] && Backend.accounts[Backend.selected].cookie === "valid" ? M3.c.success
                         : Backend.accounts.length > 0 && Backend.accounts[Backend.selected] && Backend.accounts[Backend.selected].cookie === "expired" ? M3.c.error : M3.c.warning
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Backend.accounts.length > 0 && Backend.accounts[Backend.selected]
                          ? Backend.accounts[Backend.selected].name + " · " + Backend.accounts[Backend.selected].email : "尚未連結帳號"
                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                }
                Rectangle { width: 1; height: 12; color: M3.c.outlineVariant; anchors.verticalCenter: parent.verticalCenter }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Backend.accounts.length + " 個帳號 · " + Backend.courses.length + " 個課程網址"
                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                }
                Rectangle { width: 1; height: 12; color: M3.c.outlineVariant; anchors.verticalCenter: parent.verticalCenter }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: win.termOpen ? "終端機已開啟 · Ctrl ` 關閉" : "cool.py CLI · accounts.json 同步"
                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                }
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Icon { anchors.verticalCenter: parent.verticalCenter; name: "palette"; size: 13; color: M3.c.onSurfaceVariant }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Backend.settings.themeId + " · " + Backend.variant
                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                }
                Rectangle { width: 1; height: 12; color: M3.c.outlineVariant; anchors.verticalCenter: parent.verticalCenter }
                Text {
                    id: clockText
                    anchors.verticalCenter: parent.verticalCenter
                    text: Qt.formatTime(new Date(), "hh:mm")
                    color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro; font.weight: Font.DemiBold
                    Timer { interval: 15000; running: true; repeat: true; onTriggered: clockText.text = Qt.formatTime(new Date(), "hh:mm") }
                }
            }
        }

        // 終端抽屜
        Rectangle {
            id: drawer
            width: win.termSide ? Math.max(360, Math.min(win.termWidth, parent.width * 0.7)) : parent.width - 40
            height: win.termSide ? parent.height - 86 - 48 : Math.max(280, Math.min(win.termHeight, parent.height * 0.7))
            radius: 26
            x: win.termSide ? (win.termOpen ? parent.width - width - 16 : parent.width + 24) : 20
            y: win.termSide ? 86 : (win.termOpen ? parent.height - height - 48 : parent.height + 24)
            visible: win.termSide ? x < parent.width : y < parent.height
            Behavior on x { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
            color: M3.c.surfaceContainerHigh
            border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.5)
            Behavior on y { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
            // 終端抽屜（含 Chromium/xterm）只在需要時才建立：開啟過終端或仍有 shell 在跑才載入，
            // 沒有任何終端時整個 WebEngine 會被釋放，閒置記憶體明顯較低。
            // 終端抽屜（含 Chromium/xterm）只在需要時才建立：開啟過終端或仍有 shell 在跑才載入，
            // 沒有任何終端時整個 WebEngine 會被釋放，閒置記憶體明顯較低。
            // 不用 asynchronous / source 網址：實測那樣會把載入 QtWebEngine 模組的約 1.3 秒凍結挪到「第一次開啟終端機」，
            // 反而比較糟；維持以型別載入，開啟當下只有約 0.15 秒。
            Loader {
                anchors.fill: parent
                active: win.termOpen || Backend.terminalCount > 0
                sourceComponent: TermDrawer {
                    active: win.termOpen
                    onClose: win.termOpen = false
                    onResized: function (dy) {
                        if (win.termSide) win.termWidth = Math.max(360, Math.min(win.width * 0.7, win.termWidth + dy))
                        else win.termHeight = Math.max(280, Math.min(screen.height - 120, win.termHeight + dy))
                    }
                }
            }
        }
    }

    // ───────── 指令面板 ─────────
    Rectangle {
        anchors.fill: parent; color: M3.c.scrim; opacity: win.launcherOpen ? 0.5 : 0; visible: opacity > 0.01
        Behavior on opacity { NumberAnimation { duration: M3.dMed } }
        MouseArea { anchors.fill: parent; onClicked: win.launcherOpen = false }
    }
    Launcher {
        id: launcher
        x: (parent.width - width) / 2
        y: win.launcherOpen ? 96 : 66
        opacity: win.launcherOpen ? 1 : 0; visible: opacity > 0.01
        scale: win.launcherOpen ? 1 : 0.94
        Behavior on y { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
        Behavior on opacity { NumberAnimation { duration: M3.dMed } }
        Behavior on scale { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
        onChosen: function (item) {
            win.launcherOpen = false
            if (item.kind === "page") win.go(item.value)
            else if (item.kind === "account") { Backend.select(item.value); win.go(1) }
            else if (item.kind === "course") { Backend.openUrl(item.value); win.go(2) }
            else if (item.kind === "action") {
                if (item.value === "theme") Backend.setScheme(Backend.seed, Backend.variant, !Backend.dark, Backend.contrast)
                else if (item.value === "terminal") win.termOpen = !win.termOpen
                else if (item.value === "export") { win.go(3); Backend.exportReport("txt") }
            }
        }
        Connections { target: win; function onLauncherOpenChanged() { if (win.launcherOpen) launcher.reset() } }
    }

    // ───────── Snackbar ─────────
    Rectangle {
        anchors.horizontalCenter: parent.horizontalCenter
        y: win.toastText !== "" ? parent.height - 84 : parent.height + 20
        height: 46; width: toastRow.width + 32; radius: 14; color: M3.c.inverseSurface
        Behavior on y { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
        Row {
            id: toastRow
            anchors.centerIn: parent
            spacing: 10
            Icon { anchors.verticalCenter: parent.verticalCenter; name: win.toastIcon; size: 18; fill: 1; color: M3.c.inverseOnSurface }
            Text { id: toastLabel; anchors.verticalCenter: parent.verticalCenter; text: win.toastText; color: M3.c.inverseOnSurface; font.pixelSize: M3.tBody }
        }
    }

    // ───────── 自動鎖定遮罩 ─────────
    Rectangle {
        anchors.fill: parent
        z: 300
        visible: win.locked
        color: M3.c.surface

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Vertical
                GradientStop { position: 0.0; color: M3.alpha(M3.c.primaryContainer, 0.35) }
                GradientStop { position: 0.55; color: M3.alpha(M3.c.surface, 0) }
            }
        }

        Column {
            anchors.centerIn: parent
            spacing: 14

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 72; height: 72; radius: 24
                color: M3.c.primaryContainer
                Icon { anchors.centerIn: parent; name: "lock"; fill: 1; size: 34; color: M3.c.onPrimaryContainer }
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "已自動鎖定"
                color: M3.c.onSurface; font.pixelSize: M3.tTitle
                font.weight: Font.DemiBold
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "閒置超過 " + win.lockAfter + " 分鐘，介面已鎖定。"
                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
            }
            Field {
                id: unlockField
                width: 300
                label: "輸入帳號密碼解鎖"
                password: true
                visible: Backend.hasUnlockPassword()
                onAccepted: win.unlockNow()
                Component.onCompleted: if (visible) forceInput()
            }
            Text {
                visible: win.unlockError !== ""
                anchors.horizontalCenter: parent.horizontalCenter
                text: win.unlockError
                color: M3.c.error; font.pixelSize: M3.tLabel
            }
            Btn {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "解鎖"; icon: "lock_open"; kind: "filled"
                onClicked: win.unlockNow()
            }
        }
    }
}


