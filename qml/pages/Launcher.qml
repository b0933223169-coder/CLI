import QtQuick
import Cool 1.0
import "../components"

// 指令面板：頁面、動作、帳號、課程一次搜尋
Rectangle {
    id: l
    width: 620
    height: 72 + body.height + 62
    radius: 26
    color: M3.c.surfaceContainerHigh
    border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.6)
    signal chosen(var item)

    property int sel: 0
    readonly property string query: q.text.trim()

    readonly property var allItems: {
        var out = []
        var pages = ["工作台", "帳號", "課程", "報表", "網路", "設定"]
        var icons = ["space_dashboard", "group", "menu_book", "monitoring", "lan", "tune"]
        for (var i = 0; i < pages.length; i++)
            out.push({ group: "頁面", label: pages[i], sub: "前往" + pages[i] + "頁面", icon: icons[i], kind: "page", value: i })
        out.push({ group: "動作", label: "切換深淺色", sub: "在亮色與暗色主題之間切換", icon: "contrast", kind: "action", value: "theme" })
        out.push({ group: "動作", label: "開關終端機", sub: "Ctrl ` 也可以", icon: "terminal", kind: "action", value: "terminal" })
        out.push({ group: "動作", label: "匯出學習報表", sub: "前往報表頁選擇匯出格式", icon: "download", kind: "action", value: "export" })
        for (var a = 0; a < Backend.accounts.length; a++)
            out.push({ group: "帳號", label: Backend.accounts[a].name, sub: Backend.accounts[a].email + " · " + (Backend.accounts[a].cookie === "valid" ? "登入有效" : Backend.accounts[a].cookie === "expired" ? "已過期" : "待檢查"),
                       icon: "person", kind: "account", value: a })
        for (var c = 0; c < Backend.courses.length; c++)
            out.push({ group: "課程", label: Backend.courses[c].alias, sub: Backend.courses[c].category + " · " + Backend.courses[c].url,
                       icon: "menu_book", kind: "course", value: Backend.courses[c].alias })
        return out
    }
    readonly property var filtered: {
        if (query === "") return allItems
        var qq = query.toLowerCase()
        return allItems.filter(function (it) {
            return it.label.toLowerCase().indexOf(qq) >= 0 || it.sub.toLowerCase().indexOf(qq) >= 0 || it.group.indexOf(query) >= 0
        })
    }
    readonly property var groups: ["頁面", "動作", "帳號", "課程"]
    property var shownRows: {
        var rows = [], n = 0
        for (var g = 0; g < groups.length && n < 7; g++) {
            var items = filtered.filter(function (it) { return it.group === groups[g] })
            if (items.length === 0) continue
            rows.push({ header: groups[g] })
            for (var i = 0; i < items.length && n < 7; i++) { rows.push({ item: items[i], idx: n }); n++ }
        }
        return rows
    }
    readonly property int count: filtered.length
    readonly property int shownCount: Math.min(7, filtered.length)

    function reset() { q.text = ""; sel = 0; q.forceActiveFocus() }
    function move(d) {
        if (shownCount === 0) return
        sel = (sel + d + shownCount) % shownCount
    }
    function runSel() {
        if (shownCount > 0 && filtered[sel]) l.chosen(filtered[sel])
    }
    Component.onCompleted: q.forceActiveFocus()

    // 搜尋列
    Rectangle {
        x: 14; y: 14; width: parent.width - 28; height: 48; radius: 16
        color: M3.c.surfaceContainerLowest
        Icon { x: 14; anchors.verticalCenter: parent.verticalCenter; name: "search"; size: 20; color: M3.c.primary }
        TextInput {
            id: q
            x: 44; width: parent.width - 60; height: parent.height
            verticalAlignment: TextInput.AlignVCenter
            color: M3.c.onSurface; font.pixelSize: M3.tBodyLg; clip: true
            selectByMouse: true
            selectionColor: M3.c.primary; selectedTextColor: M3.c.onPrimary
            onTextChanged: l.sel = 0
            onAccepted: l.runSel()
            Keys.onDownPressed: l.move(1)
            Keys.onUpPressed: l.move(-1)
            Text {
                visible: q.text === ""
                anchors.verticalCenter: parent.verticalCenter
                text: "搜尋頁面、帳號、課程或輸入指令…"
                color: M3.c.onSurfaceVariant; font.pixelSize: M3.tBodyLg
            }
        }
        Rectangle {
            anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
            width: 40; height: 24; radius: 7; color: M3.c.surfaceContainerHighest
            Text { anchors.centerIn: parent; text: "Esc"; color: M3.c.onSurfaceVariant; font.pixelSize: 10 }
        }
    }

    Column {
        id: body
        x: 12; y: 72; width: parent.width - 24
        Repeater {
            model: l.shownRows
            delegate: Item {
                width: body.width
                height: modelData.header !== undefined ? 26 : 48
                visible: modelData.header !== undefined ? true : modelData.idx < 8
                Rectangle {
                    visible: modelData.header !== undefined
                    x: 12; y: 6
                    width: parent.width - 24; height: 1
                    color: M3.alpha(M3.c.outlineVariant, 0.4)
                }
                Text {
                    visible: modelData.header !== undefined
                    x: 14; y: 8
                    text: modelData.header !== undefined ? modelData.header : ""
                    color: M3.c.onSurfaceVariant
                    font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.4
                }
                Rectangle {
                    visible: modelData.header === undefined
                    width: parent.width; height: 44; y: 2
                    radius: 14
                    color: modelData.header === undefined && l.sel === modelData.idx ? M3.c.secondaryContainer : "transparent"
                    Behavior on color { ColorAnimation { duration: 90 } }
                    Rectangle {
                        x: 8; width: 32; height: 32; radius: 10; anchors.verticalCenter: parent.verticalCenter
                        color: l.sel === modelData.idx ? M3.alpha(M3.c.onSecondaryContainer, 0.10) : M3.c.surfaceContainerHighest
                        Icon {
                            anchors.centerIn: parent
                            name: modelData.header === undefined ? modelData.item.icon : ""
                            size: 17
                            color: l.sel === modelData.idx ? M3.c.onSecondaryContainer : M3.c.onSurfaceVariant
                        }
                    }
                    Text {
                        x: 50; y: 5
                        text: modelData.header === undefined ? modelData.item.label : ""
                        color: l.sel === modelData.idx ? M3.c.onSecondaryContainer : M3.c.onSurface
                        font.pixelSize: M3.tBody; font.weight: Font.Medium
                    }
                    Text {
                        x: 50; y: 24
                        width: parent.width - 130
                        text: modelData.header === undefined ? modelData.item.sub : ""
                        color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                        elide: Text.ElideRight
                    }
                    Text {
                        visible: modelData.header === undefined && l.sel === modelData.idx
                        anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
                        text: "Enter"; color: M3.c.onSecondaryContainer; font.pixelSize: 10; font.weight: Font.Bold
                    }
                    StateLayer {
                        visible: modelData.header === undefined
                        anchors.fill: parent; radius: 14
                        color: M3.c.onSecondaryContainer
                        onClicked: { l.sel = modelData.idx; l.runSel() }
                    }
                }
            }
        }
    }

    Row {
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.leftMargin: 22
        anchors.bottomMargin: 16
        spacing: 14
        Text { text: "↑ ↓ 選擇"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
        Text { text: "Enter 執行"; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
        Text {
            text: l.count + " 個結果" + (l.count > l.shownCount ? " · 顯示前 " + l.shownCount + " 筆" : "")
            color: M3.c.primary; font.pixelSize: M3.tMicro; font.weight: Font.DemiBold
        }
    }
}
