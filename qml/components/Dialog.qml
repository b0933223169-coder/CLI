import QtQuick
import "."

// 模態對話框：直接宣告子項即為內容
Item {
    id: dlg
    anchors.fill: parent
    visible: opacity > 0.01
    opacity: 0
    z: 100
    property string title: ""
    property string subtitle: ""
    property string icon: ""
    property int preferredWidth: 520
    default property alias body: bodyCol.data
    signal closed()

    function open() { opacity = 1 }
    function close() { opacity = 0; dlg.closed() }

    Rectangle {
        anchors.fill: parent; color: M3.c.scrim; opacity: dlg.opacity * 0.55
        MouseArea { anchors.fill: parent; onClicked: dlg.close() }
    }

    Rectangle {
        id: card
        anchors.centerIn: parent
        width: Math.min(dlg.preferredWidth, dlg.width - 80)
        height: cardCol.height + 48
        radius: M3.rXl
        color: M3.c.surfaceContainerHigh
        border.width: 1; border.color: M3.alpha(M3.c.outlineVariant, 0.6)
        scale: dlg.opacity === 1 ? 1 : 0.94
        Behavior on scale { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }

        Column {
            id: cardCol
            x: 24; y: 24; width: parent.width - 48; spacing: 18

            Row {
                width: parent.width; spacing: 14
                Rectangle {
                    visible: dlg.icon !== ""
                    width: 44; height: 44; radius: 16; color: M3.c.primaryContainer
                    Icon { anchors.centerIn: parent; name: dlg.icon; size: 22; fill: 1; color: M3.c.onPrimaryContainer }
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - (dlg.icon !== "" ? 58 : 0) - 40
                    Text { text: dlg.title; color: M3.c.onSurface; font.pixelSize: M3.tTitle; font.weight: Font.Medium }
                    Text {
                        visible: dlg.subtitle !== ""; width: parent.width
                        text: dlg.subtitle; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tBody
                        wrapMode: Text.WordWrap; lineHeight: 1.35
                    }
                }
                IconBtn {
                    anchors.verticalCenter: parent.verticalCenter
                    icon: "close"; tip: "關閉"; size: 36; iconSize: 18
                    onClicked: dlg.close()
                }
            }

            Column {
                id: bodyCol
                objectName: "dialogBody"
                width: parent.width
                spacing: 14
            }
        }
    }
}
