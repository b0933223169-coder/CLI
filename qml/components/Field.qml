import QtQuick
import "."

Item {
    id: f
    property string label: ""
    property alias text: input.text
    property bool password: false
    signal accepted()
    implicitHeight: 64
    width: parent ? parent.width : implicitWidth
    function forceInput() { input.forceActiveFocus() }
    Text { id: lab; text: f.label; color: input.activeFocus ? M3.c.primary : M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel; font.weight: Font.DemiBold; x: 4 }
    Rectangle {
        y: lab.height + 4; width: parent.width; height: 44
        radius: M3.rLg; color: "transparent"
        border.width: input.activeFocus ? 2 : 1
        border.color: input.activeFocus ? M3.c.primary : M3.c.outline
        TextInput { id: input; anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 16; verticalAlignment: TextInput.AlignVCenter
            color: M3.c.onSurface; font.pixelSize: M3.tBody; echoMode: f.password ? TextInput.Password : TextInput.Normal; selectByMouse: true; clip: true
            selectionColor: M3.c.primary; selectedTextColor: M3.c.onPrimary
            onAccepted: f.accepted() }
    }
}
