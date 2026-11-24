import QtQuick
import "."

// 方形勾選框
Item {
    id: cb
    property bool checked: false
    property int size: 22
    signal toggled(bool value)
    implicitWidth: size
    implicitHeight: size

    Rectangle {
        anchors.fill: parent
        radius: 7
        color: cb.checked ? M3.c.primary : "transparent"
        border.width: cb.checked ? 0 : 2
        border.color: M3.c.outline
        Behavior on color { ColorAnimation { duration: M3.dShort } }
        Icon {
            anchors.centerIn: parent
            name: "check"; size: cb.size - 6
            color: M3.c.onPrimary
            opacity: cb.checked ? 1 : 0
            scale: cb.checked ? 1 : 0.5
            Behavior on opacity { NumberAnimation { duration: M3.dShort } }
            Behavior on scale { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
        }
    }
    StateLayer {
        anchors.fill: parent
        radius: 8
        onClicked: { cb.checked = !cb.checked; cb.toggled(cb.checked) }
    }
}
