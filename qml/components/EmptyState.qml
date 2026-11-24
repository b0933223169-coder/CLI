import QtQuick
import "."

// 空狀態：圖示、標題、說明與一個可選動作
Item {
    id: es
    property string icon: "inbox"
    property string title: "沒有資料"
    property string desc: ""
    property string actionText: ""
    signal action()
    implicitHeight: 200
    width: parent ? parent.width : 0

    Column {
        anchors.centerIn: parent
        spacing: 8
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 56; height: 56; radius: 20
            color: M3.c.surfaceContainerHighest
            Icon { anchors.centerIn: parent; name: es.icon; size: 26; color: M3.c.onSurfaceVariant }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: es.title; color: M3.c.onSurface
            font.pixelSize: M3.tBody; font.weight: Font.DemiBold
        }
        Text {
            visible: es.desc !== ""
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(360, es.width - 40)
            text: es.desc; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
            horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
        }
        Btn {
            visible: es.actionText !== ""
            anchors.horizontalCenter: parent.horizontalCenter
            text: es.actionText; kind: "tonal"; small: true
            onClicked: es.action()
        }
    }
}
