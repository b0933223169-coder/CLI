import QtQuick
import QtQuick.Controls
import QtWebEngine 1.10
import QtWebChannel 1.0
import Cool 1.0
import "../components"

// 內嵌終端機：真正的 ConPTY（pywinpty）＋ 終端模擬（pyte），在抽屜裡直接畫出 shell。
// 每一個分頁都是獨立程序，鍵盤輸入原樣送進 PTY，不會開外部視窗。
Item {
    id: t
    objectName: "termDrawer"
    signal close()
    signal resized(real dy)

    readonly property var profiles: Backend.terminalProfiles
    readonly property var tabs: Backend.terminalTabs
    property bool menuOpen: false
    property bool active: false
    // 目前分頁專屬的 WebChannel（每個分頁有獨立的 ConPTY 橋）
    property var activeChannel: Backend.terminalChannel(Backend.activeTerminalId)

    readonly property color termBg: Backend.settings.terminalBg
    readonly property color termFg: Backend.settings.terminalText
    readonly property color termAccent: Backend.settings.terminalCursor
    readonly property int termFontSize: Backend.settings.terminalFontSize || 13
    readonly property string termFont: Backend.settings.terminalFont || M3.mono

    onActiveChanged: if (active) {
        menuOpen = false
        Qt.callLater(function () { termView.forceActiveFocus() })
    }

    function focusTerm() { Qt.callLater(function () { termView.forceActiveFocus() }) }

    // 拖曳調整大小：下方停靠時拖上緣調高度；右側停靠時拖左緣調寬度
    readonly property bool side: Backend.settings.terminalDock === "right"
    Rectangle {
        x: t.side ? 7 : (parent.width - width) / 2
        y: t.side ? (parent.height - height) / 2 : 7
        width: t.side ? 4 : 46; height: t.side ? 46 : 4; radius: 2
        color: M3.alpha(M3.c.onSurfaceVariant, 0.35)
    }
    MouseArea {
        x: 0; y: 0
        width: t.side ? 18 : parent.width; height: t.side ? parent.height : 18
        cursorShape: t.side ? Qt.SizeHorCursor : Qt.SizeVerCursor
        property real startP: 0
        // 用視窗座標：抽屜縮放時本身會位移，本地座標會互相抵消造成抖動
        function winPos(m) { var q = mapToItem(null, m.x, m.y); return t.side ? q.x : q.y }
        onPressed: (m) => startP = winPos(m)
        onPositionChanged: (m) => {
            if (!pressed) return
            var p = winPos(m)
            t.resized(startP - p)
            startP = p
        }
    }

    // ── 標題列 ──
    Row {
        x: 18; y: 16; spacing: 10
        Rectangle {
            width: 30; height: 30; radius: 9
            anchors.verticalCenter: parent.verticalCenter
            color: M3.c.secondaryContainer
            Icon { anchors.centerIn: parent; name: "terminal"; size: 16; color: M3.c.onSecondaryContainer }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 1
            Row {
                spacing: 8
                Text {
                    text: "內嵌終端機"
                    color: M3.c.onSurface; font.pixelSize: M3.tLabel; font.weight: Font.DemiBold
                }
                Rectangle {
                    width: countRow.width + 14; height: 18; radius: 9
                    color: M3.alpha(M3.c.onSurfaceVariant, 0.12)
                    Row {
                        id: countRow
                        anchors.centerIn: parent; spacing: 4
                        Icon { name: "tab"; size: 11; anchors.verticalCenter: parent.verticalCenter; color: M3.c.onSurfaceVariant }
                        Text {
                            text: Backend.terminalCount + " 個分頁"
                            color: M3.c.onSurfaceVariant; font.pixelSize: 9; font.weight: Font.Bold
                        }
                    }
                }
            }
            Text {
                text: Backend.terminalCount > 0
                      ? Backend.terminalProfile + " · " + Backend.terminalStatus
                      : "選一個你電腦上的終端機，開啟後會自動執行 cool.py"
                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                width: Math.min(implicitWidth, 430); elide: Text.ElideRight
            }
        }
    }

    Row {
        anchors.right: parent.right; anchors.rightMargin: 12; y: 15
        spacing: 4
        IconBtn {
            icon: "add"; tip: "新增終端分頁"; size: 34; iconSize: 18
            active: t.menuOpen
            onClicked: { t.menuOpen = !t.menuOpen; t.focusTerm() }
        }
        IconBtn {
            icon: "delete_sweep"; tip: "清除這個分頁的畫面（Ctrl+Shift+K）"; size: 34; iconSize: 17
            onClicked: { Backend.clearTerminal(); t.focusTerm() }
        }
        IconBtn {
            icon: Backend.terminalRunning ? "stop_circle" : "restart_alt"
            tip: Backend.terminalRunning ? "停止目前分頁" : "重新啟動目前分頁"
            size: 34; iconSize: 18
            onClicked: {
                if (Backend.terminalRunning) Backend.stopTerminal()
                else Backend.restartTerminal()
                t.focusTerm()
            }
        }
        IconBtn { icon: "keyboard_arrow_down"; tip: "收合終端機"; size: 34; iconSize: 19; onClicked: t.close() }
    }

    // ── 分頁列 ──
    Flickable {
        id: tabBar
        x: 16; y: 52; width: parent.width - 32; height: 34
        contentWidth: tabRow.width
        contentHeight: height
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.HorizontalFlick

        Row {
            id: tabRow
            spacing: 6
            Repeater {
                model: t.tabs
                delegate: Rectangle {
                    width: 176; height: 32; radius: 10
                    color: modelData.active ? M3.c.secondaryContainer
                         : tabHover.containsMouse ? M3.c.surfaceContainerHighest
                         : M3.alpha(M3.c.surfaceContainerHighest, 0.55)
                    border.width: modelData.active ? 1 : 0
                    border.color: M3.alpha(M3.c.primary, 0.55)
                    Behavior on color { ColorAnimation { duration: M3.dShort } }

                    Rectangle {
                        x: 10; anchors.verticalCenter: parent.verticalCenter
                        width: 6; height: 6; radius: 3
                        color: modelData.running ? M3.c.success : M3.c.onSurfaceVariant
                    }
                    Text {
                        x: 22; width: parent.width - 52
                        anchors.verticalCenter: parent.verticalCenter
                        text: modelData.label
                        color: modelData.active ? M3.c.onSecondaryContainer : M3.c.onSurfaceVariant
                        font.pixelSize: 10
                        font.weight: modelData.active ? Font.DemiBold : Font.Medium
                        elide: Text.ElideRight
                    }
                    Item {
                        width: 22; height: 22
                        anchors.right: parent.right; anchors.rightMargin: 5
                        anchors.verticalCenter: parent.verticalCenter
                        Icon {
                            anchors.centerIn: parent; name: "close"; size: 12
                            color: closeHover.containsMouse ? M3.c.error : M3.c.onSurfaceVariant
                        }
                        MouseArea {
                            id: closeHover
                            anchors.fill: parent; hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Backend.closeTerminalTab(modelData.id)
                        }
                    }
                    MouseArea {
                        id: tabHover
                        anchors.fill: parent; anchors.rightMargin: 26
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            Backend.selectTerminalTab(modelData.id)
                            t.focusTerm()
                        }
                    }
                }
            }
        }
    }
    MouseArea {
        x: 16; y: 52; width: parent.width - 32; height: 34
        acceptedButtons: Qt.NoButton
        onWheel: function (w) {
            tabBar.contentX = Math.max(0, Math.min(tabBar.contentWidth - tabBar.width,
                                                 tabBar.contentX - w.angleDelta.y))
            w.accepted = true
        }
    }

    // ── 終端畫面（ConPTY + pyte，直接畫在 QML 上）──
    Rectangle {
        x: 16; y: 92; width: parent.width - 32; height: parent.height - 92 - 32
        radius: 14
        color: t.termBg
        border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.4)
        clip: true

        // VS Code 風格終端：xterm.js 跑在 QWebEngineView（Chromium）裡
        WebEngineView {
            id: termView
            objectName: "terminalView"
            anchors.fill: parent
            anchors.margins: 1
            visible: Backend.terminalCount > 0 && t.activeChannel !== null
            // xterm 資源在 <root>/xterm，此 QML 在 <root>/qml/pages → 上兩層
            url: Qt.resolvedUrl("../../xterm/index.html").toString() + "?sid=" + Backend.activeTerminalId
            webChannel: t.activeChannel
            backgroundColor: t.termBg
            focus: true
        }

        // 還沒有任何分頁
        Column {
            visible: Backend.terminalCount === 0
            width: parent.width
            y: Math.max(20, parent.height * 0.2)
            spacing: 10
            Text {
                width: parent.width; horizontalAlignment: Text.AlignHCenter
                text: "還沒有終端分頁"
                color: t.termFg; opacity: 0.75
                font.family: t.termFont; font.pixelSize: t.termFontSize + 1; font.weight: Font.DemiBold
            }
            Text {
                width: parent.width; horizontalAlignment: Text.AlignHCenter
                text: "用右上角「＋」開一個真正的 shell，會自動執行 cool.py"
                color: t.termFg; opacity: 0.5
                font.family: t.termFont; font.pixelSize: t.termFontSize - 1
            }
            Btn {
                x: (parent.width - width) / 2
                text: "開啟 " + Backend.defaultTerminalProfile
                icon: "play_arrow"; kind: "tonal"; small: true
                onClicked: { Backend.startTerminal(Backend.defaultTerminal); t.focusTerm() }
            }
        }
    }

    // ── 底部提示 ──
    Row {
        x: 22; y: parent.height - 24; spacing: 8
        Icon { name: "keyboard"; size: 12; anchors.verticalCenter: parent.verticalCenter; color: M3.c.onSurfaceVariant }
        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: "真實 ConPTY 終端 · 選取後 Ctrl+C / Ctrl+Shift+C 複製 · Ctrl+Shift+V 貼上 · 右鍵選單 · 輸入 /exit 關閉工作臺"
            color: M3.c.onSurfaceVariant; font.pixelSize: 9; opacity: 0.8
        }
    }
    Text {
        anchors.right: parent.right; anchors.rightMargin: 22
        y: parent.height - 24
        text: Backend.terminalCount > 0 ? Backend.terminalStatus : ""
        color: M3.c.onSurfaceVariant; font.pixelSize: 9; opacity: 0.7
    }

    // ── 新分頁選單（＋）──
    Item {
        anchors.fill: parent
        visible: t.menuOpen
        z: 60

        MouseArea { anchors.fill: parent; onClicked: t.menuOpen = false }

        Rectangle {
            x: parent.width - 300; y: 88
            width: 280; height: menuCol.height + 16; radius: 14
            color: M3.c.surfaceContainerHigh
            border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.6)

            Column {
                id: menuCol
                x: 6; y: 8; width: parent.width - 12; spacing: 1

                Text {
                    x: 10; width: parent.width - 20
                    text: "新增分頁"; color: M3.c.onSurfaceVariant
                    font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1
                    bottomPadding: 2
                }

                Repeater {
                    model: t.profiles
                    delegate: Rectangle {
                        width: menuCol.width; height: 34; radius: 9
                        color: mh.containsMouse ? M3.c.secondaryContainer : "transparent"
                        Icon { x: 10; anchors.verticalCenter: parent.verticalCenter; name: modelData.icon; size: 15; color: M3.c.onSurfaceVariant }
                        Text {
                            x: 34; anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 46
                            text: modelData.label
                            color: M3.c.onSurface; font.pixelSize: M3.tLabel
                            elide: Text.ElideRight
                        }
                        MouseArea {
                            id: mh
                            anchors.fill: parent; hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            ToolTip.visible: containsMouse && modelData.path !== ""
                            ToolTip.delay: 500
                            ToolTip.text: modelData.path
                            onClicked: {
                                t.menuOpen = false
                                Backend.startTerminal(modelData.id)
                                t.focusTerm()
                            }
                        }
                    }
                }

                Text {
                    x: 10; width: parent.width - 20
                    text: "開啟後自動執行 cool.py"
                    color: M3.c.onSurfaceVariant; font.pixelSize: 9; opacity: 0.8
                    topPadding: 2
                }
            }
        }
    }
}
