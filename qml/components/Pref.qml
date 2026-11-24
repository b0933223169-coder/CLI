import QtQuick
import "."

// 設定列：左側文字，右側控制項（預設屬性）
Item {
    id: p
    property string title: ""
    property string desc: ""
    property string icon: ""
    property bool dense: false
    default property alias control: holder.data
    implicitHeight: Math.max(dense ? 48 : 60, left.height + 16)
    width: parent ? parent.width : 0

    Row {
        id: left
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Rectangle {
            visible: p.icon !== ""
            width: 34; height: 34; radius: 11
            color: M3.alpha(M3.c.primary, 0.10)
            Icon { anchors.centerIn: parent; name: p.icon; size: 18; color: M3.c.primary }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            width: Math.max(120, p.width - holder.width - (p.icon !== "" ? 58 : 12) - 32)
            Text {
                text: p.title; color: M3.c.onSurface
                font.pixelSize: M3.tBody; font.weight: Font.Medium
                width: parent.width; elide: Text.ElideRight
            }
            Text {
                visible: p.desc !== ""
                text: p.desc; color: M3.c.onSurfaceVariant
                font.pixelSize: M3.tLabel
                width: parent.width; wrapMode: Text.WordWrap; lineHeight: 1.25
            }
        }
    }

    Row {
        id: holder
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
    }
}
