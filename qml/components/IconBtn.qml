import QtQuick
import "."

// 圓形圖示鈕：hover 時顯示文字提示
Item {
    id: ib
    property string icon: ""
    property string tip: ""
    property int size: 40
    property int iconSize: 20
    property bool active: false
    property bool danger: false
    property color tone: "transparent"
    signal clicked()
    implicitWidth: size
    implicitHeight: size

    Rectangle {
        anchors.fill: parent; radius: parent.width / 2
        color: ib.active ? (ib.danger ? M3.c.errorContainer : M3.c.secondaryContainer) : ib.tone
        Behavior on color { ColorAnimation { duration: M3.dShort } }
    }
    Icon {
        anchors.centerIn: parent; name: ib.icon; size: ib.iconSize
        fill: ib.active ? 1 : 0
        color: ib.danger ? M3.c.error : (ib.active ? M3.c.onSecondaryContainer : M3.c.onSurfaceVariant)
    }
    StateLayer { id: layer; anchors.fill: parent; radius: parent.width / 2; onClicked: ib.clicked() }

    Rectangle {
        visible: opacity > 0.01
        opacity: (ib.tip !== "" && layer.containsMouse) ? 1 : 0
        x: (parent.width - width) / 2
        y: -height - 6
        width: tipText.implicitWidth + 20; height: 26; radius: 8
        color: M3.c.inverseSurface
        z: 10
        Behavior on opacity { NumberAnimation { duration: M3.dShort } }
        Text { id: tipText; anchors.centerIn: parent; text: ib.tip; color: M3.c.inverseOnSurface; font.pixelSize: M3.tMicro }
    }
}
