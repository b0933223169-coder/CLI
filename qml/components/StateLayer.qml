import QtQuick
import "."

// M3 狀態層：hover 8%、press 12%
MouseArea {
    id: root
    property color color: M3.c.onSurface
    property real radius: 0
    property bool disabled: false
    hoverEnabled: true
    enabled: !disabled
    cursorShape: Qt.PointingHandCursor
    Rectangle {
        anchors.fill: parent
        radius: root.radius
        color: root.color
        opacity: root.pressed ? 0.12 : (root.containsMouse ? 0.08 : 0)
        Behavior on opacity { NumberAnimation { duration: M3.dShort } }
    }
}
