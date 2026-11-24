import QtQuick
import "."

Rectangle {
    id: sw
    property bool checked: false
    signal toggled(bool value)
    width: 52; height: 32; radius: 16
    color: checked ? M3.c.primary : M3.c.surfaceContainerHighest
    border.width: checked ? 0 : 2
    border.color: M3.c.outline
    Behavior on color { ColorAnimation { duration: M3.dShort } }
    Rectangle {
        id: knob
        anchors.verticalCenter: parent.verticalCenter
        width: sw.checked ? 24 : (hit.pressed ? 28 : 16); height: width; radius: width / 2
        x: sw.checked ? parent.width - width - 4 : (hit.pressed ? 2 : 8)
        color: sw.checked ? M3.c.onPrimary : M3.c.outline
        Behavior on x { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
        Behavior on width { NumberAnimation { duration: M3.dMed; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
    }
    StateLayer { id: hit; anchors.fill: parent; radius: parent.radius; onClicked: { sw.checked = !sw.checked; sw.toggled(sw.checked) } }
}
