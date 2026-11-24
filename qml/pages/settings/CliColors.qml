import QtQuick
import Cool 1.0
import "../../components"

Column {
    id: page
    signal notify(string text)
    width: parent ? parent.width : 0
    spacing: M3.gap

    property string expanded: ""

    readonly property var currentReport: Backend.reports.length > 0 ? Backend.reports[Backend.reports.length - 1] : null
    readonly property var prevReport: Backend.reports.length > 1 ? Backend.reports[Backend.reports.length - 2] : null

    function reportLine(r, below) {
        if (!r) return below ? "────────  尚無更多資料  ────────" : "────────  尚無報表資料  ────────"
        return r.month + "  " + (r.platform / 60).toFixed(1) + "h  " + (r.video / 60).toFixed(1) + "h  " +
               (r.practice / 60).toFixed(1) + "h" + (below ? "  未達標" : "")
    }

    function styleOf(key) { return Backend.cliStyle(key) }
    function current(field) { return Backend.settings.cliColors[field] }
    function setStyle(field, key) {
        var m = {}
        var src = Backend.settings.cliColors
        for (var k in src) m[k] = src[k]
        m[field] = key
        Backend.updateSetting("cliColors", m)
        page.notify("「" + field + "」改為 " + key)
    }
    function resetAll() {
        var m = {}
        for (var i = 0; i < Backend.cliFields.length; i++) m[Backend.cliFields[i].key] = Backend.cliFields[i].default
        Backend.updateSetting("cliColors", m)
        page.notify("CLI 報表配色已重設為預設值")
    }

    // 預覽
    Card {
        width: parent.width
        height: pv.height + 44
        Column {
            id: pv
            x: 22; y: 22; width: parent.width - 44; spacing: 12

            SectionTitle {
                width: parent.width
                eyebrow: "CLI REPORT COLORS"
                title: "CLI 報表配色"
                desc: "7 個欄位、13 種 ANSI 樣式；會寫入 CLI 使用的 colors.json"
                Btn {
                    text: "全部重設"; icon: "restart_alt"; kind: "outlined"; small: true
                    onClicked: page.resetAll()
                }
            }

            Rectangle {
                width: parent.width; height: 150
                radius: M3.rLg
                color: "#101418"
                border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.4)
                clip: true

                Column {
                    x: 16; y: 12; spacing: 3
                    Text {
                        text: "════ 學習時間 · Amy Chen ════"
                        color: page.styleOf(page.current("titleText")).fg
                        font.family: M3.mono; font.pixelSize: 11; font.weight: Font.Bold
                    }
                    Text {
                        text: "────────────────────────────"
                        color: page.styleOf(page.current("title")).fg
                        font.family: M3.mono; font.pixelSize: 11
                    }
                    Row {
                        spacing: 0
                        Text { text: "月份   "; color: page.styleOf(page.current("header")).fg; font.family: M3.mono; font.pixelSize: 10; font.weight: Font.Bold }
                        Text { text: "停留   "; color: page.styleOf(page.current("header")).fg; font.family: M3.mono; font.pixelSize: 10; font.weight: Font.Bold }
                        Text { text: "影片   "; color: page.styleOf(page.current("header")).fg; font.family: M3.mono; font.pixelSize: 10; font.weight: Font.Bold }
                        Text { text: "練習"; color: page.styleOf(page.current("header")).fg; font.family: M3.mono; font.pixelSize: 10; font.weight: Font.Bold }
                    }
                    Rectangle {
                        width: parent.width; height: 16; radius: 3
                        color: page.styleOf(page.current("current")).bg ? page.styleOf(page.current("current")).bg : "transparent"
                        Row {
                            Text { text: page.reportLine(page.currentReport, false); color: page.styleOf(page.current("current")).bg ? page.styleOf(page.current("current")).fg : M3.c.onSurface; font.family: M3.mono; font.pixelSize: 10; font.weight: Font.Bold }
                        }
                    }
                    Rectangle {
                        width: parent.width; height: 16; radius: 3
                        color: page.styleOf(page.current("below")).bg ? page.styleOf(page.current("below")).bg : "transparent"
                        Text {
                            text: page.reportLine(page.prevReport, true)
                            color: page.styleOf(page.current("below")).bg ? page.styleOf(page.current("below")).fg : M3.c.onSurface
                            font.family: M3.mono; font.pixelSize: 10
                        }
                    }
                    Text {
                        text: "────────────────────────────"
                        color: page.styleOf(page.current("sep")).fg
                        font.family: M3.mono; font.pixelSize: 10
                    }
                    Text {
                        text: "https://www.coolenglish.edu.tw/mod/quiz/report.php"
                        color: page.styleOf(page.current("url")).fg
                        font.family: M3.mono; font.pixelSize: 9
                    }
                }
            }
        }
    }

    // 欄位
    Repeater {
        model: Backend.cliFields
        delegate: Card {
            width: page.width
            height: fc.height + 44
            property string fieldKey: modelData.key

            Column {
                id: fc
                x: 22; y: 22; width: parent.width - 44; spacing: 10

                Item {
                    width: parent.width; height: 46
                    Rectangle {
                        x: 0; width: 34; height: 34; radius: 11; anchors.verticalCenter: parent.verticalCenter
                        color: M3.c.surfaceContainerHighest
                        Icon { anchors.centerIn: parent; name: fieldIcon(modelData.key); size: 17; color: M3.c.primary }
                    }
                    Column {
                        x: 46; y: 3; spacing: 1
                        Text { text: modelData.label; color: M3.c.onSurface; font.pixelSize: M3.tBody; font.weight: Font.Medium }
                        Text { text: modelData.desc; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro }
                    }
                    Row {
                        anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                        spacing: 8
                        Rectangle {
                            height: 30; width: swlbl.implicitWidth + 22; radius: 9
                            color: page.styleOf(page.current(modelData.key)).bg ? page.styleOf(page.current(modelData.key)).bg : M3.c.surfaceContainerHighest
                            border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.5)
                            Text {
                                id: swlbl; anchors.centerIn: parent
                                text: page.styleOf(page.current(modelData.key)).name + " · " + page.current(modelData.key)
                                color: page.styleOf(page.current(modelData.key)).bg ? page.styleOf(page.current(modelData.key)).fg : M3.c.onSurfaceVariant
                                font.pixelSize: 10; font.weight: Font.Bold; font.family: M3.mono
                            }
                        }
                        IconBtn {
                            icon: page.expanded === modelData.key ? "expand_less" : "expand_more"
                            tip: "選擇樣式"; size: 34; iconSize: 18
                            onClicked: page.expanded = page.expanded === modelData.key ? "" : modelData.key
                        }
                    }
                }

                Flow {
                    visible: page.expanded === modelData.key
                    width: parent.width; spacing: 6
                    Repeater {
                        model: Backend.cliStyles
                        delegate: Rectangle {
                            height: 32; width: slbl.implicitWidth + 22; radius: 9
                            color: modelData.bg ? modelData.bg : M3.c.surfaceContainerHighest
                            border.width: page.current(fieldKey) === modelData.key ? 2 : 1
                            border.color: page.current(fieldKey) === modelData.key ? M3.c.primary : M3.alpha(M3.c.outlineVariant, 0.5)
                            Text {
                                id: slbl; anchors.centerIn: parent
                                text: modelData.name
                                color: modelData.bg ? modelData.fg : M3.c.onSurfaceVariant
                                font.pixelSize: 10; font.weight: Font.DemiBold
                            }
                            StateLayer { anchors.fill: parent; radius: 9; onClicked: page.setStyle(fieldKey, modelData.key) }
                        }
                    }
                }

                Row {
                    visible: page.expanded === modelData.key
                    width: parent.width; spacing: 10
                    Field { id: hexField; width: 200; label: "自訂 HEX（#RRGGBB）" }
                    Btn {
                        y: 22; text: "套用自訂色"; icon: "palette"; kind: "tonal"; small: true
                        onClicked: {
                            var v = hexField.text.trim()
                            if (v.charAt(0) !== "#") v = "#" + v
                            if (/^#[0-9a-fA-F]{6}$/.test(v)) page.setStyle(fieldKey, v.toLowerCase())
                            else page.notify("請輸入 6 位數 HEX 色碼，例如 #ff8800")
                        }
                    }
                    Text {
                        y: 28; text: "也可直接用 cool -c 設定 256 色（COLOR_xxx / BG_xxx）"
                        color: M3.c.onSurfaceVariant; font.pixelSize: M3.tMicro
                    }
                }
            }
        }
    }

    function fieldIcon(k) {
        return k === "title" ? "crop_16_9" : k === "titleText" ? "title" : k === "header" ? "table_chart"
             : k === "current" ? "radio_button_checked" : k === "below" ? "error" : k === "url" ? "link" : "horizontal_rule"
    }
}
