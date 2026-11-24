import QtQuick
import "."

Rectangle {
    id: card
    property color tone: M3.c.surfaceContainer
    property color onTone: M3.c.onSurface
    property bool interactive: false
    signal clicked()
    radius: M3.rXl
    color: tone
    Behavior on color { ColorAnimation { duration: M3.dMed } }
    scale: hit.pressed ? 0.985 : 1
    Behavior on scale { NumberAnimation { duration: M3.dShort; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.spring } }
    StateLayer { id: hit; anchors.fill: parent; radius: card.radius; color: card.onTone; visible: card.interactive; enabled: card.interactive; onClicked: card.clicked() }
}
