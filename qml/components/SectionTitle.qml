import QtQuick
import "."

// 區塊標題：左側 eyebrow／標題／說明，右側放動作（預設屬性）
Item {
    id: st
    property string eyebrow: ""
    property string title: ""
    property string desc: ""
    property string icon: ""
    default property alias actions: rightRow.data
    implicitHeight: Math.max(46, leftCol.height)
    width: parent ? parent.width : 0

    Row {
        id: leftCol
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: 12
        Rectangle {
            visible: st.icon !== ""
            width: 38; height: 38; radius: 13
            color: M3.c.surfaceContainerHighest
            Icon { anchors.centerIn: parent; name: st.icon; size: 20; color: M3.c.primary }
        }
        Column {
            anchors.verticalCenter: parent.verticalCenter
            spacing: 2
            Text {
                visible: st.eyebrow !== ""
                text: st.eyebrow; color: M3.c.primary
                font.pixelSize: 10; font.weight: Font.Bold; font.letterSpacing: 1.6
            }
            Text { text: st.title; color: M3.c.onSurface; font.pixelSize: M3.tBodyLg; font.weight: Font.DemiBold }
            Text {
                visible: st.desc !== ""
                text: st.desc; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel
            }
        }
    }

    Row {
        id: rightRow
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: 8
    }
}
