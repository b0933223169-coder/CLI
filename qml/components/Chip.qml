import QtQuick
import "."

Rectangle {
    id: chip
    property string text: ""
    property string icon: ""
    property color tone: M3.c.secondaryContainer
    property color onTone: M3.c.onSecondaryContainer
    implicitHeight: 28
    implicitWidth: row.implicitWidth + 20
    radius: height / 2
    color: tone
    Row {
        id: row
        anchors.centerIn: parent
        spacing: 6
        Icon { visible: chip.icon !== ""; name: chip.icon; size: 15; fill: 1; color: chip.onTone; anchors.verticalCenter: parent.verticalCenter }
        Text { text: chip.text; color: chip.onTone; font.pixelSize: M3.tLabel; font.weight: Font.DemiBold; anchors.verticalCenter: parent.verticalCenter }
    }
}
