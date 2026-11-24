import QtQuick
import QtQuick.Shapes
import "."

// 環形進度（Caelestia 儀表板的圓環）
Item {
    id: ring
    property real value: 0.5
    property real thickness: 10
    property color track: M3.c.surfaceContainerHighest
    property color fill: M3.c.primary
    property string label: ""
    property string caption: ""
    implicitWidth: 120; implicitHeight: 120
    property real shown: 0
    Component.onCompleted: shown = value
    onValueChanged: shown = value
    Behavior on shown { NumberAnimation { duration: 900; easing.type: Easing.BezierSpline; easing.bezierCurve: M3.emphasized } }
    Shape {
        anchors.fill: parent
        layer.enabled: true; layer.samples: 4
        ShapePath {
            strokeColor: ring.track; strokeWidth: ring.thickness; fillColor: "transparent"; capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: ring.width / 2; centerY: ring.height / 2; radiusX: ring.width / 2 - ring.thickness / 2; radiusY: radiusX; startAngle: 135; sweepAngle: 270 }
        }
        ShapePath {
            strokeColor: ring.fill; strokeWidth: ring.thickness; fillColor: "transparent"; capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: ring.width / 2; centerY: ring.height / 2; radiusX: ring.width / 2 - ring.thickness / 2; radiusY: radiusX; startAngle: 135; sweepAngle: 270 * Math.max(0.001, Math.min(1, ring.shown)) }
        }
    }
    Column {
        anchors.centerIn: parent
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: ring.label; color: M3.c.onSurface; font.pixelSize: ring.width * 0.2; font.weight: Font.DemiBold }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: ring.caption; color: M3.c.onSurfaceVariant; font.pixelSize: M3.tLabel }
    }
}
