import QtQuick
import "."

// 細長進度條
Item {
    id: pb
    property real value: 0.5
    property color tone: M3.c.primary
    property color track: M3.c.surfaceContainerHighest
    property int thickness: 8
    implicitHeight: thickness
    implicitWidth: 160
    property real shown: 0
    Component.onCompleted: shown = value
    onValueChanged: shown = value
    Behavior on shown { NumberAnimation { duration: M3.dLong; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.emphasized } }

    Rectangle { anchors.fill: parent; radius: height / 2; color: pb.track }
    Rectangle {
        width: Math.max(0, Math.min(1, pb.shown)) * pb.width
        height: parent.height; radius: height / 2
        color: pb.tone
    }
}
